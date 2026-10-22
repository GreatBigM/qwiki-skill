#!/usr/bin/env python3
"""qwiki 一致性自检 —— 把 SCHEMA / SKILL 的约定变成可执行断言。

用法:  python3 qwiki-check.py [知识库根目录]        # 默认 ~/qwiki，体检（只读）
       python3 qwiki-check.py ~/qwiki --quiet      # 只打两栏结论
       python3 qwiki-check.py ~/qwiki --all        # 明细打全量（默认截断）
       python3 qwiki-check.py ~/qwiki --baseline   # 把当前规格项存进账本（唯一写模式）
       python3 qwiki-check.py ~/qwiki --strict     # 新增规格项也返回非零（默认不管）

退出码：0 = 可用（规格项不影响）；1 = INDEX 入口坏了（知识「找不到」）；
        2 = 仅 --strict 时的规格新增项。**规格式样不参与默认退出码**——
        知识库的核心是「找得到」，不是「排版整齐」。

设计取舍：
- **只读**，不改任何文件；发现的问题由 AI 按 SKILL §sync 处置。
- **不依赖 PyYAML**（除「YAML 可解析」一项，缺库时该项跳过并标注）——
  自检工具本身不该因为别人的环境少个包就跑不起来。
- 判定口径全部来自 SCHEMA：卡片集 = `personal/*.md` + `projects/<项目>/**/*.md`，
  排除 `resource/`（素材）、`scripts/`（根层 .md 一律视为卡片——2026-10-13 起无例外）。
"""
import datetime
import json
import os
import re
import sys

SKIP_DIRS = {"resource", "scripts", ".git"}
MAX_SUMMARY = 80          # 与 SKILL/SCHEMA 的「≤80」同源；qwiki-sync 复用，不另写一份
PROV_RE = re.compile(r"^(?:\*\*)?(?:来源|依据|状态|口径)\*{0,2}\s*[:：]|^来源\s+change|^change\s|^`change")  # 首行是出处/状态，不是结论
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
                if f.endswith(".md")
            ]
    return sorted(out)


def split(text):
    """→ (frontmatter 原文, 正文)。无头则 (None, 全文)。"""
    m = FM_RE.match(text)
    return (m.group(1), text[m.end():]) if m else (None, text)


def fm_fields(fm):
    """极简 YAML 头解析（不引 PyYAML）：标量、引号、块标量（`>-` / `|`）。

    只求取出 title / summary 这类文本值，不做 YAML 全语义——真正的「可解析」
    断言在 check_yaml（那一项才按需用 PyYAML）。块标量支持是 2026-10-22 补的：
    此前 `summary: >-` 会被读成字符串 `>-`，让「三处同串」对二十来张卡全部误报。
    """
    data, lines, i = {}, (fm or "").split("\n"), 0
    while i < len(lines):
        m = re.match(r"^([A-Za-z_][\w-]*):(?:\s*(.*))?$", lines[i])
        if not m:
            i += 1
            continue
        key, val = m.group(1), (m.group(2) or "").strip()
        if val in (">", ">-", ">+", "|", "|-", "|+"):
            i += 1
            buf = []
            while i < len(lines) and (not lines[i].strip() or lines[i].startswith(("  ", "\t"))):
                buf.append(lines[i].strip())
                i += 1
            data[key] = ("" if val.startswith(">") else "\n").join(buf).strip()
            continue
        if len(val) > 1 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        data[key] = val
        i += 1
    return data


def fm_field(fm, key):
    """从头里取一个文本值（支持块标量）。"""
    return fm_fields(fm).get(key, "")


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
    """→ [{line, section, title, summary, path, key}]，key = 去 `projects/` 前缀的路径。"""
    rows = []
    path = os.path.join(root, "INDEX.md")
    if not os.path.exists(path):
        return rows
    section = None
    for ln, line in enumerate(open(path, encoding="utf-8"), 1):
        m_sec = re.match(r"^##\s+(\S.*?)\s*$", line)
        if m_sec:
            section = m_sec.group(1)
            continue
        if not line.startswith("|"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 3 or c[0] in ("标题", "") or set(c[0]) <= set("-: "):
            continue
        m = re.search(r"[^\s|`]+\.md", c[2])
        if not m:
            continue
        key = m.group(0)
        rows.append({"line": ln, "section": section, "title": c[0], "summary": c[1],
                     "path": c[2], "key": key,
                     "facets": c[3] if len(c) > 3 else ""})
    return rows


def resolve(root, key):
    """INDEX 的「文件」列 → 知识库内的真实相对路径。

    文件列规范：`<项目>/<slug>.md` / `personal/<slug>.md` / `common/<slug>.md`
    （**不写 `projects/` 前缀**）——前缀式由调用方单列断言报错，这里先归一（只按 canonical key 映射）。
    """
    if key.startswith("projects/"):
        key = key[len("projects/"):]
    for cand in (key, "projects/" + key):
        if os.path.exists(os.path.join(root, cand)):
            return cand
    return None


def section_of(rel, projects):
    """卡片路径 → INDEX 段名（personal / common / <项目>）；推不出返回 None。"""
    if rel.startswith("personal/"):
        return "personal"
    if rel.startswith("projects/common/"):
        return "common"
    parts = rel.split("/")
    if len(parts) > 2 and parts[0] == "projects" and parts[1] in projects:
        return parts[1]
    return None


# ── 各项检查：每项返回 (名称, 通过?, [失败描述]) ─────────────────────

def check_card_headers(root, cards, rows):
    """H1 在正文首位；H1 = title；H1 后首个 `>` 行是结论；有 `> 依据/状态/来源/change/口径`。"""
    bad = []
    for rel in cards:
        fm, body = split(open(os.path.join(root, rel), encoding="utf-8").read())
        if fm is None:
            bad.append(f"{rel}: 无 YAML 头（不变量「有头 ⇔ 是卡片」：补头，或移位到 resource/）")
            continue
        lines = body.split("\n")
        k = next((i for i, l in enumerate(lines) if l.strip()), None)
        if k is None or not lines[k].startswith("# "):
            bad.append(f"{rel}: H1 不在正文首位（前面还有内容）")
            continue
        title = fm_field(fm, "title").strip()
        h1 = lines[k][2:].strip()
        if title and h1 != title:
            bad.append(f"{rel}: 正文 H1 ≠ YAML title（H1「{h1[:40]}」/ title「{title[:40]}」）")
        first = summary_line(body)
        if first is None:
            bad.append(f"{rel}: H1 后第一个非空块不是 `>` 引言行")
        elif PROV_RE.match(first):
            bad.append(f"{rel}: H1 后首行是出处/状态（{first[:24]}…），一句话结论应在前；出处另起 `>` 段")
        if not re.search(r"(?m)^>\s*\**\s*(依据|状态|来源|change|口径)", body):
            bad.append(f"{rel}: 缺 `> 依据`（或 来源/change/口径）与 `> 状态` 之一，卡头无法自证")
        for m in re.finditer(r"(?m)^##\s*(关联|参考|参见|相关链接|互链)\s*$", body):
            bad.append(f"{rel}: 相关段标题须为 `## 相关`（现为 {m.group(0).strip()}）")
    return "卡片头部（H1/title 同串 / `>` 结论行 / 依据·状态）", not bad, bad


def check_index_entries(root, cards, rows):
    """INDEX 入口（硬）：每行指向真实存在的卡、一卡一行、段头与路径一致、不漏登记。

    这一层坏了 = 「INDEX 说有 / 没有」与事实不符，检索会给出空结果或根本找不到。
    其余问题（标题写旧了、总结超长）不影响目录可用，归「规格」。
    """
    bad, seen = [], set()
    pd = os.path.join(root, "projects")
    projects = {d for d in os.listdir(pd) if os.path.isdir(os.path.join(pd, d))} if os.path.isdir(pd) else set()
    for r in rows:
        rel = resolve(root, r["key"])
        if rel is None:
            bad.append(f"INDEX:{r['line']} 死链：文件列指向不存在的文件（{r['key']}）")
            continue
        if rel in seen:
            bad.append(f"INDEX:{r['line']} 「{os.path.basename(rel)}」占了多行（一卡一行）")
        seen.add(rel)
        want = section_of(rel, projects)
        if want and r.get("section") and want != r["section"]:
            bad.append(f"INDEX:{r['line']} 段头 `## {r['section']}` 与卡片路径不符（应在 `## {want}`）")
    missing = [c for c in cards if c not in seen]
    bad += [f"{c}: 有卡但 INDEX 无登记行" for c in missing]
    return "INDEX 入口（死链 / 一卡一行 / 段头 / 漏登记）", not bad, bad


def check_index_table(root, cards, rows):
    """INDEX 结构（硬）：段头合法、表头与分隔行完整、不混入素材行。"""
    bad = []
    for r in rows:
        seg = [x for x in r["key"].split("/") if x]
        if any(x in SKIP_DIRS - {".git"} for x in seg):
            bad.append(f"INDEX:{r['line']} 素材/脚本误登本表（{r['key']}）")
    # 段头须属 {## personal, ## common, ## <projects 实际目录名>}（SCHEMA §INDEX 登记规则）
    pd = os.path.join(root, "projects")
    allowed = {"personal", "common"} | (
        {d for d in os.listdir(pd) if os.path.isdir(os.path.join(pd, d))} if os.path.isdir(pd) else set())
    idx = os.path.join(root, "INDEX.md")
    if os.path.exists(idx):
        for ln, line in enumerate(open(idx, encoding="utf-8"), 1):
            m = re.match(r"^##\s+(\S.*?)\s*$", line)
            if m and m.group(1) not in allowed:
                bad.append(f"INDEX:{ln} 段头 `## {m.group(1)}` 不在 {{personal / common / <项目目录名>}} 之列")
    # 表体完整性：每张表必须以「表头 + 分隔行」开头，数据行后不得再出现分隔行
    if os.path.exists(idx):
        tbl = []
        for ln, line in enumerate(open(idx, encoding="utf-8").read().split("\n") + [""], 1):
            if line.startswith("|"):
                tbl.append((ln, line))
                continue
            if tbl:
                first = tbl[0][1]
                if len(tbl) < 2:
                    bad.append(f"INDEX:{tbl[0][0]} 表只有一行，缺分隔行")
                else:
                    if ".md" in first:
                        bad.append(f"INDEX:{tbl[0][0]} 表体缺表头（首行就是数据行）")
                    if not set(tbl[1][1].strip()) <= set("|-: "):
                        bad.append(f"INDEX:{tbl[1][0]} 表头后不是分隔行")
                for ln2, l2 in tbl[2:]:
                    if set(l2.strip()) <= set("|-: "):
                        bad.append(f"INDEX:{ln2} 分隔行出现在数据行之后")
                tbl = []
    return "INDEX 结构（段头合法 / 表体完整 / 不混素材）", not bad, bad


def check_index_projection(root, cards, rows):
    """INDEX 投影（软）：标题列 = title、总结列 = `>` 首行、总结列不空不超长。

    投影漂移不影响「找得到」，只影响「显示得准」；`qwiki-sync.py --write` 一条命令就修。
    """
    bad = []
    for r in rows:
        rel = resolve(root, r["key"])
        if rel is None:
            continue  # 死链由「INDEX 入口」报，不重复计
        if r["key"].startswith("projects/"):
            bad.append(f"INDEX:{r['line']} 文件列带 `projects/` 前缀（应写 `<项目>/<slug>.md`，省略前缀）")
        fm, body = split(open(os.path.join(root, rel), encoding="utf-8").read())
        t, s = fm_field(fm, "title"), summary_line(body)
        if t and r["title"] != t:
            bad.append(f"INDEX:{r['line']} 标题列 ≠ 卡片 title\n      INDEX: {r['title'][:60]}\n      title: {t[:60]}")
        if not r["summary"]:
            bad.append(f"INDEX:{r['line']} 总结列为空")
        elif s and r["summary"] != s:
            bad.append(f"INDEX:{r['line']} 总结列 ≠ 卡片 `>` 行\n      INDEX: {r['summary'][:60]}\n      `>`  : {s[:60]}")
        tags = _tags_of(fm)
        want = "/".join([
            next((t.split("/", 1)[1] for t in tags if t.startswith("项目/")), "-"),
            next((t.split("/", 1)[1] for t in tags if t.startswith("模块/")), "-"),
            next((t.split("/", 1)[1] for t in tags if t.startswith("类型/")), "-"),
        ])
        if (r.get("facets") or "") != want:
            bad.append(f"INDEX:{r['line']} 分类列 ≠ 卡片三面（INDEX: {r.get('facets') or '空'} / "
                       f"卡片: {want}）—— 跑 `qwiki-sync.py --write` 重推")
        if r["summary"].startswith(("#", "|", "!")) or len(r["summary"]) > MAX_SUMMARY:
            bad.append(f"INDEX:{r['line']} 总结列异常（{len(r['summary'])} 字符，应以摘要开头且 ≤{MAX_SUMMARY}）")
    return "INDEX 投影（标题列 / 总结列）", not bad, bad


def check_links(root, cards, rows):
    """卡片 `[[...]]` 必须解析到另一张卡（素材不参与卡片图）。"""
    slugs = {os.path.splitext(os.path.basename(c))[0] for c in cards}
    bad = []
    for rel in cards:
        t = strip_code(open(os.path.join(root, rel), encoding="utf-8").read())
        for m in LINK_RE.finditer(t):
            raw = m.group(1).strip()
            if "/" in raw:
                bad.append(f"{rel} → [[{raw}]] 带项目前缀（已全库归一为 [[slug]]）")
                continue
            if raw not in slugs:
                bad.append(f"{rel} → [[{raw}]] 不是卡片")
    return "双链只连卡片（死链 / 指素材）", not bad, bad


def check_material_paths(root, cards, rows):
    """卡片里引用的素材路径必须真实存在，且不用旧目录名。

    只认「首段是真实项目名」的路径——代码仓也有 `0_workbench/change/…`、
    `text/data/…` 这类同名段，不加这条会报一堆假阳性。
    """
    pd = os.path.join(root, "projects")
    projects = {d for d in os.listdir(pd) if os.path.isdir(os.path.join(pd, d))} if os.path.isdir(pd) else set()
    bad = []
    for rel in cards:
        t = open(os.path.join(root, rel), encoding="utf-8").read()
        for m in re.finditer(r"`([a-z0-9_-]+/resource/[^`]+)`", t):
            if m.group(1) not in projects:
                continue  # 代码仓路径（rootfs/resource/… 等），不是 qwiki 素材
            if not os.path.exists(os.path.join(root, "projects", m.group(1))):
                bad.append(f"{rel}: 素材路径不存在 `{m.group(1)}`")
        for m in re.finditer(r"`([a-z0-9_-]+)/(references|design|archive|change|data)/([^`]+)`", t):
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


def check_slug_unique(root, cards, rows):
    """slug 全库唯一（§命名约定 3）：同名族（同一角色在多项目各有一张）一律加项目前缀。

    `[[slug]]` 靠 slug 解析，而解析处 `tgt.split("/")[-1]` 落进一个**集合**——
    重名在链接解析里是**静默**的：两边都"解析成功"，入链、网视图、轨迹卡归属
    却全指向不明。所以单列一条断言（2026-10-13：两个项目各有一张
    aic8800-wifi-driver.md，全靠人工跑全库双链图才挖出来）。
    """
    seen = {}
    for rel in cards:
        seen.setdefault(os.path.splitext(os.path.basename(rel))[0], []).append(rel)
    bad = [
        f"slug「{s}」重复 {len(ps)} 处：{' ｜ '.join(ps)} —— 同名族族内一律加项目前缀（如 `<项目>-{s}`）；"
        f"指向它的 [[{s}]] 目前解析不明"
        for s, ps in sorted(seen.items()) if len(ps) > 1
    ]
    return "slug 全库唯一（同名族加项目前缀）", not bad, bad


def check_upward_links(root, cards, rows):
    """检索双向可达：聚合卡**在正文段里列出的**独立卡子卡，须有一条链接指回它。

    组织面天生是"聚合卡挂子卡"的单向可见；不补上行边，检索从细节命中后就回不去
    （只能退回 INDEX 重查）。判据只认**正文段（`## 相关` 之前）**里列出的子卡——
    聚合卡「相关」段里的横向引用不算挂载（那是直链）。上行边的措辞不校验。
    """
    kinds, out_all, declared = {}, {}, {}
    for rel in cards:
        text = open(os.path.join(root, rel), encoding="utf-8").read()
        slug = os.path.splitext(os.path.basename(rel))[0]
        body = split(text)[1]
        kinds[slug] = "聚合卡" if re.search(r"(?m)^##\s*.*(模块边界|职责描述)", body) else "独立卡"
        out_all[slug] = {m.group(1).strip().split("/")[-1]
                         for m in LINK_RE.finditer(strip_code(text))}
        head = re.split(r"(?m)^##\s*相关\s*$", strip_code(body), maxsplit=1)[0]
        declared[slug] = {m.group(1).strip().split("/")[-1] for m in LINK_RE.finditer(head)}
    bad = []
    for a, kind in kinds.items():
        if kind != "聚合卡":
            continue
        for c in sorted(declared[a] - {a}):
            if kinds.get(c) != "独立卡":
                continue
            if a not in out_all.get(c, set()):
                bad.append(f"[[{c}]] 是聚合卡 [[{a}]] 正文里列出的子卡，但没有上行边（检索回不去）")
    return "检索双向可达（聚合卡子卡有上行边）", not bad, bad


def check_track_ownership(root, cards, rows):
    """每张轨迹卡（§A~§E 裁决账）的入链里至少 1 张聚合卡。"""
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
    bad = [f"轨迹卡 [[{t}]] 的入链里没有聚合卡 —— 这条线缺一张聚合卡"
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
        return "YAML 头可解析", None, ["（跳过：本机无 PyYAML —— 此项未验证，不计入通过）"]
    bad = []
    n = 0
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d != ".git"]
        for f in fn:
            if not f.endswith(".md"):
                continue
            rel = os.path.relpath(os.path.join(dp, f), root)
            fm, _ = split(open(os.path.join(dp, f), encoding="utf-8").read())
            if fm is None:
                continue
            n += 1
            try:
                data = yaml.safe_load(fm)
            except Exception as e:
                bad.append(f"{rel}: {str(e)[:60]}")
                continue
            if not isinstance(data, dict):
                continue
            for key in ("title", "type", "date"):
                if not data.get(key):
                    bad.append(f"{rel}: YAML 头缺必填键 `{key}`（title / type / date 三必填）")
            tv = data.get("type")
            if tv is not None and str(tv).strip() not in ("note", "card"):
                bad.append(f"{rel}: `type` 值 `{tv}` 不在 note|card 值域")
    return f"YAML 头可解析（{n} 个带头文件）", not bad, bad


ROLE_WORDS = {
    # 结构 / 状态
    "system", "workspace", "design", "line", "ledger",
    # 手册 / 规约 / 方法论
    "manual", "conventions", "anti-patterns", "rules", "guide", "workflow", "method", "playbook",
    # 一次性记录（配日期前缀）
    "review", "audit", "ab", "regression", "closure", "profile", "baseline", "pitfalls",
}
ONE_OFF_ROLES = {"review", "audit", "ab", "regression", "closure", "profile", "pitfalls"}


def naming_hints(root, cards, rows):
    """命名形态提示（**不计入断言、不影响退出码**）：角色词位置 / 一次性角色带日期 / 同族前缀齐否。

    规则见 SCHEMA §命名约定 规则 4；提示只报不改，由 §sync 时逐条判断。
    """
    out = []
    names = {rel: os.path.basename(rel)[:-3] for rel in cards}
    pd = os.path.join(root, "projects")
    projs = {d for d in os.listdir(pd) if os.path.isdir(os.path.join(pd, d))} if os.path.isdir(pd) else set()
    for rel, n in sorted(names.items()):
        toks = [t for t in n.split("-") if t]
        if not toks:
            continue
        last = toks[-1]
        mid_rec = [t for t in toks[:-1] if t in ONE_OFF_ROLES and t != "ab"]   # 只对「记录类」角色报错位；`ab` 常作名词（AB 槽位）故豁免
        if last not in ROLE_WORDS and mid_rec:
            out.append(f"{rel}: 记录角色 {mid_rec} 不在末位 —— 按 `<YYYYMMDD>-<主题>-<角色>` 把角色移到末位（限定语并入主题位）")
        elif last in ONE_OFF_ROLES and not re.match(r"^\d{8}-", n):
            out.append(f"{rel}: 角色 `{last}` 属一次性记录，按规则 2/4 应带 `<YYYYMMDD>-` 前缀")
    # 跨项目同族前缀齐否（族 = 去掉项目前缀后的「核心名」，须以角色词收尾）
    fam = {}
    for rel, n in names.items():
        proj = rel.split("/")[1] if rel.startswith("projects/") else None
        base = re.sub(r"^\d{8}-", "", n)
        pref = proj.replace("_", "-") if proj in projs else None
        has_pref = bool(pref and base.startswith(pref + "-"))
        core = base[len(pref) + 1:] if has_pref else base
        if core.split("-")[-1] not in ROLE_WORDS:
            continue
        fam.setdefault(core, []).append((proj, has_pref, rel))
    for core, items in sorted(fam.items()):
        if len({p for p, _, _ in items}) < 2:
            continue
        lacking = [rel for p, hp, rel in items if p and not hp]
        have = [rel for p, hp, rel in items if hp]
        if lacking and have:
            out.append(f"同族 `{core}` 前缀不齐：{'；'.join(lacking)}（同族其余带项目名前缀，如 {have[0]}）")
    return out


# 标签三面（2026-10-22 定）：项目 / 模块 / 类型 + 关键词分级。
# 词表是契约：新增取值要改这里 + SCHEMA，避免标签再次碎成一堆同义词。
FACET_MODULES = {"wifi", "内核", "内存", "网络", "驱动", "USB", "音频", "烧录",
                 "构建", "工具链", "应用", "知识库", "测试", "发布"}
FACET_TYPES = {"审查", "实测", "优化", "否决", "复盘", "设计", "排查",
               "修复", "迁移", "手册", "测试", "分析", "debug"}


def _tags_of(fm):
    """从 `tags: [a, b]` 里取出标签（不引 PyYAML）。"""
    raw = fm_field(fm, "tags")
    inner = re.search(r"\[(.*?)\]", raw or "")
    return [t.strip() for t in (inner.group(1) if inner else "").split(",") if t.strip()]


def check_tag_facets(root, cards, rows):
    """标签三面（规格，不报红）：项目=路径、模块∈词表、一级唯一、二级≥1、级别连续。"""
    pd = os.path.join(root, "projects")
    projects = {d for d in os.listdir(pd) if os.path.isdir(os.path.join(pd, d))} if os.path.isdir(pd) else set()
    bad, bare = [], 0
    for rel in cards:
        fm, _ = split(open(os.path.join(root, rel), encoding="utf-8").read())
        if fm is None:
            continue
        tags = _tags_of(fm)
        if not any(t.startswith(("项目/", "模块/", "关键词1/")) for t in tags):
            bare += 1
            continue
        proj = [t.split("/", 1)[1] for t in tags if t.startswith("项目/")]
        mods = [t.split("/", 1)[1] for t in tags if t.startswith("模块/")]
        k1 = [t.split("/", 1)[1] for t in tags if t.startswith("关键词1/")]
        k2 = [t.split("/", 1)[1] for t in tags if t.startswith("关键词2/")]
        k3 = [t.split("/", 1)[1] for t in tags if t.startswith("关键词3/")]
        want = section_of(rel, projects)
        if len(proj) != 1:
            bad.append(f"{rel}: 需要且仅需要一个 `项目/<x>`（现 {len(proj)} 个）")
        elif want and proj[0] != want:
            bad.append(f"{rel}: `项目/{proj[0]}` 与路径不符（应为 `项目/{want}`）")
        if len(mods) != 1:
            bad.append(f"{rel}: 需要且仅需要一个 `模块/<x>`（现 {len(mods)} 个）")
        elif mods[0] not in FACET_MODULES:
            bad.append(f"{rel}: 模块 `{mods[0]}` 不在词表内（{ '、'.join(sorted(FACET_MODULES)) }）")
        if len(k1) != 1:
            bad.append(f"{rel}: 关键词1 必须唯一（现 {len(k1)} 个）")
        if not k2:
            bad.append(f"{rel}: 缺关键词2（一级之后至少要有一个更窄的词）")
        if k3 and not k2:
            bad.append(f"{rel}: 有关键词3 但缺关键词2（级别不连续）")
        for t in tags:
            if t.split("/", 1)[0] not in ("项目", "模块", "类型", "关键词1", "关键词2", "关键词3"):
                bad.append(f"{rel}: 标签 `{t}` 没有分面前缀（项目/模块/类型/关键词N）")
        if len(tags) > 5:
            bad.append(f"{rel}: 标签 {len(tags)} 个（上限 5）—— 多出来的通常是第三个关键词，"
                       "说明这张卡装着不止一个知识点，该拆卡")
    if bare:
        bad.append(f"另有 {bare} 张卡仍是旧式自由标签（未分面）—— 属存量，批量改写时处理")
    return "标签三面（项目 / 模块 / 关键词分级）", not bad, bad


CHECKS = [
    # 硬错：INDEX 与事实不符（说有→不存在 / 有卡→无入口 / 放错段 / 表坏了）
    (check_index_entries, "index"),
    (check_index_table, "index"),
    # 规格：不影响「找得到」，只影响「写得齐不齐」
    (check_card_headers, "spec"),
    (check_index_projection, "spec"),
    (check_links, "spec"),
    (check_material_paths, "spec"),
    (check_naming, "spec"),
    (check_slug_unique, "spec"),
    (check_upward_links, "spec"),
    (check_track_ownership, "spec"),
    (check_material_no_header, "spec"),
    (check_tag_facets, "spec"),
    (check_yaml, "spec"),
]

# 规格项的稳定键：<对象>::<规则码>。用于账本记账（版本代差不参与，见 SKILL §sync）
SPEC_CODES = [
    (r"正文 H1 ≠ YAML title", "h1-title"),
    (r"H1 不在正文首位", "h1-first"),
    (r"不是 `>` 引言行", "quote-block"),
    (r"首行是出处/状态", "prov-first"),
    (r"缺 `> 依据`", "evidence-line"),
    (r"相关段标题须为", "related-heading"),
    (r"无 YAML 头", "yaml-header"),
    (r"文件名含下划线|文件名含大写|文件名含空格|日期是后缀", "naming"),
    (r"标题列", "index-title"),
    (r"总结列", "index-summary"),
    (r"不是卡片|带项目前缀", "links"),
    (r"素材路径|旧目录名", "material-path"),
    (r"slug「", "slug-dup"),
    (r"上行边", "upward-link"),
    (r"轨迹卡", "track-owner"),
    (r"素材/脚本带 YAML 头", "material-header"),
    (r"YAML", "yaml-parse"),
]

LEDGER = ".qwiki-maintenance.json"


def load_ledger(root):
    """账本：baseline（存量，不再提醒）+ acked（人确认过，永不再提）。读不到就当空。"""
    path = os.path.join(root, LEDGER)
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return {"baseline": dict(data.get("baseline") or {}),
                "acked": dict(data.get("acked") or {})}
    except Exception:
        return {"baseline": {}, "acked": {}}


def save_ledger(root, data):
    with open(os.path.join(root, LEDGER), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


def spec_key(msg, rows):
    """把一条规格失败压成稳定键；INDEX 行按行号回查文件列（行号会动，文件列不会）。"""
    code = next((c for pat, c in SPEC_CODES if re.search(pat, msg)), "other")
    if msg.startswith("INDEX:"):
        ln = re.match(r"INDEX:(\d+)", msg)
        key = next((r["key"] for r in rows if ln and r["line"] == int(ln.group(1))), "INDEX")
        return f"{key}::{code}"
    return f"{msg.split(':', 1)[0].strip()}::{code}"


def main(argv):
    root = os.path.expanduser(argv[0]) if argv and not argv[0].startswith("-") else os.path.expanduser("~/qwiki")
    quiet = "--quiet" in argv or "-q" in argv
    show_all = "--all" in argv
    strict = "--strict" in argv
    baseline_mode = "--baseline" in argv
    if not os.path.isdir(root):
        print(f"x 不是目录：{root}")
        return 1
    cards, rows = card_files(root), index_rows(root)
    print(f"qwiki 体检：{root}")
    print(f"  卡片 {len(cards)} 张 ｜ INDEX {len(rows)} 行\n")

    hard, spec, skipped = [], [], []
    for fn, tier in CHECKS:
        name, ok, detail = fn(root, cards, rows)
        if ok is None:
            skipped.append(name)
        elif ok is False:
            (hard if tier == "index" else spec).append((name, detail))

    ledger = load_ledger(root)
    known = set(ledger["baseline"]) | set(ledger["acked"])
    items = [(spec_key(m, rows), m) for _, d in spec for m in d]
    new_items = [(k, m) for k, m in items if k not in known]
    old_count = len(items) - len(new_items)

    if baseline_mode:
        today = datetime.date.today().isoformat()
        current = {k for k, _ in items}
        ledger["baseline"] = {k: ledger["baseline"].get(k, today) for k in sorted(current)}
        save_ledger(root, ledger)
        dropped = len(known - current - set(ledger["acked"]))
        print(f"账本已更新：存量 {len(current)} 项入 baseline"
              + (f"，销账 {dropped} 项" if dropped else "")
              + f"\n  文件：{os.path.join(root, LEDGER)}\n")
        return 0

    # ── 硬错：只有这一栏配叫「错」──
    if hard:
        for name, detail in hard:
            print(f"  INDEX 入口   ✗ {name}（{len(detail)} 处）")
            shown = detail if show_all else detail[:20]
            for d in shown:
                print(f"      {d}")
            if len(detail) > len(shown):
                print(f"      … 另 {len(detail) - len(shown)} 条（--all 打全量）")
    else:
        print("  INDEX 入口   ✓ 完整（每行都对得上卡、每张卡都有入口）")

    # ── 规格：只记账，不报警 ──
    if spec:
        head = f"  {'规格':<11}— {len(items)} 项（存量 {old_count} ／ 新增 {len(new_items)}）"
        print(head)
        for name, detail in spec:
            print(f"      · {name.split('（')[0]}：{len(detail)}")
        shown = items if show_all else new_items
        limit = len(shown) if show_all else 20
        for _, m in shown[:limit]:
            print(f"      - {m}")
        if len(shown) > limit:
            print(f"      … 另 {len(shown) - limit} 条（--all 打全量）")
    else:
        print(f"  {'规格':<11}✓ 无待维护项")

    if skipped:
        print(f"  其他         ⊘ {len(skipped)} 项未验证（缺 PyYAML，装上下次会跑）")

    hints = naming_hints(root, cards, rows)
    if hints and not quiet:
        shown_hints = hints if show_all else hints[:20]
        print(f"\n提示（不计失败 —— 命名形态建议，规则见 SCHEMA §命名约定 规则 4）")
        for h in shown_hints:
            print(f"    · {h}")
        if len(hints) > len(shown_hints):
            print(f"    … 另 {len(hints) - len(shown_hints)} 条（--all 打全量）")

    print()
    if hard:
        print(f"INDEX 入口 {len(hard)} 处错 —— 这会让知识『找不到』，先修这个；规格项都是保养，不着急。")
        return 1
    if strict and new_items:
        print(f"INDEX 入口完整；--strict 下新增规格项 {len(new_items)} 项 → 退出码 2。")
        return 2
    if items:
        print(f"可用。{len(items)} 条规格建议（存量 {old_count} ／ 新增 {len(new_items)}），"
              "不影响检索；改写那张卡时会顺手重生。")
    else:
        print("可用，且没有待维护项。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
