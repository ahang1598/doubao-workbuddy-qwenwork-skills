# 图表配置参考（chart widgets reference）

> 图表 config 的**唯一事实源**是 `dws aitable chart widgets-example --format json`。
> 本文覆盖仪表盘高频图表类型；用户要用的类型本文没有时，先跑上面命令取完整模板再填。

## 1. 公共结构

所有数据类图表 config 都含这些 key（`//` 说明，实际传纯 JSON）：

```jsonc
{
  "chartType": "<图表类型>",        // 必填，必须与模板一致
  "name": "<图表名称>",             // 必填，看板上的卡片标题，见名知意
  "sheet": "<tableId>",             // 必填，真实 tableId（AI 表格里叫 sheet）
  "view": null,                     // 可选 viewId，不用传 null
  "filter": [],                     // 无筛选传空数组；格式见 §5
  "measureType": "field",           // "field"=对字段聚合 | "record-count"=记录总数
  "measure": [                      // measureType=field 时必填；record-count 时省略/忽略
    { "value": "<fieldId>",
      "externalValue": [ { "type": "formula", "value": "sum" } ] }
  ],
  "dimension": [ { "value": "<fieldId>", "externalValue": [] } ],  // X 轴/分组维度
  "group": [ { "value": "<fieldId>" } ],                           // 第二维度(堆叠/分组图用)
  "colors": "COLOR_PALETTE_1"       // 配色，默认色板即可
}
```

### 聚合函数（formula 合法值）

| 值 | 含义 |
|---|---|
| `sum` | 求和 |
| `count` | 计数 |
| `unique-count` | 去重计数 |
| `average` | 平均值 |
| `max` / `min` | 最大 / 最小 |

### measureType 二选一

- `"record-count"`：统计记录总数，**无需 measure**。
- `"field"`：对某字段聚合，measure 指定 fieldId + formula。

## 2. 选型规则表

| 数据形态 / 分析意图 | 推荐 chartType | 说明 |
|---|---|---|
| 单一核心指标（总额/总数/均值） | `STATISTICS`（指标卡）或 `SUMMARY`（统计数字） | STATISTICS 支持环比 trend，优先用；一排 2~4 张 |
| 日期维度 × 数值（趋势） | `LINE` | 平滑可选 smooth:true；面积感用 `AREA` |
| 分类 × 数值（对比） | `HISTOGRAM`（柱状）；分类名长用 `BAR`（条形） | 分类 >8 个改用 `LEADERBOARD` |
| 两维分类 × 数值（分组对比） | `STACKED_HISTOGRAM` / `STACKED_BAR` | group 传第二维度 |
| 占比/构成 | `PIE`（分类 ≤7）；`PERCENT_STACKED_HISTOGRAM`（构成随时间变化） | 玫瑰图用 `ROSE` |
| Top N 排名 | `LEADERBOARD` | showCount 控制条数，sortRule:"desc" |
| 漏斗环节转化 | `FUNNEL` | dimension 为有序环节字段 |
| 文本高频词 | `WORD_CLOUD` | dimension 传文本字段 |
| 两数值相关性 | `SCATTER` | — |
| 多维能力对比 | `RADAR` | — |
| 原始明细浏览 | `GRID_VIEW` | 表格视图卡片 |
| 全局筛选交互 | `SLICER` | 可选，联动其他图表 |

**典型看板骨架**（4~8 张）：第 1 行 STATISTICS × 3~4（w=3）→ 第 2 行 LINE 趋势（w=12）→ 第 3 行 HISTOGRAM + PIE 并排（各 w=6）→ 第 4 行 LEADERBOARD（w=6）+ GRID_VIEW 明细（w=6）或 LEADERBOARD 通栏。

## 3. 常用模板

以下模板中 `<tableId>`/`<fieldId>` 替换为真实 ID；未列出的可选样式 key 可按 widgets-example 补，不传则用默认。

### STATISTICS 指标卡

```json
{
  "chartType": "STATISTICS", "name": "总销售额",
  "sheet": "<tableId>", "view": null, "filter": [],
  "measureType": "field",
  "measure": [{"value": "<数值fieldId>", "externalValue": [{"type": "formula", "value": "sum"}]}],
  "desc": "", "numberFormat": {"digits": 0, "format": "number", "thousandSeparator": true},
  "showComparison": false, "showTrend": false, "iconStyle": "5"
}
```

记录总数指标卡：`"measureType": "record-count"`，删掉 measure。

### SUMMARY 统计数字（极简单值）

```json
{
  "chartType": "SUMMARY", "name": "记录总数",
  "sheet": "<tableId>", "view": null, "filter": [],
  "measureType": "record-count",
  "numberFormat": {"digits": 0, "format": "number", "thousandSeparator": true},
  "desc": ""
}
```

### LINE 折线趋势

```json
{
  "chartType": "LINE", "name": "销售额趋势",
  "sheet": "<tableId>", "view": null, "filter": [],
  "measureType": "field",
  "measure": [{"value": "<数值fieldId>", "externalValue": [{"type": "formula", "value": "sum"}]}],
  "dimension": [{"value": "<日期fieldId>", "externalValue": []}],
  "xSortBy": "x", "sortRule": "asc", "nullValue": "ignore",
  "colors": "COLOR_PALETTE_1", "legend": "top", "smooth": false,
  "label": false, "labelHideOverlap": true,
  "xAxisShow": true, "yAxisShow": true
}
```

按分类分系列：加 `"group": [{"value": "<单选fieldId>"}]`。AREA/STACKED_LINE/STACKED_AREA 结构相同。

### HISTOGRAM 柱状图

```json
{
  "chartType": "HISTOGRAM", "name": "各品类销售额",
  "sheet": "<tableId>", "view": null, "filter": [],
  "measureType": "field",
  "measure": [{"value": "<数值fieldId>", "externalValue": [{"type": "formula", "value": "sum"}]}],
  "dimension": [{"value": "<分类fieldId>", "externalValue": []}],
  "xSortBy": "y", "sortRule": "desc", "nullValue": "ignore",
  "colors": "COLOR_PALETTE_1", "legend": "top", "label": true, "labelHideOverlap": true,
  "xAxisShow": true, "yAxisShow": true
}
```

> `xSortBy`：`"x"` 按维度名排，`"y"` 按度量值排（Top 对比场景用 `"y"+desc`）。BAR / STACKED_* 同此规则。

### PIE 饼图

```json
{
  "chartType": "PIE", "name": "销售额构成",
  "sheet": "<tableId>", "view": null, "filter": [],
  "measureType": "field",
  "measure": [{"value": "<数值fieldId>", "externalValue": [{"type": "formula", "value": "sum"}]}],
  "dimension": [{"value": "<分类fieldId>", "externalValue": []}],
  "colors": "COLOR_PALETTE_1", "legend": "right", "label": true,
  "innerRadius": 0, "outerRadius": 60
}
```

环形图：`innerRadius` 设 40~60。ROSE 结构同 PIE。

### LEADERBOARD 排行榜

```json
{
  "chartType": "LEADERBOARD", "name": "销售 Top 10",
  "sheet": "<tableId>", "view": null, "filter": [],
  "measureType": "field",
  "measure": [{"value": "<数值fieldId>", "externalValue": [{"type": "formula", "value": "sum"}]}],
  "dimension": [{"value": "<分类fieldId>"}],
  "showType": "list", "showCount": 10, "hideValue": false, "sortRule": "desc"
}
```

### FUNNEL 漏斗

```json
{
  "chartType": "FUNNEL", "name": "转化漏斗",
  "sheet": "<tableId>", "view": null, "filter": [],
  "measureType": "record-count",
  "dimension": [{"value": "<环节字段fieldId>"}],
  "colors": "COLOR_PALETTE_1", "sumValue": true, "funnelType": "normal"
}
```

### WORD_CLOUD 词云

```json
{
  "chartType": "WORD_CLOUD", "name": "高频词",
  "sheet": "<tableId>", "view": null, "filter": [],
  "measureType": "record-count",
  "dimension": [{"value": "<文本fieldId>"}],
  "disableParticiple": false, "colors": "COLOR_PALETTE_1"
}
```

### GRID_VIEW 明细表

```json
{
  "chartType": "GRID_VIEW", "name": "数据明细",
  "sheet": "<tableId>", "view": null, "filter": [],
  "viewSort": [], "viewGroup": [], "hiddenFields": {}, "columnSort": [],
  "cellHeight": 32, "frozenColCount": 0,
  "toolbarConfig": {"enableCreateRow": false, "enableFilter": true, "enableGroup": true, "enableSort": true, "enableFind": true, "enableDetailRecord": true}
}
```

## 4. 布局约定（chart create --layout）

- **建图前必先确认网格列数**：`dashboard get` 看 `data.meta` —— `schemaVersion=2`（返回表现为 `schemaVersionTypeVerified: true`）为 **48 列网格**；没有 schemaVersion 或值为 1 为 **12 列网格**。layout 的 x/w 必须与列数匹配，错配会把图表挤成窄条。
- 12 列网格：`{"x":0,"y":0,"w":6,"h":4}`，x∈[0,11]，w∈[1,12]，**同行宽度之和=12、高度一致**。常用尺寸：指标卡 `w=3,h=3`；半宽图 `w=6,h=5`；通栏图/表 `w=12,h=6`。
- 48 列网格：x∈[0,47]，w∈[1,48]，同行宽度之和=48；上述 12 列尺寸一律 ×4（指标卡 `w=12,h=3`；半宽图 `w=24,h=5`；通栏 `w=48,h=6`）。
- y 从 0 开始按已占行数顺延，行间不留空（留空则后续用 `dashboard arrange` 收紧）。

## 5. filter 格式（可选）

与 dashboard config-example 中 filters 的 filter 相同：

```json
[{"fieldId": "<fieldId>", "link": null, "version": 1, "symbol": "EQ", "value": "已完成"}]
```

第一个条件 `link:null`，后续 `"AND"`/`"OR"`。symbol 合法值：文本 EQ/NE/CONTAIN/EXCLUSIVE；数字 EQ/NE/GT/LT/GTE/LTE；日期 DATE_EQ/BEFORE/AFTER/NOT_AFTER/NOT_BEFORE（value 为 yyyy-MM-dd）；选项 ANY_OF/ALL_OF/NONE_OF（value 为选项 ID 数组）；存在性 EXIST/UN_EXIST（value null）。

## 6. 其他图表类型

widgets-example 全量还含：AREA / STACKED_BAR / STACKED_LINE / STACKED_AREA / PERCENT_STACKED_* / ROSE / RADAR / SCATTER / NPS / PROGRESS / PIVOT / PLOT_MAP / COMPOSITION / SLICER / TABS / RICH_TEXT / IMAGE / EMBED_WEBPAGE / MARQUEE / COUNTDOWN / AI_ANALYZE / 各视图类（KANBAN/GANTT/CALENDAR/GALLERY/卡片列表等）。用法：

```bash
dws aitable chart widgets-example --format json
```

从返回中取对应 chartType 的完整示例，删注释后替换 tableId/fieldId 使用。
