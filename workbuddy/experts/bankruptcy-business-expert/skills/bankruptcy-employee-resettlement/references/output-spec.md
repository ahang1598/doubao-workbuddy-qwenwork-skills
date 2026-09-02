# 破产职工安置 — 输出规格

## §1 写作红线

| # | 红线 | 违反后果 |
|---|------|----------|
| R1 | 禁止违规解除特殊职工（孕期/工伤/医疗期） | 阻断 |
| R2 | 禁止经济补偿计算错误（基数/年限/封顶） | 阻断 |
| R3 | 禁止社保欠缴金额漏算 | 阻断 |
| R4 | 禁止安置方案无资金来源 | 阻断 |
| R5 | 禁止群体风险评估缺失 | 阻断 |
| R6 | 禁止承诺安置方案必然通过 | 阻断 |

---

## §2 format_capabilities 格式能力声明

```yaml
format_capabilities:
  - format: docx
    scenarios: [正式文书, 职工债权审查表, 安置方案, 职工代表大会材料]
    seriousness: C-Professional
    structure_source: rule/format-docx/types/bankruptcy/T-asset-status-report.md
  - format: xlsx
    scenarios: [经济补偿测算表, 社保欠缴明细表]
    seriousness: I-Practical
```

---

## O1: 职工债权审查表（docx，必须）
欠薪/欠缴社保/经济补偿/医疗费/伤残补助/抚恤金/住房公积金逐项审查。逐人逐项列明债权金额和审查结论（确认/部分确认/不予确认+理由）。

## O2: 经济补偿测算表（xlsx，必须）
逐人计算：姓名/工龄/月平均工资/补偿基数/封顶适用/补偿月数/补偿金额。汇总：总人数/总金额/平均补偿额。

## O3: 职工安置方案（docx，必须）
含：安置方式（解除/留用/转移）/费用测算/资金来源/时间安排/社保转移方案/档案移交方案/失业保险申领指导/群体风险防控措施。

## O4: 职工代表大会材料（docx，条件必须）
会议通知/议程/方案说明要点/表决票模板。仅当需要召开职工代表大会时产出。

---

## DOCX 排版规格

### 1. 格式严肃度
C-Professional（安置方案/审查表）；I-Practical（职工代表大会材料）

### 2. 结构权威来源
`rule/format-docx/types/bankruptcy/T-asset-status-report.md`（审查表）
`rule/format-docx/types/bankruptcy/T-creditor-meeting-notice.md`（职工代表大会材料）

### 3. 页面布局
继承 `families/bankruptcy/spec.md` C-Professional 标准

### 4. 字体字号矩阵
- 文书标题：黑体、三号（16pt）、加粗、居中
- 正文：宋体、小四号（12pt）
- 一级标题：黑体、四号（14pt）
- 表格内容：宋体、五号（10.5pt）
- 表头：宋体、五号（10.5pt）、加粗、居中

### 5. 段落间距
行距1.5倍，首行缩进2字符

### 6. 禁止事项
| 排版禁止项 |
|-----------|
| 职工个人信息未脱敏（对外材料须隐去身份证号） |
| 安置方案缺少群体风险防控章节 |
| 经济补偿测算表缺少封顶适用标注 |
| 安置方案缺少资金来源说明 |
