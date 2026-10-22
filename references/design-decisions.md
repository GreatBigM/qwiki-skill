# qwiki 设计决策（决策原因层）

> 决策原因层：**为什么这样**——理解需要时查。坑与排障在 `references/agent-hook.md`；批量修卡 playbook 在 `references/bulk-repair.md`；操作流程在 `SKILL.md`。一处定义、别处引用。

## 三件事与三个文件

- **`SKILL.md`** = 怎么做（九操作流程，实现 SCHEMA 目标态的方法）；**`SCHEMA.md`** = 做成什么样（知识库宪法：目录 / 命名 / 卡片公约 / 表达形态 / 知识互联）；**`CHANGELOG.md`** = 发生过什么。三者平级互补，不混装。

## SCHEMA 单一真相源

- **宪法唯一真相源在本 skill 根目录 `SCHEMA.md`**：随 skill 发布/安装；知识库内不放置实例（曾放置 = 第三层 copy——实例改动与 skill 快照漂移）。
- 宪法变更 = 改本文件 + bump 版本 + 发布；**无模板 ↔ 实例同步义务**（无实例可同步）。
- 新库 init 不生成 SCHEMA.md（知识库骨架 = INDEX + 卡片 + `resource/` 素材 + `scripts/` 脚本）；卡片公约由加载本 skill 时读取根目录 SCHEMA.md。

## 解耦声明（2026-08-02 定稿，v1.9.0；2026-10-22 补受体口径）

- **本 skill 与 AGENTS.md / codegraph 无关**：不生成 AGENTS.md、不依赖 codegraph 索引、references 不含 codegraph-quickstart.md。
- 代码检索由各工具自身能力承担（search_files/read_file 或工具内置代码索引）——qwiki 只管理知识库本体（`~/qwiki/`）。
- 检索引导由 hook 注入（inject.sh 每轮注入"先查知识库"），SOUL.md 无需声明检索链；**该层只对 hook 受体成立**——DSH 是 skill-only 受体，靠显式 `qwiki explore` 与文末「收尾自检」兜底。

## 投影为什么是「两处」而不是「三处」（v2.14.0）

- 旧口径要求 YAML `summary` / 正文 `>` 首行 / INDEX 总结列逐字相同；而按实际习惯，YAML `summary` 常写成多行长摘要（`>-` 块标量），同串在作者侧必然破约，检查器还会把 `>-` 读成字符串。
- 现在：`>` 首行 = 一句话结论（≤80，INDEX 投影唯一来源）；YAML `summary` = 长摘要（不参与投影）；INDEX 由 `scripts/qwiki-sync.py` 生成。**手写的第二份真相必然漂移**。

## 为什么操作流程不拆进 references（2026-10-22）

- `SKILL.md` 的职责就是**详述怎么做**；把九操作拆成 `references/ops-*.md` 只是为压体积，读的人还得多跳一层。**只拆不参与执行的内容**：坑 / 决策原因 / 分发说明 / 批量修复 playbook。
