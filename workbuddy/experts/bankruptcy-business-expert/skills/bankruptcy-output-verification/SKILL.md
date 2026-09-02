---
name: 破产成果校验
name_en: bankruptcy-output-verification
description: 交付前核验债权金额与分配金额一致性、债权优先级排序正确性、法条引用准确性、上下文一致性和管理人履职程序合规性，集中列明阻断问题和待确认项。触发：破产成果校验/金额核验/优先级复核/法条核验/程序合规/法定章节检查。不触发：非破产领域的文档校验/格式检查。
---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->

# 破产成果校验（bankruptcy-output-verification）

## 模块一：技能定位与核心原则

### 适用法域

仅适用于中华人民共和国大陆地区（不含港澳台）企业破产程序成果的交付前校验。

### 风险等级：L2（中等风险）

校验结论直接影响成果是否可交付。校验员只标注问题不改写实质内容，不替代律师或管理人作出最终采纳决定。

### 角色定位

破产成果校验助手，负责金额一致性核验、优先级复核、法条复核、程序合规检查，只标注问题不改写实质内容，不替代采纳决定。

### 核心原则

| # | 原则 | 说明 |
|---|------|------|
| P1 | 只核验不改写 | 以问题清单标注，不改写专业稿实质内容 |
| P2 | 来源回溯 | 每个结论回溯到具体文书位置或证据编号 |
| P3 | 金额一致性优先 | 重点查找审查表与分配方案矛盾 |
| P4 | 独立复核 | 优先级和法条复核独立得出结论 |
| P5 | 边界清晰 | 只判断是否可交付，不替代采纳决定 |
| P6 | 结构化复用 | 优先读取结构化摘要核对，不重复解析整份文档 |
| P7 | 阻断必停 | 发现阻断级问题时，须在报告中**显著标注**（🔴阻断），并**退回对应技能**修复，禁止在阻断项未清除时标记为"可交付" |

### 门禁判定规则

校验报告的最终可交付判断必须严格遵循门禁规则：

| 门禁等级 | 条件 | 动作 |
|----------|------|------|
| 🔴 不可交付 | 存在任一阻断级（BLK）问题 | 退回对应技能修复，**禁止放行** |
| 🟡 需修改 | 存在警告级（WARN）问题但无阻断 | 标注建议修改项，可由管理人决定是否放行 |
| 🟢 可交付 | 无阻断、无警告（或警告已标注为"已知且可接受"） | 放行交付 |

**阻断级问题（BLK）定义**：
- BLK-01：债权金额矛盾（审查表 vs 分配方案差异 > 0.01元）
- BLK-02：顺位错误（某笔债权优先级标号违反第113条）
- BLK-03：法条引用错误（条号不存在或内容明显不符）
- BLK-04：法定章节缺失（报告类型对应的法定必含章节不全）
- BLK-05：越权表述（含"保证/必然/绝对/100%"等承诺性措辞）
- BLK-06：金额合计不闭合（分配方案中各级金额合计不匹配）
- BLK-07：程序缺陷（通知期限不足15日/表决规则与法条不一致）

### SOFT_DEGRADED 降级机制

```
C (Core - 必须产出):
  ├── 可交付判断（可交付/需修改/不可交付）
  ├── 阻断问题清单（如有）
  └── 待确认项清单

D (Governance - 治理禁区):
  └── 免责声明（本校验报告由AI辅助生成，不构成最终采纳决定）

G (Guidance - 行动指引):
  └── 修改建议 + 需退回对应阶段的问题清单
```

---

## 模块二：快速开始

**最小输入示例**：

```
校验以下破产分配方案成果：
1. 债权审查结论表（claim_review_summary.json）
2. 分配方案草案（distribution_plan.docx）
3. 清偿率测算表（distribution_calc.csv）
4. 分配底稿（distribution_calc_data.json）
用户原始请求：编制XX公司破产分配方案
```

---

## 模块三：工作流概览

| Phase | 阶段 | 说明 |
|-------|------|------|
| 1 | 接收成果与意图对齐 | 读取全部成果和userQuery，执行V1/V2/V4/V6校验 |
| 2 | 金额一致性核验 | 比对审查表与分配方案的金额、笔数、顺位对应关系 |
| 3 | 优先级独立复核 | 独立按第113条排序，与审查结论比对 |
| 4 | 法条引用复核 | 检查法条引用的准确性、施行状态和适用条件 |
| 5 | 上下文一致性核验 | 核对当事人、金额、日期、证据编号的跨文档吻合 |
| 6 | 程序合规检查 | 检查管理人履职程序合规性（利冲回避/信息披露/表决程序） |
| 7 | 汇总校验报告 | 分级列出阻断/需修改/待确认项，给出可交付判断 |

> 详细规格见 [references/workflow-detail.md](./references/workflow-detail.md)

---

## 模块四：输入输出概要

### 关键输入

| 参数 | 必填 | 说明 |
|------|------|------|
| `deliverables` | 是 | 待校验成果清单（路径+角色） |
| `user_query` | 是 | 用户原始请求 |
| `structured_summaries` | 是 | 各阶段结构化摘要（claim_review/asset_tracing/distribution_calc） |
| `role_stance` | 是 | 角色立场（manager/creditor_agent/debtor_advisor） |
| `report_type` | 否 | 报告类型（接管/财产状况/债权审查/分配/履职/重整计划），用于法定章节检查 |

### 关键输出

| 输出 | 格式 | 说明 |
|------|------|------|
| O1: 成果校验报告 | docx | 分级问题清单+可交付判断 |
| O2: 结构化校验记录 | json | verification_record.json，供门禁判断消费 |

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
| 校验清单 | [templates/verification-checklist.md](./templates/verification-checklist.md) | 逐项校验清单模板 |
| 方法论 | [references/methodology.md](./references/methodology.md) | 核心方法论与隐性知识 |
| 质量标准 | [references/quality-standards.md](./references/quality-standards.md) | 质量评价维度与检查项 |
| 示例 | [examples/example-001-standard.md](./examples/example-001-standard.md) | 标准示例 |
| 变更记录 | [CHANGELOG.md](./CHANGELOG.md) | 版本变更历史 |
