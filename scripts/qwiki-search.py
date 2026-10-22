#!/usr/bin/env python3
"""qwiki 检索 —— 倒排索引，把「整张 INDEX 进上下文」换成「按需取几张卡」。

用法:
  python3 qwiki-search.py [知识库根] <关键词...>          # 默认 ~/qwiki，取前 10 条
  python3 qwiki-search.py <库根> <关键词...> --limit 5    # 自定义条数
  python3 qwiki-search.py <库根> <关键词...> --json       # 机器可读（给 agent 用）
  python3 qwiki-search.py <库根> --stats                  # 索引现状（文档数 / 词数 / 体积）
  python3 qwiki-search.py <库根> <关键词...> --rebuild    # 强制重建索引

索引落在 `<库根>/.qwiki-index.json`（生成物，卡有改动时自动重建，无需手工维护）。
不改变三面模型：INDEX 仍是唯一入口，本脚本只是「按内容找卡」的加速器——
命中之后仍然读卡、仍然沿 `[[...]]` 走。

为什么要有它（规模）：`explore` 靠读 INDEX 的标题+总结做匹配，卡一多就等于把整张表
塞进上下文；倒排索引把成本从「全库」降到「命中的几张卡」。

分词：中文取二元组（单字查询补一元组），ASCII 取词；字段加权（标题 > 结论 > 标签 >
小标题 > 正文），多词命中按覆盖率加成，标题/结论里的原串命中额外加分。
"""
import importlib.util
import json
import math
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

INDEX_NAME = ".qwiki-index.json"
INDEX_VERSION = 1
BODY_TOKEN_CAP = 600          # 每卡正文最多收多少个词（长卡截断，标题/结论全收）

FIELD_WEIGHT = {"title": 6.0, "summary": 5.0, "tags": 3.0, "headings": 2.0, "body": 1.0}
CJK_RUN = re.compile(r"[\u4e00-\u9fff]+|[a-z0-9_+./-]+")


def _load_checker():
    """复用 qwiki-check.py 的解析口径（卡片集 / YAML / 结论行 / 小标题）。"""
    path = Path(__file__).with_name("qwiki-check.py")
    spec = importlib.util.spec_from_file_location("qwiki_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


qc = _load_checker()


def tokens(text):
    """中文二元组 + 单字（查询侧用）；ASCII 词小写。"""
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


def doc_fields(root, rel):
    """一张卡 → 加权字段。标题/结论/标签/小标题全收，正文按词频取前 N。"""
    text = Path(root, rel).read_text(encoding="utf-8")
    fm, body = qc.split(text)
    fields = {
        "title": qc.fm_field(fm, "title"),
        "summary": qc.summary_line(body) or "",
        "tags": " ".join(re.findall(r"\[([^\]]*)\]", qc.fm_field(fm, "tags"))),
        "headings": " ".join(re.findall(r"(?m)^##\s+(.+)$", qc.strip_code(body))),
        "body": body,
    }
    out = {}
    for name, value in fields.items():
        toks = tokens(value)
        if name == "body":
            toks = [t for t, _ in Counter(toks).most_common(BODY_TOKEN_CAP)]
        counter = Counter(toks)
        for tok, cnt in counter.items():
            out[tok] = out.get(tok, 0.0) + FIELD_WEIGHT[name] * (1 + math.log(cnt))
    return out


def build(root):
    cards = qc.card_files(root)
    docs, postings = [], {}
    for i, rel in enumerate(cards):
        text = Path(root, rel).read_text(encoding="utf-8")
        fm, body = qc.split(text)
        docs.append({
            "path": rel,
            "title": qc.fm_field(fm, "title"),
            "summary": qc.summary_line(body) or "",
            "len": len(body),
        })
        for tok, weight in doc_fields(root, rel).items():
            postings.setdefault(tok, {})[str(i)] = round(weight, 3)
    data = {"version": INDEX_VERSION, "built_at": time.time(),
            "docs": docs, "postings": postings}
    path = os.path.join(root, INDEX_NAME)
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    os.replace(path + ".tmp", path)
    return data, os.path.getsize(path)


def newest_card_mtime(root):
    newest = 0.0
    for rel in qc.card_files(root):
        newest = max(newest, os.path.getmtime(os.path.join(root, rel)))
    return newest


def load(root, rebuild=False):
    path = os.path.join(root, INDEX_NAME)
    stale = True
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            stale = data.get("version") != INDEX_VERSION or data.get("built_at", 0) < newest_card_mtime(root)
        except Exception:
            stale = True
    if rebuild or stale or not os.path.exists(path):
        return build(root) + (True,)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh), os.path.getsize(path), False


def search(data, query, limit=10):
    q_tokens = tokens(query)
    if not q_tokens:
        return []
    scores, hits = {}, {}
    total_docs = max(len(data["docs"]), 1)
    for tok in set(q_tokens):
        posting = data["postings"].get(tok, {})
        if not posting:
            continue
        idf = math.log(1 + total_docs / len(posting))   # 高频词（“为什么”“什么”）自动降权
        for doc, weight in posting.items():
            scores[doc] = scores.get(doc, 0.0) + weight * idf
            hits.setdefault(doc, []).append((tok, weight * idf))
    q = query.strip().lower()
    results = []
    for doc, base in scores.items():
        info = data["docs"][int(doc)]
        coverage = len(hits[doc]) / len(set(q_tokens))
        score = base * (1 + 0.8 * coverage)
        title, summary = (info["title"] or "").lower(), (info["summary"] or "").lower()
        if q and q in title:
            score += 12
        elif q and q in summary:
            score += 7
        matched = [tok for tok, _ in sorted(hits[doc], key=lambda x: -x[1])]
        results.append((score, info, matched))
    results.sort(key=lambda r: -r[0])
    return results[:limit]


def main(argv):
    flags, words, root, limit = set(), [], None, 10
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--limit" and i + 1 < len(argv):
            limit = int(argv[i + 1]); i += 2; continue
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
    data, size, rebuilt = load(root, rebuild="--rebuild" in flags)
    elapsed = time.time() - t0

    if "--stats" in flags:
        print(f"qwiki 索引：{root}")
        print(f"  文档 {len(data['docs'])} 张 ｜ 词条 {len(data['postings'])} 个 ｜ "
              f"{size / 1024:.0f} KB ｜ {'本次重建' if rebuilt else '命中缓存'}（{elapsed * 1000:.0f} ms）")
        return 0

    query = " ".join(words).strip()
    if not query:
        print("用法：qwiki-search.py [库根] <关键词...> [--limit N] [--json] [--stats] [--rebuild]")
        return 1
    results = search(data, query, limit)
    if "--json" in flags:
        print(json.dumps({
            "query": query,
            "rebuilt": rebuilt,
            "ms": round(elapsed * 1000),
            "results": [{"path": info["path"], "title": info["title"],
                         "summary": info["summary"], "score": round(score, 1),
                         "matched": matched}
                        for score, info, matched in results],
        }, ensure_ascii=False, indent=2))
        return 0

    print(f"qwiki 检索：{query}（{len(data['docs'])} 张卡"
          + ("，索引已更新" if rebuilt else "") + f"，{elapsed * 1000:.0f} ms）\n")
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


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
