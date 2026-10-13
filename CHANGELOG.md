# Changelog
## 2.10.0 (2026-10-12)

### Changed

- **素材一律不得带 YAML 头** —— 把「素材 ≠ 卡片」从**语义**推进到**文件形态**。此前 SCHEMA 只说「不强制带头」（同日上午那轮把它从 `type: card` 降成 `reference`，但没定去留），于是库里长期两种都有（带头 50 / 不带头 181）——「有头」不保证是卡片、「无头」也不保证不是，头就失去了判据作用。新口径确立不变量 **有 YAML 头 ⇔ 是卡片**：`resource/` 与 `scripts/` 下的 `.md` 一律删头；素材要记日期就写进文件名（`<YYYYMMDD>-` 前缀）或正文。
  - 实例侧同期清理：48 份 `type: reference` 素材删头；**2 份形态已长成卡片的素材升格为真卡**（机制梳理 / 方案文档 → 移位到项目根 + 补 `type: card` 头 + 登记 INDEX），升格后暴露的死链（卡片里的 `[[...]]` 指向素材）一并改为路径引用
  - 带头文件计数 234 → 186（恰等于卡片总数），素材带头数归零

### Added

- 自检第 9 项「素材/脚本不得带头」；`SKILL.md` §sync 补对应人工处置口径（删头，或走升格为卡）

### 附带

- 版本 2.9.0 → 2.10.0

## 2.9.0 (2026-10-12)

### Added

- **`scripts/qwiki-check.py` —— 把 SCHEMA/SKILL 的约定变成可执行断言的只读自检脚本**。库的约定此前全靠人（或 AI）记住并逐条核对，这轮实修暴露了代价：同一份约定写成文字没人执行，就会在 INDEX、命名、头部三个面上同时漂移，而且**复验三次才抓干净**。8 项断言：
  1. 卡片头部：H1 在正文首位 / H1 后第一个非空块是 `>` 引言行 / 有 `> 依据`·`> 状态`
  2. INDEX 正投影：标题列 = `title`、总结列 = `>` 行、一卡一行、无漏登记
  3. INDEX 纯度：只登记卡片、无死链、摘要长度
  4. 双链只连卡片（死链 / 指素材）
  5. 卡片引用的素材路径（存在性 + 不残留旧目录名）
  6. 命名约定（字符集 / 日期位置）
  7. 轨迹卡归属（入链 ≥1 张模块卡）
  8. YAML 头可解析（需 PyYAML，缺库则跳过并标注）
  - **只读**、退出码 0/1（可串进 hook 或 CI）、**仅需 python3 标准库**——自检工具本身不该因为别人环境少个包就跑不起来
  - 判据两处易踩：路径检查**只认首段是真实项目名**（代码仓也有 `0_workbench/change/…`、`text/data/…` 这类同名段，不加这条全是假阳性）
  - **做过反向验证**：种 4 个缺陷（H1 不在首位 / 文件名下划线 / 摘要被改 / INDEX 死链），5 项未通过、退出码 1 —— 不是橡皮章
- `SKILL.md` §sync 增「步骤 0：先跑自检」，人工作业按脚本报的条目处置；支持文件清单登记该脚本

### 附带

- 版本 2.8.5 → 2.9.0

## 2.8.5 (2026-10-12)

### Fixed

- **`templates/index.md` 没跟上今天新立的 INDEX 三条规则**——与 v2.8.2 修模板那次是同一个病：**约定写进了 SCHEMA，却没进模板，于是新建的库从出生起就不合规**。补：
  - 表头补「两列都是卡片集的正投影，不另写」（标题列 = `title` = H1；总结列 = `>` 行 = `summary`）
  - 补「总结 ≤60 字符（上限 80）」「一张卡 = 一行」
  - 示例行由 `<模块名>（模块卡）` 改为 `<卡片 title，与正文 H1 同串>`——原示例自带括注，等于示范了违规写法

### 附带

- 版本 2.8.4 → 2.8.5

## 2.8.4 (2026-10-12)

### Added

- **§命名约定 重写为三条硬规则 + 一条硬要求**（原只有一句「全小写 + 连字符」，指导不了实际）：
  1. **字符集**：全小写、`-` 分词；不用 `_`、大写、空格
  2. **日期**：要用就**一律前缀** `<YYYYMMDD>-`（不用后缀、不用 `YYYY-MM-DD`）。日期用于**一次性记录**；领域与方法论卡不带日期
  3. **唯一性**：`[[slug]]` 靠 slug 解析 ⇒ 全库唯一；语义相同的**同名族**（同一角色的卡在多个项目各有一张）**族内一律加项目名前缀**
  - **正文 H1 必须是正文第一行**（其前不得有任何内容）
- **教训入规范**：曾有一张卡把 15 行「后续修正」块引用排在 H1 之前，取「H1 后第一个 `>` 行」的脚本因此把块引用里的 `## ⚠️ …` 标题当成了摘要，**一路传进 YAML 与 INDEX 而无人察觉**——顺序错位不会被格式检查抓到，只会污染下游。故 `sync` 增列此检查
- `SKILL.md` §sync 新增两项：**命名违规**（字符集 / 日期位置 / 同名族前缀不齐）、**H1 不在正文首位**

### 实例侧同步（`~/qwiki`）

- **改名 20 处**（波及 52 条 `[[链接]]` + 33 个文件）：17 张日期后缀 → 前缀（`aic8800-rootfix-20260902` → `20260902-aic8800-rootfix`…）；2 张下划线 → 连字符（`some_workflow`、`some_app`）；1 处同名族补齐（`build-flash-system` → `项目A-build-flash-system`，与 项目B/项目C/项目D/项目E 四张对齐）
- 修 1 张卡的 **H1 顺序**（`20260905-rx-busrx-2x-audit`）+ 由此污染的 INDEX/YAML 摘要
- 结果：**命名违规 0、H1 非首位 0**

### 附带

- 版本 2.8.3 → 2.8.4

## 2.8.3 (2026-10-12)

### Changed

- **「总结」列长度口径由「≤60 汉字」改为「≤60 字符」**（上限 80）。原口径等于允许 ~120 字符，实测据此长到**中位 87 字符、最长 122**——INDEX 一眼扫不动。压缩至 **中位 51、最长 70**（超 60 的从 158 条降到 7 条，剩下的都是标识符密集、再砍就丢 grep 锚点）
- **一张卡 = 一行**。INDEX 原允许一张卡挂多条子条目（`aic8800-515-arch-review` 曾占 6 行、另两张各 2 行），子发现**属于卡片正文**，INDEX 只做导航。合并掉 7 行
- `sync` 新增两项检查：一张卡占多行、总结列超长（>80）

### 附带

- 版本 2.8.2 → 2.8.3

## 2.8.2 (2026-10-12)

### Fixed

- **模板从不生成 `> 依据` / `> 状态`**——v2.7.1 定的「按容器分轨」附加约定只活在 SCHEMA 里，**没有进过任何模板**。后果：实例里 180 张卡的这两行是手工补的，而**按模板生成的新卡从出生起就不合规**。本次补齐：
  - 覆盖型（`card-module` / `card-design` / `note-general`）→ 头部块加 `> 依据：<代码版本 / commit / 固件>（判不出写 `未标注`）`
  - 追加型（`card-measurement` / `card-issue`）→ 头部块加 `> 状态：…`；`card-measurement` 原有的 `## 状态` 段删除（那是 v2.7 前的形态，与约定重复且实测只有 1 张卡还留着）
  - `card-track` → 上一版刚把轨迹卡判为追加型，模板里却还写着 `> **依据**：…本卡是**活卡**`（正是被推翻的那个读法）⇒ 改为 `> 状态`，并把「§F 当前快照可覆盖改写」写成显式例外
- **`INDEX` 的「标题」列口径缺失，已 52/183 行漂移**。定案：**INDEX 是卡片集的正投影，两列都取自卡片，不另写**——「总结」列 = 卡片 `>` 引言行 = YAML `summary`；「标题」列 = 卡片 `title` = 正文 H1。实例按卡片回填 **155 行**，复查 191/191 一致。`sync` 新增该项检查
  - 理由与 v2.7.1 统一「总结」列**完全相同**：一个字段一个真相源。实测 183 行里 52 行标题与卡片 `title` 完全对不上（另有 78 行是截断改写），而无人察觉
- 版本 2.8.1 → 2.8.2

## 2.8.1 (2026-10-12)

### Fixed

- **Claude Code 侧的检索引导与沉淀指令从未注入过**（本次审查实测发现，最重的一条）。两处叠加：
  1. `sediment_detect_tool` 的 payload 兜底表**只认 `SessionEnd`**，`UserPromptSubmit` / `PostToolUse` / `SubagentStop` 三个事件全判 `unknown`；而 `inject.sh` 对 `unknown` 是静默 `pass`
  2. `references/agent-hook.md` 的 Claude 注册表**没按本文自己的规矩传工具名**（第 1 参），settings.json 里也就没传——两条路同时断
  - 修：兜底表补 PascalCase 事件 → `claude`；注册表与实例 settings.json 的 4 条命令补 `bash <script> claude`。实测两条路径均正常输出 `hookSpecificOutput`
  - 附带影响：此前唯一生效的是 CLAUDE.md 里那份「口径备份」——即 hook 那路是断的而无人察觉
- **轨迹卡容器归属的内部矛盾**（§骨架表写「覆盖（逐项追加）」，§公共约定与§活知识原则归「追加型」）。统一为 **追加型**，并把「§F 当前快照可覆盖改写」写成**唯一例外**（§F 本就是「当前值」，与 §H「只追加」不冲突）
- **v2.7 重构残留**：「三形态」表述（SCHEMA §目录结构、SKILL §note）→ 两角色 × 骨架；冲突标注示例的 `reviews/` → `resource/`；SKILL 引用已删的 ROUTING；§migrate 的模板清单缺轨迹卡/实测卡；§migrate 收尾提示的旧目录名
- **§公共约定 覆盖型漏列设计说明卡** → 补上；`> 依据` / `> 状态` 都补了「判不出写 `未标注`，不要编」的兜底
- **§知识互联「升级（note→card）不动链接」与 §无形态演进「不存在演进」互斥** → 改为「跨库归位只更新链接目标」
- **§迁移规则 的「L2→L1：只能升到 memory」** 是 Hermes 记忆分层的孤词（全篇无 L1/L2 定义）→ 删
- SKILL §deinit 一条命令**引号未闭合**
- 实例侧同步：**75 张卡 `title` ≠ 正文 H1**（占 41%，其中 27 张 H1 字面就是「一句话」）→ H1 统一回填 `title`；**3 张 `type` 越界**（`design`/`task`/`方法论`）→ 归位为 `note`

### 附带

- 版本 2.8.0 → 2.8.1

## 2.8.0 (2026-10-12)

### Removed

- **知识库不再持有 `HISTORY.md`（init 不再创建，`templates/history.md` 删除）**。理由有两条，都是实测出来的：
  1. **它是 skill 自己的历史，不是知识库的内容**。逐条核对实例那份档案：93 条里 **32 条是 skill 的方法论定稿与版本沿革**（import 四轮阅读、hook 事件驱动、migrate 语义收敛、八操作→九操作…）——这些的权威形态就是本 skill 的 `SKILL.md`/`SCHEMA.md` 当前态与 `CHANGELOG.md`，实例里那份是**叙述体的第二副本**，正是本库反复吃过的「副本必然漂移」那一课
  2. **另外 61 条根本不是知识**：一半是「哪个文件哪天建/改」的流水（`git log` 已有，且更准），一半是本机环境运维（家目录清理、工具升级、定时任务抢修）——跟知识库无关
- **确立单向流：仓 → 实例**。skill 仓是权威源；实例**不得**把内容回灌进仓（迁移那次差点把 69 处项目名与内网 IP 写进公开发布仓 —— 方向错了，不是脱敏能救的）
- 连带改动：`SCHEMA.md` §目录结构 去掉 HISTORY.md、§YAML 头公约 排除项收窄为 INDEX.md、§迁移规则 的「HISTORY.md 只进不出」条改写为「知识库不含历史档案文件」；`SKILL.md` §init 步骤由五步改四步、支持文件清单去掉 history 模板

### 附带

- 库骨架收敛为四类，位置可机械判定：**`INDEX.md` + 卡片（根层 `*.md`）+ `resource/`（素材）+ `scripts/`（脚本）**
- 版本 2.7.3 → 2.8.0

## 2.7.3 (2026-10-12)

### Changed

- **素材目录五个名字合并为单一 `resource/`**——`references/`｜`design/`｜`archive/`｜`change/`｜`data/` 是**按来源**起的五个名字，指的是**同一个角色**（素材）。合并后 `projects/<项目>/` 下只剩三类，且**位置可机械判定**：
  ```
  根层 *.md   = 卡片
  resource/   = 素材（知识卡片引用的数据来源）
  scripts/    = 脚本
  ```
- **顺带消掉一处旧歧义**：原来 `design/` 一名既指「workbench 设计产物（素材）」又被人当成「设计说明卡」——§卡片身份 专门写过一段提醒去区分它。合并为 `resource/` 后这个歧义自动消失，那段提醒改写为沿革说明
- `SCHEMA.md` §目录结构 / §INDEX 登记规则 / §YAML 头公约 / §卡片身份 / §知识互联 全部改用 `resource/`；`SKILL.md` §migrate / §sync / §note 的素材路径同步
- 实例侧迁移（`~/qwiki`）：5 个项目共 234 个条目从旧目录并入 `resource/`（项目F 45 / 项目A 140 / 项目A-wifi 10 / 项目D 28 / 项目G 11，**无重名冲突**）；25 个卡片文件里 132 处素材路径引用改写；INDEX 表头「路径形如」示例同步
- 另修两处「既不是卡也不是脚本」的 `.md`（本次一并归位）：
  - `项目A/scripts/git-commit-format.md` 与 `项目F/scripts/git-commit-format.md` **内容完全相同**（跨项目重复归档）⇒ 合并为一张 common 卡 `[[git-commit-format]]`，两份脚本目录副本删除，两处引用文字改指卡片
  - `项目F/scripts/README.md`（脚本清单 + 归属约定 + `<工具包>` 解散决策，此前不在 INDEX 里、检索不到）⇒ 归位为卡 `项目F-scripts-toolkit.md`
- 版本 2.7.2 → 2.7.3

## 2.7.2 (2026-10-12)

### Changed

- **定案「素材不进 INDEX，素材只是知识卡片引用的数据来源」**——修掉 SCHEMA 内部的一处自相矛盾：
  §目录结构 一直写着素材「自然淘汰，**核心回填 INDEX**」，而 §卡片身份 又说素材「不是卡片」。
  两条不能同时成立：不是卡片的东西怎么会有 INDEX 登记行。现统一为**不登记**。
  - **INDEX 登记规则**：新增一条「本表只登记卡片」——`projects/<项目>/*.md` 与 `personal/*.md`。
    素材（`references/`｜`design/`｜`archive/`｜`change/`｜`data/`）与脚本（`scripts/`）一律不登记；
    要找它们，从引用它的卡片的「相关」段按路径找（形如 `项目A/references/xxx.md`）
  - **§知识互联**：新增「**双链只连卡片**」——`[[...]]` 出现在卡片里就必须解析到另一张卡；
    指向素材用**路径引用**，不写双链。死链检测口径相应改为「对照卡片表」，并新增报「卡片里 `[[...]]` 指向素材」的口径错误
  - **§卡片身份 末段**：素材补上「**不进 INDEX、不做双链**，只被卡片按路径引用」
  - **`templates/index.md`**：去掉示例里的 reference 登记行；脚注由「核心模式/基线/调试文档必须登记」改为「素材/脚本/数据一律不进表」
  - **`SKILL.md` §migrate / §sync**：migrate 只登记新卡；sync 新增「素材误登 INDEX」检查项（删行前若内容只在表内留痕，先转 HISTORY）
- 实例侧同步（`~/qwiki`，一个 commit 内完成）：INDEX 由 319 行收敛为 **189 行纯卡片目录**（182 张卡全覆盖，
  0 缺登记）；删掉的 134 行里 130 行指向素材、4 行是「收编记录」目录行——后者内容转入 `HISTORY.md`，避免随行删除而丢失
- 版本 2.7.1 → 2.7.2

## 2.7.1 (2026-10-12)

### Fixed

- **修掉 v2.6.2 与 v2.7.0 之间的一处自相矛盾**：v2.6.2 写「INDEX 的总结列与卡片 YAML `summary` 是两份东西、**不要求相等**」，v2.7.0 又写「H1 后那句 `>` 引言行**是 INDEX 登记行的来源**」——两句话不能同时成立。现统一为**三处同源**：`YAML summary` = `>` 引言行 = `INDEX 总结列`（目标 ≤60 汉字；真相源在 YAML，改一处即改三处）。理由就是本库反复验证的那条——**副本必然漂移**（今天刚在 4 个模板里抓到一处隔日漂移的副本）
- 版本 2.7.0 → 2.7.1

## 2.7.0 (2026-10-12)

### Added

- **卡片身份从「三形态」改为「两个角色 × 骨架」**（`SCHEMA.md` §卡片身份 重写）。实测 133 张 card 里 85% 不属于原三形态中的任何一种——原框架把「骨架」当成了「分类」，而它们的角色（事件卡）本就清楚，只是骨架随事件不同。新框架：
  - **聚合卡**（组织一个领域，是入口，**覆盖型**容器）/ **事件卡**（记录一次事件，闭合即冻结，**追加型**容器）
  - 六个骨架挂在角色下：模块卡、**轨迹卡**（新）、**实测卡**（新）、问题说明卡、审查卡（候选）、设计说明卡（按需深化）+ 随笔卡
  - **容器分轨**是新增的核心机制：覆盖型随便改（读时永远最新），追加型只许追加（改它就是篡改历史）。原「活知识原则」只有一句笼统的"过时修正甚至销毁"——对大量已冻结的事件卡是错的
- **新模板 `templates/card-track.md`（轨迹卡）**：一条线（战役）的决策账本，五栏裁决分类（保留 / 拆除 / 否决 / 仅测量 / 未定）。**它的不可替代性在「否决」和「未定」两栏**——那些"试过、测完否了"的决定没有产物卡，模块卡的链接索引接不住（现有那张 515 总账卡里 `tasks.md` 出现 69 次、卡链只有 25 条，就是这个道理）
- **新模板 `templates/card-measurement.md`（实测卡）**：一次受控测量 + 裁决。**「口径」段是必填的立卡理由**——实测 80% 的卡含实测数字，只有 33% 写了测量条件，而库里最贵的一次教训正是「口径决定结论：同一天、同一臂，三个口径差 12 个百分点」
- **公共约定新增两条**：① H1 之后紧跟一句话结论（`>` 引言行，≤60 汉字）② 按容器分轨的附加行——覆盖型写 `> 依据：<版本/commit>`，追加型写 `> 状态：已闭环/已失效/已被取代`
- **轨迹卡归属规则**：每张轨迹卡都应能从某张模块卡走到（入链中至少 1 张模块卡），否则这条线缺一张模块卡。反向不要求——模块卡可以没有轨迹卡

### Changed

- `SKILL.md` §知识文件模板 → §知识文件模板（角色 × 骨架）；§支持文件清单、sync 的防腐化判定（改为按容器分轨 + 新增轨迹卡归属检查）同步
- **模板命名族**：`card-module` / `card-track` / `card-measurement` / `card-issue` / `card-design` / `note-general`——同族皆「一个具体东西」的可数名词，中文名与英文名保持直译对
- **术语澄清**：这类卡叫**实测卡**，不叫"优化卡"（相当一部分此类卡的结论是"测完决定不做"），也不叫"实验卡"（有一整类只测量、未改码）
- **修掉一处模板 ↔ 宪法的漂移**：4 个模板的 YAML 里都写着 `summary: <一句话总结>（真相源：INDEX 登记/检索直接提取）`，而 v2.6.2 已把该表述从 SCHEMA 改掉——模板脚注写着"本模板不复述，避免与宪法漂移"，而这一行正是复述，漂移发生在改动后 1 天内。已删括注
- `templates/index.md` 头部「AI 先扫本目录（~500 token）」改为「按项目段读，勿全文加载」+ 「总结列是一句话摘要」（与真实 INDEX 对齐）；personal 段列名 `知识` → `标题`
- 版本 2.6.2 → 2.7.0

### 现有知识库无需改动

本版是**框架与模板**的变更，不要求迁移已有卡片：新骨架按「卡片被 touch 时顺手归位」的既有节奏逐步套用（同 SCHEMA §YAML 头公约 的存量政策）。

## 2.6.2 (2026-10-12)

### Changed

- **宪法两处表述与事实对齐**（项目A-wifi 全库体检时发现，均属「文档描述与库内现实相反」）：
  - §YAML 头公约 的适用范围由「`projects/**/` 与 `personal/` 下的 .md」**收窄为卡片与知识文档**，明确排除 `references/`|`design/`|`change/` 下的素材文档——原文与 §卡片身份「reference/design/change 是素材，不是卡片」自相矛盾；实测有 208 个素材文档因此既像欠账又像合规，无从判定
  - §INDEX 登记规则 与 §YAML 头公约 的 `summary` 注释：明确 **INDEX 的「总结」列是检索用压缩摘要，与卡片 YAML `summary` 是两份东西、不要求相等**。原文「INDEX 登记/explore 检索**直接提取**」在 INDEX 总结被压缩后不再成立——实测 INDEX 总结列曾占全表 77.4%（209KB/271KB），已逐行瘦身为一句话（271KB → 91KB）
- 版本 2.6.1 → 2.6.2

## 2.6.1 (2026-10-12)

### Fixed

- **`install.sh` 备份落点移出 skills 扫描根**（本机重演一次后修掉）：原先把旧版 `mv` 到 `${dest}.bak.<ts>`＝`~/.claude/skills/qwiki.bak.<ts>`，而各 agent 按「含 `SKILL.md` 的目录」发现技能、不看目录名 ⇒ **每次升级都在技能列表里多出一个同名技能**（重名歧义下会静默跳过其一）。改为落 `${dest_dir%/skills}/skills-backup/`，即 `~/.claude/skills-backup/qwiki.bak.<ts>`
- 存量残留：`~/.claude/skills/` 与 `~/.hermes/skills/` 下各一个 `qwiki.bak.20261012113713` 已**移入**新位置（未删除，仍可回滚）
- README 的备份路径说明、install.sh 收尾提示同步
- 版本 2.6.0 → 2.6.1

## 2.6.0 (2026-10-12)

### Added

- **卡片新增两种形态：设计说明卡、问题说明卡**（`templates/card-design.md` / `card-issue.md`），与模块卡、随笔卡并列。设计说明卡承载结构图 / 流向图 / 泳道图 / 时序图，问题说明卡承载「正常流 vs 出错流」伪代码对照——把此前只存在于个别卡里的图表与伪代码做法，变成规范承认的形态
- **`SCHEMA.md` 新增 §表达形态**（宪法层，只写"写什么"，格式与骨架归模板）：该给图的判据（结构分层 / 跨 ≥2 组件交互 / ≥3 步流转 / 含时序竞态或队列竞争）、该给伪代码的判据（根因与修法能写成正常流 vs 出错流对照）、**锚点硬要求**（图内节点与伪代码关键行必须写真实符号名或 `file:line`，否则退化为装饰）、禁止复述文字的装饰图、以及「无图可画不强配」的例外
- **`SKILL.md` sync 操作新增第 3 步「表达形态体检」**：作用域限定为设计说明 / 问题说明形态的卡（按正文结构判定）＋ 本次新写入的卡，存量模块卡与随笔卡不报——避免对全库存量刷屏误报

### Changed

- **模板改名**：`templates/card.md` → `card-module.md`、`templates/note.md` → `note-general.md`。两族统一为 `<族>-<形态>.md`，前缀 = YAML `type`；`note-general.md` 为将来新增 `note-<形态>.md` 预留族位（届时零成本新增，不必再改名）
- **形态之别落在模板选择上，不在 `type` 值**：模块 / 设计说明 / 问题说明三形态的 `type` 一律是 `card`——避免与 workbench 的 `type: design`（`design/` 目录下的工作产物，非卡片）撞车。`SCHEMA.md` 已加一句区分说明
- **四份模板脚注收敛为一行指针**（指向 `SCHEMA.md` §卡片身份 / §表达形态），不再各自复述卡片身份——每条复述都是一处漂移源（同 §SCHEMA 单一真相源 记载的教训）
- `SKILL.md` §知识文件模板（八段）→ **§知识文件模板（卡片形态）**，列出四形态与各自模板；§支持文件清单、§架构文档、README 仓库结构同步
- `SKILL.md` `import` / `migrate` 步骤里的模板引用改为按形态选（原先硬编码八段模板）
- `SCHEMA.md` §卡片身份 公共约定 #5「一张卡一个点」措辞随三形态更新（card=一个独立形态，非仅模块）；§无形态演进、§目录结构注释同步
- 版本 2.5.3 → 2.6.0

## 2.5.3 (2026-10-10)

### Added

- 新增「沉淀标记核实」章节（会话开头被注入「知识沉淀待执行」时）：hook 只在注入文本里告知标记，标记文件本身读后即删 ⇒ 先核实再动手。核实顺序＝① 库侧现状（`git log` + `git status`）② state.db 反查窗口内 `delegate_task`（判标记真伪/是否陈旧）③ 跨工具排查（队列由各 agent 共享）④ 判定并回报（含证伪项）
- 三个坑：`agent.log` 里反复出现的 `shell hook registered: subagent_stop` **只是进程启动日志**，不是子代理活动证据；**空 detail 是陈旧/退化标记的指纹**，会等下一次注入才被消费（几天后「突然」出现在某会话开头）；已删标记无法从日志回捞（注入文本是唯一残留证据）
- 版本 2.5.2 → 2.5.3

## 2.5.2 (2026-09-28)

### Changed

- **hook 注入文案加「工作环境」一行**（`scripts/knowledge-sediment-inject.sh`）：代码仓唯一入口 = `/mnt/data/<项目>/CLAUDE.md`、Hermes 侧环境导航 `~/.hermes/AGENTS.md`（配合入口文件定案 09-28：仓内不再放 AGENTS.md）。这是「规约每轮在场」的唯一可控通道
- 版本 2.5.1 → 2.5.2

## 2.5.1 (2026-09-28)

### Changed

- 回灌本机 Hermes 副本的实测修正：沉淀标记去重优化（09-03：toolcheck 源头去重 + inject 兜底去重）
- 版本 2.5.0 → 2.5.1


本文件记录版本历史。版本号定义在 SKILL.md frontmatter 的 `version` 字段（单一真相源）。

## 2.5.0 (2026-08-29)

### Added（pi 支持入物料）

- **补 pi 为正式支持的 agent**：SKILL.md「跨工具说明 / hook 注册检测 / 事件驱动层 / hook 脚本」四处、README「跨工具兼容 / 多 agent 目标」两处，全部把 pi 纳入口径
- **pi 适配机制**：pi 无 hook 机制，由 `~/.pi/agent/extensions/qwiki-sediment.ts` 扩展承接同一标记协议（before_agent_start 注入检索引导+消费队列 / tool_result 写标记 / session_shutdown 跨会话提醒），标记队列 `${XDG_STATE_HOME:-~/.local/state}/qwiki/sediment/` 跨工具共享
- 版本 2.4.2 → 2.5.0

## 2.4.1 (2026-08-19)

### Fixed（分发就绪：安装通道 + 沉淀信号收敛）

- **hint.sh session_end 每轮空响**：Stop 门禁工具（Codex/ZCode）不再写 session_end 标记（Stop block 已承担会话内沉淀，遗留空标记导致下轮 inject 每轮空响「沉淀待执行」）；Hermes/Claude 仅在有实质标记时写跨会话提醒
- **inject.sh 空标记过滤**：过滤无 detail 的 session_end 标记（空提醒不触发沉淀指令），读后即删仍清理全部标记
- **toolcheck.sh 验证正则收紧**：去掉 `check`/`test` 宽泛词（grep 搜索含 check 被误配为验证成功），改 `\b(make|build|compile|verify|flash|burn)\b|烧录|编译` 词边界匹配
- **lib.sh 工具判定兜底补全**：`sediment_detect_tool` fallback 补 `SessionEnd`→claude、`Stop`→codex（无注册参数时正确分流，hint.sh 门禁分支依赖该判定）
- **install.sh REPO_URL 可覆盖**：`QWI_SKILL_REPO_URL` 环境变量支持本地仓/私有镜像源，便于分发前本地验证安装命令
- 版本 2.4.0 → 2.4.1

## 2.4.0 (2026-08-18)

### Changed（审查修复）

- **README 安全警告泛化**：`hermes skills install` → 「部分 agent 的 skills install」，tap 方式示例标注「以 Hermes 为例，其余 agent 同理」
- 版本 2.3.0 → 2.4.0

## 2.3.0 (2026-08-18)

### Changed（ZCode hook 事件驱动层适配）

- **四工具归一化**：`knowledge-sediment-lib.sh` 增加 `sediment_detect_tool`（注册参数 `$1` 优先，payload 特征兜底），工具判定与输出协议解耦
- **inject.sh 输出协议分支**：Hermes 走 `{"context"}`，Claude Code / ZCode 走 `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext"}}`（ZCode 与 Claude 同协议），Codex 静默不输出
- **toolcheck.sh 兼容 Claude/ZCode 工具名**：代码修改检测加 `Write/Edit/ApplyPatch/NotebookEdit`，验证检测加 `Bash`；文件路径/命令字段优先读 `tool_input`（ZCode/Claude payload 格式）
- **hint.sh**：ZCode Stop 门禁与 Codex 同协议（`{"decision":"block","reason"}`），兼容无需改动输出，仅加工具判定；ZCode 内建最多 3 次续跑
- **注册表**：`references/agent-hook.md` 增加 ZCode 段（`~/.zcode/cli/config.json` 顶层 `hooks` 键，`enabled: true` 启用，注册三项：UserPromptSubmit/PostToolUse/Stop，无 SubagentStop）；SKILL.md init 步骤 6 / note 段 / 跨工具说明同步
- 版本 2.2.0 → 2.3.0

## 2.2.0 (2026-08-18)

### Added

- **ZCode 安装目标**：install.sh 支持 ZCode（探测 `~/.zcode` → 安装到 `~/.zcode/skills/qwiki`），README 补 `--target zcode` 示例；hook 脚本对 ZCode 目标同步到 `~/.zcode/scripts/`（ZCode 无 hook 事件机制，仅复制无副作用）

## 2.1.1 (2026-08-18)

### Fixed（inject.sh 空细节尾巴，2026-08-18 实测定位）

- **`scripts/knowledge-sediment-inject.sh` 裸「细节：」尾巴**：沉淀指令拼接无条件输出「细节：」前缀，details 为空（session_end 标记天然无 detail）时 join 空列表 → 注入文本以「细节：」裸结尾，误似截断。修复：details 非空才拼「细节：…」段
- 同步：`~/.hermes/scripts/`（运行时）+ `~/.hermes/skills/qwiki/scripts/` + 本发布仓，三处一致

## 2.1.0 (2026-08-04)

### Changed（migrate 语义收敛 + sync 结构审视，2026-08-04 讨论定稿）

- **migrate 重定位为「知识入迁」**：统一判据 = 来源知识是否已是当前 v4 卡片体系？不是 → migrate。旧 wiki 遗产、本库 v2 遗产（references/design/archive）、其他工具沉淀、笔记导出——场景统一，动作一致（盘点 → 蒸馏建卡 → INDEX 回填）。本库版本升级 = 把旧版本知识库当「别的知识库」迁入，非库内原地变形
- **migrate 参数放开**：`migrate <项目>` → `migrate <来源> [目标]`（来源 = 旧库路径/项目名/笔记目录，目标可选）；新增归属路由步骤（personal / common / 项目）
- **migrate 边界声明**：只做「迁入当前版本」，v4 体系内结构调整（归属调整、上浮 common）不归 migrate
- **sync 新增第 3 步「结构审视」（主动防腐化）**：归属调整（放错库/层级的卡归位：personal ↔ projects、项目 ↔ common）——发现即处理，与检测驱动防腐化互补。步骤顺延（git commit 变第 4 步）
- import 完成提示措辞「做老知识迁移」→「做知识入迁」
- 版本 2.0.0 → 2.1.0

### Removed

- **note→card「按需演进」概念废除（2026-08-04 定稿）**：note（personal/）与 card（projects/）是两个库，归属由来源决定，不存在形态演进——随笔卡不会「成熟为模块卡」。跨库移动仅发生在归属错误时（归位，归 sync 结构审视）。SCHEMA 卡片身份节 / note 模板 / SKILL.md note 节同步修正（历史版本条目保留原名）

## 2.0.0 (2026-08-03)

### Changed（SCHEMA 单一真相源收敛，库内不放置实例）
- **~/qwiki/SCHEMA.md 实例删除**：宪法唯一真相源在本 skill 根目录 `SCHEMA.md`（随 skill 发布/安装）。原知识库实例 = 第三层 copy（仓库 → 安装目录 → 知识库），已真实漂移（实例改 [[module-slug]] 示例、skill 快照漏同步，workbench-spec 死链示例残留）——双头维护风险实锤
- **init 不再生成 SCHEMA.md**：知识库骨架 = INDEX/HISTORY + 目录；卡片公约由加载 skill 时读取根目录 SCHEMA.md
- **sync 移除「宪法同步检查」**：无实例可对比；保留一致性校验 + 防腐化判定（判定依据改指 skill 根目录 SCHEMA.md）
- **模板 ↔ 实例同步机制废除**：无实例可同步——宪法变更 = 改 SCHEMA.md + bump 版本 + 发布
- SCHEMA.md 目录树移除自身行；YAML 头排除项改「索引与档案文件」；双链示例修死链（workbench-spec → module-slug）
- templates/history.md 四件套表述改两件套（INDEX/HISTORY）
- 版本 1.9.6 → 2.0.0

## 1.9.6 (2026-08-03)

### Changed
- **SCHEMA.md 提升至 skill 根目录，与 SKILL.md 平级**：`templates/schema.md` 移至根目录改名 `SCHEMA.md`。templates/ 语义 = 可替换的参考模板（模板定位哲学），宪法不可替换——物理位置应表达概念平级（2026-08-01 定稿的平级关系此前只有文字，无物理结构支撑）。install.sh 拷贝清单 +1（SCHEMA.md）；SKILL.md 引用 4 处改路径；README 无引用不动

## 1.9.5 (2026-08-03)

### Removed
- **`templates/routing.md` 移除**：检索链职责已由 hook 承担（inject.sh 每轮注入 / Codex hint.sh Stop 门禁），ROUTING.md 无读者，SOUL/CLAUDE 不再声明检索链（方案 A 定稿）。init 不再生成 ROUTING.md，宪法 `templates/schema.md` 目录结构同步移除，知识库实例 `~/qwiki/ROUTING.md` 一并删除

## 1.9.4 (2026-08-03)

### Changed
- **`references/hermes-hooks.md` 更名 `references/agent-hook.md`**：内容本就是三工具通用注册表（Hermes config.yaml / Claude settings.json / Codex hooks.json），原文件名有误导。SKILL.md / README.md 引用同步更新，CHANGELOG 历史条目保持原名

## 1.9.3 (2026-08-03)

### Fixed
- **install.sh hook 脚本同步**：升级时把 `scripts/knowledge-sediment-*.sh` 一并同步到工具 hook 目录（`~/.hermes/scripts/`、`~/.claude/scripts/`、`~/.codex/scripts/`，即 `${dest_dir%/skills}/scripts`）。修复「只装 skill、hook 跑旧脚本」的覆盖盲区——各工具 hook 注册（config.yaml / settings.json / hooks.json）引用的是工具 scripts 目录而非 skill 目录，之前升级 skill 后需手动同步脚本

## 1.9.2 (2026-08-02)

### Changed
- **Codex hook 注册迁移至 hooks.json**：Codex CLI 不支持 config.toml 内联 hook，改用 `~/.codex/hooks.json`（三层 JSON 结构：event → entries → hooks[]）。事件名 PascalCase（`PostToolUse`/`Stop`/`SubagentStop`）
- **Codex Stop 门禁模式**：hint.sh 在 Codex Stop 事件上读队列标记 → 有标记时输出 `{"decision":"block","reason":"沉淀指令"}` 强制 AI 在结束前执行沉淀（连续 block 8 次后 CLI 自动放行）。`stop_hook_active` 从原始 payload 提取防无限循环
- **Codex inject.sh 不注册**：Codex `UserPromptSubmit` 不处理 hook 输出（`additionalContext` 不被支持），且 inject.sh 读后即删会提前消费标记导致 Stop 门禁看不到。Codex 的沉淀注入由 hint.sh Stop 门禁承担
- **lib.sh EVENT_MAP 补全 Codex PascalCase 映射**：`Stop`→`session_end`、`PostToolUse`→`post_tool`、`SubagentStop`→`subagent_stop` 等（经 hooks.json + dump 实证确认）

### Fixed
- **hermes-hooks.md Codex 段重写**：config.toml 格式替换为 hooks.json 格式，事件全景表 Codex 列改为 PascalCase，stdout 协议补 Codex Stop `decision:block` 通道
- **Codex 端到端验证通过**：预置 verify_done 标记 → toolcheck 写新标记 → Stop 门禁触发 block → 模型执行沉淀（建卡+INDEX+commit）→ 第二次 Stop 放行

## 1.9.1 (2026-08-02)

### Fixed
- **P0 verify_done 状态回归**：toolcheck.sh 补回 `[ "$SEDIMENT_STATUS" = "success" ]` 前置检查——v1.9.0 重写时丢失，失败构建也会写“验证成功”标记
- **P3 payload 传递 ARG_MAX 风险**：lib.sh 归一化层改经临时文件传 payload（原 argv 直传大 payload 如编译日志会触 128KB 单参数上限）
- **P1 README 全面对齐 v1.9.x**：移除已删除文件引用（agents-md-structure/codegraph-quickstart）、依赖表去 codegraph、手动复制补 scripts/、检索链简化、仓库结构树更新

### Changed
- **队列目录迁移至 XDG 约定**：`~/.hermes/state/knowledge-sediment/` → `${XDG_STATE_HOME:-~/.local/state}/qwiki/sediment/`，路径单一真相源定义于 lib.sh `SEDIMENT_QUEUE_DIR`（四脚本统一引用，跨工具语义中性）
- hermes-hooks.md 标题/事件全景改三工具视角（归一化事件 → 三工具事件名映射表）
- templates/schema.md 目录结构去 Hermes 字样（跨工具定位）

## 1.9.0 (2026-08-02)

### Changed（架构升级：跨工具 + 解耦）
- **三工具 hook 兼容（方案 A 落地）**：新增 `scripts/knowledge-sediment-lib.sh` 归一化层——事件名/字段映射统一 Hermes / Claude Code / Codex 三种 payload（一个脚本吃三种），15/15 兼容性测试通过（verify-compat 脚本验证后移除）
- **inject.sh 双重职责**：无条件注入检索引导（替代 SOUL 静态检索链声明）+ 有标记时追加沉淀指令（读后即删不变）
- **解耦 AGENTS.md / codegraph**：import 不再生成 AGENTS.md、sync 不再依赖 codegraph 索引；references 删除 `agents-md-structure.md`、`codegraph-quickstart.md`；检索链简化为 memory → INDEX → 知识文件 → 模型知识 → web_search（代码检索由各工具自身能力承担）
- **SOUL.md 知识体系节精简**为一行兜底（检索引导由 hook 每轮注入）
- **hermes-hooks.md 升级为三工具注册表**：Hermes config.yaml / Claude settings.json / Codex config.toml

## 1.8.4 (2026-08-02)

### Fixed
- **架构审查修复（框架/原理/流程全面 review）**：
  - 模板 ↔ 实例同步机制定稿：模板只服务 init，实例是活宪法；sync 增加「宪法同步检查」对比关键节防漂移（修复 P0：SCHEMA 实例内部矛盾——130 行旧文案与活知识原则冲突）
  - sync 步骤重编号（新增宪法同步检查后 1-6 顺延）
- 知识库实例防腐化同步（~/qwiki 仓库 f9b876f）：SCHEMA 迁移规则对齐模板、12 处双链死链修复（thread_census 改名漂移 / WiFi/perf 链接指向现有卡 / 无宿主去链化）、ROUTING 腐化检测清单更新为 项目A 九卡

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

## 2.4.2 (2026-08-28)

### Added

- install.sh 新增 pi 安装目标（探测 `~/.pi/agent` → 安装到 `~/.pi/agent/skills/<skill>`，pi 自动发现）
- 版本 2.4.1 → 2.4.2
