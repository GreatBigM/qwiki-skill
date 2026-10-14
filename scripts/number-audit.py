#!/usr/bin/env python3
"""qwiki 数字审计 —— 宪法与对外文档里不得出现**实测数字**。

CURRENT: 宪法与对外文档（SCHEMA.md / README.md / SKILL.md）不得含实测数字 —— 本文件是模型与判据，不对具体实例负责；实例的账由实例回答（`qwiki-check.py` 的输出），设计论证用公式表达。模型常量（项 / 页 / 字符 / ≤N 跳 / 区间 / 公式变量）与操作返回（0 条 / 1 条）不计。

用法:
    python3 number-audit.py [仓库根]      # 默认 = 本脚本上一级
    python3 number-audit.py --self-test   # 逐数字比对的正反样本
退出码: 0 = 全部合规；1 = 有裸数字

**为什么改判据（2026-10-14，v2.12.3）**：旧判据是「实测数字必须带口径 + 日期」，连立三轮规则、
还配了机器闸门（含语义核指纹 / --seal 重签 / --parity 描述同步），**仍实测出"同一天内 190→191"的错值**
——因为闸门只能验"有没有标注"，验不了"数字是否仍然为真"。根因不是标注缺失，是**实例的账记在了宪法里**：
SCHEMA 是抽象模型，"当前库有多少卡"本就不该由它负责。⇒ 判据换成职责边界：**样本出库**。
（旧机制一并退役：语义核指纹只能证明"改过并已显式重签"，不能证明"描述写对了"；判据收成一句话后，
描述同步的义务本身就不存在了。）

判定（确定性，不做邻近度近似）:
    扫描 SCHEMA.md / README.md / SKILL.md 的**非代码围栏**行，去掉行内代码后找「数字 + 计数单位」。
    命中即违规，除非属下列模型常量：
      ① 有边界限定词：紧邻前置 `≥ ≤ < > 至少 最多 最少 至多 约 超过`，或区间 `1-3 个`
      ② 单位是模型自身的量：`项` / `页` / `字符` / `次/时`（如 `11 项断言` / `5 页` / `≤80 字符`）
      ③ 操作 / 查询返回：`0 条` / `1 条`（有无判断，不是测量）
    由**单位表**排除标识符：`310 线` / `3.10 卡` / `v2.10.0` 这类不是数量（它们没有计数单位）。
"""
import os
import re
import sys

SCAN = ["SCHEMA.md", "README.md", "SKILL.md"]

# 实测数字：整数 + 计数单位，或 占比 / 倍数（允许小数），或 N/M（两侧各 ≥2 位）
# 前置负向断言排除 `−`（U+2212 减号，如 `n−1 张` 是公式不是数量）
NUM = re.compile(
    r"(?<![\w.−])\d+\s*(?:张|条|行|处|跳|个|次|位|对|卡|倍)"
    r"|(?<![\w.−])\d+(?:\.\d+)?\s*(?:%|×)"
    r"|(?<![\w.−])\d{2,}\s*/\s*\d{2,}"
)
QUAL = re.compile(r"(?:≥|≤|<|>|至少|最多|最少|至多|约|超过)[^，。；]{0,6}$|[-–]\s*$")
STRUCT_UNITS = ("项", "页", "字符")


def mask_code(text):
    """→ (行列表, 每行是否在代码围栏内)。"""
    raw, code, in_code = [], [], False
    for ln in text.split("\n"):
        fence = ln.lstrip().startswith("```")
        if fence:
            in_code = not in_code
        raw.append(ln)                            # 逐行对齐，行号 = 真实行号
        code.append(in_code or fence)
    return raw, code


def model_constant(m, line):
    """→ None（真数字）| "bound"（边界限定 / 区间）| "structural"（模型自身的量）。"""
    pre = line[max(0, m.start() - 12):m.start()]
    if QUAL.search(pre):
        return "bound"
    tok = m.group(0).rstrip()
    if tok.endswith(STRUCT_UNITS) or re.match(r"\s*/\s*时", line[m.end():m.end() + 3]):
        return "structural"                      # 11 项 / 5 页 / ≤80 字符 / 60 次/时（外部平台常量）
    if tok.endswith("条") and re.match(r"\d+", tok).group(0) in ("0", "1"):
        return "structural"                      # 操作 / 查询返回（有无判断）
    return None


def audit(root):
    bad = []
    for name in SCAN:
        path = os.path.join(root, name)
        if not os.path.exists(path):
            continue
        raw, code = mask_code(open(path, encoding="utf-8").read())
        for i, ln in enumerate(raw):
            if code[i]:
                continue
            line = re.sub(r"`[^`]*`", "", ln)    # 行内代码不算
            for m in NUM.finditer(line):
                if model_constant(m, line) is None:
                    bad.append((name, i + 1, m.group(0).strip(), ln.strip()[:70]))
    return bad


SELF_TEST = [
    # 违规
    ("| 卡 | 61 张同属这条线 |\n", {"61 张"}, "带单位实测数字"),
    ("全库 190 卡\n", {"190 卡"}, "带单位实测数字（全库规模）"),
    ("同族两卡 93% 靠中转\n", {"93%"}, "占比"),
    ("省 30×\n", {"30×"}, "倍数"),
    ("回链 95/95 全绿\n", {"95/95"}, "两位 N/M"),
    ("| 表格里的 45 个数字 |\n", {"45 个"}, "表格单元格（无口径可依，同样违规）"),
    ("- 某段 86 张卡\n", {"86 张"}, "列表项里的样本"),
    # 放行
    ("- 结构分层 / 跨 ≥2 组件 / ≥3 步流转 → 必给图\n", set(), "边界限定词（≥）"),
    ("- 每张轨迹卡至少 1 张聚合卡\n", set(), "边界限定词（至少）"),
    ("- 一次 1-3 个模块\n", set(), "区间"),
    ("- 共 11 项断言，每会话 ≤5 页\n", set(), "模型自身的量（项 / 页）"),
    ("- 匿名 API 限流 60 次/时 → 5000 次/时\n", set(), "外部平台常量（次/时）"),
    ("- 窗口内 0 条 delegate_task 判为陈旧标记\n", set(), "操作 / 查询返回"),
    ("- 直链 n(n−1) 行 vs 聚合 2n 行 ⇒ 比值 ≈ n/2\n", set(), "公式变量（无计数单位）"),
    ("- 版本前缀 v2.10.0 与线名 310 线 / 3.10 卡 不是数量\n", set(), "标识符（线号 / 版本号）"),
    ("```\n全库 190 卡\n```\n", set(), "代码围栏内不扫"),
    ("- 行内 `95/95` 不算\n", set(), "行内代码不算"),
    ("- 每张卡列其余 n−1 张 = n(n−1) 行\n", set(), "公式变量（n−1 张 里的减号）"),
]
NUMSTR = re.compile(r"「([^」]+)」")


def self_test():
    import tempfile
    fail = 0
    for text, expect, why in SELF_TEST:
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "SCHEMA.md"), "w", encoding="utf-8").write(text)
            got = {t for _, _, t, _ in audit(d)}
        ok = got == expect
        print(f"  {'✓' if ok else '✗'} {why}：报出 {sorted(got) or '（无）'}"
              + ("" if ok else f"（期望 {sorted(expect) or '（无）'}）"))
        fail += 0 if ok else 1
    print(f"自检：{len(SELF_TEST)} 组，" + ("全部通过" if not fail else f"{fail} 项失败"))
    return 1 if fail else 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    root = os.path.expanduser(argv[0]) if argv and not argv[0].startswith("-") \
        else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bad = audit(root)
    print(f"数字审计：{root}")
    for name, ln, tok, ctx in bad:
        print(f"  ✗ {name}:{ln} 实测数字「{tok}」—— {ctx}")
    if bad:
        print(f"\n{len(bad)} 处实测数字 —— 宪法与对外文档只放模型与判据："
              "样本挪进知识库的卡，或改写成公式 / 限定陈述（≥N / ≤N 这类模型常量不算）")
        return 1
    print("  合规：无实测数字（模型常量不计）✓")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
