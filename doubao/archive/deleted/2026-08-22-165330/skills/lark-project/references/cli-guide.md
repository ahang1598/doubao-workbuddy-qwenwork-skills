# CLI 使用指南

## 前置条件

运行环境需要 Node.js 18+。所有命令通过 `larkproject_cli_exce` 执行。

## 命令结构

```bash
larkproject_cli_exce <resource> <method> [flags] --format json
```

命令采用 `resource method` 两级结构。所有输出推荐使用 `--format json` 获取结构化数据。

## 全局 Flag

| Flag | 说明 |
|------|------|
| `--format json\|table\|ndjson` | 输出格式，默认 json |
| `--select <props>` | 选取输出属性，逗号分隔（支持 dot path，如 `name,owner.name`） |
| `--profile <name>` | 临时切换 profile |
| `--verbose` | 显示详细日志 |

## 参数传递

三种方式，优先级从高到低：

1. **Flag 模式**（推荐）：`--project-key PROJ --work-item-type-key story`
2. **--set 模式**（设置工作项字段）：`--set priority=1 --set name="任务标题"`，value 支持 JSON
3. **--params 模式**（完整 JSON）：`--params '{"project_key":"PROJ","work_item_type_key":"story"}'`

Flag 和 --set 会覆盖 --params 中的同名字段。

## 命令发现

CLI 的命令和参数会随版本更新。遇到不确定的命令或参数时，使用 `inspect` 获取最新信息：

```bash
larkproject_cli_exce inspect                    # 列出所有可用命令
larkproject_cli_exce inspect workitem.create    # 查看具体命令的参数 schema
```

## 输出处理

- 始终使用 `--format json` 获取结构化输出，方便解析
- 使用 `--select` 精简返回字段，如 `--select id,name,current_nodes.name`
- 命令返回错误时，JSON 中包含 `error` 和 `message` 字段
