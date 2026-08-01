# qwiki skill 操作参考

> 知识库宪法见 `~/qwiki/SCHEMA.md`（目录结构/命名/纯度/卡片公约：YAML 头、卡片身份、知识互联）——公约真相源在知识库内，本文件不重复定义。本文是 skill 操作视角的速览。

## ~/qwiki/ 目录结构（速览）

```
~/qwiki/
├── INDEX.md                     ← 全局知识目录，一张平表（检索总入口）
├── ROUTING.md                   ← 检索链详细说明
├── SCHEMA.md                    ← 宪法（目录结构/命名/纯度/卡片公约）
├── HISTORY.md                   ← 变更记录
├── personal/                    ← 随笔卡（qwiki note）
└── projects/<项目>/             ← 模块卡 + references/design/archive（素材）
```

## 与代码仓的关系

```
代码仓 <代码路径>/
├── AGENTS.md                    ← 跨工具通用界面
└── .codegraph/                  ← 代码索引
```

> 卡片公约（YAML 头必填三项、卡片身份、`[[slug]]` 双链、死链检测）完整定义见知识库内 `~/qwiki/SCHEMA.md`。
