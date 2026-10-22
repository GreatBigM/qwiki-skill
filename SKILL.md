---
name: qwiki
description: 个人知识库管理：卡片索引、知识沉淀、自动检索，AI 替你积累项目经验。
version: 2.19.0
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
| qwiki sync | sync | 无 |
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
4. `cd ~/qwiki && git add -A && git commit -m "init qwiki"`
5. **hook 注册检测（仅 hook 受体）**：检测当前工具 → 未注册则问"是否注册知识沉淀 hook？"→ Y → 按 `references/agent-hook.md` §注册 配置，并复制 `scripts/knowledge-sediment-*.sh` 到工具 scripts 目录。**DSH 是 skill-only 受体（无 hook 面）→ 跳过本步**，靠文末「收尾自检」兜底。

> **跨工具说明**：知识库本体（`~/qwiki/`）与工具无关，任何 agent 都能读写；事件驱动层（检索引导注入 / 自动沉淀标记）依赖各工具的 hook 面——Hermes / Claude / Codex / ZCode 走 hook，pi 与 **DSH** 分别走扩展或只有 skill 本体。各受体现状与注册表见 `references/agent-hook.md`。
> **受体现状（2026-10-22）**：本机现行受体 = **Hermes + Claude + DeepSeek Harness（DSH）**；DSH 是 skill-only 受体（`~/.dsh/skills/qwiki`，无 hook 面），自动沉淀不生效 ⇒ 靠文末「收尾自检」三问兜底。

---

## deinit — 全局拆除

1. 确认操作
2. **hook 清理**（与 init 注册对称）：
   - 从当前工具的 hooks 配置移除 knowledge-sediment 注册项
   - 删除 scripts 目录的 `knowledge-sediment-*.sh`
   - 清空标记队列 `rm -rf "${XDG_STATE_HOME:-$HOME/.local/state}/qwiki/sediment/"`
3. `cd ~/qwiki && cd .. && mv qwiki qwiki.bak.$(date +%Y%m%d)`

---

## import — 项目入驻（新增，保持纯粹）

新项目从零入驻：AI 四轮阅读 SDK → 项目卡**初版** → 目录骨架 → INDEX 登记。**不含卡片化**——意即不在这轮把历史知识蒸馏成卡（那归 migrate 与日常蒸馏）；本轮只出**一张项目卡初版**作为入口。

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

3. **项目知识卡是逐步迭代的活文档**——import 只给"可用的初版 + 迭代机制"，允许不完整但必须标注待验证项；任务完成/认知加深/踩坑时更新（这正是「自发生长」——不等用户下令）

### 四轮阅读法（AI 读 SDK 的编排）

```
第一轮：这是什么项目？   → 根目录结构/README/manifest/配置文件 → 项目概况
第二轮：怎么编译？       → 构建系统文件/CI/toolchain 痕迹 → 编译入口候选(置信度标注)
第三轮：核心模块是什么？ → search_files/read_file 追主入口/核心符号 → 分层架构
第四轮：哪里坑？怎么干活？→ 特殊机制/调试相关代码 → 工作流 + 特殊机制
```

每轮阅读必须伴随**验证动作**（编译跑通/代码互证/交叉引用），不验证的读等于没读——读到的结论都要有验证痕迹。

### 步骤

1. **现状检查**（先诊断后行动）：`ls <代码路径>/` — 已有项目知识卡 → 进入「补充」模式：diff 检查是否过时，按 `templates/card-aggregate.md` 补齐缺失章节
2. **四轮阅读 SDK**（上表；编译入口按置信度分级：用户提供 > CI 配置 > 构建足迹 > 静态推导标注待验证）
3. **项目卡初版**：工程划分用多信号源交叉，编译相关章节标注"静态推导，待验证"
4. `mkdir -p ~/qwiki/projects/<项目名>/`
5. INDEX 追加项目区块
6. 提示"项目 <项目名> 入驻完成：项目卡初版（含待验证清单）。若存在历史知识（项目 `resource/` 下的素材、或别处的旧文档），执行 qwiki migrate <项目名> 做知识入迁。"

---

## migrate — 知识入迁（非当前版本 → 当前 v4 卡片体系）

**统一判据**：来源知识是否已是当前 v4 卡片体系？不是 → migrate。旧 wiki 遗产、本库 v2 遗产（旧 references/design/archive，现统一在 `resource/`）、其他工具沉淀、笔记导出——区别只在继承关系远近，动作一致：盘点 → 蒸馏建卡 → INDEX 回填。本库版本升级 = 把旧版本知识库当「别的知识库」迁入，而非库内原地变形。

1. **来源盘点**：确认来源形态与规模（旧库目录 / 项目 `resource/`（旧名 references|design|archive）/ 笔记目录 / 导出文件），对照 INDEX 现有登记防重复
2. **核心知识识别**：高频/知识最丰富者优先，一次 1-3 个模块
3. **蒸馏建卡**（**先定用途**——种类由内容推导，SCHEMA §卡片身份）：**聚合卡** `templates/card-aggregate.md`（八段；若干紧密相关的知识要分别成卡时，它就是这批卡的**总组织**）；**独立卡**按用途选模板——轨迹卡 `templates/card-track.md` / 实测卡 `templates/card-measurement.md` / 问题说明卡 `templates/card-issue.md` / 设计说明卡 `templates/card-design.md` / 随笔卡 `templates/note-general.md` / 审查卡走**候选骨架**（`type: card`）；机制·手册·流程类走自由骨架（`type: note`）。
   - 模块边界：search_files 确认文件清单
   - 素材：memory + 来源文档 + 代码验证
   - 卡片是「导航 + 核心事实」，细节指向来源/现有 references（相关卡片段），不搬运全文
4. **归属路由**：个人知识 → `~/qwiki/personal/`，跨项目 → `~/qwiki/projects/common/`，项目 → `~/qwiki/projects/<项目>/`。命令行给了 `[目标]`（`personal` / `common` / `<项目名>`）时**全部落到该目录**（覆盖路由），没给就按内容逐张判断
5. **INDEX 回填**：只登记新卡——**素材不进 INDEX**（它们是卡片引用的数据来源，见 SCHEMA §INDEX 登记规则）
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

0. **机器体检（先跑这个）**：`python3 <skill 根>/scripts/qwiki-check.py [知识库根]`（默认 `~/qwiki`）
   - **只读**，输出两栏，**只有一栏配叫「错」**：
     - **INDEX 入口（硬）**：死链 / 漏登记 / 一卡多行 / 段头与路径不符 / 表体断裂 / 素材误登 → 坏了就是「知识在但找不到」，退出码 1，必须修
     - **规格（软）**：卡片头部（H1=title / `>` 结论行 / 依据）、INDEX 投影漂移、双链、素材路径、命名、slug 唯一、检索双向可达、轨迹卡归属、素材带头、YAML → **只记账，不影响退出码**，排版不齐不耽误检索
   - 规格项要分**存量 / 新增**：首次跑 `--baseline` 把当时全部规格项写进 `<库根>/.qwiki-maintenance.json`（唯一写模式），此后只有**新增**会被点名，修好的自动销账；`--strict` 让新增项也返回非零（给要设卡的 CI 用）
   - **版本 / 代差不参与判断**：旧卡旧规格、新卡新规格是正常状态，不提示也不计数；那张卡被改写时按当前规格重生即可
   - 明细默认截断，`--all` 打全量（大库排查用）
   - 下面是同一批约定的**说明与人工处置口径**；体检报什么，按对应条目处置

   投影漂移（标题列 / 总结列与卡片对不上）**不用逐行手改**：跑 `python3 <skill 根>/scripts/qwiki-sync.py [知识库根] --write` 重建 INDEX。它属规格栏，不影响退出码。

1. **处置顺序：先 INDEX 入口（硬错），再规格项（保养）**。两者混着修会失焦——入口坏了，改得再齐也找不到。逐项：
   - INDEX 死链/漏登记（登记行指向的文件是否存在）
   - **INDEX 两列与卡片不一致**（「标题」列 ≠ 卡片 `title`，「总结」列 ≠ 卡片 `>` 引言行）→ 按卡片回填（INDEX 是卡片集的正投影，见 SCHEMA §INDEX 登记规则）；比对取的是 `>` 块**第一行**，首行误写成引言句时改卡片首行（而非改 INDEX）
   - **投影只有两处**：INDEX 总结列 ↔ 卡片 `>` 首行（脚本生成，不手写）、INDEX 标题列 ↔ `title`。YAML `summary` 是长摘要，**不参与投影比对**。改名类字符串仍要一次改齐四处：`title` / 正文 H1 / INDEX 行 / 指向它的 `[[链接]]`（旧名可能只残留在某一处）
   - **批量修卡**（一次几十上百张、多子代理并行）→ 按 `references/bulk-repair.md`：投影由父代理单写、派工粒度、断点接力都在那里；本节只留常规 sync 口径。
   - **「总结」列超长**（>80 字符）→ 压卡片 `>` 首行到 80 以内，再跑 `qwiki-sync.py <库根> --write` （INDEX 自动跟随；YAML `summary` 不动）
   - **命名违规**（SCHEMA §命名约定）：文件名含 `_`/大写/空格、日期写成后缀 `-YYYYMMDD`、同名族前缀不齐（`build-flash-system` 有前缀的没前缀的混着）→ 改名并同步全库 `[[链接]]` 与 INDEX 两列
  - **命名形态提示**（规则 4，自检末尾独立打印，**不计失败**）：记录角色不在末位 / 一次性角色缺日期前缀 / 跨项目同族前缀不齐 → 逐条判断是否改名（名词性 token 如 `system()` / `ab-slot` 可忽略）；**改名是连锁改动**：同步 `[[链接]]`、INDEX 两列、以及聚合卡挂载判定，务必一次做完再跑自检
   - **H1 不在正文首位**（前面还有引言块/表格/标题）→ 把 H1 提上去；顺序错位会污染「H1 后第一行」取摘要的脚本
   - **素材误登 INDEX**（表内出现 `resource/`｜`scripts/` 等素材/脚本路径，或旧名 `references/`｜`design/`）→ 删行（库内变更查 git 历史，不另立档案文件）
   - **素材带头**（`resource/`｜`scripts/` 下的 `.md` 带 YAML 头）→ 删头（不变量：有头 ⇔ 是卡片）；若该文件本已是知识形态（机制梳理 / 方案 / 审查结论），走**升格为卡**——移位到项目根、补 `type: card` 头与 `> 依据`、登记 INDEX，并顺手修掉升格后暴露的 `[[...]]` 死链
   - **正文里的仓库路径必须可解析**：卡片正文引用的仓库路径须是能 `test -e` 的**真名**（不得用简写，如 `archive/clock` 须展开为 `0_workbench/archive/<批次>/clock`）；有意保留的退役值须**就地标注「已不存在」**，未标注的失效路径才是缺陷
   - **双链死链检测**：扫描全库 `[[...]]` 目标，对照**卡片表**（slug/项目-slug），报告悬空链接；另报「卡片里 `[[...]]` 指向素材」的口径错误（素材只做路径引用，见 skill 根目录 `SCHEMA.md` §知识互联）
2. **防腐化判定**（按 skill 根目录 `SCHEMA.md` §卡片身份 活知识原则与防腐化判定标准）：
   - 死链清单 → 修正引用
   - **追加还是覆盖看内容，不看卡种**（SCHEMA §活知识原则）：当下状态（聚合卡现状 / 机制梳理）→ **直接修正**；被推翻的是**"已发出的结论"**（裁决 / 实测读数 / 已被引用的判断）→ **追加修正标注**（轨迹卡走 §H，其它卡**就地**追加 `> ⚠️ 修正（YYYY-MM-DD）：…` 块引用行，紧贴被推翻那句、不抹原文），**不静默抹掉、不销毁**
   - 聚合卡改完只剩当前态，"因为什么决策、改掉哪条、哪条因此过期"记在**该线轨迹卡 §H**——旧结论不得静默删除（该线还没有轨迹卡 ⇒ 这次的"消失的知识"就是建卡的负空间信号）；整卡不可救 → 先留修正标注，再提出销毁建议（确认后删）
   - **零双链入链 = 只由 INDEX 挂载**（不是"未组织"）——聚合卡多一条反向双链就多一条按链浏览的路，有天然来路就补，**不强求**
   - **轨迹卡归属检查**：每张轨迹卡的入链里至少应有 1 张聚合卡；没有 → 报「这条线缺一张聚合卡」
3. **表达形态体检**（按 skill 根目录 `SCHEMA.md` §表达形态）——作用域：**设计说明 / 问题说明形态的卡（按正文结构判定）＋ 本次新写入的卡**；存量聚合卡、随笔卡不报，避免误报刷屏：
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

**存储与检索是怎么实现的（2026-10-13 补，2026-10-22 检索面加索引）**：
- **存储** = 文件系统分片（目录决定归属）+ 卡片自证（YAML 头 / H1 首行 / `>` 首行，三者让卡片可被正则解析）+ INDEX 正投影（三列由卡片推出，不另写）+ git（变更可追溯、可回滚；**库内历史查 git，不另立档案文件**）+ `qwiki-check.py` 两栏体检（把约定变成可执行检查）
- **检索** = 四跳：① **命中**（两种入口，见下）；② **读卡**（H1 下摘要 → 各段）；③ **沿边走**（上行到聚合卡看同类／沿直链到对偶卡／跨族边走线）；④ 素材不在检索面——从引用它的卡的「模块边界 / 相关」段按路径找。反查"谁引用了我" = 全库 grep `[[slug]]`
- **检索与取知识是两件事**：检索只做「定位到哪张卡」（返回路径 + 一行结论），**读卡才是取知识**（只读 1–2 张）
- **定位分三级信号，逐级下沉**：
  - **标签**（一级，最高精度）：`python3 scripts/qwiki-search.py <库根> --tag <标签>` 或 `"<关键词>" --tag <标签>`——Agent 已经从对话里知道关键词是什么，带上它就是显式过滤
  - **简介**：查询词落在结论行里，权重仅次于标题
  - **正文**：细节型查询唯一的召回来源（实测：只出现在正文的词，去掉正文索引后 top-3 召回从满格掉到个位数百分比）
- **入口按规模选**：`explore`（小库，读 INDEX 的标题+总结）／ `qwiki-search.py`（大库或关键词不在标题里；索引是生成物 `.qwiki-index.db`，卡改自动重建、删掉不丢知识）

**检索链两条路（2026-10-13 写明）**：① 概览型问题 → INDEX 命中**聚合卡**（它的摘要就是这块知识的总组织）；② 细节型问题 → 命中**独立卡**后，沿该卡「相关」段的第一条上行边（`本卡所属的总组织`）走到聚合卡，再看它的子卡清单找同类。缺上行边 = 细节命中后回不去，只能退回 INDEX 重查。

1. 搜索 INDEX.md 所有条目的标题+总结做匹配；**关键词不在标题/结论里时，先用 `qwiki-search.py` 走倒排**（它扫正文，命中后可回 INDEX 看同族）
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
- **hook 事件驱动层**（仅 hook 受体；DSH 无此层）：注册 / 事件 / 输出协议见 `references/agent-hook.md`——本 skill 只在安装时按注册表配置，运行时靠标记队列与注入文本。
- **知识归属路由**（决定卡放哪）：
  - 个人方法论/工作哲学 → `~/qwiki/personal/`
  - 跨项目知识（反模式/通用经验/工具坑，来源项目、适用多项目）→ `~/qwiki/projects/common/`
  - 项目特定知识 → 对应项目卡；分析报告/数据等素材 → 项目 `resource/`（素材不产卡）
- **必填动作**（生成时自动做）：正文 `>` 首行 = 一句话结论（≤80）+ YAML `summary` = 长摘要（可多行，与 `>` 首行用途不同、不强求同串）+ INDEX 行交给 `qwiki-sync.py <库根> --write`
  - 「正文 `>` 行」指 `>` 引文块的**第一行**，内容必须是**一句话结论**（不是 YAML `summary` 的原文，也不是出处）——自检按「H1 后第一个 `>` 行」取值，把背景/定义/出处写在第一行会被判「总结列不是结论」；依据行另起一个 `>` 段落放后面
- **卡片约束见 skill 根目录 `SCHEMA.md` §公共约定 + §YAML 头公约**（YAML 头 / 一句话结论 / 相关段 / 一张卡一个点 / 卡头自证）——本节不复述，避免两处措辞漂移
- 正文段落为参考骨架（背景/要点/结论），按需取舍，**不强制 schema**——写什么算什么，后续可随时补充
- 卡片身份（聚合卡 / 独立卡、`type`、库归属、无形态演进）见 `SCHEMA.md` §卡片身份——本节不复述。
- 和 import 的区别：note 无项目目录，一条 INDEX 行 + 一个 .md
- 写完后 `cd ~/qwiki && git add -A && git commit -m "note: <标题>"`

---

## status — 查看状态

INDEX 条目数、已入驻项目、知识文件数。

---

## 沉淀标记核实（仅 hook 受体）

若本会话开头被注入「知识沉淀待执行」提示，按 `references/agent-hook.md` §沉淀标记核实 执行。DSH 无 hook 面，不会出现该提示——不要凭队列目录自造卡。

---

## 知识文件模板（呈现 / 用途 × 模板）

**先定用途**（种类由内容推导：谈对象 = 独立卡，谈聚合 = 聚合卡）——用途决定用哪个模板；`type` 只区分**有没有约定骨架**（有 → `card`，自由骨架 → `note`）：

| 呈现 | 用途 | 模板 | type |
|------|------|------|------|
| **聚合卡** | 八段：模块边界 / 职责描述 / 架构设计 / 技术栈 / 代码规范 / 配置命令 / 模块间关系 / 相关 | `templates/card-aggregate.md` | card |
| 独立卡 | 轨迹卡（范围与依据 / 一句话 / 保留 / 拆除 / 否决 / 仅测量 / 未定 / 当前快照 / 卡间索引 / 聚合卡演化与退出标注 / 相关） | `templates/card-track.md` | card |
| 独立卡 | 实测卡（一句话 / 口径 / 数据 / 裁决 / 可复用 / 局限 / 状态 / 相关） | `templates/card-measurement.md` | card |
| 独立卡 | 问题说明卡（现象 / 根因 / 正常流 vs 出错流 / 修复 / 验证 / 复用手势 / 相关） | `templates/card-issue.md` | card |
| 独立卡 | 审查卡（**候选骨架，暂不立模板**：范围 / 逐条发现分级 / 可达性 / 结论） | — | card |
| 独立卡 | 设计说明卡（设计目标 / 结构图 / 流向图 / 关键设计决策 / 时序图 / 相关）——聚合卡「架构设计」段的深化 | `templates/card-design.md` | card |
| 独立卡 | 随笔卡（背景 / 要点 / 结论，自由取舍） | `templates/note-general.md` | note |
| 独立卡 | **…开放**：机制梳理 / 操作手册 / 流程与坑 / 数据口径 …… | — | note |

> 卡片角色判据、公共约定与表达形态见 skill 根目录 `SCHEMA.md` §卡片身份、§表达形态——本文件不复述。

## 架构文档

- **`SCHEMA.md`** = 目标态宪法（目录 / 命名 / 卡片公约 / 表达形态 / 知识互联），唯一真相源在 skill 根，库内不放实例。
- **本 `SKILL.md`** = 怎么做（九操作流程）。三文件分工见 `references/design-decisions.md`，支持文件清单见本文末尾；写卡时按需读 `templates/`、`scripts/`，不要一次全读。
- **操作流程不拆分（2026-10-22 定）**：SKILL.md 就是要**详述怎么做**——九操作、判定动作、核实步骤都留在正文；只有**不参与执行**的内容（坑、决策原因、分发说明、支持文件清单）才进 `references/` 与 README。为压体积把操作拆走 = 为拆而拆，读的人还得二次跳转。

## 收尾自检（无 hook 时的手工兜底）

任何工具、没有 hook 也能跑。任务收尾前自问三句，答「有」就当场落地：

1. **有没有产生可复用的结论？** 有 → 按归属路由建卡 / 更新，然后跑 `qwiki-sync.py <库根> --write` 更新投影。
2. **有没有推翻「已发出的结论」？** 有 → 就地追加 `> ⚠️ 修正（YYYY-MM-DD）：…`，不抹原文。
3. **有没有新坑？** 有 → 写进对应卡片的「坑 / 反模式」段（跨项目通性的进对应项目卡），别只留在对话里。

## 支持文件清单

本 skill 依赖以下模板与参考文件（安装时随 SKILL.md 一并打包，请勿删除）：

- 宪法（与 SKILL.md 平级，唯一真相源）：`SCHEMA.md`（随安装拷贝）
- init 模板（建库）：`templates/index.md`
- 卡片模板（生成卡：**先定用途**；聚合卡 / 独立卡由内容推导）：`templates/card-aggregate.md`（聚合卡）、`templates/card-track.md`（独立·轨迹卡）、`templates/card-measurement.md`（独立·实测卡）、`templates/card-issue.md`（独立·问题说明卡）、`templates/card-design.md`（独立·设计说明卡）、`templates/note-general.md`（独立·随笔卡）；审查卡走**候选骨架**（`type: card`）、机制·手册类走自由骨架（`type: note`）
- **检索**：`scripts/qwiki-search.py`（SQLite FTS5 磁盘倒排，contentless 不存原文；中文二元组；召回后按「字段权重 × IDF × log tf」精排；`--tag` 一级过滤，`--json` 给 agent 用，`--stats` 看规模；索引是生成物，删掉不丢知识）
- **投影生成**：`scripts/qwiki-sync.py`（INDEX 两列由卡片推出来；`--write` 落盘，修复投影类红灯不用手改；`--strict` 让「需人判」返回非零）
- **自检脚本**：`scripts/qwiki-check.py`（SCHEMA/SKILL 约定的可执行版：卡片头部 / 投影 / 纯度 / 双链 / 素材 / 命名 / slug / 可达 / 轨迹 / 带头 / YAML；只读、仅需 python3 标准库，PyYAML 可选，缺库时该项标「跳过」不计通过；`--all` 打全量明细）
- **核心测试**：`scripts/qwiki-tests.py`（守卫每条一个 fixture：缺 `>` 不覆盖总结、出处首行、空段补表头、`|` 拒绝写表、段头错位、表体断裂、PyYAML 跳过、幂等、H1≠title；断言退出码 + 报错串 + 落盘结果，退出码即结论）
- **发布前检查**（发布本仓时用，不是知识库操作）：`scripts/publish-check.py`（扫真实项目代号 / 内网 IP / MAC / 长 hash / 凭据 / 本机路径）+ `scripts/number-audit.py`（宪法与对外文档不得含实测数字——判据原文见该脚本 docstring 的 `CURRENT:` 行，**引用不复制**）+ `scripts/hooks/pre-push`（`git config core.hooksPath scripts/hooks` 启用，**五项都跑**（核心测试 / 脱敏自检 / 脱敏 / 数字 / CHANGELOG 同步），任一命中即拒绝推送）
- hook 脚本（自发生长事件驱动，四 hook 工具兼容 + pi 扩展）：`scripts/knowledge-sediment-lib.sh`（归一化层）+ `scripts/knowledge-sediment-hint.sh`、`scripts/knowledge-sediment-toolcheck.sh`、`scripts/knowledge-sediment-inject.sh`、`scripts/knowledge-sediment-subagent.sh`（ZCode 无 SubagentStop，不注册该项）；pi 适配见 `~/.pi/agent/extensions/qwiki-sediment.ts`（无 hook，事件映射同协议）——**受体现状见 init §跨工具说明**（本机 Hermes/Claude/DSH，DSH 无 hook 面）
- 参考：`references/agent-hook.md`（hook 机制 + 各家注册表 + 沉淀标记核实）、`references/design-decisions.md`（决策原因）、`references/bulk-repair.md`（批量修卡 playbook）
- 版本记录：`CHANGELOG.md`（随安装拷贝，记录版本历史）
