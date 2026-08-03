#!/bin/bash
# subagent_stop hook：子代理产出知识信号（团队协作场景沉淀）
# 兼容 Hermes / Claude Code / Codex（payload 经归一化层统一）
# 注意：payload 经环境变量传给 python（heredoc 会覆盖 stdin）

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=knowledge-sediment-lib.sh
source "$SELF_DIR/knowledge-sediment-lib.sh"

command -v python3 &>/dev/null || exit 0

# 读 stdin（hook 协议）
payload=$(cat)
export HOOK_PAYLOAD="$payload"

sediment_normalize_payload

# 仅处理子代理结束事件
sediment_is "subagent_stop" || exit 0

# detail 已由归一化层合成：role|child_status|summary
mkdir -p "$SEDIMENT_QUEUE_DIR"

python3 - "$SEDIMENT_QUEUE_DIR" "$SEDIMENT_DETAIL" "$SEDIMENT_SESSION" <<'PYEOF'
import json, os, sys, time
qdir, detail, sid = sys.argv[1], sys.argv[2], sys.argv[3]
marker = {
    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "type": "subagent_done",
    "detail": detail,
    "session_id": sid or "",
}
fn = f"{time.time_ns()}-subagent_done.json"
with open(os.path.join(qdir, fn), "w") as f:
    json.dump(marker, f)
PYEOF

exit 0
