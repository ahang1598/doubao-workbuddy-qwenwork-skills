# 中文金融术语与展示规则

## 展示规则

所有用户可见产物默认使用简体中文。英文金融术语首次出现时采用：

```text
中文全称（英文全称，英文缩写）：一句经济含义或计算口径解释。
```

后续可以使用中文简称或英文缩写。表头空间有限时采用“中文全称（缩写）”；不得只写英文全称或缩写。机器接口中的 JSON 键和脚本参数可以保留英文，但必须在报告或 Excel 中映射为中文。

## 核心估值术语

| 中文全称 | 英文全称/缩写 | 简明解释 |
|---|---|---|
| 现金流折现 | Discounted Cash Flow，DCF | 把未来现金流按资本成本折算为当前价值。 |
| 企业自由现金流 | Free Cash Flow to Firm，FCFF | 在向债权人和股东分配资金前，经营资产可提供给全部资本提供者的现金流。 |
| 股权自由现金流 | Free Cash Flow to Equity，FCFE | 在满足经营、投资和债务融资需要后，可供普通股股东分配的现金流。 |
| 息税前利润 | Earnings Before Interest and Taxes，EBIT | 扣除利息和所得税前的经营利润，用于隔离融资结构影响。 |
| 息税折旧摊销前利润 | Earnings Before Interest, Taxes, Depreciation and Amortization，EBITDA | EBIT 加回折旧摊销后的经营利润代理值，不等同于现金流。 |
| 税后经营利润 | Net Operating Profit After Tax，NOPAT | 不考虑融资结构时，经营利润扣除经营相关税负后的利润。 |
| 折旧与摊销 | Depreciation and Amortization，D&A | 对固定资产和无形资产成本的会计分摊，通常作为非现金费用加回。 |
| 资本性支出 | Capital Expenditures，Capex | 用于取得或维护长期经营资产的现金投入。 |
| 经营性净营运资本增加 | Change in Net Working Capital，ΔNWC | 经营性流动资产减经营性流动负债的增加额；增加通常占用现金。 |
| 加权平均资本成本 | Weighted Average Cost of Capital，WACC | 股权和债务资金要求回报率按目标资本结构加权后的折现率。 |
| 无风险利率 | Risk-free Rate，Rf | 与现金流币种和期限匹配、近似无违约风险的基准收益率。 |
| 贝塔系数 | Beta | 股票或业务系统性风险相对市场的敏感度。 |
| 股权风险溢价 | Equity Risk Premium，ERP | 投资股票相对无风险资产要求的额外回报。 |
| 国家风险溢价 | Country Risk Premium，CRP | 对特定国家主权、制度或市场风险要求的额外回报。 |
| 终值 | Terminal Value，TV | 显性预测期结束后全部后续现金流在预测期末的价值。 |
| 永续增长率 | Perpetual Growth Rate，g | 公司进入稳态后现金流长期持续增长的名义速率。 |
| 戈登永续增长法 | Gordon Growth Method | 用下一期稳态现金流除以 WACC 与永续增长率之差估算终值。 |
| 现值 | Present Value，PV | 未来金额按折现率换算到估值基准日后的价值。 |
| 企业价值 | Enterprise Value，EV | 经营资产对债权人、股东等全部资本提供者的价值。 |
| 普通股权益价值 | Equity Value | 企业价值加可扣现金和非经营资产、减债务及其他非普通股索取权后的价值。 |
| 投入资本回报率 | Return on Invested Capital，ROIC | 税后经营利润相对经营投入资本的回报水平。 |
| 反向现金流折现 | Reverse DCF | 从当前市值反推市场隐含的增长、利润率或现金流假设。 |

## 市场、股本与期间术语

| 中文全称 | 英文全称/缩写 | 简明解释 |
|---|---|---|
| 美国存托凭证 | American Depositary Receipt，ADR | 代表一定数量境外普通股、在美国交易的存托凭证。 |
| 限制性股票单位 | Restricted Stock Unit，RSU | 满足归属条件后交付股票的股权激励工具，可能稀释股本。 |
| 绩效股票单位 | Performance Stock Unit，PSU | 归属数量与绩效条件挂钩的股权激励工具。 |
| 完全稀释股份数 | Fully Diluted Shares | 假设具有经济稀释性的期权、RSU、PSU和可转证券计入后的股份数。 |
| 过去十二个月 | Last Twelve Months，LTM | 截至估值时点最近连续十二个月的实际财务期间。 |
| 未来十二个月 | Next Twelve Months，NTM | 从估值时点向后连续十二个月的预测财务期间。 |
| 年中折现约定 | Mid-year Convention | 假设年度现金流在年内均匀产生，并在年度中点折现。 |
| 基点 | Basis Point，bps | 利率或收益率的万分之一；100 个基点等于 1 个百分点。 |

## 数据与审计标签

| 标签 | 中文含义 | 使用规则 |
|---|---|---|
| `[R]` | 原始报告值 | 监管申报、公司披露、原始市场数据或公司行动事实。 |
| `[A]` | 分析调整 | 为可比性或经济实质进行的分析调整。 |
| `[E]` | 外部预测 | 第三方一致预期或可识别卖方预测。 |
| `[D]` | 计算推导 | 换算、日历化、滚动或公式推导值。 |
| `[H]` | 自主假设 | 分析者建立并说明依据的预测假设。 |
| `NA` | 缺失 | 无法可靠取得，不得猜测。 |
| `NM` | 无经济意义 | 分母、符号或经济关系导致指标不具解释意义。 |

## 常见表达修正

- 不只写“WACC 上升 100bps”，应写“加权平均资本成本（WACC）上升 100 个基点，即投资者要求回报率提高 1 个百分点”。
- 不只写“TV 占比 80%”，应写“终值（TV）占企业价值 80%，说明估值对长期假设较敏感”。
- 不只写“FCFF margin”，应写“企业自由现金流率（FCFF/收入）”。
- 不把 EBITDA、FCFF 和净利润互相替代；首次出现时解释各自口径。

<!-- END OF FILE: dcf-terminology-zh.md -->
