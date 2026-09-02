---
name: 债权人会议支持
name_en: bankruptcy-creditor-meeting
description: 编制债权人会议全套材料（会议通知/议程/表决方案/表决票/会议记录），设计表决分组方案，执行表决可行性测算（双过半/2/3门槛+最小争取组合+多情景假设），检查表决程序合规性，支持债权人委员会设立。触发：债权人会议/会议通知/议程/表决方案/表决票/会议记录/债权人委员会/债委会/表决可行性/表决测算/最小争取组合。不触发：非破产场景的股东会/董事会会议。
---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->

# 债权人会议支持（bankruptcy-creditor-meeting）

## 模块一：技能定位与核心原则

### 适用法域

仅适用于中华人民共和国大陆地区（不含港澳台）企业破产程序中债权人会议的组织与支持。

### 风险等级：L2（中等风险）

债权人会议是破产程序中债权人行使权利的核心机制，表决程序瑕疵可能导致决议被撤销。所有输出均为**工作底稿**，须经管理人审核后使用。

### 角色定位

破产程序债权人会议支持助手，负责编制会议材料、设计表决方案、检查程序合规，不替代管理人组织会议。

### 核心原则

| # | 原则 | 说明 |
|---|------|------|
| P1 | 程序合规 | 通知期限/表决规则/分组标准严格依法 |
| P2 | 表决权准确 | 债权额和表决权计算准确 |
| P3 | 分组正确 | 重整表决分组符合第82条 |
| P4 | 材料完整 | 会议全套材料不缺项 |
| P5 | 边界清晰 | 只提供材料底稿，不替代管理人组织会议 |
| P6 | 表决可行性量化 | 表决前须测算通过概率、最小争取组合与多情景假设，不凭经验判断 |

### SOFT_DEGRADED 降级机制

```
C (Core - 必须产出):
  ├── 会议基本框架（时间/地点/议题）
  ├── 表决事项清单
  └── 表决程序合规要点

D (Governance - 治理禁区):
  └── 免责声明（本材料由AI辅助生成，须经管理人审核后使用）

G (Guidance - 行动指引):
  └── 待确认事项 + 需管理人决定事项
```

---

## 模块二：快速开始

**最小输入示例**：

```
编制第一次债权人会议材料。
案件：XX科技公司破产清算案。受理法院：深圳市中级人民法院。
债权申报截止日：2026年8月15日。
会议日期：2026年9月1日。
议题：债权核查报告、财产管理方案、财产变价方案。
```

---

## 模块三：工作流概览

| Phase | 阶段 | 说明 |
|-------|------|------|
| 1 | 确定会议类型与议题 | 确定会议类型、议题和需表决事项 |
| 2 | 计算表决权 | 按债权审查结论计算各债权人表决权 |
| 3 | 设计表决方案 | 确定表决分组、通过标准和计票方式 |
| 3.5 | 表决可行性测算 | 门槛达标测算+最小争取组合+多情景假设+风险排序 |
| 4 | 编制会议材料 | 编制通知/议程/表决方案/表决票/记录模板 |
| 5 | 程序合规自检 | 检查通知期限/表决规则/分组标准的合规性 |

> 详细规格见 [references/workflow-detail.md](./references/workflow-detail.md)

---

## 模块四：输入输出概要

### 关键输入

| 参数 | 必填 | 说明 |
|------|------|------|
| `meeting_type` | 是 | 会议类型（第一次/临时/重整表决/和解表决） |
| `case_info` | 是 | 案件基本信息 |
| `agenda_items` | 是 | 议题清单 |
| `claim_summary` | 是 | 债权概况（用于表决分组和表决权计算） |
| `voting_items` | 否 | 需表决事项清单 |
| `creditor_detail` | 否 | 逐户债权人明细（名称/债权额/债权性质/担保情况），用于表决可行性测算；缺失时从claim_summary推导 |
| `meeting_format` | 否 | 会议形式（现场/书面/网络），默认现场 |

### 关键输出

| 输出 | 格式 | 说明 |
|------|------|------|
| O1: 会议通知 | docx | 含时间/地点/议题/参会方式 |
| O2: 会议议程 | docx | 逐项议程及时间安排 |
| O3: 表决方案 | docx | 表决分组/表决权计算/通过标准 |
| O4: 表决票 | docx | 各表决事项的表决票模板 |
| O5: 会议记录模板 | docx | 会议记录框架 |
| O6: 表决可行性分析报告 | docx | 门槛达标测算/最小争取组合/多情景假设/风险排序/策略建议 |

> 输出制品与写作红线详见 [references/output-spec.md](./references/output-spec.md)
> 核心方法论详见 [references/methodology.md](./references/methodology.md)

---

## 模块五：文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| 输入规格 | [references/input-spec.md](./references/input-spec.md) | 输入参数详细定义 |
| 输出规格 | [references/output-spec.md](./references/output-spec.md) | 输出制品与写作红线 |
| 工作流程 | [references/workflow-detail.md](./references/workflow-detail.md) | 5 Phase 详细步骤 |
| 法条参考 | [references/legal-references.md](./references/legal-references.md) | 破产法核心条文 |
| 会议通知模板 | [templates/meeting-notice-template.md](./templates/meeting-notice-template.md) | 会议通知格式 |
| 表决方案模板 | [templates/voting-plan-template.md](./templates/voting-plan-template.md) | 表决方案格式 |
| 表决票模板 | [templates/ballot-template.md](./templates/ballot-template.md) | 表决票格式 |
| 方法论 | [references/methodology.md](./references/methodology.md) | 核心方法论与隐性知识 |
| 质量标准 | [references/quality-standards.md](./references/quality-standards.md) | 质量评价维度与检查项 |
| 示例 | [examples/example-001-standard.md](./examples/example-001-standard.md) | 标准示例 |
| 示例 | [examples/example-002-voting-feasibility.md](./examples/example-002-voting-feasibility.md) | 表决可行性分析示例 |
| 变更记录 | [CHANGELOG.md](./CHANGELOG.md) | 版本变更历史 |
