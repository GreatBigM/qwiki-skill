# qwiki-skill

AI 知识库管理技能（skill）—— 用九条命令管理你的跨工具知识库。

qwiki 让 AI 助理拥有一个 git 管理的知识库：项目知识卡片 + 个人笔记 + 全局索引，按需加载、可检索、可沉淀。跨工具兼容（Hermes / Claude Code / Codex / ZCode / pi），仓库根目录即 skill 本体，用一键脚本或手动复制安装。

## 安装

本 skill 支持多 agent 目标：Hermes / Claude Code / Codex / ZCode / pi。安装脚本自动探测本机已安装的 agent，让用户选择安装目标。pi 的事件驱动层由 `~/.pi/agent/extensions/qwiki-sediment.ts` 扩展承接（pi 无 hook 机制，扩展把同一标记协议接到 pi 事件模型，标记队列跨工具共享）。

```bash
# 方式 1：交互选择安装目标（推荐，先下载再执行以保留交互）
curl -fsSL https://gitee.com/GreatBigM/qwiki-skill/raw/main/install.sh -o /tmp/install.sh && bash /tmp/install.sh

# 方式 2：指定目标（非交互，含 ZCode）
curl -fsSL https://gitee.com/GreatBigM/qwiki-skill/raw/main/install.sh | bash -s -- --target hermes,claude,zcode

# 方式 3：安装到全部检测到的 agent
curl -fsSL https://gitee.com/GreatBigM/qwiki-skill/raw/main/install.sh | bash -s -- --all
```

> 脚本等价于手动复制（clone + cp），不经过安全扫描，可先审阅脚本内容再执行。
> 已安装时自动备份旧版到 `<tool 根>/skills-backup/<skill>.bak.<时间戳>`（**扫描根之外**——agent 按「含 SKILL.md 的目录」发现技能、不看目录名，备份留在 skills 目录内会被当成第二个同名技能加载），重跑即升级（含版本对比提示）。

## 安装（备选：手动复制）

> ⚠️ 注意：部分 agent 的 `skills install`（tap/URL 方式）对 qwiki 会触发安全扫描拦截——扫描器将
> 「hook 脚本」「curl | sh 安装命令」等判定为 dangerous（误报，qwiki 的 hook 仅做知识沉淀标记），
> 且 community 来源 + dangerous 判定不可用 --force 绕过。
> **请使用一键脚本或手动复制安装，不经过扫描。**

```bash
# 1. 克隆本仓库
git clone https://gitee.com/GreatBigM/qwiki-skill.git

# 2. 复制到目标工具的 skills 目录（不经过安全扫描）
mkdir -p ~/.hermes/skills/qwiki
cp qwiki-skill/SKILL.md ~/.hermes/skills/qwiki/
cp -r qwiki-skill/templates ~/.hermes/skills/qwiki/
cp -r qwiki-skill/references ~/.hermes/skills/qwiki/
cp -r qwiki-skill/scripts ~/.hermes/skills/qwiki/
# ZCode: cp -r 到 ~/.zcode/skills/qwiki/

# 3. 会话内 /reload-skills，或新开会话自动加载
```

## 安装（备选：tap 方式，会被安全扫描拦截）

```bash
# 配置 GitHub token 可避免匿名 API 限流（60 次/时 → 5000 次/时）
export GITHUB_TOKEN=<你的 GitHub personal access token>

# 以 Hermes 为例（其余 agent 的 skills install 同理，均可能触发扫描拦截）：
hermes skills tap add GreatBigM/qwiki-skill
hermes skills install qwiki
# 预期结果：扫描判定 dangerous → BLOCKED（AGENTS.md 引用误报），请改用上方手动复制
```

## 依赖

| 依赖 | 必需 | 用途 | 获取方式 |
|------|------|------|--------|
| Hermes / Claude Code / Codex 任一 | 是 | skill 运行环境 | 各工具官方渠道 |
| git | 是 | 知识库版本管理 | 系统自带 |
| python3 | 否 | hook 脚本（缺失时静默跳过，不阻塞主流程） | 系统自带 |

零外部 skill 依赖——hook 机制说明已内嵌（references/agent-hook.md，含各家注册表）。

> 依赖表只列已在用的三家；`install.sh` 以**目录探测**决定安装目标（`~/.zcode`、`~/.pi/agent` 等存在即会被选中），本机没有的工具不会被写入。

## 快速上手

```bash
qwiki init              # 初始化知识库（创建 ~/qwiki/ 骨架 + INDEX.md）
qwiki import <项目>     # 新项目入驻：AI 读 SDK → 建项目卡 → 登记 INDEX
qwiki migrate <项目>    # 老知识升级为卡片体系
qwiki note <标题>       # 随手笔记
qwiki explore [关键词]  # 知识检索
qwiki sync              # 日常同步（宪法同步检查 + 索引一致性 + 防腐化判定）
qwiki status            # 查看知识库状态
qwiki delete <项目>     # 项目退出
qwiki deinit            # 全局拆除
```

## 仓库结构

```
qwiki-skill/
├── README.md                        ← 本文件（仓库说明 + 安装方法）
├── install.sh                       ← 一键安装脚本（多 agent 目标）
├── CHANGELOG.md                     ← 版本历史
├── SKILL.md                         ← 操作手册（九操作路由 + 详细步骤，仓库根即 skill）
├── templates/                       ← index / card-aggregate / card-track / card-measurement / card-issue / card-design / note-general 七模板
├── references/                      ← agent-hook（hook 机制 + 各家注册表：Hermes/Claude/Codex/ZCode，pi 走扩展）
└── scripts/                         ← qwiki-check.py（库自检，11 项断言）+ publish-check.py（发布前脱敏）+ number-audit.py（数字口径）+ 四 hook 脚本 + hooks/pre-push（两项检查都跑）
```

## 模型（一张图）

知识库被抽象成**一个对象 × 三个面**：

```
                  入口（唯一，只带节点、不带边）
               ┌──────────  INDEX.md  ──────────┐
               │   一行 = 一个 slug（三列正投影） │
               └────────────────┬───────────────┘
                                │  slug（唯一的接缝）
         ┌──────────────────────┼──────────────────────┐
      [存档]                 [组织]                  [检索]
    目录 = 归档分片        卡片互链（三种边）        从 INDEX 命中
    personal/              独立卡 ⇄ 独立卡（直链）    → 读卡
    projects/<项目>/         ↕ 挂载边                → 沿边走（上行/直链/跨族）
    projects/common/       聚合卡（元知识，链最多）    → 素材按路径找（不进图）
    resource/ = 附件          ↕ 跨族边（聚合卡⇄聚合卡）
```

- **对象**：卡片（= 知识，最小单元）/ 素材 / 脚本 / INDEX / 目录。**卡片只有一种**——「聚合卡」不是子类型，而是**同一张卡在内容上的呈现**：谈对象的是独立卡，谈"若干卡如何聚合"（元知识）的是聚合卡；**没有声明字段，由内容推导**
- **三个面正交**：存档（目录管归属）／组织关系（双链 + 聚合卡管）／检索入口（INDEX 管），信息不复制
- **三种边**：挂载边（为连通，子卡 ⇄ 聚合卡）／直链（为语义）／跨族边（为跨线）
- **一个入口**：INDEX 是三个面的唯一入口（漏登记 = 不存在），但只带节点不带边

## 设计理念

- **检索链**：INDEX → 知识卡 → 沿双链走（上行到聚合卡看同类 / 直链找对偶卡 / 跨族边跨线），按需加载，不把整个知识库塞进上下文
- **目录只是归档分片**：「项目树」不构成层级、也不产生关系（三面的关系见上面那张图）
- **聚合卡按知识体量长出来**：小知识就是独立卡（散挂 INDEX 属正常）；一块知识**被拆着写**、且**写得出"整体的话 + 关于这批知识的话"**时才建聚合卡——只写得出"这里有几张卡"就是索引器形态，还不该建
- **跨工具**：知识库本体与工具无关，hook 事件驱动层多工具同构（归一化层收敛 payload 差异）
- **单目录部署**：无外部 skill 依赖，复制目录即用
- **git 管理**：所有写操作自动 commit，历史可回溯
- **纯文本**：Markdown 平铺，跨工具兼容
- **机械校验**：`scripts/qwiki-check.py` 11 项断言（卡片头部 / INDEX 正投影 / 纯度 / slug 唯一 / 检索双向可达 / 轨迹卡归属 / 素材…）

## 发布前检查（脱敏）

这个仓是公开的，`scripts/publish-check.py` 扫真实项目代号 / 内网 IP / MAC / 长 hash / 凭据 / 本机路径：

```bash
python3 scripts/publish-check.py          # 逐条判定，真实标识换 <项目A> / <IP> 占位符
python3 scripts/number-audit.py            # 实测数字须落在某条「口径（… YYYY-MM-DD）」的作用域内（同列表项子树 / 同段 / 同一引用块；空行切断归属）
git config core.hooksPath scripts/hooks   # 启用 pre-push 钩子（每个克隆各做一次）→ 命中即拒绝推送
```

**为什么是钩子而不是"记得手动跑"**：脱敏靠人记必然回潮——同一批标识在 v1.7.6 脱敏过一轮，之后三个版本又各自写回去。最隐蔽的泄漏面是模板里的「好坏例」：举例越真实越像好例。

**判据的单一真相源与重签**：`scripts/number-audit.py` 的 docstring 顶部有两行——
`CURRENT:`（判据本身，SKILL / README 里逐字引用它）与 `CURRENT_FP:`（语义核指纹）。
**改了语义核（`语义核 begin/end` 之间的正则与判定函数）必须跑 `python3 scripts/number-audit.py --seal` 重签**，
否则 `--parity` 直接拒——这条治的是"改了实现、忘了改描述"（本仓复发三次）。
指纹只能证明"改过并已显式重签"，**不能**证明"描述写对了"。

**怎么验指纹的覆盖面**（核内 = SCAN 扫描范围 + 正则 + 作用域/判定函数 + `audit()` 本体）：
改这三处任一，`--parity` 都应 rc=1——① `audit()` 里的口径豁免判据（`i in covered`）
② `SCAN` 列表 ③ `NUM` 单位表。核外只剩自指的 `semantics_fp / seal / parity / self_test / main`。

**评审补丁的交接形态**（2026-10-14 立，因一次誊写事故）：给补丁要**可直接执行 + 自带回归**——
把片段落成文件或有明确落点、附一条自检条目、并写明"先跑 `--self-test` 再看结果"。
反面教材：把正则当散文重打了一遍（`\s*` 写成 `\s`），照抄会让所有口径声明失效；
那次是**真库扫描当场暴露**（口径 = 2026-10-14 实测：0 条声明、48 处裸数字）才没流出去。
**另一条同类**：含反引号 / 中文标点的文本**不要走 shell heredoc**（会被当命令替换吞掉内容，
本仓踩过四次）——一律先写文件（Write）再执行。

**改了技能本体就要写 CHANGELOG**：`pre-push` 现在会比对本次推送改了哪些文件——
动了 `SKILL.md` / `SCHEMA.md` / `templates/` / `scripts/` 之一却没动 `CHANGELOG.md`，直接拒推。
（这条防的仍是"改了实现忘了记录"：本版曾一次性补记六笔漏条目。）

## License

MIT
