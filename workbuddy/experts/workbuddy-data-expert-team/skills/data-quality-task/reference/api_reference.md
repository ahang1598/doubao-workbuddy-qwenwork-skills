# API 参考 — Data Quality CLI

## 一、综合诊断（入口工具）

### quality-task diagnose

```bash
wedatacli quality-task diagnose --catalog <catalog> --schema <schema> --table <table> [--time_range 7d] [--latest_only] [--compare_alerts <N>]
```

**关键行为**：
- 当 `completeness.is_complete=true` 时，禁止再调用其他检索类工具（如 `quality-task get`、`list-rule-execs`），工具已自动完成下钻。
- `--compare_alerts N`：告警历史对比模式，一次性获取最近 N 次异常执行的规则级详情并输出对比摘要（N 默认 3，最大 5）。适用于"最近 N 次告警根因一样吗"类问题，**使用此参数后禁止再逐条调用 `list-execs` + `list-rule-execs` 手动对比**。

**返回结构增强字段**：

| 字段路径 | 说明 |
|---------|------|
| `quality_task.tasks[].dimensions` | 每个任务的规则覆盖维度列表（如 `["completeness", "validity"]`），从 RulesYaml 自动解析 |
| `quality_task.exec_stats.total_execs` | 时间范围内总执行次数 |
| `quality_task.exec_stats.passed_count` | 通过次数 |
| `quality_task.exec_stats.abnormal_count` | 异常次数（规则触发） |
| `quality_task.exec_stats.failed_count` | 执行失败次数 |
| `quality_task.exec_stats.latest_exec_time` | 最近一次执行时间 |
| `quality_task.exec_stats.latest_exec_result` | 最近一次执行结果（normal/abnormal/failed） |

**输出格式**：ToolSummary 包含【总览】【质量任务详情】【执行统计】【问题摘要】四个区块，模型应基于这些结构化数据组织回答。

---

## 一.五、创建前预检（复合接口）

### PrepareCreateDataQualityTask

```bash
wedatacli quality-task prepare_create --catalog <catalog> --schema <schema> --table <table>
```

**一次性返回创建质量任务所需的全部前置信息**（内部并行调用 4 个 SDK 接口）：

| 返回字段 | 说明 |
|---------|------|
| `current_user` | 当前用户信息（`uin` → OwnerId） |
| `existing_tasks` | 同表已有的质量任务列表（`task_id`/`task_name`/`published_version`/`has_draft`/`rule_count`） |
| `rule_templates` | 可用规则模板（`template_code`/`name`/`scope`/`dimension`） |
| `notifications` | 通知渠道列表（`notification_id` → ChannelId / `name` → ChannelName / `channel_type`） |
| `errors` | 部分接口失败时的错误信息（不影响其他字段返回） |

**创建场景必须首先调用此接口**，禁止分别调用 `current-user get`、`list-rule-templates`、`notification list`、`quality-task list`。

---

## 二、检索类

### ListDataQualityTasks

```bash
# 推荐：使用具名快捷参数（与 diagnose/create 风格一致）
wedatacli quality-task list --catalog hive_catalog --schema ods --table orders

# 也支持按任务名/状态过滤
wedatacli quality-task list --table orders --status published

# 高级用法：使用 --filters JSON 数组（支持更多组合条件）
wedatacli quality-task list --filters '[{"Name":"TableName","Values":["orders"]}]' --page_number 1 --page_size 20
```

**快捷参数**：`--catalog` / `--schema` / `--table` / `--task_name` / `--status`（与 `--filters` 可混用，快捷参数会自动合并到 filters 中）

**Filter.Name**（高级）：`TaskName` / `CatalogName` / `SchemaName` / `TableName` / `Status` / `OwnerId`

**响应**：`TaskId` / `TaskName` / `CatalogName.SchemaName.TableName` / `OwnerId` / `RulesYaml` / `VersionStatus` / `WorkflowRefs` / `AlarmChannels` / `AlertRuleNames` / `CreateTime` / `UpdateTime`

### GetDataQualityTask

```bash
wedatacli quality-task get --task_id task_xxx
```

### ListDataQualityRules

```bash
wedatacli quality-task list-rules --task_id task_xxx --filters '[{"Name":"Dimension","Values":["completeness"]}]'
```

**Filter.Name**：`RuleName` / `RuleType` / `Dimension` / `Status` / `Scope`

### ListDataQualityRuleTemplates

```bash
wedatacli quality-task list-rule-templates --filters '[{"Name":"Dimension","Values":["completeness"]},{"Name":"Scope","Values":["column"]}]' --page_number 1 --page_size 20
```


---

## 二、管理类

### CreateDataQualityTask（创建/更新）

```bash
wedatacli quality-task create \
  --task-name "质量任务_orders" \
  --catalog hive_catalog --schema ods --table orders \
  --owner-id 100046949685 \
  --rules-yaml "<YAML原始文本>" \
  --description "订单表质量监控" \
  --alarm-channels '[{"ChannelType":"NOTIFICATION_CHANNEL","ChannelId":"ntf_xxx","ChannelName":"生产值班群"}]' \
  --alert-rule-names "表为空告警,订单金额空值率"
```

- `--task-id` 空=创建，非空=更新（全量覆盖）
- `--rules-yaml`：直接传原始 YAML 文本，CLI 自动处理 base64 编码（也兼容已编码的 base64 字符串）
- `--alarm-channels`：JSON 数组，写请求顶层不进 YAML
- `--alert-rule-names`：逗号分隔，必须精确匹配 YAML 中 rule_name

**AlarmChannelInfo**：

| 字段 | 说明 |
|------|------|
| `ChannelType` | `NOTIFICATION_CHANNEL` / `EMAIL` |
| `ChannelId` | NOTIFICATION_CHANNEL 时必填，由 `ListNotifications` 解析 |
| `ChannelName` | 渠道展示名或邮箱地址 |

**响应**：`{ "TaskId": "task_xxx", "VersionNo": 3 }`

### DeleteDataQualityTask

```bash
wedatacli quality-task delete --task-id task_xxx
```

### PublishDataQualityTask

```bash
wedatacli quality-task publish --task-id task_xxx
```

### ListDataQualityTaskVersions

```bash
wedatacli quality-task list-versions --task_id task_xxx
```

---

## 三、执行类

### TryRunDataQualityTask

```bash
wedatacli quality-task run --task-id task_xxx --resource-id res_xxx
```

**获取候选资源**：`wedatacli get compute-resources`（过滤 `ExecAvailableStatus=1`）

### ListDataQualityTaskExecs

```bash
# 推荐：使用具名快捷参数（与 diagnose/create 风格一致）
wedatacli quality-task list-execs --task_id task_xxx --latest_only

# 按表名 + 时间范围 + 状态过滤
wedatacli quality-task list-execs --catalog hive_catalog --schema ods --table orders --check_status abnormal --start_date 2026-08-01 --end_date 2026-08-18

# 高级用法：使用 --filters JSON 数组
wedatacli quality-task list-execs --filters '[{"Name":"TaskId","Values":["task_xxx"]},{"Name":"LatestOnly","Values":["true"]}]'
```

**快捷参数**：`--task_id` / `--catalog` / `--schema` / `--table` / `--check_status` / `--start_date` / `--end_date` / `--latest_only`（与 `--filters` 可混用）

**Filter.Name**（高级）：`TaskId` / `TaskName` / `ExecMode` / `Status` / `InstanceStatus` / `CheckStatus` / `StartDate` / `EndDate` / `CatalogName` / `SchemaName` / `TableName` / `LatestOnly`

**ToolSummary 输出**：结构化摘要包含统计（通过/异常/失败次数）和每条执行记录的详情（ID、任务名、模式、状态、时间）。

#### 常用调用模式

> **核心规则**：快捷参数和 `--filters` 可混用，快捷参数会自动合并到 filters 中。优先使用快捷参数，复杂组合再用 `--filters`。

### ListDataQualityRuleExecs

```bash
wedatacli quality-task list-rule-execs --task_exec_id exec_xxx
```

**响应**：`RuleExecId` / `RuleName` / `ExecResultStatus`(passed/triggered/failed/not_executed) / `ActualValue` / `SourceResult` / `TriggerCondition` / `ExecutedSql` / `SubInstanceStatus`

### GetDataQualityRuleExecLog

```bash
wedatacli quality-task rule-exec-log --rule_exec_id rule_exec_xxx
```

### GetDataQualityRuleExecHistory

```bash
wedatacli quality-task rule-exec-history --rule_id rule_xxx --limit 20
```

---

## 四、工作流集成

### ListDataQualityTasksForWorkflow

```bash
wedatacli quality-task list-for-workflow --task_name "订单" --page_size 100
```

返回轻量摘要（**不含** `RulesYaml` / `VersionStatus`）。

### DATA_QUALITY 节点参数契约

| 要点 | 值 |
|------|---|
| `TaskTypeName` | `"DATA_QUALITY"` |
| Property `Source` | `"4"`（固定） |
| Property `SourceUniqueId` | `TaskId` |
| Property `SourceName` | `TaskName` |
| `ResourceGroupId` | type=2 作业集群 |
| 前置条件 | `VersionStatus = published` |

---

## 五、辅助 API

### GetCurrentUser

```bash
wedatacli current-user
```

取 `Data.Uin` 填充 `OwnerId`。

> **创建场景已由 `prepare_create` 覆盖**，无需单独调用。仅在非创建场景（如查询当前用户身份）时使用。

### ListNotifications

```bash
wedatacli notification list --keywords "<渠道名称>"
```

`NotificationId` → `ChannelId`，`Name` → `ChannelName`。

WorkspaceId 会自动注入，无需手动传递。

> **创建场景已由 `prepare_create` 覆盖**，无需单独调用。仅在非创建场景（如单独查询渠道列表）时使用。

### GetTablesWithColumns（批量获取表详情含字段）

```bash
# 获取 schema 下所有表的详情（含字段结构）
wedatacli get tables --with-columns --catalog <C> --schema <S>

# 指定表名列表
wedatacli get tables --with-columns --catalog <C> --schema <S> --tables "table1,table2,table3"
```
**批量场景必须用此工具**：需要多张表字段结构时（如批量推荐质量规则），禁止逐表 `get table` 串行获取。

---

## 六、关键枚举值

| 枚举 | 取值 |
|------|------|
| VersionStatus | `draft` / `published` / `abandoned` |
| ExecResultStatus | `passed` / `triggered` / `failed` / `not_executed` |
| ExecMode | `try_run` / `scheduled` |
| RuleType | `system_template` / `custom_sql` |
