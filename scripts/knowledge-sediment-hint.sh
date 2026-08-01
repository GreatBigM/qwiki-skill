#!/bin/bash
# on_session_end hook：知识沉淀提示触发器
# 会话结束时写标记文件，下次会话 AI 检查标记 → 加载 qwiki 检查最近会话知识点 → 沉淀 → 清标记
# stdin 协议：JSON {"hook_event_name": "on_session_end", "session_id": "...", ...}

payload=$(cat)
session_id=$(echo "$payload" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('session_id', 'unknown'))
except Exception:
    print('unknown')
" 2>/dev/null || echo "unknown")

mkdir -p "$HOME/.hermes/state"
echo "$(date '+%Y-%m-%d %H:%M:%S') $session_id" > "$HOME/.hermes/state/knowledge-sediment-hint"
exit 0
