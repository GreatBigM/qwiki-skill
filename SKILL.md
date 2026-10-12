---
name: qwiki
description: 个人知识库管理：卡片索引、知识沉淀、自动检索，AI 替你积累项目经验。
version: 2.7.0
author: GreatBigM
license: MIT
category: knowledge
metadata:
  agent:
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
| qwiki migrate <来源> [目标] | migrate | 来源（旧库路径/项目名/笔记目录），目标可选 |
| qwiki delete <项目> | delete | 项目名 |
| qwiki sync [项目] | sync | 可选，缺省全部 |
| qwiki explore [关键词] | explore | 可选 |
| qwiki note <标题> | note | 笔记标题 |
| qwiki status | status | 无 |

> 知识生成（蒸馏建卡）是日常任务的自发行为，无命令触发——干活读透模块顺手沉淀。migrate 仅用于非当前版本知识的批量入迁（旧库/遗产/笔记导入），非生产动作。

---

## init — 全局初始化（创世，一次）

创建 ~/qwiki/ 骨架 + INDEX.md + personal/。

0. **幂等检查**：`[ -d ~/qwiki ]`
   - 不存在 → 继续
   - 已存在 → 提示"qwiki 知识库已存在（~/qwiki/）"，询问"是否重新初始化？（将覆盖 INDEX.md，知识文件保留）"
   - 用户拒绝 → 退出
   - 用户同意 → 备份旧 INDEX.md 为 .bak，继续
1. `mkdir -p ~/qwiki/personal ~/qwiki/projects/common`
2. `cd ~/qwiki && git init`
3. 创建 INDEX.md（按 `templates/index.md` 模板生成：空表 + personal 分区 + 维护规则脚注）
4. 创建 HISTORY.md（按 `templates/history.md` 模板生成：大事记档案——方法论定稿/架构决策/实践结论，事件粒度）
5. `cd ~/qwiki && git add -A && git commit -m "init qwiki"`
6. **hook 注册检测**（自发生长事件驱动层，跨工具通用）：
   - 检测当前工具（Hermes `~/.hermes/config.yaml` / Claude `~/.claude/settings.json` / Codex `~/.codex/hooks.json` / ZCode `~/.zcode/cli/config.json` / pi `~/.pi/agent/extensions/qwiki-sediment.ts`）
   - 检查该工具 hooks 是否已注册 knowledge-sediment 脚本（session_end/stop + post_tool + pre_llm；ZCode 无 subagent 事件，注册三项即可；pi 无 hook 机制，由扩展事件映射承接同协议）
   - 缺失 → 提示"知识自动沉淀依赖 hook 事件驱动（每轮检索引导 + 代码修改即时感知 + 会话结束补沉淀）。是否注册？"→ Y → 按 `references/agent-hook.md` 的注册表配置 + 复制 `scripts/knowledge-sediment-*.sh` 到工具 scripts 目录

> **跨工具说明**：知识库本体（~/qwiki/）与工具无关，任何 agent（Hermes / Claude Code / Codex / ZCode / pi）都能读写。事件驱动层多工具同构（Hermes/Claude/Codex/ZCode 走 hook，脚本 `scripts/knowledge-sediment-lib.sh` 按工具分支归一化事件名与输出协议；pi 无 hook，由 `~/.pi/agent/extensions/qwiki-sediment.ts` 扩展把同一标记协议接到 pi 事件模型——before_agent_start 注入检索引导+消费队列 / tool_result 写标记 / session_shutdown 跨会话提醒；标记队列 `${XDG_STATE_HOME:-~/.local/state}/qwiki/sediment/` 跨工具共享），检索引导由 inject.sh 每轮注入（Hermes 走 context，Claude/ZCode 走 hookSpecificOutput.additionalContext）或 hint.sh Stop 门禁注入（Codex/ZCode）——SOUL.md 无需声明检索链（方案 A 定稿，2026-08-02）。

---

## deinit — 全局拆除

1. 确认操作
2. **hook 清理**（与 init 注册对称）：
   - 从当前工具的 hooks 配置移除 knowledge-sediment 注册项
   - 删除 scripts 目录的 `knowledge-sediment-*.sh`
   - 清空标记队列 `rm -rf "${XDG_STATE_HOME:-$HOME/.local/state}/qwiki/sediment/`
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

1. **现状检查**（先诊断后行动）：`ls <代码路径>/` — 已有项目知识卡 → 进入「补充」模式：diff 检查是否过时，按 `templates/card-module.md` 补齐缺失章节
2. **四轮阅读 SDK**（上表；编译入口按置信度分级：用户提供 > CI 配置 > 构建足迹 > 静态推导标注待验证）
3. **项目卡初版**：工程划分用多信号源交叉，编译相关章节标注"静态推导，待验证"
4. `mkdir -p ~/qwiki/projects/<项目名>/`
5. INDEX 追加项目区块
6. 提示"项目 <项目名> 入驻完成：项目卡初版（含待验证清单）。若存在历史知识（references/design 等），执行 qwiki migrate <项目名> 做知识入迁。"

---

## migrate — 知识入迁（非当前版本 → 当前 v4 卡片体系）

**统一判据**：来源知识是否已是当前 v4 卡片体系？不是 → migrate。旧 wiki 遗产、本库 v2 遗产（references/design/archive）、其他工具沉淀、笔记导出——区别只在继承关系远近，动作一致：盘点 → 蒸馏建卡 → INDEX 回填。本库版本升级 = 把旧版本知识库当「别的知识库」迁入，而非库内原地变形。

1. **来源盘点**：确认来源形态与规模（旧库目录 / 项目 references|design|archive / 笔记目录 / 导出文件），对照 INDEX 现有登记防重复
2. **核心知识识别**：高频/知识最丰富者优先，一次 1-3 个模块
3. **蒸馏建卡**（按形态选模板：模块卡 `templates/card-module.md` / 设计说明卡 `templates/card-design.md` / 问题说明卡 `templates/card-issue.md` / 随笔卡 `templates/note-general.md`）：
   - 模块边界：search_files 确认文件清单
   - 素材：memory + 来源文档 + 代码验证
   - 卡片是「导航 + 核心事实」，细节指向来源/现有 references（相关卡片段），不搬运全文
4. **归属路由**：个人知识 → `~/qwiki/personal/`，跨项目 → `~/qwiki/projects/common/`，项目 → `~/qwiki/projects/<项目>/`
5. **INDEX 回填**：新卡登记 + 核心 references 补登记（旧日志/单次分析类按自然淘汰）
6. `cd ~/qwiki && git commit -m "migrate <来源>: <N> 张卡 + INDEX 回填"`
7. 提示"迁移完成：N 张卡，INDEX 回填 M 条。"

无可迁对象时：提示"来源已是当前 v4 卡片体系（或无可迁知识），无需迁移。"

> **边界**：migrate 只做「迁入当前版本」。v4 体系内的结构调整（归属调整、上浮 common）归 sync 结构审视，不归 migrate。

---

## delete — 项目退出

1. 确认操作
2. INDEX 删行
3. `cd ~/qwiki && git rm -r projects/<项目名> && git commit -m "delete <项目名>"`

---

## sync — 日常同步（一致性校验 + 防腐化 + 结构审视）

1. 一致性校验（报告修复）：
   - INDEX 死链/漏登记（登记行指向的文件是否存在）
   - **双链死链检测**：扫描全库 `[[...]]` 目标，对照知识库文件表（slug/项目-slug），报告悬空链接（见 skill 根目录 `SCHEMA.md` §知识互联）
2. **防腐化判定**（按 skill 根目录 `SCHEMA.md` §卡片身份 活知识原则与防腐化判定标准，**按容器分轨**）：
   - 死链清单 → 修正引用（两轨同）
   - **覆盖型**（模块卡 / 随笔卡）与代码/实测矛盾 → **修正内容**；不可救 → 提出销毁建议（确认后删）
   - **追加型**（轨迹卡 / 各事件卡）被推翻 → **追加「后续修正」标注**（或标 `已失效` / `已被 <卡> 取代`），**不改原行、不销毁**
   - **聚合卡出现零入链 = 异常**（它本该被引用）→ 查为什么；事件卡零入链属正常（散挂 INDEX），保留标记冷门
   - **轨迹卡归属检查**：每张轨迹卡的入链里至少应有 1 张模块卡；没有 → 报「这条线缺一张模块卡」
3. **表达形态体检**（按 skill 根目录 `SCHEMA.md` §表达形态）——作用域：**设计说明 / 问题说明形态的卡（按正文结构判定）＋ 本次新写入的卡**；存量模块卡、随笔卡不报，避免误报刷屏：
   - 该给图（结构分层 / 跨 ≥2 组件 / ≥3 步流转 / 含时序竞态）却纯文字 → 报
   - 图内节点、伪代码关键行无真实符号名或 `file:line` → 报
   - 仅复述文字的装饰图 → 报
4. **结构审视（主动防腐化，2026-08-04 定稿）**：
   - 归属调整：放错库/放错层级的卡归位（personal ↔ projects、项目 ↔ common）——跨库移动只在归属错误时发生，非形态演进（note/card 是两个库，无演进）
   - 发现即处理，与检测驱动防腐化互补
5. `cd ~/qwiki && git add -A && git commit -m "sync $(date +%Y%m%d)"`（有变更时）

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

`qwiki note <标题>` → 按 `templates/note-general.md` 创建 `~/qwiki/personal/<slug>.md` → INDEX 加一行。

- **自动判断模式（自发生长）**：三触发源出现时 AI 直接建卡/更新，不等用户命令——
  ① 验证结论产生（实测/分析出结论）② 重复实践未命中知识点（查 INDEX 无对应卡且实践再现）③ 代码修改后对应卡需更新
- **hook 事件驱动层**（善用 hook/扩展，任务嵌入事件点，跨工具通用）：`scripts/knowledge-sediment-*.sh` 注册到当前工具 hooks（Hermes config.yaml / Claude settings.json / Codex hooks.json / ZCode `~/.zcode/cli/config.json`，见 `references/agent-hook.md` 注册表）；pi 由 `~/.pi/agent/extensions/qwiki-sediment.ts` 扩展承接（无 hook 机制，事件映射同协议：before_agent_start 注入引导 / tool_result 写标记 / session_shutdown 提醒）——session_end/stop 写标记 / post_tool 信号检测 / pre_llm 每轮注入检索引导+读队列沉淀指令（Codex/ZCode 由 Stop 门禁承担） / subagent_stop 子代理产出（ZCode 无此事件，不注册）——标记写入队列目录（XDG 约定 `${XDG_STATE_HOME:-~/.local/state}/qwiki/sediment/`，定义于 lib.sh），inject 读后即删（Codex/ZCode 由 hint.sh Stop 门禁读后即删）。多工具 payload 经 `scripts/knowledge-sediment-lib.sh` 归一化（一个脚本吃四种 hook 工具：Hermes/Claude/Codex/ZCode），输出协议按工具分支，机制说明见 `references/agent-hook.md`
- **知识归属路由**（决定卡放哪）：
  - 个人方法论/工作哲学 → `~/qwiki/personal/`
  - 跨项目知识（反模式/通用经验/工具坑，来源项目、适用多项目）→ `~/qwiki/projects/common/`
  - 项目特定知识 → 对应项目卡或 `references/`
- **必填动作**（生成时自动做，三处一次填齐同一字符串）：YAML summary（真相源）+ 正文 `>` 行（渲染副本）+ INDEX 登记行
- YAML 头按公约：title/type/date 必填 + summary 真相源 + tags
- 相关段用 `[[slug]]` 双链（文档级链接，见 skill 根目录 `SCHEMA.md` §知识互联）
- 正文段落为参考骨架（背景/要点/结论），按需取舍，**不强制 schema**——写什么算什么，后续可随时补充
- 卡片身份：note 是随笔卡（personal/ 库，个人来源），card 是项目卡（projects/ 库，项目来源，模块 / 设计说明 / 问题说明三形态）——两个库、归属由来源决定，**无形态演进**；跨库归位（归属错误时）由 sync 结构审视处理
- 和 import 的区别：note 无项目目录，一条 INDEX 行 + 一个 .md
- 写完后 `cd ~/qwiki && git add -A && git commit -m "note: <标题>"`

---

## 沉淀标记核实（会话开头被注入「知识沉淀待执行」时）

hook 只在**本轮注入文本**里告诉你「有标记」，标记文件本身已被 inject **读后即删**——先核实再动手，别照着空标记硬造卡。

**第一步：看注入文本有没有「细节：…」段**
- 有细节 ⇒ 真产出（subagent_stop 的 detail = role|状态|摘要），照细节建卡/更新
- 只有「检测到沉淀标记（xxx）」无细节 ⇒ detail 为空（退化/陈旧标记），核实后多半结论是「无需沉淀」
- **队列目录为空不能证明没有标记**（读完即删是常态）；队列目录 mtime ≈ 本会话启动时刻 = 标记刚被消费

**第二步：核实顺序（判「无待沉淀」前必跑，缺一步不算核对过）**
1. 库侧现状：`cd ~/qwiki && git log --oneline -12 && git status --short` —— 工作区干净且时间窗内已有对应 commit ⇒ 产出已沉淀，标记属陈旧遗留
2. 反查产出事件是否真的存在（Hermes 侧 state.db，只读连接即可，不必停任何进程）：
   - `select session_id,timestamp from messages where tool_calls like '%delegate_task%' and timestamp > <窗口起点 epoch> order by timestamp desc`
   - 再看 `sessions`（id/model/started_at/title），`platform=subagent` 的会话才是真子代理；窗口内 0 条 delegate_task ⇒ 不存在产出该标记的子代理，标记必为陈旧/退化
3. 跨工具排查：队列跨工具共享（lib.sh `SEDIMENT_QUEUE_DIR`），标记可能来自别的 agent —— 查各自会话落点的新增/改动（Claude `~/.claude/projects/**/*.jsonl` 按 mtime；本机已卸载的工具不必再列）
4. 判定并回报：未沉淀 → 按归属路由建卡/更新 + INDEX + commit；已沉淀 → 忽略本条，给出依据（commit hash / 时间窗）

**坑**
- `agent.log` 里反复出现的 `shell hook registered: subagent_stop` **只是进程启动日志**（no_agent cron worker 每几分钟起一次也照打），不是子代理运行过的证据——别据此认定「有子代理活动」
- 退化/陈旧标记会一直躺在队列里，等**下一次任意工具的注入**才被清掉 ⇒ 会在几天后「突然」出现在某个会话开头；空 detail 是它的指纹
- 已删标记无法从日志回捞（grep 注入文案/标记类型名都无痕）——注入文本是唯一残留证据；别在别处找标记文件，队列目录只有一个真相源
- 结论必须写进回复：查了什么、结论、依据、**证伪项**（用户要看到核查痕迹，不接受「无可沉淀」的静默一笔带过）

---

## status — 查看状态

INDEX 条目数、已入驻项目、知识文件数。

---

## 知识文件模板（角色 × 骨架）

**先定角色（聚合 / 事件），再选骨架**——骨架之别在模板，不在 `type` 值（card 一律 `type: card`）：

| 角色 | 骨架 | 模板 | type |
|------|------|------|------|
| 聚合 | 模块卡（八段：模块边界 / 职责描述 / 架构设计 / 技术栈 / 代码规范 / 配置命令 / 模块间关系 / 相关） | `templates/card-module.md` | card |
| 聚合 | 轨迹卡（范围与依据 / 一句话 / 保留 / 拆除 / 否决 / 仅测量 / 未定 / 当前快照 / 卡间索引 / 过时修正标注 / 相关） | `templates/card-track.md` | card |
| 事件 | 实测卡（一句话 / 口径 / 数据 / 裁决 / 可复用 / 局限 / 状态 / 相关） | `templates/card-measurement.md` | card |
| 事件 | 问题说明卡（现象 / 根因 / 正常流 vs 出错流 / 修复 / 验证 / 复用手势 / 相关） | `templates/card-issue.md` | card |
| 事件 | 审查卡（**候选骨架，暂不立模板**：范围 / 逐条发现分级 / 可达性 / 结论） | — | card |
| 按需 | 设计说明卡（设计目标 / 结构图 / 流向图 / 关键设计决策 / 时序图 / 相关）——模块卡「架构设计」段的深化 | `templates/card-design.md` | card |
| 个人 | 随笔卡（背景 / 要点 / 结论，自由取舍） | `templates/note-general.md` | note |

> 卡片角色判据、公共约定与表达形态见 skill 根目录 `SCHEMA.md` §卡片身份、§表达形态——本文件不复述。

## 架构文档

- **SCHEMA.md**（本 skill 根目录）= **做成什么样**：知识库宪法（目录结构/命名/纯度/卡片公约：YAML 头、卡片身份、表达形态、知识互联）——目标态定义，**唯一真相源在本 skill**（随 skill 发布/安装），知识库内不放置实例
- **本 SKILL.md** = **怎么做**：九操作流程——实现 SCHEMA 目标态的方法
- 平级关系（2026-08-01 定稿）：SKILL 的每个操作都在实现 SCHEMA 定义的目标态（init 按蓝图建库、note 按卡片公约生成、import 按目录结构入驻），两者互补不重叠

### SCHEMA 单一真相源（2026-08-03 定稿，v2.0.0）

- **宪法唯一真相源在本 skill 根目录 `SCHEMA.md`**：随 skill 发布/安装；知识库内不放置 SCHEMA 实例（曾放置 = 第三层 copy——实例改动与 skill 快照漂移，module-slug 示例漏同步教训）
- 宪法变更 = 改本文件 + bump 版本 + 发布；**无模板 ↔ 实例同步义务**（无实例可同步）
- 新库 init 不生成 SCHEMA.md（知识库骨架 = INDEX/HISTORY + 目录）；卡片公约由加载本 skill 时读取根目录 SCHEMA.md

### 解耦声明（2026-08-02 定稿，v1.9.0）

- **本 skill 与 AGENTS.md / codegraph 无关**：不生成 AGENTS.md、不依赖 codegraph 索引、references 不含 codegraph-quickstart.md
- 代码检索由各工具自身能力承担（search_files/read_file 或工具内置代码索引如 codegraph MCP）——qwiki 只管理知识库本体（~/qwiki/）
- 检索引导由 hook 注入（inject.sh 每轮注入"先查知识库"），SOUL.md 无需声明检索链

## 支持文件清单

本 skill 依赖以下模板与参考文件（安装时随 SKILL.md 一并打包，请勿删除）：

- 宪法（与 SKILL.md 平级，唯一真相源）：`SCHEMA.md`（随安装拷贝）
- init 模板（建库）：`templates/index.md`、`templates/history.md`
- 卡片模板（生成卡，先定角色再选骨架）：`templates/card-module.md`（聚合·模块卡）、`templates/card-track.md`（聚合·轨迹卡）、`templates/card-measurement.md`（事件·实测卡）、`templates/card-issue.md`（事件·问题说明卡）、`templates/card-design.md`（按需·设计说明卡）、`templates/note-general.md`（个人·随笔卡）
- hook 脚本（自发生长事件驱动，四 hook 工具兼容 + pi 扩展）：`scripts/knowledge-sediment-lib.sh`（归一化层）+ `scripts/knowledge-sediment-hint.sh`、`scripts/knowledge-sediment-toolcheck.sh`、`scripts/knowledge-sediment-inject.sh`、`scripts/knowledge-sediment-subagent.sh`（ZCode 无 SubagentStop，不注册该项）；pi 适配见 `~/.pi/agent/extensions/qwiki-sediment.ts`（无 hook，事件映射同协议）
- 参考：`references/agent-hook.md`（hook 机制说明 + 三工具注册表）
- 版本记录：`CHANGELOG.md`（随安装拷贝，记录版本历史）
