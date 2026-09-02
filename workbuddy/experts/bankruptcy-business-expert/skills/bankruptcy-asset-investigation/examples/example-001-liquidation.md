# Example 001: 破产清算财产调查

## 输入

```yaml
case: "XX制造有限公司破产清算案"
case_number: "（2026）粤03破申056号"
acceptance_date: "2026-07-01"
debtor: "XX制造有限公司"
procedure_type: "bankruptcy_liquidation"
```

## 场景

债务人是一家中小型制造企业，主要财产：银行存款约50万、厂房设备（评估值约800万）、应收账款（账面2000万，但账龄普遍>2年）。管理人已接管账簿和银行流水，发现受理前6个月内有3笔大额转出共计300万。

## 预期输出

O1 接管清单（docx）：7类财产分组，标注接管状态
O2 财产状况报告（docx）：资产清查→负债情况→追收情况
O3 追收线索清单（docx）：3笔转出线索标记为第32条偏颇清偿
O4 结构化摘要（json）：含 total_assets_estimated≈1050万、3条recovery_clues
