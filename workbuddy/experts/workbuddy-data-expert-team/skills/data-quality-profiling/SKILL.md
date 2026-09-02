---
name: data-quality-profiling
layer: L3
lintCheckVersion: "1.0"
tags: [data-development]
user-invocable: false
requires:
  - scenarios/common/skills/artifact-uploader
description: WeData 数据剖析 Profiling ：表级数据分布画像与漂移监测。当用户提及 Profiling、数据画像、分布漂移、快照分析、时序剖析、推理日志监控、dashboard 时触发。不处理质量规则和异常检测。
---

# WeData Data Quality Profiling

## Skill 概述

本 skill 覆盖 `DataQualityService` 中**数据剖析（Data Profiling）**相关的 **6 个业务 API**。Profiling 是与"质量任务（DataQualityTask）"**并列的能力**：质量任务关注"规则是否满足"，Profiling 关注"数据分布画像 / 漂移监测"，对齐 Databricks Lakehouse Monitoring。

## 不适用场景

- **质量任务**（规则 CRUD / 试运行 / 诊断 / 工作流集成）→ `data-quality-task`
- **智能异常检测**（Schema 级异常 / 新鲜度 / 完整度 / 学习中）→ `data-quality-anomaly`
- 通用数据资产检索 → `knowledge`
- 数据模型/指标定义 → `semantic-manage`

## 必需输入

- **用户意图**：自然语言（至少一项）
- **写操作**：必须有用户明确触发指令，不得由 LLM 主动发起

---

## 硬性约束

以下规则**不可违反、不可跳过、不可降级**。

### H7 Profiling 跨 workspace 写禁止

`GetProfilingMonitor` 返回的 `AlreadyExistsLocation` 非空 → 当前 workspace **不是**配置归属 workspace → 禁止 `Create / Update / Delete / Refresh`。

**正确处理**：

```markdown
这张表 `{catalog}.{schema}.{table}` 的 Profiling 配置已在 **项目 {WorkspaceId}** 创建（ConfigId: `{ConfigId}`）。

跨工作空间**只能查看**，不能修改/删除。请：
- 查看 → 跳转到 [项目 {WorkspaceId} 的 Profiling 页面] 操作
- 在当前工作空间重做 → 联系归属项目管理员先删除原配置
```

后端会硬拦截（错误码 `ErrProfilingCrossWorkspaceModify`），AI 必须**事前避免**而不是依赖错误回滚。

### H8 Profiling 不可变字段不得隐式改

以下 6 项字段一旦建过指标表就**锁定**：`ProfilingType` / `TimestampCol` / `PredictionCol` / `ModelIdCol` / `ProblemType` / `OutputSchemaName`

**正确处理**：用户要改这些字段 → **二次确认 → 删除原配置 → 重建**：

```markdown
你要修改的字段 `{field_name}` 是 Profiling 的**不可变参数**（一旦建过指标表不能修改）。
要变更必须**先删除原配置再重建**，删除会清理所有历史指标和 Dashboard。

请回复 **"确认删除并重建 {ConfigId}"** 继续。
```

### 全局安全约束

- 涉及 dashboard / 数据画像 / 监控效果的请求，**第一步必须 `GetProfilingMonitor` 探测**（F.0）
- `ProfilingType` **始终弹菜单让用户选**，不替用户假定；`INFERENCE_LOG`/`TIME_SERIES` 必填列字段**逐个问用户**，严禁猜列名
- **Dashboard 链接展示**：`DashboardInfo.AccessKey` 必须通过 `wedatacli profiling-monitor dashboard-url --access-key <AccessKey>` 构造完整 URL，**禁止把裸 AccessKey 数字直接展示给用户**，**禁止硬编码域名**
- Profiling **不需要** `OwnerId`（与质量任务不同）
- Profiling **不进** wedata 工作流（自带 `ScheduleConfig`）
- 不得编造 `ConfigId` / `ResourceId` / `ChannelId`
- 不得编造执行结果

**自检口诀**：Profiling 跨空间只读、不可变字段先删再建。

---

## 停止条件

| 条件 | 处理 |
|------|------|
| `AlreadyExistsLocation` 非空且用户要写操作 | 告知跨 workspace 只读，引导跳转，结束 |
| 用户要改 H8 不可变字段但拒绝删除重建 | 告知"不可变字段无法直接修改"，结束 |
| 用户说"质量任务/规则/试运行" | 路由到 `data-quality-task`，本 skill 不处理 |
| 用户说"异常检测/智能异常/新鲜度/完整度/学习中" | 路由到 `data-quality-anomaly`，本 skill 不处理 |
| `profiling-monitor get` 返回 Config 为空且用户只想看 dashboard | 告知"该表还没有 Profiling 监控"，引导创建 |

---

## 意图路由（第一步 MUST）

| 意图类别 | 触发词 | 工作流 |
|----------|--------|--------|
| **F.0 查看监控** | "开/看/查看 dashboard / 看监控效果 / 查看数据画像 / 监控模型效果 / 打开监控看板" | F.0 先探测 |
| **F.1 创建/更新** | "做画像 / 配 Profiling / 监控分布漂移 / 开个数据画像监控" | F.1 创建 |
| **F.2 删除** | "删除 Profiling / 不要监控了" | F.2 删除 |
| **F.3 刷新/查询** | "立刻跑一次 / 手动刷新 / 看执行历史 / 看日志" | F.3 执行查询 |

> **dashboard / 画像 / 监控效果 消歧优先级规则（最高优先级）**：用户话里出现 **"dashboard / 看板 / 数据画像 / 监控效果 / 模型效果（监控）/ 监控报表"** 等词时，**无论动词是"开/看/查看/查/帮我监控"，一律先判定为 Profiling**，第一步必须 `GetProfilingMonitor` 探测该表是否已有 Profiling 配置（详见 F.0），**禁止**直接走质量任务检索/创建或自行闲聊回复。

---

## 工作流 F.0：查看监控效果 / dashboard（先探测）

> 用户说"开/看 dashboard、看监控效果、查看数据画像、监控模型效果"等时，**第一步永远是 `GetProfilingMonitor` 探测**。

### 探测步骤

1. **定位表**：catalog/schema/table 必填；不齐 → 询问或从上下文取。
2. **探测**：`wedatacli profiling-monitor get --catalog <c> --schema <s> --table <t>`，按返回分支：
   - **`AlreadyExistsLocation` 非空**（已在其他 workspace 配置）→ 跨 workspace 只读：输出"已在项目 {ws} / ConfigId {id} 创建"，给出 **[查看监控仪表盘]** 链接（通过 `wedatacli profiling-monitor dashboard-url --access-key <AccessKey>` 获取 URL），**禁止本会话改**。
   - **`Config` 非空对象**（本 workspace 已有配置）→ **告知"该表已有 Profiling 监控"并让用户选**：展示摘要（ConfigId / ProfilingType / Granularity / MonitorVersion / Dashboard 状态），并给三选项菜单：
     ```markdown
     表 `{catalog}.{schema}.{table}` 已有 Profiling 监控（类型：{ProfilingType}，ConfigId：{id}）。你想：
     1. **查看 dashboard** — [打开监控仪表盘]（通过 `wedatacli profiling-monitor dashboard-url --access-key <AccessKey>` 获取 URL）
     2. **立即刷新一次** — 重新计算最新指标（RefreshProfilingMonitor）
     3. **修改配置 / 重配** — 调整 Granularity 等可变字段（不可变字段需删除重建，H8）
     请回复序号。
     ```
   - **`Config` 为空对象**（未配置）→ 该表还没有监控，进入 F.1 创建。

---

## 工作流 F.1：创建 / 更新 Profiling（强制 5 步）

1. **识别意图 + 定位表**：catalog/schema/table 必填；不齐 → 询问或从上下文取
2. **跨 workspace 检测（H7 强制）**：若未经 F.0 探测 → 先执行 F.0；若已探测过则复用结果。按 F.0 分支决定：跨 workspace → 结束；已有配置且要改不可变字段 → 引导 F.2 删除重建；已有配置改可变字段 → 进入步骤 3（更新）；未配置 → 进入步骤 3（创建）。
3. **采集配置**（按 ProfilingType 必填矩阵收集，详见 [spec.md](reference/spec.md#profilingtype-必填字段矩阵)）：
   - **`ProfilingType` 始终弹三选一菜单让用户选**（`SNAPSHOT` 快照画像 / `TIME_SERIES` 时序画像 / `INFERENCE_LOG` 推理日志监控）——**即使用户话里暗示了类型也不要替用户直接定类型**，必须展示菜单请用户确认。
   - **`INFERENCE_LOG` 的 4 个必填字段**（`TimestampCol` / `PredictionCol` / `ModelIdCol` / `ProblemType`）**必须逐个询问用户确认**，**严禁凭表名/列名猜测**填入；`TIME_SERIES` 的 `TimestampCol` 同理逐个问。
   - 推荐：`Granularity`（默认 `1 day`）、`ScheduleMode`（默认 `MANUAL`）、`OutputSchemaName`（默认沿用源表）、`ResourceConfig`（默认分布式 medium/medium/2/2）
4. **配置确认闭环**：展示完整配置（JSON 格式，逐字段含中文注释）→ 用户回复"确认" → 调 `wedatacli profiling-monitor create`
   - 创建前必须过 [spec.md 11 项自检清单](reference/spec.md#创建前自检清单11-项)
5. **汇报 + 推荐下一步**：返回 `ConfigId` →
   - ① 立即手动跑一次 → "帮我刷新这个 Profiling"（`wedatacli profiling-monitor refresh --config-id <id>`）
   - ② 看历史执行 → "看 Profiling 执行记录"（`wedatacli profiling-monitor list-execs --config-id <id>`）
   - ③ Dashboard 查看：[查看监控仪表盘]（通过 `wedatacli profiling-monitor dashboard-url --access-key <AccessKey>` 获取 URL）

---

## 工作流 F.2：删除 Profiling（强制 4 步）

> 不可逆：删除会清理指标表 + Dashboard。

1. `GetProfilingMonitor` 拉摘要（ConfigId / 表 / ProfilingType / Dashboard / MonitorVersion）
   - `AlreadyExistsLocation` 非空 → 跨 workspace，**禁止删除**，引导跳转
2. 高亮"删除会清理 `{output_catalog}.{output_schema}.{table}_profile_metrics` / `_drift_metrics` 指标表 + Dashboard，不可恢复"
3. 要求用户回复**「确认删除 {ConfigId}」**（必须含 ConfigId）
4. 校验通过 → `wedatacli profiling-monitor delete --config-id <id>` → 汇报结果

---

## 工作流 F.3：手动刷新 / 执行查询（只读 + 一次写）

| 意图 | API |
|------|-----|
| "看 dashboard / 看监控效果" | `GetProfilingMonitor` → 构造 dashboard 链接（先走 F.0） |
| "立刻跑一次 Profiling / 手动刷新" | `wedatacli profiling-monitor refresh --config-id <id>`（跨 workspace 禁用 H7） |
| "看执行历史 / 跑了几次" | `wedatacli profiling-monitor list-execs --config-id <id>` |
| "为什么这次执行失败 / 看日志" | `wedatacli profiling-monitor exec-log --exec-id <id>` |

---

## 产物归档

Profiling 执行失败诊断报告等产物，通过 `Skill("artifact-uploader")` 上传到 `databuddy/governance/`。

关键约束：`domain="governance"` → 回显 `studio_link` → 失败时展示 `errors[]`。

---

## 参考文件索引

- [领域规范（实体模型 / 枚举 / 字段矩阵 / 自检清单）](reference/spec.md)
- [API 接口说明（7 CLI 命令格式）](reference/api_reference.md)
