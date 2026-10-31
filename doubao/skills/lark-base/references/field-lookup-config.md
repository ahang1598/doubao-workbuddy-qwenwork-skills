# 查找引用字段契约

## 目录

- [字段结构与逐行匹配](#字段结构与逐行匹配)
- [硬性约束](#section-5-hard-constraints)
- [where 筛选条件](#where-筛选条件)
- [聚合规则](#section-4-aggregate-rules)
- [常见配置模式](#常见配置模式)
- [错误用法汇总](#section-8-anti-pattern-collection)
- [约束速查](#约束速查)

## 字段结构与逐行匹配

| 配置项 | JSON 键 | 规则 |
|---|---|---|
| 类型 | `type` | 必填，值为 `"lookup"` |
| 来源表 | `from` | 必填；取数表 |
| 返回字段 | `select` | 必填；来源表字段 |
| 筛选条件 | `where` | 必填；至少一条 |
| 聚合方式 | `aggregate` | 可选；默认 `raw_value` |

对当前表每行执行：按 `where` 筛选来源表 → 读取 `select` → 按 `aggregate` 聚合 → 返回；两表逐行对应时，必须用 `where` 表达关系。

<a id="section-5-hard-constraints"></a>

## 硬性约束

1. `where` 始终至少含一条条件。
2. Lookup 是只读计算字段，不得手动设置单元格值。
3. 先创建来源表和引用字段；无需预建关联字段，允许按同义字段匹配。
4. 来源表必须与当前表同属一个多维表格；不支持跨多维表格 Lookup。
5. 修改 `from` 时同时修改 `select`；只改来源表会报错。

## where 筛选条件

条件使用 2 或 3 元素元组 `[field, operator, value?]`；`field` 必须属于 `from` 表，值为常量或当前表字段引用。完整结构：

```json
{
  "type": "lookup", "name": "金额", "from": "订单表", "select": "金额", "aggregate": "sum",
  "where": {"logic": "and", "conditions": [
    ["客户名", "==", {"type": "field_ref", "field": "客户名"}],
    ["状态", "==", {"type": "constant", "value": "已完成"}]
  ]}
}
```

`empty` / `non_empty` 允许二元组 `["状态","empty"]`；值必须为 `null` 或省略。

<a id="how-to-find-the-matching-field-pair"></a>

### 如何确定匹配字段对

关联字段在当前表时，写公式 `[关联字段].[字段]`，不建 Lookup。确需 Lookup 时，用 `+field-get` 确认来源表主字段，不按名称猜；主字段可能是拼接公式。禁止交换两侧：

| 两表关系 | 左侧来源表字段 | 右侧当前表 `field_ref` |
|---|---|---|
| 来源表关联字段指向当前表 | 来源表关联字段 | 当前表主字段 |
| 当前表关联字段指向来源表 | 来源表主字段 | 当前表关联字段 |
| 无关联字段，按同义字段匹配 | 来源表匹配字段 | 当前表对应字段 |

关联字段取关联记录主字段比较。按集合语义选 `==` 或 `intersects`；固定、动态条件放入同一 `where`。

### 值格式

固定条件用 `{"type":"constant","value":...}`；逐行匹配用 `{"type":"field_ref","field":"当前表字段"}`。

| 来源字段类型 | `constant.value` |
|---|---|
| `text` | 字符串：`"已完成"` |
| `number` | 数字：`100`、`0.8` |
| `datetime` / `created_at` / `updated_at` | `"ExactDate(2025-01-01)"`、`"ExactDate(2025-01-01 09:30)"`、`"Today"`、`"Yesterday"`、`"Tomorrow"` |
| `select`（`multiple=false/true`） | 选项名数组：`["Todo"]`、`["Todo","Done"]` |
| `link` | 记录引用数组：`[{"id":"rec_xxx"},{"id":"rec_yyy"}]` |
| `user` / `created_by` / `updated_by` | 用户引用数组：`[{"id":"ou_xxx"},{"id":"ou_yyy"}]` |
| `checkbox` | `true` / `false` |
| `attachment` / `location` | 仅支持 `empty` / `non_empty`；值为 `null` 或省略 |
| `auto_number` | 不支持常量比较；改用 `field_ref` |
| `formula` / `lookup`（类型明确） | 按实际结果类型 |
| `formula` / `lookup`（类型模糊） | 字符串：`"some text"` |

日期字段仅含日期时用 `ExactDate(YYYY-MM-DD)`，含时间时用 `ExactDate(YYYY-MM-DD HH:mm)`；复杂或相对日期筛选使用公式字段。

### 动态字段引用与集合比较

`field_ref` 比较前把两端转为集合：`==` 要求完全相等；`intersects` 要求交集非空。

| 字段类型 | 集合元素 |
|---|---|
| `text` | 单个字符串 |
| `number` / `auto_number` / `datetime` | 单个数字 |
| `select`（`multiple=false/true`） | 选项名字符串 |
| `user` / `created_by` / `updated_by` | 用户姓名字符串 |
| `link` | 关联记录主字段的字符串表示 |
| `formula` / `lookup` | 计算结果值 |

例：人员值 `["name1","name2"]` 与文本 `"name1"` 比较，`intersects` 为 `true`，`==` 为 `false`；人员值 `["name1"]` 与该文本用 `==` 为 `true`。关联记录先转为主字段字符串再比较。

### 支持的运算符

| 运算符 | 含义 | 适用字段 |
|---|---|---|
| `==` / `!=` | 相等 / 不相等 | 所有类型 |
| `>` / `>=` / `<` / `<=` | 大于 / 大于等于 / 小于 / 小于等于 | `number`、`datetime` |
| `intersects` / `disjoint` | 交集非空 / 无交集 | 所有类型；`intersects` 常用于 `field_ref` |
| `empty` / `non_empty` | 为空 / 非空 | 所有类型；值为 `null` 或省略 |

`where.logic` 只支持一层 `and` 或 `or`，不支持嵌套；`conditions` 至少一条，空数组会报错。

<a id="section-4-aggregate-rules"></a>

## 聚合规则

省略 `aggregate` 或设为 `"raw_value"`，均原样返回全部匹配值。

| 枚举 | 含义 | `select` 要求 | 结果 |
|---|---|---|---|
| `sum` | 总额、求和、累计金额 | `number` | 数字 |
| `average` | 平均、均值 | `number` | 数字 |
| `max` | 最大、最晚、最近 | `number` / `datetime` | 与来源相同 |
| `min` | 最小、最早 | `number` / `datetime` | 与来源相同 |
| `counta` | 计数、多少条、总数量 | 任意字段 | 数字 |
| `unique_counta` | 去重计数、多少种 | 待去重字段 | 数字 |
| `unique` | 去重列表、有哪些、不同值 | 待展示字段 | 列表 |
| `raw_value` | 全部、所有值；默认 | 待展示字段 | 列表 |

“涉及哪些类别”用 `unique`；“有多少类别”用 `unique_counta`。枚举只用小写字母和下划线：用 `sum` / `average`，不用 `Sum` / `Average`；计数用 `counta`，不用 `count`。

## 常见配置模式

下表中客户表主字段为“客户名”；订单表主字段为“订单编号”，含指向客户表的关联字段“客户”、文本“客户名”、数字“金额”。

| 模式（当前表；目标） | `from` / `select` / `aggregate` | `conditions` |
|---|---|---|
| 1 来源表的关联字段指向当前表（客户表；统计订单数） | `订单表` / `订单编号` / `counta` | `[["客户","intersects",{"type":"field_ref","field":"客户名"}]]` |
| 2 当前表的关联字段指向来源表（订单表；引用客户负责人） | `客户表` / `负责人` / 省略 | `[["客户名","intersects",{"type":"field_ref","field":"客户"}]]` |
| 3 无关联字段，按同义字段匹配（客户表；汇总金额） | `订单表` / `金额` / `sum` | `[["客户名","==",{"type":"field_ref","field":"客户名"}]]` |
| 4 动态匹配加固定状态（只汇总当前负责人名下已完成订单） | `订单表` / `金额` / `sum` | `[["负责人","==",{"type":"field_ref","field":"负责人"}],["状态","==",{"type":"constant","value":"已完成"}]]` |
| 5a 固定日期：2025-01-01 起（含当天） | `订单表` / `金额` / `sum` | `[["客户名","==",{"type":"field_ref","field":"客户名"}],["日期",">=",{"type":"constant","value":"ExactDate(2025-01-01)"}]]` |
| 5b 动态当天：“日期”必须是真实发生日期 | `订单表` / `金额` / `sum` | `[["客户名","==",{"type":"field_ref","field":"客户名"}],["日期","==",{"type":"constant","value":"Today"}]]` |

固定范围按指定边界保存，不随运行日期变化；动态当天不得复用固定边界。当天边界按 Base 时区解释。保存后核对动态值及当天、非当天代表记录；跨日时动态范围必须移动，固定范围必须保持。复杂动态范围使用受支持的日期值或等价公式。

<a id="section-8-anti-pattern-collection"></a>

## 错误用法汇总

| 错误 | 后果与恢复 |
|---|---|
| 省略 `where` | 每行读取全部来源记录；补表达两表关系的 `where` |
| `{"type":"constant","value":"客户名"}` 表达动态关联 | 改为 `{"type":"field_ref","field":"客户名"}` |
| `{"aggregate":"count"}` | 改为 `{"aggregate":"counta"}` |
| `{"aggregate":"SUM"}` / `{"aggregate":"Sum"}` | 改为小写枚举，如 `sum` / `average` |
| `conditions` 中嵌套 `logic` | 展平成一层，或只用一层 `or` |
| 混淆 Link 与 Lookup | Link 建立可编辑记录关系；Lookup 与 Formula 均为只读计算字段 |
| 条件写成 `{"fieldRef":"状态","operator":"is","value":...}` | 改为元组 `["状态","==",{"type":"constant","value":"已完成"}]` |
| 请求缺少 `type` | 加入 `"type":"lookup"`；请求体必须包含该键值 |

## 约束速查

- 表名和字段名必须与 `+table-get` 输出逐字一致。
- `select` 常量使用选项名。
- `link` / `user` 常量使用 `{id}` 对象数组。
