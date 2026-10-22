# qwiki-skill

AI 知识库管理技能（skill）—— 用九条命令管理你的跨工具知识库。

qwiki 让 AI 助理拥有一个 git 管理的知识库：项目知识卡片 + 个人笔记 + 全局索引，按需加载、可检索、可沉淀。跨工具兼容（Hermes / Claude Code / DeepSeek Harness / Codex / ZCode / pi），仓库根目录即 skill 本体，用一键脚本或手动复制安装。Codex / ZCode / pi 条目为**分发兼容说明**——**本机受体现状见下方「安装」节注记**。

## 安装

本 skill 支持多 agent 目标：Hermes / Claude Code / DeepSeek Harness（DSH）/ Codex / ZCode / pi。安装脚本自动探测本机已安装的 agent，让用户选择安装目标。DSH 是 skill-only 受体——技能根 `~/.dsh/skills`，目录包写盘即热更新（免重启），`--target dsh` 只装 skill 本体、不落 hook 脚本（DSH 无 hooks 配置面）。pi 的事件驱动层由 `~/.pi/agent/extensions/qwiki-sediment.ts` 扩展承接（pi 无 hook 机制，扩展把同一标记协议接到 pi 事件模型，标记队列跨工具共享）。

> **受体现状（2026-10-22）**：本机现行受体 = **Hermes + Claude + DeepSeek Harness（DSH）**；`codex` 未安装 / `pi` 未安装 / ZCode 已卸载。DSH 是 **skill-only 受体**：装 `~/.dsh/skills/qwiki`，无 hook 配置面（扩展面是 cordis 插件），事件驱动层不注册。下文 Codex / ZCode / pi 相关条目**保留为分发兼容说明**——`install.sh` 按目录探测自动跳过不存在的受体，未装即不会被写入。

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
cp qwiki-skill/SCHEMA.md ~/.hermes/skills/qwiki/     # 宪法：SKILL.md 全程引用它，不可省
cp qwiki-skill/CHANGELOG.md ~/.hermes/skills/qwiki/
cp -r qwiki-skill/templates ~/.hermes/skills/qwiki/
cp -r qwiki-skill/references ~/.hermes/skills/qwiki/
cp -r qwiki-skill/scripts ~/.hermes/skills/qwiki/
# ZCode: cp -r 到 ~/.zcode/skills/qwiki/

# 3. 会话内 /reload-skills，或新开会话自动加载
```

## 安装（备选：tap 方式，会被安全扫描拦截）

```bash
# 配置 GitHub token 可大幅提高 API 限额（匿名限额很低，具体见 GitHub 文档）
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
| DeepSeek Harness（dsh） | 是 | skill 运行环境 | 本机 `~/.local/bin/dsh`（npm 包 `@deepseek-ai/dsh`） |
| git | 是 | 知识库版本管理 | 系统自带 |
| python3 | 否 | hook 脚本（缺失时静默跳过，不阻塞主流程） | 系统自带 |

零外部 skill 依赖——hook 机制说明已内嵌（references/agent-hook.md，含各家注册表）。

> 依赖表只列已在用的四家；`install.sh` 以**目录探测**决定安装目标（`~/.zcode`、`~/.pi/agent` 等存在即会被选中），本机没有的工具不会被写入（本机现无 codex / ZCode / pi——受体现状见上文「安装」节注记）。

## 快速上手

```bash
qwiki init              # 初始化知识库（创建 ~/qwiki/ 骨架 + INDEX.md）
qwiki import <项目>     # 新项目入驻：AI 读 SDK → 建项目卡 → 登记 INDEX
qwiki migrate <来源> [目标]  # 非当前版本知识入迁（旧库 / 笔记 / 项目 resource）
qwiki note <标题>       # 随手笔记
qwiki explore [关键词]  # 知识检索
qwiki sync              # 日常同步（一致性校验 + 防腐化 + 结构审视）
qwiki status            # 查看知识库状态
qwiki delete <项目>     # 项目退出
qwiki deinit            # 全局拆除
```

## 仓库结构

```
qwiki-skill/
├── README.md / install.sh / CHANGELOG.md   ← 仓库说明 / 安装 / 版本历史
├── SKILL.md                                ← 操作手册（九操作路由 + 详细步骤，仓库根即 skill）
├── SCHEMA.md                               ← 宪法（知识库目标态的唯一真相源，随安装拷贝）
├── templates/                              ← 卡片模板
├── references/                             ← 决策原因 / hook 机制 / 批量修卡 playbook
└── scripts/                                ← 库自检 / 投影生成 / 发布闸门 / hook 脚本
```

> 支持文件逐个清单见 `SKILL.md` 末尾「支持文件清单」（单一真相源，本文件不复述）。

## 模型（一张图）

知识库被抽象成**一个对象 × 三个面**：

```
                  入口（唯一，只带节点、不带边）
               ┌──────────  INDEX.md  ──────────┐
               │   一行 = 一个 slug（四列正投影） │
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

- **实体**：卡片（= 知识，最小单元）/ 素材 / 脚本 / INDEX / 目录。**卡片只有一种**——「聚合卡」不是子类型，而是**同一张卡在内容上的呈现**：谈对象的是独立卡，谈"若干卡如何聚合"（元知识）的是聚合卡；**没有声明字段，由内容推导**
- **三个面正交**：存档（目录管归属）／组织关系（双链 + 聚合卡管）／检索入口（INDEX 管），信息不复制
- **三种边**：挂载边（为连通，子卡 ⇄ 聚合卡）／直链（为语义）／跨族边（为跨线）
- **一个入口**：INDEX 是三个面的唯一入口（漏登记 = 不存在），但只带节点不带边

## 设计理念

- **检索链**：检索只做定位（`scripts/qwiki-search.py`：标签 → 简介 → 正文三级信号），**读卡才是取知识**（只读 1–2 张）→ 再沿双链走（上行到聚合卡看同类 / 直链找对偶卡 / 跨族边跨线）；不把整个知识库塞进上下文
- **目录只是归档分片**：「项目树」不构成层级、也不产生关系（三面的关系见上面那张图）
- **聚合卡按知识体量长出来**：小知识就是独立卡（散挂 INDEX 属正常）；一块知识**被拆着写**、且**写得出"整体的话 + 关于这批知识的话"**时才建聚合卡——只写得出"这里有几张卡"就是索引器形态，还不该建
- **跨工具**：知识库本体与工具无关，hook 事件驱动层多工具同构（归一化层收敛 payload 差异）
- **单目录部署**：无外部 skill 依赖，复制目录即用
- **git 管理**：所有写操作自动 commit，历史可回溯
- **纯文本**：Markdown 平铺，跨工具兼容
- **机械体检**：`scripts/qwiki-check.py` 分两栏——**INDEX 入口**（死链 / 漏登记 / 表体断裂，坏了就是「找不到」，退出码 1）与**规格**（卡片头部 / 投影 / 命名 / 双链…，只记账不报红）

## 发布前检查（脱敏）

这个仓是公开的，`scripts/publish-check.py` 扫真实项目代号 / 内网 IP / MAC / 长 hash / 凭据 / 本机路径：

```bash
python3 scripts/qwiki-tests.py             # 核心测试：check / sync 的守卫边界（改过脚本必跑）
python3 scripts/publish-check.py          # 逐条判定，真实标识换 <项目A> / <IP> 占位符
python3 scripts/number-audit.py            # 宪法与对外文档不得含实测数字（判据原文见其 docstring 的 CURRENT: 行）
git config core.hooksPath scripts/hooks   # 启用 pre-push 钩子（每个克隆各做一次）→ 命中即拒绝推送
```

**为什么是钩子而不是"记得手动跑"**：脱敏靠人记必然回潮——同一批标识在 v1.7.6 脱敏过一轮，之后三个版本又各自写回去。最隐蔽的泄漏面是模板里的「好坏例」：举例越真实越像好例。

**服务端也有一份**：`.github/workflows/gates.yml` 在 push / PR 上跑同一批闸门（核心测试 / 脱敏自检 / 脱敏 / 数字审计）。`pre-push` 只在你本机推时生效——换台机器、网页端改文件、别人提 PR，都不会经过它。

**判据的单一真相源**：`scripts/number-audit.py` 的 docstring 顶部 `CURRENT:` 一行写着这条规则本身，实现与它对齐。
> 曾有过「语义核指纹 + `--seal` 重签 + `--parity` 描述同步」一整套机制，2.12.3 退役：它只能证明"改过并已显式重签"，**不能**证明"描述写对了"；而判据收成一句话之后，同步的义务本来就不存在了。

**评审补丁的交接形态**（2026-10-14 立，因一次誊写事故）：给补丁要**可直接执行 + 自带回归**——
把片段落成文件或有明确落点、附一条自检条目、并写明"先跑 `--self-test` 再看结果"。
反面教材：把正则当散文重打了一遍（`\s*` 写成 `\s`），照抄会让整条判据失效——那次是**真库扫描当场暴露**才没流出去。
**另一条同类**：含反引号 / 中文标点的文本**不要走 shell heredoc**（会被当命令替换吞掉内容，
本仓踩过四次）——一律先写文件（Write）再执行。

**改了技能本体就要写 CHANGELOG**：`pre-push` 现在会比对本次推送改了哪些文件——
动了 `SKILL.md` / `SCHEMA.md` / `install.sh` / `templates/` / `references/` / `scripts/` 之一却没动 `CHANGELOG.md`，直接拒推。
（这条防的仍是"改了实现忘了记录"：本版曾一次性补记六笔漏条目。）

## License

MIT
