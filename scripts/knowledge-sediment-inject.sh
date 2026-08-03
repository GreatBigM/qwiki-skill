#!/bin/bash
# pre_llm_call / UserPromptSubmit hook：检索引导 + 沉淀指令注入
# 兼容 Hermes / Claude Code / Codex（payload 经归一化层统一）
#
# 输出协议：{"context": "..."} → 注入 LLM 上下文
# 注意：Codex UserPromptSubmit 不处理 hook 输出（静默忽略），
#       Codex 的沉淀注入由 hint.sh Stop 门禁承担
#
# 职责：
#   1. 无条件：注入"先查知识库"检索引导
#   2. 有标记：追加沉淀指令（队列读后即删）

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=knowledge-sediment-lib.sh
source "$SELF_DIR/knowledge-sediment-lib.sh"

command -v python3 &>/dev/null || exit 0

# 读 stdin（hook 协议）
payload=$(cat)
export HOOK_PAYLOAD="$payload"

sediment_normalize_payload

# 仅处理 LLM 调用前事件
sediment_is "pre_llm" || exit 0

# ---- 输出构造 ----
python3 - "$SEDIMENT_QUEUE_DIR" "$SEDIMENT_PROMPT" <<'PYEOF'
import json, os, sys

qdir, prompt = sys.argv[1], sys.argv[2]

# 检索引导（固定注入，每轮生效）——检索链单一真相源在此
guide = "【知识库检索】涉及项目/技术/历史问题先查 ~/qwiki：INDEX.md（全局目录）→ 知识文件（projects/<项目>/ 或 personal/）→ 相关卡；查不到再凭经验或 web。沉淀规则：验证结论/代码修改/子代理产出自动写卡（≤5 页/会话）。"

# 沉淀指令（有标记才追加）
instr = ""
try:
    files = sorted(os.listdir(qdir)) if os.path.isdir(qdir) else []
except Exception:
    files = []

if files:
    marks = []
    for fn in files:
        try:
            with open(os.path.join(qdir, fn)) as f:
                m = json.load(f)
            marks.append(m)
        except Exception:
            continue
    if marks:
        types = [m.get("type", "?") for m in marks]
        details = [m.get("detail", "") for m in marks if m.get("detail")]
        t_sum = "/".join(sorted(set(types)))
        instr = f"【知识沉淀待执行】检测到沉淀标记（{t_sum}）。执行：①按归属路由建卡或更新（个人→personal/，跨项目→projects/common/，项目→项目卡）②更新 INDEX ③git commit。细节：{' | '.join(d[:120] for d in details)}"
        # 读后即删（确定性生命周期）
        for fn in files:
            try:
                os.remove(os.path.join(qdir, fn))
            except Exception:
                pass

ctx = guide
if instr:
    ctx += "\n" + instr

print(json.dumps({"context": ctx}, ensure_ascii=False))
PYEOF

exit 0
