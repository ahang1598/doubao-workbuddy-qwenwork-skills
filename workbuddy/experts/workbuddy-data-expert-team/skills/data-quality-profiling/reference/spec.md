# 数据剖析领域规范（Data Profiling）

> 本文件定义 Profiling 的**实体模型、核心概念、枚举值、字段矩阵**。字段以 `protocol/data-quality/service/data_quality_service.proto` 为准。

---

## 实体模型

```
Workspace
  └── Profiling Monitor（绑定一张表，三元组 (catalog, schema, table) 全局唯一，跨 workspace 共享）
        ├── ProfilingType: SNAPSHOT / TIME_SERIES / INFERENCE_LOG（不可变 H8）
        ├── Granularity: 1 hour / 1 day / 1 week / 1 month（时间窗口拆分粒度，非扫描周期，可改）
        ├── ScheduleMode: MANUAL / SCHEDULED（自带 cron，不进 wedata 工作流）
        ├── ResourceConfig: 引擎规格（可改）
        ├── Dashboard: bi-server 透传渲染（自动创建）
        └── 执行记录（ProfilingExec：手动/定时/首次创建自动触发）
```

---

## 两阶段工作原理

1. **质量服务侧**开启 Profiling 任务 → 按调度策略（Cron/手动）扫描源表算出两张中间指标表：
   - `{table}_profile_metrics`（画像/空值/零值/窗口行数）
   - `{table}_drift_metrics`（漂移）
2. **Dashboard 服务**基于这两张指标表自动建仪表盘、预置系统默认图表，用户经 `DashboardInfo.AccessKey` 直接查看（无需自己配图）。

---

## 枚举定义

- **ProfilingType**: SNAPSHOT(快照画像) / TIME_SERIES(时序画像) / INFERENCE_LOG(推理日志监控)
- **ScheduleMode**: MANUAL(手动触发) / SCHEDULED(定时调度，需配 CrontabExpression)
- **Granularity**: `1 hour` / `1 day` / `1 week` / `1 month`
- **ProblemType**（仅 INFERENCE_LOG）: classification(分类) / regression(回归)
- **ProfilingExec.Status**: LAUNCHED(已提交) / RUNNING(运行中) / COMPLETED(完成) / FAILED(失败)
- **ProfilingExec.TriggerMode**: manual(手动) / scheduled(定时) / config_init(首次创建自动触发)

---

## ProfilingType 必填字段矩阵

| ProfilingType | 必填字段（除三元组外） | 可选字段 |
|---|---|---|
| `SNAPSHOT` | — | `Granularity` / `BaselineTableName` / `SlicingExpressions` / `ScheduleConfig` |
| `TIME_SERIES` | `TimestampCol` | `LabelCol` / `Granularity` / `SlicingExpressions` |
| `INFERENCE_LOG` | `TimestampCol` + `PredictionCol` + `ModelIdCol` + `ProblemType` | `LabelCol` / `SlicingExpressions` |

---

## 不可变字段（H8）

以下 6 项字段一旦建过指标表就**锁定**，不能通过更新模式修改：

| 字段 | 不可变原因 |
|------|-----------|
| `ProfilingType` | 决定指标表 schema 和指标计算引擎，类型变化等于换一套指标体系 |
| `TimestampCol` | 指标表时间分区键 |
| `PredictionCol` | 指标表预测值列 |
| `ModelIdCol` | 指标表模型分组列 |
| `ProblemType` | 决定公平性 / 准确性等指标的计算口径 |
| `OutputSchemaName` | 指标表的物理 catalog.schema 落地位置 |

## 可变字段

`Granularity` / `LabelCol` / `BaselineTableName` / `ResourceId` / `ScheduleMode` / `StoragePath` / `SlicingExpressions` / `ScheduleConfig` / `ResourceConfig`

---

## 跨 Workspace 语义

Profiling 配置以 `(catalog, schema, table)` 三元组全局唯一。`GetProfilingMonitor` 返回：

| 场景 | `Config` | `AlreadyExistsLocation` | 结论 |
|------|----------|------------------------|------|
| 未配置 | 空对象 | 空 | 可创建 |
| 本 workspace 已配置 | 完整对象 | 空 | 可更新/删除/刷新 |
| 其他 workspace 已配置 | 完整对象（只读） | 非空 | 禁止写操作 |

---

## 与质量任务、异常检测的关系

| 维度 | DataQualityTask | Profiling Monitor | Schema Anomaly |
|------|------------------|-------------------|----------------|
| 关注点 | 用户定义的具体规则是否满足 | 数据分布画像 / 漂移监测 | 自动学习基线检测异常 |
| 配置粒度 | Task（绑表） | Monitor（绑表） | Schema 级开关 |
| 是否需要用户写规则 | 是 | 否 | 否 |
| 触发方式 | 工作流调度 / 试运行 | 自带 cron / 手动 Refresh | 系统后台周期扫描 |
| 是否需要 OwnerId | 是 | **否** | 否 |
| 是否进 wedata 工作流 | 是 | **否**（自带 ScheduleConfig） | 否 |

---

## 创建前自检清单（11 项）

1. 已先调 `profiling-monitor get` 检测跨 workspace 状态
2. `ProfilingType` 是 `SNAPSHOT` / `TIME_SERIES` / `INFERENCE_LOG` 三选一（大写）
3. `TIME_SERIES` 已提供 `TimestampCol`
4. `INFERENCE_LOG` 已提供 `TimestampCol` + `PredictionCol` + `ModelIdCol` + `ProblemType`
5. `ProblemType` 是 `classification` / `regression`
6. `ScheduleMode` 是 `MANUAL` / `SCHEDULED`；`SCHEDULED` 时 `ScheduleConfig.CrontabExpression` 必填
7. `Granularity` 是 `1 hour` / `1 day` / `1 week` / `1 month` 之一
8. `OutputSchemaName` 格式为 `{schema}` 或 `{catalog}.{schema}`，或留空（沿用源表）
9. `SlicingExpressions` 中每个表达式可在源表 schema 中求值为布尔
10. `ResourceConfig.ExecutorAllocation=DYNAMIC` 时填 `ExecutorMinNum` + `ExecutorMaxNum`；`FIXED` 时填 `ExecutorFixedNum`
11. 更新模式下未修改 H8 不可变字段
