# Example 001: 标准债权审查

## 输入

```yaml
case: "XX制造有限公司破产清算案"
case_number: "（2026）粤03破申056号"
acceptance_date: "2026-07-01"
claims:
  - creditor: "XX原料供应商"
    claimed: 5000000
    type: "货款"
    evidence: [合同, 送货单, 对账单]
  - creditor: "张三（职工）"
    claimed: 150000
    type: "职工债权-经济补偿金"
  - creditor: "某银行"
    claimed: 10000000
    secured: true
    collateral: "厂房抵押"
    estimated_value: 8000000
  - creditor: "某税务局"
    claimed: 500000
    type: "税收债权-欠税本金"
```

## 预期输出

O1 债权审查结论表（docx）：4笔债权分类审查：
- 货款500万→确认，普通债权
- 职工15万→确认，职工债权（第113条第(一)项）
- 银行1000万→厂房抵押800万确认担保债权，超出200万转普通债权
- 税款50万→确认，税款债权（第113条第(二)项）
O3 结构化摘要（json）：total_amount_confirmed=15,650,000
