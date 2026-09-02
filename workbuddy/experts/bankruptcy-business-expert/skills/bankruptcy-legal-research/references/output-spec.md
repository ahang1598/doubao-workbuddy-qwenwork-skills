# 破产法律研究 — 输出规格

## 目录
- §1 写作红线
- §2 format_capabilities 格式能力声明
- O1-O2 输出制品定义
- DOCX 排版规格

---

## §1 写作红线

| # | 红线 | 违反后果 |
|---|------|----------|
| R1 | 禁止编造法条号/案号/施行日期 | 阻断 |
| R2 | 禁止引用已失效条文不标注 | 阻断 |
| R3 | 禁止将类案倾向表述为本案必然结果 | 阻断 |
| R4 | 禁止将待核查依据表述为确定结论 | 阻断 |
| R5 | 禁止承诺裁判结果 | 阻断 |
| R6 | 援引司法解释未标文号和施行日期 | 警告 |
| R7 | 案例未标注效力层级 | 警告 |

---

## §2 format_capabilities 格式能力声明

```yaml
format_capabilities:
  - format: docx
    scenarios: [正式文书, 法律分析报告]
    seriousness: C-Professional
    structure_source: rule/format-docx/families/opinion/spec.md  # 借用 opinion 族，无破产专属类型卡
  - format: html
    scenarios: [结构化表格, 会话内展示, 打印PDF]
  - format: json
    scenarios: [机读中间产物]
```

---

## O1: 法律分析报告（docx，必须）
结构：法律争点→构成要件分析（对照表）→适用法条（标注施行状态）→类案与裁判倾向（如有）→法律认定意见→风险提示。

## O2: 结构化研究摘要（json，必须）

```json
{
  "meta": {"research_question":"","research_date":"","depth":""},
  "issues": [{"issue":"","elements":[{"element":"","facts":"","satisfied":true,"basis":""}]}],
  "legal_basis": [{"provision":"","name":"","status":"current|amended|repealed|pending","source":""}],
  "case_tendency": [{"case_no":"","court":"","level":"guiding|reference|general","tendency":""}],
  "opinion": "",
  "risk_notes": [],
  "pending_verification": []
}
```

---

## DOCX 排版规格

### 1. 格式严肃度
C-Professional（客户级专业成果，法律分析意见）

### 2. 结构权威来源
法律研究属分析性文书，无破产专属类型卡，借用 `rule/format-docx/families/opinion/spec.md`（意见书族）排版规范。

### 3. 页面布局
继承 opinion 族 C-Professional 标准：
- 纸张：A4 纵向
- 页边距：上2.5cm / 下2.0cm / 左2.8cm / 右2.6cm

### 4. 字体字号矩阵
- 文书标题：黑体、三号（16pt）、加粗、居中
- 正文：宋体、小四号（12pt）
- 一级标题：黑体、四号（14pt）
- 二级标题：宋体、小四号（12pt）、加粗

### 5. 段落间距参数表
- 行距：1.5 倍行距
- 首行缩进：2 字符
- 段前段后：0 pt

### 6. 编号规则
四级编号：一、（一）、1.、（1）

### 7. 偏离声明
借用 opinion 族 C-Professional 规格，不设封面/目录。

### 8. python-docx 渲染指令
LLM 直接生成 docx 内容（script_necessity=none），不含脚本渲染。

### 9. 禁止事项
| 排版禁止项 |
|-----------|
| 法条引用未用《》包裹 |
| 案例引用未标注案号和法院 |
| 使用"保证""一定"等绝对化表述 |
| 出具日期不准确 |

### 10. 内容结构
法律分析报告五段式：法律争点→构成要件分析→适用法条→类案倾向→认定意见+风险提示。
