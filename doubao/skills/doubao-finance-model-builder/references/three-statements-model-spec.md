# 三表模型结构与审计规范

## 目录

1. 表页结构
2. 最低科目集
3. 格式和公式
4. 检查表
5. 交付门槛

## 1. 表页结构

推荐顺序：

1. `封面`：公司、市场/代码、模型用途、版本、基准日、币种/单位、准则、情景、预测区间、模型状态和关键结论；
2. `假设`：情景选择器、基准/乐观/悲观假设、来源和备注；
3. `经营驱动`：业务量价、客户、产能、门店、订单、人数等经营驱动；
4. `明细预测`：营运资本、固定资产、债务、利息、税务、股权和其他滚动；
5. `利润表`；
6. `资产负债表`；
7. `现金流量表`；
8. `检查`：勾稽、完整性、合理性和错误扫描；
9. `来源`：输入、期间、单位、来源类型、链接、访问日期和备注。

`volume_price` 模式在 `假设` 与 `经营驱动` 之间增加 `产品明细`。每张计算表首列保存稳定语义键，例如 `product.copper.revenue`、`bs.cash`、`is.net_income`；显示标签放在第二列。公式生成器通过语义键取得行号，禁止在跨表公式中散落手写行号。

产品明细至少展示产量、产销率、销量、数量换算系数、实现价格、价格单位换算系数、价格币种兑模型币种、收入、单位成本、成本单位换算系数、成本币种兑模型币种、销售成本、毛利和毛利率。历史期额外展示已披露收入/成本及差异；未覆盖项目使用显式口径调节行。币种一致时汇率系数也必须显式写1。

复杂公司可拆分 `收入预测`、`固定资产`、`债务`、`税务`、`权益`、`季度预测` 等表页，但保持从输入到输出的左到右逻辑。

## 2. 最低科目集

### 利润表

- Revenue
- COGS
- Gross profit / Gross margin
- SG&A
- R&D（适用时）
- Other operating expense/income
- EBITDA / EBITDA margin
- D&A
- EBIT / EBIT margin
- Interest income
- Interest expense
- Other non-operating items
- EBT
- Income tax / Effective tax rate
- Net income / Net margin

### 资产负债表

- Cash and cash equivalents
- Accounts receivable
- Inventory
- Other current assets
- Total current assets
- Net PP&E
- Goodwill and intangibles（适用时）
- Other non-current assets
- Total assets
- Accounts payable
- Other current liabilities
- Short-term and long-term debt
- Lease liabilities（适用时）
- Other non-current liabilities
- Total liabilities
- Share capital / APIC
- Retained earnings
- AOCI / treasury stock / NCI（适用时）
- Total equity
- Total liabilities and equity
- Balance check

### 现金流量表

- Net income
- D&A and other non-cash items
- Change in AR
- Change in inventory
- Change in AP
- Change in other operating assets/liabilities
- CFO
- Capex
- Acquisitions/disposals/other investing
- CFI
- Debt issuance/repayment
- Equity issuance/repurchase
- Dividends
- CFF
- FX effect（适用时）
- Net change in cash
- Beginning cash
- Ending cash

## 3. 格式和公式

- 用真实日期存储期间，显示为 `yyyyA`、`yyyyE`、`Q1 2027E` 等；
- 清晰分隔历史与预测，不在同一计算块混用月、季、年；
- 蓝色字体表示用户可编辑假设，黑色表示公式，绿色表示工作簿内跨表链接，红色表示外部工作簿链接；
- 预测公式保持 copy-across 一致；总计优先 `SUM` 紧邻上方范围；
- 任何关键假设只出现一次，其他位置通过单元格引用；
- 所有金额、百分比、倍数和日期使用显式数字格式；
- 输入和来源单独保存，公式区禁止隐藏硬编码；
- 重要输入在单元格备注或 `Sources` 表中记录来源。

## 4. 检查表

每项检查单独一行，包含 `Actual`、`Expected`、`Difference`、`Tolerance`、`Status` 和 `Fix hint`。

最低检查项：

| 检查 | 计算 | 合格条件 |
|---|---|---|
| 资产负债平衡 | 总资产 - 总负债和权益 | 绝对值 ≤ 容差 |
| 现金勾稽 | BS 现金 - CFS 期末现金 | 绝对值 ≤ 容差 |
| 留存收益滚动 | 期末 RE - (期初 RE + NI - 分红 ± 其他) | 绝对值 ≤ 容差 |
| 固定资产滚动 | 期末 PPE - (期初 PPE + Capex - D&A - 处置) | 绝对值 ≤ 容差 |
| 债务滚动 | 期末债务 - (期初债务 + 借款 - 还款 ± 其他) | 绝对值 ≤ 容差 |
| 收入合计 | 合并收入 - 分部合计 | 绝对值 ≤ 容差 |
| 现金变化 | 期末现金 - 期初现金 - 净现金变化 | 绝对值 ≤ 容差 |
| 来源完整性 | 未标注关键硬编码数量 | 0 |
| 公式错误 | 错误单元格数量 | 0 |
| 情景有效 | 选择器属于有效情景 | TRUE |
| 净利润归属 | 净利润 - 归母净利润 - 少数股东损益 | 绝对值 ≤ 容差 |
| 少数股东权益滚动 | 期末NCI - (期初NCI + NCI损益 - NCI分红) | 绝对值 ≤ 容差 |
| 分红现金符号 | CFS支付股利 + 母公司股利 + NCI股利 | 差额为0且CFS支付股利≤0 |
| 产品历史勾稽 | 披露收入/成本 - 产品计算值 - 口径调节 | 绝对值 ≤ 容差 |
| 产品单位公式 | 收入和成本公式包含数量、单位换算、逐期汇率与金额除数 | TRUE |

合理性检查包括收入增速、毛利率、费用率、税率、DSO/DIO/DPO、资本开支强度、净债务/EBITDA 和最低现金。合理性超阈值可显示 `WARN`，但不得伪装成 `PASS`。

## 5. 交付门槛

- 三表、关键滚动和现金勾稽全部通过；
- 关键公式和来源经抽样追踪；
- 所有表页渲染检查，标题、标签、金额、备注和图表无裁切；
- 大幅预测跳变有来源或解释；
- 所有剩余限制在 `Cover` 和交付说明中可见；
- 模型状态只能在必需检查全部通过时显示 `PASS`。
- 将检查结果导出为机器可读 `delivery-audit.json` 并运行 `scripts/three-statements/validate_delivery.py`；不得依靠封面手填状态。
- 运行 `scripts/three-statements/audit_three_statements_workbook.py --recalculate required` 直接读取并隔离重算工作簿。`delivery-audit.json` 不得覆盖直接审计失败项。
- 正式模型关键字段来源覆盖率为100%，计算区硬编码关键结果数为0，未解释配平项数为0。
- 组合DCF或LBO任务只有在三表交付审计为 `PASS` 后才能向下游传递预测。

<!-- END OF FILE: three-statements-model-spec.md -->
