#!/usr/bin/env python3
"""qwiki 数字审计 —— 宪法与对外文档里不得出现**实测数字**。

CURRENT: 宪法与对外文档（SCHEMA.md / README.md / SKILL.md / templates/*.md / references/*.md）不得含实测数字 —— 它们是模型与判据，不对具体实例负责；实例的账由实例回答（`qwiki-check.py` 的输出），设计论证用公式表达。反引号内同样禁止（不是免检通道），历史叙述里复述旧值同样禁止。不计：模型常量（项 / 页 / 字符 / ≤N 跳 / 区间 / 公式变量）与操作返回（0 条 / 1 条）；排除：CHANGELOG.md（按日期留痕的记录，数字本属正当）。

用法:
    python3 number-audit.py [仓库根]      # 默认 = 本脚本上一级
    python3 number-audit.py --self-test   # 逐数字比对的正反样本（按缺陷类别组织）
退出码: 0 = 全部合规；1 = 有裸数字

**为什么改判据（2026-10-14，v2.12.3）**：旧判据是「实测数字必须带口径 + 日期」，连立数轮规则、
还配了机器闸门（含语义核指纹 / --seal 重签 / --parity 描述同步），**仍实测出"同一天内同一规模两个值"**——
因为闸门只能验"有没有标注"，验不了"数字是否仍然为真"。根因不是标注缺失，是**实例的账记在了宪法里**：
SCHEMA 是抽象模型，"当前库有多少卡"本就不该由它负责。⇒ 判据换成职责边界：**样本出库**。

判定（确定性，不做邻近度近似）:
    扫**随安装下发的对外件**（枚举见上方 `CURRENT:`，此处不重复——副本越多越会漂）的
    **非代码围栏**行，找「数字 + 计量单位」。命中即违规，除非属下列模型常量：
      ① 有边界限定词：紧邻前置 `≥ ≤ < > 至少 最多 最少 至多`，或区间 `1-3 个` / `1 至 3 个`
         （`约` / `超过` **不算**——那是把样本糊化，不是模型常量；连字符须**紧随数字**才是区间，
         行首列表符 `- 190 张卡` 不算）
      ② 单位是模型自身的量：`项` / `页` / `字符`（不进单位表 ⇒ 天然不计，无分支）
      ③ 操作 / 查询返回：`0 条` / `1 条`（有无判断，不是测量）

已知边界（有意，不是缺陷）:
    · **代码围栏（```）内不扫**：那里是 shell / 配置举例（版本、超时、命令行参数），数字是语法不是论断。
      代价：样本可以藏进围栏——接受，因为围栏是"贴出来的代码"，不是论述。
    · **反引号内**（单个 `）**照扫**：实测过「规模 `190 张卡`」零成本绕过旧版，故不是免检通道。
    · **中文数字抓不到**（`三轮` / `七成` / `九成` 里的数字不是阿拉伯数字）：把样本糊成中文数字即绕过。
      这是闸门已知盲区——堵它得把中文数词也建模，代价远大于收益（而且模糊措辞本来就是合法中文）。
      约束交回规则本身：宪法里不许有实例样本，**写的时候**就别写，别指望闸门。
    · **值转移 / 区间同形**：`190–191`（复述旧值）与 `1–3 个`（区间）、`190 至 191` 与 `1 至 3 个`
      写法完全同形 ⇒ 按"后随是不是计量单位"区分。残留下的口子：**带单位的至式复述**
      （`190 至 191 张`）会被当成区间放过；汉语谓词式（`从 190 涨到 191`）同理。
      真正管住它们的是规则本身。
    · **版本号 / 线号**由单位表天然排除（`v2.10.0`、`310 线`、`3.10 卡` 都不是数量）。
    · **计数类单位只认整数**（小数只对时间 / 体积这类计量单位开口子）：否则 `3.10 卡` 会被当读数。
      代价：`1.5 个` 漏报——可接受，计数类本来就少用小数。
"""
import glob
import os
import re
import sys

SCAN = ["SCHEMA.md", "README.md", "SKILL.md"]
SCAN_GLOB = ["templates/*.md", "references/*.md"]

# 单位表**只有这一份**：按"允不允许小数"分成计数 / 计量两张，判别器要的并集由它们派生
# （判别器曾自带一张小表且漂过——缺时间 / 体积单位，于是 `超时 1 至 3 分钟` 被当成值转移打红。
# 表漂移和副本漂移是同一个病，所以只写一处）
COUNT_UNITS = "张|条|行|处|跳|个|次|位|对|卡|倍|轮|份|度"      # 整数——收了小数会把 `3.10 卡` 当读数
MEASURE_UNITS = "字节|分钟|小时|秒|毫秒|天"                       # 可带小数——`1.6MB` / `0.5s` 是读数常态
ASCII_UNITS = "ms|s|MB|KB|GB|us|ns"
UNITS = COUNT_UNITS + "|" + MEASURE_UNITS                         # 区间判别器用
# `周 / 月 / 年` 有意不收：与日期写法同形（`2026 年 10 月`），收了会把日期打红

# 实测数字：计数单位（整数）/ 计量单位（可带小数）/ 占比 / 倍数 / N/M / N→M 转移
NUM = re.compile(
    r"(?<![\dA-Za-z_.−])\d+\s*(?:%s)" % COUNT_UNITS
    + r"|(?<![\dA-Za-z_.−])\d+(?:\.\d+)?\s*(?:%s)" % MEASURE_UNITS
    + r"|(?<![\dA-Za-z_.−])\d+(?:\.\d+)?\s*(?:%s)(?![\w])" % ASCII_UNITS
    + r"|(?<![\dA-Za-z_.−])\d+(?:\.\d+)?\s*(?:%|×)"
    + r"|(?<![\dA-Za-z_.−])\d{2,}\s*/\s*\d{2,}"
    + r"|(?<![\dA-Za-z_.−])\d+\s*(?:→|–|—|至)\s*\d+"  # 值转移 / 区间（历史复述与 `1 至 3 个` 同形）
)
# 模型常量：边界限定（`约` / `超过` 不在列——它们是把样本糊化的措辞）+ 区间
# 连字符须**紧随数字**才是区间（`1-3 个`），否则行首列表符 `- 190 张卡` 会被当区间整条放行
QUAL = re.compile(r"(?:≥|≤|<|>|至少|最多|最少|至多)[^，。；]{0,6}$|(?<=\d)[-–]\s*$")
# `项 / 页 / 字符` 不进单位表 ⇒ 天然不计（曾有 `tok.endswith(STRUCT_UNITS)` 一条分支，永不生效）


def scan_files(root):
    out = list(SCAN)
    for pat in SCAN_GLOB:
        out += sorted(os.path.relpath(p, root) for p in glob.glob(os.path.join(root, pat)))
    return out


def mask_code(text):
    """→ (行列表, 每行是否在代码围栏内)。逐行对齐，行号 = 真实行号。"""
    raw, code, in_code = [], [], False
    for ln in text.split("\n"):
        fence = ln.lstrip().startswith("```")
        if fence:
            in_code = not in_code
        raw.append(ln)
        code.append(in_code or fence)
    return raw, code


def model_constant(m, line):
    """→ None（真数字）| "bound"（边界限定 / 区间）| "structural"（模型自身的量）。"""
    pre = line[max(0, m.start() - 12):m.start()]
    if QUAL.search(pre):
        return "bound"
    tok = m.group(0).rstrip()
    # `1–3 个` / `1 至 3 个` 这种"区间 + 单位"是模型常量，与 `190–191`（值转移）同形
    # ⇒ 看**紧跟其后**是不是计量单位：带单位 = 区间（放行），不带 = 值转移（报）
    if re.search(r"[→–—至]", tok) and re.match(
            r"\s*(?:%s|(?:%s)(?![\w]))" % (UNITS, ASCII_UNITS), line[m.end():m.end() + 5]):
        return "structural"
    if tok.endswith("条") and re.match(r"\d+", tok).group(0) in ("0", "1"):
        return "structural"                      # 操作 / 查询返回（有无判断）
    return None


def audit(root):
    bad = []
    for name in scan_files(root):
        path = os.path.join(root, name)
        if not os.path.exists(path):
            continue
        raw, code = mask_code(open(path, encoding="utf-8").read())
        for i, ln in enumerate(raw):
            if code[i]:
                continue
            for m in NUM.finditer(ln):            # 整行扫描：反引号内不豁免
                if model_constant(m, ln) is None:
                    bad.append((name, i + 1, m.group(0).strip(), ln.strip()[:70]))
    return bad


# 样本按**缺陷类别**组织（不是按实现顺手写）：每条对应一个已知会漏的方向 + 一条正向控制
SELF_TEST = [
    # ── 正样本：必须报 ──
    ("SCHEMA.md", "| 卡 | 61 张同属这条线 |\n", {"61 张"}, "带单位实测数字"),
    ("SCHEMA.md", "全库 190 卡\n", {"190 卡"}, "带单位实测数字（全库规模）"),
    ("SCHEMA.md", "同族两卡 93% 靠中转\n", {"93%"}, "占比"),
    ("SCHEMA.md", "省 30×\n", {"30×"}, "倍数"),
    ("SCHEMA.md", "回链 95/95 全绿\n", {"95/95"}, "两位 N/M"),
    ("SCHEMA.md", "| 表格里的 45 个数字 |\n", {"45 个"}, "表格单元格"),
    ("SCHEMA.md", "- 本库约有 190 张卡\n", {"190 张"}, "★ 类别：约 不算模型常量（糊化旁路）"),
    ("SCHEMA.md", "- 全库超过 60 张卡\n", {"60 张"}, "★ 类别：超过 不算模型常量（糊化旁路）"),
    ("SCHEMA.md", "- 旧规则连立 3 轮评审，吐了 2 份报告\n", {"3 轮", "2 份"},
     "★ 类别：轮 / 份 / 度 未进单位表"),
    ("SCHEMA.md", "- 冷启动 300s，重传 1500ms\n", {"300s", "1500ms"}, "★ 类别：时间单位未进单位表"),
    ("SCHEMA.md", "- 镜像 40MB，日志 12KB\n", {"40MB", "12KB"}, "★ 类别：体积单位未进单位表"),
    ("SCHEMA.md", "- 当前规模 `190 张卡`，`2080 对`\n", {"190 张", "2080 对"},
     "★ 类别：反引号内不是免检通道"),
    ("SCHEMA.md", "- 旧值 190→191 已经失真\n", {"190→191"}, "★ 类别：历史叙述里复述旧值（箭头式）"),
    ("SCHEMA.md", "- 分片在 190–191 之间\n", {"190–191"}, "★ 类别：历史复述（短横 / 破折号式）"),
    ("SCHEMA.md", "- 全库共190 卡\n", {"190 卡"},
     "★ 类别：汉字紧贴数字（\\w 含汉字使负向断言过宽 → 已改 ASCII 类）"),
    ("SCHEMA.md", "- 该线61 张卡\n", {"61 张"}, "★ 类别：同上（另一写法）"),
    ("SCHEMA.md", "- 190 张卡同属这条线\n", {"190 张"},
     "★ 类别：行首列表符 `-` 曾被当区间连字符（整条列表项放行）"),
    ("SCHEMA.md", "- 300s 冷启动\n", {"300s"}, "★ 类别：同上（ASCII 计量单位同一个错）"),
    ("SCHEMA.md", "- 冷启动 1.6MB，重传 0.5s\n", {"1.6MB", "0.5s"},
     "★ 类别：单位分支曾只认整数——小数正是嵌入式读数常态（体积 / 时间）"),
    ("SCHEMA.md", "- 超时 2.5 秒，保留 1.5 天\n", {"2.5 秒", "1.5 天"},
     "★ 类别：同上（中文计量单位）"),
    ("SCHEMA.md", "- 一次 1–3 个模块\n", set(), "正向控制：区间 + 单位（与值转移同形，按后续单位区分）"),
    ("SCHEMA.md", "- 超时 1 至 3 分钟\n", set(), "★ 类别：判别器单位表曾与大表不同步（时间区间被误报）"),
    ("SCHEMA.md", "- 日志 1–3 MB\n", set(), "★ 类别：同上（ASCII 体积单位）"),
    ("SCHEMA.md", "- 冷启动 300 毫秒，保留 30 天\n", {"300 毫秒", "30 天"},
     "★ 类别：中文时间单位未进大表（零成本漏报）"),
    ("SCHEMA.md", "- 冷启动 300 秒\n", {"300 秒"}, "★ 类别：同上（秒 比 分钟 / 小时 更常用却曾缺席）"),
    ("SCHEMA.md", "- 一次 1 至 3 个模块\n", set(), "★ 类别：至式区间曾被误报（合法常量被打红）"),
    ("SCHEMA.md", "- 分片在 190 至 191 之间\n", {"190 至 191"}, "★ 类别：至式值转移（与区间同形，按后续单位区分）"),
    ("SCHEMA.md", "- 复述 190 至 191 张的旧值\n", set(),
     "正向控制：已声明的口子——带单位的至式复述按区间放过"),
    ("SCHEMA.md", "- 匿名 API 限流 60 次/时\n", {"60 次"},
     "★ 类别：`次/时` 豁免已退役（外部平台常量同样会随对方改版而烂）"),
    ("SCHEMA.md", "- 自检第 8 项 / 共 11 项断言\n", set(), "正向控制：汉字前缀下的模型常量仍放行"),
    ("templates/card-x.md", "- 本库实测：80% 的卡片缺口径\n", {"80%"},
     "★ 类别：模板（随安装下发的对外件）也在扫描面内"),
    # ── 反样本：必须放行 ──
    ("SCHEMA.md", "- 结构分层 / 跨 ≥2 组件 / ≥3 步流转 → 必给图\n", set(), "边界限定词（≥）"),
    ("SCHEMA.md", "- 每张轨迹卡至少 1 张聚合卡\n", set(), "边界限定词（至少）"),
    ("SCHEMA.md", "- 一次 1-3 个模块\n", set(), "区间"),
    ("SCHEMA.md", "- 共 11 项断言，每会话 ≤5 页\n", set(), "模型自身的量（项 / 页）"),
    ("SCHEMA.md", "- 窗口内 0 条 delegate_task 判为陈旧标记\n", set(), "操作 / 查询返回"),
    ("SCHEMA.md", "- 直链 n(n−1) 行 vs 聚合 2n 行 ⇒ 比值 ≈ n/2\n", set(), "公式变量（无计量单位）"),
    ("SCHEMA.md", "- 每张卡列其余 n−1 张 = n(n−1) 行\n", set(), "正向控制：公式里的减号不进匹配"),
    ("SCHEMA.md", "- 版本前缀 v2.10.0 与线名 310 线 / 3.10 卡 不是数量\n", set(), "标识符（线号 / 版本号）"),
    ("SCHEMA.md", "```\n全库 190 卡\n```\n", set(), "正向控制：代码围栏内不扫（有意边界）"),
    ("CHANGELOG.md", "## 2.12.3\n- 8 处样本 5 处已失真\n", set(), "正向控制：CHANGELOG 不入扫描面"),
]
NUMSTR = re.compile(r"「([^」]+)」")


def self_test():
    import tempfile
    fail = 0
    for name, text, expect, why in SELF_TEST:
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, name)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8").write(text)
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
    print(f"数字审计：{root}（扫描面：{' / '.join(scan_files(root))}）")
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
