# 筛选条件

## filter 格式规则

`conditions` 可含多项；`isEmpty`、`isNotEmpty` 省略 `value`，其他操作符必须传 `value`：

```json
{"filter":{"conjunction":"and","conditions":[
{"field_name":"状态","operator":"is","value":"已完成"},
{"field_name":"金额","operator":"isGreater","value":1000},
{"field_name":"日期","operator":"isGreater","value":["ExactDate",1704038400000]},
{"field_name":"日期","operator":"isLess","value":["ExactDate",1735574400000]}]}}
```

## 操作符

`is` 等于，`isNot` 不等于，`contains` 包含，`doesNotContain` 不包含，`isEmpty` 为空，`isNotEmpty` 不为空，`isGreater` 大于，`isGreaterEqual` 大于等于，`isLess` 小于，`isLessEqual` 小于等于。

### 字段类型与操作符速查

先用 `+field-list` / `+field-get` 确认字段 `type`（canonical 名：`number`、`text`、`select`、`datetime`、`checkbox`、`user`）。

| 字段类型 | 可用操作符 | `value` 类型 |
|---|---|---|
| `text` | is, isNot, contains, doesNotContain, isEmpty, isNotEmpty | string |
| `number` | is, isNot, isGreater, isGreaterEqual, isLess, isLessEqual, isEmpty, isNotEmpty | number |
| `select`（`multiple=false`） | is, isNot, isEmpty, isNotEmpty | string（选项名） |
| `select`（`multiple=true`） | is, isNot, contains, doesNotContain, isEmpty, isNotEmpty | 选多个用 string[]，选单个用 string |
| `datetime` / `created_at` / `updated_at` | is, isGreater, isGreaterEqual, isLess, isLessEqual, isEmpty, isNotEmpty | `["ExactDate", Unix 毫秒时间戳]`，或相对关键字如 `["CurrentWeek"]`、`["CurrentMonth"]` |
| `checkbox` | is | boolean（`true` / `false`） |
| `user` / `created_by` / `updated_by` | is, isNot, isEmpty, isNotEmpty | string 或 string[] 用户 ID（`ou_xxx`） |

## 各字段类型的 value 格式

按上表构造 `value`。不知道用户 `open_id` 时，先运行 `lark-cli contact +search-user --query "<姓名/邮箱/手机号>" --as user` 查 ID。

## 日期筛选

图表 `data_config.filter` 筛选 `datetime` / `created_at` / `updated_at` 时：

- 绝对日期和区间边界写 `["ExactDate", <Unix 毫秒时间戳>]`，不得传裸时间戳。
- 当前自然周写 `{"field_name":"<日期字段>","operator":"is","value":["CurrentWeek"]}`，当前自然月把值换成 `["CurrentMonth"]`。它们只限定记录范围，不产生按周或按月的分组维度。
- `isEmpty` / `isNotEmpty` 不传 `value`。

## 多条件示例

在 `conditions` 中并列多项，见上方结构示例（状态、金额和日期区间）。
