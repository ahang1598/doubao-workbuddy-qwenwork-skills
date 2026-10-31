# 记录视图与表单共享筛选契约

## 适用对象

以下对象用 `logic`（`and`/`or`）连接「字段/操作符/值」tuple：

| 对象 | 命令/配置 | 协议 |
|---|---|---|
| 记录 | `+record-list`/`+record-search` 的 `--filter-json` | [读取](record-read.md) |
| 视图 `filter` | `+view-set-filter`/`+view-get-filter` | [视图筛选](view-filter.md) |
| 表单题目 | `+form-questions-create`/`+form-questions-update` 的 `visible_rule` | [题目属性](form-questions.md#显隐条件visible_rule) |

本协议不适用于 `+data-query`。它的 `--dsl` 使用 LiteQuery `filters` 对象（如 `{"type":1,"conjunction":"and","conditions":[{"field_name":"状态","operator":"is","value":["有效"]}]}`），不是这里的 tuple `["状态","==","有效"]`；构造时读 [query-dsl.md](query-dsl.md) 的 FilterGroup/Condition。

## 条件结构与默认值

- 必须传 `{logic?,conditions?}` JSON 对象；`logic` 默认 `and`，优先用 canonical `and`/`or`；`conditions` 默认 `[]`。
- 条件为 `[field,operator,value?]`；`empty`/`non_empty` 可省略 value，写 `[field,"empty"]`/`[field,"non_empty"]`。

```json
{"logic":"and","conditions":[["状态","intersects",["Doing"]]]}
```

清空：`{"conditions":[]}`。

## 运算符（operator）

`==`、`!=`、`>`、`>=`、`<`、`<=`、`intersects`、`disjoint`、`empty`、`non_empty`。

## 条件值（value）

| 类型 | value/约束 |
|---|---|
| `text` | 字符串，如 `["标题","intersects","发布"]` |
| `location` | 仅按 `full_address` 字符串匹配，不支持经纬度；优先 `["位置","intersects","深圳"]`，仅完整地址完全一致时用 `==` |
| `number`/`auto_number` | 数字，如 `["工时",">=",3.5]` |
| `select` | 选项名数组，如 `["Doing","Blocked"]` |
| `user`/`created_by`/`updated_by` | 对象数组：`[{"id":"ou_xxx"}]` |
| `group_chat` | 对象数组：`[{"id":"oc_xxx"}]` |
| `link` | 记录 id 对象数组：`[{"id":"rec_xxx"}]` |
| `checkbox` | 布尔值，如 `["完成","==",true]` |

不得猜人员 `open_id`：`lark-cli contact +search-user --query "<姓名/邮箱/手机号>" --as user`。不得猜群 `chat_id`：`lark-cli im +chat-search --query "<群名关键词>" --as user`，取 `oc_xxx`。

### `datetime` / `created_at` / `updated_at`

- value 用 `ExactDate(2026-01-01)`、`ExactDate(2026-01-01 11:30)` 或相对日期；当前基准仅 `Today`、`Yesterday`、`Tomorrow`。
- 不得发送 `CurrentWeek`、`CurrentMonth` 等周/月关键字；本环境拒绝。
- tuple DSL（View/Record/Form 显隐）与 `+data-query`/Dashboard 对象式 filter 不得互用关键字、operator、value 形状。
- 长期复用本周、本月/今年筛选：用动态 Formula 筛其字符串/数字结果；仅经用户授权时新建/修改辅助字段。写后回读字段和代表性结果，再提交。

例如“是否本月”字段的表达式为 `IF(AND(YEAR([日期])=YEAR(TODAY()),MONTH([日期])=MONTH(TODAY())),"是","否")`，筛选写 `{"logic":"and","conditions":[["是否本月","==","是"]]}`。

- 一次性查询按当前时间算准确区间；固定历史边界用 `ExactDate(...)`。不得把本次固定日期保存为持续更新的视图。边界优先 `>`/`<`，不得假设所有日期场景支持 `>=`/`<=`。

### `formula` / `lookup`

- 先读字段定义和代表性结果，再选同类型的单个字符串或数字；不得猜值试错。
- “是/否”结果传 `"是"`，1/0 结果传 `1`；不得因字段名“是否…”传 `true`，不得把文本结果写成 `["是"]`。
- 多文本结果用 `logic:"or"` 拆成标量条件，不得用数组模拟 select。示例：`["风险说明","intersects","高风险"]`、`["汇总分",">=",80]`。
- 结果无法按支持类型过滤时说明限制；仅经用户授权改变结构时增加返回字符串/数字的辅助 Formula，不得修改无关字段兜底。

## 易错点

- 不得写旧的对象风格：`{"field_name":...,"operator":...}`。
- `user`/`group_chat`/`link` 不得写单个标量；`empty`/`non_empty` 不得塞 value。
