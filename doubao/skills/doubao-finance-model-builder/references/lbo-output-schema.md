# 输入与输出规范

## 目录

- 输入JSON
- 引擎输出
- Excel结论与说明页

## 输入JSON

金额全部使用同一报告币种和同一单位。核心结构：

    {
      "company": {"name": "示例公司", "ticker": "000000", "market": "A", "currency": "CNY"},
      "as_of_date": "2026-07-16",
      "entry": {
        "equity_purchase_price": 1000,
        "debt_to_refinance": 300,
        "cash_acquired": 80,
        "target_cash_used": 40,
        "minimum_cash": 30,
        "minority_interest": 0,
        "preferred_stock": 0,
        "other_debt_like": 0,
        "preferred_stock_to_repay": 0,
        "other_debt_like_to_repay": 0,
        "transaction_fees": 20,
        "financing_fees": 10,
        "management_rollover": 50,
        "entry_ebitda": 160
      },
      "debt_tranches": [
        {
          "name": "Term Loan",
          "opening_balance": 500,
          "cash_interest_rate": 0.08,
          "pik_rate": 0,
          "mandatory_amortization_rate": 0.01,
          "cash_sweep_priority": 2,
          "is_revolver": false,
          "commitment": 0,
          "maturity_year": 7,
          "cash_interest_rate_by_year": {"1": 0.08, "2": 0.085}
        },
        {
          "name": "Revolver",
          "opening_balance": 0,
          "cash_interest_rate": 0.09,
          "pik_rate": 0,
          "mandatory_amortization_rate": 0,
          "cash_sweep_priority": 1,
          "is_revolver": true,
          "commitment": 100,
          "maturity_year": 5
        }
      ],
      "years": [
        {
          "year": 1,
          "ebitda": 170,
          "cash_taxes": 18,
          "capex": 30,
          "change_nwc": 5,
          "other_cash_costs": 0,
          "follow_on_equity": 0,
          "sponsor_distribution": 0
        }
      ],
      "exit": {
        "years": [3, 4, 5, 6, 7],
        "multiples": [7, 8, 9],
        "exit_fee_rate": 0.01,
        "exit_debt_like_adjustments": 0,
        "sponsor_ownership": null
      },
      "target_irrs": [0.20, 0.25, 0.30],
      "assumption_ledger": {
        "ebitda_growth": "零增长",
        "depreciation_amortization": "0",
        "depreciation_tax_shield": "不计折旧税盾",
        "capex": "每年20",
        "working_capital": "每年变动0",
        "cash_taxes": "按25%现金税率",
        "refinancing": "到期债务不自动再融资"
      },
      "management_case": {
        "name": "EBITDA年均增长3%",
        "years": [],
        "exit_year": 5,
        "exit_multiple": 8.0
      },
      "provenance": {
        "sources": [{"source_id": "SRC-01", "title": "公司年报", "date": "2026-03-31"}],
        "field_sources": {
          "entry": ["SRC-01"],
          "operating_case": ["SRC-01"],
          "debt_terms": ["SRC-01"],
          "exit": ["SRC-01"]
        }
      }
    }

年份必须连续从1开始，并覆盖所有退出年份。利率和比例使用小数，例如8%写为0.08。cash_interest_rate填写默认全包利率；浮动利率路径可通过cash_interest_rate_by_year逐年覆盖。

## 引擎输出

输出包括：

- model_status_code、model_status与blocking_issues；
- company与as_of_date；
- validation_errors与warnings；
- sources_and_uses；
- entry_valuation；
- annual_debt_schedule；
- exit_results；
- return_bridge；
- target_irr_diagnostics。
- assumption_ledger；
- management_case_comparison（提供经营改善情景时）。

`provenance` 缺失、来源ID重复、字段组为空或引用不存在的来源ID时，引擎仍可形成计算底稿，但状态为 `INCOMPLETE`。只有 `PASS` 才能在Excel结论页输出利润、MOIC和XIRR结论。输入数字类型错误必须由验证器返回错误清单，不得直接抛出未处理异常。

每个退出结果至少包含退出年份、退出倍数、退出企业价值、退出净债务、原始及截断后股权价值、财务投资人退出回收、累计投入、累计回收、利润、MOIC和XIRR。

## Excel结论与说明页

工作簿内的结论与说明顺序：

1. 一页结论：第3至第7年Base结果、最合理退出窗口和关键风险；
2. 数据基准与证据表；
3. 进入估值及Sources & Uses；
4. 经营假设与三种情景；
5. 债务偿还与流动性；
6. 退出回报矩阵；
7. 回报来源；
8. 敏感性与目标回报反推；
9. 失效条件、置信度和待核验事项。

结论表同时展示绝对利润、MOIC和IRR，避免只给单一回报指标。

“回报来源”必须列示每项金额及其占股权价值变化的比例，不得只写定性段落。若Base回报受损或接近股权归零，紧接风险分析展示 `management_case_comparison`，对比退出EBITDA、企业价值、股权价值、MOIC和XIRR。

<!-- END OF FILE: lbo-output-schema.md -->
