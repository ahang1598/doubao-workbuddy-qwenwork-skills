# 可选计算与筛选接口

按需要使用，均为Python 3.9+标准库实现。脚本不联网、不读取研究资料、不判断业务事实、不写交付文件；研究主体、财务口径、来源有效性及最终解释由本题与原文确定。

## 通用算术

`financial_checks.py`只提供比率、增长、每股、差额、带符号变动汇总和加权平均。字段及CLI约定见本文件末尾的“算术参数”。没有预设财务指标合格线或行业方法。

## 条件与逐级排序

```bash
python3 scripts/screening_checks.py inputs.json
```

输入为显式的 `rules`、`rows` 及可选 `sort`。`rules` 中每条规则提供唯一 `id`、输入字段 `field`、比较符 `operator` 和阈值 `threshold`；比较符支持 >=、>、<=、<、==。需要逐项达标的序列设置 `all_values=true` 并给 `expected_count`，不以平均数替代。

`rows` 每行包含唯一字符串 `code` 和 `values` 对象，数值可以是十进制字符串，未知写null。代码仅用于连接输入与结果，不参与通过条件或排序推断。`sort` 每项提供 `field` 与布尔值 `descending`，按给定次序逐级比较原始值；同键值保留并列。

接口只实现AND关系。OR或其他逻辑另用符合原题的计算，不交给AND接口强行替代。结果 `decisions` 保留逐条条件及通过、失败或未知状态，`passing_codes` 只含全部通过者，`counts` 给出各状态数量。存在失败且同时缺数时仍保留未知字段。

`ranked_passing` 给通过者的排序；只有并列组确实需要的排序值缺失，才返回 `ranking_status=unknown`。此时完整榜单为空，`determined_ranks` 仍列出名次已经确定的对象；`missing_sort_values` 指出当前阻止比较的字段。筛选状态不变。未请求排序时状态为not_requested。输入限64条规则、10000行和10个排序键；这些是处理规模限制，不是研究条件。重复代码、非法输入和不一致的序列长度返回错误。

## 同池阈值情景

```bash
python3 scripts/screening_scenarios.py inputs.json
```

沿用上述输入，另给可选 `scenarios` 数组；每个情景提供唯一 `id` 和 `thresholds` 对象，以既有规则ID映射新阈值，最多16个情景。不通过该参数修改字段、期间、比较符或业务定义；定义变化需另建明示的条件集。

各情景从同一完整输入行重新计算。输出 `results.baseline` 及情景结果，`changes.added/removed` 是相对基准通过集合的新增与退出。`near_miss_codes` 仅含一条失败且没有未知的对象；`funnel` 是按规则顺序逐层筛选，`independent_rule_counts` 是全池每项独立统计，两者含义不同。

以上字段只描述输入上的计算结果，不证明股票池覆盖、来源真实性或交付内容正确。


## 算术参数

按本题定义确定输入后，才使用 `scripts/financial_checks.py`。脚本只计算显式输入，不识别公司、行业、事件、数据来源或会计处理，也不预设研究时点和筛选条件。

```bash
python3 scripts/financial_checks.py inputs.json
python3 scripts/financial_checks.py - < inputs.json
```

输入为UTF-8 JSON，数值可写为十进制字符串。金额使用一致单位；比例返回值与百分数区分使用。输出中的数值为字符串，增长率无法按正基数解释时返回null，不将其当零。在支持的输入范围内，加、减、乘和求和保留精确结果；除法结果最多保留28位有效数字。若商的舍入会影响严格边界，用原始分子与分母比较，并考虑分母的符号。展示精度仍以来源为准。

| operation | 必填输入 | 运算含义 |
|---|---|---|
| ratio | numerator、denominator | 分子除以非零分母，同时返回比率和百分数 |
| growth | before、after | 返回差额；前值为正时另返回相对增长百分数 |
| per_share | amount、shares | 金额除以正股数；股数采用什么口径由本题决定 |
| difference | before、after | 返回后值减前值 |
| bridge | opening、changes | 期初值加各项带正负号的变化，返回变化合计及期末值；changes可以为空 |
| weighted_mean | values、weights | 按显式非负权重计算均值；两组等长且总权重大于零 |

虚构算术示例：

```json
{"operation":"bridge","opening":"80","changes":["12","-7"]}
```

得到变化合计5、期末值85。这只说明输入数字的运算关系，不证明项目完整、单位一致或经济解释成立。

Python 3.9+、标准库实现，不联网、不写输出文件。CLI成功退出0，输入无效退出2并在stderr输出错误JSON；命令参数错误输出argparse用法。输入限1MiB，拒绝重复JSON键、非法结构、布尔数值、非有限数字和超出支持范围的精度或数量级。拒绝未知操作，不回退到某种事件公式。
