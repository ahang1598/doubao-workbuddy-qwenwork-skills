# 安全评审报告模板

## 报告结构

以下章节顺序固定，不可调换。所有字段值中，中文描述用简体中文，机器标识符保持英文。

```
# 安全威胁评审 — {文档标题}

_Session: `{session_id}` · Model: `{model}`_

**发布决策：{BLOCK|CONDITIONAL|PASS}** · 有文档证据的威胁：{XX}%

## Executive Summary

{决策导向的执行摘要：整体风险态势、最重要的 3-5 个问题、首要行动建议}

**Risk posture:** {critical} critical · {high} high · {medium} medium · {low} low threats across {total} total.
**Compliance:** {pass} pass · {partial} partial · {fail} fail · {na} n/a.

## 风险主题聚类

### `{CL-NN}` {威胁簇标题} _({severity}, {confidence}%)_

{威胁簇描述：共同根因/弱点、影响范围}

- **关联威胁**：`{T-NN}`, `{T-NN}`, ...
- **影响组件**：`{element_id}`, `{element_id}`, ...

（按簇内最高严重度降序排列）

## 攻击链

### `{AP-NN}` {攻击链标题} _({severity}, 可行性 {feasibility}%)_

{攻击链概述}

1. **{步骤标题}**：{步骤描述} (`{T-NN}`)
2. **{步骤标题}**：{步骤描述} (`{T-NN}`, `{T-NN}`)

**关键控制**：{控制措施 1}；{控制措施 2}

（按 feasibility 降序排列）

## Data Flow Diagram

### Elements

| ID | Name | Type | Trust Boundary | Technologies |
|----|------|------|----------------|--------------|
| `{element_id}` | {name} | {type} | {trust_boundary 或 -} | {技术列表 或 -} |

### Trust Boundaries

- **{tb_name}** (`{tb_id}`): {description}

### Diagram

```mermaid
flowchart LR
    {element_id}([{name}])
    {element_id}[{name}]
    {element_id}[({name})]
    {source} -->|{flow_name}| {target}
```

> Mermaid 形状规则：
> - external_entity → `([名称])`（圆角矩形）
> - process → `[名称]`（矩形）
> - data_store → `[(名称)]`（圆柱）
> - data_flow → `source -->|名称| target`（箭头）
> - 名称中的空格替换为下划线，截取前 24 字符
> - 名称中的双引号替换为单引号

## STRIDE Threat Model

Threats grouped by DFD element and STRIDE category.

### `{element_id}` {element_name} _({element_type})_

- **{category}**: {威胁标题 1}; {威胁标题 2}
- **{category}**: {威胁标题 3}

（无威胁的类别标注 _No threats identified for applicable categories._）

## Risk Register

| ID | Element | Category | Severity | L | I | Threat |
|----|---------|----------|----------|---|---|--------|
| `{T-NN}` | {element_name} | {category} | **{severity}** | {likelihood} | {impact} | {title} |

（按 severity 排序：critical → high → medium → low）

## Threat Details

### {T-NN} — {威胁标题} _({category}, {severity})_

- **Element**: `{element_id}` {element_name}
- **Scenario**: {scenario}
- **Precondition**: {precondition}
- **Potential impact**: {potential_impact}
- **Confidence**: {XX}% · `{disposition}`
- **Evidence**:
  - `{source 或 section_id}`: "{原文引用}"
  - `{source 或 section_id}`（推断）: "{引用或推理依据}"
- **Assumptions**: {假设 1}；{假设 2}
- **Risk rationale**: {打分理由}

（按 severity 排序）

## Compliance Checks

| Pack | Rule | Status | Gap |
|------|------|--------|-----|
| {pack} | `{rule_id}` {rule} | {icon} {status} | {gap} |

> Status icon: ✅ pass · ❌ fail · ⚠️ partial · ➖ na

## Review Opinions & Recommendations

### [{P0|P1|P2|P3}] {ref_type} `{ref_id}` — {severity}

**Opinion**: {一句话说清问题及影响}

**Recommendation**: {一句话具体整改措施}

**Owner**: {建议责任方}

**Verification**:
- {验证步骤 1}
- {验证步骤 2}

**Acceptance criteria**:
- {验收标准 1}
- {验收标准 2}

（按 priority 排序：P0 → P1 → P2 → P3）

## 待澄清问题

- {open_question 1}
- {open_question 2}
- ...

## 评审元数据

- **评审文档**：{文档名称/来源}
- **评审时间**：{YYYY-MM-DD HH:MM}
- **评审方法**：STRIDE 威胁建模 + 合规基线检查
- **有文档证据的威胁**：{XX}%（附 direct 类型证据的威胁占比）
- **威胁总数**：{total}（critical={n}, high={n}, medium={n}, low={n}）
- **合规检查**：{total} 条规则（pass={n}, partial={n}, fail={n}, na={n}）
- **威胁簇**：{n} 个 · **攻击链**：{n} 条
- **声明**：本报告基于用户提供的设计文档进行分析，文档不完整或不准确之处可能影响评审结论。实际安全状况需结合代码审计和渗透测试综合评估。
```

## 发布决策判定标准

| 决策 | 条件 |
|------|------|
| **BLOCK** | 存在 ≥1 条 critical 威胁，或存在 ≥1 条 priority=P0 的评审意见，或存在 ≥1 条 status=fail 的合规项 |
| **CONDITIONAL** | 存在 ≥1 条 high 威胁，或存在 ≥1 条 priority=P1 的评审意见，或存在 ≥1 条 status=partial 的合规项 |
| **PASS** | 不满足以上任何条件，可上线（仍需关注中低危项） |

## 执行摘要写作要点

1. **决策导向**：直接告诉读者"能不能上线""最大的风险是什么""首先要做什么"
2. **不罗列所有发现**：综合归纳，只提最重要的 3-5 个问题
3. **量化支撑**：用威胁数量、严重度分布、有文档证据的威胁占比等数据支撑判断
4. **行动建议**：明确给出首要行动项（P0/P1），不要只说"需要关注安全"
5. **保守原则**：基于文档明确描述的内容做判断，不假设未提及的控制存在
