# Hermes Hook 机制（qwiki 自发生长基础设施）

> 2026-08-01 定稿。qwiki 知识自动生成的事件驱动层——hook 是触发器（写标记/注入指令），沉淀是 AI 的活（加载本 skill 执行）。

## 原理：为什么用 hook 不用 SOUL

- SOUL 是身份/方法论（每会话注入，稳定）——任务逻辑不应污染敏感身份文件
- hook 是事件驱动（工具调用/会话生命周期触发）——任务嵌入事件点，SOUL 零改动
- 分发友好：hook 脚本 + config 注册可随 skill 打包，协作者装上即生效

## 事件全景（VALID_HOOKS，agent 源码 plugins.py）

| 事件 | 时机 | 用法 |
|------|------|------|
| `post_tool_call` | 每次工具调用后 | 信号检测：代码修改/验证成功 → 写标记 |
| `pre_llm_call` | 每次 LLM 调用前 | 有标记 → 注入 `{"context": "指令"}`（append 到 user message，缓存前缀稳定） |
| `on_session_end` | 会话结束时 | 写"待沉淀"标记（下次会话补沉淀） |
| `subagent_stop` | 子代理完成 | 子代理产出 → 写标记（团队场景沉淀） |
| `pre_tool_call` / `post_llm_call` / `on_session_start` / `transform_*` | — | 按需扩展（信号检测/统计阈值等） |

## Wire 协议（stdin/stdout）

- **stdin**（JSON 管道）：`{"hook_event_name": "...", "session_id": "...", "cwd": "...", "extra": {...}, ...事件特定字段}`
  - `post_tool_call` extra：`tool_name/args/result/status/duration_ms/task_id`
- **stdout**（JSON 可选）：`{"context": "..."}` → pre_llm_call 注入 LLM 上下文；`{"decision": "block", ...}` → pre_tool_call 拦截；空/非匹配 JSON → 静默

## 注册（config.yaml）

```yaml
hooks:
  on_session_end:
    - command: ~/.hermes/scripts/knowledge-sediment-hint.sh
  post_tool_call:
    - command: ~/.hermes/scripts/knowledge-sediment-toolcheck.sh
  pre_llm_call:
    - command: ~/.hermes/scripts/knowledge-sediment-inject.sh
  subagent_stop:
    - command: ~/.hermes/scripts/knowledge-sediment-subagent.sh
```

首次触发需 consent（allowlist `~/.hermes/shell-hooks-allowlist.json`）；非 TTY 需 `hooks_auto_accept: true` 或 `--accept-hooks`。验证：`hermes hooks list / test <event> / doctor`。

## 沉淀链路（标记 → 注入 → 执行）

```
标记文件 ~/.hermes/state/knowledge-sediment-hint（JSON：type/detail/session_id）
  type=code_change  代码修改（含文件路径）→ 注入"按模块边界匹配更新卡"
  type=verify_done  验证成功（含命令）   → 注入"结论按归属路由沉淀"
  type=session_end  会话结束            → 注入"检索最近会话知识点"
  type=subagent_done 子代理产出         → 注入"检查子代理产出知识点"
执行：加载本 skill → 按归属路由建卡/更新（个人→personal/，跨项目→projects/common/，项目→项目卡）→ 清标记
```

## 坑

- **heredoc 覆盖 stdin**：`cat | python3 << 'EOF'` 中 python 的 stdin 是 heredoc（读到代码本身）——payload 必须经环境变量传递（`export HOOK_PAYLOAD="$payload"` + `os.environ`）
- `hermes hooks test --payload-file` 的默认 payload 固定 `tool_name=terminal`（--for-tool 只影响 matcher 不改变 payload）——模拟测试要传完整 payload
- 注入会 append 到 user message——指令要精炼（一次沉淀动作），执行完清标记避免重复注入
