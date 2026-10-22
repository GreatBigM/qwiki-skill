#!/usr/bin/env python3
"""qwiki 核心测试 —— 把 check / sync 的守卫边界钉成断言（守卫一条用例）。

用法:  python3 qwiki-tests.py            # 全部跑一遍
       python3 qwiki-tests.py -v         # 附带每条用例的实际输出
退出码: 0 = 全过；1 = 有失败

为什么不用「文本 golden」：
  check / sync 的输出里带绝对路径与计数，逐字 golden 每换一台机器就红。这里断言的是
  **可判定的口径**——退出码、报错串（用户看到的那句话）、落盘后的文件内容。口径变了
  用例就该红，路径变了不该。

本文件同时是「红线」的守门人：**INDEX 入口错 → 退出码 1；规格项 → 退出码 0**。
谁以后把规格接进入口错误（或反过来），用例立刻红。

覆盖：
  基线全绿 / 缺 `>` 引言行 / 出处首行 / 空段补表头 / `|` 拒绝写表 / 段头错位 / 表体断裂 /
  PyYAML 缺库 / 幂等 / H1≠title / 出处行不覆盖总结 / `--all` / `sync --strict` /
  死链 / 漏登记 / 规格不红（含 --strict）/ 账本三态（入账 → 存量 → 销账）

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
SEARCH = HERE / "qwiki-search.py"
PY = sys.executable

CARD = """---
title: {title}
type: note
date: 2026-10-22
tags: {tags}
---

# {h1}

{body}
"""

GOOD_BODY = "> 结论\n\n> 依据：fixture\n"
FACET_TAGS = "[项目/personal, 模块/wifi, 关键词1/甲, 关键词2/乙]"   # 合规的三面标签

INDEX_HEAD = "| 标题 | 总结 | 文件 | 分类 |\n|------|------|------|------|"


def card(title="卡片标题", h1=None, body=GOOD_BODY, tags="[]"):
    return CARD.format(title=title, h1=h1 or title, body=body, tags=tags)


def index(rows, section="personal"):
    """三列旧格式的 fixture 自动补上第四列（分类），避免每处手写。"""
    padded = [r if r.count("|") >= 5 else r.rstrip().rstrip("|").rstrip() + " | - |" for r in rows]
    return f"## {section}\n\n{INDEX_HEAD}\n" + "\n".join(padded) + "\n"


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
    """基线：合规卡 + 合规 INDEX 必须可用（没有这条，后面的红都可能是"本来就红"）。"""
    root = make_kb(tmp, {"personal/card.md": card()},
                   index(["| 卡片标题 | 结论 | personal/card.md |"]))
    rc, out = run(CHECK, root)
    # 不断言「无 PyYAML 也可」以外的措辞：机器缺 PyYAML 时只影响「其他」栏
    return rc == 0 and "INDEX 入口   ✓" in out, f"rc={rc}"


def case_missing_quote(tmp):
    """缺 `>` 引言行：只算规格（不红）；sync 不得覆盖已有总结。"""
    root = make_kb(tmp, {"personal/card.md": card(body="只有正文，没有引文块。\n")},
                   index(["| 卡片标题 | 结论 | personal/card.md |"]))
    rc, out = run(CHECK, root)
    spec = rc == 0 and "不是 `>` 引言行" in out and "INDEX 入口   ✓" in out
    _, out2 = run(SYNC, root, "--write")
    kept = "| 卡片标题 | 结论 | personal/card.md |" in read(root) and "没有 `>` 引文块" in out2
    return spec and kept, f"rc={rc} / sync 保留原总结={kept}"


def case_prov_first(tmp):
    """出处首行：识别得出「首行是出处/状态」，但算规格项，不阻断。"""
    root = make_kb(tmp, {"personal/card.md": card(body="> 依据：2026-10-22 实测\n")},
                   index(["| 卡片标题 | 依据：2026-10-22 实测 | personal/card.md |"]))
    rc, out = run(CHECK, root)
    return rc == 0 and "首行是出处/状态" in out, f"rc={rc}"


def case_empty_section(tmp):
    """空段补表头：sync 往没有表的 `## personal` 里补登记，须连表头与分隔行一起补。"""
    root = make_kb(tmp, {"personal/card.md": card()}, "## personal\n")
    _, out = run(SYNC, root, "--write")
    text = read(root)
    ok = (INDEX_HEAD in text and "|------|------|------|" in text
          and "| 卡片标题 | 结论 | personal/card.md |" in text)
    rc, _ = run(CHECK, root)
    return ok and rc == 0, f"补表头={ok} / 事后体检 rc={rc}"


def case_pipe_title(tmp):
    """`|` 标题：撑破表格的行宁可不写（转人工），不许产出 4 列坏行。"""
    root = make_kb(tmp, {"personal/card.md": card(title="含|管道")},
                   index(["| 旧标题 | 结论 | personal/card.md |"]))
    before = read(root)
    _, out = run(SYNC, root, "--write")
    after = read(root)
    no_broken = after == before and len([l for l in after.split("\n")
                                         if l.startswith("|") and l.count("|") > 5]) == 0
    return no_broken and "含 `|`" in out, f"INDEX 未变={after == before}"


def case_section_mismatch(tmp):
    """段头错位（硬）：卡片在 projects/alpha 下却登记在 `## personal` → 退出码 1。"""
    root = make_kb(tmp, {"projects/alpha/card.md": card()},
                   index(["| 卡片标题 | 结论 | alpha/card.md |"], section="personal"))
    rc, out = run(CHECK, root)
    return rc == 1 and "与卡片路径不符" in out, f"rc={rc}"


def case_table_break(tmp):
    """表体断裂（硬）：数据行后再出现分隔行 → 退出码 1。"""
    rows = ["| 卡片标题 | 结论 | personal/card.md |", "|------|------|------|"]
    root = make_kb(tmp, {"personal/card.md": card()}, index(rows))
    rc, out = run(CHECK, root)
    return rc == 1 and "分隔行出现在数据行之后" in out, f"rc={rc}"


def case_yaml_skip(tmp):
    """PyYAML 缺库：标「未验证」而不是冒充通过（-S 屏蔽 site-packages）。"""
    root = make_kb(tmp, {"personal/card.md": card()},
                   index(["| 卡片标题 | 结论 | personal/card.md |"]))
    rc, out = run(CHECK, root, flags=("-S",))
    return rc == 0 and "未验证" in out, f"rc={rc}"


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
    """H1 ≠ title：规格项，不阻断（旧卡不该因此变红）。"""
    root = make_kb(tmp, {"personal/card.md": card(h1="另一个标题")},
                   index(["| 卡片标题 | 结论 | personal/card.md |"]))
    rc, out = run(CHECK, root)
    return rc == 0 and "正文 H1 ≠ YAML title" in out, f"rc={rc}"


def case_summary_preserved(tmp):
    """出处/状态行不覆盖总结：sync 只报告，不把 INDEX 里的旧结论换成状态行。"""
    body = "> 状态：已闭环 · 2026-10-22\n\n> 依据：fixture\n"
    root = make_kb(tmp, {"personal/card.md": card(body=body)},
                   index(["| 卡片标题 | 旧结论 | personal/card.md |"]))
    _, out = run(SYNC, root, "--write")
    kept = "| 卡片标题 | 旧结论 | personal/card.md |" in read(root)
    return kept and "首行是出处/状态" in out, f"总结保留={kept}"


def case_all_flag(tmp):
    """`--all`：默认截断并提示「另 N 条」，--all 打全量（否则大库只能另写脚本捞）。"""
    cards = {f"personal/card-{i}.md": card(title=f"卡{i}", h1=f"另一标题{i}", tags=FACET_TAGS)
             for i in range(25)}
    rows = [f"| 卡{i} | 结论 | personal/card-{i}.md |" for i in range(25)]
    root = make_kb(tmp, cards, index(rows))
    rc, out = run(CHECK, root)
    truncated = rc == 0 and "另 5 条" in out
    rc2, out2 = run(CHECK, root, "--all")
    full = rc2 == 0 and "… 另" not in out2 and out2.count("正文 H1 ≠ YAML title") == 25
    return truncated and full, f"默认截断={truncated} / --all 全量={full}"


def case_strict(tmp):
    """`sync --strict`：需人判 > 0 时退出码 2（打印了却 exit 0，CI 等于没报）。"""
    root = make_kb(tmp, {"personal/card.md": card(body="只有正文。\n")},
                   index(["| 卡片标题 | 结论 | personal/card.md |"]))
    rc_plain, _ = run(SYNC, root, "--write")
    rc_strict, out = run(SYNC, root, "--write", "--strict")
    return rc_plain == 0 and rc_strict == 2 and "--strict" in out, \
        f"默认 rc={rc_plain} / --strict rc={rc_strict}"


def case_dead_link(tmp):
    """死链（硬）：INDEX 行指向不存在的文件 → 退出码 1，且点名文件列。"""
    root = make_kb(tmp, {"personal/card.md": card()},
                   index(["| 卡片标题 | 结论 | personal/card.md |",
                          "| 幽灵卡 | 幽灵结论 | personal/ghost.md |"]))
    rc, out = run(CHECK, root)
    return rc == 1 and "死链" in out and "ghost.md" in out, f"rc={rc}"


def case_missing_registration(tmp):
    """漏登记（硬）：卡在库里但 INDEX 没有入口 → 退出码 1（知识在但找不到）。"""
    root = make_kb(tmp, {"personal/card.md": card()}, index([]))
    rc, out = run(CHECK, root)
    return rc == 1 and "无登记行" in out, f"rc={rc}"


def case_spec_never_red(tmp):
    """规格项永不默认报红：命名违规 → rc 0；只有 --strict 才 2。"""
    root = make_kb(tmp, {"personal/Bad_Name.md": card()},
                   index(["| 卡片标题 | 结论 | personal/Bad_Name.md |"]))
    rc, out = run(CHECK, root)
    soft = rc == 0 and "规格" in out and "INDEX 入口   ✓" in out
    rc2, _ = run(CHECK, root, "--strict")
    return soft and rc2 == 2, f"默认 rc={rc} / --strict rc={rc2}"


def case_ledger(tmp):
    """账本三态：--baseline 入账 → 再体检算存量（strict 也不红）→ 修好后销账。"""
    root = make_kb(tmp, {"personal/card.md": card(h1="另一个标题", tags=FACET_TAGS)},
                   index(["| 卡片标题 | 结论 | personal/card.md |"]))
    _, out_new = run(CHECK, root)
    new_seen = "新增 1" in out_new
    run(CHECK, root, "--baseline")
    ledger = os.path.exists(os.path.join(root, ".qwiki-maintenance.json"))
    _, out_old = run(CHECK, root)
    stock = ledger and "存量 1 ／ 新增 0" in out_old
    rc_strict, _ = run(CHECK, root, "--strict")
    (root / "personal/card.md").write_text(card(tags=FACET_TAGS), encoding="utf-8")   # 修好那张卡
    _, out_fix = run(CHECK, root, "--baseline")
    empty = '"baseline": {}' in read(root, ".qwiki-maintenance.json")
    return new_seen and stock and rc_strict == 0 and empty, \
        f"入账={new_seen}/{ledger} 存量={stock} strict rc={rc_strict} 销账={empty}"


def case_search_rank(tmp):
    """检索排序：命中的卡排第一（索引自动构建，无需预先准备）。"""
    cards = {
        "personal/alpha.md": card(title="RX 聚合为何不生效", body="> RX 聚合从未生效\n\n> 依据：fixture\n\n## 证据\n聚合分支是死代码。\n"),
        "personal/beta.md": card(title="串口烧录手册", body="> TFTP 烧录三步\n\n> 依据：fixture\n"),
    }
    rows = ["| RX 聚合为何不生效 | RX 聚合从未生效 | personal/alpha.md |",
            "| 串口烧录手册 | TFTP 烧录三步 | personal/beta.md |"]
    root = make_kb(tmp, cards, index(rows))
    rc, out = run(SEARCH, root, "RX 聚合", "--json")
    import json as _json
    data = _json.loads(out)
    first = data["results"][0]["path"] if data["results"] else None
    return rc == 0 and first == "personal/alpha.md", f"rc={rc} top={first}"


def case_search_cjk(tmp):
    """中文二元组：只出现在一张卡里的词要能命中，且不误召回全库。"""
    cards = {
        "personal/one.md": card(title="零拷贝证伪", body="> 微基准证伪零拷贝\n\n> 依据：fixture\n"),
        "personal/two.md": card(title="内存预算", body="> zram 与 swap 分离\n\n> 依据：fixture\n"),
    }
    rows = ["| 零拷贝证伪 | 微基准证伪零拷贝 | personal/one.md |",
            "| 内存预算 | zram 与 swap 分离 | personal/two.md |"]
    root = make_kb(tmp, cards, index(rows))
    rc, out = run(SEARCH, root, "零拷贝", "--json")
    import json as _json
    data = _json.loads(out)
    paths = [r["path"] for r in data["results"]]
    return rc == 0 and paths[:1] == ["personal/one.md"] and "personal/two.md" not in paths, \
        f"rc={rc} hits={paths}"


def case_search_body_only(tmp):
    """正文独有词：不在标题/结论里，也必须能被召回（靠 rg 扫正文）。"""
    body = "> 结论很短\n\n> 依据：fixture\n\n奇美拉词只在正文出现一次。\n"
    root = make_kb(tmp, {"personal/card.md": card(body=body)},
                   index(["| 卡片标题 | 结论很短 | personal/card.md |"]))
    rc, out = run(SEARCH, root, "奇美拉", "--json")
    import json as _json
    data = _json.loads(out)
    hit = [r for r in data["results"] if r["path"] == "personal/card.md"]
    return rc == 0 and bool(hit) and hit[0]["body"] is True, f"rc={rc} hits={len(data['results'])}"


def case_search_no_hit(tmp):
    """零命中：退出码 0 + 明确提示（空结果不是错误）。"""
    root = make_kb(tmp, {"personal/card.md": card()},
                   index(["| 卡片标题 | 结论 | personal/card.md |"]))
    rc, out = run(SEARCH, root, "完全不存在的词组", "--json")
    import json as _json
    data = _json.loads(out)
    return rc == 0 and data["results"] == [], f"rc={rc} n={len(data['results'])}"


def case_search_tag(tmp):
    """`--tag` 一级过滤：只在该标签的卡里找；无标签可筛时不报错、不误召回。"""
    cards = {
        "personal/a.md": card(title="甲 聚合生效",
                              tags="[项目/personal, 模块/wifi, 关键词1/聚合, 关键词2/生效]",
                              body="> 聚合生效\n\n> 依据：fixture\n"),
        "personal/b.md": card(title="乙 内存回收",
                              tags="[项目/personal, 模块/内存, 关键词1/内存, 关键词2/回收]",
                              body="> 内存回收\n\n> 依据：fixture\n"),
    }
    rows = ["| 甲 聚合生效 | 聚合生效 | personal/a.md | personal/wifi/- |",
            "| 乙 内存回收 | 内存回收 | personal/b.md | personal/内存/- |"]
    root = make_kb(tmp, cards, index(rows))
    import json as _json
    only_tag = _json.loads(run(SEARCH, root, "--module", "内存", "--json")[1])
    tagged_q = _json.loads(run(SEARCH, root, "回收", "--module", "内存", "--json")[1])
    none = _json.loads(run(SEARCH, root, "--module", "不存在", "--json")[1])
    ok = ([r["path"] for r in only_tag["results"]] == ["personal/b.md"]
          and [r["path"] for r in tagged_q["results"]] == ["personal/b.md"]
          and none["results"] == [])
    return ok, f"仅标签={len(only_tag['results'])} 标签+词={len(tagged_q['results'])} 未知标签={len(none['results'])}"


def case_tag_facets(tmp):
    """标签三面（规格）：项目与路径不符 / 缺二级关键词都报出来，但不阻断（rc 0）。"""
    wrong = card(title="标签错卡", tags="[项目/nope, 模块/wifi, 关键词1/甲]")
    root = make_kb(tmp, {"personal/bad.md": wrong},
                   index(["| 标签错卡 | 结论 | personal/bad.md |"]))
    rc, out = run(CHECK, root)
    return (rc == 0 and "与路径不符" in out and "缺关键词2" in out), f"rc={rc}"


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
    case_all_flag,
    case_strict,
    case_dead_link,
    case_missing_registration,
    case_spec_never_red,
    case_ledger,
    case_search_rank,
    case_search_cjk,
    case_search_body_only,
    case_search_no_hit,
    case_search_tag,
    case_tag_facets,
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
        print(f"  {'✓' if ok else '✗'} {fn.__name__:<26s} {name}")
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
