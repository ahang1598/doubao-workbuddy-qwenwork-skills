# Offline Integration Node Design Guide

## Purpose

This guide defines how offline Data Integration Task nodes should be designed, configured, and orchestrated within workflows.

An offline integration node represents a workflow task that executes a published offline data integration task by `data_integration_task_id`. It supports both data ingestion / data access tasks (external system → TCLake) and data egress tasks (TCLake → external system).

This guide focuses on workflow orchestration and node configuration.

It does NOT describe source/target connector implementation details.

Data integration task authoring, source/target mapping, schema mapping, and synchronization logic belong to the data integration task design process.

---

## Node Responsibilities

An offline integration node is responsible for:

- Referencing a published data integration task through `data_integration_task_id`
- Resolving the published integration task template path
- Participating in workflow DAG execution
- Consuming workflow parameters
- Consuming upstream dependencies
- Producing outputs for downstream workflow tasks
- Configuring DATA_ACCESS execution resources
- Configuring retry policy and relying on platform-default timeout behavior
- Preserving the original task direction defined by the referenced integration task

An offline integration node is NOT responsible for:

- Creating data integration tasks
- Designing source/target schemas
- Managing datasource connections
- Implementing synchronization logic
- Handling schema drift remediation
- Managing runtime instances or execution logs

---

## Required Configuration

An offline integration node must provide the following configuration:

| Field | Description |
|---------|-------------|
| workflow_id | Target workflow identifier |
| task_name | Workflow node name |
| data_integration_task_id | Published offline data integration task identifier |

An offline integration node cannot be created without these fields. Workspace selection is resolved from the default `wedatacli` workspace context.

---

## Optional Configuration

An offline integration node may additionally configure:

| Field | Description |
|---------|-------------|
| resource_group_id | Optional DATA_ACCESS execution resource override; if omitted, the CLI auto-selects a default at creation |
| parameters | Task parameters |
| depend_on_list | Upstream dependencies |
| depend_on_run_condition | Dependency trigger policy (default: `ALL_SUCCESS`; supported values are listed in `workflow_guide.md`) |
| retry_strategy | Retry configuration |
| position | Node position in workflow canvas |

---

## Integration Task Reference Rules

`data_integration_task_id` identifies the data integration task executed by the workflow node.

Use `wedatacli workflow task support-integration-tasks` to list selectable published offline integration tasks (`IsProd = 1`, `TaskCategory = 0`). By default it returns both ingestion/access and egress tasks; use `--direction ingress` or `--direction egress` when a specific direction is needed, and use `--keyword <kw>` to filter by task name keyword. When the response is larger than 1024 bytes or contains more than 3 items, the CLI writes only `payload.items` to `output_file`; stdout keeps paging metadata, `direction`, `keyword`, and one `payload.items_example` sample item. Spilled files are created in the system temp directory with basenames formatted as `<unix_timestamp>_<2 lowercase letters>.json`.

During creation, `wedatacli workflow task create --task-type ingestion` resolves the required published offline integration task template by:

1. Verifying that the offline integration task has a production/published version.
2. If the task is not published, stopping immediately and prompting the user to publish it before workflow orchestration.
3. Matching the provided `integration_task_id` against selectable published offline integration tasks.
4. Resolving the template path required for workflow execution.
5. Writing the required integration task reference into the node configuration.

Recommended:

```text
data_integration_task_id = published_integration_task_id
TemplatePath = resolved CosPath from published task
```

Direction classification:

| Direction | Integration task shape |
|-----------|------------------------|
| ingress | `OutputConnectionType = TCLake` and source is an external system |
| egress | `InputConnectionType = TCLake` and target is an external system |

Both directions are created in workflows as `TaskTypeName = DATA_INTEGRATION` with `Source = 4`, `TemplatePath`, and `DataIntegrationTaskId`.

Avoid:

```text
data_integration_task_id = unpublished task
data_integration_task_id = task without CosPath
```

Rules:

- Only use published offline data integration tasks (`IsProd = 1`, `TaskCategory = 0`)
- If the selected task is not published, publish it first before creating the workflow node
- Ensure the selected integration task has a valid `CosPath`
- Keep integration task ownership clear
- Keep source/target connector configuration outside this node guide
- Validate source availability and target write behavior before orchestration
- Do not recreate or modify the referenced integration task to change direction; choose the correct published task instead

---

## Dependency Design Rules

Offline integration nodes are commonly used as source-loading or outbound-export tasks.

Prefer simple and explicit dependency relationships.

Recommended:

```text
ingestion_source
    ↓
sql_clean
    ↓
python_or_sql_publish
```

Avoid:

```text
a
b
c
 \|/
ingestion_node
```

when dependencies are unnecessary.

Rules:

- Avoid circular dependencies
- Avoid hidden source readiness assumptions
- Prefer explicit dependency configuration
- Minimize fan-in complexity
- Keep DAG structure understandable

---

## Parameter Design Rules

Workflow-wide configuration should be defined as workflow parameters.

Task-specific configuration should be defined as task parameters.

Examples:

Workflow parameter:

```text
dt
env
region
```

Task parameter:

```text
source_partition
target_partition
batch_id
```

Prefer parameterization over hardcoded values.

Avoid:

```text
source_partition = 2025-01-01
target_table = fixed_dev_table
```

Prefer:

```text
source_partition = ${dt}
target_partition = ${dt}
```

---

## Resource Configuration Rules

Compute resources are auto-selected at node creation. When `resource_group_id` is omitted from `wedatacli workflow task create --task-type ingestion`, the CLI resolves an available default DATA_ACCESS execution resource automatically.

Offline integration nodes use available compute resources with `ResourceType` 1 (DATA_ACCESS).

Rules:

- Do not query or select a resource group when creating an offline integration node; the tool selects it automatically.
- Only pass `resource_group_id` when the user explicitly requests a specific execution resource.
- For explicit overrides, use `wedatacli workflow task support-resource-groups --task-type ingestion` to list selectable DATA_ACCESS resources and pick a valid one.
- Resource changes after creation go through `wedatacli workflow task update --resource-group-id ...`.

Do not use Job or Analytics resources for offline integration nodes when an explicit override is chosen.

---

## Retry Strategy Rules

Retries should be configured only when failures are expected to be transient and the integration task can tolerate reruns.

Examples:

Suitable for retry:

- Temporary infrastructure issues
- Resource contention
- Network instability
- Temporary source or target availability issues

Not suitable for retry:

- Invalid datasource credentials
- Missing source tables or fields
- Incompatible schema mapping
- Permission errors
- Non-idempotent target writes without deduplication or overwrite protection
- Invalid business logic in integration task configuration

Recommended:

```text
retry_times = 3
retry_interval = 5 minutes
```

Avoid unlimited retries.

Offline integration tasks should be idempotent before retry is enabled.

---

## Timeout Strategy Rules

> **Note**: Timeout strategy configuration is not yet exposed as a dedicated offline integration node command.
> Timeout behavior currently follows platform defaults. Update this section when `update_timeout_strategy` is implemented.

---

## Naming Conventions

Task names should be:

- Business meaningful
- Stable
- Easy to identify
- Valid according to the script rule: Chinese, English, digits, `_`, and `-` only

Recommended:

```text
ingest_ods_user_profile
ingest_order_detail_daily
source_pg_to_ods_order
```

Avoid:

```text
ingestion1
test_task
tmp
```

Naming should remain stable across workflow versions.

---

## Workflow Placement Patterns

### Pattern 1 — Source Ingestion Before SQL Processing

```text
ingestion_source
    ↓
sql_clean
```

Used when data must be loaded before SQL transformation.

---

### Pattern 2 — Multi-Source Ingestion Then Aggregation

```text
ingest_source_a
    ↓
ingest_source_b
    ↓
sql_aggregate
```

Used when multiple source loads are staged before aggregation.

---

### Pattern 3 — Ingestion + Quality Validation

```text
ingestion_source
    ↓
quality_check
    ↓
publish_result
```

Used for production-grade ingestion pipelines.

---

### Pattern 4 — Ingestion as Workflow Entry Point

```text
ingestion_entry
    ↓
downstream_processing
```

Used when ingestion triggers the first materialized dataset in a workflow.

---

## Anti Patterns

Avoid the following designs:

### Unpublished Integration Task

Do not create offline integration nodes from unpublished integration tasks.

Bad:

```text
data_integration_task_id has no IsProd = 1 version
```

Preferred:

```text
data_integration_task_id references a published task with CosPath
```

---

### Missing Template Path

Avoid tasks that cannot resolve `TemplatePath` from published metadata.

Bad:

```text
published task has empty CosPath
```

Preferred:

```text
published task has valid CosPath used as TemplatePath
```

---

### Non-Idempotent Target Writes

Avoid retrying offline integration tasks that append duplicate records on rerun.

Bad:

```text
append-only target write without partition or deduplication
```

Preferred:

```text
partition overwrite or deterministic deduplication
```

---

### Hidden Source Readiness Assumptions

Avoid relying on source readiness without explicit upstream dependency or schedule alignment.

Bad:

```text
ingestion reads source before source export is complete
```

Preferred:

```text
source_ready_task → ingestion_node
```

---

### Excessive Fan-In

Avoid nodes with too many upstream dependencies.

Bad:

```text
a
b
c
d
e
 \|/
ingestion_node
```

Prefer staged source readiness checks or aggregation.

---

## CLI Mapping

Offline integration nodes are managed through `wedatacli workflow task` and `wedatacli workflow apply`.

Supported operations include:

| Intent | Command |
|------------|----------|
| create node | `wedatacli workflow task create --task-type ingestion ...` |
| query node | `wedatacli workflow task get ...` |
| update parameters / description / resource / retry | `wedatacli workflow task update ...` |
| update dependencies | `wedatacli workflow task dependencies add|overwrite|clear ...` |
| update canvas position | `wedatacli workflow task move ...` |
| list published offline integration tasks | `wedatacli workflow task support-integration-tasks [--direction all|ingress|egress] [--keyword <kw>]` |
| list available DATA_ACCESS resources (only for explicit overrides) | `wedatacli workflow task support-resource-groups --task-type ingestion` |
| change referenced integration task declaratively | `wedatacli workflow apply --file ...` |

---

## Design Checklist

Before creating an offline integration node, verify:

- Offline data integration task exists
- Offline data integration task has a published version (`IsProd = 1`)
- If the task is still unpublished, publish it first before orchestration
- Data integration task has a valid `CosPath` for `TemplatePath`
- Required workflow exists
- Node name is meaningful and valid
- Source and target availability have been validated
- Parameters are defined
- Dependencies have been reviewed by the model
- DATA_ACCESS compute resource is auto-selected at creation; no manual resource selection unless the user explicitly requests an override
- Retry strategy is configured only for idempotent or transient-failure-safe offline integration tasks
- Timeout behavior follows platform defaults until a dedicated update command is implemented
- DAG dependency design has been reviewed by the model

An offline integration node is considered valid only when all required configuration is complete and model dependency review is complete.
