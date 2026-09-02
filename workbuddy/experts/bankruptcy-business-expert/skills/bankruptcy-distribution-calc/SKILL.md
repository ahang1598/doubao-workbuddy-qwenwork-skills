---
name: 破产分配计算
name_en: bankruptcy-distribution-calc
description: 依据债权审查结论和可供分配财产总额，执行分配顺位计算、优先债权足额清偿计算、普通债权按比例分配，编制分配方案草案和清偿率测算表。触发：分配方案/分配顺位/清偿率计算/破产费用/共益债务/按比例分配/分配草案。不触发：非破产场景的债务清偿安排/和解协议个别清偿。
---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->

# 破产分配计算（bankruptcy-distribution-calc）

## 模块一：技能定位与核心原则

### 适用法域

仅适用于中华人民共和国大陆地区（不含港澳台）企业破产程序。

### 风险等级：L3（高风险）

分配计算直接影响各债权人受偿金额，计算错误将导致管理人履职责任和分配方案被异议。所有输出均为**测算参考**，分配方案须经债权人会议表决和法院裁定认可。

### 角色定位

破产分配计算助手，负责分配顺位计算、清偿率测算、分配方案草案编制，不替代管理人作出分配决定。

### 核心原则

| # | 原则 | 说明 |
|---|------|------|
| P1 | 数据来源约束 | 仅基于审查确认数据，不使用申报或待确认金额 |
| P2 | 顺位严格 | 前一顺位未足额清偿的，后一顺位清零 |
| P3 | 精度可核 | 每步列明公式/基数/比例/结果 |
| P4 | 双格式一致 | 草案与测算表数据完全一致 |
| P5 | 不足额标注 | 某顺位无法足额清偿时显著标注 |
| P6 | 结构化交接 | 产出结构化分配底稿供校验复用 |

### SOFT_DEGRADED 降级机制

```
C (Core - 必须产出):
  ├── 各顺位债权总额汇总
  ├── 可供分配财产总额与列支项
  └── 普通债权清偿率初步测算（标注置信度）

D (Governance - 治理禁区):
  └── 免责声明（本测算由AI辅助生成，不构成最终分配方案）

G (Guidance - 行动指引):
  └── 待确认数据清单 + 需管理人核实事项 + 计算复核建议
```

---

## 模块二：快速开始

**最小输入示例**：

```
计算破产分配方案。
可供分配财产：2000万元。
破产费用：100万元。共益债务：50万元。
职工债权：300万元（50笔）。社保税款：200万元。
担保债权：500万元（担保物变现600万元）。
普通债权：3000万元（200笔）。
```

---

## 模块三：工作流概览

| Phase | 阶段 | 说明 |
|-------|------|------|
| 1 | 数据接收与校验 | 读取债权审查摘要和可供分配财产数据，校验数据完整性 |
| 2 | 汇总债权数据 | 按三层模型汇总各层债权总额和笔数 |
| 3 | Layer 0 财产外扣除 | 担保物变现价款扣除费用后清偿别除权，超额/不足处理 |
| 4 | Layer 1 随时清偿 | 从可供分配财产中列支破产费用和共益债务 |
| 5 | Layer 2 三顺位清偿 | 依次计算职工债权→社保统筹+税款→普通债权清偿 |
| 6 | 编制草案与测算表 | 编制分配方案草案和清偿率测算表，产出结构化底稿 |

> 详细规格见 [references/workflow-detail.md](./references/workflow-detail.md)

---

## 模块四：输入输出概要

### 关键输入

| 参数 | 必填 | 说明 |
|------|------|------|
| `claim_review_summary` | 是 | 债权审查结构化摘要（claim_review_summary.json） |
| `distributable_assets` | 是 | 可供分配财产总额及明细 |
| `secured_claims_detail` | 否 | 担保债权与担保物对应关系明细 |
| `interim_distribution` | 否 | 是否有中间分配（有则需提供已分配明细） |
| `distribution_mode` | 否 | 分配方式偏好（一次/多次），默认一次 |

### 关键输出

| 输出 | 格式 | 说明 |
|------|------|------|
| O1: 分配方案草案 | docx | 含顺位/比例/方式/时间的完整草案 |
| O2: 清偿率测算表 | csv | 逐笔清偿明细（可用 Excel 打开） |
| O3: 结构化分配底稿 | json | distribution_calc_data.json，供校验复用 |

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
| 分配方案模板 | [templates/distribution-plan-template.md](./templates/distribution-plan-template.md) | 分配方案草案格式 |
| 测算表模板 | [templates/calc-table-template.md](./templates/calc-table-template.md) | 清偿率测算表格式 |
| 方法论 | [references/methodology.md](./references/methodology.md) | 核心方法论与隐性知识 |
| 质量标准 | [references/quality-standards.md](./references/quality-standards.md) | 质量评价维度与检查项 |
| 示例 | [examples/example-001-standard.md](./examples/example-001-standard.md) | 标准示例 |
| 变更记录 | [CHANGELOG.md](./CHANGELOG.md) | 版本变更历史 |
