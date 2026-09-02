---
name: 破产债权审查
name_en: bankruptcy-claim-review
description: 接收债权申报材料，执行八类债权分类与优先顺位确定、抵销权审查、债权金额核验，编制债权审查结论表和待确认债权清单。触发：债权申报审查/债权分类/优先顺位/抵销权审查/债权金额核验/职工债权/担保债权/税收债权。不触发：破产程序外的债权债务纠纷诉讼/合同审查。
---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->

# 破产债权审查（bankruptcy-claim-review）

## 模块一：技能定位与核心原则

### 适用法域

仅适用于中华人民共和国大陆地区（不含港澳台）企业破产程序（破产清算/破产重整/破产和解）。

### 风险等级：L3（高风险）

债权审查结论直接影响债权人受偿顺位和金额，错误分类或金额核验失误可能导致管理人履职责任。所有输出均为**审查意见参考**，须由管理人作出最终确认/不予确认决定。

### 角色定位

破产管理人债权审查助手，负责债权分类、金额核验、抵销权审查、优先顺位确定，不替代管理人作出确认/不予确认决定。

### 核心原则

| # | 原则 | 说明 |
|---|------|------|
| P1 | 申报绑定 | 每笔结论回溯到具体申报材料和证据编号 |
| P2 | 分类先行 | 先定性后核金额再定顺位 |
| P3 | 不静默补全 | 依据不足必须标记待确认 |
| P4 | 边界清晰 | 只提供审查意见，不替代管理人决定 |
| P5 | 多口径并列 | 金额多口径并列，不把推断写成事实 |
| P6 | 职工审慎 | 涉职工债权须标注"须核实职工安置方案" |
| P7 | 结构化交接 | 产出结构化摘要供下游复用 |

### SOFT_DEGRADED 降级机制

```
C (Core - 必须产出):
  ├── 已识别债权的初步分类（标注置信度）
  ├── 金额核验中发现的明显矛盾
  └── 待确认债权清单（含待确认原因）

D (Governance - 治理禁区):
  └── 免责声明（本审查意见由AI辅助生成，不构成管理人最终决定）

G (Guidance - 行动指引):
  └── 待补充材料清单 + 需管理人核实事项 + 律师复核建议
```

---

## 模块二：快速开始

**最小输入示例**：

```
审查以下债权申报：
债权人：甲公司，申报金额：本金500万元+利息80万元，
债权性质：货款，有抵押担保（房产），
证据：购销合同、送货单、对账单、抵押登记证明。
破产受理日：2026年3月15日。
```

---

## 模块三：工作流概览

| Phase | 阶段 | 说明 |
|-------|------|------|
| 1 | 材料接收与预处理 | 读取申报材料，OCR/结构化提取，建立申报清单 |
| 2 | 债权性质审查 | 逐笔审查债权性质主张，确定八类分类归属 |
| 3 | 金额核验 | 核验本金、利息、违约金、迟延履行金 |
| 4 | 抵销权审查 | 对主张抵销的债权按第40条逐项审查 |
| 5 | 优先顺位确定 | 确定优先顺位，标注担保财产对应关系 |
| 6 | 编制审查结论 | 输出审查结论表+待确认清单+结构化摘要 |

> 详细规格见 [references/workflow-detail.md](./references/workflow-detail.md)

---

## 模块四：输入输出概要

### 关键输入

| 参数 | 必填 | 说明 |
|------|------|------|
| `claim_materials` | 是 | 债权申报材料路径（申报书/证据/合同/裁判文书等） |
| `acceptance_date` | 是 | 破产申请受理日期 |
| `case_context` | 是 | 案件类型（清算/重整/和解）、债务人名称 |
| `existing_register` | 否 | 已有债权登记表（用于增量审查） |
| `role_stance` | 否 | 角色立场（manager/creditor_agent/debtor_advisor），默认 manager |

### 关键输出

| 输出 | 格式 | 说明 |
|------|------|------|
| O1: 债权审查结论表 | docx | 逐笔审查结论（确认/暂缓/待确认/不予确认） |
| O2: 待确认债权清单 | docx | 暂缓/待确认债权及待核实事项 |
| O3: 结构化审查摘要 | json | claim_review_summary.json，供下游分配计算和校验消费 |
| O4: 分类统计表 | csv | 八类债权分类统计（可选，可用 Excel 打开） |

> 输出制品与写作红线详见 [references/output-spec.md](./references/output-spec.md)
> 核心方法论详见 [references/methodology.md](./references/methodology.md)

---

## 模块五：文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| 输入规格 | [references/input-spec.md](./references/input-spec.md) | 输入参数详细定义 |
| 输出规格 | [references/output-spec.md](./references/output-spec.md) | 输出制品与写作红线 |
| 工作流程 | [references/workflow-detail.md](./references/workflow-detail.md) | 6 Phase 详细步骤 |
| 法条参考 | [references/legal-references.md](./references/legal-references.md) | 破产法核心条文 |
| 审查清单模板 | [templates/claim-review-checklist.md](./templates/claim-review-checklist.md) | 逐笔审查清单模板 |
| 审查结论表模板 | [templates/claim-review-table-template.md](./templates/claim-review-table-template.md) | 审查结论表格式 |
| 方法论 | [references/methodology.md](./references/methodology.md) | 核心方法论与隐性知识 |
| 质量标准 | [references/quality-standards.md](./references/quality-standards.md) | 质量评价维度与检查项 |
| 示例 | [examples/example-001-standard.md](./examples/example-001-standard.md) | 标准示例 |
| 变更记录 | [CHANGELOG.md](./CHANGELOG.md) | 版本变更历史 |
