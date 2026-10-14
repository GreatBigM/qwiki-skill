#!/usr/bin/env python3
"""qwiki 数字审计 —— 宪法与对外文档里的实测数字必须挂「口径行」。

用法:
    python3 number-audit.py [仓库根]      # 默认 = 本脚本上一级
    python3 number-audit.py --self-test   # 正反样本自检（含已知缺陷类别的回归组）
退出码: 0 = 全部合规；1 = 有裸数字（可直接串进 pre-push / CI）

**为什么要有它（2026-10-14）**：同一条规则（数字必须带口径 + 日期）连立三轮，
每轮都靠人工 grep 补漏——补 2 处漏 3 处、再补 3 处又漏 1 处，其中一处还是
"日期张冠李戴"（段落定稿日 2026-10-13 被当成数字的测量日）骗过了人眼。
根因与脱敏同构：**规则靠人记必然回潮**，所以它得是机器判的。

判定（确定性，不调窗口）:
    一个数字合格 ⇔ **它所在的块内存在一行「口径声明」**。
      块       = 空白行分隔的段落（含其下的子列表项）
      口径声明 = 去掉行首空白 / `>` / `-` / `*` / 加粗后，以「口径」起句，且该行含 `YYYY-MM-DD`
    块内其他位置出现的日期**一概不作数**——日期必须落在口径行上。
    ⇒ 这是把「这个日期归不归这个数字」的**语义判断**，换成「有没有那一行」的**语法判断**：
      不需要窗口、不需要调参、不存在"错日期恰好落在同一句"。
      v1 把「同行出现任意日期」当合格——于是"段落定稿日"把整行数字全免检，
      **恰恰漏掉了它立项时引用的那个病例**（2026-10-14 修）。

实测数字的边界（三类不计）:
    ① 操作 / 查询返回：`0 条` / `1 条`（有无判断，不是测量）
    ② 结构性计数：`11 项` / `≤80 字符` / `5 页` / `八段` / `1-3 个` / `60 次/时`
    ③ 公式变量：`n` / `2n` / `C(n,2)` / `n(n−1)`
    ④ 标识符（线号 / 版本号 / 项目号）不是数字量，由**单位表**天然排除（它们没有量词）
       —— 所以不另立"3 位以上裸整数"规则：实测那只会抓到 `310 线` 这类名字（假阳性），
          而给每个线号加白名单，正是"白名单越长、豁免面越大"的病复发。
    ⑤ 模糊量词（"只占少数 / 几十张 / 若干"）**只在报告里提示、不判失败**——它是绕过
       闸门的退路（把数字改成模糊说法即可合规，本仓发生过），但模糊量词在中文里本身
       合法，硬判必误报。

单位表：`%` `张` `条` `行` `处` `跳` `个` `次` `位` `对` `卡` `倍` `×`，以及 `N/M`
    2026-10-14 补 `对/卡/倍/×` —— 此前 `1830 对` / `435 对` / `190 卡` / `30×`
    全在闸门外（"X 对"恰是这套模型自己的核心量词）。

覆盖范围（取舍，不是缺陷）：只扫 SCHEMA.md / README.md / SKILL.md。
    CHANGELOG 是带日期的记录（数字本就该落在那里）；references/ 与 templates/ 未纳入。
    要扩就把文件名加进 SCAN。
"""
import os
import re
import sys

SCAN = ["SCHEMA.md", "README.md", "SKILL.md"]

# 实测数字的写法：整数 + 计数单位，或 占比 / 倍数（允许小数），或 N/M
# 计数单位限定整数：否则 `3.10 卡` / `5.15 卡` 这类**线号**会被当成数量
# （v2 曾把 3.10 卡、5.15 卡、`v4 卡片体系` 的 4 一起误报 —— 2026-10-14 修）
NUM = re.compile(
    r"(?<![\w.])\d+\s*(?:张|条|行|处|跳|个|次|位|对|卡)"
    r"|(?<![\w.])\d+(?:\.\d+)?\s*(?:%|倍|×)"
    r"|(?<![\w.])\d+\s*/\s*\d+"
)
DATE = re.compile(r"20\d\d-\d\d-\d\d")

# 结构性 / 公式 / 操作类豁免：**按匹配项**判定（v1 按整行，一行里出现
# "至少 / ≥ / ≤" 就把该行所有数字一起免检 —— 2026-10-14 修）
STRUCT = re.compile(
    "|".join([
        r"[≥≤<>]\s*\d",        # ≥80 / ≤5 / <3
        r"至少[^，。；]{0,8}\d",  # 至少 1 张 / 至少应有 1 张聚合卡
        r"\d+\s*项",           # 11 项断言
        r"\d+\s*页",           # 每会话 5 页
        r"1-3\s*个",           # 一次 1-3 个模块
        r"\d+\s*次\s*/\s*时",   # 60 次/时
        r"[01]\s*条",          # 操作 / 查询返回：0 条 / 1 条（有无判断）
        r"C\(\s*n",            # C(n,2)
        r"n\s*[（(]\s*n",       # n(n-1)
        r"\b2n\b",             # 2n 行
    ])
)

# 模糊量词（2026-10-14 起只**提示**、不判失败）：「把具体数字改成"只占少数 / 几十张"
# 来绕过闸门」是这条规则的退路（本仓 2.12.0 真发生过）。但模糊量词在中文里本身合法
# （"相当一部分""改几十张卡"都是正常措辞），硬判必然误报 —— 故降级为提示：
# 看到它时先问一句"这里原本是具体数字吗"，是就改回数字并补口径行。
VAGUE = re.compile(r"只占少数|占少数|几十[张条处个]|若干[张条处个]|十来个|寥寥")


def strip_prefix(line):
    """去掉行首空白 / 引用 / 列表符 / 加粗，用于识别「口径」起句。"""
    s = line.strip()
    s = re.sub(r"^[>+\-*\s]+", "", s)
    s = re.sub(r"^\*+", "", s)
    return s


def is_decl(line):
    """口径声明：以「口径」起句且含日期。"""
    return strip_prefix(line).startswith("口径") and bool(DATE.search(line))


def split(text):
    """按空白行切块 + 标出代码围栏内的行（两者都不参与判定）。"""
    raw = text.split("\n")
    code, in_code = [], False
    for ln in raw:
        if ln.lstrip().startswith("```"):
            code.append(True)
            in_code = not in_code
            continue
        code.append(in_code)
    blocks, cur = [], []
    for i, ln in enumerate(raw):
        if ln.strip() == "":
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(i)
    if cur:
        blocks.append(cur)
    return raw, code, blocks


def audit(root):
    bad, hints = [], []
    for name in SCAN:
        path = os.path.join(root, name)
        if not os.path.exists(path):
            continue
        raw, code, blocks = split(open(path, encoding="utf-8").read())
        for i, ln in enumerate(raw):
            if code[i]:
                continue
            m = VAGUE.search(re.sub(r"`[^`]*`", "", ln))
            if m:
                hints.append(f"{name}:{i + 1} 模糊量词「{m.group(0)}」—— {ln.strip()[:56]}")
        for blk in blocks:
            if any(is_decl(raw[i]) for i in blk):
                continue            # 块级绑定：本块有口径行 ⇒ 整块合格
            for i in blk:
                if code[i]:
                    continue
                line = re.sub(r"`[^`]*`", "", raw[i])   # 行内代码不属于实测数字
                for m in NUM.finditer(line):
                    w0, w1 = max(0, m.start() - 12), min(len(line), m.end() + 6)
                    if STRUCT.search(line[w0:w1]):
                        continue
                    bad.append(
                        f"{name}:{i + 1} 裸数字「{m.group(0).strip()}」"
                        f"（本块无「口径：… YYYY-MM-DD」行）—— {raw[i].strip()[:64]}"
                    )
    return bad, hints


SELF_TEST = [
    ("| 卡 | 61 张同属这条线 |\n", True, "裸数字（无口径行）"),
    ("某段 86 张卡\n口径：该段根层 .md 卡片数（2026-10-14 实测）\n", False, "同块带独立口径行"),
    ("某段 86 张卡\n\n口径：该段根层 .md 卡片数（2026-10-14 实测）\n", True,
     "★ 口径行被空行隔到别的块（块级绑定必须同块）"),
    ("每张轨迹卡的入链里至少应有 1 张聚合卡\n", False, "结构性量词（至少应有）"),
    ("C(n,2) 里的 n 与 2n 都不算实测数字\n", False, "公式白名单"),
    # ↓ 已知缺陷类别的回归组（v1 自检全绿却漏掉它 —— 5 组样本没有一组测这个类别）
    ("> **目录不可拆的四件事（2026-10-13）**：② **grep 域**——按段检索"
     "（`projects/<项目段>/` 84 张卡，不是全库 190）\n", True,
     "★ 日期张冠李戴（同行有日期、但不是口径行）"),
    ("> **目录不可拆的四件事（2026-10-13）**：② **grep 域**——按段检索（86 张卡）\n"
     "> 口径：最大段卡片数（2026-10-14 实测）\n", False, "张冠李戴已修：补独立口径行"),
    ("共 435 对，其中只有 39 对有直接双链\n", True, "★ 单位「对」（H3 回归）"),
    ("直链 3660 行，聚合 122 行，省 30×\n", True, "★ 单位「×」（H3 回归）"),
    ("共 1830 对，其中至少 130 对有直链\n", True, "★ 整行豁免回归：含「至少」不得连坐放行（H2 回归）"),
    ("窗口内 0 条 delegate_task 时判定为陈旧标记\n", False, "操作/查询返回（0 条）"),
    ("310 线 ↔ 515 线 ⇒ 3.10 卡到 5.15 卡 3 跳可达\n", True,
     "★ 线号/版本号不是量：3.10 卡 · 5.15 卡 不得误报（但 3 跳 是真数字）"),
    ("当前 v4 卡片体系下的迁移规则\n", False, "★ 版本前缀 v4 不得被当成「4 卡」"),
]


def self_test():
    import tempfile
    fail = 0
    for text, should_hit, why in SELF_TEST:
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "SCHEMA.md"), "w", encoding="utf-8").write(text)
            hit = bool(audit(d)[0])
        ok = hit == should_hit
        exp = "报出" if should_hit else "放行"
        print(f"  {'✓' if ok else '✗'} {why}：{'报出' if hit else '放行'}"
              + ("" if ok else f"（期望{exp}）"))
        fail += 0 if ok else 1
    print(f"自检：{len(SELF_TEST)} 组，" + ("全部通过" if not fail else f"{fail} 项失败"))
    return 1 if fail else 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    root = os.path.expanduser(argv[0]) if argv else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bad, hints = audit(root)
    print(f"数字审计：{root}")
    for b in bad:
        print(f"  ✗ {b}")
    if hints:
        print(f"\n  提示（模糊量词，不判失败——若这里原本是具体数字，请改回并补口径行）：")
        for h in hints:
            print(f"    · {h}")
    if bad:
        print(f"\n{len(bad)} 处裸数字 —— 补一行「口径：…（YYYY-MM-DD 实测）」，"
              "或属结构性计数/操作返回则加进 STRUCT")
        return 1
    print("  合规：每个实测数字所在块都有「口径 + 日期」行 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
