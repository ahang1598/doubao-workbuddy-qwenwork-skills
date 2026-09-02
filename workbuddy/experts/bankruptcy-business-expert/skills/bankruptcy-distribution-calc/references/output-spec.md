# 破产分配计算 — 输出规格

## 目录
- §1 写作红线
- §2 format_capabilities 格式能力声明
- O1-O3 输出制品定义
- DOCX 排版规格

---

## §1 写作红线

| # | 红线 | 违反后果 |
|---|------|----------|
| R1 | 禁止使用未确认金额进行分配计算 | 阻断 |
| R2 | 禁止跳过顺位直接计算后顺位 | 阻断 |
| R3 | 禁止草案与测算表数据不一致 | 阻断 |
| R4 | 禁止仅给结果不给计算过程 | 阻断 |
| R5 | 禁止承诺清偿率不变或分配必然通过 | 阻断 |
| R6 | 禁止遗漏尾差处理说明 | 警告 |
| R7 | 清偿率精度不足四位小数 | 警告 |

---

## §2 format_capabilities 格式能力声明

```yaml
format_capabilities:
  - format: csv
    scenarios: [表格数据, Excel兼容]
    encoding: UTF-8 BOM
  - format: docx
    scenarios: [正式文书, 法院提交]
    seriousness: C-Professional
    structure_source: rule/format-docx/types/bankruptcy/T-distribution-plan.md
  - format: html
    scenarios: [结构化表格, 条件格式底色, 会话内展示, 打印PDF]
    constraints:
      - 内联样式铁律（§17.18.3）
      - 禁止 HARD_BLOCK / 外部 CSS
      - 含 @media print 适配
  - format: json
    scenarios: [机读中间产物, 下游技能消费（manager-report / creditor-meeting）]
```

---

## O1: 分配方案草案（docx，必须）

章节：可供分配财产总额→破产费用与共益债务→各顺位清偿计算→普通债权清偿率→逐笔清偿明细→分配方式与实施时间。每顺位列明债权总额/可供分配金额/清偿比例/清偿金额。

## O2: 清偿率测算表（csv，必须）

> 格式从 xlsx 降级为 csv（§17.17：LLM 无法直出二进制 xlsx，csv 可用 Excel 直接打开）。

表头：债权编号/债权人/债权性质/确认金额/清偿顺位/清偿比例/清偿金额。

### 格式要求
- UTF-8 BOM 编码（Excel 兼容）
- 逗号分隔，首行为表头
- 数字右对齐（Excel 打开后设置）
- 不足额项在单独区块标注

### Excel 格式建议（用户手动操作指南）
- 打开 csv 后在 Excel 中：①冻结首行；②金额列设为「会计数字格式」；③清偿率列设为百分比格式
- 建议将汇总表/明细表/破产费用表分为单独 Sheet（csv 单表限制，xlsx 可选升级）

## O3: 结构化分配底稿（json，必须）

```json
{
  "meta": {"case_id":"","calc_date":"","total_distributable":0,"currency":"CNY"},
  "expenses": {"bankruptcy_fees":0,"common_benefit_debts":0},
  "input": {
    "claims_total": 0,
    "labor_claims_total": 0,
    "tax_claims_total": 0,
    "secured_claims_total": 0,
    "ordinary_claims_total": 0,
    "total_distributable": 0,
    "claims_detail": [],
    "asset_realization": [],
    "source": "claim-review + asset-investigation"
  },
  "by_layer": {
    "layer0_property_offset": {
      "secured_claims": [{"claim_id":"","property_value":0,"disposal_cost":0,"allocated":0,"surplus_to_pool":0,"shortfall_as_unsecured":0}],
      "construction_priority": [{"claim_id":"","project_name":"","allocated":0}]
    },
    "layer1_immediate_payment": {
      "bankruptcy_fees": [{"item":"","amount":0}],
      "common_benefit_debts": [{"item":"","amount":0}],
      "total_fees": 0,
      "total_debts": 0
    },
    "layer2_statutory_priority": {
      "employee_claims": {"total":0,"allocated":0,"rate":"","note":"含养老/医疗个人账户"},
      "social_tax": {"total":0,"allocated":0,"rate":"","note":"社保统筹+税款"},
      "ordinary_claims": {"total":0,"available":0,"rate":"","items":[{"claim_id":"","creditor":"","confirmed_amount":0,"allocated_amount":0}]}
    }
  },
  "rounding_note": ""
}
```

---

## DOCX 排版规格

### 1. 格式严肃度
C-Professional（客户级专业成果，管理人向法院/债权人会议提交）

### 2. 结构权威来源
`rule/format-docx/types/bankruptcy/T-distribution-plan.md`

### 3. 页面布局
继承 `families/bankruptcy/spec.md`：
- 纸张：A4 纵向
- 页边距：上2.5cm / 下2.0cm / 左2.8cm / 右2.6cm

### 4. 字体字号矩阵
- 文书标题：黑体、三号（16pt）、加粗、居中
- 正文：宋体、小四号（12pt）
- 一级标题：黑体、四号（14pt）
- 表格内容：宋体、五号（10.5pt）
- 表头：宋体、五号（10.5pt）、加粗、居中

### 5. 段落间距参数表
- 行距：1.5 倍行距
- 表格内行距：单倍行距

### 6. 编号规则
分配明细表：连续编号；章节标题：一、二、三、；合计行加粗浅灰底色。

### 7. 偏离声明
参考 T-distribution-plan 类型卡覆盖项，允许封面页。

### 8. python-docx 渲染指令
LLM 直接生成 docx 内容（script_necessity=none），不含脚本渲染。

### 9. 禁止事项
| 排版禁止项 |
|-----------|
| 分配顺序违反企业破产法第113条 |
| 清偿率计算错误或无计算过程 |
| 破产费用/共益债务明细缺失 |
| 可供分配财产来源无明细 |
| 金额未右对齐/未千分位 |
| 落款缺少管理人公章位置 |

### 10. 内容结构
详见 T-distribution-plan 类型卡"内容骨架"（§5 论证主题：可供分配财产总额/参加分配债权范围/分配顺序合法性/分配执行方案/提存与预留）。
