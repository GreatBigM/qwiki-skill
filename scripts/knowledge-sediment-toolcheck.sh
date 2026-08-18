#!/bin/bash
# post_tool_call hook：代码修改/验证成功信号检测 → 写沉淀标记
# 兼容 Hermes / Claude Code / Codex / ZCode（payload 经归一化层统一）

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=knowledge-sediment-lib.sh
source "$SELF_DIR/knowledge-sediment-lib.sh"

command -v python3 &>/dev/null || exit 0

# 读 stdin（hook 协议）
payload=$(cat)
export HOOK_PAYLOAD="$payload"

sediment_normalize_payload
sediment_detect_tool "$@"

# 仅处理工具调用后事件
sediment_is "post_tool" || exit 0

# 代码修改检测：write_file / patch / edit / apply_patch 等
case "$SEDIMENT_TOOL" in
  # Claude/ZCode 系工具名（Write/Edit/ApplyPatch/NotebookEdit），与 Hermes/Codex 小写名并存
  write_file|write|patch|edit|apply_patch|edit_file|replace|multi_edit|Write|Edit|ApplyPatch|NotebookEdit)
    # 文件路径从 payload 提取（归一化层未单独提，此处从原始 payload 提取；兼容各工具字段）
    fpath=$(echo "$payload" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    a=d.get('args',{}) or {}
    t=d.get('tool_input',{}) or {}
    p=a.get('path') or t.get('file_path') or t.get('path') or a.get('file_path') or ''
    print(p)
except Exception:
    print('')
" 2>/dev/null)
    if [ -n "$fpath" ]; then
      mkdir -p "$SEDIMENT_QUEUE_DIR"
      python3 - "$SEDIMENT_QUEUE_DIR" "$fpath" "$SEDIMENT_SESSION" <<'PYEOF'
import json, os, sys, time
qdir, fpath, sid = sys.argv[1], sys.argv[2], sys.argv[3]
marker = {
    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "type": "code_change",
    "detail": f"文件: {fpath}",
    "session_id": sid or "",
}
fn = f"{time.time_ns()}-code_change.json"
with open(os.path.join(qdir, fn), "w") as f:
    json.dump(marker, f)
PYEOF
    fi
    ;;
  # 验证成功检测：terminal/bash 命令 + 状态成功（ZCode/Claude 系工具名为 Bash）
  terminal|bash|shell|exec|command|Bash)
    # 归一化层已算 status；仅成功命令才算验证（失败构建不写标记）
    [ "$SEDIMENT_STATUS" = "success" ] || exit 0
    cmd=$(echo "$payload" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    a=d.get('args',{}) or {}
    t=d.get('tool_input',{}) or {}
    p=a.get('command') or t.get('command') or a.get('cmd') or t.get('cmd') or ''
    print(p[:200])
except Exception:
    print('')
" 2>/dev/null)
    # 验证类命令模式：构建/烧录/验证动词（去掉 check/test 宽泛词防 grep 搜索误配，\b 限词边界）
    if echo "$cmd" | grep -qiE '\b(make|build|compile|verify|flash|burn)\b|烧录|编译'; then
      mkdir -p "$SEDIMENT_QUEUE_DIR"
      python3 - "$SEDIMENT_QUEUE_DIR" "$cmd" "$SEDIMENT_STATUS" "$SEDIMENT_SESSION" <<'PYEOF'
import json, os, sys, time
qdir, cmd, status, sid = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
marker = {
    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "type": "verify_done",
    "detail": f"命令: {cmd} | 状态: {status}",
    "session_id": sid or "",
}
fn = f"{time.time_ns()}-verify_done.json"
with open(os.path.join(qdir, fn), "w") as f:
    json.dump(marker, f)
PYEOF
    fi
    ;;
esac

exit 0
