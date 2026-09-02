# 破产成果校验 — 输出规格

## 目录
- §1 写作红线
- §2 format_capabilities 格式能力声明
- O1-O2 输出制品定义
- DOCX 排版规格

---

## §1 写作红线

| # | 红线 | 违反后果 |
|---|------|----------|
| R1 | 禁止放过金额矛盾 | 阻断 |
| R2 | 禁止照抄审查/计算阶段表述充当独立复核 | 阻断 |
| R3 | 禁止放行结果承诺/越权定性/法域误用 | 阻断 |
| R4 | 禁止声称已修复问题 | 阻断 |
| R5 | 禁止遗漏法定必含章节检查 | 阻断 |
| R6 | 禁止将待核查依据放行不标注 | 阻断 |
| R7 | 校验结论未回溯到具体位置 | 警告 |

---

## §2 format_capabilities 格式能力声明

```yaml
format_capabilities:
  - format: docx
    scenarios: [正式文书, 校验报告]
    seriousness: C-Professional
    structure_source: rule/format-docx/families/opinion/spec.md  # 借用 opinion 族
  - format: html
    scenarios: [结构化表格, 会话内展示, 打印PDF]
  - format: json
    scenarios: [机读中间产物, 门禁判断]
```

---

## O1: 成果校验报告（docx，必须）

结构：可交付判断→意图达成结论→阻断问题→需修改项→待律师/管理人确认项→金额与优先级核验→法条引用核验→程序合规检查→已通过检查。

问题分级：
- **阻断**：不可交付，须退回对应阶段修复
- **需修改**：交付前必须修正
- **待确认**：需律师专业判断或管理人决定

## O2: 结构化校验记录（json，必须）

```json
{
  "meta": {"verification_date":"","deliverables_count":0,"report_type":""},
  "intent_alignment": {"status":"achieved|partial|not_achieved","gaps":[]},
  "blocking_issues": [{"issue":"","location":"","severity":"blocking","recommendation":""}],
  "modification_needed": [{"issue":"","location":"","recommendation":""}],
  "pending_confirmation": [{"item":"","reason":"","assignee":"lawyer|manager"}],
  "amount_verification": {"consistent":true,"discrepancies":[]},
  "priority_verification": {"consistent":true,"discrepancies":[]},
  "legal_citation_verification": {"accurate":true,"issues":[]},
  "procedural_compliance": {"compliant":true,"issues":[]},
  "deliverable_status": "deliverable|needs_modification|not_deliverable"
}
```

---

## DOCX 排版规格

### 1. 格式严肃度
C-Professional（客户级专业成果，内部质量校验报告）

### 2. 结构权威来源
校验报告属分析性文书，借用 `rule/format-docx/families/opinion/spec.md`（意见书族）C-Professional 排版规范。

### 3. 页面布局
- 纸张：A4 纵向
- 页边距：上2.5cm / 下2.0cm / 左2.8cm / 右2.6cm

### 4. 字体字号矩阵
- 文书标题：黑体、三号（16pt）、加粗、居中
- 正文：宋体、小四号（12pt）
- 一级标题：黑体、四号（14pt）
- 问题标注：阻断项加粗+红色、需修改加粗+橙色

### 5. 段落间距参数表
- 行距：1.5 倍行距
- 首行缩进：2 字符

### 6. 编号规则
问题按 severity 分组编号：B-01/B-02（阻断）、M-01/M-02（需修改）、C-01/C-02（待确认）。

### 7. 偏离声明
不设封面/目录/免责声明。

### 8. python-docx 渲染指令
LLM 直接生成 docx 内容（script_necessity=none），不含脚本渲染。

### 9. 禁止事项
| 排版禁止项 |
|-----------|
| 阻断项/需修改项/待确认项混淆 |
| 问题未回溯到具体文件和位置 |
| 金额核对无交叉比对过程 |
| 结论与明细不一致 |

### 10. 内容结构
校验报告九段式：可交付判断→意图达成→阻断问题→需修改项→待确认项→金额核验→法条核验→程序合规→已通过检查。
