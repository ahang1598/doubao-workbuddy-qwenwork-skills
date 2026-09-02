# Example 001: 房地产企业重整计划草案

## 输入

```yaml
debtor: "XX房地产开发有限公司"
case_number: "（2026）粤03破申078号"
acceptance_date: "2026-06-01"
procedure_type: "reorganization"
confirmed_claims:
  secured: 50000000    # 土地抵押
  employee: 2000000    # 职工债权
  tax: 3000000         # 欠税
  ordinary: 80000000   # 普通债权
investor:
  name: "XX投资集团"
  investment: 30000000  # 3亿
strategy: "引入战略投资人+续建未完工楼盘+部分债转股"
liquidation_rate: "12.5%"
```

## 预期输出

O1 重整计划草案（docx，lawyer_draft范式）：
- 论证7个主题：经营方案（续建+销售）/债权调整（担保50M全额/职工2M全额/税款3M全额/普通80M→40%清偿+60%债转股）/清偿方案（投资人3亿+销售回款+资产处置）/清算地板（重整40% vs 清算12.5%）/出资人权益调整（原股东让渡70%股权给投资人）/执行监督（3年执行期）

O2 债权调整与清偿对照表（csv）：各类债权调整前后对照
O3 结构化草案摘要（json）：含liquidation_floor_test
