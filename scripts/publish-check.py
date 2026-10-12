#!/usr/bin/env python3
"""发布前脱敏检查 —— 扫发布仓里不该出门的真实标识。

用法:  python3 publish-check.py [目录]          # 默认脚本所在仓的根
       python3 publish-check.py --self-test     # 验证规则本身（种样本 → 必须命中）
退出码: 0 = 干净；1 = 有命中（别推）

为什么需要它：脱敏靠人记必然回潮——同一批项目代号在 v1.7.6 脱敏过一轮，
v2.6.2 / v2.7.3 / v2.8.4 又各自写回去，因为**写文档时顺手就用真实名字举例**。
最隐蔽的泄漏面是模板里的「好坏例」：举例越真实越像好例。

命中不代表一定违规（可能本就是占位符示例）——**逐条人工判定**，是真实标识就换 <项目A> / <IP> 这类占位符。
"""
import os
import re
import sys

SKIP_DIRS = {".git", "__pycache__", "node_modules"}
SKIP_FILES = {"publish-check.py"}          # 本脚本自身含规则字面量

PATTERNS = [
    (r"\bhm\d{4}(?:_[a-z]+)?\b", "项目代号 hm####"),
    (r"\bbw\d{3}\b", "项目代号 bw###"),
    (r"\bup\d{2}\b", "项目代号 up##"),
    (r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "内网 IP 10/8"),
    (r"\b192\.168\.\d{1,3}\.\d{1,3}\b", "内网 IP 192.168/16"),
    (r"\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b", "内网 IP 172.16/12"),
    (r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b", "MAC 地址"),
    (r"\b[0-9a-fA-F]{32,}\b", "长 hash（固件/提交）"),
    (r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\b\s*[:=]\s*\S+", "凭据赋值"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "私钥块"),
    (r"/home/[a-z0-9_-]+/", "本机家目录路径"),
    (r"/mnt/data/", "内网代码树路径"),
]
ALLOW = ("127.0.0.1", "0.0.0.0", "192.0.2.", "198.51.100.", "203.0.113.", "<IP>", "<项目")
COMPILED = [(re.compile(p), n) for p, n in PATTERNS]


def scan(root):
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
                if any(a in line for a in ALLOW):
                    continue
                for rx, name in COMPILED:
                    m = rx.search(line)
                    if m:
                        hits.append((os.path.relpath(p, root), ln, name, m.group(0)[:60]))
    return hits


def self_test():
    # 样本一律用合成值（hm9999 之类）——真名写进这里，等于亲手把泄漏面放进发布仓
    must_hit = ["设备 10.99.99.99", "见 `hm9999/resource/x.md`", "bw999/scripts/README.md",
                "up99 迁移", "mac aa:bb:cc:dd:ee:ff", "fw 3f2a1b0c4d5e6f708192a3b4c5d6e7f8",
                "password: hunter2", "/home/demo/qwiki", "/mnt/data/hm9999"]
    must_miss = ["占位符 `hm[0-9]{4}` 这类模式", "设备 <IP>（eth0 已摘）", "127.0.0.1",
                 "文档保留段 192.0.2.1 与 203.0.113.9", "<项目A>-build-flash-system",
                 "setup12 / backup07 / group11"]
    bad = [s for s in must_hit if not any(rx.search(s) for rx, _ in COMPILED)]
    bad += [s for s in must_miss if any(rx.search(s) for rx, _ in COMPILED)]
    print("自检：" + ("全部通过" if not bad else "失败 → " + repr(bad)))
    return 1 if bad else 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    root = os.path.expanduser(argv[0]) if argv and not argv[0].startswith("-") \
        else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = scan(root)
    print(f"发布前脱敏检查：{root}")
    for f, ln, name, frag in hits:
        print(f"  {f}:{ln}: [{name}] {frag}")
    print(f"\n{'干净，可以发布' if not hits else f'{len(hits)} 处命中 —— 逐条判定，真实标识换占位符'}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
