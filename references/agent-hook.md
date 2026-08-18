# Hook 机制（qwiki 自发生长基础设施，跨工具）

> 2026-08-02 定稿，2026-08-18 增 ZCode。qwiki 知识自动生成的事件驱动层——hook 是触发器（写标记/注入指令），沉淀是 AI 的活（加载本 skill 执行）。多工具（Hermes/Claude Code/Codex/ZCode）同构，payload 差异由 `scripts/knowledge-sediment-lib.sh` 归一化，工具判定与输出协议由 `sediment_detect_tool` 承担（注册命令第 1 参为工具名）。

## 原理：为什么用 hook 不用 SOUL

- SOUL 是身份/方法论（每会话注入，稳定）——任务逻辑不应污染敏感身份文件
- hook 是事件驱动（工具调用/会话生命周期触发）——任务嵌入事件点，SOUL 零改动
- 分发友好：hook 脚本 + config 注册可随 skill 打包，协作者装上即生效

## 事件全景（多工具事件名 → 归一化类型）

| 归一化事件 | Hermes | Claude Code | Codex | ZCode | 用法 |
|------|------|------|------|------|------|
| `post_tool` | post_tool_call | PostToolUse | PostToolUse | PostToolUse | 信号检测：代码修改/验证成功 → 写标记 |
| `pre_llm` | pre_llm_call | UserPromptSubmit | UserPromptSubmit | UserPromptSubmit | 每轮注入检索引导 + 有标记追加沉淀指令（Codex 不处理输出，沉淀由 Stop 门禁承担） |
| `session_end` | on_session_end | SessionEnd | Stop | Stop | 写"待沉淀"标记（Codex/ZCode Stop 门禁：有标记则 block 强制沉淀） |
| `subagent_stop` | subagent_stop | SubagentStop | SubagentStop | （不支持） | 子代理产出 → 写标记（团队场景沉淀；ZCode 无此事件，不注册） |

## Wire 协议（stdin/stdout）

- **stdin**（JSON 管道）：`{"hook_event_name": "...", "session_id": "...", "cwd": "...", ...事件特定字段}`——事件字段在**顶层**，无 `extra` 嵌套（源码 hooks.py 确认，2026-08-02 修 B3）
  - `post_tool_call` 顶层字段：`tool_name/args/result/status/duration_ms/task_id/tool_call_id`
  - `subagent_stop` 顶层字段：`parent_session_id/child_role/child_summary/child_status/tool_call_history/duration_ms`
- **stdout**（JSON 可选，按工具协议分支，由 `sediment_detect_tool` 判定）：
  - `pre_llm_call`（Hermes）：`{"context": "..."}` → 注入 LLM 上下文
  - `UserPromptSubmit`（Claude Code / ZCode）：`{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "..."}}` → 注入 LLM 上下文（ZCode 与 Claude 同协议，inject.sh 已分支输出）
  - `Stop`（Codex / ZCode）：`{"decision": "block", "reason": "..."}` → 强制 AI 继续执行沉淀（两工具同协议，hint.sh 输出兼容）
  - `pre_tool_call`（Hermes/Claude）：`{"decision": "block", ...}` → 拦截
  - 空/非匹配 JSON → 静默
  - **注意**：Codex `UserPromptSubmit` 不处理 hook 输出（静默忽略，inject.sh 对该工具不输出）；ZCode 不支持 `SubagentStop` 事件

## 注册（三工具注册表，2026-08-02 跨工具落地）

> 同一套脚本（`scripts/knowledge-sediment-*.sh`），多种注册方式。payload 差异由 `knowledge-sediment-lib.sh` 归一化（事件名/字段映射），工具判定与输出协议由 `sediment_detect_tool` 承担（注册命令第 1 参为工具名，如 `bash <script> zcode`），脚本本身工具无关。

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

### ZCode（~/.zcode/cli/config.json）

> ZCode hook 与 Claude Code 事件同名同协议（PostToolUse/UserPromptSubmit/Stop），配置在 `~/.zcode/cli/config.json`（或项目级 `.zcode/config.json`）顶层 `hooks` 键，**默认禁用，须 `"enabled": true` 才生效**；无信任门槛。ZCode 不支持 `SubagentStop`，故 subagent.sh 不注册。
> 输出协议：注入用 `hookSpecificOutput.hookEventName + additionalContext`（inject.sh 已分支）；Stop 门禁 `{"decision":"block","reason"}` 与 Codex 同协议（ZCode 内建最多 3 次续跑）。

```json
{
  "hooks": {
    "enabled": true,
    "events": {
      "UserPromptSubmit": [
        {"hooks": [{"type": "command", "command": "bash ~/.zcode/scripts/knowledge-sediment-inject.sh zcode"}]}
      ],
      "PostToolUse": [
        {"hooks": [{"type": "command", "command": "bash ~/.zcode/scripts/knowledge-sediment-toolcheck.sh zcode"}]}
      ],
      "Stop": [
        {"hooks": [{"type": "command", "command": "bash ~/.zcode/scripts/knowledge-sediment-hint.sh zcode"}]}
      ]
    }
  }
}
```

> **ZCode 注意事项**：
> - matcher 匹配值是工具名（大小写敏感，`Bash`/`Write`/`Edit` 等）——上面注册不带 matcher，匹配全部工具，与其余三工具行为一致；toolcheck.sh 已兼容 Claude/ZCode 工具名（Write/Edit/ApplyPatch/Bash）
> - `command` 的 `timeout` 单位是**秒**（qwiki 脚本是轻量标记/注入，默认 60s 足够）
> - 首次配置后新会话生效；`Stop` 的 block 最多 3 次续跑（Codex 是 8 次），标记多时 AI 优先在会话内消化沉淀

### Codex（hooks.json）

> Codex hook 配置文件为 `~/.codex/hooks.json`（用户级）或项目级 `.codex/hooks.json`。
> 事件名 PascalCase，三层 JSON 结构：event → entries(matcher) → hooks[] 数组。
> **注意**：Codex `UserPromptSubmit` 不处理 hook 输出（静默忽略），`additionalContext` 不被支持。
> 沉淀注入通过 `Stop` 事件的 `decision: "block"` + `reason` 强制 AI 在结束前执行沉淀（Stop 门禁模式）。
> 因此 `inject.sh` **不注册**到 Codex（避免标记被提前消费，Stop 门禁看不到）。

```json
{
  "hooks": {
    "PostToolUse": [
      {"hooks": [{"type": "command", "command": "bash ~/.codex/scripts/knowledge-sediment-toolcheck.sh"}]}
    ],
    "Stop": [
      {"hooks": [{"type": "command", "command": "bash ~/.codex/scripts/knowledge-sediment-hint.sh"}]}
    ],
    "SubagentStop": [
      {"hooks": [{"type": "command", "command": "bash ~/.codex/scripts/knowledge-sediment-subagent.sh"}]}
    ]
  }
}
```

> **Stop 门禁模式**（hint.sh 在 Codex 上的特殊行为）：
> 读队列标记 → 有标记且 `stop_hook_active=false` → 输出 `{"decision":"block","reason":"沉淀指令"}` → 强制 AI 在结束前执行沉淀 → 连续 block 8 次后 CLI 自动放行。
> `stop_hook_active` 从原始 payload 提取（防无限循环）。
>
> **Codex 事件名实证**（hooks.json + dump 确认，2026-08-02）：
> `UserPromptSubmit`/`PostToolUse`/`PreToolUse`/`Stop`/`SessionEnd`/`SubagentStop`/`SubagentStart`/`PreCompact`/`PostCompact`。
> payload 字段 snake_case（`session_id`/`cwd`/`prompt`/`tool_name`/`stop_hook_active`/`last_assistant_message`）。
> 首次启用需 trust（`codex` TUI hooks 管理或 `--dangerously-bypass-hook-trust` 仅自动化场景）。

## 沉淀链路（标记 → 注入 → 执行）

```
队列目录 ${XDG_STATE_HOME:-~/.local/state}/qwiki/sediment/（每个事件一个 JSON 文件：<纳秒时间戳>-<type>.json，路径定义于 lib.sh SEDIMENT_QUEUE_DIR）
  type=code_change  代码修改（含文件路径）→ 注入"按模块边界匹配更新卡"
  type=verify_done  验证成功（含命令）   → 注入"结论按归属路由沉淀"
  type=session_end  会话结束            → 注入"检索最近会话知识点"
  type=subagent_done 子代理产出         → 注入"检查子代理产出知识点"
inject.sh 读取全部标记 → 合并为一条指令注入（Hermes 走 context，Claude/ZCode 走 hookSpecificOutput.additionalContext）→ 读后即删（确定性生命周期，不依赖 AI 清除）
  ⚠ Codex：inject.sh 不注册（UserPromptSubmit 输出被忽略，且读后即删会提前消费标记）
  Codex / ZCode 的沉淀注入由 hint.sh Stop 门禁承担（Stop 时读标记 → block 强制沉淀；ZCode 内建最多 3 次续跑）
执行：加载本 skill → 按归属路由建卡/更新（个人→personal/，跨项目→projects/common/，项目→项目卡）
```

## 坑

- **heredoc 覆盖 stdin**：`cat | python3 << 'EOF'` 中 python 的 stdin 是 heredoc（读到代码本身）——payload 必须经环境变量传递（`export HOOK_PAYLOAD="$payload"` + `os.environ`）
- `hermes hooks test --payload-file` 的默认 payload 固定 `tool_name=terminal`（--for-tool 只影响 matcher 不改变 payload）——模拟测试要传完整 payload
- 注入会 append 到 user message——指令要精炼（一次沉淀动作），inject 读后即删避免重复注入
- **队列目录设计**：每个事件写独立文件（纳秒时间戳前缀），避免快速连续事件互相覆盖；inject 一次性消费全部标记
