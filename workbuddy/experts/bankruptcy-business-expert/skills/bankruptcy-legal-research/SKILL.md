---
name: 破产法律研究
name_en: bankruptcy-legal-research
description: 检索破产法及司法解释，执行债权性质法律认定、撤销权与抵销权法律分析、重整计划合法性审查和类案裁判倾向分析，为其他子代理提供法律依据支撑。触发：破产法检索/债权性质认定/撤销权分析/抵销权分析/重整计划审查/类案检索/程序合法性。不触发：非破产领域的一般法律研究/合同审查。
---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->

# 破产法律研究（bankruptcy-legal-research）

## 模块一：技能定位与核心原则

### 适用法域

仅适用于中华人民共和国大陆地区（不含港澳台）现行有效法律体系。

### 风险等级：L2（中等风险）

法律研究结论影响债权审查、分配方案和重整计划的合法性判断。研究意见供律师和管理人参考，不替代律师对外出具确定性法律意见。

### 角色定位

破产法律研究助手，负责法条检索、构成要件分析、类案检索、法律认定意见，不替代律师对外出具确定性法律意见。

### 核心原则

| # | 原则 | 说明 |
|---|------|------|
| P1 | 要件先行 | 先建构成要件清单，再检索依据 |
| P2 | 来源可核验 | 每条依据标注名称/条文号/施行日期/检索来源 |
| P3 | 效力分层 | 区分法律/司法解释/会议纪要/地方指引/案例 |
| P4 | 时效敏感 | 核对法律是否现行有效、是否被修订废止 |
| P5 | 边界清晰 | 只提供研究意见，不替代律师定性 |
| P6 | 检索收敛 | 核心规则覆盖即收敛，轮次预算15-20轮 |

### SOFT_DEGRADED 降级机制

```
C (Core - 必须产出):
  ├── 核心法条检索结果（标注施行状态）
  ├── 法律争点初步分析
  └── 待核查事项清单

D (Governance - 治理禁区):
  └── 免责声明（本研究意见由AI辅助生成，不构成正式法律意见）

G (Guidance - 行动指引):
  └── 需进一步检索的方向 + 建议咨询专业律师的事项
```

---

## 模块二：快速开始

**最小输入示例**：

```
研究问题：破产受理前3个月内，债务人对某银行的到期贷款
进行了清偿，管理人能否主张撤销？
案件背景：债务人2026年3月15日被受理破产，
2026年1月向某银行清偿到期贷款500万元。
```

---

## 模块三：工作流概览

| Phase | 阶段 | 说明 |
|-------|------|------|
| 1 | 确定法律争点 | 识别债权性质争议/撤销权适用/抵销权审查/重整计划合法性等争点 |
| 2 | 检索法律依据 | 检索破产法及司法解释，记录条文与施行状态 |
| 3 | 构成要件分析 | 建立要件清单，逐项分析要件是否满足 |
| 4 | 类案检索（可选） | 检索类似案件裁判文书，提炼裁判要点与倾向 |
| 5 | 形成分析意见 | 输出法律认定意见、适用条件和风险提示 |

> 详细规格见 [references/workflow-detail.md](./references/workflow-detail.md)

---

## 模块四：输入输出概要

### 关键输入

| 参数 | 必填 | 说明 |
|------|------|------|
| `research_question` | 是 | 法律研究问题或争议焦点 |
| `case_facts` | 是 | 已确认的相关案件事实 |
| `research_depth` | 否 | 研究深度（法规/法规+司法解释/法规+司法解释+类案） |
| `specific_provisions` | 否 | 需要重点分析的特定法条 |

### 关键输出

| 输出 | 格式 | 说明 |
|------|------|------|
| O1: 法律分析报告 | docx | 争点→要件→法条→类案→意见→风险提示 |
| O2: 结构化研究摘要 | json | legal_research_summary.json，供其他子agent消费 |

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
| 要件库 | [references/elements-library.md](./references/elements-library.md) | 核心权利构成要件库 |
| 方法论 | [references/methodology.md](./references/methodology.md) | 核心方法论与隐性知识 |
| 质量标准 | [references/quality-standards.md](./references/quality-standards.md) | 质量评价维度与检查项 |
| 示例 | [examples/example-001-standard.md](./examples/example-001-standard.md) | 标准示例 |
| 变更记录 | [CHANGELOG.md](./CHANGELOG.md) | 版本变更历史 |
