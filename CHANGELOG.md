# Changelog

本文件记录版本历史。版本号定义在 SKILL.md frontmatter 的 `version` 字段（单一真相源）。

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
