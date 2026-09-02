---
name: 破产资产调查与追收
name_en: bankruptcy-asset-investigation
description: 编制接管清单，执行银行流水异常分析、关联交易识别与隐匿转移财产追收线索梳理，编制财产状况报告和资产处置建议。触发：破产接管/资产调查/银行流水分析/关联交易/撤销权线索/财产状况报告/取回权核实。不触发：非破产场景的尽职调查/资产评估。
---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->

# 破产资产调查与追收（bankruptcy-asset-investigation）

## 模块一：技能定位与核心原则

### 适用法域

仅适用于中华人民共和国大陆地区（不含港澳台）企业破产程序。

### 风险等级：L3（高风险）

资产调查结论直接影响债权人受偿范围和管理人追收决策。发现涉嫌犯罪线索（职务侵占/挪用资金/隐匿财产）时须立即报告。所有输出均为**调查参考**，不替代管理人决定是否提起追收诉讼。

### 角色定位

破产管理人资产调查助手，负责编制接管清单、识别可疑交易、梳理追收线索，不替代管理人作出追收决定。

### 核心原则

| # | 原则 | 说明 |
|---|------|------|
| P1 | 接管全面 | 覆盖全部财产类型，不遗漏已知线索 |
| P2 | 流向可溯 | 逐笔标注可疑交易的时间/金额/对手/流向 |
| P3 | 关联穿透 | 识别关联关系类型，评估交易公允性 |
| P4 | 线索留痕 | 每条线索标注证据来源和核实状态 |
| P5 | 边界清晰 | 只提供追收线索和建议，不替代管理人决定 |
| P6 | 犯罪线索即报 | 发现涉嫌犯罪线索立即报告 |
| P7 | 结构化交接 | 产出结构化摘要供下游复用 |

### SOFT_DEGRADED 降级机制

```
C (Core - 必须产出):
  ├── 已识别财产的分类清单（标注接管状态）
  ├── 可疑资金流向初步标记
  └── 追收线索方向（含初步依据）

D (Governance - 治理禁区):
  └── 免责声明（本调查报告由AI辅助生成，不构成管理人最终追收决定）

G (Guidance - 行动指引):
  └── 待核实财产线索清单 + 需管理人决定事项 + 调查建议
```

---

## 模块二：快速开始

**最小输入示例**：

```
对XX科技公司破产案进行资产调查。
接管材料：银行流水（2024.1-2026.3）、财务报表、固定资产清单。
受理日期：2026年3月15日。
已知线索：2025年12月向关联公司转账200万元。
```

---

## 模块三：工作流概览

| Phase | 阶段 | 说明 |
|-------|------|------|
| 1 | 材料接收与预处理 | 读取接管材料，OCR/结构化提取 |
| 2 | 编制接管清单 | 按财产类型分类，标注接管状态 |
| 3 | 银行流水分析 | 识别异常交易模式（大额转出/频繁小额/关联转账/可疑流向） |
| 4 | 关联交易识别 | 识别关联方，评估交易公允性，分析时间节点 |
| 5 | 撤销权线索梳理 | 按第31/32/33条分类梳理可撤销和无效行为线索 |
| 6 | 编制财产状况报告 | 汇总资产/负债/权益/追收/变现方案，提出处置建议 |

> 详细规格见 [references/workflow-detail.md](./references/workflow-detail.md)

---

## 模块四：输入输出概要

### 关键输入

| 参数 | 必填 | 说明 |
|------|------|------|
| `takeover_materials` | 是 | 接管材料路径（账册/流水/合同/权属证明等） |
| `acceptance_date` | 是 | 破产申请受理日期 |
| `debtor_info` | 是 | 债务人基本信息（名称/行业/注册资本） |
| `known_clues` | 否 | 已知财产线索或可疑交易 |
| `related_parties` | 否 | 已知关联方清单 |

### 关键输出

| 输出 | 格式 | 说明 |
|------|------|------|
| O1: 接管清单 | docx | 按财产类型分类的接管清单 |
| O2: 财产状况报告 | docx | 资产/负债/权益/追收/变现方案 |
| O3: 追收线索清单 | docx | 撤销权/无效行为线索，含方向和依据 |
| O4: 结构化资产摘要 | json | asset_tracing_summary.json，供下游复用 |

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
| 接管清单模板 | [templates/takeover-checklist-template.md](./templates/takeover-checklist-template.md) | 接管清单格式 |
| 追收线索模板 | [templates/recovery-clue-template.md](./templates/recovery-clue-template.md) | 追收线索清单格式 |
| 方法论 | [references/methodology.md](./references/methodology.md) | 核心方法论与隐性知识 |
| 质量标准 | [references/quality-standards.md](./references/quality-standards.md) | 质量评价维度与检查项 |
| 示例 | [examples/example-001-liquidation.md](./examples/example-001-liquidation.md) | 标准示例 |
| 变更记录 | [CHANGELOG.md](./CHANGELOG.md) | 版本变更历史 |
