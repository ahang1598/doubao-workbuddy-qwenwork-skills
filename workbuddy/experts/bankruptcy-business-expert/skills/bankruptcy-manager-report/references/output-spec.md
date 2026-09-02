# 管理人报告编制 — 输出规格

## 目录
- §1 写作红线
- §2 报告类型与法定章节清单
- §3 format_capabilities 格式能力声明
- O1-O2 输出制品定义
- DOCX 排版规格

---

## §1 写作红线

| # | 红线 | 违反后果 |
|---|------|----------|
| R1 | 禁止遗漏法定必含章节 | 阻断 |
| R2 | 禁止数据与前序阶段成果矛盾 | 阻断 |
| R3 | 禁止虚构案件信息或数据 | 阻断 |
| R4 | 禁止空白章节或裸占位 | 阻断 |
| R5 | 禁止替代管理人签名或盖章 | 阻断 |
| R6 | 数据未标注来源 | 警告 |

---

## §2 报告类型与法定章节清单

> R1"禁止遗漏法定必含章节"的法定章节定义，LLM 生成时须逐项对照。

### 接管报告（企业破产法第25条）

| 章节 | 内容要素 |
|------|---------|
| ①接管时间 | 法院指定管理人日期/实际接管日期 |
| ②接管范围 | 印章证照/账簿文书/财产/营业事务 |
| ③交接状态 | 已接管/未接管及原因 |
| ④未接管财产 | 未接管财产清单及追收计划 |
| ⑤接管障碍 | 交接障碍及解决措施 |

### 财产状况报告（企业破产法第25条）

| 章节 | 内容要素 |
|------|---------|
| ①接管情况 | 接管时间/范围/交接状态/未接管财产及原因 |
| ②财产清查 | 货币资金/应收账款/存货/固定资产/无形资产/对外投资/其他 |
| ③负债情况 | 已知债权人清单/债权申报情况/或有负债 |
| ④财产评估 | 评估方法/评估结论/估值说明 |
| ⑤追收情况 | 已追收财产/待追收财产/追收障碍分析 |
| ⑥其他事项 | 未决诉讼/关联交易/担保物情况 |

### 履职报告（企业破产法第25条、第69条）

| 章节 | 内容要素 |
|------|---------|
| ①接管工作 | 范围/时间节点/障碍及解决 |
| ②调查工作 | 债务人财产/经营/关联方调查方法及发现 |
| ③债权审查 | 审查方法/进度/结果/异议处理 |
| ④债权人会议 | 召集情况/议题/表决结果/决议执行 |
| ⑤财产管理/处分 | 管理措施/处分决定/法院许可 |
| ⑥合规与信息披露 | 利益冲突/关联关系声明/重大事项（§69） |

### 分配方案报告（企业破产法第115条）

| 章节 | 内容要素 |
|------|---------|
| ①方案依据 | 法定分配依据+可供分配财产范围说明 |
| ②分配安排 | 各顺序分配金额/比例/方式/时间（对应第115条第2款） |
| ③提存与预留 | 提存金额/原因/后续处理方案 |
| ④剩余财产处理 | 剩余财产去向/处置方式 |
| ⑤后续工作与说明 | 实施分配的方法/账户与档案安排 |

---

## §3 format_capabilities 格式能力声明

```yaml
format_capabilities:
  - format: docx
    scenarios: [正式文书, 法院提交, 管理人报告]
    seriousness: C-Professional
    structure_source: rule/format-docx/types/bankruptcy/T-manager-duty-report.md
  - format: html
    scenarios: [结构化表格, 会话内展示, 打印PDF]
    constraints:
      - 内联样式铁律（§17.18.3）
      - 禁止 HARD_BLOCK / 外部 CSS
      - 含 @media print 适配
  - format: json
    scenarios: [机读中间产物, 数据校验]
```

---

## O1: 管理人报告（docx，必须）

按报告类型输出对应法定章节（§2 法定章节清单）。

格式：C-Professional，结构来源 type card `T-manager-duty-report.md`。

## O2: 报告数据核对表（json，必须）

```json
{
  "meta": {"report_type":"","case_id":"","report_date":""},
  "input": {
    "allocation_plan": {},
    "source": "distribution-calc O3"
  },
  "data_consistency": [
    {"item":"债务人名称","source":"case_info","value":"","consistent":true},
    {"item":"债权总额","source":"claim-review / summary.total_amount_confirmed","value":"","consistent":true},
    {"item":"可供分配财产","source":"asset-investigation / meta.total_assets_estimated","value":"","consistent":true}
  ],
  "chapter_completeness": [
    {"chapter":"","required":true,"present":true,"content_filled":true}
  ]
}
```

---

## DOCX 排版规格

### 1. 格式严肃度
C-Professional（客户级专业成果，管理人向法院/债权人会议提交）

### 2. 结构权威来源
`rule/format-docx/types/bankruptcy/T-manager-duty-report.md`

### 3. 页面布局
继承 `families/bankruptcy/spec.md`：
- 纸张：A4 纵向
- 页边距：上2.5cm / 下2.0cm / 左2.8cm / 右2.6cm
- 正式报告建议含封面页

### 4. 字体字号矩阵
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

### 6. 编号规则
四级编号：一、（一）、1.、（1）——论证性报告允许最深四层。

### 7. 偏离声明
参考 T-manager-duty-report 类型卡覆盖项（三类型路由/报告期间标注/封面建议包含）。

### 8. python-docx 渲染指令
LLM 直接生成 docx 内容（script_necessity=none），不含脚本渲染。

### 9. 禁止事项
| 排版禁止项 |
|-----------|
| 报告类型错误（财产状况报告/履职报告/分配方案报告混淆） |
| 遗漏法定必含章节（各类报告章节清单见§2） |
| 财产状况报告未区分接管财产与未接管财产 |
| 履职报告未披露关联关系和利益冲突 |
| 使用 word-document-processing 遗留引用（已废除） |
| 落款缺少管理人公章位置 |

### 10. 内容结构
详见 T-manager-duty-report 类型卡"内容骨架"（三类报告各有论证主题清单；lawyer_draft 范式）。
