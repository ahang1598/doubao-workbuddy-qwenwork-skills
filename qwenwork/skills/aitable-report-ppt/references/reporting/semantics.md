# 计算语义合同（semantics-1.0）

本文件是 Python oracle（`scripts/build_verification_oracle.py`）与 JS runtime（`assets/components/report-runtime.js`）的**共同语义依据**。两套实现共享本合同与陷阱夹具（`evals/fixtures/semantic-traps/`），**不共享计算代码**。任何本文件定义的变化都必须升级 `semantics_version`，并同步升级两侧实现后才能处理新版本规格。

Schema（`assets/report-spec.schema.json`）声明"允许写什么值"；本合同定义"每个值究竟意味着什么"。遇到本合同未定义的情形，两侧实现都必须报 `semantics_unsupported` 硬错误——**宁可失败不猜**。

## 1. 类型与空值判定

- **空值（null）**：字段缺失、JSON null、trim 后长度为 0 的字符串、空数组。
- **数值解析**：number 类型直接使用；字符串 trim 后能被十进制语法（可含正负号、小数点、科学计数法，如 `-12.5`、`3e2`）完整解析的按数值处理；**其余（含千分位逗号 `1,000`、百分号 `50%`、混合文本）在数值上下文中视为空值**，从而受 `null_policy` 管辖——绝不静默当 0。
- **文本归一化（normText）**：Unicode NFC 归一化 + trim 首尾空白；大小写敏感；内部空白不折叠。

## 2. 聚合函数

设成员集 R（经筛选/membership 后的记录，保持 `records.json` 数组原序），目标字段 f：

| 函数 | 定义 |
|---|---|
| `count` | \|R\|（记录数，与 f 无关） |
| `distinct_count` | f 上非空值经 `normText(String(v))` 后去重的个数 |
| `sum` | f 上非空数值之和；全空 → 0 |
| `avg` | sum ÷ 分母；`null_policy: exclude` 时分母 = 非空数值行数；`as_zero` 时空值按 0 计入且分母 = \|R\|；分母为 0 → **null**（页面显示"暂无数据"，不显示 0） |
| `min` / `max` | 非空数值上取；全空 → null |
| `median` | 非空数值升序排序；奇数取中位，偶数取中间两数算术平均；全空 → null |
| `percentage` | 分组场景：分组 sum ÷ 全体 sum × 100；全体 sum 为 0 → null。全精度计算，仅显示时舍入（§5） |

**求和顺序**：按 `records.json` 数组原序累加。两侧均为 IEEE-754 double，同序累加保证逐位一致。

## 3. null_policy 与 zero_policy

- `null_policy: exclude`——目标字段为空的记录不参与该口径聚合；分组字段为空的记录不进入任何分组。
- `null_policy: as_zero`——数值上下文空值按 0 参与；分组上下文等同 exclude。
- `null_policy: as_category`——分组字段为空的记录归入固定分组 **`未填写`**，该分组恒排序列末位。
- `zero_policy: show`——聚合结果为 0 的分组保留；字段配置（fields 定义中的 `options`）存在但无记录的选项也以 0 呈现。
- `zero_policy: hide`——0 值分组不呈现，但必须在 report-spec 的 evidence 中声明被隐藏的分组清单。
- `zero_policy: placeholder`——0 值分组保留并带视觉占位标记（数值与 show 一致）。
- **多值分组字段**（多选、人员）：按元素展开，记录计入其每个元素对应的分组（可计入多组）。

## 4. 排序与并列

- `sort.by: value` 按聚合值；`label` 按分组标签；`custom` 按 `custom_order`（未列出的项排在已列出项之后，其间按标签序）。
- **并列打破**：一律按分组标签的 **Unicode 码点升序**（禁止 localeCompare——Python 与 JS 的 locale 排序不可移植；JS 侧必须按码点而非 UTF-16 单元比较）。
- 排序必须稳定。`as_category` 产生的 `未填写` 分组在任何排序结果中恒居末位。

## 5. 数值显示与容差

- 显示舍入：**四舍五入、远离零**（round half away from zero）。两侧统一公式：`sign(v) × floor(|v| × 10^d + 0.5) ÷ 10^d`（double 精度下计算；禁用 Python 内置 `round` 的银行家舍入和 JS `Math.round` 的向正无穷取半）。
- 比对一律在全精度值上进行：`tolerance.type: exact` → 逐位相等；`relative` → \|a−b\| ≤ value × \|expected\|；`absolute` → \|a−b\| ≤ value。
- 舍入只发生在渲染层；oracle 存全精度值。

## 6. 日期与时区

- 时间戳按毫秒 epoch 解析；时区取 spec 的 `report.timezone`，缺省 `Asia/Shanghai`（UTC+8，无夏令时）。
- 分桶算法：`shifted = ms + offset分钟 × 60000`，对 shifted 用 UTC 历法取年月日。按日键格式 `YYYY-MM-DD`，按月 `YYYY-MM`。
- 按日边界：`[00:00:00.000, 次日 00:00:00.000)`。只有日期无时间的字段按该时区当日 00:00 处理。

## 7. filter_ast 操作符

| 操作符 | 定义 |
|---|---|
| `eq` | normText 后严格相等（数值字段按数值相等）；`value` 为 null 时匹配空值字段。**多值字段**：任一元素相等即真 |
| `ne` | `!eq` |
| `gt` / `gte` / `lt` / `lte` | 仅数值与日期；字段值为空或不可解析 → **false**（不抛错） |
| `in` | 字段值属于 `value` 列表；多值字段任一元素属于列表即真；列表含 null 时匹配空值 |
| `contains` | 仅文本；子串匹配（normText 后、大小写敏感）；字段值为空 → false；**搜索值为空或 null → false** |
| `and` | 全部子式为真；`children` 为空数组 → **true** |
| `or` | 任一子式为真；`children` 为空数组 → **false** |
| `not` | 恰一个子式取反 |

### 兼容别名（两侧必须同等支持，仅为兼容既有规格，新规格禁止使用）

| 别名 | 等价形式 |
|---|---|
| `{"op":"all"}` | 恒真（≡ 空 `and`） |
| `items` 字段 | ≡ `children` |
| `in` 的 `values` 字段 | ≡ `value`（列表） |
| `{"op":"is_null","field":f}` | ≡ `eq(f, null)` |
| `{"op":"not_null","field":f}` | ≡ `ne(f, null)` |

## 8. 图表定义的兼容别名

| 别名（旧内联实现） | 规范形式（Schema 1.1） |
|---|---|
| `dimension` | `aggregation.group_by` |
| `measure` | `aggregation.value_field` |
| 顶层字符串 `aggregation` | `aggregation.function`（缺省 `count`） |
| `sort.values`（数组） | `sort: {by:"custom", custom_order:[...]}` |

## 9. 版本演进

- `report-spec.json` 携带 `semantics_version`（缺省 `"1.0"`）。
- Schema 新增字段但不改计算含义 → 只升 `schema_version`。
- 本文件任何定义变化 → 升 `semantics_version`；oracle 与 runtime 在指纹核对时拒绝处理版本不一致的规格。

## 10. 陷阱夹具

`evals/fixtures/semantic-traps/` 下每个夹具覆盖一个"两个合理实现会自然分歧"的点。`expected.json` 由人工审定（`"reviewed": true`）后才参与断言；**禁止把任一实现的首跑结果直接当正确答案**。执行方式见 `scripts/test_contracts.py`：Python oracle 与 JS runtime 分别计算，双方先各自与 expected 比对，再互相比对，三方必须逐项一致。
