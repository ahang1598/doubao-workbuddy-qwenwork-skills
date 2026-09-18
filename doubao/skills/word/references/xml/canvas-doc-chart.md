# 本地 Word XML：图表占位与数据规范

本页定义 `<chart/>` 占位语法和图表数据的声明式 JSON 结构。CLI 参数、执行顺序及回读流程见下方命令参考，本页不重复定义。

> 使用前须完整读取本页；未见末行「全文完」时，调整 offset 继续读取至该标记。

公共 XML 规则先读 [`canvas-doc-xml.md`](canvas-doc-xml.md)。图表读取、新建、数据替换、尺寸与删除见 [`canvas-doc-chart.md`](../cli/canvas-doc-chart.md)。

## 内容模型

图表数据和正文位置分开管理：

- 声明式 JSON 数据描述图表类型、分类、系列和展示属性；
- `<chart data-id="..."/>` 管理正文位置与尺寸；
- 不直接写内部 snapshot、token、series id、axis id 或 `reference_map`。

## XML 占位

```xml
<chart id="chart_record_id" data-id="opaque_data_id" width="432pt" height="252pt"/>
```

- 图表为 inline；纯图表段落可投影为顶层简写。
- 新建省略 `id`，使用 `chart_data_create` 返回的 `data-id`；更新保留 Fetch 返回的 `id` 和 `data-id`。
- `width` / `height` 只接受 `16pt..1584pt`。
- 图表固定为 inline，不支持浮动或 anchor，也不能含子节点。
- 图表 JSON 不写进 XML。

## 数据结构

```json
{
  "chart_type": "column",
  "chart_subtype": "clustered",
  "categories": ["Q1", "Q2"],
  "series": [{"name": "收入", "values": [120, 200]}],
  "presentation": {"title": "季度收入", "legend": "bottom", "data_labels": "outside"}
}
```

### 图表类型与子类型

| `chart_type` | `chart_subtype` |
|---|---|
| `column` / `bar` | `clustered`、`stacked`、`percent-stacked` |
| `line` | `linear`、`smooth` |
| `pie` | `pie`、`donut` |
| `radar` | `area`、`line`、`line-with-markers` |
| `combo` | 不传；series 的 `series_type` 取 `column` 或 `line`，`axis` 取 `primary` 或 `secondary` |

### 数据与展示属性

- categories 为 1..256 个，series 为 1..16 个；每个 series 的 values 数量等于 categories 数量。
- values 必须是有限 JSON number，绝对值不超过 `Number.MAX_SAFE_INTEGER`。
- pie 只允许一个 series、无负数且至少一个正数；radar 至少 3 个 categories。
- combo 为 2..16 个 series，且至少各有一个 column 和 line series。
- column/bar 的 `percent-stacked` 不允许某一分类下所有系列值均为 0。
- 单图最多 2048 个数据点，JSON 对象/数组嵌套深度最多 8；只接受已定义且适用于当前图表类型的字段。不要重复 JSON 对象键：JSON 文本输入会检测并拒绝重复键；这不表示分类标签或系列名称必须唯一。
- categories 文本最长 256、series name 最长 128、标题/副标题/坐标轴标题最长 512，均按 UTF-16 code unit 计；字符串不得为空白或包含控制字符。

### presentation

全部可选；更新时以 Fetch canonical 数据为底稿保留非目标字段。

| 字段 | 取值与适用范围 |
|---|---|
| `title` / `subtitle` | 非空白字符串，最长 512 UTF-16 code units |
| `title_style` / `subtitle_style` | 见下方文字样式；有样式时必须同时保留对应标题文本 |
| `legend` | `none\|top\|left\|right\|bottom`；默认 `bottom` |
| `legend_style` | 图例文字样式；`legend=none` 时禁止 |
| `data_labels` | 默认 `none`；column/bar：`none\|auto\|outside\|inside-middle\|inside\|inside-zero`；line/radar：`none\|auto\|center\|left\|right\|top\|down`；pie：`none\|auto\|outside\|inside`；combo：`none\|auto` |
| `data_label_style` | 数据标签文字样式；`data_labels=none` 时禁止 |
| `background_color` | 图表背景色，`#RRGGBB` |
| `border_color` | 图表边框色，`#RRGGBB`；`none` 表示无边框 |
| `default_text_style` | 图表默认文字 `{font_size?,color?}` |
| `color_theme` | 下列 Word 色板名，或 1..16 个 `#RRGGBB` 颜色；优先沿用 Fetch 返回值 |
| `hole_size` | 仅 donut；整数 `1..100`，单位 `%` |
| `sector_border_color` | 仅 pie/donut；全部扇区边框色，`#RRGGBB` |
| `sector_separation` | 仅 pie/donut；整数 `0..100`，单位 `%` |
| `start_angle` | 仅 pie/donut；`0\|45\|90\|135\|180\|225\|270\|315` |
| `axes` | 仅 column/bar/line/combo；可含 `category`、`primary_value`；`secondary_value` 仅允许存在 secondary series 的 combo |
| `radar_axes` | 仅 radar；除通用显示项外支持 `shape=polygon\|circle`、标签旋转/样式、网格线样式和值轴范围 |

文字样式可含 `font_size`（`10\|12\|14\|16\|18\|20\|24\|30\|36`）、`color=#RRGGBB`、
boolean `bold/italic/underline/strikethrough`。

`color_theme` 字符串只接受 `brandColorSeries`、`complementaryColorSeries`、`converseColorSeries`、
`primaryColorSeries`、`rainbowColorSeries` 及各自追加 `@v2` 的版本；单色系列只接受
`singleColorSeries-{B,D,G,O,R,W,Y}` 及对应的 `singleColorSeries-{B,D,G,O,R,W,Y}-@v2`。花括号表示
从集合中选择一个字母，不是实际值的一部分；不要自行构造其它 theme 名。

每个 `axes` 项可含 `visible`、`title`、`major_gridlines`、`major_gridlines_color=#RRGGBB`、
`major_gridlines_width=1\|2\|3`、`label_rotation=-90\|-45\|0\|45\|90`、`label_style`、
`title_style`；`primary_value/secondary_value` 还可含有限数 `min/max`，二者同时存在时 `min < max`。
`visible` 默认 true；`primary_value.major_gridlines` 默认 true，其余笛卡尔轴默认 false。pie 不接受 axes，
radar 不接受 Cartesian `axes`。隐藏标签或网格线时，不要继续携带对应样式。

### series 与 data point 样式

- column/bar series 支持 `fill_color`、`fill_opacity` 和逐系列 `data_labels/data_label_style`；
  `points[].fill_color` 可覆盖单个数据点。
- line/radar series 支持 `line_color`、`line_opacity`、`line_width=1|2|4|8`、
  `line_dash=solid|dotted|dashed`、`marker_color`、`marker_shape=circle|triangle|rect|diamond|square`、
  `marker_size=0|2|5|7|10|14` 及逐系列数据标签；`points[]` 可覆盖单点
  `fill_color/marker_shape/marker_size`。
- radar area 另支持 `area_fill_color=#RRGGBB` 和连续值 `area_fill_opacity=0..1`。
- pie/donut 使用唯一 series 的 `points[].fill_color/sector_separation` 覆盖单个扇区。
- combo 的 column series 复用填充与数据标签字段，line series 复用折线、marker 和数据标签字段；
  line series 还可设 `line_style=linear|smooth`。两类 series 不得混用字段。
- `fill_opacity/line_opacity` 只接受 `0|0.1|0.3|0.5|0.7|0.9|1`。`points` 长度必须与
  `values` 一致，未覆盖的位置写 `{}`；全空数组会规范化为缺席。

这些字段已有 Word 编辑或渲染能力，应优先用 `chart_data_replace`，不要仅因主题色、雷达形状/填充、
逐系列/逐点样式、圆环孔径、扇区边框/分离/起始角、图表边框、默认文字或副标题样式直接回退
OOXML。更新时必须以 Fetch 返回的完整 canonical 数据为底稿，只修改目标字段，避免覆盖其它已支持样式。

保存重开时，色板名可能物化为颜色数组，`hole_size` / `sector_separation` 可能按 OOXML 离散值规范化；
当前 `radar_axes.shape` 和副标题尚无完整 TTOffice 持久化闭环。用户要求最终文件交付时必须保存重开回读，
不能只凭当前会话的 `chart_data` 回读或渲染成功宣称这些字段已持久化。

===== 全文完 =====
