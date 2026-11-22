# 问答：能力说明与只读查询

本页处理能力/用法问答，以及定位应用、列页面与组件、查看配置或计算结果。需要修改见 [1-n 修改](modify.md)，从零搭建见 [0-1 搭建](create.md)；所需协议从 [AppMode 索引](../app-mode.md#协议索引) 按需打开。

## 目标

用最少的读取命令还原真实结构，结论带真实 token 与来源，不把猜测写成事实，也不因“先看看”创建或修复任何对象。

## 能力与用法问答

1. 先判断用户在问公开能力/使用方式，还是具体 App 的当前状态；前者只读命中协议或精确命令 help，无需定位 App 或调用 API。
2. 参数问题读 help，组件行为读对应组件，数量/布局规则读搭建规则，权限问题读应用权限；不为回答一个问题加载整套搭建流程。
3. 回答附依据与实际能力边界；不能由历史结果推定当前部署已支持。涉及当前资源状态时执行下方只读步骤。

## 硬约束

1. **零写操作**：不 create、update、delete、move 任何对象；不自动创建 App、Page、Base。
2. **无权限不等于无标题**：`+app-page-list` 返回的 Page `name` 为空表示当前用户对该页无权限，必须如实报告，且不要用其 `page_id` 继续读取或写入。
3. **unsupported 只认存在**：`type=unsupported` 的组件只能从列表识别，不调用 `get`、`get-data`、`update`。
4. **命名不等于命中**：名称相似不算定位成功，必须给出真实 `app_token`、`page_id`、`widget_id` 或 `chart_token`。
5. **读后要改则转层**：用户同时要求修改时，先完成只读定位并报告，再按 [1-n 迭代](modify.md) 重新读取现状后写入。

## 当前应用的查询步骤

### 第 1 步：解析入口

- `/app/` URL：`+url-resolve --url '<url>'`，使用真实返回的 `app_token` 及链接携带的 `workspace_token`、`page_id`。
- 只有 Workspace：`+workspace-entity-list --workspace-token <token> --type baseapp --page-size 30`，`has_more=true` 时继续分页。
- 只有标题：说明没有全局 `+app-list`，请用户给链接或 Workspace，不按名称猜 token。

### 第 2 步：读应用

`+app-get --app-token <app_token>`：取名称、主题、页面摘要与 `ref`。`ref` 的 key 是 `base_token`，值是已被组件引用的 Table 名称；未被引用的 Base 不会出现。

### 第 3 步：读页面与导航

- 需要页面组、父子关系、顺序：`+app-page-tree-list`。
- 只要页面目录：`+app-page-list`。
- 需要单个页面详情：`+app-page-get`。

### 第 4 步：读组件

- 摘要与类型：`+app-block-list --page-id <page_id> --page-size 100`。
- 单个组件完整配置：`+app-block-get`；只取详情字段可用 `--jq '.data.block.data_config'`，图表 token 用 `--jq '.data.block.chart_token'`。
- 完整导航、布局与容器层级：`+app-structure-get`。

只查摘要时不逐个 `get`，避免无意义放大读取量。

### 第 5 步：读计算结果

需要图表数值时用 `+app-block-get-data --app-token <app_token> --base-token <base_token> --block-id <chart_token>`。`--block-id` 必须传组件摘要里的 `chart_token`，`base_token` 普通图表取 `data_config.base_token`，`ai_chart` 取 `ai_config.data_sources[0].base_token`。text、list、view、button、容器不套图表取数；列表与视图的数据效果按真实引用读取来源。

### 第 6 步：汇报

输出结构固定，缺项写“未读取”，不省略：

- **应用**：名称、`app_token`、主题、页面数。
- **页面**：名称、`page_id`、所属组、顺序。
- **组件**：名称、`widget_id`、类型、所在 Page、绑定 Base/Table（如有）。
- **数据**：仅当用户问到指标时给数值与口径。
- **缺口**：无权限页、unsupported 组件、缺证据项分别列出，不合并成“正常”。

## 回读与边界

- 只读任务不补建、不删改，也不为满足默认页数或首页阈值补对象。
- 结论只引用本次真实读取结果；历史快照、记忆或名称推断不能当现状。
- 用户要求“顺便优化/补齐”时，明确分成只读结论与后续写任务，写任务按 [1-n 迭代](modify.md) 或 [0-1 搭建](create.md) 重新判断层级。
