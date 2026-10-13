# 阶段三：加载方法论与构建检查表

> **你接收到的上游数据：** 阶段一产物 JSON（含 user_position, market_position, review_depth, special_concerns, file_format）。阶段二产物 JSON（可选；含 overall_risk_level, counterparty_risks, query_date, skipped_parties，本阶段不直接使用，透传至阶段四和阶段五）。
> **你需要产出的下游数据：** 阶段三产物 JSON（格式见 SKILL.md）。

---

## 步骤 1：加载基础参考文件

以下两个文件**每次审查必须加载**：

| 文件 | 用途 |
|------|------|
| [references/contract-types.md](../references/contract-types.md) | 识别合同类型，提取关键条款清单，含类型特征词表 |
| [references/review-methodology.md](../references/review-methodology.md) | 根据审核深度锁定审查范围和检查清单 |

以下两个通用增强文件按审核深度加载：

| 文件 | 加载条件 | 用途 |
|------|----------|------|
| `references/general-micro-review.md` | 标准/深度审核必加载；快速审核仅在用户明确要求文字校对、语病检查、金额日期核对时加载 | 错别字、语句不通、金额日期矛盾、条款引用错误、逻辑冲突等文本质量审查 |
| `references/general-structure-rules.md` | 标准/深度审核必加载；快速审核仅在用户关注签署、附件、主体完整性时加载 | 合同名称、首部主体、前言、签署栏、附件一致性审查 |

---

## 步骤 2：判定合同类型（特征词匹配法）

加载 `contract-types.md` 后，对当前合同进行类型判定。**使用特征词匹配，而非语义理解。**

### 判定流程（三个检查点依次执行，命中即停）

**检查点 A：是否明确匹配 17 类之一？**

使用 `references/contract-types.md` 中的"类型判定特征词表"，检查合同是否命中任一类型的特征词。

**命中规则：**
- 命中单一类型 → 记录为**情况一**，进入步骤 3
- 命中多个类型 → 若某类型特征词命中数明显最多，记录为**情况一**；若各类型命中数相近，进入检查点 B
- 无类型命中 → 进入检查点 B（进一步判断是否混合类型或无名合同）

**检查点 B：是否涉及两种以上有名合同类型且命中数相近？**

检查合同是否同时命中多个类型的特征词，且各类型命中数量相近：
- 是 → 记录为**情况二（混合类型）**，判定主合同类型和从合同类型（根据核心交易目的），进入步骤 3
- 否 → 进入检查点 C

**检查点 C：无法匹配任何类型**

记录为**情况三（无名合同）**，进入步骤 3

---

## 步骤 3：按类型加载专用参考文件

根据步骤 2 的判定结果，加载对应的风险模板和语言规范：

### 情况一（明确匹配）

加载以下文件（将 `[类型名]` 替换为实际匹配的合同类型）：

| 文件 | 说明 |
|------|------|
| `references/risk-templates/[类型名].md` | 该类型风险判定表 |
| `references/legal-language/通用规范.md` | 每次必加载 |
| `references/legal-language/批注模板.md` | 每次必加载（v3.8.0 新增） |
| `references/legal-language/[类型名].md` | 该类型语言规范 |
| `references/common-errors.md` | 常见错误预防（v3.8.0 新增） |

### 情况二（混合类型）

| 文件 | 说明 |
|------|------|
| `references/risk-templates/[主类型].md` | 主合同类型风险表 |
| `references/risk-templates/[从类型].md` | 从合同类型风险表 |
| `references/legal-language/通用规范.md` | 每次必加载 |
| `references/legal-language/批注模板.md` | 每次必加载 |
| `references/legal-language/[主类型].md` | 主类型语言规范 |
| `references/legal-language/[从类型].md` | 从类型语言规范 |
| `references/common-errors.md` | 常见错误预防 |

**合并规则：**
1. 合并两类关键条款为一张检查表，标注每项来源类型
2. 对重叠的风险项，取更严格的等级

### 情况三（无名合同）

| 文件 | 说明 |
|------|------|
| `references/risk-templates/通用.md` | 通用风险判定表 |
| `references/legal-language/通用规范.md` | 每次必加载 |
| `references/legal-language/批注模板.md` | 每次必加载 |
| `references/legal-language/通用合同条款.md` | 通用条款规范 |
| `references/common-errors.md` | 常见错误预防 |

以 `review-methodology.md` 的四层审核检查清单为主要审查框架。

---

## 步骤 4：按需加载管辖审查规则

检查合同是否包含争议解决/管辖条款。

| 条件 | 操作 |
|------|------|
| 合同包含争议解决/管辖条款 | 加载 `references/jurisdiction-review-rules.md` |
| 合同不包含 | 暂不加载（阶段三完整性核查发现缺失时再加载） |

---

## 步骤 5：构建内部检查表

综合以上加载的文件，构建内部检查表：

**步骤 5.1：提取关键条款清单**
从 `contract-types.md` 提取当前类型的"关键条款"清单，每项标记为"待检"

**步骤 5.2：锁定检查项范围**
从 `review-methodology.md` 根据审核深度锁定检查项范围：

| 审核深度 | 风险等级范围 | 条款类型范围 |
|---------|-------------|-------------|
| 快速 | 致命风险、重要风险 | 标的、价款、违约责任、解除条款 |
| 标准 | 致命风险、重要风险、一般风险；并覆盖影响理解、履行、证据和专业度的文字质量问题 | 标的、数量质量、价款、履行、违约责任、解除终止、不可抗力、担保保险、争议解决、首尾附件、关键逻辑一致性 |
| 深度 | 全部等级 | 所有条款；包含标准审核全部内容，并展开轻微瑕疵、格式统一和表达精修 |

**步骤 5.3：添加特殊关注点**
如有用户特殊关注点，添加为最高优先级检查项

**步骤 5.4：添加通用增强检查项**
根据审核深度将通用增强文件纳入 `loaded_references`：

| 审核深度 | 通用增强检查项 |
|----------|----------------|
| 快速 | 默认不加入；用户特别关注文字质量、签署或附件时加入对应文件 |
| 标准 | 加入 `general-micro-review.md`、`general-structure-rules.md` |
| 深度 | 加入 `general-micro-review.md`、`general-structure-rules.md`，并允许输出轻微瑕疵和格式统一问题 |

加入后，在内部检查表中追加：
- 文本质量：错别字、语句不通、金额日期冲突、条款引用错误、主体简称混用、权利义务矛盾
- 首尾附件：合同名称与实质、首部主体、授权代表、前言、签署栏、附件列明/缺失/冲突/优先顺序

---

## 步骤 6：整理阶段三产物

```json
{
  "contract_type": "买卖合同",
  "type_scenario": "情况一",
  "primary_type": null,
  "secondary_type": null,
  "checklist": ["标的", "数量", "质量", "价款", "履行时间地点方式", "验收", "违约责任"],
  "review_scope": "根据审核深度确定的检查范围描述",
  "fallback_flag": null,
  "loaded_references": [
    "references/contract-types.md",
    "references/review-methodology.md",
    "references/risk-templates/买卖合同.md",
    "references/general-micro-review.md",
    "references/general-structure-rules.md",
    "references/legal-language/通用规范.md",
    "references/legal-language/批注模板.md",
    "references/legal-language/买卖合同.md",
    "references/common-errors.md"
  ]
}
```

**字段说明：**
- `fallback_flag`：情况一填 `null`；情况二填 `"混合类型"`；情况三填 `"无名合同"`
- `primary_type` / `secondary_type`：仅情况二需要填写
