# 图表计算结果

## 目录

- [对象与支持范围](#对象与支持范围)
- [命令与参数](#命令与参数)
- [返回结构总览](#返回结构总览)
- [协议字段说明](#协议字段说明)
- [alias 规则与读取方式](#alias-规则与读取方式)
- [如何正确解读返回值](#如何正确解读返回值)
- [各图表类型的协议细节](#各图表类型的协议细节)
- [返回边界与技术限制](#返回边界与技术限制)
- [参考](#参考)

## 对象与支持范围

用 `+dashboard-block-get-data` 获取仪表盘图表组件（block）的最终计算结果，即供 AI 消费的图表协议 JSON，而非 block 配置。需读取 `name`、`type`、`layout`、`data_config` 或所属 dashboard 时，先用 `+dashboard-block-get`。

文本组件（`text`）不产生可计算数据，不适用本协议。视图组件用[视图组件数据读取](dashboard-view.md#读取视图组件数据)获取记录，也不使用本协议。

### 支持的图表类型

| 类别 | 类型 |
|---|---|
| 二维图表（11 种） | 柱状图、条形图、折线图、饼图、环形图、面积图、组合图、散点图、漏斗图、雷达图、排行榜 |
| 特殊类型（3 种） | 词云、指标卡（statistics）、透视表（pivotTable） |

## 命令与参数

```bash
lark-cli base +dashboard-block-get-data \
  --base-token bascn***************CtadY \
  --block-id chtxxxxxxxx
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `--base-token <token>` | 是 | 标识目标多维表格的 Base Token |
| `--block-id <id>` | 是 | 目标图表组件的唯一 Block ID |
| `--format <fmt>` | 否 | 输出格式；遵循 CLI 全局输出格式规则 |
| `--dry-run` | 否 | 只预览 API 调用，不执行 |

命令不需要 `--dashboard-id`；`base_token + block_id` 即可定位图表结果。

### dry-run 用途

用以下命令校验 `base_token` / `block_id`、调试 agent 生成的命令，或在自动化测试中确认请求结构：

```bash
lark-cli base +dashboard-block-get-data \
  --base-token bascn_example_token \
  --block-id chtxxxxxxxx \
  --dry-run \
  --format pretty
```

可看到类似接口路径：

```text
GET /open-apis/base/v3/bases/bascn_example_token/dashboards/blocks/chtxxxxxxxx/data
```

## 返回结构总览

成功时输出标准 `{ok, identity, data}` 信封；`identity` 是本次调用实际使用的身份，`data` 是图表协议本体：

```json
{"ok":true,"identity":"user","data":{"dimensions":[],"measures":[],"main_data":[]}}
```

| 图表类型 | 一定有 | 可能有 |
|---|---|---|
| 二维图表、词云 | `dimensions`、`measures`、`main_data` | 无 |
| 指标卡 | `dimensions`、`measures`、`main_data` | `comparison_data`、`trend_data` |
| 透视表 | `dimensions`、`measures`、`sort`、`result_structure`、`main_data` | 无 |

透视表规则见[透视表（pivotTable）](#四透视表pivottable)。

## 协议字段说明

### 1) `dimensions`

维度定义数组；用它把主结果或趋势结果中的 `dim_*` key 还原为字段。

```json
[{"field_name":"状态","alias":"dim_54q25oCB"}]
```

| 字段 | 说明 |
|---|---|
| `field_name` | 维度字段显示名称 |
| `alias` | 在 `main_data` / `trend_data` 中使用的维度 key |

### 2) `measures`

指标定义数组；用它把 `me_*` key 还原为聚合指标。

```json
[{"field_name":"Count","aggregation":"count_all","alias":"me_Y291bnRfYWxsX0NvdW50"}]
```

| 字段 | 说明 |
|---|---|
| `field_name` | 被统计字段；`aggregation = count_all` 时固定为 `Count`，表示记录总数 |
| `aggregation` | 聚合方式，常见值：`count_all` / `count` / `sum` / `avg` / `min` / `max` |
| `alias` | 在 `main_data` / `comparison_data` / `trend_data` 中使用的指标 key |

例如，金额求和对应 `field_name = 金额`、`aggregation = sum`；记录总数对应 `field_name = Count`、`aggregation = count_all`。

### 3) `main_data`

主结果集。每行是一个对象，key 必须取自 `dimensions` / `measures` 声明的 `alias`，而非字段名。

```json
[{"dim_54q25oCB":{"value":"A"},"me_Y291bnRfYWxsX0NvdW50":{"value":3}}]
```

### 4) `comparison_data`

仅指标卡可能返回。两个值的固定顺序为：当前周期值、对比周期值。原始协议通常不直接给周期名称或日期区间文本；判断同比/环比及比较窗口时，读取组件配置或 UI 上下文。

### 5) `trend_data`

仅指标卡可能返回。它是时间序列，每行通常包含一个时间维度和一个指标值。

## alias 规则与读取方式

把 alias 当作结果表的列 ID，不当作人类可读字段名。

| 对象 | 常见生成规则 |
|---|---|
| 维度 | `dim_` + `base64(field_name)` |
| 指标 | `me_` + `base64(aggregation + "_" + field_name)` |

文中 `dim_xxx`、`me_xxx` 或短 alias 是简化值，不保证与真实值逐字符一致。始终按返回的 `dimensions` / `measures` 声明映射：先用 alias 找字段与聚合，再读数据值，不得猜测 alias。

必需协议字段缺失或 alias 映射失败时，判定核验失败；不得用空数组或零值代替后判为通过。

## 如何正确解读返回值

1. 读 `dimensions`，确认每个 `dim_*` alias 对应的字段。
2. 读 `measures`，确认每个 `me_*` alias 的字段和聚合方式。
3. 读 `main_data` / `comparison_data` / `trend_data`，将 alias 还原成字段和指标后再解释。

## 各图表类型的协议细节

### 一、二维图表

适用于柱状图、条形图、折线图、饼图、环形图、面积图、组合图、散点图、漏斗图、雷达图、排行榜。

| 项目 | 规则 |
|---|---|
| `dimensions` | 通常 `1~2` 个；不分组时通常 1 个，分组时通常 2 个 |
| `measures` | 指标定义数组 |
| `main_data` | 按维度组合展开；每行表示一个维度值或“主维度 + 分组维度”组合，每个 measure 是该组合的聚合结果 |
| 排行榜 | 复用相同协议，无专属字段；条数和顺序由 block 的 `limit_size` 与 `group_by[0].sort` 决定；保持服务端顺序，不得反转或重排 |

将结果视为聚合结果表。时间轴图通常以第一维为横轴、measure 为纵轴；饼图和环形图中每行通常对应一个扇区的分类与数值。结果用于排序、Top N、占比、分组对比和趋势分析，不是原始记录。

以下最小示例同时展示分组维度；无分组时省略第二个维度及对应值：

```json
{
  "dimensions":[
    {"field_name":"状态","alias":"dim_status"},
    {"field_name":"负责人","alias":"dim_owner"}
  ],
  "measures":[{"aggregation":"count_all","field_name":"Count","alias":"me_count"}],
  "main_data":[{"dim_status":{"value":"A"},"dim_owner":{"value":"B"},"me_count":{"value":2}}]
}
```

### 二、词云

词云沿用 `dimensions + measures + main_data`：`dimensions` 是被分词的来源字段；每行表示“一个拆分词 + 该词的聚合结果”；measure 的含义取决于聚合方式和指标字段。

结果不是原文列表，通常已结合图表过滤条件、时间范围和数据权限计算完成。用它做关键词排序、热点词解释、按词聚合分析和主题归纳，不得当作逐条文本记录。

### 三、指标卡（statistics）

指标卡返回主值，以及可选的同/环比和趋势结果。

| 字段 | 规则 |
|---|---|
| `measures` | 有且仅有一个指标 |
| `main_data` | 通常一行；表示卡片主值，如记录总数或字段聚合值；本身不带时间周期概念 |
| `comparison_data` | 可选；依次为当前周期值、对比周期值；表示周期内记录总数或字段聚合值 |
| `trend_data` | 可选；表示一段时间内的指标变化序列 |
| `dimensions` | 可能含同/环比日期字段、趋势日期字段，为趋势或比较提供语义，不作为主分组展示 |

`main_data` 与 `comparison_data[0]` 口径可能不同，不一定相等。例如主值为 `7`、当前周期值为 `6`。

同时指定同/环比和趋势时，`dimensions` 日期维度顺序固定：第一个是趋势日期维度，并作为 `trend_data` 的时间列；第二个是同/环比日期维度，只补充比较所用日期字段的语义。`comparison_data` 自身通常不携带日期字段。

```json
{
  "dimensions":[
    {"field_name":"日期","alias":"dim_date"},
    {"field_name":"日期2","alias":"dim_date2"}
  ],
  "measures":[{"aggregation":"count_all","field_name":"Count","alias":"me_count"}],
  "main_data":[{"me_count":{"value":7}}],
  "comparison_data":[{"me_count":{"value":6}},{"me_count":{"value":0}}],
  "trend_data":[{"dim_date":{"value":"2026-04-24"},"me_count":{"value":2}}]
}
```

此例中主值为 `7`，当前/对比周期值为 `6` / `0`；趋势在 `2026-04-24` 的值为 `2`。要说明“和上周比”或“和上月比”，读取组件配置或 UI 上下文。

### 四、透视表（pivotTable）

透视表使用独立二维聚合协议：`result_structure.rowAxis` 与 `columnAxis` 按顺序引用维度 alias；`sort` 引用同级维度或指标 alias；`main_data` 只含叶子格子，不混入行列小计。

透视表 alias 基于 Snapshot 的稳定 `field_key`，仍以 `dimensions` / `measures` 声明为准。

## 返回边界与技术限制

| 边界 | 处理 |
|---|---|
| 不返回 block 名称、类型、`layout`、`data_config`、所属 dashboard | 用 `+dashboard-block-get` 获取 |
| 返回图表聚合后的最终结果，而非原始表全量明细 | 按图表过滤、分组、聚合和时间窗口口径解释 |
| alias 只是协议 key | 用 `dimensions` / `measures` 还原 |
| `comparison_data` 不一定有周期标签 | 用组件配置或 UI 上下文精确判断比较窗口 |

## 参考

- `+dashboard-block-get`：获取 block 元数据
- [dashboard-chart-config.md](dashboard-chart-config.md)：`data_config` 结构和组件类型
