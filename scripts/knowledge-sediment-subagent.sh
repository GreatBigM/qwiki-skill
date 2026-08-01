#!/bin/bash
# subagent_stop hook：子代理产出知识信号（团队协作场景沉淀）
# 子代理（coder/tester/reviewer/ops）完成 → 写标记 → pre_llm_call 注入"检查子代理产出知识点"

export HOOK_PAYLOAD="$(cat)"
python3 << 'EOF'
import sys, json, os, time

try:
    d = json.loads(os.environ.get("HOOK_PAYLOAD", "{}"))
except Exception:
    sys.exit(0)

role = d.get("extra", {}).get("role", "") if isinstance(d.get("extra"), dict) else ""
task = d.get("extra", {}).get("goal", "") if isinstance(d.get("extra"), dict) else ""
session_id = d.get("session_id", "unknown")

marker = os.path.expanduser("~/.hermes/state/knowledge-sediment-hint")
os.makedirs(os.path.dirname(marker), exist_ok=True)

entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"),
         "type": "subagent_done",
         "detail": f"子代理({role or '未知'})完成: {(task or '')[:60]}",
         "session_id": session_id}
with open(marker, "w") as f:
    json.dump(entry, f, ensure_ascii=False)
sys.exit(0)
EOF
exit 0
