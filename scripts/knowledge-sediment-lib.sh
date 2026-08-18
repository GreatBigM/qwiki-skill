#!/bin/bash
# knowledge-sediment-lib.sh — 多工具 hook payload 统一归一化层（Hermes/Claude Code/Codex/ZCode）
# 被 knowledge-sediment-{hint,toolcheck,inject,subagent}.sh source
# 职责：读 stdin JSON → 归一化为统一事件类型 + 提取公共字段 + 识别当前工具
# 用法：`source knowledge-sediment-lib.sh` 后调用 `sediment_normalize_payload`、`sediment_detect_tool`
# 工具判定：优先注册参数 $1（各工具注册命令自带工具名），否则从 payload 特征推断
#
# 归一化结果（全局变量，函数内 export 或显式读取）：
#   SEDIMENT_EVENT    : 统一事件类型 session_end | code_change | verify_done | subagent_done | other
#   SEDIMENT_TOOL     : 工具名（小写）
#   SEDIMENT_STATUS   : 工具状态 success | error
#   SEDIMENT_SESSION  : session_id
#   SEDIMENT_DETAIL   : 事件细节文本（工具结果摘要 / 子代理信息 / 空）
#   SEDIMENT_PROMPT   : 用户 prompt（pre_llm_call / UserPromptSubmit 用）
#   SEDIMENT_CWD      : 工作目录
#   SEDIMENT_QUEUE_DIR: 标记队列目录（XDG 约定，跨工具共享）

# 队列目录单一真相源（四脚本统一引用，改路径只动这里）
export SEDIMENT_QUEUE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwiki/sediment"

sediment_normalize_payload() {
  # 读 stdin（heredoc 保护：hook 脚本内 stdin 已被 consume，用环境变量传入）
  local payload="${HOOK_PAYLOAD:-$(cat)}"

  # payload 经临时文件传给 python（大 payload 如编译日志直传 argv 会触 ARG_MAX）
  local pfile
  pfile=$(mktemp "${TMPDIR:-/tmp}/sediment.XXXXXX")
  printf '%s' "$payload" > "$pfile"

  # python3 归一化：三工具事件名/字段差异在此收敛
  local norm
  norm=$(python3 - "$pfile" <<'PYEOF'
import json, sys

try:
    with open(sys.argv[1], errors="replace") as f:
        raw = f.read()
except Exception:
    raw = ""
try:
    data = json.loads(raw) if raw.strip() else {}
except Exception:
    data = {}

# ---- 事件名归一化（三工具命名差异）----
EVENT_MAP = {
    # Hermes (snake_case)
    "post_tool_call": "post_tool",
    "pre_llm_call": "pre_llm",
    "on_session_end": "session_end",
    "subagent_stop": "subagent_stop",
    "on_session_start": "session_start",
    "on_session_finalize": "session_finalize",
    "on_session_reset": "session_reset",
    # Claude Code / ZCode (PascalCase，两者事件同名，同一套归一化)
    "PostToolUse": "post_tool",
    "UserPromptSubmit": "pre_llm",
    "SessionEnd": "session_end",
    "SubagentStop": "subagent_stop",
    "SessionStart": "session_start",
    "PreCompact": "pre_compact",
    "PostCompact": "post_compact",
    "PreToolUse": "pre_tool",
    # Codex (snake_case，二进制实证：pre_tool_use/post_tool_use/user_prompt_submit/session_end 等)
    "pre_tool_use": "pre_tool",
    "post_tool_use": "post_tool",
    "user_prompt_submit": "pre_llm",
    "session_start": "session_start",
    "session_end": "session_end",
    "subagent_start": "subagent_start",
    "subagent_stop": "subagent_stop",
    "pre_compact": "pre_compact",
    "post_compact": "post_compact",
    # Codex PascalCase（hooks.json 实证：hook_event_name 字段为 PascalCase）
    "UserPromptSubmit": "pre_llm",
    "PostToolUse": "post_tool",
    "PreToolUse": "pre_tool",
    "Stop": "session_end",
    "SessionEnd": "session_end",
    "SubagentStop": "subagent_stop",
    "SubagentStart": "subagent_start",
    "PreCompact": "pre_compact",
    "PostCompact": "post_compact",
}
evt_raw = data.get("hook_event_name", "")
evt = EVENT_MAP.get(evt_raw, "other")

# ---- 公共字段提取（各工具字段差异兜底）----
tool = data.get("tool_name") or data.get("tool") or ""
if not tool and data.get("args"):
    # Codex 某些版本工具名在 args 里
    tool = ""
tool = str(tool).lower()

status = "success"
st = data.get("status")
if isinstance(st, str):
    status = "error" if st.lower() in ("error", "failed", "failure", "blocked") else "success"
elif isinstance(st, bool):
    status = "error" if not st else "success"
# Claude PostToolUse: tool_response.is_error
tr = data.get("tool_response")
if isinstance(tr, dict) and tr.get("is_error"):
    status = "error"
# Codex: result 里可能带 error 标记
res = data.get("result")
if isinstance(res, dict) and (res.get("error") or res.get("is_error")):
    status = "error"

session = data.get("session_id") or data.get("session") or ""
prompt = data.get("prompt") or data.get("user_prompt") or data.get("user_message") or data.get("query") or ""
cwd = data.get("cwd") or data.get("working_directory") or ""

# ---- 细节文本（子代理 / 工具结果）----
detail = ""
role = data.get("child_role") or data.get("subagent_role") or data.get("role") or ""
summary = data.get("child_summary") or data.get("subagent_summary") or data.get("summary") or ""
child_status = data.get("child_status") or data.get("subagent_status") or ""
if role or summary:
    detail = f"{role}|{child_status}|{summary}"

# 输出为 shell 可读的键值对
out = {
    "event": evt, "tool": tool, "status": status, "session": session,
    "detail": detail, "prompt": prompt, "cwd": cwd,
}
for k, v in out.items():
    # 转义单引号防 shell 注入
    v = str(v).replace("'", "'\\''")
    print(f"SEDIMENT_{k.upper()}='{v}'")
PYEOF
)
  rm -f "$pfile"

  # 将归一化结果 eval 为环境变量（脚本内可见）
  eval "$norm" 2>/dev/null || true
}

# 便捷判断：是否属于某事件类型
sediment_is() { [ "$SEDIMENT_EVENT" = "$1" ]; }

# ─── 工具判定（输出格式路由依据）────────────────────────────────────
# 同一套脚本注册到四个工具，输出协议不同（Hermes: {"context"}；Claude/ZCode: {"hookSpecificOutput"}；
# Codex: 不处理注入输出）。注册命令带工具名参数（见 references/agent-hook.md 注册表），
# 未带参数时从 payload 特征兜底推断。
sediment_detect_tool() {
    # 优先注册参数（agent-hook.md 注册表各工具命令第 1 参为工具名）
    if [ "$#" -gt 0 ] && [ -n "$1" ]; then
        SEDIMENT_AGENT="$1"
        return 0
    fi
    # payload 特征兜底：hook_event_name + 字段差异
    local evt_agent=""
    evt_agent=$(echo "${HOOK_PAYLOAD:-}" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
e = d.get('hook_event_name', '')
if e in ('pre_llm_call', 'post_tool_call', 'on_session_end', 'subagent_stop'):
    print('hermes')
elif e == 'SessionEnd':
    print('claude')
elif e == 'Stop':
    print('codex')
elif 'user_prompt' in d:
    print('claude')
elif e in ('user_prompt_submit', 'pre_tool_use', 'post_tool_use'):
    print('codex')
else:
    print('unknown')
" 2>/dev/null)
    SEDIMENT_AGENT="${evt_agent:-unknown}"
}

# 便捷判断：当前工具是否为 Claude 系（Claude Code / ZCode，输出走 hookSpecificOutput 协议）
sediment_is_claude_like() { [ "$SEDIMENT_AGENT" = "claude" ] || [ "$SEDIMENT_AGENT" = "zcode" ]; }
