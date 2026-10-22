#!/usr/bin/env python3
"""qwiki 一致性自检 —— 把 SCHEMA / SKILL 的约定变成可执行断言。

用法:  python3 qwiki-check.py [知识库根目录]        # 默认 ~/qwiki
       python3 qwiki-check.py ~/qwiki --quiet      # 只打失败项与汇总
       python3 qwiki-check.py ~/qwiki --all        # 失败明细打全量（默认截断到 20 条）
退出码: 0 = 全过；1 = 有失败项（可直接串进 hook / CI）

设计取舍：
- **只读**，不改任何文件；发现的问题由 AI 按 SKILL §sync 处置。
- **不依赖 PyYAML**（除「YAML 可解析」一项，缺库时该项跳过并标注）——
  自检工具本身不该因为别人的环境少个包就跑不起来。
- 判定口径全部来自 SCHEMA：卡片集 = `personal/*.md` + `projects/<项目>/**/*.md`，
  排除 `resource/`（素材）、`scripts/`（根层 .md 一律视为卡片——2026-10-13 起无例外）。
"""
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
                     "path": c[2], "key": key})
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


def check_index_projection(root, cards, rows):
    """INDEX 两列 = 卡片集的正投影；段头由路径推出；一卡一行。"""
    bad, seen = [], set()
    pd = os.path.join(root, "projects")
    projects = {d for d in os.listdir(pd) if os.path.isdir(os.path.join(pd, d))} if os.path.isdir(pd) else set()
    for r in rows:
        if r["key"].startswith("projects/"):
            bad.append(f"INDEX:{r['line']} 文件列带 `projects/` 前缀（应写 `<项目>/<slug>.md`，省略前缀）")
        rel = resolve(root, r["key"])
        if rel is None:
            bad.append(f"INDEX:{r['line']} 文件列指向不存在的文件（{r['key']}）")
            continue
        if rel in seen:
            bad.append(f"INDEX:{r['line']} 「{os.path.basename(rel)}」占了多行（一卡一行）")
        seen.add(rel)
        want = section_of(rel, projects)
        if want and r.get("section") and want != r["section"]:
            bad.append(f"INDEX:{r['line']} 段头 `## {r['section']}` 与卡片路径不符（应在 `## {want}`）")
        fm, body = split(open(os.path.join(root, rel), encoding="utf-8").read())
        t, s = fm_field(fm, "title"), summary_line(body)
        if t and r["title"] != t:
            bad.append(f"INDEX:{r['line']} 标题列 ≠ 卡片 title\n      INDEX: {r['title'][:60]}\n      title: {t[:60]}")
        if not r["summary"]:
            bad.append(f"INDEX:{r['line']} 总结列为空")
        elif s and r["summary"] != s:
            bad.append(f"INDEX:{r['line']} 总结列 ≠ 卡片 `>` 行\n      INDEX: {r['summary'][:60]}\n      `>`  : {s[:60]}")
    missing = [c for c in cards if c not in seen]
    bad += [f"{c}: 有卡但 INDEX 无登记行" for c in missing]
    return "INDEX 正投影（标题列 / 总结列 / 段头 / 一卡一行 / 无漏登记）", not bad, bad


def check_index_clean(root, cards, rows):
    """INDEX 只登记卡片；无死链；总结列长度。"""
    bad = []
    for r in rows:
        seg = [x for x in r["key"].split("/") if x]
        if any(x in SKIP_DIRS - {".git"} for x in seg):
            bad.append(f"INDEX:{r['line']} 素材/脚本误登本表（{r['key']}）")
        if resolve(root, r["key"]) is None:
            bad.append(f"INDEX:{r['line']} 死链（{r['key']}）")
        if r["summary"].startswith(("#", "|", "!")) or len(r["summary"]) > MAX_SUMMARY:
            bad.append(f"INDEX:{r['line']} 总结列异常（{len(r['summary'])} 字符，应以摘要开头且 ≤{MAX_SUMMARY}）")
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
    return "INDEX 纯度（只登记卡片 / 无死链 / 摘要长度 / 表体完整）", not bad, bad


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


CHECKS = [
    check_card_headers,
    check_index_projection,
    check_index_clean,
    check_links,
    check_material_paths,
    check_naming,
    check_slug_unique,
    check_upward_links,
    check_track_ownership,
    check_material_no_header,
    check_yaml,
]


def main(argv):
    root = os.path.expanduser(argv[0]) if argv and not argv[0].startswith("-") else os.path.expanduser("~/qwiki")
    quiet = "--quiet" in argv or "-q" in argv
    show_all = "--all" in argv
    if not os.path.isdir(root):
        print(f"✗ 不是目录：{root}")
        return 1
    cards, rows = card_files(root), index_rows(root)
    print(f"qwiki 自检：{root}")
    print(f"  卡片 {len(cards)} 张 ｜ INDEX {len(rows)} 行\n")
    failed, skipped, failed_names = 0, 0, []
    for fn in CHECKS:
        name, ok, detail = fn(root, cards, rows)
        print(f"  {'⊘' if ok is None else ('✓' if ok else '✗')} {name}")
        if ok is not True:
            shown = detail if show_all else detail[:20]
            for d in shown:
                print(f"      {d}")
            if len(detail) > len(shown):
                print(f"      … 另 {len(detail) - len(shown)} 条（--all 打全量）")
        if ok is False:
            failed += 1
            failed_names.append(name)
        elif ok is None:
            skipped += 1
    hints = naming_hints(root, cards, rows)
    if hints and not quiet:
        shown_hints = hints if show_all else hints[:20]
        print(f"\n提示（不计失败 —— 命名形态建议，规则见 SCHEMA §命名约定 规则 4）")
        for h in shown_hints:
            print(f"    · {h}")
        if len(hints) > len(shown_hints):
            print(f"    … 另 {len(hints) - len(shown_hints)} 条（--all 打全量）")
    if any("正投影" in n for n in failed_names):
        print("\n提示：投影类红灯（标题列 / 总结列与卡片对不上）不用手改 —— "
              "跑 `python3 scripts/qwiki-sync.py <库根> --write` 重建 INDEX 后再自检。")
    print()
    if failed:
        print(f"{failed} 项未通过 —— 按 SKILL §sync 处置")
    elif skipped:
        print(f"{len(CHECKS) - skipped} 项通过 · {skipped} 项跳过（未验证）")
    else:
        print("全部通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
