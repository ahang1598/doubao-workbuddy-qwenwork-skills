# 智能异常检测领域规范（Schema Anomaly）

> 本文件定义 Schema 异常检测的**实体模型、核心概念、状态机、枚举值**。字段以 `protocol/data-quality/service/data_quality_service.proto` 为准。

---

## 实体模型

```
Workspace
  └── Schema 异常检测开关（绑定 catalog.schema，Schema 级开关，表级自动继承）
        ├── ResourceId（计算资源，可选，默认不索要）
        ├── Status: enabled / disabled
        └── 表级继承（自动生效）
              ├── DetectionType: freshness（数据是否按时产出）
              ├── DetectionType: completeness（数据量是否完整）
              ├── BaselineState: learning / ready / paused
              └── AnomalyResult（每个维度独立产出）
                    ├── Status: open / resolved
                    └── Severity: warning / critical
```

**关键理解**：异常检测是 **Schema 级开关**。开启某 Schema 的检测后，该 Schema 下**所有表自动继承**，无需为每张表单独配置。每张表会针对 freshness / completeness 两个维度**独立学习基线**，学习完成后开始产出 open 异常。

---

## Schema 级开关 vs 表级继承语义

| 操作 | 粒度 | API |
|------|------|-----|
| 开启监控 | **Schema 级** | `EnableSchemaAnomaly` |
| 关闭监控 | **Schema 级** | `DisableSchemaAnomaly` |
| 更新资源 | Schema 级 | `UpdateSchemaAnomalyConfig` |
| 查询配置 | Schema 级 | `GetSchemaAnomalyConfig` |
| 查询状态 | **表级**（继承） | `GetTableAnomalyInheritStatus` |
| 查询异常结果 | **表级 / 全局** | `ListAnomalyResults` |

> **没有"表级开关"** — 不能为某张表单独开启 / 关闭异常检测。表的检测状态是**继承自 Schema** 的，AI 不要承诺用户"只给某张表开"。

---

## BaselineState 状态机

每张表的每个 `DetectionType`（freshness / completeness）有独立的 BaselineState：

```
       Schema EnableSchemaAnomaly
              │
              ▼
        ┌─────────────┐
        │  learning   │  收集样本中（约 7 天，每个维度独立）
        │ SampleCount<MinSamples │
        └──────┬──────┘
               │ 样本数达标
               ▼
        ┌─────────────┐
        │   ready     │  基线就绪，开始检测异常并产出 open 记录
        └──────┬──────┘
               │ Schema DisableSchemaAnomaly
               ▼
        ┌─────────────┐
        │   paused    │  保留基线但停止检测
        └─────────────┘
```

| 状态 | 是否产出 open 异常 | 备注 |
|------|------|------|
| `learning` | 不会 | 用户问异常时**主动告知"该维度还在学习中，预计 N 天后开始检测"** |
| `ready` | 会 | 正常工作状态 |
| `paused` | 不会 | Schema 关闭后的状态 |

---

## 枚举定义

### DetectionType

| 值 | 说明 |
|---|---|
| `freshness` | 数据是否按时产出（新鲜度） |
| `completeness` | 数据量是否完整（完整度） |

### AnomalyResult.Status

| 值 | 说明 |
|---|---|
| `open` | 异常未恢复 |
| `resolved` | 异常已恢复（系统自动判定） |

### AnomalyResult.Severity

| 值 | 图标 | 说明 |
|---|---|---|
| `critical` | | 严重异常 |
| `warning` | | 警告级异常 |

---

## 与质量任务、Profiling 的关系

| 维度 | DataQualityTask | Profiling Monitor | Schema Anomaly |
|------|------------------|-------------------|----------------|
| 关注点 | 用户定义的具体规则是否满足 | 数据分布画像 / 漂移监测 | 自动学习基线检测异常 |
| 配置粒度 | Task（绑表） | Monitor（绑表） | **Schema 级开关**（一次开 N 张表） |
| 是否需要用户写规则 | 是 | 否 | **否**（系统自动学习） |
| 触发方式 | 工作流调度 / 试运行 | 自带 cron / 手动 Refresh | 系统后台周期扫描 |
| 学习期 | 无 | 无 | **~7 天**（learning → ready） |

---

## AnomalyConfigInfo 响应字段

| 字段 | 说明 |
|------|------|
| `Status` | `enabled` / `disabled` |
| `ResourceId` | 计算资源 ID |
| `LastEnabledAt` / `ClosedAt` | 最近开启 / 关闭时间（毫秒） |
| `CreatorUin` / `UpdaterUin` | 创建/更新人 |

## TableAnomalyDimensionStatus 字段

| 字段 | 说明 |
|------|------|
| `DetectionType` | `freshness` / `completeness` |
| `BaselineState` | `learning` / `ready` / `paused` |
| `SampleCount` / `MinSamples` | 已采集样本数 / 基线最小样本数门槛 |
| `LastScanTime` | 上次采集时间（毫秒） |
| `HasOpenAnomaly` | 是否存在 open 异常 |
| `OpenSeverity` / `OpenDescription` | open 异常的严重程度和描述（已 i18n） |

## AnomalyResultItem 字段

| 字段 | 说明 |
|------|------|
| `AnomalyId` | 异常业务主键 UUID |
| `TableFullQualifiedName` | 表全限定名 `catalog.schema.table` |
| `DetectionType` | `freshness` / `completeness` |
| `Severity` | `warning` / `critical` |
| `Status` | `open` / `resolved` |
| `Description` | 异常描述（已 i18n，直接展示给用户） |
| `ActualValue` / `ExpectedValue` / `LowerBound` / `UpperBound` | 实际值 / 期望值 / 阈值上下界（double） |
| `DetectedAt` / `LastSeenAt` / `ResolvedAt` | 时间戳（毫秒，0 = 未恢复） |
| `OccurrenceCount` | 命中次数（去重后累加） |
| `ScanIntervalMs` | 当前扫描间隔（毫秒，展示用） |
