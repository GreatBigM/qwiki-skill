# ~/qwiki/ 目录结构

```
~/qwiki/                          ← Hermes 知识库（git 管理）
├── INDEX.md                     ← 全局知识目录，一张平表
├── ROUTING.md                   ← 检索链详细说明
├── personal/                    ← 个人笔记（自由格式）
│   └── <主题>.md
└── projects/<项目>/             ← 项目知识（平铺）
    └── <模块名>.md
```

## 与代码仓的关系

```
代码仓 <代码路径>/
├── AGENTS.md                    ← 跨工具通用界面
└── .codegraph/                  ← 代码索引
```

## YAML 头公约（v1，2026-08-01 定稿）

所有知识库文档（`projects/**/` 与 `personal/` 下的 .md）统一 YAML 头。排除：INDEX.md/ROUTING.md（索引生成物）、templates/（模板本身）、AGENTS.md（跨工具兼容，保持纯 markdown）、spec.md（workbench 体系另立规矩）。

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
- **summary 单一真相源**：reference/card/design 放 YAML；note 类型用正文 `>` 引言行（轻量随笔不强制 YAML summary，避免双写）
- title 与正文 H1 一致，AI 生成时自动填，不手动双写
- 存量文档每次 touch 时顺手归位（不突击迁移）；新旧格式矛盾文件优先统一
