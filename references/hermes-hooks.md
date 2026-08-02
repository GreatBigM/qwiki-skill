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

- **stdin**（JSON 管道）：`{"hook_event_name": "...", "session_id": "...", "cwd": "...", ...事件特定字段}`——事件字段在**顶层**，无 `extra` 嵌套（源码 hooks.py 确认，2026-08-02 修 B3）
  - `post_tool_call` 顶层字段：`tool_name/args/result/status/duration_ms/task_id/tool_call_id`
  - `subagent_stop` 顶层字段：`parent_session_id/child_role/child_summary/child_status/tool_call_history/duration_ms`
- **stdout**（JSON 可选）：`{"context": "..."}` → pre_llm_call 注入 LLM 上下文；`{"decision": "block", ...}` → pre_tool_call 拦截；空/非匹配 JSON → 静默

## 注册（三工具注册表，2026-08-02 跨工具落地）

> 同一套脚本（`scripts/knowledge-sediment-*.sh`），三种注册方式。payload 差异由 `knowledge-sediment-lib.sh` 归一化（事件名/字段映射），脚本本身工具无关。

### Hermes（config.yaml）

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

### Claude Code（settings.json）

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {"hooks": [{"type": "command", "command": "~/.claude/scripts/knowledge-sediment-inject.sh"}]}
    ],
    "PostToolUse": [
      {"hooks": [{"type": "command", "command": "~/.claude/scripts/knowledge-sediment-toolcheck.sh"}]}
    ],
    "SessionEnd": [
      {"hooks": [{"type": "command", "command": "~/.claude/scripts/knowledge-sediment-hint.sh"}]}
    ],
    "SubagentStop": [
      {"hooks": [{"type": "command", "command": "~/.claude/scripts/knowledge-sediment-subagent.sh"}]}
    ]
  }
}
```

> Claude 已有 `UserPromptSubmit → codegraph prompt-hook`（检索引导）——可保留（代码检索引导）或替换为本 inject.sh（知识库检索引导），二选一或并存（inject 先跑输出 context，codegraph 再补充）。

### Codex（config.toml）

```toml
[hooks]
  [hooks.UserPromptSubmit]
  command = "~/.codex/scripts/knowledge-sediment-inject.sh"
  [hooks.PostToolUse]
  command = "~/.codex/scripts/knowledge-sediment-toolcheck.sh"
  [hooks.SessionEnd]
  command = "~/.codex/scripts/knowledge-sediment-hint.sh"
  [hooks.SubagentStop]
  command = "~/.codex/scripts/knowledge-sediment-subagent.sh"
```

> Codex hooks 语法以 `codex --help` + 官方 config 文档为准（0.146.0 已确认事件枚举 PreToolUse/PostToolUse/SessionEnd/SubagentStop/UserPromptSubmit/PreCompact/PostCompact）。

## 沉淀链路（标记 → 注入 → 执行）

```
队列目录 ~/.hermes/state/knowledge-sediment/（每个事件一个 JSON 文件：<纳秒时间戳>-<type>.json）
  type=code_change  代码修改（含文件路径）→ 注入"按模块边界匹配更新卡"
  type=verify_done  验证成功（含命令）   → 注入"结论按归属路由沉淀"
  type=session_end  会话结束            → 注入"检索最近会话知识点"
  type=subagent_done 子代理产出         → 注入"检查子代理产出知识点"
inject.sh 读取全部标记 → 合并为一条指令注入 → 读后即删（确定性生命周期，不依赖 AI 清除）
执行：加载本 skill → 按归属路由建卡/更新（个人→personal/，跨项目→projects/common/，项目→项目卡）
```

## 坑

- **heredoc 覆盖 stdin**：`cat | python3 << 'EOF'` 中 python 的 stdin 是 heredoc（读到代码本身）——payload 必须经环境变量传递（`export HOOK_PAYLOAD="$payload"` + `os.environ`）
- `hermes hooks test --payload-file` 的默认 payload 固定 `tool_name=terminal`（--for-tool 只影响 matcher 不改变 payload）——模拟测试要传完整 payload
- 注入会 append 到 user message——指令要精炼（一次沉淀动作），inject 读后即删避免重复注入
- **队列目录设计**：每个事件写独立文件（纳秒时间戳前缀），避免快速连续事件互相覆盖；inject 一次性消费全部标记
