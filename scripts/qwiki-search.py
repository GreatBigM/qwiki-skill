#!/usr/bin/env python3
"""qwiki 检索 —— 只读 INDEX + `rg` 扫正文，按面过滤、按字段加权排序。

用法:
  python3 qwiki-search.py [知识库根] <关键词...>          # 默认 ~/qwiki，取前 10 条
  python3 qwiki-search.py <库根> <关键词...> --limit 5
  python3 qwiki-search.py <库根> --project <项目>          # 只按面过滤（可不给关键词）
  python3 qwiki-search.py <库根> --module <模块> --type <类型>
  python3 qwiki-search.py <库根> <关键词...> --json        # 机器可读（给 agent 用）
  python3 qwiki-search.py <库根> --stats                   # 规模与依赖现状

数据来源只有两样，都在库里、都可删可重建：
  1. **INDEX.md**（四列：标题 / 总结 / 文件 / 分类）—— 面过滤与标题/结论匹配；
  2. **`rg` 扫正文** —— 关键词不在标题/结论里时的召回。

不需要数据库：当初要它，是为了「全库 df 统计」与「正文倒排」；现在前者由**关键词分级**
（关键词1 宽 / 关键词2 窄，作者已写死）替代，后者由 rg 承担（万卡库几十毫秒）。

排序口径：标题命中 > 结论命中 > 正文命中；同字段内按词频微调。
**检索只做定位**（返回路径 + 一行结论），读卡才是取知识。
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
from collections import Counter

INDEX_NAME = "INDEX.md"
CJK_RUN = re.compile(r"[\u4e00-\u9fff]+|[a-z0-9_]+")
FIELD_WEIGHT = {"title": 6.0, "summary": 5.0, "body": 2.0}


def tokens(text):
    """中文二元组 + 单字；ASCII 词小写。与写卡时的口径一致。"""
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


def load_index(root):
    """解析 INDEX 四列；分类列形如 `<项目>/<模块>/<类型>`（缺失位写作 `-`）。"""
    path = os.path.join(root, INDEX_NAME)
    rows, section = [], None
    for ln, line in enumerate(open(path, encoding="utf-8"), 1):
        m = re.match(r"^##\s+(\S.*?)\s*$", line)
        if m:
            section = m.group(1)
            continue
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in ("标题", "") or set(cells[0]) <= set("-: "):
            continue
        m2 = re.search(r"[^\s|`]+\.md", cells[2])
        if not m2:
            continue
        key = m2.group(0)
        path = key if key.startswith(("personal/", "projects/")) else ("projects/" + key)
        rows.append({"line": ln, "section": section, "title": cells[0], "summary": cells[1],
                     "key": key, "path": path, "facets": cells[3] if len(cells) > 3 else ""})
    return rows


def norm_path(key):
    if key.startswith(("personal/", "projects/")):
        return key
    return ("personal/" + key) if key.startswith("personal") else ("projects/" + key)


def match_facets(row, facets):
    """facets 形如 ['项目/<x>', '模块/<y>']；与分类列逐位比对。"""
    if not facets:
        return True
    parts = (row["facets"] or "-/-/-").split("/")
    parts += ["-"] * (3 - len(parts))
    slot = {"项目": parts[0], "模块": parts[1], "类型": parts[2]}
    for f in facets:
        prefix, _, value = f.partition("/")
        if prefix in slot:
            if slot[prefix] != value:
                return False
        elif value and value not in row["facets"]:
            return False
    return True


def body_hits(root, query):
    """正文召回：rg 优先；没有 rg 就退回 Python 扫（慢但正确）。返回相对路径集合。"""
    terms = [t for t in query.split() if t]
    if not terms:
        return set()
    if shutil.which("rg"):
        cmd = ["rg", "-l", "-i", "-F", "--no-messages", "--glob", "*.md", root]
        for t in terms:
            cmd += ["-e", t]
        out = subprocess.run(cmd, capture_output=True, text=True).stdout
        return {os.path.relpath(p, root) for p in out.splitlines() if p.strip()}
    hits = set()
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ("resource", "scripts", ".git")]
        for f in fn:
            if not f.endswith(".md"):
                continue
            p = os.path.join(dp, f)
            text = open(p, encoding="utf-8", errors="ignore").read().lower()
            if any(t.lower() in text for t in terms):
                hits.add(os.path.relpath(p, root))
    return hits


def score_row(row, q_tokens, phrase, in_body):
    score = 0.0
    for field in ("title", "summary"):
        text = (row[field] or "").lower()
        counter = Counter(tokens(text))
        for tok in q_tokens:
            n = counter.get(tok)
            if n:
                score += FIELD_WEIGHT[field] * (1 + math.log(n))
        if phrase and phrase in text:
            score += FIELD_WEIGHT[field] * 2
    if in_body:
        score += FIELD_WEIGHT["body"]
    return score


def main(argv):
    flags, words, root, limit, facets = set(), [], None, 10, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--limit" and i + 1 < len(argv):
            limit = int(argv[i + 1]); i += 2; continue
        if a in ("--tag", "--project", "--module", "--type") and i + 1 < len(argv):
            value = argv[i + 1]
            prefix = {"--project": "项目", "--module": "模块", "--type": "类型"}.get(a)
            facets.append(value if prefix is None else f"{prefix}/{value}")
            i += 2; continue
        if a.startswith("-"):
            flags.add(a); i += 1; continue
        if root is None and os.path.isdir(os.path.expanduser(a)):
            root = a; i += 1; continue
        words.append(a); i += 1
    root = os.path.expanduser(root or "~/qwiki")
    if not os.path.isdir(root):
        print(f"x 不是目录：{root}")
        return 1
    index_path = os.path.join(root, INDEX_NAME)
    if not os.path.exists(index_path):
        print(f"x 缺 INDEX.md：{index_path}（先跑 qwiki-sync.py --write）")
        return 1

    rows = load_index(root)
    if "--stats" in flags:
        size = os.path.getsize(index_path)
        print(f"qwiki 检索面：{root}")
        print(f"  INDEX {len(rows)} 行 ｜ {size / 1024:.0f} KB ｜ "
              f"正文召回 {'rg' if shutil.which('rg') else 'Python 扫描（无 rg，慢）'}")
        return 0

    query = " ".join(words).strip()
    if not query and not facets:
        print("用法：qwiki-search.py [库根] <关键词...> [--project x] [--module x] [--type x] "
              "[--tag 标签] [--limit N] [--json] [--stats]")
        return 1

    pool = [r for r in rows if match_facets(r, facets)]
    body = body_hits(root, query) if query else set()
    q_tokens = tokens(query)
    phrase = query.lower().strip()
    scored = []
    for r in pool:
        in_body = r["path"] in body or r["key"] in body
        s = score_row(r, q_tokens, phrase, in_body) if query else 0.0
        if query and not s:
            continue
        scored.append((s, r, in_body))
    scored.sort(key=lambda x: -x[0])

    if "--json" in flags:
        print(json.dumps({
            "query": query,
            "facets": facets,
            "results": [{"path": r["path"], "title": r["title"], "summary": r["summary"],
                         "facets": r["facets"], "score": round(s, 1), "body": b}
                        for s, r, b in scored[:limit]],
        }, ensure_ascii=False, indent=2))
        return 0

    print(f"qwiki 检索：{query or '（仅按面过滤）'}"
          + (f" ［{' '.join(facets)}］" if facets else "")
          + f"（INDEX {len(rows)} 行 → 候选 {len(pool)}）\n")
    if not scored:
        print("  没有命中。换个说法，或确认这张知识还没入库。")
        return 0
    for n, (s, r, b) in enumerate(scored[:limit], 1):
        print(f"  {n}. {r['path']}   [{s:.1f}]" + ("  ·正文命中" if b else ""))
        print(f"     {r['title']}")
        if r["summary"]:
            print(f"     > {r['summary'][:90]}")
        if r["facets"] and r["facets"] != "-/-/-":
            print(f"     面：{r['facets']}")
    print("\n下一步：读命中的那张卡；要沿关系走，看它的 `## 相关`。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
