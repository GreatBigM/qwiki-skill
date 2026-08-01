# Changelog

本文件记录版本历史。版本号定义在 SKILL.md frontmatter 的 `version` 字段（单一真相源）。

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
