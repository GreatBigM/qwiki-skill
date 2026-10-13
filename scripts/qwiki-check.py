#!/usr/bin/env python3
"""qwiki 一致性自检 —— 把 SCHEMA / SKILL 的约定变成可执行断言。

用法:  python3 qwiki-check.py [知识库根目录]        # 默认 ~/qwiki
       python3 qwiki-check.py ~/qwiki --quiet      # 只打失败项与汇总
退出码: 0 = 全过；1 = 有失败项（可直接串进 hook / CI）

设计取舍：
- **只读**，不改任何文件；发现的问题由 AI 按 SKILL §sync 处置。
- **不依赖 PyYAML**（除「YAML 可解析」一项，缺库时该项跳过并标注）——
  自检工具本身不该因为别人的环境少个包就跑不起来。
- 判定口径全部来自 SCHEMA：卡片集 = `personal/*.md` + `projects/<项目>/**/*.md`，
  排除 `resource/`（素材）、`scripts/`、`spec.md`。
"""
import os
import re
import sys

SKIP_DIRS = {"resource", "scripts", ".git"}
SKIP_FILES = {"spec.md"}
H1_RE = re.compile(r"^# (.+)$", re.M)
FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
LINK_RE = re.compile(r"\[\[([^\]|\n]+?)(?:\|[^\]\n]*)?\]\]")
CODE_RE = re.compile(r"```.*?```", re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


# ── 基础：收集与解析 ────────────────────────────────────────────────

def card_files(root):
    """卡片集（不含 note 的话也一并算——note 是随笔卡，同属卡片）。"""
    out = []
    for base in ("personal", "projects"):
        for dp, dn, fn in os.walk(os.path.join(root, base)):
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            out += [
                os.path.relpath(os.path.join(dp, f), root)
                for f in fn
                if f.endswith(".md") and f not in SKIP_FILES
            ]
    return sorted(out)


def split(text):
    """→ (frontmatter 原文, 正文)。无头则 (None, 全文)。"""
    m = FM_RE.match(text)
    return (m.group(1), text[m.end():]) if m else (None, text)


def fm_field(fm, key):
    """从头里取一个标量（不引 PyYAML；只用于 title/summary 这类单行值）。"""
    m = re.search(r"(?m)^" + key + r":\s*(.*)$", fm or "")
    if not m:
        return ""
    v = m.group(1).strip()
    if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return v


def summary_line(body):
    """H1 之后第一个非空块的首个 `>` 行（去掉 `>` 与空白）。"""
    lines = body.split("\n")
    i = next((k for k, l in enumerate(lines) if l.startswith("# ")), None)
    if i is None:
        return None
    k = i + 1
    while k < len(lines) and not lines[k].strip():
        k += 1
    if k >= len(lines) or not lines[k].startswith(">"):
        return None
    return lines[k].lstrip(">").strip()


def strip_code(t):
    return INLINE_CODE_RE.sub("", CODE_RE.sub("", t))


# ── INDEX 解析 ────────────────────────────────────────────────────

def index_rows(root):
    """→ [{line, title, summary, path, key}]，key = 去 `projects/` 前缀的路径。"""
    rows = []
    path = os.path.join(root, "INDEX.md")
    if not os.path.exists(path):
        return rows
    for ln, line in enumerate(open(path, encoding="utf-8"), 1):
        if not line.startswith("|"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 3 or c[0] in ("标题", "") or set(c[0]) <= set("-: "):
            continue
        m = re.search(r"[^\s|`]+\.md", c[2])
        if not m:
            continue
        key = m.group(0)
        rows.append({"line": ln, "title": c[0], "summary": c[1], "path": c[2], "key": key})
    return rows


def resolve(root, key):
    """INDEX 的「文件」列 → 知识库内的真实相对路径。"""
    for cand in (key, "projects/" + key):
        if os.path.exists(os.path.join(root, cand)):
            return cand
    return None


# ── 各项检查：每项返回 (名称, 通过?, [失败描述]) ─────────────────────

def check_card_headers(root, cards, rows):
    """H1 在正文首位；H1 后第一个非空块是 `>` 行；有 `> 依据` / `> 状态`。"""
    bad = []
    for rel in cards:
        fm, body = split(open(os.path.join(root, rel), encoding="utf-8").read())
        lines = body.split("\n")
        k = next((i for i, l in enumerate(lines) if l.strip()), None)
        if k is None or not lines[k].startswith("# "):
            bad.append(f"{rel}: H1 不在正文首位（前面还有内容）")
            continue
        if summary_line(body) is None:
            bad.append(f"{rel}: H1 后第一个非空块不是 `>` 引言行")
        if not re.search(r"(?m)^>\s*\**\s*(依据|状态)", body):
            bad.append(f"{rel}: 缺 `> 依据`（覆盖型）或 `> 状态`（追加型）")
    return "卡片头部（H1 首位 / `>` 引言行 / 依据·状态）", not bad, bad


def check_index_projection(root, cards, rows):
    """INDEX 两列 = 卡片集的正投影；一卡一行。"""
    bad, seen = [], set()
    for r in rows:
        rel = resolve(root, r["key"])
        if rel is None:
            bad.append(f"INDEX:{r['line']} 文件列指向不存在的文件（{r['key']}）")
            continue
        if rel in seen:
            bad.append(f"INDEX:{r['line']} 「{os.path.basename(rel)}」占了多行（一卡一行）")
        seen.add(rel)
        fm, body = split(open(os.path.join(root, rel), encoding="utf-8").read())
        t, s = fm_field(fm, "title"), summary_line(body)
        if t and r["title"] != t:
            bad.append(f"INDEX:{r['line']} 标题列 ≠ 卡片 title\n      INDEX: {r['title'][:60]}\n      title: {t[:60]}")
        if s and r["summary"] != s:
            bad.append(f"INDEX:{r['line']} 总结列 ≠ 卡片 `>` 行\n      INDEX: {r['summary'][:60]}\n      `>`  : {s[:60]}")
    missing = [c for c in cards if c not in seen]
    bad += [f"{c}: 有卡但 INDEX 无登记行" for c in missing]
    return "INDEX 正投影（标题列 / 总结列 / 一卡一行 / 无漏登记）", not bad, bad


def check_index_clean(root, cards, rows):
    """INDEX 只登记卡片；无死链；总结列长度。"""
    bad = []
    for r in rows:
        seg = [x for x in r["key"].split("/") if x]
        if any(x in SKIP_DIRS - {".git"} for x in seg):
            bad.append(f"INDEX:{r['line']} 素材/脚本误登本表（{r['key']}）")
        if resolve(root, r["key"]) is None:
            bad.append(f"INDEX:{r['line']} 死链（{r['key']}）")
        if r["summary"].startswith(("#", "|", "!")) or len(r["summary"]) > 80:
            bad.append(f"INDEX:{r['line']} 总结列异常（{len(r['summary'])} 字符，应以摘要开头且 ≤80）")
    return "INDEX 纯度（只登记卡片 / 无死链 / 摘要长度）", not bad, bad


def check_links(root, cards, rows):
    """卡片 `[[...]]` 必须解析到另一张卡（素材不参与卡片图）。"""
    slugs = {os.path.splitext(os.path.basename(c))[0] for c in cards}
    bad = []
    for rel in cards:
        t = strip_code(open(os.path.join(root, rel), encoding="utf-8").read())
        for m in LINK_RE.finditer(t):
            tgt = m.group(1).strip().split("/")[-1]
            if tgt not in slugs:
                bad.append(f"{rel} → [[{m.group(1).strip()}]] 不是卡片")
    return "双链只连卡片（死链 / 指素材）", not bad, bad


def check_material_paths(root, cards, rows):
    """卡片里引用的素材路径必须真实存在，且不用旧目录名。

    只认「首段是真实项目名」的路径——代码仓也有 `0_workbench/change/…`、
    `text/data/…` 这类同名段，不加这条会报一堆假阳性。
    """
    projects = {d for d in os.listdir(os.path.join(root, "projects"))
                if os.path.isdir(os.path.join(root, "projects", d))}
    bad = []
    for rel in cards:
        t = open(os.path.join(root, rel), encoding="utf-8").read()
        for m in re.finditer(r"`([a-z0-9_]+/resource/[^`]+)`", t):
            if not os.path.exists(os.path.join(root, "projects", m.group(1))):
                bad.append(f"{rel}: 素材路径不存在 `{m.group(1)}`")
        for m in re.finditer(r"`([a-z0-9_]+)/(references|design|archive|change|data)/([^`]+)`", t):
            if m.group(1) not in projects:
                continue  # 代码仓路径（0_workbench/… 等），不是 qwiki 素材
            bad.append(f"{rel}: 旧目录名 `{m.group(0)}`（应 {m.group(1)}/resource/）")
    return "卡片引用的素材路径", not bad, bad


def check_naming(root, cards, rows):
    """SCHEMA §命名约定：全小写连字符；日期一律前缀。"""
    bad = []
    for rel in cards:
        n = os.path.basename(rel)[:-3]
        if "_" in n:
            bad.append(f"{rel}: 文件名含下划线")
        if re.search(r"[A-Z]", n):
            bad.append(f"{rel}: 文件名含大写")
        if " " in n:
            bad.append(f"{rel}: 文件名含空格")
        if re.search(r"-\d{8}$", n) and not re.match(r"^\d{8}-", n):
            bad.append(f"{rel}: 日期是后缀（应前缀 <YYYYMMDD>-）")
    return "命名约定（字符集 / 日期位置）", not bad, bad


def check_track_ownership(root, cards, rows):
    """每张轨迹卡（§A~§E 裁决账）的入链里至少 1 张模块卡。"""
    modules, tracks, inbound = set(), [], {}
    for rel in cards:
        body = split(open(os.path.join(root, rel), encoding="utf-8").read())[1]
        slug = os.path.splitext(os.path.basename(rel))[0]
        if re.search(r"(?m)^##\s*.*(模块边界|职责描述)", body):
            modules.add(slug)
        if re.search(r"(?m)^##\s*[A-E]\.", body) and re.search(r"(?m)^##\s*[F-H]\.", body):
            tracks.append(slug)
    for rel in cards:
        t = strip_code(open(os.path.join(root, rel), encoding="utf-8").read())
        for m in LINK_RE.finditer(t):
            inbound.setdefault(m.group(1).strip().split("/")[-1], set()).add(
                os.path.splitext(os.path.basename(rel))[0]
            )
    bad = [f"轨迹卡 [[{t}]] 的入链里没有模块卡 —— 这条线缺一张模块卡"
           for t in tracks if not (inbound.get(t, set()) & modules)]
    return f"轨迹卡归属（{len(tracks)} 张）", not bad, bad


def check_material_no_header(root, cards, rows):
    """素材与脚本不得带 YAML 头 —— 不变量「有头 ⇔ 是卡片」（SCHEMA §YAML 头公约 v2.10.0）。"""
    bad = []
    for base in ("personal", "projects"):
        for dp, dn, fn in os.walk(os.path.join(root, base)):
            dn[:] = [d for d in dn if d != ".git"]
            if not ({"resource", "scripts"} & set(dp.split(os.sep))):
                continue
            for f in fn:
                if not f.endswith(".md"):
                    continue
                if split(open(os.path.join(dp, f), encoding="utf-8").read())[0] is not None:
                    bad.append(f"{os.path.relpath(os.path.join(dp, f), root)}: 素材/脚本带 YAML 头"
                               "（有头 ⇔ 卡片：删头，或升格为卡）")
    return "素材/脚本不得带头", not bad, bad


def check_yaml(root, cards, rows):
    """YAML 头可解析（需 PyYAML；缺库则跳过）。"""
    try:
        import yaml
    except ImportError:
        return "YAML 头可解析", True, ["（跳过：本机无 PyYAML）"]
    bad = []
    n = 0
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d != ".git"]
        for f in fn:
            if not f.endswith(".md"):
                continue
            fm, _ = split(open(os.path.join(dp, f), encoding="utf-8").read())
            if fm is None:
                continue
            n += 1
            try:
                yaml.safe_load(fm)
            except Exception as e:
                bad.append(f"{os.path.relpath(os.path.join(dp, f), root)}: {str(e)[:60]}")
    return f"YAML 头可解析（{n} 个带头文件）", not bad, bad


CHECKS = [
    check_card_headers,
    check_index_projection,
    check_index_clean,
    check_links,
    check_material_paths,
    check_naming,
    check_track_ownership,
    check_material_no_header,
    check_yaml,
]


def main(argv):
    root = os.path.expanduser(argv[0]) if argv and not argv[0].startswith("-") else os.path.expanduser("~/qwiki")
    quiet = "--quiet" in argv or "-q" in argv
    if not os.path.isdir(root):
        print(f"✗ 不是目录：{root}")
        return 1
    cards, rows = card_files(root), index_rows(root)
    print(f"qwiki 自检：{root}")
    print(f"  卡片 {len(cards)} 张 ｜ INDEX {len(rows)} 行\n")
    failed = 0
    for fn in CHECKS:
        name, ok, detail = fn(root, cards, rows)
        print(f"  {'✓' if ok else '✗'} {name}")
        if not ok:
            for d in detail[:20]:
                print(f"      {d}")
            if len(detail) > 20:
                print(f"      … 另 {len(detail) - 20} 条")
        if not ok:
            failed += 1
    print()
    print("全部通过" if not failed else f"{failed} 项未通过 —— 按 SKILL §sync 处置")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
