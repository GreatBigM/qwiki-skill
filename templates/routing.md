# 知识检索路由

> 检索链的完整说明。概要见 SOUL.md「知识体系」节。

## 检索链

收到用户消息后，按以下顺序检索：

1. **memory（L1）** — SOUL.md + memory，偏好/事实/身份，高频注入。命中直接答。
2. **INDEX.md（~/qwiki/INDEX.md）** — 全局知识目录，一张平表。语义匹配标题+总结，按需加载正文。
3. **知识文件（~/qwiki/projects/ 或 ~/qwiki/personal/）** — 项目卡片（八段模板）或个人笔记（自由格式）。
4. **AGENTS.md（代码仓顶层）** — 跨工具通用界面，按 § 按需加载。后备全景。
5. **codegraph query/callers** — 代码符号/调用链。codegraph 未安装时回落到 search_files + read_file。
6. **模型自身知识** — 内核/协议/语言内置知识。
7. **web_search** — 外部网络搜索。

## 降级路径

```
codegraph 可用 → codegraph query/callers
codegraph 不可用 → search_files + read_file（token 消耗较高）
```

## 自生长

落到 AGENTS.md 完成任务后：
- 任务中读了 3+ 文件且深入理解了模块结构 → 蒸馏知识写入 ~/qwiki/
- 更新 INDEX.md 追加条目
- `cd ~/qwiki && git commit`

> 知识生成是自发行为（干活副产品），无专门子命令；命令（import/migrate 等）只管理库的形态。migrate 是存量整理（历史知识升级为卡片），非知识生产。

## 知识腐化检测

sync 时自动执行：
- 遍历卡片「模块边界」中列出的文件路径
- codegraph query 验证文件是否仍在索引中
- 缺失 → INDEX 对应条目标记 ⚠️ 待验证，通知用户

> ⚠️ 腐化检测依赖卡片「模块边界」中的文件路径。已卡片化的项目参与检测；v2 references/design 文档（无模块边界路径）待 migrate 卡片化后纳入。

## 知识文件模板

### 项目卡片（八段）
模块边界 / 职责描述 / 架构设计 / 技术栈 / 代码规范 / 配置命令 / 模块间关系 / 相关卡片

详见 qwiki skill templates/card.md

### 个人笔记
自由格式。详见 qwiki skill templates/note.md
