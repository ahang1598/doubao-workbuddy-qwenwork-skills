# 破产资产调查与追收 — 输出规格

## 目录
- §1 写作红线
- §2 format_capabilities 格式能力声明
- O1-O4 输出制品定义
- DOCX 排版规格

---

## §1 写作红线

| # | 红线 | 违反后果 |
|---|------|----------|
| R1 | 禁止虚构财产线索/流水记录/关联关系 | 阻断 |
| R2 | 禁止替代管理人决定追收/评估/处置 | 阻断 |
| R3 | 禁止遗漏第31/32/33条分类标注 | 阻断 |
| R4 | 禁止将待核实线索表述为已查证事实 | 阻断 |
| R5 | 禁止改写银行流水金额/日期/交易对手 | 阻断 |
| R6 | 禁止遗漏犯罪线索报告 | 阻断 |
| R7 | 估值未标注评估方法和数据来源 | 警告 |
| R8 | 关联交易未标注关联关系类型 | 警告 |

---

## §2 format_capabilities 格式能力声明

```yaml
format_capabilities:
  - format: docx
    scenarios: [正式文书, 法院提交, 管理人报告]
    seriousness: C-Professional
    structure_source: rule/format-docx/types/bankruptcy/T-asset-status-report.md
  - format: html
    scenarios: [结构化表格, 会话内展示, 打印PDF]
  - format: markdown
    scenarios: [纯文本摘要, 会话内展示]
  - format: json
    scenarios: [机读中间产物, 下游技能消费（distribution-calc / manager-report）]
```

---

## O1: 接管清单（docx，必须）
按7类财产分组，每项标注：财产编号/名称/类型/接管状态/权属/估值/来源/核实状态。

## O2: 财产状况报告（docx，必须）
章节：资产清查→负债情况→所有者权益→财产追收情况→财产评估与变现方案。

## O3: 追收线索清单（docx，必须）
每条线索：编号/行为类型(第31/32/33条)/时间/金额/对手/关联关系/证据来源/核实状态/追收方向/初步依据。

## O4: 结构化资产摘要（json，必须）

```json
{
  "meta": {"case_id":"","acceptance_date":"","total_assets_estimated":0,"total_recovery_clues":0},
  "assets": [{"asset_id":"","type":"","name":"","status":"takeover|pending|verify|recovery","estimated_value":0,"confidence":"high|medium|low"}],
  "recovery_clues": [{"clue_id":"","type":"art31|art32|art33","date":"","amount":0,"counterparty":"","relationship":"","evidence":"","verify_status":"verified|pending","recovery_direction":""}]
}
```

---

## DOCX 排版规格

### 1. 格式严肃度
C-Professional（客户级专业成果，管理人向法院/债权人会议提交）

### 2. 结构权威来源
`rule/format-docx/types/bankruptcy/T-asset-status-report.md`

### 3. 页面布局
继承 `families/bankruptcy/spec.md`：
- 纸张：A4 纵向
- 页边距：上2.5cm / 下2.0cm / 左2.8cm / 右2.6cm

### 4. 字体字号矩阵
继承 bankruptc族 + T-asset-status-report 覆盖：
- 文书标题：黑体、三号（16pt）、加粗、居中
- 正文：宋体、小四号（12pt）
- 一级标题：黑体、四号（14pt）
- 二级标题：宋体、小四号（12pt）、加粗
- 表格内容：宋体、五号（10.5pt）
- 表头：宋体、五号（10.5pt）、加粗、居中

### 5. 段落间距参数表
- 行距：1.5 倍行距
- 首行缩进：2 字符
- 段前段后：0 pt
- 表格内行距：单倍行距

### 6. 编号规则
四级编号体系：一、（一）、1.、（1）

### 7. 偏离声明
参考 T-asset-status-report 类型卡全部覆盖项，无额外偏离。

### 8. python-docx 渲染指令
LLM 直接生成 docx 内容（script_necessity=none），不含脚本渲染。

### 9. 禁止事项
| 排版禁止项 |
|-----------|
| 金额未右对齐/未千分位 |
| 表头行不重复（每页顶部须重复） |
| 财产类别无区分底色 |
| 落款缺少管理人公章位置 |
| 估值未标注评估方法和数据来源 |

### 10. 内容结构
详见 T-asset-status-report 类型卡"内容骨架"（§5 论证主题：接管说明/财产清查/负债评估/追收障碍/其他事项 + C-table-asset-summary 6 列表格）。
