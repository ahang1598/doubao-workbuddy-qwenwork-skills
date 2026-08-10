# 确定性领域工具契约

工具：`scripts/company_cashflow_bridge.py`

规则：

1. 先运行工具，再写分析。
2. 工具输出中的计算、分类和未知变量优先于模型自由计算。
3. 模型可以解释和组织工具结果，但不得改写数值、补默认值或删除已发生成本。
4. 工具无法计算时，保留变量和数据缺口，不手算替代。
5. Closed-fixture 模式禁止引用 Fixture 外事实。

领域要求：

工具输出负责现金流桥接和增长率；模型不得新增Fixture外阈值、行业平均或未来自然修复判断。

- `operating_cash_flow` 必须来自现金流量表；净利润桥的计算值不能替代缺失的法定 CFO。
- 输入 `free_cash_flow` 时必须同时提供 `fcf_definition` 的名称、类型、公式和正式来源。
- 分析者常规 FCF 仅按法定 CFO 减现金 CapEx 计算；公司 adjusted FCF 使用 `adjusted_fcf_definition` 逐项桥接，提供 `statutory_total_cash_metric`，并声明客户融资口径。
- adjusted FCF 不能对账时保留 `unreconciled_difference`，不得覆盖法定现金流。
