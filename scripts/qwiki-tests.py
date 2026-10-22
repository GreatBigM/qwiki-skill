#!/usr/bin/env python3
"""qwiki 核心测试 —— 把 check / sync 的守卫边界钉成断言（守卫一条用例）。

用法:  python3 qwiki-tests.py            # 全部跑一遍
       python3 qwiki-tests.py -v         # 附带每条用例的实际输出
退出码: 0 = 全过；1 = 有失败

为什么不用「文本 golden」：
  check / sync 的输出里带绝对路径与计数，逐字 golden 每换一台机器就红。这里断言的是
  **可判定的口径**——退出码、报错串（用户看到的那句话）、落盘后的文件内容。口径变了
  用例就该红，路径变了不该。

覆盖的边界（每条都对应一次真实踩坑或一条守卫）：
  基线全绿 / 缺 `>` 引言行 / 出处首行 / 空段补表头 / `|` 拒绝写表 /
  段头错位 / 表体断裂 / PyYAML 缺库标跳过 / 幂等 / H1≠title / 出处行不覆盖总结

接进发布闸门：`scripts/hooks/pre-push` 第一步就验它（守卫坏了，后面的"通过"不作数）。
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECK = HERE / "qwiki-check.py"
SYNC = HERE / "qwiki-sync.py"
PY = sys.executable

CARD = """---
title: {title}
type: note
date: 2026-10-22
---

# {h1}

{body}
"""

GOOD_BODY = "> 结论\n\n> 依据：fixture\n"

INDEX_HEAD = "| 标题 | 总结 | 文件 |\n|------|------|------|"


def card(title="卡片标题", h1=None, body=GOOD_BODY):
    return CARD.format(title=title, h1=h1 or title, body=body)


def index(rows, section="personal"):
    body = "\n".join(rows)
    return f"## {section}\n\n{INDEX_HEAD}\n{body}\n"


def make_kb(tmp, cards, index_text):
    root = Path(tmp)
    for rel, text in cards.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    (root / "INDEX.md").write_text(index_text, encoding="utf-8")
    return root


def run(script, root, *args, flags=()):
    proc = subprocess.run([PY, *flags, str(script), str(root), *args],
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def read(root, rel="INDEX.md"):
    return (Path(root) / rel).read_text(encoding="utf-8")


# ── 用例：每个返回 (通过?, 说明) ─────────────────────────────────────

def case_baseline(tmp):
    """基线：合规卡 + 合规 INDEX 必须全绿（没有这条，后面的红都可能是"本来就红"）。"""
    root = make_kb(tmp, {"personal/card.md": card()},
                   index(["| 卡片标题 | 结论 | personal/card.md |"]))
    rc, out = run(CHECK, root)
    return rc == 0 and "全部通过" in out, f"rc={rc}"


def case_missing_quote(tmp):
    """缺 `>` 引言行：check 报红；sync 不得覆盖已有总结（没有结论不是"空"，是"没写"）。"""
    root = make_kb(tmp, {"personal/card.md": card(body="只有正文，没有引文块。\n")},
                   index(["| 卡片标题 | 结论 | personal/card.md |"]))
    rc, out = run(CHECK, root)
    hit = rc == 1 and "不是 `>` 引言行" in out
    _, out2 = run(SYNC, root, "--write")
    kept = "| 卡片标题 | 结论 | personal/card.md |" in read(root) and "没有 `>` 引文块" in out2
    return hit and kept, f"check rc={rc} / sync 保留原总结={kept}"


def case_prov_first(tmp):
    """出处首行：check 必须认出「首行是出处/状态」而不是把出处当结论。"""
    root = make_kb(tmp, {"personal/card.md": card(body="> 依据：2026-10-22 实测\n")},
                   index(["| 卡片标题 | 依据：2026-10-22 实测 | personal/card.md |"]))
    rc, out = run(CHECK, root)
    return rc == 1 and "H1 后首行是出处/状态" in out, f"rc={rc}"


def case_empty_section(tmp):
    """空段补表头：sync 往没有表的 `## personal` 里补登记，须连表头与分隔行一起补。"""
    root = make_kb(tmp, {"personal/card.md": card()}, "## personal\n")
    _, out = run(SYNC, root, "--write")
    text = read(root)
    ok = (INDEX_HEAD in text and "|------|------|------|" in text
          and "| 卡片标题 | 结论 | personal/card.md |" in text)
    rc, out2 = run(CHECK, root)
    return ok and rc == 0, f"补表头={ok} / 事后自检 rc={rc} / {out.strip().splitlines()[-1] if out.strip() else ''}"


def case_pipe_title(tmp):
    """`|` 标题：撑破表格的行宁可不写（转人工），不许产出 4 列坏行。"""
    root = make_kb(tmp, {"personal/card.md": card(title="含|管道")},
                   index(["| 旧标题 | 结论 | personal/card.md |"]))
    before = read(root)
    _, out = run(SYNC, root, "--write")
    after = read(root)
    no_broken = after == before and len([l for l in after.split("\n")
                                         if l.startswith("|") and l.count("|") > 4]) == 0
    return no_broken and "含 `|`" in out, f"INDEX 未变={after == before}"


def case_section_mismatch(tmp):
    """段头错位：卡片在 projects/alpha 下，登记在 `## personal` 必须报出来。"""
    root = make_kb(tmp, {"projects/alpha/card.md": card()},
                   index(["| 卡片标题 | 结论 | alpha/card.md |"], section="personal"))
    rc, out = run(CHECK, root)
    return rc == 1 and "与卡片路径不符" in out, f"rc={rc}"


def case_table_break(tmp):
    """表体断裂：数据行后再出现分隔行，必须报（否则表格会被后加的段落解析成两张）。"""
    rows = ["| 卡片标题 | 结论 | personal/card.md |", "|------|------|------|"]
    root = make_kb(tmp, {"personal/card.md": card()}, index(rows))
    rc, out = run(CHECK, root)
    return rc == 1 and "分隔行出现在数据行之后" in out, f"rc={rc}"


def case_yaml_skip(tmp):
    """PyYAML 缺库：YAML 项标「跳过」并计入未验证，不许冒充通过（-S 屏蔽 site-packages）。"""
    root = make_kb(tmp, {"personal/card.md": card()},
                   index(["| 卡片标题 | 结论 | personal/card.md |"]))
    rc, out = run(CHECK, root, flags=("-S",))
    skipped = ("⊘ YAML 头可解析" in out
               and ("1 项跳过" in out or "项跳过（未验证）" in out))
    return rc == 0 and skipped, f"rc={rc} / 跳过标记={skipped}"


def case_idempotent(tmp):
    """幂等：sync --write 连跑两次，第二次 0 修正且 INDEX 逐字节不变。"""
    root = make_kb(tmp, {"personal/card.md": card()},
                   index(["| 卡片标题 | 结论 | personal/card.md |"]))
    run(SYNC, root, "--write")
    first = read(root)
    _, out2 = run(SYNC, root, "--write")
    second = read(root)
    clean = "标题列修正 0 ｜ 总结列修正 0 ｜ 文件列归一 0" in out2
    return first == second and clean, f"二次 0 修正={clean} / 字节一致={first == second}"


def case_h1_mismatch(tmp):
    """H1 ≠ title：投影与正文标题是同一个字符串，漂移必须报。"""
    root = make_kb(tmp, {"personal/card.md": card(h1="另一个标题")},
                   index(["| 卡片标题 | 结论 | personal/card.md |"]))
    rc, out = run(CHECK, root)
    return rc == 1 and "正文 H1 ≠ YAML title" in out, f"rc={rc}"


def case_summary_preserved(tmp):
    """出处/状态行不覆盖总结：sync 只报告，不把 INDEX 里的旧结论换成长辈状态行。"""
    body = "> 状态：已闭环 · 2026-10-22\n\n> 依据：fixture\n"
    root = make_kb(tmp, {"personal/card.md": card(body=body)},
                   index(["| 卡片标题 | 旧结论 | personal/card.md |"]))
    _, out = run(SYNC, root, "--write")
    kept = "| 卡片标题 | 旧结论 | personal/card.md |" in read(root)
    return kept and "首行是出处/状态" in out, f"总结保留={kept}"


CASES = [
    case_baseline,
    case_missing_quote,
    case_prov_first,
    case_empty_section,
    case_pipe_title,
    case_section_mismatch,
    case_table_break,
    case_yaml_skip,
    case_idempotent,
    case_h1_mismatch,
    case_summary_preserved,
]


def main(argv):
    verbose = "-v" in argv or "--verbose" in argv
    print(f"qwiki 核心测试：{len(CASES)} 个 fixture\n")
    failed = 0
    for fn in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                ok, detail = fn(tmp)
            except Exception as exc:  # 用例自身炸了也算失败，不能静默
                ok, detail = False, f"{type(exc).__name__}: {exc}"
        failed += not ok
        name = fn.__doc__.strip().split("\n")[0]
        print(f"  {'✓' if ok else '✗'} {fn.__name__:<24s} {name}")
        if verbose or not ok:
            print(f"      {detail}")
    print()
    if failed:
        print(f"{failed} 个用例失败 —— 守卫或口径被改了，先查上面标 ✗ 的那条")
        return 1
    print(f"全部通过（{len(CASES)} / {len(CASES)}）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
