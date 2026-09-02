# 破产债权审查 — 输出规格

## 目录
- §1 写作红线
- §2 format_capabilities 格式能力声明
- O1-O4 输出制品定义
- DOCX 排版规格

---

## §1 写作红线

| # | 红线 | 违反后果 |
|---|------|----------|
| R1 | 禁止虚构债权人/金额/日期/证据 | 阻断 |
| R2 | 禁止替代管理人作出确认/不予确认决定 | 阻断 |
| R3 | 禁止仅给结论不给依据 | 阻断 |
| R4 | 禁止遗漏抵销权审查结论 | 阻断 |
| R5 | 禁止将待确认债权表述为已确认 | 阻断 |
| R6 | 禁止改写申报金额或证据原文 | 阻断 |
| R7 | OCR低置信内容未标注核对建议 | 警告 |
| R8 | 利息计算未列明公式和基数 | 警告 |

---

## §2 format_capabilities 格式能力声明

```yaml
format_capabilities:
  - format: docx
    scenarios: [正式文书, 法院提交, 债权人会议附件]
    seriousness: C-Professional
    structure_source: rule/format-docx/types/bankruptcy/T-claim-review-table.md
  - format: html
    scenarios: [结构化表格, 条件格式底色, 会话内展示, 打印PDF]
    constraints:
      - 内联样式铁律（§17.18.3）
      - 禁止 HARD_BLOCK / 外部 CSS
      - 含 @media print 适配
  - format: csv
    scenarios: [表格数据, Excel兼容]
    encoding: UTF-8 BOM
  - format: json
    scenarios: [机读中间产物, 下游技能消费（distribution-calc / manager-report / creditor-meeting）]
```

---

## O1: 债权审查结论表（docx，必须）

### 结构

```
第一部分：申报概况
  - 申报总数/申报总金额/申报期间
  - 材料完整性统计

第二部分：审查结论表
  - 确认债权（按顺位分组，浅绿色底色）
    - 表格：申报编号/债权人/申报金额/确认金额/差异/审查结论/法条依据
  - 暂缓确认债权（浅黄色底色）
    - 表格：同上+暂缓原因
  - 不予确认债权（浅红色底色）
    - 表格：同上+不予确认理由

第三部分：分类统计
  - 分类统计表（八类顺位+别除权笔数和金额统计）

第四部分：抵销权审查结论
  - 抵销权主张清单和审查结论

第五部分：待确认债权清单
  - 集中列出全部待确认/暂缓债权及待核实事项
```

### 格式要求
- 格式严肃度：C-Professional
- 结构来源：rule/format-docx/types/bankruptcy/T-claim-review-table.md
- 分组底色：确认=浅绿(#E8F5E9) / 暂缓=浅黄(#FFF9C4) / 不予确认=浅红(#FFEBEE)
- 金额列：右对齐、千分位、保留两位小数
- 免责声明在首部（前500字内）

## O2: 待确认债权清单（docx，必须）

### 结构

```
按待确认原因分组：
  - 金额争议（附各方主张和依据）
  - 性质争议（附各方主张和依据）
  - 证据不足（附待补充证据清单）
  - 需管理人核实（附待核实事项）
  - 诉讼仲裁未决（附案件信息）
```

## O3: 结构化审查摘要（json，必须）

### claim_review_summary.json

```json
{
  "meta": {
    "case_id": "案件ID",
    "acceptance_date": "受理日期",
    "review_date": "审查日期",
    "total_claims": 0,
    "total_amount_declared": 0,
    "total_amount_confirmed": 0
  },
  "summary": {
    "total_amount_confirmed": 0,
    "total_labor_claims": 0,
    "total_tax_claims": 0,
    "total_secured_claims": 0,
    "total_ordinary_claims": 0,
    "total_claims_count": 0,
    "review_date": ""
  },
  "claims": [
    {
      "claim_id": "BK-CLAIM-001",
      "creditor_name": "债权人名称",
      "claim_type": "八类顺位分类（别除权单列）",
      "priority_rank": 1-8,
      "amount_declared": 0,
      "amount_confirmed": 0,
      "review_conclusion": "confirmed|suspended|pending|rejected",
      "review_basis": "审查依据说明",
      "legal_basis": ["法条引用"],
      "offset_review": {
        "claimed": false,
        "conclusion": "allowed|denied|pending",
        "amount": 0,
        "reason": ""
      },
      "secured_property": {
        "property_id": "",
        "estimated_value": 0,
        "surplus_to_pool": 0,
        "shortfall_as_unsecured": 0
      },
      "pending_items": [],
      "confidence": "high|medium|low",
      "source_refs": []
    }
  ],
  "statistics": {
    "by_type": {},
    "by_conclusion": {}
  }
}
```

## O4: 分类统计表（csv，可选）

> 格式从 xlsx 降级为 csv（§17.17：LLM 无法直出二进制 xlsx，csv 可用 Excel 直接打开）。

### 内容

| Sheet/区块 | 内容 |
|---|---|
| 分类统计 | 八类债权笔数/申报金额/确认金额统计 |
| 顺位汇总 | 按优先顺位的金额汇总 |
| 确认明细 | 已确认债权逐笔明细 |
| 待确认明细 | 待确认债权逐笔明细 |

### 格式要求
- UTF-8 BOM 编码（Excel 兼容）
- 逗号分隔，首行为表头
- 数字右对齐（Excel 打开后设置）
- 待确认项可在单独区块标注

---

## DOCX 排版规格

### 1. 格式严肃度
C-Professional（客户级专业成果，管理人向法院/债权人会议提交）

### 2. 结构权威来源
`rule/format-docx/types/bankruptcy/T-claim-review-table.md`

### 3. 页面布局
继承 `families/bankruptcy/spec.md`：
- 纸张：A4 纵向
- 页边距：表格密集型文书可缩左右边距至2.0cm

### 4. 字体字号矩阵
- 文书标题：黑体、三号（16pt）、加粗、居中
- 正文：宋体、小四号（12pt）
- 一级标题：黑体、四号（14pt）
- 表格内容：宋体、五号（10.5pt）
- 表头：宋体、五号（10.5pt）、加粗、居中

### 5. 段落间距参数表
- 行距：1.5 倍行距
- 首行缩进：2 字符
- 表格内行距：单倍行距

### 6. 编号规则
表格行连续编号；分组标题使用"一、二、三、"。

### 7. 偏离声明
参考 T-claim-review-table 类型卡全部覆盖项（template_fill 范式、7列表格、三色分组底色）。

### 8. python-docx 渲染指令
LLM 直接生成 docx 内容（script_necessity=none），不含脚本渲染。

### 9. 禁止事项
| 排版禁止项 |
|-----------|
| 审查结论表缺少分组底色 |
| 金额未右对齐/未千分位 |
| 法条依据列为空 |
| 抵销权主张被忽略（如有） |
| 落款缺少管理人公章位置 |
| 使用 word-document-processing 遗留引用 |

### 10. 内容结构
详见 T-claim-review-table 类型卡"内容骨架"（template_fill 范式，固定结构模板：文书首部→审查说明段→主表7列→分组底色→抵销权审查→统计汇总）。
