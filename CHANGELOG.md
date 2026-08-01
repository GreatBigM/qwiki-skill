# Changelog

本文件记录版本历史。版本号定义在 SKILL.md frontmatter 的 `version` 字段（单一真相源）。

## 1.8.4 (2026-08-02)

### Fixed
- **架构审查修复（框架/原理/流程全面 review）**：
  - 模板 ↔ 实例同步机制定稿：模板只服务 init，实例是活宪法；sync 增加「宪法同步检查」对比关键节防漂移（修复 P0：SCHEMA 实例内部矛盾——130 行旧文案与活知识原则冲突）
  - sync 步骤重编号（新增宪法同步检查后 1-6 顺延）
- 知识库实例防腐化同步（~/qwiki 仓库 f9b876f）：SCHEMA 迁移规则对齐模板、12 处双链死链修复（thread_census 改名漂移 / WiFi/perf 链接指向现有卡 / 无宿主去链化）、ROUTING 腐化检测清单更新为 hm6502 九卡

## 1.8.3 (2026-08-02)

### Fixed
- **回退恢复**：v1.8.1 提交时仅挑选部分文件，用户 v1.9.0 改动被丢弃——本轮补回：
  - SKILL.md init 第 10 步标注「仅 Hermes 环境」+ 多 agent 降级说明块
  - SKILL.md deinit 重构为 4-6 步（hook 清理 + SOUL.md 自动清理，与 init 对称）
  - SKILL.md hook 事件驱动层描述改为队列目录版
  - references/hermes-hooks.md 沉淀链路改队列目录 + 读后即删 + 队列目录坑
  - CHANGELOG 补回 install.sh 补拷贝 scripts、deinit 对称、队列重构等历史说明（见 1.8.1/1.8.2 条目）

## 1.8.2 (2026-08-02)

### Fixed
- **B1 实现补齐（v1.8.1 声明未落地）**：`knowledge-sediment-hint.sh` 重写为队列目录协议——python3 写 JSON 标记到 `~/.hermes/state/knowledge-sediment/`（纳秒时间戳文件名），session_id 完整保留；python3 缺失时静默退出不阻塞主流程。此前为单文件纯文本标记，与 inject.sh 的 json.load 协议不兼容导致 session_id 丢失
- **B2 实现补齐（v1.8.1 声明未落地）**：`knowledge-sediment-subagent.sh` 改读顶层 `child_role/child_summary/child_status/parent_session_id`（hooks.py subagent_stop 协议），detail 不再恒为"子代理(未知)"；标记写入队列目录与 inject.sh 消费协议对齐

## 1.8.1 (2026-08-02)

### Fixed
- **hook 协议 bug 修复（2026-08-01 复盘 B1/B2/B3，源码二次确认）**：
  - B1: hint.sh 输出纯文本与 inject.sh 的 json.load 协议不兼容 → session_id 丢失。改为 JSON 格式（与 toolcheck/subagent 一致），inject 成功读取 session_id
  - B2: subagent.sh 读 `extra.role/extra.goal`，真实 payload 在顶层 `child_role/child_summary/child_status`（hooks.py:187-205）→ detail 恒为"子代理(未知)"。已改读顶层字段 + parent_session_id
  - B3: references/hermes-hooks.md 写 post_tool_call extra 嵌套，实际字段在顶层（hooks.py:120-128）。已修正 Wire 协议段并补充 subagent_stop 字段清单

## 1.8.0 (2026-08-01)

### Added
- **hook 事件驱动层（善用 hook，SOUL 零改动）**：scripts/knowledge-sediment-*.sh 四脚本（on_session_end 写标记 / post_tool_call 信号检测 / pre_llm_call 指令注入 / subagent_stop 子代理产出）→ references/hermes-hooks.md 机制说明 → init 流程加 hook 注册检测
- 自发生长升级为事件驱动：当前对话内即时触发（post_tool_call 感知代码修改/验证成功 → 下轮注入指令），无需等下次会话

## 1.7.7 (2026-08-01)

### Added
- projects/common/（跨项目公共知识）入宪同步：templates/schema.md 补 common 定义、templates/index.md 补 common 区、init 流程建 common/ 目录
- note 操作新增「知识归属路由」：个人方法论→personal/、跨项目知识→projects/common/、项目特定→项目卡/references

## 1.7.6 (2026-08-01)

### Changed
- 发布侧脱敏：SKILL.md 移除内部技能名引用；templates/schema.md 示例改通用占位符（内部项目名示例→通用占位符、workbench 产物→项目文档）；references/codegraph-quickstart.md 移除内部技能名
- 支持文件清单补 CHANGELOG.md（skills install 与 install.sh 两通道行为一致）

## 1.7.5 (2026-08-01)

### Added
- 自发生长机制（note 操作自动判断模式）：三触发源——验证结论产生 / 重复实践未命中知识点 / 代码修改按模块边界匹配更新
- sync 防腐化判定：死链修引用、矛盾修正、完全过时销毁、孤岛标记冷门保留
- card 模板模块边界段标注「兼作更新路由」

## 1.7.4 (2026-08-01)

### Added
- SCHEMA 卡片身份节新增「活知识原则」：卡片不是档案——先提纯、后持续更新防腐化、过时可修正或销毁（只进不出只适用于 HISTORY 档案）

## 1.7.3 (2026-08-01)

### Added
- 卡片公共约定第 5 条「一张卡一个点」：card=一个独立模块（模块粒度），note=一个独立知识点（知识点粒度）——不因总结知识合并多知识进一张卡，相关用 `[[slug]]` 连接
- note/card 模板定位声明同步（note=知识点粒度，card=模块粒度）

## 1.7.2 (2026-08-01)

### Changed
- 执行层说明收敛：qwiki SKILL.md 架构文档节 / templates/schema.md / SCHEMA.md 顶部的「命名决策」说明全部移除——SCHEMA/SPEC 语义定性单一真相源收敛至框架层（hermes-skill-gen 约束 7），执行层按 SKILL+模板执行，不需要知道选词依据

## 1.7.1 (2026-08-01)

### Changed
- 命名决策深化：SCHEMA/SPEC 按可变性分工——SCHEMA=不可更改的（宪法/蓝图），SPEC=可更改的（工程约束/当前规格，随 change 闭环更新）；取代"SPEC 留给 workbench"表述，同步 SKILL.md 架构文档节 + templates/schema.md

## 1.7.0 (2026-08-01)

### Added
- templates/history.md：HISTORY 大事记模板（事件粒度：方法论定稿/架构决策/实践结论，与 git log 区分）
- SKILL.md init 流程新增创建 HISTORY.md——init 四件套齐（INDEX/ROUTING/SCHEMA/HISTORY）
- 支持文件清单分类标注：init 模板（建库）vs 卡片模板（生成卡）

### Changed
- 知识库根 README.md 删除：v2 模型说明（五类工件模型）完全过时，与 v4 卡片体系/SCHEMA 宪法矛盾，接入指引已被 ROUTING+SCHEMA 覆盖

## 1.6.0 (2026-08-01)

### Changed
- **references/spec.md 删除**：定位分歧根源（SPEC 既非"怎么做"也非"做成什么样"）；references/ 只留下级接入参考（codegraph-quickstart / agents-md-structure）
- **SCHEMA/SKILL 平级定位定稿**（SKILL.md 架构文档节 + SCHEMA.md 顶部）：SCHEMA = 做成什么样（知识库目标态），SKILL = 怎么做（九操作流程），平级互补
- **命名决策定稿**：SCHEMA（结构蓝图）长期代表知识库宪法；SPEC 留给 workbench 项目规格，不混用
- SKILL.md 支持文件清单移除 references/spec.md

## 1.5.0 (2026-08-01)

### Added
- templates/schema.md：SCHEMA 宪法模板（目录结构/命名/纯度/卡片公约），init 时创建——新用户安装 skill 即有宪法
- 知识库侧 SCHEMA.md 并入卡片公约三节（YAML 头公约/卡片身份/知识互联）

### Changed
- **公约真相源迁移**：卡片公约从 skill references/spec.md 迁入知识库 `~/qwiki/SCHEMA.md`（宪法在知识库内，skill 只保留操作引用，不重复定义）
- references/spec.md 精简为操作速览（目录结构 + 与代码仓关系 + 指向 SCHEMA.md）
- SKILL.md init 流程新增创建 SCHEMA.md；note/sync/模板节的公约引用全部改指 SCHEMA.md
- note/card 模板定位声明引用改指 SCHEMA.md

## 1.4.0 (2026-08-01)

### Added
- 卡片身份概念（spec.md §卡片身份）：知识库最小单元是卡片，note（随笔卡/personal）与 card（模块卡/projects）同一身份不同形态，公共约定类似基类
- 知识互联公约（spec.md §知识互联）：`[[slug]]` 文档级双链（不做内容级链接）、撞名消歧 `[[项目/slug]]`、反链=全库搜索、死链检测挂 sync
- note 模板：summary 真相源（YAML）+ 正文 `>` 渲染副本 + `[[slug]]` 双链 + 按需演进指引
- card 模板：补 YAML 头 + 相关段统一为「相关」+ `[[slug]]` 双链 + 卡片身份声明

### Changed
- summary 单一真相源修正：note 类型由"只写正文 `>` 行"改为"YAML summary 真相源 + 正文 `>` 渲染副本"（INDEX 登记直接提取，生成时三处同步填）
- SKILL.md note 节更新（三处同步必填动作）+ sync 节新增双链死链检测
- 八段模板末段「相关卡片」统一为「相关」

## 1.3.0 (2026-08-01)

### Added
- YAML 头公约 v1（references/spec.md）：所有知识库文档统一 YAML 头，必填 title/type/date，推荐 summary/tags，可选 author/version/status/related
- 排除项明确：INDEX/ROUTING/templates/AGENTS.md/spec.md 不纳入公约
- note 模板对齐公约：YAML 增加 type: note；一句话总结约定为正文 `>` 引言行（note 类型不写 YAML summary，避免双写）

### Changed
- SKILL.md 引用公约（知识文件模板节）
- 存量杂格式统一：8 个文件（4 中文键 + 2 skill frontmatter + 2 change 风格）转换为公约格式，来源/吸收至信息补入正文引用行

## 1.2.0 (2026-08-01)

### Added
- note 模板丰富化（templates/note.md 3 行 → 完整轻量骨架）：YAML 头（title/date/tags）+ 一句话总结 + 相关段
- 模板定位声明：YAML 头/一句话/相关段为 AI 生成必填动作（检索与 INDEX 登记依赖），正文段落（背景/要点/结论）为参考骨架不强制 schema

### Changed
- SKILL.md note 节对齐新模板：一句话总结自动写入 INDEX 登记行；note 成熟可升级为八段卡（蒸馏时机）

## 1.1.0 (2026-08-01)

### Added
- 顶部新增「AI 替你完成」使用哲学头节：用户指挥 AI，AI 替用户执行，用户不面对命令行
- AI 交互约定：依赖缺失→对话层引导确认，参数问清后写入，不让用户手动敲命令
- triggers 补充：qwiki/知识库/知识管理/wiki/知识检索/知识同步/项目入驻/知识卡片

### Changed
- init 流程调整：先 git init 建骨架，最后统一提交（git add + commit 后置）
- delete 路径脱敏：/mnt/data/<项目> → <代码路径>（通用化，去除内部环境依赖）
- README 手动复制路径对齐仓库根目录布局（去 skills/qwiki 嵌套）

## 1.0.0 (2026-07-31)

### Added
- 初始发布：qwiki 知识库管理九操作（init/deinit/import/migrate/delete/sync/explore/note/status）
- 仓库根目录即 skill 本体布局，install.sh 一键安装
- references: spec.md / agents-md-structure.md / codegraph-quickstart.md
- templates: index.md / routing.md / card.md / note.md
