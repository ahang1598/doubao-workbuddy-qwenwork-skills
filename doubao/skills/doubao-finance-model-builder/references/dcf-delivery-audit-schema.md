# DCF交付审计清单

完成Excel和报告后，准备 `delivery-audit.json`。该文件记录对最终交付物的检查，不复制估值逻辑。

```json
{
  "calculation_validation_status": "PASS",
  "source_coverage_ratio": 1.0,
  "source_mapping_audit_passed": true,
  "source_conflict_count": 0,
  "share_class_metadata_complete": true,
  "corporate_action_review_complete": true,
  "share_count_as_of_valuation_date": true,
  "price_share_basis_consistent": true,
  "market_cap_cross_check_passed": true,
  "corporate_action_unapplied_count": 0,
  "three_statements_in_scope": true,
  "balance_sheet_checks": [{"period": "2027E", "difference": 0, "tolerance": 0.01}],
  "cash_rollforward_checks": [{"period": "2027E", "difference": 0, "tolerance": 0.01}],
  "wacc_outputs": {"summary": 0.08, "dcf": 0.08, "base_scenario": 0.08},
  "per_share_outputs": {"summary": 25.1, "excel": 25.1, "report": 25.1},
  "scenario_uses_shared_model": true,
  "sensitivity_uses_shared_model": true,
  "hardcoded_key_output_count": 0,
  "share_bridge_difference": 0,
  "equity_bridge_difference": 0,
  "all_visible_sheets_rendered": true,
  "unresolved_warning_count": 0
}
```

`wacc_outputs` 和 `per_share_outputs` 中每个用户可见位置均要列示。验证器将其与Python计算的基准情景比较。三表不在范围内时将 `three_statements_in_scope` 设为 `false`；组合任务不得设为 `false`。

`source_coverage_ratio` 是关键字段有有效来源或假设依据映射的比例，不是来源行数。`source_mapping_audit_passed` 只有在逐字段来源ID均真实存在、与使用值和日期一致时才能为 `true`；空对象或只有分类键不得通过。`share_class_metadata_complete` 要求每个证券均有交易所、估值日股数及日期、不复权价格及日期、币种、显式汇率、独立市值和来源ID。

`corporate_action_review_complete` 仅在检索从最近可靠股本日覆盖至估值日、所有行动有公告日/生效日/来源时为 `true`；`share_count_as_of_valuation_date` 要求估值日前已生效行动全部滚入股数；`price_share_basis_consistent` 要求使用不复权近端收盘价；`market_cap_cross_check_passed` 要求逐证券计算市值与同日独立市值在容差内一致；`corporate_action_unapplied_count` 必须为0。`share_bridge_difference` 是分证券股数与完全稀释股数差额；`equity_bridge_difference` 是Excel股权价值与企业价值桥接重算值差额。

公式错误、循环引用、外部工作簿链接、静态情景/敏感性及关键Excel输出一致性只接受 `artifact-audit.json` 的直接读取结果，不再接受人工填列 `formula_error_count`。运行交付验证时必须传入 `--workbook-audit artifact-audit.json`。任何必需字段缺失、直接审计失败、关键输出不一致、三表不平或终值占比超过门槛，验证结果不得为 `PASS`。

<!-- END OF FILE: dcf-delivery-audit-schema.md -->
