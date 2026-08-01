# qwiki-skill

Hermes Agent 知识库管理技能（skill）—— 用九条命令管理你的二级知识库。

qwiki 让 AI 助理拥有一个 git 管理的知识库：项目知识卡片 + 个人笔记 + 全局索引，按需加载、可检索、可沉淀。本仓库以 [skills.sh](https://skills.sh) 标准布局分发（`skills/qwiki/`），克隆后手动复制到 skills 目录即可用。

## 安装（推荐：手动复制）

> ⚠️ 注意：`hermes skills install`（tap/URL 方式）对 qwiki 会触发安全扫描拦截——扫描器将
> 「引用 AGENTS.md」「curl | sh 安装命令」等判定为 dangerous（误报，qwiki 本质是管理
> AGENTS.md 的知识库 skill），且 community 来源 + dangerous 判定不可用 --force 绕过。
> **请使用手动复制安装，不经过扫描。**

```bash
# 1. 克隆本仓库
git clone https://github.com/GreatBigM/qwiki-skill.git

# 2. 复制到 Hermes 的 skills 目录（不经过安全扫描）
cp -r qwiki-skill/skills/qwiki ~/.hermes/skills/qwiki

# 3. 会话内 /reload-skills，或新开会话自动加载
```

## 安装（备选：tap 方式，会被安全扫描拦截）

```bash
# 配置 GitHub token 可避免匿名 API 限流（60 次/时 → 5000 次/时）
export GITHUB_TOKEN=<你的 GitHub personal access token>

hermes skills tap add GreatBigM/qwiki-skill
hermes skills install qwiki
# 预期结果：扫描判定 dangerous → BLOCKED（AGENTS.md 引用误报），请改用上方手动复制
```

## 依赖

| 依赖 | 必需 | 用途 | 获取方式 |
|------|------|------|---------|
| Hermes Agent | 是 | skill 运行环境 | https://hermes-agent.nousresearch.com/docs |
| git | 是 | 知识库版本管理 | 系统自带 |
| codegraph | 否 | 代码索引（可选增强，缺失时回落 search_files） | 见 SKILL.md 安装命令 |

零外部 skill 依赖 —— 本仓库已内嵌 AGENTS.md 章节规范（references/agents-md-structure.md）和 codegraph 快速上手（references/codegraph-quickstart.md）。

## 快速上手

```bash
qwiki init              # 初始化知识库（创建 ~/qwiki/ + INDEX.md + ROUTING.md）
qwiki import <项目>     # 新项目入驻：AI 读 SDK → 建 AGENTS.md → 登记 INDEX
qwiki migrate <项目>    # 老知识升级为卡片体系
qwiki note <标题>       # 随手笔记
qwiki explore [关键词]  # 知识检索
qwiki sync              # 日常同步（codegraph sync + 索引一致性 + 腐化检测）
qwiki status            # 查看知识库状态
qwiki delete <项目>     # 项目退出
qwiki deinit            # 全局拆除
```

## 仓库结构

```
qwiki-skill/
├── README.md                        ← 本文件（仓库说明 + 安装方法）
└── skills/qwiki/                    ← skill 本体（tap 安装源）
    ├── SKILL.md                     ← 操作手册（九操作路由 + 详细步骤）
    ├── templates/                   ← index / routing / card / note 四模板
    └── references/                  ← spec / agents-md-structure / codegraph-quickstart
```

## 设计理念

- **检索链**：memory → INDEX → 知识文件 → AGENTS.md → codegraph → web_search，按需加载，不把整个知识库塞进上下文
- **单目录部署**：无外部 skill 依赖，复制目录即用
- **git 管理**：所有写操作自动 commit，历史可回溯
- **纯文本**：Markdown 平铺，跨工具兼容

## License

MIT
