# 视图组件配置与读取

## 对象与入口

`+dashboard-block-create --type view` 创建明细、列表或时间安排。组件属 Dashboard，以 `base_token + dashboard_id + block_id` 管理。业务配置写 `data_config`；外层 `type:view` 是组件类型，`view_type` 是展示类型。
筛选、分组、排序、可见字段与视图引用分别处理。

## 创建输入

| 键 | 规则 |
|---|---|
| `table_name` | 必填非空 |
| `view_type` | 必填非空；如 `grid`、`gantt`、`gallery` |
| `filter` | 可选；仪表盘 `conjunction + conditions[]` 对象协议，见 [Dashboard Block 配置](dashboard-chart-config.md) |
| `group_by` | 可选数组；每项含非空 `field_name`，可含 `mode`、`sort:{type,order}` |
| `sort_by` | 可选数组；每项含非空 `field_name`、`order:asc/desc`；保序 |
| `visible_fields` | 可选字段名数组；保序 |

## 创建与更新的约束

- 创建/更新拒绝 `data_config` 顶层 `timebar`、`card`；值为 `{}`/`null` 也报参数错误。读取仍原样输出已有配置；独立数据表视图配置命令不受影响。
- 无需 `series`、`count_all`，拒绝图表指标配置。
- `filter` 沿用仪表盘校验：1～50 条条件，数组值最多 200 项；按真实字段类型填值，不转 `+view-set-filter` tuple 协议。
- `group_by` 将 `mode`、`sort.type/order` 转小写；`sort.type=group/view` 且无 `order` 时补 `asc`。
- CLI 不套用普通图表的两个分组维度上限，也不把数据表视图接口的类型限制或数量上限当作组件限制。
- 以下由服务端校验：`view_type` 支持范围，表和字段解析，展示类型与分组模式枚举，各配置对不同视图类型的适用性。

## 创建示例

### 表格视图

把真实表名、字段保存为 `view.json`：
```json
{"table_name":"任务表","view_type":"grid","filter":{"conjunction":"and","conditions":[{"field_name":"状态","operator":"is","value":"进行中"}]},
"group_by":[{"field_name":"状态","mode":"integrated","sort":{"type":"group","order":"asc"}}],"sort_by":[{"field_name":"截止时间","order":"asc"}],"visible_fields":["任务名称","状态","负责人","截止时间"]}
```
```bash
lark-cli base +dashboard-block-create --base-token BASE_TOKEN --dashboard-id DASHBOARD_ID \
  --name "进行中的任务" --type view --data-config @view.json
```
`--position '{"x":<x>,"y":<y>,"w":<w>,"h":<h>}'`（坐标按视觉规范的组件清单和尺寸表定）指定与 `data_config` 平级的布局属性。

### 甘特图

`{"table_name":"任务表","view_type":"gantt"}`

### 画册

`{"table_name":"任务表","view_type":"gallery"}`

甘特图和画册示例只指定展示类型，不配置起止时间或封面；有效配置由服务端校验。

## 更新

只提交变动的 `data_config`；无需外层 `type`，只改排序时无需重传 `table_name`、`view_type`：
```bash
lark-cli base +dashboard-block-update --base-token BASE_TOKEN --dashboard-id DASHBOARD_ID \
  --block-id BLOCK_ID --data-config '{"sort_by":[{"field_name":"截止时间","order":"desc"}]}'
```
- CLI 解析 JSON 对象，检查 `timebar/card`、规范化分组；局部更新不套创建必填项。
- 保留空数组和 `filter:null`；服务端决定其清空、嵌套合并及换表/展示类型后的旧配置处理。
- 修改受支持的嵌套配置须提交完整子对象；换表/展示类型须提交目标类型支持的完整配置。
- 只提交待改的可写字段，不回传 GET 结果。旧 `timebar/card` 只核对，不带回，也不传 `null` 清除。

## 返回结构与配置回读

创建、更新响应在 `data.block` 返回。GET 的 `data.block.data_config` 返回 `tableId / viewId / viewType` 等引用；不得假定原样返回 `table_name / view_type / filter / sort_by` 等输入。

用引用 ID 对应的 `+view-get-filter/sort/group/visible-fields/timebar/card` 回读持久化业务配置。

## 读取视图组件数据

```bash
lark-cli base +dashboard-block-get --base-token BASE_TOKEN --dashboard-id DASHBOARD_ID --block-id BLOCK_ID
```
`data.block.data_config` 的引用使用 camelCase：
```json
{"tableId":"tbl_example","viewId":"vew_example","viewType":1}
```
`tableId`、`viewId` 必须来自目标组件，不用 `block_id` 或默认视图代替。存量响应中 `tableId` 若是只含一个 ID 的数组，取该值；`viewId` 若是数字，转成字符串。

```bash
lark-cli base +record-list --base-token BASE_TOKEN --table-id tbl_example --view-id vew_example \
  --format ndjson --output ./records.ndjson
```
- 使用组件的 `base_token`。默认省略 `--filter-json`、`--sort-json`、`--field-id`，继承筛选、排序、可见字段；接口还补时间轴、封面、分组所需字段。用户要求额外条件或字段时再显式传入，对应部分会覆盖视图配置。
- 返回视图内记录，不模拟页面布局、分组折叠、仪表盘全局筛选或点击联动。
- 按 stdout 摘要及 manifest 的 `has_more` 判完整性。需要全量且 `has_more=true` 时，用 manifest 的 `next_offset` 作下次 `--offset`，写入另一个 artifact。完整读取见 [Record 分页协议](record-read.md#解析返回与完整分页)。
- 视图不存在或不可访问的报错不表示空数据，按 [视图读取失败恢复](#视图读取失败恢复) 处理。
`+dashboard-block-get-data` 只用于图表计算结果；视图组件走上述记录查询。

## 校验与透传选项

- `--no-validate` 跳过本地语义校验、规范化（含 `timebar/card` 检查），仍须合法 JSON 对象。透传不代表服务端支持，不得作为参数报错后的默认重试。
- 内联 JSON、`@file`、dry-run、执行共用同一解析结果。
- `--dry-run` 只验证请求，不证明服务端已部署。

## 视图读取失败恢复

引用缺失或表引用不唯一时，不能构造唯一记录请求；先核对组件详情，不猜数据源。视图不存在或不可访问时，报告读取失败并核对引用、权限；不得去掉 `--view-id` 退回整表，不得把失败当空数据。
