# Base Filter 条件结构（公共协议）

Filter 是一组「字段/操作符/值」条件的组合，用 `logic`（`and` / `or`）把多条 `conditions` 连接起来，用于描述「满足什么条件」。视图筛选 `filter`、记录读取/搜索的 `--filter-json`、表单题目显隐条件 `visible_rule` 复用同一套 tuple 结构，本文件是其公共协议（SSOT）。

## 0. 适用范围

本协议只适用于以下场景：

- `+view-set-filter` / `+view-get-filter` 的视图筛选配置。
- `+record-list --filter-json` / `+record-search --filter-json` 的结构化记录筛选。
- `+form-questions-create` / `+form-questions-update` 中的 `visible_rule` 显隐条件。

本协议**不适用于 `+data-query`**。`+data-query` 支持过滤，但使用的是 LiteQuery DSL 的 `filters` 对象结构：`{"type":1,"conjunction":"and","conditions":[{"field_name":"状态","operator":"is","value":["有效"]}]}`，不是这里的 tuple 条件 `["状态","==","有效"]`。构造 `+data-query --dsl` 时请阅读 [lark-base-data-query.md](lark-base-data-query.md) 的 FilterGroup / Condition 章节。

## 1. 顶层结构

- 必须是 JSON 对象。
- 顶层结构是 `{logic?, conditions?}`。
- `logic` 默认 `and`；推荐只用 canonical 值 `and` / `or`。
- `conditions` 默认空数组。
- 每条条件写成 tuple：`[field, operator, value?]`。
- `empty` / `non_empty` 可写成 2 项：`[field, "empty"]`、`[field, "non_empty"]`。

```json
{
  "logic": "and",
  "conditions": [
    ["状态", "intersects", ["Doing"]],
    ["负责人", "intersects", [{ "id": "ou_xxx" }]],
    ["截止时间", "empty"]
  ]
}
```

清空写法：

```json
{
  "conditions": []
}
```

## 2. operator

可用 operator：
- `==`
- `!=`
- `>`
- `>=`
- `<`
- `<=`
- `intersects`
- `disjoint`
- `empty`
- `non_empty`

## 3. value 写法

value 类型取决于条件引用对象（字段 / 题目）的类型。

### `text`

用字符串：

```json
["标题", "intersects", "发布"]
```

### `location`

location 筛选只按 `full_address` 字符串匹配，不能直接按经纬度筛选；优先使用 `intersects` 做包含匹配，例如查深圳：

```json
["位置", "intersects", "深圳"]
```

不推荐写 `["位置", "==", "深圳"]` 这类精确匹配，除非确保筛选值与完整 `full_address` 完全一致。

### `number` / `auto_number`

用数字：

```json
["工时", ">=", 3.5]
```

### `select`

用选项名数组：

```json
["状态", "intersects", ["Doing", "Blocked"]]
```

### `user` / `created_by` / `updated_by`

用对象数组：

> **人员筛选：不要猜 ID。** 不知道 `open_id` 时，先用 `lark-contact` 查 id：`lark-cli contact +search-user --query "<姓名/邮箱/手机号>" --as user`。

```json
["负责人", "intersects", [{ "id": "ou_xxx" }]]
```

### `group_chat`

用对象数组：

> **群组筛选：不要猜 ID。** 不知道 `chat_id` 时，先用 `lark-im` 搜群：`lark-cli im +chat-search --query "<群名关键词>" --as user`；取结果里的 `oc_xxx`。

```json
["负责群", "intersects", [{ "id": "oc_xxx" }]]
```

### `link`

用记录 id 对象数组：

```json
["关联任务", "intersects", [{ "id": "rec_xxx" }]]
```

### `checkbox`

用布尔值：

```json
["完成", "==", true]
```

### `datetime` / `created_at` / `updated_at`

用相对时间关键字或 `ExactDate(...)`：

```json
["截止时间", "==", "ExactDate(2026-01-01)"]
```

```json
["截止时间", "==", "ExactDate(2026-01-01 11:30)"]
```

```json
["截止时间", "==", "Today"]
```

本节的 tuple DSL（View/Record/Form 显隐条件）与 `+data-query` / Dashboard 的对象式 filter 是不同协议，不能复制关键字、operator 或 value 形状互用。对象式 filter 另读对应 reference。

当前基准使用的相对日期关键字仅有 `Today`、`Yesterday`、`Tomorrow`。不要发送 `CurrentWeek`、`CurrentMonth` 等周/月关键字；本环境会拒绝这些值。

长期复用的本周、本月或今年筛选，使用动态 Formula 再筛选它的字符串或数字结果；只在用户授权修改表结构时新建/修改辅助字段。例如“是否本月”的表达式可为 `IF(AND(YEAR([日期])=YEAR(TODAY()),MONTH([日期])=MONTH(TODAY())),"是","否")`，写后回读字段和代表性结果，再提交：

```json
{"logic":"and","conditions":[["是否本月","==","是"]]}
```

若仅做一次性查询，可按当前时间计算准确的日期区间；固定历史日期边界使用 `ExactDate(...)`。不要把本次计算出的固定日期保存为会持续更新的视图。边界筛选优先用 `>` / `<`，不假设所有日期场景支持 `>=` / `<=`。

### `formula` / `lookup`

- 先读取字段定义和代表性计算结果，再选择单个字符串或数字作为筛选值，不先猜值试错。
- 返回“是/否”的 Formula 传 `"是"`；返回 1/0 的 Formula 传 `1`。不要因字段名为“是否…”而传 `true`，也不要把文本计算结果套成 `["是"]`。
- 多个文本结果用 `logic:"or"` 组合多个标量条件；不能用数组模拟 select。既有计算结果无法按支持类型过滤时，先说明限制；只有用户授权改变结构时才增加返回字符串/数字的辅助 Formula，不能修改无关字段兜底。

字符串示例：

```json
["风险说明", "intersects", "高风险"]
```

数字示例：

```json
["汇总分", ">=", 80]
```

## 4. 易错点

- 不要再写旧对象风格：`{"field_name":...,"operator":...}`。
- `user` / `group_chat` / `link` 不要写成单个标量。
- `empty` / `non_empty` 不要硬塞无意义的 value。
- 日期条件稳定写法用 `ExactDate(...)` 或 `Today` / `Yesterday` / `Tomorrow`。
- `formula` / `lookup` 筛选值与实际结果同类型，只传一个字符串或数字；多值匹配拆成多个条件。

## 5. 参考
- [lookup-field-guide.md](lookup-field-guide.md)
