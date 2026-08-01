# Codegraph 快速上手（内嵌规范）

> 通用最小流程。qwiki 依赖 codegraph 做代码索引，
> 本文件覆盖安装 → 索引 → 查询 → 同步的完整闭环。不涉及 MCP 集成等环境特定配置。

## 安装

```bash
curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh
```

安装后确认：`which codegraph`。

## 初始化 + 索引

在源码树根目录（项目代码仓）执行：

```bash
cd <代码仓根目录>
codegraph init          # 生成 .codegraph/ 配置
# 编辑 .gitignore / codegraph.json：排除产物目录（build/out/工具链等），只索引源码
codegraph index         # 建立索引库 .codegraph/codegraph.db
```

> 只需源码树，无编译环境依赖。大仓（monorepo）务必配置排除规则后再 index，
> 否则索引体积和耗时失控（参考 codegraph-monorepo-exclusions 的思路：选择性纳入 + 产物排除）。

## 查询（CLI）

```bash
codegraph query <search> -p <代码仓> -j    # 模糊搜索符号/文件
codegraph callers <symbol> -p <代码仓> -j  # 查调用方（最可靠）
codegraph status <代码仓>                    # 索引状态
```

CLI 每次独立进程，读 `.codegraph/codegraph.db` 索引库，不依赖常驻服务。

> 反模式：用 grep/search_files 查符号而不先用 codegraph CLI——CLI 有索引，快得多且跨文件。
> 先 `codegraph query`，返回空或超时才 fallback 到 search_files。

## 同步

```bash
codegraph sync          # 增量更新索引（代码变更后执行）
```

> 索引被中断后必须 sync 收尾；大仓 sync 可能耗时数小时，期间查询返回 busy 是正常排队，
> 非错误，其他项目不受影响。

## 陷阱速查

1. **DB locked**：
   `python3 -c "import sqlite3; conn=sqlite3.connect('<代码仓>/.codegraph/codegraph.db', timeout=10); conn.execute('PRAGMA wal_checkpoint(TRUNCATE)'); conn.close()"`
2. **pkill 误杀 index 进程**：必须精确匹配 `"codegraph.*serve"`，不要 `pkill -f codegraph` 全杀。
3. **未安装 codegraph 时的降级**：检索链中 codegraph 环节回落到 search_files + read_file（token 消耗较高）。
