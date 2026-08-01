---
name: qwiki
description: Use when user says qwiki. Knowledge base management.
version: 1.1.0
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
AI:  加载本 skill → 识别操作 → 检查依赖（codegraph/git/目录）
AI:  对话层引导用户确认缺失项（安装 codegraph? git init? SOUL.md 注入?）
用户: 确认/拒绝
AI:  执行操作 → 回报结果
```

**铁律：用户给出意图 → AI 识别操作并直接执行，不反问"你要不要先做环境准备"。**
依赖缺失 → AI 对话层引导用户设定，拿齐就干。

> **AI 交互约定（agent 必读）**：
> - 操作识别：用户说 "qwiki <操作>" 或自然语言意图（录入/同步/检索知识库），映射到九操作
> - 依赖引导：环境依赖（codegraph 未装 / git 未初始化 / SOUL.md 未注入）→ 对话层询问用户是否处理，不静默跳过
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
1. **codegraph 检测**：`which codegraph`
   - 已安装 → 检索链含 codegraph 一环
   - 未安装 → 检索链自动降级到 search_files + read_file（可选增强：自行安装 codegraph 可提升代码检索效率，安装方法见 `references/codegraph-quickstart.md`）
2. `mkdir -p ~/qwiki/personal ~/qwiki/projects`
3. `cd ~/qwiki && git init`
4. 创建 INDEX.md（按 `templates/index.md` 模板生成：空表 + personal 分区 + 维护规则脚注）
5. 创建 ROUTING.md（按 `templates/routing.md` 模板生成：检索链 7 级 + 降级路径 + 自生长规则 + 腐化检测 + 模板指引）
6. `cd ~/qwiki && git add -A && git commit -m "init qwiki"`
7. **SOUL.md 注入检测**：
   - 检查 `~/.hermes/SOUL.md` 是否已有「知识体系」节
   - 已有 → 跳过
   - 缺失 → 提示"SOUL.md 中未声明 qwiki 知识库，检索链不会自动生效。是否添加？"
   - Y → 追加知识体系节到 SOUL.md（含检索链 + L1/L2 说明）

---

## deinit — 全局拆除

1. 确认操作
2. 询问："是否同时卸载 codegraph？"（如已安装）
3. 是 → `codegraph uninstall` 或 `rm -rf ~/.codegraph/`
4. `cd ~/qwiki && cd .. && mv qwiki qwiki.bak.$(date +%Y%m%d)`
5. 建议从 SOUL.md 移除知识库声明

---

## import — 项目入驻（新增，保持纯粹）

新项目从零入驻：AI 四轮阅读 SDK → codegraph 索引 → AGENTS.md 初版 → 目录骨架 → INDEX 登记。**不含卡片化**（卡片归 migrate 和日常蒸馏时机）。

输入：项目名、代码路径（编译入口/Docker 镜像**可选**——不依赖用户提供，见下）。

### 核心原则（2026-07-31 讨论定稿）

1. **AI 读 SDK 本身就是在做 import**——用户不是信息源，只在"审阅初版"介入一次。用户提供不了编译入口/环境是常态，不阻塞流程
2. **编译是可选精化，不是前提**——默认路径不依赖编译；bear 捕获只在编译可用时（用户给了 / AI 找到了 / ops 配好了）作为精化步骤
3. **多信号源交叉**——无环境也能得出可靠工程划分：

| 信号 | 获取方式 | 环境依赖 |
|------|---------|---------|
| 目录结构 | ls / search_files | 无 |
| 构建足迹 | Makefile/CMakeLists/Kconfig/feeds | 无 |
| CI 配置 | .github/.gitlab-ci/Jenkinsfile（金矿：机器可读的编译流程） | 无 |
| 符号调用链 | codegraph explore | 无 |
| manifest | repo 工具文件 | 无 |
| 编译事实 | bear（可选精化） | 有 |

4. **AGENTS.md 是逐步迭代的活文档**——import 只给"可用的初版 + 迭代机制"，允许不完整但必须标注待验证项；任务完成/认知加深/踩坑时更新（与 ROUTING 自生长规则同构）

### 四轮阅读法（AI 读 SDK 的编排）

```
第一轮：这是什么项目？   → 根目录结构/README/manifest/配置文件 → 项目概况 §1
第二轮：怎么编译？       → 构建系统文件/CI/toolchain 痕迹 → 编译入口候选(置信度标注) + 工程划分 §2 §3
第三轮：核心模块是什么？ → codegraph explore 主入口/核心符号(源码+调用链一次拿全) → 分层架构 §4 §5
第四轮：哪里坑？怎么干活？→ 特殊机制/调试相关代码 → 工作流 §8 + 特殊机制 §6
```

每轮阅读必须伴随**验证动作**（编译跑通/代码互证/交叉引用），不验证的读等于没读——读到的结论都要有验证痕迹。

### 步骤

1. **现状检查**（先诊断后行动，2026-07-31 试点修正）：
   - `ls <代码路径>/AGENTS.md` — 已有 → 进入「补充」模式：diff 检查是否过时，按 `references/agents-md-structure.md` 补齐缺失章节
   - `ls <代码路径>/.codegraph/` + `codegraph status` — 已有则跳过 init；新鲜度看 codegraph.db mtime
2. 缺 codegraph 索引 → 若已安装 codegraph：`codegraph init`（分析目录 → 配置排除规则 → init/index，详见 `references/codegraph-quickstart.md`）——**只需源码树，无环境依赖，永远先行**；未安装 → 跳过，检索走 search_files + read_file（降级路径，不阻塞 import）
3. **四轮阅读 SDK**（上表，按 `references/agents-md-structure.md` 的 §1-§10 组织；编译入口按置信度分级：用户提供 > CI 配置 > 构建足迹 > 静态推导标注待验证）
4. **AGENTS.md 初版**：工程划分用多信号源交叉，编译相关章节标注"静态推导，待验证"；保留通用节结构
5. `mkdir -p ~/qwiki/projects/<项目名>/`
6. INDEX 追加项目区块
7. 提示"项目 <项目名> 入驻完成：AGENTS.md 初版（含待验证清单）。编译可用时执行 bear 校正精化（用编译事实替换静态推导）。若存在历史知识（references/design 等），执行 qwiki migrate <项目名> 做老知识迁移。"

### 精化（可选，编译可用时）

bear 全量捕获（capture-project-scope）→ 用编译事实替换静态推导 → 工程划分定稿。环境装配是 ops 的活，不在 import 流程内自动做。

---

## migrate — 主动迁移（老知识升级）

import 之后接力执行：检测项目历史知识（references/design/archive 等 v2 遗产），迁移整理为 v4 卡片体系。

1. **老知识盘点**：`ls ~/qwiki/projects/<项目>/references|design|archive/` + INDEX 现有登记，确认遗产规模
2. **核心模块识别**：高频调试/知识最丰富者优先，一次 1-3 个模块
3. **蒸馏建卡**（`templates/card.md` 八段模板）：
   - 模块边界：search_files 确认文件清单（大库 codegraph query 可能超时；文件存在性验证走 search_files，符号/调用链才用 codegraph）
   - 素材：memory + 已有 references + 代码验证
   - 卡片是「导航 + 核心事实」，细节指向 references（相关卡片段），不搬运全文
4. **INDEX 回填**：新卡登记 + 核心 references 补登记（旧日志/单次分析类按自然淘汰）
5. `cd ~/qwiki && git commit -m "migrate <项目>: <N> 张卡 + INDEX 回填"`
6. 提示"项目 <项目名> 迁移完成：N 张卡，INDEX 回填 M 条。"

无老知识时：提示"未检测到历史知识，无需迁移。"

---

## delete — 项目退出

1. 确认操作
2. 询问：“是否同时删除 codegraph 索引库（<代码路径>/.codegraph/）？”
3. 是 → `rm -rf <代码路径>/.codegraph/`
4. INDEX 删行
5. `cd ~/qwiki && git rm -r projects/<项目名> && git commit -m "delete <项目名>"`

---

## sync — 日常同步

1. `codegraph sync`（未安装则跳过，索引同步在无 codegraph 时不适用）
2. INDEX 一致性校验（死链/漏登记 → 报告修复）
3. **知识腐化检测**（仅 codegraph 已安装时执行）：
   - 遍历 INDEX 中所有项目卡片
   - 提取「模块边界」中列出的关键文件路径
   - 对每个路径 `codegraph query` 验证是否仍在索引中
   - 缺失 → INDEX 对应条目标记 `⚠️ 待验证`，通知用户
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
4. 无匹配 → "知识库中未找到相关条目，自动回落 AGENTS.md → codegraph → web_search"

`qwiki explore` — 输出 INDEX 全文概览

---

## note — 随手笔记

`qwiki note <标题>` → 创建 `~/qwiki/personal/<slug>.md` → INDEX 加一行。

- 不强制七段模板，写什么算什么
- slug 从标题自动生成（小写+连字符）
- 正文后续可随时补充
- 和 import 的区别：note 无 codegraph、无 AGENTS、无项目目录，一条 INDEX 行 + 一个 .md
- 写完后 `cd ~/qwiki && git add -A && git commit -m "note: <标题>"`

---

## status — 查看状态

INDEX 条目数、已入驻项目、codegraph 状态、知识文件数。

---

## 知识文件模板（八段）

模块边界 / 职责描述 / 架构设计 / 技术栈 / 代码规范 / 配置命令 / 模块间关系 / 相关卡片

## 架构文档

本仓库 `references/spec.md`（知识库目录结构规范）。知识库设计方法论演进记录见各版本架构文档。

## 支持文件清单

本 skill 依赖以下模板与参考文件（安装时随 SKILL.md 一并打包，请勿删除）：

- 模板：`templates/index.md`、`templates/routing.md`、`templates/card.md`、`templates/note.md`
- 参考：`references/spec.md`、`references/agents-md-structure.md`、`references/codegraph-quickstart.md`
