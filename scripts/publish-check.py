#!/usr/bin/env python3
"""发布前脱敏检查 —— 扫发布仓里不该出门的真实标识。

用法:  python3 publish-check.py [目录]          # 默认脚本所在仓的根
       python3 publish-check.py --self-test     # 验证规则本身（种样本 → 必须命中）
退出码: 0 = 干净；1 = 有命中（别推）

为什么需要它：脱敏靠人记必然回潮——同一批项目代号在 v1.7.6 脱敏过一轮，
v2.6.2 / v2.7.3 / v2.8.4 又各自写回去，因为**写文档时顺手就用真实名字举例**。
最隐蔽的泄漏面是模板里的「好坏例」：举例越真实越像好例。

命中不代表一定违规（可能本就是占位符示例）——**逐条人工判定**，是真实标识就换 <项目A> / <IP> 这类占位符。

口径（2026-10-15 收紧，三个洞同批修）：
  1. **大小写不敏感**：`HM9999` 与 `hm9999` 同等命中（旧版只认小写，大写整体漏）。
  2. **按匹配项豁免，不按行豁免**：一行里出现 `<项目A>` 不再给同行的真实标识背书
     （旧版 `if any(a in line for a in ALLOW): continue` 把整行放掉）。
  3. **词边界用显式字符类，不用 \\b**：`\\b` 在 str 模式下 \\w 含汉字 ⇒「项目hm9999」漏检；
     前后只排除字母数字 ⇒ `xhm9999`/`setup12` 不误报，`build_HM9999_debug.sh`/「项目hm9999」要命中。

说明（举例一律写合成代号，本文件随仓公开，写真实例即等于把泄漏面放进发布件）：
  · 本文件在 SKIP_FILES 里（含规则字面量与自检样本）⇒ **它自身不在扫描面内**，改它时人工核对；
    因此「自检样本会被扫描命中」这类说法对本文件不成立，只适用于样本写在闸门之外的脚本。
  · 下列 PATTERNS 里的数字代号是**扫描签名表**（枚举真实代号才能检出它们），不是「举例」。

已知边界（**不是覆盖**，改本文件或审发布件时人工过一遍）：
  1. 人名 / 昵称 / 厂商 SDK 名 / 内部 skill 名无法正则枚举，也**不应写进发布仓**（写进来等于把泄漏面放进
     发布件）⇒ 这类靠人工重扫，或在本机未跟踪的 `scripts/publish-deny.local`（每行一个真名，gitignore）
     里维护，本闸门会自动一并扫（该文件不进仓，且在 SKIP_FILES 内——否则名单会被自己的规则命中，pre-push 永久红灯）。
  2. 本文件自身在 SKIP_FILES 里（含规则字面量）⇒ 它的样本 / 模式表不在扫描面内，改它时人工核对。
  3. 未识别形态：长 hash 折行、全角句点 IP（`10．1．2．3`）。
  4. **git 元数据不在扫描面内**：`SKIP_DIRS` 含 `.git` ⇒ 作者/提交者邮箱、commit message 永不进扫描面。
     推公开仓前单独查：`git config user.email` + `git log --format='%ae' | sort | uniq -c`
     （必须为 noreply 邮箱；公司邮箱一旦推上去永久可查）。
"""
import os
import re
import sys

SKIP_DIRS = {".git", "__pycache__", "node_modules"}
SKIP_FILES = {"publish-check.py", "publish-deny.local"}  # 前者含规则字面量；后者是本机名单本身
DENY_FILE = "scripts/publish-deny.local"   # 本机私用名单（gitignore），每行一个真名

# ── 字符类（三个洞的修法在这里，改前先读文件头「口径」）─────────────────────
# 代号：前后只排除字母数字 ⇒ 不排除 _（含 build_HM9999_debug.sh）、不排除汉字（含「项目hm9999」）
_A = r"[0-9A-Za-z]"
L, R = rf"(?<!{_A})", rf"(?!{_A})"
# IP / 路径：连 . 也排除，避免把长数字的尾巴当 IP
LW, RW = r"(?<![0-9A-Za-z_.])", r"(?![0-9A-Za-z_.])"

PATTERNS = [
    (rf"(?i){L}hm\d{{4}}(?:_[a-z0-9]+)?{R}", "项目代号 hm####"),
    (rf"(?i){L}prj0\d{{2}}{R}", "项目代号 PRJ0##"),
    (rf"{L}(?:6502|6503|6401|6402|6801|6802){R}", "项目数字代号签名"),
    (rf"(?i){L}bw\d{{3}}{R}", "项目代号 bw###"),
    (rf"(?i){L}up\d{{2}}{R}", "项目代号 up##"),
    (rf"{LW}10\.\d{{1,3}}\.\d{{1,3}}\.\d{{1,3}}{RW}", "内网 IP 10/8"),
    (rf"{LW}192\.168\.\d{{1,3}}\.\d{{1,3}}{RW}", "内网 IP 192.168/16"),
    (rf"{LW}172\.(?:1[6-9]|2\d|3[01])\.\d{{1,3}}\.\d{{1,3}}{RW}", "内网 IP 172.16/12"),
    (rf"(?<![0-9A-Fa-f])(?:[0-9a-fA-F]{{2}}[:-]){{5}}[0-9a-fA-F]{{2}}(?![0-9A-Fa-f])", "MAC 地址"),
    (rf"{L}[0-9a-fA-F]{{32,}}{R}", "长 hash（固件/提交）"),
    # 凭据：值不能以反引号 / < / 引号开头（那种是「串口提示符 Password:`」这类说明性文字，属已知误报形态）
    (r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|token)\b\s*[:：=]\s*[^\s`<\"']\S*", "凭据赋值"),
    (r"(?i)\bBearer\s+[A-Za-z0-9._-]{12,}", "凭据（Bearer token）"),
    (r"密码\s*[:：]\s*[^\s`<]", "凭据赋值（中文「密码：」）"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "私钥块"),
    (r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}", "邮箱"),
    (r"(?i)/home/(?!<)[a-z0-9_-]+/", "本机家目录路径"),
    (r"/mnt/data/(?!<)", "内网代码树路径"),
]
# 按**匹配项**豁免（旧版按整行豁免，等于给同行的真名背书）。
# 说明：后两条 IP 组现有 pattern 本就命中不到，留着是显式声明「这些是文档保留段」。
ALLOW_RE = re.compile(
    r"^(?:"
    r"git@(?:gitee|github)\.com"
    r"|[\w.+-]+@users\.noreply\.github\.com"
    r"|[\w.+-]+@example\.(?:com|org|net)"
    r"|127\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|0\.0\.0\.0"
    r"|192\.0\.2\.\d{1,3}"
    r"|198\.51\.100\.\d{1,3}"
    r"|203\.0\.113\.\d{1,3}"
    r")$"
)
COMPILED = [(re.compile(p), n) for p, n in PATTERNS]


def load_deny(root):
    """本机私用真名名单（未跟踪文件，不进仓）：一行一个，原文匹配。"""
    p = os.path.join(root, DENY_FILE)
    try:
        with open(p, encoding="utf-8") as fh:
            return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
    except OSError:
        return []


def line_hits(line, pats):
    """扫一行，返回 [(规则名, 片段)]。scan() 与本文件自检**共用这一份口径**（各写一套正是假绿温床）。"""
    out = []
    for rx, name in pats:
        for m in rx.finditer(line):
            frag = m.group(0)
            if ALLOW_RE.match(frag):
                continue
            out.append((name, frag[:60]))
    return out


def scan(root):
    pats = list(COMPILED) + [(re.compile(re.escape(n)), "本机私用名单") for n in load_deny(root)]
    hits = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in sorted(fn):
            if f in SKIP_FILES:
                continue
            p = os.path.join(dp, f)
            try:
                text = open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue
            for ln, line in enumerate(text.split("\n"), 1):
                for name, frag in line_hits(line, pats):
                    hits.append((os.path.relpath(p, root), ln, name, frag))
    return hits


def self_test():
    # 样本一律用合成值（hm9999 之类）——真名写进这里，等于亲手把泄漏面放进发布仓。
    # 样本按**已知缺陷类别**增长，不按实现顺手写：每加一个洞的修法，就在对应组里补一条。
    must_hit = [
        # 基础形态
        "设备 10.99.99.99", "见 `hm9999/resource/x.md`", "bw999/scripts/README.md",
        "up99 迁移", "mac aa:bb:cc:dd:ee:ff", "fw 3f2a1b0c4d5e6f708192a3b4c5d6e7f8",
        "password: hunter2", "/home/demo/qwiki", "/mnt/data/hm9999",
        # 大小写变体（洞一）
        "见 HM9999/resource/x.md", "BW999/scripts/README.md", "UP99 迁移", "Hm9999 混合大小写",
        "build_HM9999_debug.sh",
        # 汉字紧贴 / 前后缀（洞三）
        "项目hm9999 的说明", "hm9999项目", "设备地址10.99.99.99 端口", "网关10.99.99.99与掩码",
        # 代号形态补全（含数字代号签名表的两个新成员）
        "PRJ099# 提示符", "老项目 6502 与 6503", "样机 6801 与 6802 两支",
        # 整行豁免 / 子串误豁免（洞二）
        "hm9999 见 <项目B>", "hm9999 <项目A>-build", "设备 10.0.0.0 与 hm9999",
        "项目 hm9999 的 IP 是 10.99.99.99（对照 127.0.0.1）",
        "password: hunter2 见 0.0.0.0",
        # 词表 / 形态覆盖
        "mac AA-BB-CC-DD-EE-FF", "token=ghp9abc123def", "Authorization: Bearer eyJhbGciOiJIUzI1zI",
        "联系 ops9@company-inc.com",
    ]
    must_miss = [
        # 占位符与文档保留段
        "占位符 `hm[0-9]{4}` 这类模式", "设备 <IP>（eth0 已摘）", "127.0.0.1",
        "文档保留段 192.0.2.1 与 203.0.113.9", "<项目A>-build-flash-system",
        "/mnt/data/<项目>/CLAUDE.md", "占用 <项目>_wifi 树",
        # 防误报（收紧字符类后必须仍然放行）
        "setup12 / backup07 / group11", "xhm9999", "路径 172.32.1.1 与 192.169.1.1",
        "zzz3f2a1b0c4d5e6f708192a3b4c5d6e7f8zzz",
        # 已知误报形态：串口提示符字面量 / 公开远端
        "串口提示符 `Password:` 字面量与说明", "git@gitee.com:GreatBigM/example.git",
        # 公开型号不得被打红（闸门只管内部标识）
        "T32 / aic8800 是公开型号",
    ]
    bad = [f"该命中却放行: {s}" for s in must_hit if not line_hits(s, COMPILED)]
    bad += [f"该放行却命中: {s}" for s in must_miss if line_hits(s, COMPILED)]
    bad += self_test_deny()
    print("自检：" + ("全部通过" if not bad else "失败 → " + repr(bad)))
    return 1 if bad else 0


def self_test_deny():
    """私用名单机制的回归样本（合成名）：既验「名单词必中」，也验「名单文件自身不在扫描面」。"""
    import shutil
    import tempfile
    bad = []
    d = tempfile.mkdtemp(prefix="deny-selftest-")
    try:
        os.makedirs(os.path.join(d, "scripts"), exist_ok=True)
        with open(os.path.join(d, "scripts", "publish-deny.local"), "w", encoding="utf-8") as fh:
            fh.write("# 合成名，仅自检用\nsynthcodename9z\n")
        with open(os.path.join(d, "probe.md"), "w", encoding="utf-8") as fh:
            fh.write("这一段出现 synthcodename9z 就该被打红\n")
        hits = scan(d)
        if not any(n == "本机私用名单" for _, _, n, _ in hits):
            bad.append("私用名单：名单里的词未被打红（load_deny 未接进 scan？）")
        if any(f.endswith("publish-deny.local") for f, _, _, _ in hits):
            bad.append("私用名单：名单文件自身被扫（SKIP_FILES 缺 publish-deny.local）⇒ pre-push 会永久红灯")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return bad


def main(argv):
    if "--self-test" in argv:
        return self_test()
    root = os.path.expanduser(argv[0]) if argv and not argv[0].startswith("-") \
        else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = scan(root)
    deny = load_deny(root)
    print(f"发布前脱敏检查：{root}" + (f"（含本机私用名单 {len(deny)} 条）" if deny else ""))
    for f, ln, name, frag in hits:
        print(f"  {f}:{ln}: [{name}] {frag}")
    print(f"\n{'干净，可以发布' if not hits else f'{len(hits)} 处命中 —— 逐条判定，真实标识换占位符'}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
