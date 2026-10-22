#!/usr/bin/env python3
"""qwiki 投影同步 —— 把 INDEX 从「手写副本」变成卡片集的派生物。

用法:  python3 qwiki-sync.py [知识库根目录]           # 预览（只读，什么都不改）
       python3 qwiki-sync.py [知识库根目录] --write  # 落盘
       python3 qwiki-sync.py [知识库根目录] --write --strict  # 需人判 > 0 时退出码 2

为什么有这个脚本（SCHEMA §INDEX 登记规则）：
  INDEX 是卡片集的正投影，「正投影」由人维护必然漂移——改一张卡要同步 INDEX
  两列，230 张卡的规模下漏一行是必然而非意外。本脚本把投影这一侧变成生成物：
  人只写卡，INDEX 由卡片推出来。

投影口径（v2.14.0 起，两处同串而不是三处）：
  - 标题列 ← 卡片 YAML `title`
  - 总结列 ← 正文 `>` 引文块的**首行**（一句话结论，≤80 字符）
  - 文件列 ← canonical key（省略 `projects/` 前缀）
  - YAML `summary`（可多行的长摘要）**不参与投影**：它与 `>` 首行是两种用途，
    不要求逐字相同——此前「三处同串」对按实际习惯写成的二十多张卡全是误报。

不修（要人判，只报告）：
  - `>` 首行超过 80 字符（压句子不能机断）
  - 卡片没有 `>` 引文块，或首行是出处/状态（结论要人写）
  - 标题/总结含 `|`（会撑破表格；改写后再同步）
  - INDEX 行指向不存在的文件（改名残留，删不删由人定）

只读自检仍在 qwiki-check.py；本脚本复用它的解析函数，避免口径两处实现。

`--strict`：把「需人判」升级成非零退出码（2）——CI 与批处理里，打印了却 exit 0 等于没报。
"""
import importlib.util
import os
import re
import sys
from pathlib import Path


def _load_checker():
    """复用 qwiki-check.py 的解析口径。"""
    path = Path(__file__).with_name("qwiki-check.py")
    spec = importlib.util.spec_from_file_location("qwiki_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


qc = _load_checker()
MAX_SUMMARY = qc.MAX_SUMMARY


def row_line(title, summary, key, facets=""):
    return f"| {title} | {summary} | {key} | {facets} |"


def facets_of(fm):
    """卡片 tags → INDEX 的分类列（项目/模块/类型）。三面缺一就留空位，不猜。"""
    tags = _tags(fm)
    proj = next((t.split("/", 1)[1] for t in tags if t.startswith("项目/")), "")
    mod = next((t.split("/", 1)[1] for t in tags if t.startswith("模块/")), "")
    typ = next((t.split("/", 1)[1] for t in tags if t.startswith("类型/")), "")
    return "/".join([proj or "-", mod or "-", typ or "-"])


def _tags(fm):
    raw = qc.fm_field(fm, "tags")
    inner = qc.re.search(r"\[(.*?)\]", raw or "")
    return [t.strip() for t in (inner.group(1) if inner else "").split(",") if t.strip()]


def canonical_key(rel):
    return rel[len("projects/"):] if rel.startswith("projects/") else rel





def is_table_row(line):
    return line.startswith("|") and ".md" in line and not set(line.strip()) <= set("|-: ")


def main(argv):
    root = os.path.expanduser(next((a for a in argv if not a.startswith("-")), "~/qwiki"))
    write = "--write" in argv
    strict = "--strict" in argv
    if not os.path.isdir(root):
        print(f"x 不是目录: {root}")
        return 1

    cards = qc.card_files(root)
    pd = os.path.join(root, "projects")
    projects = {d for d in os.listdir(pd) if os.path.isdir(os.path.join(pd, d))} if os.path.isdir(pd) else set()

    ident, manual, unsafe = {}, [], set()
    for rel in cards:
        fm, body = qc.split(open(os.path.join(root, rel), encoding="utf-8").read())
        title, summary = qc.fm_field(fm, "title"), qc.summary_line(body)
        if not title:
            manual.append(f"{rel}: YAML 缺 `title`，标题列无法生成")
        if not summary:
            manual.append(f"{rel}: 没有 `>` 引文块，总结列无法生成")
        elif len(summary) > MAX_SUMMARY:
            manual.append(f"{rel}: `>` 首行 {len(summary)} 字符（>{MAX_SUMMARY}），需人压句")
        elif qc.PROV_RE.match(summary):
            manual.append(f"{rel}: `>` 首行是出处/状态（不是结论），先把一句话结论写到首行")
        if "|" in (title or "") or "|" in (summary or ""):
            unsafe.add(rel)
            manual.append(f"{rel}: title/总结含 `|`，会撑破表格；改写后再同步")
        ident[rel] = (title, summary or "", facets_of(fm))

    index_path = os.path.join(root, "INDEX.md")
    if not os.path.exists(index_path):
        print(f"x 缺 INDEX.md: {index_path}")
        return 1
    lines = open(index_path, encoding="utf-8").read().split("\n")
    out, seen, stat = [], set(), {"title": 0, "summary": 0, "path": 0}
    dropped, dead = [], []

    for line in lines:
        if not is_table_row(line):
            out.append(line)
            continue
        cells = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            out.append(line)
            continue
        title, summary, path = cells[0], cells[1], cells[2]
        m = re.search(r"[^\s|`]+\.md", path)
        rel = qc.resolve(root, m.group(0)) if m else None
        if rel is None or rel not in ident:
            dead.append(f"INDEX 行未匹配到卡片（保留原样）：{path[:60]}")
            out.append(line)
            continue
        if rel in seen:
            dropped.append(f"重复行删除：{canonical_key(rel)}")
            continue
        seen.add(rel)
        if rel in unsafe:
            out.append(line)
            continue
        new_title, new_summary, new_facets = ident[rel]
        new_title = new_title or title
        if not new_summary or qc.PROV_RE.match(new_summary):
            new_summary = summary
        new_key = canonical_key(rel)
        stat["title"] += title != new_title
        stat["summary"] += summary != new_summary
        stat["path"] += (m.group(0) if m else path) != new_key
        out.append(row_line(new_title, new_summary, new_key, new_facets))

    added = []
    for rel in cards:
        if rel in seen:
            continue
        section = qc.section_of(rel, projects)
        title, summary, _ = ident[rel]
        if rel in unsafe or (summary and qc.PROV_RE.match(summary)):
            manual.append(f"{rel}: 有卡但 INDEX 无登记行；总结不可用（含 `|` 或首行是出处），未自动补")
            continue
        if not section or not title or not summary:
            manual.append(f"{rel}: 有卡但 INDEX 无登记行，且无法自动补（段头/标题/摘要缺失）")
            continue
        head = f"## {section}"
        start = next((i for i, l in enumerate(out) if l.rstrip() == head), None)
        if start is None:
            manual.append(f"{rel}: 有卡但 INDEX 无 `{head}` 段，无法插入")
            continue
        end = next((i for i in range(start + 1, len(out)) if out[i].startswith("## ")), len(out))
        row = row_line(title, summary, canonical_key(rel), ident[rel][2])
        rows = [i for i in range(start + 1, end) if is_table_row(out[i])]
        sep = next((i for i in range(start + 1, end) if out[i].startswith("|---")), None)
        if rows:
            out.insert(rows[-1] + 1, row)
        elif sep is not None:
            out.insert(sep + 1, row)
        else:
            out[start + 1:start + 1] = ["", "| 标题 | 总结 | 文件 | 分类 |",
                                        "|------|------|------|------|", row]
        added.append(f"补登记：{canonical_key(rel)} → ## {section}")

    # 旧三列表 → 四列（表头 / 分隔行 / 数据行一起补，避免一张表两种形状）
    fixed = []
    for ln in out:
        pipes = ln.count("|")
        if ln.startswith("|") and "标题" in ln and pipes == 4:
            ln = "| 标题 | 总结 | 文件 | 分类 |"
        elif ln.startswith("|") and set(ln.strip()) <= set("|-: ") and pipes == 4:
            ln = "|------|------|------|------|"
        elif ln.startswith("|") and ".md" in ln and pipes == 4:
            ln = ln.rstrip().rstrip("|").rstrip() + " | - |"
        fixed.append(ln)
    out = fixed

    print(f"qwiki 投影同步：{root}")
    print(f"  卡片 {len(cards)} 张 ｜ INDEX {len(qc.index_rows(root))} 行 ｜ "
          f"模式 {'写入' if write else '预览（加 --write 落盘）'}\n")
    print(f"  标题列修正 {stat['title']} ｜ 总结列修正 {stat['summary']} ｜ 文件列归一 {stat['path']}")
    print(f"  补登记 {len(added)} ｜ 重复行删除 {len(dropped)} ｜ 需人判 {len(manual)}")
    for group in (added, dropped, dead, manual):
        for item in group:
            print(f"      · {item}")

    if not write:
        print("\n预览模式，未改任何文件。")
    else:
        tmp = index_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write("\n".join(out))
        os.replace(tmp, index_path)
        print("\n✅ 已写入 INDEX.md")
    if strict and manual:
        print(f"✗ --strict：{len(manual)} 项需人判 → 退出码 2")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
