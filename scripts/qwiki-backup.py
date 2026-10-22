#!/usr/bin/env python3
"""qwiki 备份 —— 把知识库打成**单个** git bundle，每日覆盖，坏了能整库恢复。

用法:
  python3 qwiki-backup.py [库根] [目标文件] [--keep N]
      默认：~/qwiki → ~/qwiki.bundle，--keep 1（只留一份，每次覆盖）

为什么是 bundle 而不是复制目录：
  - **单文件**：一份就是一个完整的库（全部提交、分支、标签），拷走即备份；
  - **自带校验**：`git bundle verify` 能证明它没坏，复制目录做不到；
  - **可增量也可全量**：这里用 `--all` 全量，几百张卡的库只有几 MB。

安全约束：
  - 目标不能落在库内（否则把自己备份进自己）；
  - 先写 `.tmp` 再原子替换，备份过程中断不会留下半个文件；
  - 写完必须 `verify` 通过才认账。

恢复：`git clone <目标文件> ~/qwiki-restored`
"""
import os
import shutil
import subprocess
import sys


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def main(argv):
    args, keep = [], 1
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--keep" and i + 1 < len(argv):
            keep = max(1, int(argv[i + 1])); i += 2; continue
        if not a.startswith("-"):
            args.append(a)
        i += 1
    kb = os.path.expanduser(args[0] if args else "~/qwiki")
    target = os.path.expanduser(args[1] if len(args) > 1 else "~/qwiki.bundle")

    if not os.path.isdir(os.path.join(kb, ".git")):
        print(f"x 不是 git 仓库：{kb}")
        return 1
    if os.path.abspath(target).startswith(os.path.abspath(kb) + os.sep):
        print(f"x 目标不能放到库内：{target}")
        return 1
    if not shutil.which("git"):
        print("x 找不到 git")
        return 1

    os.makedirs(os.path.dirname(os.path.abspath(target)) or ".", exist_ok=True)
    tmp = target + ".tmp"
    r = run(["git", "-C", kb, "bundle", "create", tmp, "--all"])
    if r.returncode != 0:
        print(f"x 打包失败：{r.stderr.strip()[:200]}")
        return 1
    v = run(["git", "bundle", "verify", tmp])
    if v.returncode != 0:
        os.path.exists(tmp) and os.remove(tmp)
        print(f"x 校验失败：{v.stderr.strip()[:200]}")
        return 1
    if keep > 1:
        for n in range(keep - 1, 0, -1):
            old = f"{target}.{n}"
            if os.path.exists(old):
                os.replace(old, f"{target}.{n + 1}")
        os.replace(target, f"{target}.1") if os.path.exists(target) else None
    os.replace(tmp, target)

    head = run(["git", "-C", kb, "rev-parse", "--short", "HEAD"]).stdout.strip()
    size = os.path.getsize(target) / 1024
    print(f"qwiki 备份：{kb} → {target}")
    print(f"  {size:.0f} KB ｜ HEAD {head} ｜ 校验通过"
          + ("" if keep == 1 else f" ｜ 保留 {keep} 份"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
