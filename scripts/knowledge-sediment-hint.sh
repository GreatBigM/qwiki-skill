#!/bin/bash
# Stop / on_session_end hook：会话结束 → 沉淀门禁
# 兼容 Hermes / Claude Code / Codex（payload 经归一化层统一）
#
# Codex 特殊行为（Stop 事件）：
#   有标记且 stop_hook_active=false → {"decision":"block","reason":"沉淀指令"}
#   强制 AI 在结束前执行沉淀（连续 block 8 次后 CLI 自动放行）
# Hermes/Claude（session_end 事件）：
#   写 session_end 标记到队列（下次 inject 消费）

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=knowledge-sediment-lib.sh
source "$SELF_DIR/knowledge-sediment-lib.sh"

command -v python3 &>/dev/null || exit 0

# 读 stdin（hook 协议）
payload=$(cat)
export HOOK_PAYLOAD="$payload"

sediment_normalize_payload

# 仅处理会话结束事件（Hermes on_session_end / Codex Stop）
sediment_is "session_end" || exit 0

mkdir -p "$SEDIMENT_QUEUE_DIR"

# stop_hook_active 从原始 payload 提取（Codex Stop 特有，防无限循环）
stop_active=$(echo "$payload" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    print('true' if d.get('stop_hook_active') else 'false')
except Exception:
    print('false')
" 2>/dev/null)

python3 - "$SEDIMENT_QUEUE_DIR" "$SEDIMENT_SESSION" "$stop_active" <<'PYEOF'
import json, os, sys, time

qdir, sid, stop_active = sys.argv[1], sys.argv[2], sys.argv[3]

# 读队列标记
marks = []
try:
    files = sorted(os.listdir(qdir)) if os.path.isdir(qdir) else []
except Exception:
    files = []

for fn in files:
    try:
        with open(os.path.join(qdir, fn)) as f:
            marks.append(json.load(f))
    except Exception:
        continue

# 写 session_end 标记（跨会话沉淀用）
marker = {
    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "type": "session_end",
    "detail": "",
    "session_id": sid or "",
}
fn_out = f"{time.time_ns()}-session_end.json"
with open(os.path.join(qdir, fn_out), "w") as f:
    json.dump(marker, f)

# Codex Stop 门禁：有标记且未被 block 过 → 强制沉淀
if marks and stop_active != "true":
    types = [m.get("type", "?") for m in marks]
    details = [m.get("detail", "") for m in marks if m.get("detail")]
    t_sum = "/".join(sorted(set(types)))
    reason = f"【知识沉淀门禁】检测到沉淀标记（{t_sum}）。结束前执行：①按归属路由建卡或更新（个人→personal/，跨项目→projects/common/，项目→项目卡）②更新 INDEX ③git commit。细节：{' | '.join(d[:120] for d in details)}"
    # 读后即删（沉淀指令已下达，标记使命完成）
    for fn in files:
        try:
            os.remove(os.path.join(qdir, fn))
        except Exception:
            pass
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
# 无标记或已 block 过 → 静默放行
PYEOF

exit 0
