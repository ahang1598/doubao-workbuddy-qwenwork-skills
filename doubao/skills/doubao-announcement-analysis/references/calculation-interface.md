# 通用算术接口

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
