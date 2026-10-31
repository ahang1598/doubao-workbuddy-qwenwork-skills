# Dashboard 多数据源配置


## 发行版前置条件

多源创建及多源切片器需要已包含对应能力的 CLI 发行版和配套服务端。旧 CLI 即使支持其他图表，也可能在本地报缺少 `table_name` 或不支持 `data_sources`；这是发行版能力不匹配，不应改成辅助表或单源来冒充原需求。已有组件仍可先只读查询。需要确认能力时，用下方创建模板的最小配置配合真实子命令的 `--dry-run` 检查本地校验；它不写入数据，也不能证明服务端支持或实际渲染成功。若本地拒绝，报告当前 CLI 版本及错误，停止受影响写入并请求更新发行版，不用 `--no-validate` 绕过。

同一 Base 内支持 `column/line/bar/scatter/combo/area/pie/ring/funnel/wordCloud/statistics/ranking/radar/slicer`。传 `data_sources`（至少 2 个不重复的数据表，无额外数量上限）即启用多源，不可混用顶层单源字段，也不需要提交内部 `enableMultiDataSource`。

配套 CLI 在多源创建和更新时均将来源内 `series[].rollup` 转为大写，更新不补创建默认值；本地拒绝相同 Base 写法与表名的重复来源、切片器来源携带 `series/count_all` 和范围外的 `backgroundOpacity`。省略 Base 与显式 Base 的同表判定、字段存在性、权限和跨源兼容性仍由服务端核对；本地校验通过不能替代服务端或页面验收。

## 字段结构

| 字段 | 类型 | 说明（更新语义见“创建与更新规则”） |
|------|------|------|
| `data_sources` | object[] | 来源数组 |
| `data_sources[].table_name` | string | 必填，当前 Base 的表名；不做全局表名反查，不用于换表 |
| `data_sources[].base_token` | string | 可选，省略时继承命令外层 `--base-token`；必须属于同一 Base，显式跨 Base 不支持 |
| `data_sources[].source_id` | string | 创建时建议省略；更新时使用 Get 返回的来源身份 |
| `data_sources[].series` / `count_all` | array / boolean | 不能同时提供；图表创建时可均省略，服务端默认统计记录总数 |
| `data_sources[].group_by` | object[] | 每源最多一个维度；必填规则见组件表 |
| `data_sources[].filter` | object | 可选筛选条件 |
| `data_sources[].alias` | string | 可选来源系列别名 |
| `multi_source` | object | 可选组件级配置 |

需要字段求和等才传 `series`，每源最多一个指标，各来源指标模式、rollup、分组数量须一致。

普通图表创建时省略 `group_by`，服务端为每张表独立选择默认类别字段，不生成空分组。柱状图优先单选，其次文本、人员、日期、多选、公式、引用；折线／面积／散点优先日期。需要确定横轴时显式提供 `group_by`；无可用默认字段时必须显式配置。

`multi_source.series_split` 默认 false（汇总），通常无需传；true 按来源拆分系列。它不是多数据源开关。

## 各组件的多源能力

| 组件 | 来源与组件级配置 |
|---|---|
| `column/line/bar/scatter/combo/area/pie/ring/funnel/wordCloud` | 每源记录数或唯一指标、分组和筛选；`multi_source.series_split` 控制汇总／拆系列 |
| `statistics` | 每源记录数或唯一指标；不允许分组或排序；格式用 `multi_source.number_format` 或原生格式，不能混用 |
| `ranking` | 每源恰好一个分组；`multi_source.limit_size` 为 1–500；排序只支持 `value` |
| `radar` | 每源必须一个分组，使用按记录聚合 |
| `slicer` | 每源恰好一个分组，禁止 `series/count_all`；展示和选择模式放在 `multi_source`，不放顶层 |

统一排序用 `multi_source.sort={type:group|value,order:asc|desc}`；不提供时各来源分组排序须一致。更新时 `alias:null` 清除别名，不通过改数组顺序改变身份。多源切片器的 `multi_source.displayMode/selectMode/order` 分别为 `dropdown|tiled`、`single|multiple`、`asc|desc`，创建缺省为 `tiled/multiple/asc`；其他组件不接受这三项。

## 创建与更新规则

Get 返回每源的 `source_id/base_token/table_name` 和生效配置。后续优先使用返回的 `source_id`，也可用唯一 `table_name`；两者同时提供必须定位同一来源。来源身份不按数组下标推测。

单源转多源使用 `+dashboard-block-update`，向同一组件提交至少两个来源的完整 `data_sources`，沿用创建时的字段和默认值。先 Get 读取原配置，需要保留原统计口径时，将原表的指标、分组和筛选显式放入对应来源；不要将原扁平字段与 `data_sources` 混传。转换保留组件 ID、名称、布局和未修改的样式，不需要删除或重建。只传 `multi_source` 不能开启多源。

已有多源更新 `data_sources` 是 **至少 1 项已有来源的补丁数组，不是整体替换**，无额外数量上限：

- 未列出的来源和未传字段保持不变；不能通过省略来源删除、通过顺序重排，或隐式新增来源／换表。多源转回单源不支持。
- `series/group_by` 数组整体替换；省略 `group_by` 保留原值，不重新选字段。显式传 `series` 或 `count_all:true` 切换该来源指标方式，均省略则保留原指标，不能套用创建默认计数规则。
- `filter` 对象替换全部条件；`filter:null` 清空；省略保留。表与字段须属于对应来源，各来源仍须符合指标、rollup 和维度一致性约束。
- `multi_source` 按字段更新，不替换来源数组；仅传 `{"multi_source":{"series_split":true}}`、排行榜的 `limit_size` 或切片器选择模式均不改其他来源。指标卡 `number_format` 按子字段合并。
- 切片器展示更新保留联动目标和已选条件；显式更新来源配置或改变单／多选模式会清空已选条件。
- 旧快照自定义来源 ID 可能在更新后归一为 `src_N`；继续操作时使用最新响应身份。

## 可复制模板

```bash
lark-cli base +dashboard-block-create \
  --base-token '<BASE_TOKEN>' --dashboard-id '<DASHBOARD_ID>' \
  --name '多数据源柱状图' --type column \
  --data-config '{"data_sources":[{"table_name":"数据表"},{"table_name":"数据表 副本"}]}'

lark-cli base +dashboard-block-get \
  --base-token '<BASE_TOKEN>' --dashboard-id '<DASHBOARD_ID>' \
  --block-id '<BLOCK_ID>'

# 仅改副本横轴，其余来源、指标和筛选保留
lark-cli base +dashboard-block-update \
  --base-token '<BASE_TOKEN>' --dashboard-id '<DASHBOARD_ID>' \
  --block-id '<BLOCK_ID>' \
  --data-config '{"data_sources":[{"table_name":"数据表 副本","group_by":[{"field_name":"文本","mode":"integrated"}]}]}'

# 单源转多源：提交完整目标，保留原表统计口径须显式填写
lark-cli base +dashboard-block-update \
  --base-token '<BASE_TOKEN>' --dashboard-id '<DASHBOARD_ID>' \
  --block-id '<SINGLE_SOURCE_BLOCK_ID>' \
  --data-config '{"data_sources":[{"table_name":"销售表","series":[{"field_name":"销售额","rollup":"SUM"}],"group_by":[{"field_name":"月份"}]},{"table_name":"预算表","series":[{"field_name":"预算额","rollup":"SUM"}],"group_by":[{"field_name":"月份"}]}],"multi_source":{"series_split":true}}'
```

## 使用限制与错误处理

来源配置或回读失败时，按错误消息中的来源身份定位数据表，检查表名、字段和访问权限。错误未明确来源时，不推断某张表异常。

`+dashboard-block-get-data` 读取计算结果，不提供独立的每源计算状态、结果归属或下钻接口。多源配置不支持跨 Base、组件复制、来源增删／重排，以及跨组件大类切换。同大类内的堆积、平滑等子形态使用 [同大类子形态切换](dashboard-style.md#同大类子形态切换) 的 `viewModel.chartKind`，不修改来源配置。

`--linkage` 使用更新请求外层的同源目标列表，不属于 `data_config`，不支持多源字段映射。修改多源配置时保留已有合法联动。

创建请求超时或返回网络错误时，先查询组件列表确认是否已创建，再决定是否重试，避免重复创建。批量创建同一仪表盘的组件须串行执行。
