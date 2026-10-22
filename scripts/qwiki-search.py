#!/usr/bin/env python3
"""qwiki 检索 —— 磁盘倒排（SQLite FTS5，contentless），按需取卡，不把整库读进上下文。

用法:
  python3 qwiki-search.py [知识库根] <关键词...>          # 默认 ~/qwiki，取前 10 条
  python3 qwiki-search.py <库根> <关键词...> --limit 5
  python3 qwiki-search.py <库根> <关键词...> --json       # 机器可读（给 agent 用）
  python3 qwiki-search.py <库根> --stats                  # 索引现状（文档数 / 体积 / 更新量）
  python3 qwiki-search.py <库根> <关键词...> --rebuild    # 全量重建

索引落在 `<库根>/.qwiki-index.db`（生成物，按 mtime 增量更新）。**删掉不损失任何知识**：
INDEX 仍是唯一入口，本脚本只是「按内容找卡」的加速器——命中之后仍然读卡、仍然沿 `[[...]]` 走。

为什么是 SQLite FTS5（contentless），而不是「内存里一份 JSON」：
  个人库的量级信封是万级。JSON 方案每次查询把整份索引读进内存，万卡时几十 MB、首字节以秒计。
  FTS5 把倒排放在磁盘、只读命中的行；`content=''` 让索引**不存原文**，体积只有存文本方案的三分之一，
  代价是列不可回读——所以排序改成「FTS5 召回候选 → 读那几十张卡自己算分」。

排序口径（与定稿一致）：字段权重 × IDF × (1+log tf)，标题/结论原串命中额外加分。
中文分词用二元组；「什么 / 为什」这类高频词靠 IDF 自动降权。
"""
import importlib.util
import json
import math
import os
import re
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

INDEX_NAME = ".qwiki-index.db"
SCHEMA_VERSION = 6
SHORTLIST = 800               # 精排上限：先按「命中词的 IDF 之和」粗排，取前 N 再算字段权重
FIELD_WEIGHT = {"title": 6.0, "summary": 5.0, "tags": 3.0, "headings": 2.0, "body": 1.0}
CJK_RUN = re.compile(r"[\u4e00-\u9fff]+|[a-z0-9_]+")   # 与 FTS5 的分词边界对齐（_ 保留）


def _load_checker():
    """复用 qwiki-check.py 的解析口径（卡片集 / YAML / 结论行 / 小标题）。"""
    path = Path(__file__).with_name("qwiki-check.py")
    spec = importlib.util.spec_from_file_location("qwiki_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


qc = _load_checker()


def tokens(text):
    """中文二元组 + 单字；ASCII 词小写。索引与查询共用同一套切法。"""
    out = []
    for run in CJK_RUN.findall((text or "").lower()):
        if re.match(r"[\u4e00-\u9fff]", run):
            if len(run) == 1:
                out.append(run)
            else:
                out.extend(run[i:i + 2] for i in range(len(run) - 1))
        else:
            out.append(run)
    return out


def read_card(root, rel):
    """→ (展示用字段, 各字段词频)。索引与精排共用这一套解析，不写第二份。"""
    text = Path(root, rel).read_text(encoding="utf-8")
    fm, body = qc.split(text)
    fields = {
        "title": qc.fm_field(fm, "title"),
        "summary": qc.summary_line(body) or "",
        "tags": " ".join(re.findall(r"\[([^\]]*)\]", qc.fm_field(fm, "tags"))),
        "headings": " ".join(re.findall(r"(?m)^##\s+(.+)$", qc.strip_code(body))),
        "body": body,
    }
    return ({"title": fields["title"], "summary": fields["summary"],
             "tags": fields["tags"]},
            {k: Counter(tokens(v)) for k, v in fields.items()})


def connect(root, fresh=False):
    path = os.path.join(root, INDEX_NAME)
    if os.path.exists(path):
        con0 = sqlite3.connect(path)
        version = con0.execute("PRAGMA user_version").fetchone()[0]
        con0.close()
        if version != SCHEMA_VERSION:
            fresh = True
    if fresh:
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(path + suffix):
                os.remove(path + suffix)
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    con.execute("CREATE TABLE IF NOT EXISTS cards("
                "id INTEGER PRIMARY KEY, path TEXT UNIQUE, mtime REAL, title TEXT, summary TEXT, "
                "t_title TEXT, t_summary TEXT, t_tags TEXT, t_headings TEXT, tags TEXT)")
    # contentless：只存倒排不存原文；detail=none 省掉位置信息（本方案不做短语匹配）
    con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5("
                "body, content='', contentless_delete=1, detail=none, "
                "tokenize=\"unicode61 tokenchars '_'\")")
    return con


def sync(con, root):
    """按 mtime 增量更新：改过的卡重灌，删掉的卡清行。"""
    cards = qc.card_files(root)
    mtimes = {c: os.path.getmtime(os.path.join(root, c)) for c in cards}
    known = dict(con.execute("SELECT path, mtime FROM cards"))
    changed = [c for c in cards if known.get(c) != mtimes[c]]
    removed = [c for c in known if c not in mtimes]
    with con:
        for path in removed:
            row = con.execute("SELECT id FROM cards WHERE path = ?", (path,)).fetchone()
            if row:
                con.execute("DELETE FROM fts WHERE rowid = ?", (row[0],))
            con.execute("DELETE FROM cards WHERE path = ?", (path,))
        for path in changed:
            display, counters = read_card(root, path)
            raw_tags = display["tags"]
            words = " ".join(" ".join(c.elements()) for c in counters.values())
            con.execute("INSERT OR REPLACE INTO cards "
                        "(path, mtime, title, summary, t_title, t_summary, t_tags, t_headings, tags) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (path, mtimes[path], display["title"], display["summary"],
                         " ".join(counters["title"].elements()),
                         " ".join(counters["summary"].elements()),
                         " ".join(counters["tags"].elements()),
                         " ".join(counters["headings"].elements()),
                         "," + ",".join(sorted(t.strip().lower() for t in
                                               re.findall(r"[^,\[\]]+", raw_tags) if t.strip())) + ","))
            rowid = con.execute("SELECT id FROM cards WHERE path = ?", (path,)).fetchone()[0]
            con.execute("DELETE FROM fts WHERE rowid = ?", (rowid,))
            con.execute("INSERT INTO fts (rowid, body) VALUES (?, ?)", (rowid, words))
    return len(changed) + len(removed)


def search(con, root, query, limit=10, tag=None):
    """召回 = 各 token 命中集的并集；排序 = 字段权重 × IDF × (1+log tf)。

    为什么不用 FTS5 的 bm25 直接排序：它按文档长度归一，长卡（恰恰常是干货最多的卡）
    会被系统性地压下去——实测目标卡在 bm25 里排到一百多名。召回与排序分开后，
    召回只求「不漏」，排序用与定稿一致的公式。
    """
    toks = list(dict.fromkeys(tokens(query)))
    tagged = None
    if tag:
        tagged = {r[0] for r in con.execute(
            "SELECT id FROM cards WHERE tags LIKE ?", (f"%,{tag.strip().lower()},%",))}
        if not toks:                      # 只给标签：列出这个标签下的卡
            rows = con.execute("SELECT path, title, summary FROM cards WHERE id IN ("
                               + ",".join("?" * len(tagged)) + ") ORDER BY path LIMIT ?",
                               (*sorted(tagged), limit)) if tagged else []
            return [(0.0, {"path": p, "title": t, "summary": sm}, []) for p, t, sm in rows]
    if not toks:
        return []
    total = con.execute("SELECT COUNT(*) FROM cards").fetchone()[0] or 1
    idf, postings = {}, {}
    for t in toks:
        rows = con.execute("SELECT rowid FROM fts WHERE fts MATCH ?", (t,)).fetchall()
        postings[t] = {r[0] for r in rows}
        idf[t] = math.log(1 + total / len(rows)) if rows else 0.0
    live = [t for t in toks if idf[t] > 0]
    if not live:
        return []
    cand = set().union(*(postings[t] for t in live))
    if tagged is not None:
        cand &= tagged
    if len(cand) > SHORTLIST:
        # 粗排：命中词的 IDF 之和（不看字段）。保证「命中所有词」的卡进短名单，
        # 再把精排留给字段权重——万卡时这一步把几千个候选压到几百个。
        cheap = {}
        for tok in live:
            for rid in postings[tok]:
                cheap[rid] = cheap.get(rid, 0.0) + idf[tok]
        cand = set(sorted(cheap, key=lambda r: -cheap[r])[:SHORTLIST])
    ids = sorted(cand)
    q = query.strip().lower()
    scored = []
    for chunk in range(0, len(ids), 200):
        part = ids[chunk:chunk + 200]
        rows = con.execute(
            "SELECT id, path, title, summary, t_title, t_summary, t_tags, t_headings "
            "FROM cards WHERE id IN (" + ",".join("?" * len(part)) + ")", part).fetchall()
        for rid, path, title, summary, *fields in rows:
            counts = [Counter((f or "").split()) for f in fields]
            score = 0.0
            # 四个重字段按词频加权；正文不存词频，只记「出现过」（权重最低，足够区隔）
            for (field, weight), counter in zip(
                    ((k, v) for k, v in FIELD_WEIGHT.items() if k != "body"), counts):
                for tok in live:
                    n = counter.get(tok)
                    if n:
                        score += weight * (1 + math.log(n)) * idf[tok]
            for tok in live:
                if rid in postings[tok]:
                    score += FIELD_WEIGHT["body"] * idf[tok]
            if q and q in (title or "").lower():
                score += 6
            elif q and q in (summary or "").lower():
                score += 3
            scored.append((score, {"path": path, "title": title, "summary": summary}, live[:8]))
    scored.sort(key=lambda r: -r[0])
    return scored[:limit]


def main(argv):
    flags, words, root, limit, tag = set(), [], None, 10, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--limit" and i + 1 < len(argv):
            limit = int(argv[i + 1]); i += 2; continue
        if a == "--tag" and i + 1 < len(argv):
            tag = argv[i + 1]; i += 2; continue
        if a.startswith("-"):
            flags.add(a); i += 1; continue
        if root is None and os.path.isdir(os.path.expanduser(a)):
            root = a; i += 1; continue
        words.append(a); i += 1
    root = os.path.expanduser(root or "~/qwiki")
    if not os.path.isdir(root):
        print(f"x 不是目录：{root}")
        return 1

    t0 = time.time()
    con = connect(root, fresh="--rebuild" in flags)
    try:
        changed = sync(con, root)
        elapsed = time.time() - t0
        total = con.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
        db = os.path.join(root, INDEX_NAME)
        size = sum(os.path.getsize(db + s) for s in ("", "-wal", "-shm") if os.path.exists(db + s))

        if "--stats" in flags:
            print(f"qwiki 索引：{root}")
            print(f"  文档 {total} 张 ｜ {size / 1024:.0f} KB ｜ "
                  + (f"本次更新 {changed} 张" if changed else "已是最新")
                  + f"（{elapsed * 1000:.0f} ms）")
            return 0

        query = " ".join(words).strip()
        if not query and not tag:
            print("用法：qwiki-search.py [库根] <关键词...> [--tag 标签] [--limit N] [--json] [--stats] [--rebuild]")
            return 1
        results = search(con, root, query, limit, tag)
        if "--json" in flags:
            print(json.dumps({
                "query": query,
                "rebuilt": bool(changed),
                "ms": round(elapsed * 1000),
                "results": [{"path": info["path"], "title": info["title"],
                             "summary": info["summary"], "score": round(score, 1),
                             "matched": matched}
                            for score, info, matched in results],
            }, ensure_ascii=False, indent=2))
            return 0

        print(f"qwiki 检索：{query}" + (f" ［标签 {tag}］" if tag else "") + f"（{total} 张卡"
              + (f"，更新 {changed} 张索引" if changed else "") + f"，{elapsed * 1000:.0f} ms）\n")
        if not results:
            print("  没有命中。换个说法，或确认这张知识还没入库。")
            return 0
        for n, (score, info, matched) in enumerate(results, 1):
            print(f"  {n}. {info['path']}   [{score:.1f}]")
            print(f"     {info['title']}")
            if info["summary"]:
                print(f"     > {info['summary'][:90]}")
            print(f"     命中：{' '.join(matched[:8])}")
        print("\n下一步：读命中的那张卡；要沿关系走，看它的 `## 相关`。")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
