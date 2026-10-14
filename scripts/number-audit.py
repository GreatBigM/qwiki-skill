#!/usr/bin/env python3
"""qwiki 数字审计 —— 宪法与对外文档里的实测数字必须落在「口径行」的作用域里。

CURRENT: 实测数字须落在某条「口径（… YYYY-MM-DD）」的作用域内（同列表项子树 / 同段 / 同一引用块；空行切断归属）
    —— 这一行是判据的**单一真相源**：`--parity` 会断言同一句话出现在 SKILL.md 与
       README.md 里（改语义忘了改描述，pre-push 就拒推）。改判据时先改这里。

CURRENT_FP: ba1beb653096bf35
    —— 语义核（下面 `语义核 begin/end` 之间：NUM / DATE / DECL / STRUCT / VAGUE / 作用域与
       判定那几个函数）的 sha256 前 16 位。**改了语义核必须跑 `--seal` 重签**，否则
       `--parity` 直接拒（"实现动过、描述没重签"）。它只能证明"改过并已显式重签"，
       **不能**证明"描述写对了"——别宣称超出这个范围。

用法:
    python3 number-audit.py [仓库根]      # 默认 = 本脚本上一级
    python3 number-audit.py --self-test   # 逐数字比对的正反样本（含已知缺陷类别的回归组）
    python3 number-audit.py --parity      # 断言 CURRENT 那句在 SKILL.md / README.md 里逐字相同
退出码: 0 = 全部合规；1 = 有裸数字 / 描述与实现不一致（可直接串进 pre-push / CI）

**为什么要有它（2026-10-14）**：同一条规则（数字必须带口径 + 日期）连立三轮，
每轮都靠人工 grep 补漏——补 2 处漏 3 处、再补 3 处又漏 1 处，其中一处是
「日期张冠李戴」（段落定稿日被当成数字的测量日）骗过了人眼。根因与脱敏同构：
**规则靠人记必然回潮**，所以它得是机器判的。

判定（确定性：不调窗口、不做块级近似、不复制数字）:
    一个数字合格 ⇔ **它落在某条口径行的作用域里**。
      口径行 = 含「口径」且含 `YYYY-MM-DD` 的行（行内口径也算，如 `2026-10-14 实测（口径 = …）`）
      作用域 = 该口径行**所属的那个语法单位**——
               ① 列表项子树（本级 + 其后所有更深缩进的行），或
               ② 口径行是引用块时，整段连续 `>` 行
    ⇒ 按**缩进 / 引用符**判归属，不按字符距离：
      - v1「同行或上一行有日期」→ 无关日期把整行数字全免检（立项病例本身漏网）
      - v2「块内有口径行 ⇒ 整块合格」→ 连坐升到块级（实测 SCHEMA 45 个数字 100% 靠它豁免，
        一个口径行覆盖过 18 个数字）
      - v3（本版）作用域收到**列表项 / 引用块**一级 ⇒ 同块其它列表项的数字照查

实测数字的边界（不计）:
    ① 操作 / 查询返回：`0 条` / `1 条`（有无判断，不是测量）
    ② 结构性计数：`11 项` / `≤80 字符` / `5 页` / `八段` / `1-3 个` / `60 次/时`
       —— 判定**锚定在匹配项本身**（只看紧邻前后文），不用 ±12 字窗口：
         窗口会把相邻数字的限定词算到本数字头上
         （实测：`每张轨迹卡至少 1 张聚合卡；全库 190 卡` 里 190 曾被「至少」连坐）
    ③ 公式变量：`n` / `2n` / `C(n,2)` / `n(n−1)`（不含单位，天然不进 NUM）
    ④ 标识符（线号 / 版本号 / 项目号）不是数字量，由**单位表**排除（它们没有量词）；
       不另立"3 位以上裸整数"规则——实测那只会抓到 `310 线` 这类名字（假阳性）
    ⑤ 模糊量词（"只占少数 / 几十张 / 若干"）**只提示、不判失败**：它是绕过闸门的退路，
       但在中文里本身合法，硬判必误报

单位表：`%` `张` `条` `行` `处` `跳` `个` `次` `位` `对` `卡` `倍` `×`，以及 `N/M`

自审实测到的边界（取舍，已知）:
    ⓐ **口径要与数字同属一个语法单位**——同一个列表项（含其子项）、同一段（无空行的续行 /
       懒续行）、或同一个引用块。**空行会切断归属**（跨空行的独立段落不被认作该数字的口径）：
       这是有意的——否则"段落级"豁免会把连坐放大回去。
    ⓑ **限定词是可绕过的**：数字前加 `≥` / `至少` 即免检，所以这一类的豁免**一律报提示**
       （qualifier），让旁路可见；项 / 页 / 次每时 / 0-1 条 属真结构性计数，不提示。
    ⓒ `N/M` 只认**两侧各 ≥2 位**（`95/95` 是测量；`4/5` 这类轮次分数不是）。
    ⓓ **表格单元格不是列表项 / 引用块** ⇒ 表格里的实测数字无法被口径覆盖（当前三份文件
       的表内无实测数字，属边界）。要在表里放实测数字，就把口径写成表下方的 `>` 引用块
       并保持与表相邻，或把该项改成列表。

覆盖范围（取舍，不是缺陷）：只扫 SCHEMA.md / README.md / SKILL.md。
    CHANGELOG 是带日期的记录（数字本就该落在那里）；references/ 与 templates/ 未纳入。
    要扩就把文件名加进 SCAN。
"""
import hashlib
import os
import re
import sys

SCAN = ["SCHEMA.md", "README.md", "SKILL.md"]

# 实测数字：整数 + 计数单位，或 占比 / 倍数（允许小数），或 N/M
# 计数单位限定整数：否则 `3.10 卡` / `5.15 卡` 这类**线号**会被当成数量
# ══ 语义核 begin（改这里必须跑 --seal 重签 CURRENT_FP）══
NUM = re.compile(
    r"(?<![\w.])\d+\s*(?:张|条|行|处|跳|个|次|位|对|卡)"
    r"|(?<![\w.])\d+(?:\.\d+)?\s*(?:%|倍|×)"
    r"|(?<![\w.])\d{2,}\s*/\s*\d{2,}"
)
DATE = re.compile(r"20\d\d-\d\d-\d\d")

# 「口径」必须是**被边界引导的声明**：前面是行首 / 括号 / 句读 / 加粗。
# 否则「此前口径写作…」「工具侧口径…」这类**提到**口径这个词的句子会被当成声明，
# 把同项的实测数字一并无条件免检（洞 B：2026-10-14 由删除实验证实）。
DECL = re.compile(r"(?:^|[（(，,；;。：:])\s*\*{0,2}口径")

# 结构性 / 操作返回 / 区间：只看紧邻前后文

# 模糊量词：只提示、不判失败
VAGUE = re.compile(r"只占少数|占少数|几十[张条处个]|若干[张条处个]|十来个|寥寥")


def strip_prefix(line):
    """去掉行首空白 / 引用 / 列表符 / 加粗。"""
    s = line.strip()
    s = re.sub(r"^[>+\-*\s]+", "", s)
    return re.sub(r"^\*+", "", s)


def is_decl(line):
    """口径声明：**被边界引导**的「口径」+ 同行日期（行内口径也算）。"""
    return bool(DECL.search(strip_prefix(line)) or DECL.search(line)) and bool(DATE.search(line))


def indent_of(line):
    return len(line) - len(line.lstrip(" \t"))


def is_quote(line):
    return line.lstrip().startswith(">")


def mask_code(text):
    """→ (行列表, 每行是否在代码围栏内)。"""
    raw = text.split("\n")
    code, in_code = [], False
    for ln in raw:
        if ln.lstrip().startswith("```"):
            code.append(True)
            in_code = not in_code
            continue
        code.append(in_code)
    return raw, code


def is_block_start(line):
    """新块起始（列表项 / 引用 / 标题 / 表格 / 分隔线）—— 懒续行判定用。"""
    s = line.lstrip()
    return bool(re.match(r"(?:[-*+>#|]\s|\d+\.\s|---)", s))


def scopes(raw, code):
    """每条口径行 → 它豁免的行号集合（列表项子树 / 引用块，含 Markdown 懒续行）。"""
    out = []
    for i, ln in enumerate(raw):
        if code[i] or not is_decl(ln):
            continue
        if is_quote(ln):
            lo = i
            while lo > 0 and is_quote(raw[lo - 1]) and not code[lo - 1]:
                lo -= 1
            hi = i
            while hi + 1 < len(raw) and is_quote(raw[hi + 1]) and not code[hi + 1]:
                hi += 1
            out.append(set(range(lo, hi + 1)))
            continue
        ind = indent_of(ln)
        head = i
        j = i - 1
        while j >= 0 and raw[j].strip() != "" and not code[j]:
            if indent_of(raw[j]) < ind:
                head = j
                break
            if indent_of(raw[j]) == ind and not is_block_start(raw[j]):
                head = j        # 同一段的续行（无空行分隔 ⇒ Markdown 里属同一段）
                break
            if indent_of(raw[j]) == ind and is_block_start(raw[j]) and not is_block_start(ln):
                head = j        # 口径行是上一列表项的**懒续行**（无空行分隔）
                break
            j -= 1
        base = indent_of(raw[head])
        scope = {head, i}
        k = head + 1
        while k < len(raw) and raw[k].strip() != "" and not code[k]:
            deeper = indent_of(raw[k]) > base
            lazy = (not is_block_start(raw[k])) and indent_of(raw[k]) <= base
            if not (deeper or lazy):
                break           # 同级（或更浅）的新块 ⇒ 本列表项到此为止
            scope.add(k)
            k += 1
        out.append(scope)
    return out


def struct_reason(m, line):
    """→ None（不是结构性）| "qualifier"（限定词豁免，**要提示**）| "structural"（真结构性计数）。

    锚定在匹配项本身（单位在匹配项内部，故看 tok）。
    限定词那一类是可被绕过的（在数字前加 `≥` 就行），所以它豁免时要**报提示**；
    项 / 页 / 次每小时 / 0-1 条 是真结构性计数，不必提示。
    """
    tok = m.group(0)
    pre = line[max(0, m.start() - 10):m.start()]
    if (re.search(r"(?:≥|≤|<|>)\s*$", pre)
            or re.search(r"(?:至少|不超过|最多|最少|至多)[^，。；]{0,6}$", pre)
            or re.search(r"[-–]\s*$", pre)):
        return "qualifier"                           # ≥80 / 至少应有 1 张 / 1-3 个
    digits = re.match(r"\d+", tok)
    v = int(digits.group(0)) if digits else None
    if tok.rstrip().endswith(("项", "页")) or re.search(r"次\s*/\s*时\s*$", tok):
        return "structural"                          # 11 项断言 / 5 页 / 60 次/时
    if tok.rstrip().endswith("条") and v in (0, 1):
        return "structural"                          # 0 条 / 1 条 = 有无判断
    return None


# ══ 语义核 end ══


def semantics_fp():
    """语义核的指纹（sha256 前 16 位）——只覆盖 begin/end 之间的实现。"""
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    m = re.search(r"(?s)# ══ 语义核 begin.*?# ══ 语义核 end ══", src)
    return hashlib.sha256(m.group(0).encode()).hexdigest()[:16] if m else ""


def seal(root):
    """--seal：重算并回写 CURRENT_FP（改语义核的人跑一次）。"""
    path = os.path.abspath(__file__)
    src = open(path, encoding="utf-8").read()
    fp = semantics_fp()
    if not re.search(r"(?m)^CURRENT_FP:", src):
        print("✗ docstring 缺 `CURRENT_FP:` 行")
        return 1
    open(path, "w", encoding="utf-8").write(
        re.sub(r"(?m)^CURRENT_FP:.*$", f"CURRENT_FP: {fp}", src))
    print(f"已重签 CURRENT_FP: {fp}")
    print("（若语义确实变了，接着把 SKILL.md / README.md 的描述改成新的 CURRENT 那句话）")
    return 0


def audit(root):
    bad, hints = [], []
    for name in SCAN:
        path = os.path.join(root, name)
        if not os.path.exists(path):
            continue
        raw, code = mask_code(open(path, encoding="utf-8").read())
        covered = set()
        for s in scopes(raw, code):
            covered |= s
        for i, ln in enumerate(raw):
            if code[i]:
                continue
            m = VAGUE.search(re.sub(r"`[^`]*`", "", ln))
            if m:
                hints.append(f"{name}:{i + 1} 模糊量词「{m.group(0)}」—— {ln.strip()[:56]}")
        for i, ln in enumerate(raw):
            if code[i] or i in covered:
                continue
            line = re.sub(r"`[^`]*`", "", ln)        # 行内代码不属于实测数字
            for m in NUM.finditer(line):
                reason = struct_reason(m, line)
                if reason == "qualifier":
                    hints.append(
                        f"{name}:{i + 1} 限定词豁免「{m.group(0).strip()}」—— "
                        "前置 ≥ / ≤ / 至少 等限定词使其免检；确认它是结构性阈值而非实测值")
                    continue
                if reason:
                    continue
                bad.append(
                    f"{name}:{i + 1} 裸数字「{m.group(0).strip()}」"
                    f"（不在任何口径行的作用域内）—— {ln.strip()[:64]}"
                )
    return bad, hints


NUMSTR = re.compile(r"「([^」]+)」")
SELF_TEST = [
    ("| 卡 | 61 张同属这条线 |\n", {"61 张"}, "裸数字（无口径行）"),
    ("- 某段 86 张卡\n  - **口径（2026-10-14 实测）**：该段根层 .md 卡片数\n", set(),
     "口径行是同列表项的子项 ⇒ 覆盖本级"),
    ("- 某段 86 张卡\n\n  - **口径（2026-10-14 实测）**：该段根层 .md 卡片数\n", {"86 张"},
     "★ 口径行被空行隔开（不在同一列表项子树内）"),
    ("- 每张轨迹卡的入链里至少应有 1 张聚合卡\n", set(), "结构性量词（至少应有）"),
    ("- C(n,2) 里的 n 与 2n 都不算实测数字\n", set(), "公式白名单"),
    ("> **目录不可拆的四件事（2026-10-13）**：② **grep 域**——按段检索（86 张卡）\n", {"86 张"},
     "★ 日期张冠李戴（同行有日期、但不是口径行）"),
    ("> **四件事（2026-10-13）**：② grep 域（86 张卡）\n> 口径：（86 张卡 = 该段根层 .md 数，2026-10-14 实测）\n", set(),
     "引用块内口径行 ⇒ 覆盖整个引用块"),
    ("- 共 435 对，其中只有 39 对有直接双链\n", {"435 对", "39 对"}, "★ 单位「对」（H3 回归）"),
    ("- 直链 3660 行，聚合 122 行，省 30×\n", {"3660 行", "122 行", "30×"}, "★ 单位「×」（H3 回归）"),
    ("- 每张轨迹卡至少 1 张聚合卡；全库 190 卡\n", {"190 卡"},
     "★ 相邻限定词不得连坐：v2 的 ±12 字窗口会把 190 卡 也放行"),
    ("- 窗口内 0 条 delegate_task 时判定为陈旧标记\n", set(), "操作/查询返回（0 条）"),
    ("- 310 线 ↔ 515 线 ⇒ 3.10 卡到 5.15 卡 3 跳可达\n", {"3 跳"},
     "★ 线号 / 版本号不是量：3.10 卡 · 5.15 卡 不误报（3 跳 是真数字）"),
    ("- 当前 v4 卡片体系下的迁移规则\n", set(), "★ 版本前缀 v4 不得被当成「4 卡」"),
    ("- **口径（2026-10-14 实测）**：无关说明\n- 另一项\n  - 子项里 186 张卡\n", {"186 张"},
     "★ 兄弟项的子项不得被上一个口径行吞掉（v3 首版作用域循环写错，实测假阴性）"),
    ("- 某段 86 张卡\n口径：（86 张卡 = 该段根层 .md 数，2026-10-14 实测）\n", set(),
     "★ 无空行的口径行是上一列表项的懒续行（CommonMark 语义）⇒ 覆盖该列表项"),
    ("- 有效轮 4/5（负载态）\n", set(), "★ 小分数不是 `N/M` 计数（判据收窄为两侧各 ≥2 位）"),
    ("- 回链 95/95 全绿\n", {"95/95"}, "★ 两位 `N/M` 仍是测量，须带口径"),
    ("全库 186 条关系，口径如下\n口径：（186 条 = 双链边数，2026-10-14 实测）\n", set(),
     "★ 无空行的口径行与上一行属同一段 ⇒ 覆盖该段"),
    ("- 某机制：此前口径写作旧说法（2026-10-13 定稿），实测 33 张因此分叉\n", {"33 张"},
     "★ 伪口径：提到「口径」这个词 ≠ 口径声明（洞 B 回归）"),
    ("- 某机制：记忆分层是工具侧口径：本宪法不定义（2026-10-13 清理），全库 190 卡\n", {"190 卡"},
     "★ 伪口径变体：术语解释里的「口径」（洞 B 回归）"),
    ("- 某段 86 张卡（口径 = 该段根层 .md 数，2026-10-14 实测）\n", set(),
     "正向控制：行内口径（括号引导）仍算声明"),
    ("- **聚合卡承担中转**：61 张子卡 1830 对\n  - **口径（2026-10-14 实测）**：子卡 = 正文段列出的独立卡\n"
     "- 另一条无关的：全库 190 卡\n", {"190 卡"},
     "★ 块级连坐回归：口径行只覆盖它所属的列表项，同块另一列表项的数字照查"),
]


def self_test():
    import tempfile
    fail = 0
    for text, expect, why in SELF_TEST:
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "SCHEMA.md"), "w", encoding="utf-8").write(text)
            bad, _ = audit(d)
        got = {m.group(1) for b in bad for m in NUMSTR.finditer(b)}
        ok = got == expect
        print(f"  {'✓' if ok else '✗'} {why}：报出 {sorted(got) or '（无）'}"
              + ("" if ok else f"（期望 {sorted(expect) or '（无）'}）"))
        fail += 0 if ok else 1
    print(f"自检：{len(SELF_TEST)} 组，" + ("全部通过" if not fail else f"{fail} 项失败"))
    return 1 if fail else 0


def parity(root):
    """--parity：① 验语义核指纹（实现动过没重签 ⇒ 拒）② 断言 CURRENT 那句话三方逐字一致。"""
    me = open(os.path.abspath(__file__), encoding="utf-8").read()
    m = re.search(r"(?m)^CURRENT:\s*(.+)$", me)
    if not m:
        print("✗ 本脚本 docstring 缺 `CURRENT:` 行（判据的单一真相源）")
        return 1
    canon = m.group(1).strip()

    bad = []
    sealed = re.search(r"(?m)^CURRENT_FP:\s*(\S+)", me)
    if not sealed:
        bad.append("docstring 缺 `CURRENT_FP:` 行（跑 `--seal` 生成）")
    elif sealed.group(1) != semantics_fp():
        bad.append("语义核已变但未重签 CURRENT_FP ⇒ 跑 `--seal`，"
                   "并把 SKILL.md / README.md 的描述改成新的 CURRENT 那句")

    for name in ("SKILL.md", "README.md"):
        path = os.path.join(root, name)
        if not os.path.exists(path):
            continue
        if canon not in open(path, encoding="utf-8").read():
            bad.append(f"{name} 里找不到 CURRENT 那句（判据改了但描述没改）")

    print("描述同步检查（--parity）：" + ("通过 ✓" if not bad else f"{len(bad)} 处不同步"))
    for b in bad:
        print(f"  ✗ {b}")
    if bad:
        print(f"\n  当前判据：{canon}")
        return 1
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    if "--seal" in argv:
        return seal(None)
    root = os.path.expanduser(argv[0]) if argv and not argv[0].startswith("-") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if "--parity" in argv:
        return parity(root)
    bad, hints = audit(root)
    print(f"数字审计：{root}")
    for b in bad:
        print(f"  ✗ {b}")
    if hints:
        print("\n  提示（不判失败）：")
        for h in hints:
            print(f"    · {h}")
    if bad:
        print(f"\n{len(bad)} 处裸数字 —— 把它挪进某条「口径（… YYYY-MM-DD）」的作用域"
              "（同列表项 / 同引用块），或属结构性计数 / 操作返回则调 STRUCT")
        return 1
    print("  合规：每个实测数字都落在口径行的作用域内 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
