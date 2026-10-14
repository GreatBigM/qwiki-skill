#!/usr/bin/env python3
"""qwiki 数字审计 —— 宪法与对外文档里的实测数字必须带「口径 + 日期」。

用法:  python3 number-audit.py [仓库根]        # 默认 = 本脚本上一级
退出码: 0 = 全部合规；1 = 发现裸数字（可直接串进 pre-push / CI）

**为什么要有它（2026-10-14）**：同一条规则（数字必须带口径 + 日期）连立三轮，
每一轮都靠人工 grep 补漏——补 2 处漏 3 处、再补 3 处又漏 1 处，其中一处还是
"日期张冠李戴"（段落定稿日 2026-10-13 被当成数字的测量日）骗过了人眼。
根因与脱敏同构：**规则靠人记必然回潮**，所以它得是机器判的。

判定：一行里出现实测数字（`N%` / `N 张/条/行/处/跳/个/次` / `N/M`）时，
**同一行或上一行**必须出现「口径」「实测」或 `YYYY-MM-DD`；否则报裸数字。
结构性计数（八段、11 项断言、C(n,2) 里的 n 等）走 ALLOW 白名单豁免。
"""
import os
import re
import sys

SCAN = ["SCHEMA.md", "README.md", "SKILL.md"]
NUM = re.compile(r"\d+(?:\.\d+)?\s*(?:%|张|条|行|处|跳|个|次|位)|\d+\s*/\s*\d+")
CTX = re.compile(r"口径|实测|20\d\d-\d\d-\d\d")
ALLOW = [
    "11 项", "≤80", "80 字符", "5 页", "八段", "九操作", "三工具", "七模板",
    "三面", "三种", "两类", "四个", "四件", "三跳", "C(n", "2n", "n(n", "4 空格",
    "至少", "≥", "≤", "次/时", "1-3 个",
]


def audit(root):
    bad = []
    for name in SCAN:
        path = os.path.join(root, name)
        if not os.path.exists(path):
            continue
        lines = open(path, encoding="utf-8").read().split("\n")
        for i, line in enumerate(lines):
            if not NUM.search(line) or any(a in line for a in ALLOW):
                continue
            ctx = line + (lines[i - 1] if i else "")
            if CTX.search(ctx):
                continue
            for m in NUM.finditer(line):
                bad.append(f"{name}:{i + 1} 裸数字「{m.group(0).strip()}」—— {line.strip()[:70]}")
    return bad


def self_test():
    """种正反样本：裸数字必中、带口径 / 白名单必不中。"""
    import tempfile
    cases = [
        ("| 卡 | 61 张同属这条线 |\n", True, "裸数字（无口径、非结构性）"),
        ("某段 86 张卡（2026-10-14 实测，口径 = 该段 .md 数）\n", False, "带口径 + 日期"),
        ("实测：占比 93%（口径 = C(n,2) 分母）\n", False, "带口径"),
        ("每张轨迹卡的入链里至少应有 1 张聚合卡\n", False, "结构性量词（至少）"),
        ("C(n,2) 里的 n 与 2n 都不算实测数字\n", False, "公式白名单"),
    ]
    fail = 0
    for text, should_hit, why in cases:
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "SCHEMA.md"), "w", encoding="utf-8").write(text)
            hit = bool(audit(d))
        ok = hit == should_hit
        print(f"  {'✓' if ok else '✗'} {why}：{'报出' if hit else '放行'}")
        fail += 0 if ok else 1
    print("自检：全部通过" if not fail else f"自检：{fail} 项失败")
    return 1 if fail else 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    root = os.path.expanduser(argv[0]) if argv else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bad = audit(root)
    print(f"数字审计：{root}")
    for b in bad:
        print(f"  ✗ {b}")
    if bad:
        print(f"\n{len(bad)} 处裸数字 —— 补「口径 + 日期」，或属结构性计数就加进 ALLOW")
        return 1
    print("  合规：实测数字都带口径 / 日期 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
