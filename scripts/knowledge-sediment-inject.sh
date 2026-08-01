#!/bin/bash
# pre_llm_call hook：知识沉淀指令注入（当前对话内即时触发）
# 读取待沉淀标记（JSON：type/detail/session_id）→ 注入针对性指令；无标记 → 静默

marker="$HOME/.hermes/state/knowledge-sediment-hint"
if [ -f "$marker" ]; then
  python3 << 'EOF'
import sys, json, os

marker = os.path.expanduser("~/.hermes/state/knowledge-sediment-hint")
try:
    with open(marker) as f:
        d = json.load(f)
    mtype = d.get("type", "session_end")
    detail = d.get("detail", "")
except Exception:
    mtype, detail = "session_end", ""

if mtype == "code_change":
    instruction = (f"【知识沉淀检查·代码修改】刚修改了 {detail}。执行：加载 qwiki skill，"
                   "按文件路径匹配相关模块卡的「模块边界」→ 更新受影响卡（活知识：与代码同步）；"
                   "如有新的可复用知识点按归属路由建卡；完成后删除标记文件 ~/.hermes/state/knowledge-sediment-hint")
elif mtype == "verify_done":
    instruction = (f"【知识沉淀检查·验证结论】刚执行 {detail} 并成功。若产生验证过的结论（实测数据支撑），"
                   "按归属路由建卡或更新相关卡（个人方法论→personal/，跨项目→projects/common/，项目特定→项目卡）；"
                   "完成后删除标记文件 ~/.hermes/state/knowledge-sediment-hint")
else:
    instruction = ("【知识沉淀检查】上次会话已结束。执行：加载 qwiki skill，用 session_search 检索最近会话知识点"
                   "（验证结论/重复实践/代码修改三类触发源）→ 按归属路由建卡或更新 → 删除标记文件 "
                   "~/.hermes/state/knowledge-sediment-hint")

print(json.dumps({"context": instruction}, ensure_ascii=False))
EOF
fi
exit 0
