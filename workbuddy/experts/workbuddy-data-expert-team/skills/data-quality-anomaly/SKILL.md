---
name: data-quality-anomaly
layer: L3
lintCheckVersion: "1.0"
tags: [data-development]
user-invocable: false
requires: []
description: WeData 智能异常检测 ：Schema 级自动基线学习与异常检测（新鲜度/完整度）。当用户提及异常检测、智能异常、新鲜度、完整度、学习中、基线时触发。不处理质量规则和 Profiling。
---

# WeData Data Quality Anomaly Detection

## Skill 概述

本 skill 覆盖 `DataQualityService` 中**智能异常检测（Schema Anomaly）**相关的 **6 个对外 API**。异常检测是与"质量任务"、"Profiling"并列的能力：基于历史基线自动检测**新鲜度（freshness）** 和**完整度（completeness）** 异常。

异常检测是 **Schema 级开关**（不是 Task 级）。开启后该 Schema 下所有表自动接入，每张表针对 freshness / completeness 两个维度独立学习基线，约 7 天后开始检测。

## 不适用场景

- **质量任务**（规则 CRUD / 试运行 / 诊断 / 工作流集成）→ `data-quality-task`
- **数据剖析 Profiling**（数据画像 / 分布漂移 / dashboard）→ `data-quality-profiling`
- 通用数据资产检索 → `knowledge`
- 数据模型/指标定义 → `semantic-manage`

## 必需输入

- **用户意图**：自然语言（至少一项）
- **写操作**：必须有用户明确触发指令，不得由 LLM 主动发起

---

## 硬性约束

以下规则**不可违反、不可跳过、不可降级**。

### H9 Schema 异常检测关闭需双确认

`DisableSchemaAnomaly` 必须同时满足：
1. 请求参数 `Confirmed: true`
2. 用户原文回复包含**"确认关闭 {catalog}.{schema}"**字样

**正确处理（5 步）**：

1. `GetSchemaAnomalyConfig` 拉摘要（catalog / schema / Status / ResourceId / LastEnabledAt）
2. 高亮影响（模板见 G.2 步骤 2）
3. 要求用户原文回复**"确认关闭 {catalog}.{schema}"**（必须含 catalog.schema 字符串）
4. 校验通过 → 调 `wedatacli schema-anomaly disable --catalog <c> --schema <s>`；不通过 → 重新要求完整回复
5. 汇报结果（`ClosedAt` 时间戳）

**反模式**：
- 用户只回"确认" → 不通过，重新要求带 catalog.schema
- 不传 `Confirmed=true` → 后端拒绝
- AI 主动建议"是否需要关闭" → 必须用户显式触发

### 全局安全约束

- `ResourceId` **默认禁止索要/弹出选择**：异常检测由系统后台周期扫描，开启时**不需要**用户指定计算资源——**绝不在开启流程中弹出计算资源选择列表**；仅当用户主动要求"用某资源跑异常检测"才走 `wedatacli get compute-resources`
- **开启前必须用 `wedatacli get schema --catalog <c> --schema <s>` 校验 catalog.schema 存在（G.1 步骤 1，强制前置）**
- 学习期主动告知（避免用户误以为"开启了但没异常 = 系统坏了"）
- 不得编造 `AnomalyId` / `Description`
- 不得讲"异常规则"概念（系统自动学习，不存在用户可写的规则）

### 不提供的能力（强制告知）

- **手动恢复异常**（`ResolveAnomalyResult`）：白名单已排除。用户问"如何手动恢复" → 告知"系统会基于后续扫描自动恢复，无需手动；如有特殊需求联系平台"
- **表级单独开关**：异常检测是 Schema 级开关，不能为某张表单独开/关，AI 不要承诺
- **修改基线**：基线由系统学习产生，用户不能修改

**自检口诀**：Schema 异常关闭要带 catalog.schema。

---

## 停止条件

| 条件 | 处理 |
|------|------|
| `wedatacli get schema` 返回 schema 不存在 / 报错 | 告知「`{catalog}.{schema}` 不存在，请核对」，**禁止**继续调 enable |
| `GetSchemaAnomalyConfig` 返回 `Status=disabled` 且用户要关闭 | 告知"已是关闭状态，无需重复操作"，结束 |
| 用户要为单张表开/关异常检测 | 告知"异常检测是 Schema 级开关，不支持表级单独开关"，结束 |
| 用户要修改基线 | 告知"基线由系统自动学习产生，不支持手动修改"，结束 |
| 用户要手动恢复异常 | 告知"系统会基于后续扫描自动恢复，无需手动"，结束 |
| 用户说"质量任务/规则/试运行" | 路由到 `data-quality-task`，本 skill 不处理 |
| 用户说"Profiling/数据画像/dashboard/监控效果" | 路由到 `data-quality-profiling`，本 skill 不处理 |

---

## 意图路由（第一步 MUST）

| 意图类别 | 触发词 | 工作流 |
|----------|--------|--------|
| **G.1 开启** | "给 xxx 库开异常检测 / 智能异常监控 / 开启异常检测" | G.1 开启 |
| **G.2 关闭** | "关掉异常检测 / 不要异常监控了 / 关闭异常检测" | G.2 关闭 |
| **G.3 表详情** | "这张表的异常检测状态 / 看 schema 配置 / 用的什么资源" | G.3 查看 |
| **G.4 异常列表** | "有哪些异常 / 学习中的表 / 看异常列表 / 异常结果" | G.4 列表 |

> **与质量任务 / Profiling 不混淆**：
> - Anomaly **不是 Task 的子能力**：开启 Schema 异常检测**不会**自动创建质量任务
> - Anomaly **没有用户可写的规则 YAML**：异常由系统基于历史基线自动判定

---

## 工作流 G.1：开启 Schema 异常检测（写）

> **异常检测由系统后台周期扫描，开启时绝不弹出/索要计算资源选择。**

1. **校验 schema 存在**：`wedatacli get schema --catalog <c> --schema <s>`，不存在则告知并终止
2. **确认**：展示 catalog + schema → 用户回复"确认"（不弹计算资源）
3. **调用**：`wedatacli schema-anomaly enable --catalog <c> --schema <s>`
4. **结果告知**：成功后主动说明学习期约 7 天、学习中暂不产出异常、完成后自动检测

---

## 工作流 G.2：关闭 Schema 异常检测（H9 强制）

> 基线和 open 异常保留，但停止检测。按 H9 执行双确认 5 步。

1. `GetSchemaAnomalyConfig` 确认当前状态（`Status=disabled` → 告知已关闭，结束）
2. 告知影响：所有表检测停止、open 异常保留、基线保留
3. 要求用户回复**「确认关闭 {catalog}.{schema}」**
4. 校验通过 → `wedatacli schema-anomaly disable --catalog <c> --schema <s>`
5. 汇报 `ClosedAt`

---

## 工作流 G.3：表详情查看（只读）

- 表级状态（含异常检测维度信息）：`wedatacli quality-task diagnose --catalog <c> --schema <s> --table <t>`（diagnose 内部会调用 `GetTableAnomalyInheritStatus`，返回异常检测状态和各维度基线信息）
- Schema 配置：`wedatacli GetSchemaAnomalyConfig '{"CatalogName":"<c>","SchemaName":"<s>"}'`（旧接口格式）

输出时主动告知 BaselineState：`learning`（学习中）/ `ready`（正常检测）/ `paused`（已关闭）

---

## 工作流 G.4：异常结果列表（只读）

**用户意图**："有哪些异常 / 学习中的表 / 看异常列表"

**CLI 命令**：`wedatacli schema-anomaly list_results`（完整参数见 [api_reference.md](reference/api_reference.md#6-listanomalyresults)）

**调用要点**：
- 默认查 `open` 状态（用户问"有哪些异常"时不传 `--status`）
- 用户问"恢复历史 / 已修复的异常" → 传 `--status resolved`
- 响应中包含 `LearningCount`，必须输出

输出格式：

```markdown
## 异常检测结果
共 **{TotalCount}** 条 open 异常，另有 **{LearningCount}** 张表正在学习基线（暂不产出异常）。

| 表 | 维度 | 严重程度 | 描述 | 实际值 | 期望值 | 首次发现 | 命中次数 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| hive_catalog.ods.orders | freshness | critical | {Description} | {ActualValue} | [{LowerBound}, {UpperBound}] | {DetectedAt} | {OccurrenceCount} |
```

> 严重程度图标约定：`critical → `、`warning → `。

---

## 参考文件索引

- [领域规范（实体模型 / 状态机 / 枚举）](reference/spec.md)
- [API 接口说明（6 API CLI 调用格式）](reference/api_reference.md)
