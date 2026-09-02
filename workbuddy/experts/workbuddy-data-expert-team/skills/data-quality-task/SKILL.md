---
name: data-quality-task
layer: L3
lintCheckVersion: "1.0"
tags: [data-development]
user-invocable: false
requires:
  - scenarios/common/skills/artifact-uploader
  - scenarios/data-development/skills/asset-discovery
  - scenarios/data-development/skills/workflow-orchestration
description: >
  WeData 数据质量任务：基于规则的数据质量校验、监控与调度。
  当用户想了解表的数据质量状况（空值率、重复率、完整性、唯一性、一致性、有效性等），
  或提及质量任务、质量规则、规则模板、试运行、执行结果、质量告警、质量诊断、
  "表有没有质量问题"、"帮我检查数据质量"时触发。
  不处理数据画像/分布漂移（→ data-quality-profiling）和 Schema 级智能异常检测（→ data-quality-anomaly）。
---

# WeData Data Quality Task

## Skill 概述

本 skill 覆盖 `DataQualityService` 中**基于规则的数据质量校验**相关 API。质量任务是与"Profiling"、"异常检测"并列的能力：用户定义规则 → 调度/试运行 → 判定是否异常 → 告警通知。

## 不适用场景

- **数据剖析 Profiling**（数据画像 / 分布漂移 / dashboard）→ `data-quality-profiling`
- **智能异常检测**（Schema 级异常 / 新鲜度 / 完整度 / 学习中）→ `data-quality-anomaly`
- 通用数据资产检索 → `knowledge` / `semantic-meta-search`
- 数据模型/指标定义 → `semantic-manage`

## 必需输入

- **用户意图**：自然语言（至少一项）
- **写操作**：必须有用户明确触发指令，不得由 LLM 主动发起

---

## 硬性约束

以下规则**不可违反、不可跳过、不可降级**。

| # | 约束 | 一句话提示 |
|---|------|-----------|
| **H1** | `CreateDataQualityTask` 失败 → 立即终止链路 | 禁止用其他 TaskId 继续（串号风险） |
| **H2** | ResourceId 必须用户选 | 即使只有 1 个也要确认 |
| **H3** | 调度意图必须先采集血缘+同表+DAG 再推荐 | 禁止直接问二选一 |
| **H4** | 调 API 前必须两块独立展示（YAML 全文 + 告警配置） | 等用户"确认" |
| **H5** | 删除需用户回复同时包含"确认删除"+ TaskId | 批量逐个确认 |
| **H6** | 调度必须先发布（`VersionStatus = published`） | draft 先引导发布 |
| **H7** | `AlarmChannels`/`AlertRuleNames` 写请求顶层 | **禁止**放进 YAML（会被静默丢弃） |
| **H8** | 创建后禁止自动发布 | 必须用户显式确认 |

### 效率约束

#### 表定位策略

| 场景 | 正确行为 | 禁止行为 |
|------|---------|------------|
| 用户给出完整表名 | 直接执行 | — |
| 缺 catalog/schema | `search table '<表名>'` 定位（**最多 1 次**） | 遍历 catalog 猜测 |
| **未给出任何表名** | **立即询问**，零工具调用 | `get catalogs` / `get tables` 列举 |
| 搜索返回 0 结果 | **立即告知**"未找到"，停止 | 缩短关键词反复重试 |
| 搜索返回多个候选 | 展示列表让用户选 | 自行猜测选择 |

> **快速失败原则**：表名定位相关 CLI 调用**不得超过 3 次**。

#### CLI 调用规范

- 调用前**必须**参考 [api_reference.md](reference/api_reference.md) 中的命令模板，禁止凭猜测拼参数
- 需要查询多个 catalog/schema/表时**必须并行调用**，禁止串行
- 诊断多条规则执行结果时**必须并行**获取各规则详情

#### 创建前信息收集（一次调用）

```bash
wedatacli quality-task prepare_create --catalog <c> --schema <s> --table <t>
```

返回：`current_user`（OwnerId）、`existing_tasks`（同表已有任务）、`rule_templates`（规则模板）、`notifications`（通知渠道）。

**禁止**分别调用 `current-user get`、`list-rule-templates`、`notification list`、`quality-task list --filters TableName`。

#### 模板使用策略

- 默认优先使用 `system_template`（标准化程度高、维护成本低）
- 仅当需求无法被现有系统模板覆盖时才降级为 `custom_sql`
- 确定使用 `custom_sql` 后**禁止**单独调用 `list-rule-templates`

---

## 停止条件

| 条件 | 处理 |
|------|------|
| `CreateDataQualityTask` 失败 | 立即终止链路，禁止用其他 TaskId 继续（H1） |
| 用户未给出任何表名 | 立即询问目标表，零工具调用 |
| `search table` 返回 0 结果 | 告知"未找到该表"，停止探索 |
| 表名定位 CLI 调用已达 3 次 | 停止探索，告知用户确认表名 |
| 用户说"Profiling/数据画像/dashboard/监控效果" | 路由到 `data-quality-profiling` |
| 用户说"异常检测/智能异常/新鲜度/完整度/学习中" | 路由到 `data-quality-anomaly` |
| `completeness.is_complete=true`（诊断模式） | 禁止再调用其他检索类工具 |

---

## 意图路由（第一步 MUST）

| 意图类别 | 触发词 | 工作流 |
|----------|--------|--------|
| **E.0 综合诊断** | "数据质量怎么样 / 帮我检查数据质量 / 表有没有质量问题" | E.0 诊断 |
| **E.1 创建/更新** | "创建质量任务 / 加规则 / 配质量监控" | E.1 创建 |
| **E.2 试运行** | "试运行 / 跑一下看看 / 测试规则" | E.2 试运行 |
| **E.3 删除** | "删除质量任务 / 不要这个任务了" | E.3 删除 |
| **E.4 调度集成** | "配调度 / 加入工作流 / 定时跑" | E.4 调度 |
| **E.5 查询** | "看规则 / 看执行记录 / 看告警" | E.5 查询 |

---

## 工作流 E.0：综合诊断模式（质量域入口）

当用户描述宽泛质量问题时，**必须**使用综合诊断复合工具一次性完成三维度探测：

```bash
wedatacli quality-task diagnose --catalog <c> --schema <s> --table <t> [--time_range <N>d] [--latest_only] [--compare_alerts <N>]
```

**时间范围选择策略**：

| 用户表述 | 参数 |
|---------|------|
| "最近一次" / "上次" | `--latest_only` |
| "最近" / "怎么样" / 无时间限定 | 默认（`--time_range 7d`） |
| "最近一周" | `--time_range 7d` |
| "最近一个月" | `--time_range 30d` |
| "最近N次告警根因一样吗" | `--compare_alerts N` |

### 工具输出字段

1. **quality_task**：任务是否存在 + 任务列表（含规则数、覆盖维度）+ 执行统计（通过/异常/失败次数）+ 最近执行记录 + 自动下钻到触发规则级别
2. **quality_task.exec_stats**：时间范围内的执行统计摘要（total_execs/passed_count/abnormal_count/failed_count/latest_exec_time/latest_exec_result）
3. **profiling**：Profiling 配置是否存在 + 跨 workspace 状态
4. **anomaly**：异常检测继承状态 + 各维度基线状态 + open 异常
5. **summary**：已配置维度、问题数量、推荐动作
6. **completeness**：`is_complete` + `covered_questions` + `uncovered_questions`
7. **next_actions**：下一步建议命令（`priority`: none/optional/recommended）

### 诊断后续动作

- **`completeness.is_complete=true`** → 直接基于当前结果回答，**禁止**额外调用其他工具
- `summary.has_issues=true` → 进入诊断决策树（见 [spec.md §诊断决策树](reference/spec.md#诊断决策树)）
- **根因追溯限制**：最多 2 层、每层最多 3 个上游节点；超限则汇报已发现信息
- 某维度 `exists=false` → 推荐语气建议开启，不强制
- `next_actions` 中 `priority=none` 的命令 **禁止主动执行**

### 诊断模式禁止行为

- 禁止分别跳转到 `Skill("data-quality-profiling")` 和 `Skill("data-quality-anomaly")` 执行完整工作流
- 禁止对 `ListDataQualityTaskExecs` 进行超过 3 次分页遍历
- 禁止读取 `spec.md` 全文（工具输出已足够做诊断判断）
- `completeness.is_complete=true` 时禁止调用 `quality-task get`、`list-rule-execs` 等
- `priority=none` 时禁止主动执行该命令

---

## 工作流 E.1：创建 / 更新质量任务

1. **定位表** → 按表定位策略收集 catalog/schema/table
2. **`prepare_create`（强制第一步）**：一次性获取 OwnerId + 同表已有任务 + 规则模板 + 通知渠道
   - 已有任务 → 询问用户新建还是追加
3. **确定 rule_type** → 按模板使用策略判断 `system_template` / `custom_sql`
4. **构造 YAML** → 过 [14 项自检清单](reference/spec.md#自检清单14-项)
5. **告警配置** → 用户未提及则推荐语气建议开启；`ChannelId` 从 `prepare_create` 返回的 `notifications` 获取
6. **H4 配置确认闭环** → 两块独立展示（YAML 全文 + 告警配置）→ 等用户"确认"
7. **调 `wedatacli quality-task create`** → 返回 `TaskId` + `VersionNo`
8. **H8 禁止自动发布** → 汇报结果，提示用户可发布/试运行

---

## 工作流 E.2：试运行

1. **收集 ResourceId（H2）**：`wedatacli get compute-resources` → 过滤 `ExecAvailableStatus=1` → 表格让用户选
2. **调 `wedatacli quality-task run --task-id <id> --resource-id <id>`**
3. **轮询**：首次 2s → 间隔 3s → 最多 20 次 → 终止条件 `SubInstanceStatus ∈ {completed, cancelled}`
4. **结果处理**：失败/触发的规则进入诊断决策树

---

## 工作流 E.3：删除质量任务

1. 展示任务摘要（TaskId / TaskName / 表 / 规则数 / 版本状态）
2. 高亮"删除不可恢复，关联工作流节点会失效"
3. 要求用户回复同时包含**"确认删除"+ TaskId**（H5）
4. 校验通过 → `wedatacli quality-task delete --task-id <id>` → 汇报结果

---

## 工作流 E.4：工作流集成（配调度）

**4 步流程**（H3 + H6）：

1. **校验发布状态** → draft 先引导发布
2. **智能推荐**（并发采集血缘+同表+DAG）：

| 优先级 | 条件 | 推荐 |
|--------|------|------|
| P1 | 下游有工作流任务 | 加入该工作流，插入下游之前 |
| P2 | 上游有工作流任务 | 加入该工作流，插入上游之后 |
| P3 | 同表已有任务的 WorkflowRefs 非空 | 加入同一工作流 |
| P4 | 以上均不满足 | 新建独立工作流 |

3. **用户选择**
4. **交接给 `workflow-orchestration`**（本 skill 禁止直接调 `CreateWorkflow`/`UpdateWorkflow`）

---

## 产物归档

诊断报告和试运行结果（规则≥5 或失败≥1）通过 `Skill("artifact-uploader")` 上传，`domain="governance"`。

---

## 参考文件索引

- [领域规范（实体模型 / YAML 规范 / 诊断决策树 / 自检清单）](reference/spec.md)
- [API 接口说明（CLI 命令格式与参数）](reference/api_reference.md)
