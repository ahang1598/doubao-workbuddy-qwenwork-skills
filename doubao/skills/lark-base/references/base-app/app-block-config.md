# BaseApp Block 公共配置与兼容索引

本页只维护外层CLI协议；组件参数、业务规则、默认尺寸与示例分别由 [逐组件文件](app-component-selection.md) 维护。下列旧章节入口继续有效，不维护第二份组件规则。本文“组件协议”指当前CLI API元数据、公开规则与服务端校验。

## 类型映射

标准族column/bar/line/pie/ring/area/combo/scatter/funnel/wordCloud/radar，单值statistics；专属ranking/progress/countdown/slicer/button/pivotTable/view/image/nps；text；list的standard/grouped/collapsible/card/detail；comboLayout/tabs；AI为ai_chart。列表省略sub-type默认standard，11种标准图可用update --type原位互转，其它type及全部sub_type不可改。具体路由读 [索引](app-component-selection.md)。

## 外层请求字段

Create发送name/type、必要sub_type及data_config/ai_config/display_config/interaction_config/layout_config/structure_config。标准列表可省sub_type，其它列表类型显式发送；图表/text/view/ai_chart不得发送sub_type。普通Update至少name、一层配置或标准图互转的type，只发送显式字段；sub_type及非标准图换型不支持；AI Block 用 `--ai-config`，与 `--data-config` 二选一。

display/interaction/layout/structure使用名称制公开字段，可用各层clear_fields/reset_fields，拒绝null和未知字段；方法层多参数数组逐项展开，不能混入内部快照。独立custom_config/custom_info与display/interaction合计≤16 KiB，不接受保留键或非JSON。参数落点读 [页面API](app-page-api.md)。

### 布局输入与回读单位

`--layout-config.position` 写入使用 **48 列栅格**，不是回读像素；根组件整数 `x,y≥0`、`w,h≥1`、`x+w≤48`。例如标题写入 `{"position":{"x":0,"y":0,"w":48,"h":3},"size_mode":{"width":"fixed","height":"auto"}}`，原生回读可能是 `x=0,y=0,w=1494,h=78`。**不能把回读的1494/78原样写回**：会再次按栅格放大；只修宽度仍留下错误高度。需要换算时，确认本次回读为该原生比例后，横向除31.125、纵向除26，再按布局协议写入。

布局碰撞由 Builder SDK 约束；text 的 auto/固定模式仍按用户要求配置，Agent 不据回读像素手动计算后续组件避让。写后用完整 `+app-structure-get` 回读 rect、size_mode、parent/pane，核用户位置、尺寸和最终配置；只看名称/类型或写入成功不能代替验收。完整流程见 [布局步骤](../../scenes/app-mode/layout.md)。

## AI Block

独立读 [AI宿主](component-ai-chart.md) 和 [AI Block协议](../ai-block.md)；不套普通五层配置或旧aiBlock+data-config入口。

- 创建用 `+app-block-create --type ai_chart --ai-config '<JSON>'`；更新用 `+app-block-update --block-id --ai-config`。`--ai-config` 与 `--data-config` 互斥，同时提交会被拒绝。
- `ai_config` 承载 chart_type/sub_chart_type/engine/spec/data_sources；`data_config` 不承载 AI 配置，回读与验收只认 `ai_config`。
- `+app-get` 的 `ref` 是 `base_token -> table_name[]`；按 [ref 表名解析](app-commands.md#ref-表名解析)，在对应 Base 的完整 `+table-list` 中按真实表名唯一定位并保留表 ID，`data_sources[0]` 使用该 Base key 与真实 `table_name`。单 Base 仍须核对目标表，多 Base 同名须确定目标 Base；缺失或歧义停止该项。不存在 `ref.base_token` 字段，未关联 Base 或跨 Base 会被 Node codec 拒绝。
- 位置、尺寸走 `layout_config`（`+app-block-update --layout-config` 或 `+app-page-update --layout-config`），不存在 `--position`/`--size-mode`。
- `type/sub_type` 创建后不可修改；AI 与普通图表不可互转。

## 列表配置

读 [列表公共协议](component-list.md) 及本轮subtype文件，包含真实字段名、columns/fields、筛选、分组与更新。

## 创建示例

列表完整示例见 [列表创建](component-list.md#创建与字段)，图表数据示例见 [公共数据](app-data-common.md#标准-app-图表共享协议)；其它类型示例在对应文件。

### 列表详情与普通新增

读 [记录交互](component-list.md#记录详情新增与动作)。

### 表单与页面入口按钮

读 [按钮](component-button.md)，Form分享定位仍由既有Form场景处理。

## 更新语义

未传保持，不注入create默认或读后拼全量；数组/对象替换以类型协议为准，不能泛化为全量合并。标准data_sources完整有序替换、切base同时带源；pivot/nps/字段countdown显式view_name/filter互相替换。button.clear_action和image.reset_settings各自与对应配置互斥。当前列表page_buttons按名称增量更新，空数组保留，不清空。

### 清空主筛选

读 [清空与回读](app-data-common.md#清空与回读)，不把clear_fields放data_config或用null/空条件替代。

## 视图组件

读 [视图](component-view.md)；“表格视图/视图组件”指 view 的 grid 形态，不是 list/standard——用户点名即建 view，仅模糊说“表格/清单/列表”时默认 List 并在歧义时先澄清；get-data不支持view。

## 图表与富文本

### App 专属图表

分别读 [ranking](component-ranking.md)、[progress](component-progress.md)、[countdown](component-countdown.md)。

### 交互与展示组件

分别读 [slicer](component-slicer.md)、[button](component-button.md)、[pivot](component-pivot-table.md)、[image](component-image.md)、[nps](component-nps.md)。按钮/图片不支持get-data。

### 标准 App 图表与 statistics

读 [公共多源数据协议](app-data-common.md)、[标准图表](component-charts.md) 与 [statistics](component-statistics.md)。

### 富文本局部样式

读 [text](component-text.md)，正文与实际text_runs来自block-get，不使用get-data。

### 列表顶部页面按钮

读 [列表页面按钮](component-list.md#列表顶部页面按钮)，真实同App Page ID，不携带当前记录。

### 正式自定义配置

读 [页面API](app-page-api.md#普通组件尺寸与样式)；custom_info.openapi_及custom_config.layout为保留字段，实际布局按正式层读写。

### 页面整体布局

读 [页面API](app-page-api.md#页面整体布局) 与 [页面布局规则](../../scenes/app-mode/layout.md)。page-update布局处理根直接组件，block-update布局处理单组件，不能混用。写后独立get/structure核对实际位置与模式，不能用请求回显证明生效。
