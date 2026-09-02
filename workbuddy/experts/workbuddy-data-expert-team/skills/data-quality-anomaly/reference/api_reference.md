# 智能异常检测 API 接口说明

> 本文件是 `data-quality-anomaly` skill 的 **CLI 工具调用规格**。领域概念/实体模型见 [spec.md](spec.md)，工作流逻辑见 [SKILL.md](../SKILL.md)。

---

## API 列表

| # | API | CLI 命令 | 功能 | 触发场景 |
|---|-----|---------|------|---------|
| 1 | `EnableSchemaAnomaly` | `schema-anomaly enable` | 开启 Schema 级异常检测 | 用户说"给 ods 库开异常检测 / 智能异常监控" |
| 2 | `DisableSchemaAnomaly` | `schema-anomaly disable` | 关闭 Schema 级异常检测（含 H9 二次确认） | 用户说"关掉异常检测 / 不要异常监控了" |
| 3 | `UpdateSchemaAnomalyConfig` | `schema-anomaly update_config` | 更新 Schema 配置（如修改计算资源） | 用户说"换个资源跑异常检测" |
| 4 | `GetSchemaAnomalyConfig` | ⚠️ 无独立子命令（旧接口可用） | 查询 Schema 级配置 | 用户说"看下异常检测配置 / 用的什么资源" |
| 5 | `GetTableAnomalyInheritStatus` | ⚠️ 无独立子命令（`quality-task diagnose` 内部调用） | 查询表级继承状态 | 用户说"这张表的异常检测状态" |
| 6 | `ListAnomalyResults` | `schema-anomaly list_results` | 分页查询异常结果列表（含学习中表数量） | 用户说"有哪些异常 / 学习中的表 / 看异常列表" |

> ⚠️ 标注说明：第 4、5 项未注册独立 CLI 子命令。第 4 项可通过旧接口 JSON 格式调用；第 5 项的信息已集成在 `quality-task diagnose` 输出中。

---

## API 详情

### 1. EnableSchemaAnomaly

**CLI 调用**：

```bash
wedatacli schema-anomaly enable --catalog <c> --schema <s>
```

**请求参数**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `CatalogName` | | 数据目录 |
| `SchemaName` | | Schema 名 |
| `ResourceId` | — | 计算资源 ID。可选，默认不索要；空 = 暂不指定，由系统调度 |

**响应**：返回 `AnomalyConfigInfo`（含 `Status=enabled` / `LastEnabledAt`）。

---

### 2. DisableSchemaAnomaly

**CLI 调用**：

```bash
wedatacli schema-anomaly disable --catalog <c> --schema <s>
```

**请求参数**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `CatalogName` | | 数据目录 |
| `SchemaName` | | Schema 名 |
| `Confirmed` | | 必须为 `true`（H9 强制） |

**响应**：`{ WorkspaceId, CatalogName, SchemaName, ClosedAt }`

---

### 3. UpdateSchemaAnomalyConfig

**CLI 调用**：

```bash
wedatacli schema-anomaly update-config '{"CatalogName":"c","SchemaName":"s","Config":{...}}'
```

**请求参数**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `CatalogName` | | 数据目录 |
| `SchemaName` | | Schema 名 |
| `ResourceId` | — | 留空表示不修改 |

**响应**：返回更新后的 `AnomalyConfigInfo`。

---

### 4. GetSchemaAnomalyConfig

**CLI 调用**：

```bash
# 注意：此命令当前未注册独立子命令，配置信息可通过 quality-task diagnose 获取
# 如需独立查询，使用旧接口：
wedatacli GetSchemaAnomalyConfig '{"CatalogName":"<c>","SchemaName":"<s>"}'
```

**请求参数**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `CatalogName` | ✅ | 数据目录 |
| `SchemaName` | ✅ | Schema 名 |

**响应**：`AnomalyConfigInfo`（字段详见 [spec.md](spec.md#anomalyconfiginfo-响应字段)）。

---

### 5. GetTableAnomalyInheritStatus

**CLI 调用**：

```bash
# 注意：此命令当前未注册独立子命令，表级状态可通过 quality-task diagnose 获取
# 如需独立查询，使用旧接口：
wedatacli GetTableAnomalyInheritStatus '{"CatalogName":"<c>","SchemaName":"<s>","TableName":"<t>"}'
```

**请求参数**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `CatalogName` | | 数据目录 |
| `SchemaName` | | Schema 名 |
| `TableName` | | 表名 |

**响应核心字段**：

| 字段 | 说明 |
|------|------|
| `InheritedStatus` | 继承的 Schema 级状态：`enabled` / `disabled` |
| `SchemaCatalogName` / `SchemaName` | 继承来源 |
| `Dimensions` | `TableAnomalyDimensionStatus` 列表（字段详见 [spec.md](spec.md#tableanomalydimensionstatus-字段)） |

---

### 6. ListAnomalyResults

**CLI 调用**：

```bash
# 查询整个 Schema 下的 open 异常
wedatacli schema-anomaly list_results --catalog <c> --schema <s>

# 查询指定表的异常
wedatacli schema-anomaly list_results --catalog <c> --schema <s> --table <t>

# 按检测类型过滤
wedatacli schema-anomaly list_results --catalog <c> --schema <s> --detection_type freshness

# 按严重程度过滤
wedatacli schema-anomaly list_results --catalog <c> --schema <s> --severity critical

# 按状态过滤（默认 open）
wedatacli schema-anomaly list_results --catalog <c> --schema <s> --status resolved

# 组合过滤 + 分页
wedatacli schema-anomaly list_results --catalog <c> --schema <s> --table <t> --detection_type freshness --severity critical --page_number 1 --page_size 10
```

**请求参数**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--catalog` | ✅ | Catalog 名称 |
| `--schema` | ✅ | Schema 名称 |
| `--table` | ❌ | 表名（不传则查询整个 Schema） |
| `--detection_type` | ❌ | 检测类型过滤：`freshness` / `completeness`，多个用逗号分隔 |
| `--severity` | ❌ | 严重程度过滤：`warning` / `critical`，多个用逗号分隔 |
| `--status` | ❌ | 状态过滤：`open`（默认）/ `resolved` |
| `--page_number` | ❌ | 页码，从 1 开始，默认 1 |
| `--page_size` | ❌ | 每页大小，默认 20，最大 100 |

**响应**：

| 字段 | 说明 |
|------|------|
| `Items` | `AnomalyResultItem` 列表（字段详见 [spec.md](spec.md#anomalyresultitem-字段)） |
| `TotalCount` | 总记录数（当前筛选范围） |
| `LearningCount` | 当前筛选范围内处于"学习中"的表数量（去重后） |

---

## 不对外 API

| 方法 | 说明 |
|------|------|
| `ResolveAnomalyResult` | 手动恢复异常记录（open → resolved），proto 注释明确"暂不对外"。用户问"如何手动恢复" → 告知"系统会基于后续扫描结果自动恢复，无需手动操作；如有特殊需求联系平台" |
| `TriggerAspect` | 切面回调，调度服务内部调用 |
