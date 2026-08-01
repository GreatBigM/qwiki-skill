#!/bin/bash
# pre_llm_call hook：知识沉淀指令注入（当前对话内即时触发）
# 读取队列目录中所有待沉淀标记 → 合并为一条指令注入 → 读后即删（确定性生命周期，不依赖 AI 清除）

QUEUE_DIR="$HOME/.hermes/state/knowledge-sediment"
# python3 缺失时静默退出（hook 不应阻塞主流程）
command -v python3 &>/dev/null || exit 0
[ -d "$QUEUE_DIR" ] && [ -n "$(ls -A "$QUEUE_DIR" 2>/dev/null)" ] && python3 << 'EOF'
import sys, json, os, glob

queue_dir = os.path.expanduser("~/.hermes/state/knowledge-sediment")
markers = sorted(glob.glob(os.path.join(queue_dir, "*.json")))
if not markers:
    sys.exit(0)

instructions = []
for path in markers:
    try:
        with open(path) as f:
            d = json.load(f)
        mtype = d.get("type", "session_end")
        detail = d.get("detail", "")
    except Exception:
        mtype, detail = "session_end", ""

    if mtype == "code_change":
        instructions.append(f"• 代码修改（{detail}）：按文件路径匹配相关模块卡的「模块边界」→ 更新受影响卡")
    elif mtype == "verify_done":
        instructions.append(f"• 验证成功（{detail}）：若产生验证过的结论，按归属路由建卡或更新相关卡")
    elif mtype == "subagent_done":
        instructions.append(f"• 子代理产出（{detail}）：检查产出中的可沉淀知识点")
    else:
        instructions.append("• 上次会话已结束：检索最近会话知识点（验证结论/重复实践/代码修改）→ 按归属路由建卡或更新")

    # 读后即删——确定性消费，不依赖 AI 行为
    try:
        os.remove(path)
    except OSError:
        pass

if instructions:
    combined = ("【知识沉淀检查】以下事件待沉淀（加载 qwiki skill 执行，归属路由：个人→personal/，"
                "跨项目→projects/common/，项目→项目卡）：\n" + "\n".join(instructions))
    print(json.dumps({"context": combined}, ensure_ascii=False))
EOF
exit 0
