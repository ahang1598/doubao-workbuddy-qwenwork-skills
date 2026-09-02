---
name: 管理人报告编制
name_en: bankruptcy-manager-report
description: 编制破产管理人各类法定报告（接管报告/财产状况报告/履职报告/分配方案报告），确保法定必含章节完整、数据一致、程序合规。触发：接管报告/财产状况报告/履职报告/管理人报告/分配方案报告。不触发：重整计划草案（用bankruptcy-reorg-plan-draft）/非破产场景的报告编制。
---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->

# 管理人报告编制（bankruptcy-manager-report）

## 模块一：技能定位与核心原则

### 适用法域

仅适用于中华人民共和国大陆地区（不含港澳台）企业破产程序中管理人法定报告的编制。

### 风险等级：L2（中等风险）

管理人报告是向法院和债权人会议提交的法定文件，内容错误或章节缺失可能导致管理人履职责任。所有输出均为**工作底稿**，须经管理人审核后对外提交。

### 角色定位

破产管理人报告编制助手，负责法定报告编制、数据一致性核对、法定章节完整性检查，不替代管理人审核后对外提交。

### 核心原则

| # | 原则 | 说明 |
|---|------|------|
| P1 | 法定章节完整 | 任一法定必含章节缺失即不可交付 |
| P2 | 数据一致 | 报告数据与前序阶段成果一致 |
| P3 | 来源可溯 | 每项数据标注来源（审查表/调查报告/计算底稿） |
| P4 | 边界清晰 | 只提供工作底稿，不替代管理人提交 |
| P5 | 样式适配 | 按受理法院要求或用户偏好调整格式 |

### SOFT_DEGRADED 降级机制

```
C (Core - 必须产出):
  ├── 报告法定必含章节骨架（标注已填/待填）
  ├── 已有数据填充章节
  └── 待补充信息清单

D (Governance - 治理禁区):
  └── 免责声明（本报告由AI辅助生成，须经管理人审核后提交）

G (Guidance - 行动指引):
  └── 待补充材料清单 + 需管理人确认事项
```

---

## 模块二：快速开始

**最小输入示例**：

```
编制XX科技公司破产案财产状况报告。
案件类型：破产清算。受理法院：深圳市中级人民法院。
数据来源：债权审查结论表、接管清单、资产调查报告。
```

---

## 模块三：工作流概览

| Phase | 阶段 | 说明 |
|-------|------|------|
| 1 | 确定报告类型与法定章节 | 根据程序阶段确定报告类型和法定必含章节清单 |
| 2 | 收集数据源 | 收集各阶段结构化摘要和数据来源 |
| 3 | 编制报告 | 按法定章节逐一编制，填充数据 |
| 4 | 数据一致性自检 | 核对报告数据与前序阶段成果的一致性 |
| 5 | 输出报告与数据核对表 | 输出完整报告和数据核对表 |

> 详细规格见 [references/workflow-detail.md](./references/workflow-detail.md)

---

## 模块四：输入输出概要

### 关键输入

| 参数 | 必填 | 说明 |
|------|------|------|
| `report_type` | 是 | 报告类型（takeover/asset_status/duty/distribution_plan） |
| `case_info` | 是 | 案件基本信息（债务人/案号/法院/程序类型/受理日期） |
| `data_sources` | 是 | 数据来源（各阶段结构化摘要路径） |
| `report_style` | 否 | 报告样式偏好（standard/detailed/brief），默认standard |
| `court_requirements` | 否 | 受理法院特殊格式要求 |

### 关键输出

| 输出 | 格式 | 说明 |
|------|------|------|
| O1: 管理人报告 | docx | 含法定必含章节的完整报告 |
| O2: 报告数据核对表 | json | report_data_check.json，用于校验员核验 |

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
| 接管报告模板 | [templates/takeover-report-template.md](./templates/takeover-report-template.md) | 接管报告格式 |
| 财产状况报告模板 | [templates/asset-status-report-template.md](./templates/asset-status-report-template.md) | 财产状况报告格式 |
| 履职报告模板 | [templates/duty-report-template.md](./templates/duty-report-template.md) | 履职报告格式 |
| 分配方案报告模板 | [templates/distribution-report-template.md](./templates/distribution-report-template.md) | 分配方案报告格式 |
| 方法论 | [references/methodology.md](./references/methodology.md) | 核心方法论与隐性知识 |
| 质量标准 | [references/quality-standards.md](./references/quality-standards.md) | 质量评价维度与检查项 |
| 示例 | [examples/example-001-standard.md](./examples/example-001-standard.md) | 标准示例 |
| 变更记录 | [CHANGELOG.md](./CHANGELOG.md) | 版本变更历史 |
