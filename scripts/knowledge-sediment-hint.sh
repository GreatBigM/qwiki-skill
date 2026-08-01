#!/bin/bash
# on_session_end hook：知识沉淀提示触发器
# 会话结束时写标记文件到队列目录，下次 pre_llm_call 时 inject.sh 消费
# stdin 协议：JSON {"hook_event_name": "on_session_end", "session_id": "...", ...}

payload=$(cat)

# python3 缺失时静默退出（hook 不应阻塞主流程）
if ! command -v python3 &>/dev/null; then
  exit 0
fi

session_id=$(echo "$payload" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('session_id', 'unknown'))
except Exception:
    print('unknown')
" 2>/dev/null || echo "unknown")

QUEUE_DIR="$HOME/.hermes/state/knowledge-sediment"
mkdir -p "$QUEUE_DIR"
python3 - "$session_id" << 'EOF'
import sys, json, os, time
session_id = sys.argv[1]
queue_dir = os.path.expanduser("~/.hermes/state/knowledge-sediment")
os.makedirs(queue_dir, exist_ok=True)
entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"),
         "type": "session_end",
         "detail": "",
         "session_id": session_id}
fname = f"{time.time_ns()}-session_end.json"
with open(os.path.join(queue_dir, fname), "w") as f:
    json.dump(entry, f, ensure_ascii=False)
sys.exit(0)
EOF
exit 0
