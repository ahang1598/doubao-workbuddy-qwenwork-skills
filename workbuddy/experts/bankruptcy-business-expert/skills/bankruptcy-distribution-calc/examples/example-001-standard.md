# Example 001: 标准分配计算

## 输入

```yaml
case: "XX制造有限公司破产清算案"
total_distributable: 8000000
expenses:
  bankruptcy_fees: 500000
  common_benefit_debts: 200000
claims:
  employee_claims: 150000
  tax_claims: 500000
  secured_claims:
    - claim_id: "CLM-003"
      creditor: "某银行"
      property_value: 8000000
      confirmed_amount: 10000000
  ordinary_claims:
    total: 5000000
```

## 预期输出

O1 分配方案草案（docx）：
- 可供分配：800万 - 50万(破产费用) - 20万(共益债务) = 730万
- 职工债权15万→全额清偿
- 税款50万→全额清偿
- 担保债权→厂房800万清偿担保部分，超出200万转普通
- 普通债权：(500万+200万)=700万 / 可供(730-15-50-800→已不足)=负值→分配需重新计算

O2 清偿率测算表（csv）：逐笔清偿率
O3 结构化底稿（json）：含完整分配明细
