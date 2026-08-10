# 标准化 DCF 输入

计算脚本接收 UTF-8 JSON。比例使用小数，例如 `8.5%` 写为 `0.085`；金额和股份采用 `meta.units` 指定的同一数量级。

## 机器字段与中文展示

JSON 键名为保证脚本兼容性保留英文，但面向用户的报告、Excel、图表、状态和警告必须转换为中文。常用映射如下：

- `bear` → 悲观情景；`base` → 基准情景；`bull` → 乐观情景。
- `PASS` → 通过；`WARNING` → 警告；`FAIL` / `ERROR` → 失败 / 错误。
- `revenue` → 营业收入；`ebit` → 息税前利润（EBIT）；`fcff` → 企业自由现金流（FCFF）。
- `wacc` → 加权平均资本成本（WACC）；`terminal_growth` → 永续增长率（g）；`terminal_value` → 终值（TV）。

英文缩写首次出现在用户产物时，采用“中文全称（英文全称，英文缩写）：一句口径或经济含义解释”的格式。后续可使用中文全称或缩写。

## 最低结构

```json
{
  "meta": {
    "company": "示例公司",
    "ticker": "000000.SZ",
    "valuation_date": "2026-06-30",
    "currency": "CNY",
    "units": "million",
    "discount_convention": "mid_year",
    "terminal_discount_timing": "end_year",
    "data_grade": "C",
    "model_purpose": "formal",
    "required_source_mappings": ["forecast", "wacc", "equity_bridge", "corporate_actions", "market_cap_cross_check"],
    "consolidated_fcff_includes_non_wholly_owned_subsidiaries": false
  },
  "wacc_components": {
    "risk_free_rate": 0.025,
    "beta": 1.05,
    "equity_risk_premium": 0.055,
    "country_risk_premium": 0.0,
    "size_premium": 0.0,
    "other_equity_premium": 0.0,
    "pre_tax_cost_of_debt": 0.04,
    "marginal_tax_rate": 0.25,
    "equity_weight": 0.8,
    "debt_weight": 0.2,
    "capital_structure_basis": "current_actual",
    "capital_structure_rationale": "使用估值基准日实际市场价值资本结构"
  },
  "equity_bridge": {
    "cash": 200,
    "non_operating_investments": 0,
    "associates": 0,
    "debt": 300,
    "lease_liabilities": 20,
    "unfunded_pension": 0,
    "preferred_stock": 0,
    "minority_interest": 10,
    "other_claims": 0,
    "diluted_shares": 100,
    "current_share_price": 25
  },
  "scenarios": {
    "base": {
      "terminal_growth": 0.025,
      "tax_rate": 0.25,
      "scenario_evidence": {
        "rationale": "基于历史增速、公司产能和稳态收敛形成基准路径",
        "changed_drivers": ["收入增速", "EBIT利润率", "资本开支"],
        "source_ids": ["SRC-01"],
        "invalidation_conditions": ["收入增速连续两个报告期低于假设下限"]
      },
      "forecast": [
        {"period": "2027E", "revenue": 1200, "ebit_margin": 0.15, "da": 45, "capex": 60, "delta_nwc": 18},
        {"period": "2028E", "revenue": 1320, "ebit_margin": 0.16, "da": 49, "capex": 65, "delta_nwc": 18}
      ]
    }
  },
  "sources": [],
  "field_sources": {}
}
```

## 预测字段

公式工作簿还要求提供最近实际期收入锚点，用于把三种情景的预测收入还原为逐年增长率：

```json
"historical_anchor": {
  "period": "2026A",
  "revenue": 1000.0,
  "ebit_margin": 0.135
}
```

正式模型的 `historical_anchor` 必须来自最近已公开实际期，并映射到来源。不得为了得到预期增速而反推或修改实际期收入。

每期必须提供：

- `period`：期间标签。
- `revenue`：收入。
- `ebit_margin` 或 `ebit`：二选一；同时提供时以 `ebit` 为准并检查差异。
- `da`：折旧摊销，加回项输入正数。
- `capex`：资本开支，流出项输入正数。
- `delta_nwc`：经营性净营运资本增加，增加输入正数、释放输入负数。

可选字段：

- `tax_rate`：该期边际现金税率；缺失时使用情景税率。
- `other_noncash`：其他应加回非现金费用，输入正数。
- `other_investment`：其他经营性投资，流出输入正数。
- `discount_time`：从估值日至现金流时点的年数；缺失时按折现约定生成。

## WACC

正式模型必须提供 `wacc_components` 让脚本和Excel计算。若情景使用不同资本成本，可在情景内提供完整 `wacc_components`。直接提供 `wacc` 只允许用于 `model_purpose: illustrative` 的示例模型，并在来源台账说明方法；正式模型不得以硬编码WACC绕过组成项。

权重不必精确合计 1，脚本会按总和归一化，但差异较大时验证器警告。

正式模型在 `wacc_components` 增加：

- `capital_structure_basis`：`current_actual`、`target` 或 `hybrid`。
- `capital_structure_rationale`：说明公司实际D/E、最终采用结构和替代理由。

如采用目标或行业结构，来源台账仍需保存公司基准日实际D/E，不得用行业结构覆盖公司事实。

## 估值日股本、公司行动与市场价值

正式模型即使只有一种普通股，也必须在 `equity_bridge` 中提供 `share_classes`；A+H、ADR或多类别证券逐项列示：

以下片段使用纯虚构证券；采用该片段时，`equity_bridge.diluted_shares` 应同步设为 `180`。正式任务不得复制示例数值。

```json
"share_classes": [
  {
    "security_id": "DEMO-A",
    "exchange": "SSE",
    "shares": 130,
    "shares_date": "2026-06-30",
    "price": 20,
    "price_date": "2026-06-30",
    "price_basis": "unadjusted_close",
    "currency": "CNY",
    "fx_to_valuation_currency": 1.0,
    "source_id": "SRC-PRICE-A",
    "reference_market_cap": 2600,
    "market_cap_date": "2026-06-30",
    "market_cap_source_id": "SRC-MCAP-A",
    "market_cap_tolerance_pct": 0.02
  },
  {
    "security_id": "DEMO-H",
    "exchange": "HKEX",
    "shares": 50,
    "shares_date": "2026-06-30",
    "price": 10,
    "price_date": "2026-06-30",
    "price_basis": "unadjusted_close",
    "currency": "HKD",
    "fx_to_valuation_currency": 0.9,
    "source_id": "SRC-PRICE-H",
    "reference_market_cap": 450,
    "market_cap_date": "2026-06-30",
    "market_cap_source_id": "SRC-MCAP-H",
    "market_cap_tolerance_pct": 0.02
  }
],
"corporate_action_review": {
  "baseline_share_date": "2025-12-31",
  "search_start_date": "2025-12-31",
  "reviewed_through_date": "2026-06-30",
  "source_ids": ["SRC-CORP-A", "SRC-CORP-H"],
  "no_unrecorded_actions_confirmed": true,
  "actions": [
    {
      "security_id": "DEMO-A",
      "action_type": "capitalization_issue",
      "announcement_date": "2026-05-10",
      "effective_date": "2026-05-18",
      "before_shares": 100,
      "change_shares": 30,
      "after_shares": 130,
      "applied_to_share_count": true,
      "source_id": "SRC-CORP-A"
    }
  ]
}
```

`share_classes[].shares` 合计必须与 `diluted_shares` 一致。`shares_date` 必须等于估值日；`price_date` 使用估值日或此前最近交易日，且正式模型不得早于估值日超过7个日历日；`price_basis` 必须为 `unadjusted_close`。不得缺省汇率为1，也不得使用估值基准日之后的价格。

`reference_market_cap` 采用估值币种，日期必须与价格日一致。脚本以 `shares × price × fx_to_valuation_currency` 计算分证券市值，并与独立市值反向勾稽；差异超过 `market_cap_tolerance_pct` 时直接失败。不得以复权价计算市值，也不得使用A股价格乘A+H全部股数。

`corporate_action_review` 从最近可靠股本日覆盖至估值日。`actions` 记录送股、转增、拆合股、增发、配售、回购注销、可转证券转换、ADR比率及A/H股本变化；估值日前已生效项目必须 `applied_to_share_count=true`，且最后一项 `after_shares` 与对应 `share_classes[].shares` 一致。即使无公司行动，仍需提供空数组、检索来源和 `no_unrecorded_actions_confirmed=true`。

正式任务在准备本段输入前，必须已有通过的 `equity-evidence-validation.json`；`source_id` 必须能追溯至 `equity-evidence.json` 中已冻结的本地官方证据。

## 情景依据

正式模型的每个情景必须提供 `scenario_evidence`：

- `rationale`：情景的经济叙述；
- `changed_drivers`：相对基准变化的驱动，不得只写最终估值；
- `source_ids`：事实、历史或假设依据；
- `invalidation_conditions`：未来可观察的失效条件。

缺少情景依据、`source_ids` 为空或引用不存在的来源时验证状态为 `INCOMPLETE`。

三种情景的 `forecast` 必须分别保存折旧摊销、资本开支和营运资本投入；逐年 `tax_rate`、`other_noncash`、`other_investment`、`discount_time` 以及情景 `terminal_fcff` 一旦提供，也必须原样进入Excel假设区。不得只改变收入和利润率而让现金流转换假设静默共用，也不得让Excel用固定0、固定税率、固定0.5/1.5折现时点或末期FCFF覆盖标准化输入。公式工作簿由同一DCF公式链重新计算三种情景。

公式工作簿是五期模板：三种情景的期间标签和顺序必须完全一致，且必须恰为5期；Python计算器仍可处理不少于2期的DCF。若要把其他预测期长度交付为Excel，必须先扩展模板和公式合约测试，不得截断或补造期间。

## 敏感性

可提供：

```json
"sensitivity": {
  "wacc_rates": [0.07, 0.08, 0.09, 0.10, 0.11],
  "terminal_growth_rates": [0.01, 0.02, 0.025, 0.03, 0.04]
}
```

缺失时脚本以基准 WACC 上下各 100/200 个基点和基准 g 上下各 50/100 个基点生成网格。

## 来源字段

`sources` 保存来源台账且 `source_id` 必须非空、唯一；`field_sources` 将关键字段映射到来源编号及标签。正式模型中 `forecast`、`wacc`、`equity_bridge`、`corporate_actions` 和 `market_cap_cross_check` 等必需映射不仅要有键，还必须包含至少一个真实存在的 `source_id`；空对象不得计为覆盖。自主预测 `[H]` 应指向假设说明或模型依据，不要求伪造外部 URL。

<!-- END OF FILE: dcf-input-schema.md -->
