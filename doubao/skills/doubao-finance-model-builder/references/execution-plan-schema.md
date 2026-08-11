# 建模执行计划协议

## 目录

1. 作用与边界
2. 最低结构
3. 跨模块字段
4. 模块专属要求
5. 阶段状态与结论门

## 1. 作用与边界

在正式计算前建立 `execution-plan.json`，把任务范围、证据要求、模型驱动、交付物和阻断条件冻结为机器可读计划。计划不保存第二套估值结果，也不能替代标准化输入、计算输出或交付审计。

计划只允许以下工作流：`three_statements`、`dcf`、`lbo`、`comps`。组合任务按依赖顺序列示，并为每个工作流提供独立的 `module_plans`。

## 2. 最低结构

```json
{
  "schema_version": "3.1",
  "meta": {
    "task_id": "demo-20260630",
    "company": "示例公司",
    "valuation_date": "2026-06-30",
    "information_cutoff_date": "2026-06-30",
    "currency": "CNY",
    "units": "million",
    "model_purpose": "formal"
  },
  "workflows": ["dcf"],
  "deliverables": {
    "hero": "dcf-formula-model.xlsx",
    "support": ["announcement-sweep.json", "announcement-sweep-validation.json", "equity-evidence.json", "equity-evidence-validation.json", "data-source-ledger.json", "assumption-evidence-matrix.json", "model-contract.json", "model-audit.json", "normalized-dcf.json", "calculated-dcf.json", "delivery-validation.json", "artifact-audit.json"]
  },
  "evidence": {
    "source_ids": ["SRC-REPORT", "SRC-PRICE", "SRC-CORP"],
    "required_topics": ["latest_announcements", "historicals", "forecast", "wacc", "equity_bridge", "share_count", "market_price", "corporate_actions"],
    "conflict_resolution_required": true
  },
  "equity_evidence_plan": {
    "manifest_file": "equity-evidence.json",
    "validation_file": "equity-evidence-validation.json",
    "evidence_directory": "evidence",
    "validator": "scripts/common/validate_equity_evidence.py",
    "acquire_before_bridge": true,
    "must_pass_before_model": true,
    "local_primary_files_required": true,
    "official_search_result_required": true,
    "market_cap_reverse_check_required": true
  },
  "module_plans": {"dcf": {}},
  "quality_gates": ["latest_announcement_sweep", "source_mapping", "local_primary_equity_evidence", "corporate_actions", "market_cap_reverse_check", "formula_errors", "cross_artifact_consistency", "unified_model_audit", "direct_artifact_audit", "artifact_hash_lock"],
  "result_policy": {
    "allowed_statuses": ["PASS", "INCOMPLETE", "FAIL"],
    "conclusion_requires_pass": true,
    "point_value_terminal_share_limit": 0.90
  }
}
```

## 3. 跨模块字段

- `valuation_date`：估值或分析基准日。
- `information_cutoff_date`：允许进入模型的信息截止日，不得晚于估值日。
- `model_purpose`：`formal` 或 `illustrative`。正式模型不得使用未说明占位值。
- `deliverables.hero`：模型计算、质量审计和飞书在线表格导入的唯一正式 `.xlsx` 源文件；`support` 只列审计和复算附件。用户的默认交付入口为该文件经 `lark-cli sheets +workbook-import` 导入后的飞书在线表格链接。
- `evidence.source_ids`：计划引用的来源编号全集，必须唯一。
- `data-source-ledger.json`：在标准化输入和预测前记录逐字段来源披露。
- `assumption-evidence-matrix.json`：在模型计算前连接历史数据、业务驱动、预测逻辑和模型参数。
- `model-contract.json`与`model-audit.json`：冻结prompt驱动、公式路径、场景、单位和反向DCF闭环，并保存统一机器审计。
- `evidence.conflict_resolution_required`：计划要求后续解决冲突；执行计划阶段不得提前声称 `conflicts_resolved=true`。
- `equity_evidence_plan`：涉及市场价值的正式任务必须先取得本地官方证据、再建股数桥，并在建模前通过 `validate_equity_evidence.py`。
- `required_topics`：必须取得或显式标记缺口的证据主题。
- `quality_gates`：执行前约定的硬检查，不得在结果不理想时删除。
- `result_policy`：固定使用 `PASS / INCOMPLETE / FAIL`；只有 `PASS` 才能输出估值或回报结论。

涉及价格、每股价值或市值时，计划只冻结检索和验证要求，不得提前填写检索结果。实际执行时先保存官方基准股本、官方检索结果和公告正文的本地文件及哈希，再建立股数桥；证据验证通过后才做市值反向校验。

所有正式任务的 `required_topics` 必须包含 `latest_announcements`，`quality_gates` 必须包含 `latest_announcement_sweep`，交付附件必须包含 `announcement-sweep.json` 和 `announcement-sweep-validation.json`。按 `references/latest-announcement-sweep.md` 从最新已纳入披露的公开日检索至信息截止日；计划阶段不得预填“无相关公告”。

所有正式任务的交付附件同时列入`data-source-ledger.json`和`assumption-evidence-matrix.json`。执行计划只声明文件、字段和覆盖范围，不得预填尚未检索的数值、链接或“依据充分”结论。

## 4. 模块专属要求

### 三表预测

`module_plans.three_statements` 至少包括：

- `input_file`、`workbook_file` 和 `validation_file`；
- `revenue_driver_level`：`segment`、`volume_price`、`operating_kpi` 或带解释的 `total_growth_fallback`；
- `material_driver_threshold`；
- `required_rollforwards`：现金、营运资本、固定资产、债务和权益；
- `required_checks`：资产负债表、期末现金和留存收益勾稽。

### DCF

`module_plans.dcf` 至少包括：

- 标准化输入、计算输出、公式工作簿和交付验证文件；
- `forecast_driver_level` 与重大分部阈值；
- 悲观、基准、乐观三种情景，每种包含 `rationale`、`changed_drivers`、`source_ids` 和 `invalidation_conditions`；
- `wacc`：公司实际D/E、采用D/E、采用口径和替代理由；
- `terminal_value`：方法、永续增长率或退出倍数、显性期长度和终值占比上限；
- 三表在范围内时，说明只有三表审计通过后才能向DCF传递预测。

### LBO

`module_plans.lbo` 至少包括：

- 输入、计算和验证文件；
- 明示的 `key_assumptions`，包括 EBITDA增长、折旧摊销、资本开支、营运资本变动和税率；
- `operating_improvement_case`；
- `return_attribution_required=true`；
- 分层债务、到期偿付、现金来源和退出年份范围。

### 可比公司

`module_plans.comps` 至少包括：

- 输入、计算和报告/工作簿文件；
- `peer_roles` 包含 `core`、`secondary` 和 `excluded`；
- `peer_rationale_required=true`；
- `premium_discount_analysis_required=true`；
- 目标公司与同行的价格、股本、企业价值桥和预测快照日期要求。

## 5. 阶段状态与结论门

运行记录使用以下阶段，不把过程状态伪装成模型结论：

1. `scope_locked`：证券、时点、币种和方法已冻结；
2. `latest_announcements_frozen`：最新公告结果页和正文已冻结，发现项均已处置并通过验证；
3. `equity_evidence_frozen`：官方股本、检索结果和公司行动证据已本地冻结并通过哈希验证；
4. `evidence_frozen`：其他来源和冲突处理完成；
5. `calculation_validated`：确定性计算检查完成；
6. `artifact_verified`：公式工作簿/报告完成公式与视觉检查；
7. `artifact_directly_audited`：最终主要交付物已被独立重新读取并以SHA-256锁定；
8. `delivery_validated`：跨产物审计完成。

任一必须阶段缺失，最高为 `INCOMPLETE`；任何硬检查失败为 `FAIL`。计划验证通过只说明执行路径完整，不代表模型可以输出结论。

<!-- END OF FILE: execution-plan-schema.md -->
