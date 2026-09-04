# dashboard block data_config SSOT

Block 的 `data_config` 字段因 `type` 不同而变化。本文档是 dashboard block `data_config` 的单一事实来源（SSOT），包含组件类型、字段结构、筛选格式、约束和可复制模板。

## 支持的组件类型（`type` 枚举）

| type 值 | 说明 |
|---------|------|
| `column` | 柱状图 |
| `bar` | 条形图 |
| `line` | 折线图 |
| `pie` | 饼图 |
| `ring` | 环形图 |
| `area` | 面积图 |
| `combo` | 组合图 |
| `scatter` | 散点图 |
| `funnel` | 漏斗图 |
| `wordCloud` | 词云 |
| `radar` | 雷达图 |
| `statistics` | 指标卡 |
| `text` | 文本（支持 Markdown） |

## 字段类型与操作符速查（AI 决策用）

> 先用 `+field-list` / `+field-get` 确认字段 `type`；本节使用当前字段接口里的 canonical 类型名：`number`、`text`、`select`、`datetime`、`checkbox`、`user`。

```
text: is, isNot, contains, doesNotContain, isEmpty, isNotEmpty
number: is, isNot, isGreater, isGreaterEqual, isLess, isLessEqual, isEmpty, isNotEmpty
select（multiple=false）: is, isNot, isEmpty, isNotEmpty
select（multiple=true）: is, isNot, contains, doesNotContain, isEmpty, isNotEmpty
datetime: is, isGreater, isGreaterEqual, isLess, isLessEqual, isEmpty, isNotEmpty
checkbox: is (value: true/false)
user / created_by / updated_by: is, isNot, isEmpty, isNotEmpty
```

## data_config 通用结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `table_name` | string | 关联数据表名称 |
| `series` | `[{ "field_name": "xxx", "rollup": "SUM" }]` | 指标/Y 轴（与 `count_all` 二选一）。rollup 支持 `SUM` / `MAX` / `MIN` / `AVERAGE` |
| `count_all` | boolean | COUNTA 聚合，统计所有记录数（与 `series` 二选一） |
| `group_by` | `[{ "field_name": "xxx", "mode": "integrated", "sort": {...} }]` | X 轴分组维度。`mode` 必填，`sort` 可选，见下方说明 |
| `filter` | object | 筛选条件 |
| `filter.conjunction` | `"and"` / `"or"` | 筛选逻辑 |
| `filter.conditions` | `[{ "field_name", "operator", "value" }]` | 筛选条件数组，value 类型因字段类型而异（见下方 filter 格式规则） |

### 字段所属表边界

`series`、`group_by` 和 `filter.conditions` 中的每个 `field_name` 都必须逐字存在于 `data_config.table_name` 对应表。逐页执行 `+field-list --limit 200 --jq '.data | {total, page_count: (.fields | length), fields: [.fields[] | {id, name, type}]}'`，再在返回数据中逐字比对目标字段；不要把字段名或其他外部文本拼入 shell/JQ 表达式。找到全部目标字段即可停止。目标仍缺失时，只有 `page_count > 0` 且 `offset + page_count < total` 才用该和作为下一页 `--offset`；空页、offset 未增长或第二次出现同一 offset 时停止并报告读取不完整，不得重复请求。穷尽分页前不能判定字段不存在。Dashboard 不支持用 `关联字段.目标字段` 等点号路径临时跨表取维度、指标或筛选字段，也不能使用其他表的 field ID 或缓存中的旧 field ID。

需要关联表属性时，先判断能否直接把拥有该字段的表作为 `table_name` 且仍保持所需记录粒度；否则按 [Formula](formula-field-guide.md) / [Lookup](lookup-field-guide.md) 指引在当前数据源表创建本地计算投影，默认使用 Formula，仅当用户明确要求 Lookup 时才使用 Lookup。创建后按上面的有界字段查找确认本地字段，并用一次记录查询确认有源值的样例行已得到预期结果，再把该本地字段名用于 Dashboard。无法安全投影或结果为空时不得改用点号路径猜测，也不得宣告组件完成。

### text 类型特殊结构

`text` 类型组件用于展示富文本内容，**不需要数据源配置**（无 `table_name`、`series`、`group_by`、`filter`）。

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | **必填**。支持 Markdown 语法，详见下方说明 |

**支持的 Markdown 语法：**

| 语法 | 示例 | 效果 |
|------|------|------|
| 一级标题 | `# 标题` | 大标题 |
| 二级标题 | `## 标题` | 中标题 |
| 三级标题 | `### 标题` | 小标题 |
| 加粗 | `**文字**` | **文字** |
| 斜体 | `*文字*` | *文字* |
| 删除线 | `~~文字~~` | ~~文字~~ |
| 有序列表 | `1. 项目` | 1. 项目 |
| 无序列表 | `- 项目` | - 项目 |

> **注意**：以上未提及的 Markdown 语法（如链接、图片、代码块、表格等）均不支持。

## group_by 详细说明

### mode 枚举

| mode | 含义 | 适用场景 |
|------|------|----------|
| `integrated` | 聚合分组（默认） | 绝大部分场景，按字段值分组统计 |
| `enumerated` | 多值拆分统计 | 多选、人员等多值字段，将每个选项/人员拆开独立统计 |

> 多选、人员等多值字段默认用 `enumerated`；其他字段默认用 `integrated`。

### sort 排序

| sort.type | 含义 | 典型场景 |
|-----------|------|----------|
| `group` | 按横轴值排序 | 按月份升序、按品类名字母序 |
| `value` | 按纵轴值排序 | 按销售额从大到小 |
| `view` | 按数据源记录顺序 | 保持原表行序（不常用） |

`sort.order`：`asc`（升序）/ `desc`（降序）

只要写 `sort` 对象，就需要明确排序方向。CLI 会把 `sort.type` 为 `group` 或 `view` 且缺少 `order` 的情况规范化为 `order:"asc"`；`sort.type:"value"` 必须显式写 `order:"asc"` 或 `order:"desc"`，因为指标值排序方向会改变业务含义。

如果表中行序就是业务顺序，首次创建 block 时就一次性设置 `sort:{"type":"view","order":"asc"}` 保留行序，避免创建后再二次更新排序条件。

### 时间口径决策

范围筛选回答“统计哪些记录”，分组维度回答“结果按什么粒度展开”；两者不可互相代替。一个请求包含多个图表、指标卡或结论时，在首次 Create/Update 前为每个交付物分别确定 `range`（筛选范围）与 `grain`（分组粒度），读完本节后逐项复核原计划。时间词只约束其所在的子目标，不得从相邻交付物继承；现有组件名称和配置只能作为待核对的现状，不能覆盖用户本次语义。

| 用户语义 | 必须落地的配置 |
|----------|----------------|
| 按年月、逐月、各月、月度趋势、跨月比较 | `group_by` 必须包含稳定的年月键；不要只加 `CurrentMonth`，也不要直接用会产生日桶的原始 datetime |
| 本月、当月、当前月 KPI | 用 `CurrentMonth` 或等价本月 filter 限定范围；`group_by` 只保留用户另行要求的维度，单值指标卡不强加月份分组 |
| 按月份和另一维度 | `group_by` 同时包含年月键和另一维度，顺序与图表主轴/系列语义一致 |
| 本年度 | 必须保留年度 filter；filter 类型不匹配时不能删掉范围约束后交付 |

裸“每月”或“月度”同时可能表示逐月序列或当前月 KPI：若该交付物还要求趋势、各月、跨月、按年月或时间轴，走年月分组；若该交付物明确要求本期单值、本月或当月汇总，走本月 filter。输出形态仍无法判断时先澄清；用户明确要求立即执行或禁止追问时，未带“本月 / 当月 / 当前月”等范围词的“月度对比 / 月度趋势”默认使用 `YYYY-MM` 分组，不得借用相邻交付物的 `CurrentMonth`。

服务端没有稳定保留月粒度配置键时，先按 [Formula](formula-field-guide.md) 创建文本公式字段，例如 `TEXT([日期字段], "YYYY-MM")`，用该字段作为 `group_by` 并按 group 升序。年度 datetime filter 无法稳定表达时，为目标指标创建动态 helper measure，例如 `IF(YEAR([日期字段]) = YEAR(TODAY()), [指标字段], "")`，再让 Dashboard 聚合该字段；不要持久化“当前四位年份”常量，也不要用未经验证的 Formula filter 兜底。创建公式后先用记录查询确认当年记录有值、非当年记录为空，再配置并按 Dashboard 交付健康门禁回读；不得用组件名称或请求中的未保留字段声称粒度正确。

### 相对时间与年度范围验收

“本月、当月、今年、本年度、年度、年底、近 N 天/月、超过 N 天/月、即将到期”等词是数据范围要求，不只是组件名称。完成前必须对本轮创建或修改的每个组件执行 `+dashboard-block-get`，检查保存后的 `data_config.filter` 和依赖公式：

1. 除非用户明确要求固定历史区间，否则禁止把当前运行日期展开成 `ExactDate` 或固定年月边界后持久化；使用 `CurrentMonth`、动态年度公式或等价相对时间条件。
2. “年度/年底”类评分、汇总、排名必须绑定真实业务日期字段，并存在当前年度范围；没有日期字段时先补充字段或澄清，不得聚合全历史后只把组件命名为“年度”。
3. 同一需求的公式、视图、Dashboard 和最终回答必须使用同一时间范围。任一对象仍是固定当前日期、缺少年度范围或范围互相矛盾，都视为验收失败并返工。
4. 用 `+dashboard-block-get-data` 验证计算结果；若样例数据全在同一时期，不能据此证明时间范围正确，仍以保存配置中的动态条件为准。

示例 — 柱状图按销售额降序：

```json
{
  "table_name": "订单表",
  "series": [{ "field_name": "金额", "rollup": "SUM" }],
  "group_by": [{ "field_name": "类别", "mode": "integrated", "sort": {"type": "value", "order": "desc"} }]
}
```

## filter 格式规则

**基本结构：**

```json
{
  "filter": {
    "conjunction": "and",
    "conditions": [
      { "field_name": "字段名", "operator": "操作符", "value": "值" }
    ]
  }
}
```

**多条件示例（and/or）：**

```json
{
  "filter": {
    "conjunction": "and",
    "conditions": [
      { "field_name": "状态", "operator": "is", "value": "已完成" },
      { "field_name": "金额", "operator": "isGreater", "value": 1000 }
    ]
  }
}
```

**操作符：**

| 操作符 | 含义 | 是否需要 value |
|--------|------|---------------|
| `is` | 等于 | 是 |
| `isNot` | 不等于 | 是 |
| `contains` | 包含 | 是 |
| `doesNotContain` | 不包含 | 是 |
| `isEmpty` | 为空 | 否 |
| `isNotEmpty` | 不为空 | 否 |
| `isGreater` | 大于 | 是 |
| `isGreaterEqual` | 大于等于 | 是 |
| `isLess` | 小于 | 是 |
| `isLessEqual` | 小于等于 | 是 |

**各字段类型的 value 格式：**

| 字段类型 | value 类型 | 适用操作符 | 示例 |
|----------|-----------|-----------|------|
| `text` | string | is, isNot, contains, doesNotContain, isEmpty, isNotEmpty | `{"field_name":"姓名","operator":"contains","value":"张"}` |
| `number` | number | is, isNot, isGreater, isGreaterEqual, isLess, isLessEqual, isEmpty, isNotEmpty | `{"field_name":"金额","operator":"isGreater","value":0}` |
| `select` (`multiple=false`) | string（选项名） | is, isNot, isEmpty, isNotEmpty | `{"field_name":"状态","operator":"is","value":"已完成"}` |
| `select` (`multiple=true`) | string[]（选多个）/ string（选单个） | is, isNot, contains, doesNotContain, isEmpty, isNotEmpty | 多选传数组如 `["标签1","标签2"]`；单选传单个字符串 |
| `datetime` / `created_at` / `updated_at` | 绝对日期 `["ExactDate", Unix 毫秒时间戳]`；当前月 `["CurrentMonth"]` | is, isGreater, isGreaterEqual, isLess, isLessEqual, isEmpty, isNotEmpty | `{"field_name":"创建日期","operator":"is","value":["CurrentMonth"]}` |
| `checkbox` | boolean | is | `{"field_name":"已审核","operator":"is","value":true}` |
| `user` / `created_by` / `updated_by` | string 或 string[]（用户 ID，格式 `ou_xxx`）。不知道 `open_id` 时先用 `lark-cli contact +search-user --query "<姓名/邮箱/手机号>" --as user` 查 id。 | is, isNot, isEmpty, isNotEmpty | `{"field_name":"负责人","operator":"is","value":"ou_xxxxxxxxxxxxxxxx"}` |
| 所有类型（为空/不为空） | 不需要 value | isEmpty, isNotEmpty | `{"field_name":"备注","operator":"isEmpty"}` |

> `value` 类型因字段而异，可为 `string | number | boolean | string[] | ["ExactDate", number] | ["CurrentMonth"]`，需按上表构造。

### 日期筛选

图表 `data_config.filter` 筛选 `datetime` / `created_at` / `updated_at` 字段时：

- 有值条件支持 `is`、`isGreater`、`isGreaterEqual`、`isLess` 和 `isLessEqual`。
- 绝对日期或区间边界写成 `["ExactDate", <Unix 毫秒时间戳>]`，不得直接传裸时间戳。
- 当前自然月范围可用 `{"field_name":"<日期字段>","operator":"is","value":["CurrentMonth"]}`；`CurrentMonth` 只限定记录范围，不产生按月分组维度。
- `isEmpty` / `isNotEmpty` 不传 `value`。

日期区间示例：

```json
{
  "filter": {
    "conjunction": "and",
    "conditions": [
      {"field_name":"创建日期","operator":"isGreater","value":["ExactDate",1704038400000]},
      {"field_name":"创建日期","operator":"isLess","value":["ExactDate",1735574400000]}
    ]
  }
}
```

## 约束与本地校验

- 必填与互斥
  - 图表类型必填：`table_name`
  - text 类型必填：`text`
  - 互斥：`series` 与 `count_all` 二选一，且至少提供其一（仅图表类型）
  - text 类型**不支持**：`series`、`count_all`、`group_by`、`filter`
- 长度/结构
  - `group_by` 最多 2 个；每项 `field_name` 必填
  - `group_by[].sort.type` 取值 `group|value|view`；`order` 取值 `asc|desc`
- 规范化（CLI 自动处理；`--no-validate` 时不生效，`data_config` 原样透传给后端）
  - `series[].rollup` 自动转成大写（如 `sum` → `SUM`）
  - `group_by[].sort.type/order` 自动转成小写
  - `group_by[].sort.type` 为 `group` 或 `view` 且缺少 `order` 时，自动补 `order:"asc"`；`value` 排序不会自动补方向
- 本地校验（可通过 `--no-validate` 跳过）
  - `+dashboard-block-create` 默认对 `data_config` 做轻量校验；失败会聚合错误并给出修复建议
  - `+dashboard-block-update` 不带 `--type`，所以不做按组件类型的强校验，字段由后端验证；但 `number_format` 子字段与 create 一样本地拦截（见下方 number_format 小节）
  - 仅需传入合法 JSON；CLI 不会擅自改写你的业务含义

## 可复制模板

**按意图选择模板：**
- 比较不同类别数值 → 柱状图 / 条形图
- 看趋势变化 → 折线图 / 面积图
- 看占比分布 → 饼图 / 环形图 / 词云
- 多指标对比 → 组合图
- 宽表多指标横向对比（如各科平均分、各渠道平均分、多个评分项对比）→ 先判断是否需要把字段名转换成可分组维度；不要把主键、姓名、学号等实体字段误当横轴
- 看两变量关系 → 散点图
- 看流程转化 → 漏斗图
- 看多维度评分 → 雷达图
- 显示单个指标 → 指标卡（统计数字或记录数）

最小柱状图：

```json
{
  "table_name": "表名",
  "series": [{ "field_name": "数值字段", "rollup": "SUM" }],
  "group_by": [{ "field_name": "分组字段", "mode": "integrated" }]
}
```

最小饼图/环形图（按分类字段统计行数占比）：

```json
{
  "table_name": "表名",
  "count_all": true,
  "group_by": [{ "field_name": "分类字段", "mode": "integrated" }]
}
```

折线图（按月趋势）：

```json
{
  "table_name": "表名",
  "series": [{ "field_name": "金额", "rollup": "SUM" }],
  "group_by": [{ "field_name": "月份", "mode": "integrated", "sort": {"type":"group","order":"asc"} }]
}
```

条形图（横向柱状图）：

```json
{
  "table_name": "表名",
  "series": [{ "field_name": "数值字段", "rollup": "SUM" }],
  "group_by": [{ "field_name": "分组字段", "mode": "integrated" }]
}
```

面积图（趋势填充）：

```json
{
  "table_name": "表名",
  "series": [{ "field_name": "数值字段", "rollup": "SUM" }],
  "group_by": [{ "field_name": "时间字段", "mode": "integrated", "sort": {"type":"group","order":"asc"} }]
}
```

组合图（柱+线等多指标对比）：

```json
{
  "table_name": "表名",
  "series": [
    { "field_name": "指标1", "rollup": "SUM" },
    { "field_name": "指标2", "rollup": "SUM" }
  ],
  "group_by": [{ "field_name": "分类字段", "mode": "integrated" }]
}
```

宽表多指标横向对比（多个数值字段本身就是要比较的对象）：

- 典型表达：各科平均分对比、各渠道平均值对比、多个评分项对比。
- 不要把“学号 / 姓名 / 客户 / 记录编号”等实体主键字段放进 `group_by`，否则会变成逐个实体的多指标对比。
- 如果组件无法直接把多个 `series` 展示成“字段名作为横轴”的图，先创建 helper 汇总表，如 `科目`、`平均分` 两列；每个被比较字段写一条汇总记录，再按汇总表画柱状图。
- helper 汇总值必须由 `+data-query` 或可复核的程序化聚合算出；不要手工心算平均值。

示例：原始表有 `语文`、`数学`、`英语` 三个分数字段，用户要“各科平均分对比”。先聚合三科平均分，写入汇总表：

```text
科目 | 平均分
语文 | <avg_语文>
数学 | <avg_数学>
英语 | <avg_英语>
```

再创建图表：

```json
{
  "table_name": "各科平均分汇总",
  "series": [{ "field_name": "平均分", "rollup": "AVERAGE" }],
  "group_by": [{ "field_name": "科目", "mode": "integrated", "sort": {"type":"view","order":"asc"} }]
}
```

散点图（两变量相关性）：

```json
{
  "table_name": "表名",
  "series": [{ "field_name": "Y轴字段（数值/指标）", "rollup": "SUM" }],
  "group_by": [{ "field_name": "X轴字段（分类/维度）", "mode": "integrated" }]
}
```

漏斗图（流程转化）：

先判断用户要看的数值语义：

- **当前数量**：统计每个当前状态/阶段下有多少记录，例如“各环节当前数量”“当前阶段分布”。源表有状态/阶段字段时，直接用 `count_all:true` + `group_by`。
- **累计数量**：统计到达该阶段及其后续阶段（后缀和）的累计数量，例如“流程转化”“从 A 到 B 各环节转化”。此口径假设流程单向、无跳阶/回退、记录不删除；不满足时须用状态变更历史，不能对当前快照累加。如果表中已有累计数量字段或阶段汇总表，直接用该字段画漏斗图；否则先计算累计数量，创建并写入 helper 汇总表后再画图。

当前数量：

```json
{
  "table_name": "表名",
  "count_all": true,
  "group_by": [{ "field_name": "状态字段", "mode": "integrated" }]
}
```

累计数量：

```json
{
  "table_name": "流程汇总表名",
  "series": [{ "field_name": "累计数量", "rollup": "SUM" }],
  "group_by": [{ "field_name": "阶段字段", "mode": "integrated", "sort": {"type":"view","order":"asc"} }]
}
```

如果只有当前状态数据但用户要看流程转化，需要先按业务阶段顺序计算每个阶段的累计数量，再创建 helper 汇总表（如：阶段、累计数量），用 `+record-batch-create` 一次写入后，按“累计数量”模板创建漏斗图。helper 表行序就是业务顺序时，首次创建 block 时一次性设置好 `group_by.sort`。

> ⚠️ 注意:helper 汇总表仅用于源表无法直接聚合出目标形态的场景（如上面的累计数量漏斗图）。只要能在源表上直接用 `group_by` + `rollup`（含 `AVERAGE`）算出，就不需要新建 helper 表。

词云（文本频率）：

```json
{
  "table_name": "表名",
  "count_all": true,
  "group_by": [{ "field_name": "文本字段", "mode": "integrated" }]
}
```

雷达图（多维度评分）：

```json
{
  "table_name": "表名",
  "series": [
    { "field_name": "维度1", "rollup": "SUM" },
    { "field_name": "维度2", "rollup": "SUM" },
    { "field_name": "维度3", "rollup": "SUM" }
  ],
  "group_by": [{ "field_name": "分类字段", "mode": "integrated" }]
}
```

指标卡（统计数字）：

```json
{
  "table_name": "数据表",
  "series": [{ "field_name": "数字", "rollup": "SUM" }]
}
```

指标卡（统计记录数）：

```json
{
  "table_name": "数据表",
  "count_all": true
}
```

### statistics 指标卡数值格式 number_format（可选）

仅 `type: statistics` 支持在 `data_config` 里加可选 `number_format`，控制数值展示格式与精度；不传时服务端会补 `{"formatName":"digital"}`，`precision` 保持省略。其它组件类型不支持该字段：create 会被 CLI 直接拒绝（显式 `--no-validate` 可跳过），避免把后端严格 schema 错误延迟到请求阶段；update 不带 `--type`，由服务端结合组件现有类型裁决。

- `formatName`（string，可选）：必须精确匹配下表 5 个枚举之一，**区分大小写**（不同于 `series[].rollup` 会被自动转成大写，这里不做规范化，`DIGITAL` 会被拒绝）。
- `precision`（integer，可选）：小数位数，`0` 到 `9` 的整数；`2.5` 这类非整数会被本地拒绝。

| formatName | 含义 | 示例（precision=2） |
|------------|------|--------------------|
| `digital` | 千分位数字（不传 `number_format` 时的服务端默认值） | `1,234.56` |
| `digital_without_separator` | 无千分位数字 | `1234.56` |
| `percentage_rounded` | 百分比 | `1,234.56%` |
| `cyn_rounded` | 人民币金额 | `¥1,234.56` |
| `dollar_rounded` | 美元金额 | `$1,234.56` |

指标卡（金额，保留 2 位小数）：

```json
{
  "table_name": "订单表",
  "series": [{ "field_name": "金额", "rollup": "SUM" }],
  "number_format": { "formatName": "dollar_rounded", "precision": 2 }
}
```

> **更新时 `number_format` 按子字段合并**：例如现有 `{"formatName":"digital","precision":2}` 时只传 `{"number_format":{"precision":0}}`，服务端会保留 `formatName:"digital"` 并把精度改为 `0`。其它顶层 key 的更新策略见 [lark-base-dashboard.md](lark-base-dashboard.md)。

文本组件（Markdown 富文本）：

```json
{
  "text": "# 🚀 一级标题\n这是一个 **加粗** *斜体* ~~删除线~~ 的示例。\n\n## 📌 二级标题\n1. 有序列表项 1\n2. 有序列表项 2\n\n### 📌 三级标题\n- 无序列表项 1\n- 无序列表项 2"
}
```

> **注意**：text 类型组件不需要 `table_name`、`series`、`group_by`、`filter` 等数据源相关字段。

## 常见错误与修复

- 同时存在 `series` 与 `count_all`
  - 现象：后端/本地校验报互斥错误
  - 修复：见「关键约束」章节的二选一规则
- 缺少 `table_name`
  - 现象：本地校验缺少必填字段
  - 修复：指定数据源表名（使用表名，非表 ID）
- `series[].rollup` 大小写/取值不合法
  - 现象：本地校验提示枚举不支持
  - 修复：改为 `SUM|MAX|MIN|AVERAGE` 中之一（不区分大小写，CLI 会统一为大写；计数请使用 `count_all:true`）
- `group_by` 超出 2 个或字段名为空
  - 修复：保留前 2 个，或补齐 `field_name`
- 排序枚举不合法
  - 修复：`group_by.sort.type` 仅能为 `group|value|view`；`order` 为 `asc|desc`
- filter 写法不规范
  - 修复：`conjunction` 取 `and|or`；`conditions[].operator` 必须在本页表格列举的范围内；除 `isEmpty/isNotEmpty` 外需提供 `value`

## 坑点

- **`count_all` 与 `series` 二选一** — 两者不能同时使用
- **filter `value` 类型因字段而异** — 文本/单选为 string，数字为 number，日期为毫秒时间戳，多选/人员可为 string[]，复选框为 boolean；`isEmpty`/`isNotEmpty` 不需要 value
- **filter 的选项值必须溯源到真实字段选项** — `select` / `multiselect` 条件的 `value` 只能是该字段已存在的选项，先用 `+field-list` 或 `+field-search-options` 确认。写入不存在的选项、空字符串或空数组通常不会报错，但组件会静默筛不出数据（在界面上表现为筛选项一个都没勾中），最容易被误判成“筛选已配好”。交付前必须用 `+dashboard-block-get` 回读 `data_config.filter.conditions[]`，逐条确认 `field_name`、`operator`、`value` 与预期一致，再用 `+dashboard-block-get-data` 确认结果非空且符合口径
- **`data_config` 结构随 `type` 变化** — 不同组件类型的字段不同，创建前务必确认类型对应的字段
- **表名用 name，不是 ID** — `table_name` 对应的是表名称（如「订单表」），不是 `table_id`
