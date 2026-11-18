# 可选计算工具

涉及数值运算时按需使用，不要求研究流程必须调用脚本。输入的单位、币种、经济含义与来源由研究者确定；程序仅计算，不识别公司、行业、估值方法或报告内容。

## 调用约定

在skill根目录执行 `python3 scripts/financial_math.py input.json` 或 `python3 scripts/market_math.py input.json`；位置参数 `input` 必填，可以用 `-` 读取标准输入。两个脚本仅依赖Python 3标准库；`market_math.py` 引用同包的 `financial_math.py`，无需额外安装。

JSON对象必填`operation`，其余字段见各表。数值可以是JSON数字或十进制字符串，不接受布尔、null、非有限数和重复字段。数值文本上限256字符、系数最多80位、十进制数量级−100至100；输入文件上限1 MiB，CLI以400位Decimal精度计算。

正常输出为JSON，其中数值使用十进制字符串，另含`arithmetic_only: true`，退出0。无常规经济含义的比率返回null，不以零代替。缺字段、非法操作或输入错误返回`{"error":"invalid_input","hint":"..."}`并退出2。`--help`显示用法。脚本不联网、不写文件、不记录原始输入；它不证明来源真实或比较结论成立。

## 财务运算

| operation | 必填字段 | 结果与适用范围 |
|---|---|---|
| ratio | numerator, denominator | `ratio=分子/分母`及`percent=ratio×100`；分母≤0均为null |
| growth | before, after | `absolute_change=after−before`及增长百分比；before≤0时增长率为null |
| aggregate | values, metric_kind | 非空数值列表的`sum`和`mean`；metric_kind必须为additive。仅处理可加总量，不把比率、每股值或余额当可累计流量 |
| bridge | base, remove, add, metric_kind | `bridged_value=base−remove+add`；metric_kind必须为additive。可表达流量期间桥接，但窗口的连续性和范围不由脚本识别 |
| scale | value, factor | `converted_value=value×factor`；factor为正。数量级或汇率换算需显式提供合适的倍率，不自动推断方向 |

下面均为合成示例：

```json
{"operation":"ratio","numerator":"30","denominator":"120"}
```
输出`ratio="0.25"`、`percent="25.00"`。

```json
{"operation":"bridge","metric_kind":"additive","base":"160","remove":"35","add":"50"}
```
输出`bridged_value="175"`；对于期间桥接，这个数是目标期间值，不是未来预测。

```json
{"operation":"aggregate","metric_kind":"additive","values":["8","12","16"]}
```
输出`sum="36"`、`mean="12"`；均值不代表每个组成项都等于该数。

```json
{"operation":"scale","value":"7.8","factor":"10"}
```
输出`converted_value="78.0"`。乘数来自明确的转换关系，不因公司或行业自动选择。

## 市场运算

| operation | 必填字段 | 结果与适用范围 |
|---|---|---|
| returns | start, end, benchmark_start, benchmark_end | 起止价格全正；个股与基准收益百分比、百分点超额、相对财富超额 |
| risk | prices, frequency, periods_per_year | 至少3个正价格；frequency=daily，年化因子为正整数。输出简单日收益的样本标准差年化百分比、峰谷最大回撤百分比（非负）和收益观察数 |
| premium | left_price, right_price, fx_right_to_left, entitlement_ratio | 输入全正；右证券价格×右币转左币汇率×权益比，得到与一单位左证券等权益的右价格。输出该等值价和两个方向溢价百分比；负数为折价 |

所有价格输入须与问题所选窗口、复权和币种口径相符。波动率不接受缺失日自动补零；脚本不携带日期，不会自行对齐交易日。相对财富超额`(1+r)/(1+b)−1`不等于收益差`r−b`；结果展示时使用各自名称。

```json
{"operation":"returns","start":100,"end":120,"benchmark_start":100,"benchmark_end":110}
```
个股20%、基准10%、超额10个百分点，相对财富超额约9.0909%。

```json
{"operation":"risk","prices":[100,125,100],"frequency":"daily","periods_per_year":252}
```
最大回撤20%、收益观察数2、样本波动率年化约505.12%；这是短序列演示，不是可靠风险估计。

```json
{"operation":"premium","left_price":90,"right_price":120,"fx_right_to_left":1,"entitlement_ratio":1}
```
右等值价120，左相对右折价25%，右相对左溢价约33.3333%。此函数只计算等权益价差，不提供套利或交易结论。
