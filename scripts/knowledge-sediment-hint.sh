#!/bin/bash
# on_session_end hook：会话结束 → 写"待沉淀"标记
# 兼容 Hermes / Claude Code / Codex（payload 经归一化层统一）

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=knowledge-sediment-lib.sh
source "$SELF_DIR/knowledge-sediment-lib.sh"

command -v python3 &>/dev/null || exit 0

# 读 stdin（hook 协议）
payload=$(cat)
export HOOK_PAYLOAD="$payload"

sediment_normalize_payload

# 仅处理会话结束事件
sediment_is "session_end" || exit 0

QUEUE_DIR="$HOME/.hermes/state/knowledge-sediment"
mkdir -p "$QUEUE_DIR"

python3 - "$QUEUE_DIR" "$SEDIMENT_SESSION" <<'PYEOF'
import json, os, sys, time
qdir, sid = sys.argv[1], sys.argv[2]
marker = {
    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "type": "session_end",
    "detail": "",
    "session_id": sid or "",
}
fn = f"{time.time_ns()}-session_end.json"
with open(os.path.join(qdir, fn), "w") as f:
    json.dump(marker, f)
PYEOF

exit 0
