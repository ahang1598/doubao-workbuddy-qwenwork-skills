---
name: 重整计划草案编制
name_en: bankruptcy-reorg-plan-draft
description: 编制破产重整计划草案（含经营方案/债权调整方案/债权清偿方案/执行期限与监督/出资人权益调整）和和解协议草案。触发：重整计划/重整草案/经营方案/债权调整/出资人权益/和解协议。不触发：破产清算分配方案/非破产场景的企业重组方案。
---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->

# 重整计划草案编制（bankruptcy-reorg-plan-draft）

## 模块一：技能定位与核心原则

### 适用法域

仅适用于中华人民共和国大陆地区（不含港澳台）企业破产重整与和解程序。

### 风险等级：L3（高风险）

重整计划草案直接影响债权人受偿和企业存亡，须经债权人会议分组表决和法院批准。所有输出均为**草案参考**，不替代管理人决定对外提交。

### 角色定位

破产重整计划草案编制助手，负责经营方案/债权调整/清偿方案/出资人权益调整方案编制，不替代管理人/债务人提交决定。

### 核心原则

| # | 原则 | 说明 |
|---|------|------|
| P1 | 法定章节完整 | 第81条全部法定章节不得遗漏 |
| P2 | 清算地板测试 | 重整清偿率不得低于模拟清算清偿率 |
| P3 | 同类公平 | 同一组别债权调整比例相同 |
| P4 | 可行性论证 | 经营方案须有可行性分析，不是空泛口号 |
| P5 | 边界清晰 | 只提供草案，不替代管理人/债务人提交决定 |
| P6 | 数据可追溯 | 调整比例和清偿率须有计算依据 |

### SOFT_DEGRADED 降级机制

```
C (Core - 必须产出):
  ├── 债权分类与调整框架
  ├── 清偿方案初步框架（含清偿率估算）
  └── 法定必含章节骨架（标注待填充项）

D (Governance - 治理禁区):
  └── 免责声明（本草案由AI辅助生成，须经债权人会议表决和法院批准）

G (Guidance - 行动指引):
  └── 待补充信息清单 + 需管理人/债务人确认事项 + 律师复核建议
```

---

## 模块二：快速开始

**最小输入示例**：

```
编制XX房产公司重整计划草案。
债务人：XX房地产开发有限公司，重整程序。
债权概况：职工债权300万/社保税款200万/担保债权5000万/普通债权2亿。
可供偿债资源：在建工程估值1.5亿/应收账款3000万/投资人意向出资8000万。
经营方案方向：引入战略投资人续建在售楼盘。
```

---

## 模块三：工作流概览

| Phase | 阶段 | 说明 |
|-------|------|------|
| 1 | 信息收集与分析 | 收集债务人信息、债权概况、可供偿债资源、经营方向 |
| 2 | 债权分类与清算地板测试 | 按法定顺位分类，计算模拟清算清偿率作为底线 |
| 3 | 设计债权调整方案 | 确定各类债权调整比例和方式，确保公平对待 |
| 4 | 设计债权受偿方案 | 确定清偿方式/期限/比例/资金来源 |
| 5 | 编制经营方案 | 编制业务方向/经营措施/盈利预测/可行性分析 |
| 6 | 编制出资人权益调整方案 | 如有需要，设计股权稀释/让渡方案 |
| 7 | 组装草案与自检 | 组装完整草案，执行法定章节完整性自检 |

> 详细规格见 [references/workflow-detail.md](./references/workflow-detail.md)

---

## 模块四：输入输出概要

### 关键输入

| 参数 | 必填 | 说明 |
|------|------|------|
| `debtor_info` | 是 | 债务人基本信息（名称/行业/主营业务/资产负债概况） |
| `claim_summary` | 是 | 债权审查结论摘要（各顺位债权总额和笔数） |
| `available_resources` | 是 | 可供偿债资源（资产估值/投资人意向/经营收入预测） |
| `business_plan_direction` | 是 | 经营方案方向（续建/转型/出售/其他） |
| `investor_info` | 否 | 战略投资人信息（如有） |
| `procedure_type` | 否 | 程序类型（reorganization/settlement），默认reorganization |

### 关键输出

| 输出 | 格式 | 说明 |
|------|------|------|
| O1: 重整计划草案 | docx | 含全部法定章节的完整草案 |
| O2: 债权调整与清偿对照表 | csv | 各类债权调整前后对照（可用 Excel 打开） |
| O3: 结构化草案摘要 | json | reorg_plan_summary.json |

> 输出制品与写作红线详见 [references/output-spec.md](./references/output-spec.md)
> 核心方法论详见 [references/methodology.md](./references/methodology.md)

---

## 模块五：文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| 输入规格 | [references/input-spec.md](./references/input-spec.md) | 输入参数详细定义 |
| 输出规格 | [references/output-spec.md](./references/output-spec.md) | 输出制品与写作红线 |
| 工作流程 | [references/workflow-detail.md](./references/workflow-detail.md) | 7 Phase 详细步骤 |
| 法条参考 | [references/legal-references.md](./references/legal-references.md) | 破产法核心条文 |
| 草案模板 | [templates/reorg-plan-template.md](./templates/reorg-plan-template.md) | 重整计划草案模板 |
| 和解模板 | [templates/settlement-template.md](./templates/settlement-template.md) | 和解协议草案模板 |
| 方法论 | [references/methodology.md](./references/methodology.md) | 核心方法论与隐性知识 |
| 质量标准 | [references/quality-standards.md](./references/quality-standards.md) | 质量评价维度与检查项 |
| 示例 | [examples/example-001-standard.md](./examples/example-001-standard.md) | 标准示例 |
| 变更记录 | [CHANGELOG.md](./CHANGELOG.md) | 版本变更历史 |
