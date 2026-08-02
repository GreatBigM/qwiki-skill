#!/bin/bash
# knowledge-sediment-lib.sh — 三工具 hook payload 统一归一化层（Hermes/Claude Code/Codex）
# 被 knowledge-sediment-{hint,toolcheck,inject,subagent}.sh source
# 职责：读 stdin JSON → 归一化为统一事件类型 + 提取公共字段
# 用法：`source knowledge-sediment-lib.sh` 后调用 `sediment_normalize_payload`
#
# 归一化结果（全局变量，函数内 export 或显式读取）：
#   SEDIMENT_EVENT    : 统一事件类型 session_end | code_change | verify_done | subagent_done | other
#   SEDIMENT_TOOL     : 工具名（小写）
#   SEDIMENT_STATUS   : 工具状态 success | error
#   SEDIMENT_SESSION  : session_id
#   SEDIMENT_DETAIL   : 事件细节文本（工具结果摘要 / 子代理信息 / 空）
#   SEDIMENT_PROMPT   : 用户 prompt（pre_llm_call / UserPromptSubmit 用）
#   SEDIMENT_CWD      : 工作目录

sediment_normalize_payload() {
  # 读 stdin（heredoc 保护：hook 脚本内 stdin 已被 consume，用环境变量传入）
  local payload="${HOOK_PAYLOAD:-$(cat)}"

  # python3 归一化：三工具事件名/字段差异在此收敛
  local norm
  norm=$(python3 - "$payload" <<'PYEOF'
import json, sys, re

raw = sys.argv[1] if len(sys.argv) > 1 else ""
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
    # Claude Code (PascalCase)
    "PostToolUse": "post_tool",
    "UserPromptSubmit": "pre_llm",
    "SessionEnd": "session_end",
    "SubagentStop": "subagent_stop",
    "SessionStart": "session_start",
    "PreCompact": "pre_compact",
    "PostCompact": "post_compact",
    "PreToolUse": "pre_tool",
    # Codex (PascalCase)
    "PreToolUse": "pre_tool",
    "PostToolUse": "post_tool",
    "UserPromptSubmit": "pre_llm",
    "SessionEnd": "session_end",
    "SubagentStop": "subagent_stop",
    "SessionStart": "session_start",
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
prompt = data.get("prompt") or data.get("user_message") or data.get("query") or ""
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

  # 将归一化结果 eval 为环境变量（脚本内可见）
  eval "$norm" 2>/dev/null || true
}

# 便捷判断：是否属于某事件类型
sediment_is() { [ "$SEDIMENT_EVENT" = "$1" ]; }
