# Profiling CLI 工具参考

> 本文件是 `data-quality-profiling` skill 的 **CLI 工具调用规格**。领域概念/实体模型见 [spec.md](spec.md)，工作流逻辑见 [SKILL.md](../SKILL.md)。

---

## CLI 命令总览

| 操作 | 命令 |
|------|------|
| 查询配置 | `wedatacli profiling-monitor get --catalog <c> --schema <s> --table <t>` |
| 创建/更新 | `wedatacli profiling-monitor create --catalog <c> --schema <s> --table <t> --profiling-type <type>` |
| 删除 | `wedatacli profiling-monitor delete --config-id <id>` |
| 手动刷新 | `wedatacli profiling-monitor refresh --config-id <id>` |
| Dashboard URL | `wedatacli profiling-monitor dashboard-url --access-key <key>` |
| 执行历史 | `wedatacli profiling-monitor list-execs --config-id <id> [--page 1 --page-size 10]` |
| 执行日志 | `wedatacli profiling-monitor exec-log --exec-id <id>` |

> **禁止**使用 `wedatacli --help`、`wedatacli --describe`、`wedatacli get`、`wedatacli search` 等探索性命令来"学习"工具用法。直接使用上述精确命令。

---

## 1. profiling-monitor get

查询指定表的 Profiling 配置（含 Dashboard 信息、跨 workspace 提示）。

**示例**：

```bash
wedatacli profiling-monitor get --catalog hive_catalog --schema ods --table orders
```

**响应字段**：

| 字段 | 说明 |
|------|------|
| `Config` | 完整配置对象，未配置时为空对象（所有字段零值） |
| `Config.ConfigId` | 配置 ID |
| `Config.ProfilingType` | `SNAPSHOT` / `TIME_SERIES` / `INFERENCE_LOG` |
| `Config.DashboardInfo.AccessKey` | Dashboard 渲染 Key（须通过 `dashboard-url` 命令转为完整 URL） |
| `Config.MonitorVersion` | 配置版本号 |
| `Config.Enabled` | 是否启用 |
| `AlreadyExistsLocation` | 跨 workspace 提示（非空 = 配置归属其他 workspace，禁止写操作） |
| `AlreadyExistsLocation.WorkspaceId` | 归属 workspace ID |
| `AlreadyExistsLocation.ConfigId` | 归属配置 ID |

---

## 2. profiling-monitor create

创建或更新 Profiling 配置。

**示例（SNAPSHOT 最简）**：

```bash
wedatacli profiling-monitor create --catalog hive_catalog --schema ods --table orders --profiling-type SNAPSHOT
```

**示例（TIME_SERIES 含调度）**：

```bash
wedatacli profiling-monitor create --catalog hive_catalog --schema ods --table orders --profiling-type TIME_SERIES --timestamp-col create_time --granularity "1 day" --schedule-mode SCHEDULED --cron "0 0 2 * * ?" --timezone Asia/Shanghai
```

**示例（INFERENCE_LOG）**：

```bash
wedatacli profiling-monitor create --catalog ml_catalog --schema inference --table credit_score_log --profiling-type INFERENCE_LOG --timestamp-col predict_time --prediction-col score --model-id-col model_id --problem-type classification --label-col actual_label --granularity "1 hour"
```

**响应**：`{ "ConfigId": "cfg_xxx" }`

> 创建前必须过 [spec.md 11 项自检清单](spec.md#创建前自检清单11-项)。

---

## 3. profiling-monitor delete

删除配置（连带清理指标表 + Dashboard，不可恢复）。

```bash
wedatacli profiling-monitor delete --config-id cfg_xxx
```

> 跨 workspace 调用会被拒绝。

---

## 4. profiling-monitor refresh

立即触发一次执行（不影响后续定时调度）。

```bash
wedatacli profiling-monitor refresh --config-id cfg_xxx
```

> 跨 workspace 调用会被拒绝。

---

## 5. profiling-monitor list-execs

分页查询执行记录。

```bash
wedatacli profiling-monitor list-execs --config-id cfg_xxx --page 1 --page-size 10
```

**响应字段**（`ProfilingExecRecord`）：

| 字段 | 说明 |
|------|------|
| `ExecId` | 执行 UUID |
| `Status` | `LAUNCHED` / `RUNNING` / `COMPLETED` / `FAILED` |
| `TriggerMode` | `manual` / `scheduled` / `config_init` |
| `StartTime` / `FinishTime` | 时间 |
| `Duration` | 耗时（秒） |
| `ErrorMessage` | 失败原因 |

---

## 6. profiling-monitor exec-log

查单次执行的引擎日志。

```bash
wedatacli profiling-monitor exec-log --exec-id exec_xxx
```

---

## 7. profiling-monitor dashboard-url

将 AccessKey 转为完整的 Dashboard URL。

```bash
wedatacli profiling-monitor dashboard-url --access-key 849585041024274432
```

**响应**：完整 URL（CLI 自动拼接 consoleDomain/WorkspaceId/RegionId）。

> 展示给用户时用 `[查看监控仪表盘](URL)` 格式，**禁止**把裸 AccessKey 数字直接展示。
