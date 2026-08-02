---
name: qwiki
description: Use when user says qwiki. Knowledge base management.
version: 1.9.0
author: Hermes Agent
license: MIT
category: knowledge
metadata:
  hermes:
    tags: [knowledge-base, wiki, projects]
    triggers: [qwiki, 知识库, 知识管理, wiki, 知识检索, 知识同步, 项目入驻, 知识卡片]
    related_skills: []
---

# Qwiki — 知识库管理

## ⚡ 使用方式（AI 替你完成）

**本技能的使用方式是：用户指挥 AI，AI 替用户执行。用户不面对命令行。**

```
用户: qwiki import <项目> / 把项目录入知识库 / 同步知识库
AI:  加载本 skill → 识别操作 → 检查依赖（git/目录）
AI:  对话层引导用户确认缺失项（git init?）
用户: 确认/拒绝
AI:  执行操作 → 回报结果
```

**铁律：用户给出意图 → AI 识别操作并直接执行，不反问"你要不要先做环境准备"。**
依赖缺失 → AI 对话层引导用户设定，拿齐就干。

> **AI 交互约定（agent 必读）**：
> - 操作识别：用户说 "qwiki <操作>" 或自然语言意图（录入/同步/检索知识库），映射到九操作
> - 依赖引导：环境依赖（git 未初始化）→ 对话层询问用户是否处理，不静默跳过
> - 交互式设定优先：涉及路径/项目名等参数，AI 问清后写入，不让用户手动敲命令
> - 执行回报：操作完成 + 关键结果（新卡片数/INDEX 更新/commit）

## 操作路由

| 输入 | 操作 | 参数 |
|------|------|------|
| qwiki init | init | 无 |
| qwiki deinit | deinit | 无 |
| qwiki import <项目> | import | 项目名 |
| qwiki migrate <项目> | migrate | 项目名 |
| qwiki delete <项目> | delete | 项目名 |
| qwiki sync [项目] | sync | 可选，缺省全部 |
| qwiki explore [关键词] | explore | 可选 |
| qwiki note <标题> | note | 笔记标题 |
| qwiki status | status | 无 |

> 知识生成（蒸馏建卡）是日常任务的自发行为，无命令触发——干活读透模块顺手沉淀。migrate 仅用于存量知识批量整理（历史 references 升级为卡片），非生产动作。

---

## init — 全局初始化（创世，一次）

创建 ~/qwiki/ 骨架 + INDEX.md + personal/。

0. **幂等检查**：`[ -d ~/qwiki ]`
   - 不存在 → 继续
   - 已存在 → 提示"qwiki 知识库已存在（~/qwiki/）"，询问"是否重新初始化？（将覆盖 INDEX.md 和 ROUTING.md，知识文件保留）"
   - 用户拒绝 → 退出
   - 用户同意 → 备份旧 INDEX.md/ROUTING.md 为 .bak，继续
1. `mkdir -p ~/qwiki/personal ~/qwiki/projects/common`
2. `cd ~/qwiki && git init`
3. 创建 INDEX.md（按 `templates/index.md` 模板生成：空表 + personal 分区 + 维护规则脚注）
4. 创建 ROUTING.md（按 `templates/routing.md` 模板生成：检索链 + 降级路径 + 自生长规则 + 腐化检测 + 模板指引）
5. 创建 SCHEMA.md（按 `templates/schema.md` 模板生成：宪法——目录结构/命名/纯度/卡片公约）
6. 创建 HISTORY.md（按 `templates/history.md` 模板生成：大事记档案——方法论定稿/架构决策/实践结论，事件粒度）
7. `cd ~/qwiki && git add -A && git commit -m "init qwiki"`
8. **hook 注册检测**（自发生长事件驱动层，跨工具通用）：
   - 检测当前工具（Hermes `~/.hermes/config.yaml` / Claude `~/.claude/settings.json` / Codex `~/.codex/config.toml`）
   - 检查该工具 hooks 是否已注册 knowledge-sediment 脚本（session_end/post_tool/pre_llm/subagent）
   - 缺失 → 提示"知识自动沉淀依赖 hook 事件驱动（每轮检索引导 + 代码修改即时感知 + 会话结束补沉淀）。是否注册？"→ Y → 按 `references/hermes-hooks.md` 的注册表配置 + 复制 `scripts/knowledge-sediment-*.sh` 到工具 scripts 目录

> **跨工具说明**：知识库本体（~/qwiki/）与工具无关，任何 agent（Hermes / Claude Code / Codex）都能读写。hook 事件驱动层三工具同构（事件名归一化由 `scripts/knowledge-sediment-lib.sh` 承担），检索引导由 inject.sh 每轮注入——SOUL.md 无需声明检索链（方案 A 定稿，2026-08-02）。

---

## deinit — 全局拆除

1. 确认操作
2. **hook 清理**（与 init 注册对称）：
   - 从当前工具的 hooks 配置移除 knowledge-sediment 注册项
   - 删除 scripts 目录的 `knowledge-sediment-*.sh`
   - 清空标记队列 `rm -rf ~/.hermes/state/knowledge-sediment/`
3. `cd ~/qwiki && cd .. && mv qwiki qwiki.bak.$(date +%Y%m%d)`

---

## import — 项目入驻（新增，保持纯粹）

新项目从零入驻：AI 四轮阅读 SDK → 项目卡骨架 → 目录骨架 → INDEX 登记。**不含卡片化**（卡片归 migrate 和日常蒸馏时机）。

输入：项目名、代码路径（可选——不依赖用户提供，见下）。

### 核心原则（2026-07-31 讨论定稿，2026-08-02 去 codegraph/AGENTS 依赖）

1. **AI 读 SDK 本身就是在做 import**——用户不是信息源，只在"审阅初版"介入一次。用户提供不了编译入口/环境是常态，不阻塞流程
2. **多信号源交叉**——无环境也能得出可靠工程划分：

| 信号 | 获取方式 | 环境依赖 |
|------|---------|---------|
| 目录结构 | ls / search_files | 无 |
| 构建足迹 | Makefile/CMakeLists/Kconfig/feeds | 无 |
| CI 配置 | .github/.gitlab-ci/Jenkinsfile（金矿：机器可读的编译流程） | 无 |
| 源码阅读 | search_files + read_file（符号/调用链逐层追） | 无 |
| manifest | repo 工具文件 | 无 |

3. **项目知识卡是逐步迭代的活文档**——import 只给"可用的初版 + 迭代机制"，允许不完整但必须标注待验证项；任务完成/认知加深/踩坑时更新（与 ROUTING 自生长规则同构）

### 四轮阅读法（AI 读 SDK 的编排）

```
第一轮：这是什么项目？   → 根目录结构/README/manifest/配置文件 → 项目概况
第二轮：怎么编译？       → 构建系统文件/CI/toolchain 痕迹 → 编译入口候选(置信度标注)
第三轮：核心模块是什么？ → search_files/read_file 追主入口/核心符号 → 分层架构
第四轮：哪里坑？怎么干活？→ 特殊机制/调试相关代码 → 工作流 + 特殊机制
```

每轮阅读必须伴随**验证动作**（编译跑通/代码互证/交叉引用），不验证的读等于没读——读到的结论都要有验证痕迹。

### 步骤

1. **现状检查**（先诊断后行动）：`ls <代码路径>/` — 已有项目知识卡 → 进入「补充」模式：diff 检查是否过时，按 `templates/card.md` 补齐缺失章节
2. **四轮阅读 SDK**（上表；编译入口按置信度分级：用户提供 > CI 配置 > 构建足迹 > 静态推导标注待验证）
3. **项目卡初版**：工程划分用多信号源交叉，编译相关章节标注"静态推导，待验证"
4. `mkdir -p ~/qwiki/projects/<项目名>/`
5. INDEX 追加项目区块
6. 提示"项目 <项目名> 入驻完成：项目卡初版（含待验证清单）。若存在历史知识（references/design 等），执行 qwiki migrate <项目名> 做老知识迁移。"

---

## migrate — 主动迁移（老知识升级）

import 之后接力执行：检测项目历史知识（references/design/archive 等 v2 遗产），迁移整理为 v4 卡片体系。

1. **老知识盘点**：`ls ~/qwiki/projects/<项目>/references|design|archive/` + INDEX 现有登记，确认遗产规模
2. **核心模块识别**：高频调试/知识最丰富者优先，一次 1-3 个模块
3. **蒸馏建卡**（`templates/card.md` 八段模板）：
   - 模块边界：search_files 确认文件清单
   - 素材：memory + 已有 references + 代码验证
   - 卡片是「导航 + 核心事实」，细节指向 references（相关卡片段），不搬运全文
4. **INDEX 回填**：新卡登记 + 核心 references 补登记（旧日志/单次分析类按自然淘汰）
5. `cd ~/qwiki && git commit -m "migrate <项目>: <N> 张卡 + INDEX 回填"`
6. 提示"项目 <项目名> 迁移完成：N 张卡，INDEX 回填 M 条。"

无老知识时：提示"未检测到历史知识，无需迁移。"

---

## delete — 项目退出

1. 确认操作
2. INDEX 删行
3. `cd ~/qwiki && git rm -r projects/<项目名> && git commit -m "delete <项目名>"`

---

## sync — 日常同步

1. **宪法同步检查**（模板 ↔ 实例防漂移，见架构文档节）：对比 `~/qwiki/SCHEMA.md` 与 skill 模板 `templates/schema.md` 关键节（卡片身份/迁移规则/知识互联），发现语义漂移 → 报告用户确认后同步
2. 一致性校验（报告修复）：
   - INDEX 死链/漏登记（登记行指向的文件是否存在）
   - **双链死链检测**：扫描全库 `[[...]]` 目标，对照知识库文件表（slug/项目-slug），报告悬空链接（见 `~/qwiki/SCHEMA.md` §知识互联）
3. **防腐化判定**（按 `~/qwiki/SCHEMA.md` §卡片身份 活知识原则）：
   - 死链清单 → 修正引用
   - 与代码/实测矛盾的卡 → 修正内容
   - 完全不符合现实的卡 → 提出销毁建议（确认后删）
   - 孤岛（零入链）→ 标记冷门保留，不销毁
4. `cd ~/qwiki && git add -A && git commit -m "sync $(date +%Y%m%d)"`（有变更时）

---

## explore — 知识检索

`qwiki explore <关键词>` — 语义匹配 INDEX 条目，按匹配度排序。

1. 搜索 INDEX.md 所有条目的标题+总结，语义匹配
2. 结果展示：
   - 匹配度高的前三条 → 列出标题+总结，用户选一条加载
   - 第四条固定为 chat 选项 → "直接对话，让 AI 检索"
     AI 帮用户整理提示词、确认信息 → 确认后重新语义匹配 INDEX → 重复搜索动作
3. 用户选择 → 加载对应知识文件或进入对话检索
4. 无匹配 → "知识库中未找到相关条目，自动回落 web_search"

`qwiki explore` — 输出 INDEX 全文概览

---

## note — 随手笔记（随笔卡）

`qwiki note <标题>` → 按 `templates/note.md` 创建 `~/qwiki/personal/<slug>.md` → INDEX 加一行。

- **自动判断模式（自发生长）**：三触发源出现时 AI 直接建卡/更新，不等用户命令——
  ① 验证结论产生（实测/分析出结论）② 重复实践未命中知识点（查 INDEX 无对应卡且实践再现）③ 代码修改后对应卡需更新
- **hook 事件驱动层**（善用 hook，任务嵌入事件点，跨工具通用）：`scripts/knowledge-sediment-*.sh` 注册到当前工具 hooks（Hermes config.yaml / Claude settings.json / Codex config.toml）——session_end 写标记 / post_tool 信号检测 / pre_llm 每轮注入检索引导+读队列沉淀指令 / subagent_stop 子代理产出——标记写入队列目录 `~/.hermes/state/knowledge-sediment/`，inject 读后即删。三工具 payload 经 `scripts/knowledge-sediment-lib.sh` 归一化（一个脚本吃三种），机制说明见 `references/hermes-hooks.md`
- **知识归属路由**（决定卡放哪）：
  - 个人方法论/工作哲学 → `~/qwiki/personal/`
  - 跨项目知识（反模式/通用经验/工具坑，来源项目、适用多项目）→ `~/qwiki/projects/common/`
  - 项目特定知识 → 对应项目卡或 `references/`
- **必填动作**（生成时自动做，三处一次填齐同一字符串）：YAML summary（真相源）+ 正文 `>` 行（渲染副本）+ INDEX 登记行
- YAML 头按公约：title/type/date 必填 + summary 真相源 + tags
- 相关段用 `[[slug]]` 双链（文档级链接，见 `~/qwiki/SCHEMA.md` §知识互联）
- 正文段落为参考骨架（背景/要点/结论），按需取舍，**不强制 schema**——写什么算什么，后续可随时补充
- 卡片身份：note 是随笔卡（个人来源），与 card 模块卡（项目来源）同一身份；按需演进为模块卡（结构扩展，公约与链接不变）
- 和 import 的区别：note 无项目目录，一条 INDEX 行 + 一个 .md
- 写完后 `cd ~/qwiki && git add -A && git commit -m "note: <标题>"`

---

## status — 查看状态

INDEX 条目数、已入驻项目、知识文件数。

---

## 知识文件模板（八段）

模块边界 / 职责描述 / 架构设计 / 技术栈 / 代码规范 / 配置命令 / 模块间关系 / 相关

> 卡片公共约定（见 `~/qwiki/SCHEMA.md` §卡片身份）：YAML 头（title/type/date 必填 + summary 真相源）+ 一句话总结 + `[[slug]]` 双链 + 相关段。card=模块卡（八段），note=随笔卡（自由正文），同一身份不同形态。

## 架构文档

- **SCHEMA.md**（`~/qwiki/SCHEMA.md`）= **做成什么样**：知识库宪法（目录结构/命名/纯度/卡片公约：YAML 头、卡片身份、知识互联）——目标态定义，真相源在知识库内，init 时由 `templates/schema.md` 创建
- **本 SKILL.md** = **怎么做**：九操作流程——实现 SCHEMA 目标态的方法
- 平级关系（2026-08-01 定稿）：SKILL 的每个操作都在实现 SCHEMA 定义的目标态（init 按蓝图建库、note 按卡片公约生成、import 按目录结构入驻），两者互补不重叠

### 模板 ↔ 实例同步（2026-08-02 定稿，防漂移）

- **模板（`templates/schema.md`）只服务 init**：新库创建时按模板生成实例；已初始化知识库的 SCHEMA.md 是**活的宪法**，演进只发生在实例侧
- 模板更新 ≠ 已初始化库自动跟随——**同步义务**：
  1. 改模板（skill 侧变更）时，若影响既有实例语义（如 HISTORY.md 限定词），**必须同步修改 `~/qwiki/SCHEMA.md` 对应节**
  2. sync 操作增加「宪法同步检查」：对比实例 SCHEMA.md 与模板 schema.md 的关键节（卡片身份/迁移规则），发现漂移 → 报告用户确认后同步
- 原则：**模板是 init 快照，实例是活文档**——两者允许短暂漂移，但关键语义变更（卡片公约/防腐化规则）必须手动同步，不能等腐化检测兜底

### 解耦声明（2026-08-02 定稿，v1.9.0）

- **本 skill 与 AGENTS.md / codegraph 无关**：不生成 AGENTS.md、不依赖 codegraph 索引、references 不含 codegraph-quickstart.md
- 代码检索由各工具自身能力承担（search_files/read_file 或工具内置代码索引如 codegraph MCP）——qwiki 只管理知识库本体（~/qwiki/）
- 检索引导由 hook 注入（inject.sh 每轮注入"先查知识库"），SOUL.md 无需声明检索链

## 支持文件清单

本 skill 依赖以下模板与参考文件（安装时随 SKILL.md 一并打包，请勿删除）：

- init 模板（建库）：`templates/index.md`、`templates/routing.md`、`templates/schema.md`、`templates/history.md`
- 卡片模板（生成卡）：`templates/card.md`、`templates/note.md`
- hook 脚本（自发生长事件驱动，三工具兼容）：`scripts/knowledge-sediment-lib.sh`（归一化层）+ `scripts/knowledge-sediment-hint.sh`、`scripts/knowledge-sediment-toolcheck.sh`、`scripts/knowledge-sediment-inject.sh`、`scripts/knowledge-sediment-subagent.sh`
- 参考：`references/hermes-hooks.md`（hook 机制说明 + 三工具注册表）
- 版本记录：`CHANGELOG.md`（随安装拷贝，记录版本历史）
