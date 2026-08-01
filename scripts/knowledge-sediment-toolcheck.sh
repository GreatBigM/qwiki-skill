#!/bin/bash
# post_tool_call hook：知识信号检测（当前对话内触发）
# 检测工具调用：代码修改 → 写"待更新卡"标记；验证成功 → 写"验证结论"标记
# 标记被 pre_llm_call hook 读取 → 下一轮注入沉淀指令（不等下次会话）
# 注意：payload 经环境变量传给 python（heredoc 会覆盖 stdin）

payload=$(cat)
export HOOK_PAYLOAD="$payload"
python3 << 'EOF'
import sys, json, os, time

try:
    d = json.loads(os.environ.get("HOOK_PAYLOAD", "{}"))
except Exception:
    sys.exit(0)

tool = d.get("tool_name", "")
args = d.get("args", {}) if isinstance(d.get("args"), dict) else {}
result = d.get("result", "") or ""
status = d.get("status", "ok")
session_id = d.get("session_id", "unknown")

marker = os.path.expanduser("~/.hermes/state/knowledge-sediment-hint")
os.makedirs(os.path.dirname(marker), exist_ok=True)

def write_marker(mtype, detail):
    entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "type": mtype,
             "detail": detail, "session_id": session_id}
    with open(marker, "w") as f:
        json.dump(entry, f, ensure_ascii=False)

# 信号 1：代码修改（patch / write_file）
if tool in ("patch", "write_file"):
    path = args.get("path", "")
    if path:
        write_marker("code_change", f"修改文件: {path}")
        sys.exit(0)

# 信号 2：编译/烧录/测试类命令成功（terminal）
if tool == "terminal":
    cmd = args.get("command", "")
    low = cmd.lower()
    if status == "ok" and any(k in low for k in
        ("make ", "build", "cmake", "flash", "烧录", "编译", "qwiki", "sync")):
        write_marker("verify_done", f"命令: {cmd[:80]}")
        sys.exit(0)

# 无信号 → 静默
sys.exit(0)
EOF
exit 0
