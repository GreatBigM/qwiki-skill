#!/bin/bash
# subagent_stop hook：子代理产出知识信号（团队协作场景沉淀）
# 子代理（coder/tester/reviewer/ops）完成 → 写标记到队列目录 → pre_llm_call 注入"检查子代理产出知识点"
# 注意：payload 经环境变量传给 python（heredoc 会覆盖 stdin）

export HOOK_PAYLOAD="$(cat)"
# python3 缺失时静默退出（hook 不应阻塞主流程）
command -v python3 &>/dev/null || exit 0
python3 << 'EOF'
import sys, json, os, time

try:
    d = json.loads(os.environ.get("HOOK_PAYLOAD", "{}"))
except Exception:
    sys.exit(0)

# subagent_stop 真实 payload：顶层 child_role/child_summary（见 hooks.py subagent_stop 协议）
role = d.get("child_role", "") or ""
summary = d.get("child_summary", "") or ""
status = d.get("child_status", "") or ""
parent_session_id = d.get("parent_session_id", "") or d.get("session_id", "unknown")

queue_dir = os.path.expanduser("~/.hermes/state/knowledge-sediment")
os.makedirs(queue_dir, exist_ok=True)

entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"),
         "type": "subagent_done",
         "detail": f"子代理({role or '未知'})完成[{status or ''}]: {(summary or '')[:60]}",
         "session_id": parent_session_id}
fname = f"{time.time_ns()}-subagent_done.json"
with open(os.path.join(queue_dir, fname), "w") as f:
    json.dump(entry, f, ensure_ascii=False)
sys.exit(0)
EOF
exit 0
