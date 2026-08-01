# qwiki SCHEMA

> qwiki 目录结构、命名约定、内容纯度标准、卡片公约（YAML 头/卡片身份/知识互联）。
> Last updated: <YYYY-MM-DD>（init 创建）

> **定位**：SCHEMA = 做成什么样（知识库目标态）；SKILL = 怎么做（九操作流程）。平级互补：SKILL 的每个操作都在实现 SCHEMA 定义的目标态。
> **命名决策**：本文件用 SCHEMA（结构蓝图）长期代表知识库宪法；SPEC 一词留给 workbench 项目规格（projects/<项目>/spec.md），不混用。

---

## 目录结构

```
~/qwiki/                          ← Hermes 知识库（git 管理）
├── INDEX.md                     ← 全局知识目录，一张平表（检索总入口）
├── ROUTING.md                   ← 检索链详细说明
├── SCHEMA.md                    ← 本文（宪法：目录结构+命名+纯度+卡片公约）
├── HISTORY.md                   ← 变更记录
├── personal/                    ← 个人笔记（qwiki note，随笔卡）
└── projects/<项目>/             ← 项目知识
    ├── <模块名>.md              ← 模块卡（八段模板）
    ├── spec.md                  ← 项目规格（workbench 产物，非卡片）
    └── references|design|archive/  ← 项目文档素材（自然淘汰，核心回填 INDEX）
    （AGENTS.md 在代码仓顶层 /mnt/data/<项目>/AGENTS.md，不在 qwiki 内——跨工具共享界面）
```

## INDEX 登记规则

- 新写入知识**必须**同步追加 INDEX 条目（检索链依赖 INDEX 命中，漏登记=检索不到）
- 旧 v2 文档按「自然淘汰」：日志/单次分析类不登记，核心模式/基线/调试文档登记
- 每会话写 qwiki ≤ 5 页

## 命名约定

- **目录名**：全小写 + 连字符（`hm6801`、`_toolkit`）
- **文件名**：全小写 + 连字符（`flash-timing-benchmark.md`）
- **项目内文件**：保留原有文件名不变（迁移时不动名字）

## 内容纯度标准

### 什么放 qwiki

- 已验证的技术知识、设计决策、bugfix 复盘
- 可复用的经验总结
- 外部资料解读

### 什么不放 qwiki

- 临时笔记、未验证的猜想
- 代码本身（代码在 repo 里，wiki 只存分析结论和设计文档）

### 冲突标注

新信息与已有内容矛盾时，**两边都记**，打 `contradictions` 标记：
```
> [!WARNING] contradictions
> 2026-06-20: 实测发现 VPU1 实际编码能力与旧文档矛盾（见 reviews/xxx.md）
```

## YAML 头公约（v1）

所有知识库文档（`projects/**/` 与 `personal/` 下的 .md）统一 YAML 头。排除：INDEX.md/ROUTING.md/SCHEMA.md/HISTORY.md（索引与宪法文件）、templates/（模板本身）、AGENTS.md（跨工具兼容，保持纯 markdown）、projects/<项目>/spec.md（workbench 项目规格，另立规矩）。

```yaml
---
title: <标题>                  # 必填：与正文 H1 一致
type: note|card|reference|design|change   # 必填：文档类型
date: <YYYY-MM-DD>             # 必填：创建日期
summary: <一句话总结>           # 推荐：INDEX 登记/explore 检索直接提取
tags: [<标签>]                 # 推荐：检索用
author: <作者>                 # 可选
version: <版本>                # 可选：change/design 用
status: draft|review|accepted|archived    # 可选：状态
related: [<相对路径>]          # 可选：相关文档
---
```

规则：
- **必填三项（title/type/date）是检索、登记、分类的生命线**，其余字段按文档类型自取（模板定位哲学：约束流程行为，不约束细节）
- **summary 单一真相源**：放 YAML；note 类型正文 `>` 引言行为其渲染副本（AI 生成时同步填，非手动维护）
- title 与正文 H1 一致，AI 生成时自动填，不手动双写
- 存量文档每次 touch 时顺手归位（不突击迁移）；新旧格式矛盾文件优先统一

## 卡片身份

**知识库的最小单元是卡片**。note 与 card 同一身份、不同形态：

| 形态 | type | 来源 | 正文结构 | 模板 |
|------|------|------|---------|------|
| 随笔卡 | note | personal/（个人） | 自由（背景/要点/结论为参考骨架） | templates/note.md |
| 模块卡 | card | projects/（项目） | 八段（模块边界…相关） | templates/card.md |

公共约定（所有卡片无条件遵守，类似基类）：
1. YAML 头：title/type/date 必填 + summary 真相源
2. 一句话总结（INDEX 登记直接提取）
3. `[[slug]]` 双链（见知识互联节）
4. 相关段（标题统一为 `## 相关`）

按需演进：随笔卡因知识互联需要（如成为枢纽）或内容优化需要（内容增长需结构化）扩展为模块卡——结构扩展，公约与链接不变。不设自动升级门槛。

reference/design/change 是项目文档（workbench 产物），是卡片的素材来源，不是卡片。

## 知识互联

卡片之间用 `[[slug]]` 双链互联（slug = 文件名去 .md，如 `[[workbench-spec]]`）：
- **链接只指向文档，不做内容级（锚点/章节）链接**
- 撞名消歧：`[[项目/slug]]`（如 `[[hm6502/aic8800-wifi-driver]]`）
- 可带说明：`[[slug]] — 引用说明`（相关段格式）
- 反链 = 全库搜索 `[[slug]]` 出现处（search_files），即"谁引用了我"
- 死链检测：sync 时扫描所有 `[[...]]` 目标，对照知识库文件表，报告悬空链接
- 网视图靠查询呈现（孤岛=零入链，枢纽=高入链），不做可视化

链接粒度与文档管理单元一致（文件级），升级（note→card）不动链接。

## 迁移规则

- **L2→L1**：只能升到 memory，**永远不允许写入 SOUL.md**
- **只进不出**：内容不删，只追加。过时内容加 `deprecated` 标记而非删除

> @see [[ROUTING.md]]
