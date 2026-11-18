# 确定性现金流工具契约

当分析任务存在明确的多期财务三表、现金流补充调整、自定义自由现金流口径差异或一次性现金事项与股东现金回报检验时，可按需调用 `scripts/company_cashflow_bridge.py` 执行复算。一般性简短公司问答无需运行此脚本。

## 一、核心能力与输入规范

1. **三层现金流桥与残差输出**：
   - 以合并 `net_profit` 为起点，加总输入中提供的非现金调整与营运资金项，得出 `calculated_cfo`，并显式计算 `cfo_reconciliation_difference = calculated_cfo - reported_cfo`（未零值对平时诚实反映残差）。
   - 对非标准现金流特征主体（如在补充 JSON 中标记 `cashflow_profile` 为 `"balance_sheet_driven"` 或 `"pre_revenue"`，或设置 `standard_cashflow_applicable: false`），脚本返回不适用标记并提示按对应资产负债或里程碑框架分析。
2. **常规现金 FCF 与披露 FCF 差额方向**：
   - 自动计算 `calculated_fcf = reported_cfo - abs(capex)`。
   - 若同时提供公司披露 `free_cash_flow` 及元数据 `fcf_definition`（包含 `name`、`kind`、`formula`、`source`），脚本在 `bridges.<期间>` 下输出 `fcf_reconciliation_difference`（`kind` 为 `analyst_conventional` 时计算）及 `fcf_discrepancy`（仅返回数值差额 `conventional_minus_reported` 与方向 `direction`：`aligned`、`reported_lower_than_conventional` 或 `reported_higher_than_conventional`，具体成因由分析者结合披露解释）。
   - 多期公司自定义调整口径可在 JSON 中通过 `adjusted_fcf_definitions` 按期别配置（必填字段为 `name`、`reported_metric`、`starting_metric`、`statutory_total_cash_metric`、`source`，其余说明字段均可选）。
3. **一次性现金事项正常化调整（`one_time_cash_adjustments`）**：
   - 按报告期传入记录列表，每条需含 `name`、`amount`（正数绝对额）、`cash_direction`（`"outflow"` 或 `"inflow"`）、`already_in_reported_cfo`（布尔值）和 `source`。
   - 当 `already_in_reported_cfo=true` 时，一次性流出执行加回（`+amount`），一次性流入执行扣减（`-amount`），写入 `bridges.<期间>.one_time_normalization`。
4. **现金分配覆盖度与非现金资本安排（`shareholder_payouts`）**：
   - 按报告期传入 `cash_dividends`、`cash_buybacks`（可选通用项 `other_cash_distributions`、`other_related_cash_outflows`、`non_cash_capital_commitments`）。
   - 结果写入 `bridges.<期间>.shareholder_payout_coverage`，输出 `total_cash_shareholder_return`、`cash_fcf_coverage` 与 `normalized_fcf_coverage`（含 `fully_covered`、`payout_of_fcf_pct`、`fcf_coverage_multiple`、`cash_surplus_or_gap` 等），并将 `non_cash_capital_commitments` 单列记录，不计入当期现金分配流出。

## 二、数据结构示例与运行边界

- 基础长表 CSV 规范字段包含 `entity`、`period`、`metric`、`value`、`currency`、`unit`、`scope`（`source_locator` 可选），样例见 [financials.csv](../assets/cashflow-example/financials.csv)、[adjustments.json](../assets/cashflow-example/adjustments.json) 与 [payouts.json](../assets/cashflow-example/payouts.json)。目录输入模式自动读取目录内 `financials.csv` 及支持的补充 JSON 文件。
- 单次调用中所有行须保持同一实体、币种、数量级单位与合并范围，同一期间同一指标出现冲突数值时记入 `conflict_register` 并阻止错误对平；输入结构缺失、口径混杂或文件异常将返回退出码 `2`。
- 工具不可用或材料缺乏补充明细时，在正文保留缺口或降级说明，不强行补零或虚构数据；未实际运行的脚本不得声称已执行。
