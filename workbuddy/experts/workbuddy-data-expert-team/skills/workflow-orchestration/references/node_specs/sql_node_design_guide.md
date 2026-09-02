# SQL Node Design Guide

## Purpose

This guide defines how SQL Task nodes should be designed, configured, and orchestrated within workflows.

A SQL node represents a workflow task that executes a SQL code file selected by `code_file_id` or `code_file_path`.

This guide focuses on workflow orchestration and node configuration.

It does NOT describe SQL implementation details.

SQL authoring, SQL optimization, and SQL business logic design belong to `studio-development`.

---

## Node Responsibilities

A SQL node is responsible for:

- Executing a SQL code file
- Participating in workflow DAG execution
- Consuming workflow parameters
- Consuming upstream dependencies
- Producing outputs for downstream tasks
- Configuring execution resources
- Configuring retry policy and relying on platform-default timeout behavior

A SQL node is NOT responsible for:

- Writing SQL code
- Optimizing SQL logic
- Designing business transformations
- Managing datasource connections

---

## Required Configuration

A SQL node must provide the following configuration:

| Field | Description |
|---------|-------------|
| workflow_id | Target workflow |
| task_name | SQL node name |
| code_file_id or code_file_path | Exactly one selector for the SQL file |

A SQL node cannot be created without `workflow_id`, `task_name`, and exactly one code-file selector. Workspace selection is no longer a CLI argument; the script uses the default workspace resolved by `wedatacli`.

---

## Optional Configuration

A SQL node may additionally configure:

| Field | Description |
|---------|-------------|
| code_file_version | Fixed released SQL code version |
| resource_group_id | Optional execution resource override; if omitted, the CLI auto-selects a default execution resource at creation |
| catalog | SQL default catalog override |
| schema | SQL default schema override |
| parameters | Full task parameter list |
| parameter_overrides | Partial task parameter overrides |
| depend_on | Upstream task ids |
| depend_condition | Dependency trigger policy (default: `ALL_SUCCESS`; supported values are listed in `workflow_guide.md`) |
| retry settings | Retry configuration |
| x / y | Node position in workflow canvas |

---

## Dependency Design Rules

SQL nodes should only depend on required upstream tasks.

Prefer simple and explicit dependency relationships.

Recommended:

```text
ingestion
    ↓
sql_clean
    ↓
sql_aggregate
```

Avoid:

```text
sql_a
  ↘
    sql_b
  ↗
sql_c
```

when dependencies are unnecessary.

Rules:

- Avoid circular dependencies
- Avoid hidden dependencies
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
target_table
partition_field
```

Prefer parameterization over hardcoded values.

Avoid:

```sql
where dt = '2025-01-01'
```

Prefer:

```sql
where dt = '${dt}'
```

### SQL Code-File Parameter Binding

For SQL tasks, `wedatacli workflow task create --task-type sql` resolves the selected code file and, when `--code-file-version` is omitted, the latest published SQL version.

Discovery path:

```text
code_file_id or code_file_path -> wedatacli workflow task create --task-type sql -> resolved CodeFileId / CodeFileVersion / Catalog / Schema
```

When the user provides a SQL `code_file_id` or `code_file_path`, follow these rules:

| User Intent | AI Action |
|---|---|
| Create SQL node from a selected code file and no parameter intent is mentioned | Create the task normally and do not invent extra task parameters |
| User asks which dynamic parameters are available | Run `wedatacli workflow task parameter-configs --workflow-id <id> --task-type sql` first |
| User provides the complete desired parameter set | Use `--parameters`; treat it as full replacement |
| Existing SQL node should only change selected parameter keys | Use `wedatacli workflow task update --parameter-overrides ...` |
| SQL code file, code version, catalog, or schema must change | Prefer `wedatacli workflow apply` (or recreate the task if the change is isolated) |

Do not blindly convert static SQL constants into workflow dynamic parameters. Static business constants such as `region=shanghai` should remain static unless the user explicitly asks to make them dynamic.

Recommended pattern:

```bash
wedatacli workflow task create \
  --workflow-id wf_001 \
  --task-type sql \
  --task-name sql_customer_profile \
  --code-file-path /Workspace/olist/dws/sql_customer_profile.sql \
  --parameter-overrides bizdate={{workflow.start_time.day}}
```

Use `--parameters` when you want to provide the complete task parameter list explicitly.
Use `wedatacli workflow task parameter-configs` to inspect workflow/task dynamic parameter keys available to SQL tasks.
Use `wedatacli workflow apply` when the desired SQL task definition change is broader than parameter/resource/retry edits.

#### Verification Rules

After creating or updating SQL parameters, query the node or workflow and verify:

- `ParamList` contains all expected static parameters.
- Overridden keys contain workflow dynamic expressions such as `{{workflow.trigger.time.iso_date}}`.
- Non-overridden SQL file defaults remain unchanged.
- `TaskTypePropertyList` still contains the expected `CodeFileId` and `CodeFileVersion`.

---

## Resource Configuration Rules

Compute resources are auto-selected at node creation. When `resource_group_id` is omitted from `wedatacli workflow task create --task-type sql`, the CLI resolves an available default execution resource automatically: it prefers a Job resource (`ResourceType` 2) and falls back to an Analytics resource (`ResourceType` 3) only when no Job resource is available. RAY cluster resources are excluded.

SQL nodes use available compute resources with `ResourceType` 2 (Job) or 3 (Analytics); RAY cluster resources are excluded.

Rules:

- Do not query or select a resource group when creating a SQL node; the tool selects it automatically.
- Only pass `resource_group_id` when the user explicitly requests a specific execution resource.
- For explicit overrides, use `wedatacli workflow task support-resource-groups --task-type sql` to list selectable resources and pick a valid one.
- Resource changes after creation go through `wedatacli workflow task update --resource-group-id ...`.

Avoid allocating excessive resources for lightweight tasks when an explicit override is chosen.

---

## Retry Strategy Rules

Retries should be configured only when failures are expected to be transient.

Examples:

Suitable for retry:

- Temporary infrastructure issues
- Resource contention
- Network instability

Not suitable for retry:

- SQL syntax errors
- Missing tables
- Invalid permissions
- Invalid business logic

Recommended:

```text
retry_times = 3
retry_interval = 5 minutes
```

Avoid unlimited retries.

---

## Timeout Strategy Rules

> **Note**: Timeout strategy configuration is not yet exposed as a dedicated SQL node command.
> Timeout behavior currently follows platform defaults. Update this section when `update_timeout_strategy` is implemented.

---

## Naming Conventions

Task names should be:

- Business meaningful
- Stable
- Easy to identify

Recommended:

```text
ods_user_profile

dwd_order_detail

dws_user_summary
```

Avoid:

```text
sql1

test_task

tmp
```

Naming should remain stable across workflow versions.

---

## Workflow Placement Patterns

### Pattern 1 — Single Transformation

```text
source
    ↓
sql_transform
```

Used for simple processing tasks.

---

### Pattern 2 — Multi-Stage Warehouse

```text
ods_user
    ↓
dwd_user
    ↓
dws_user
```

Used for warehouse modeling workflows.

---

### Pattern 3 — Aggregation Pipeline

```text
detail
    ↓
aggregate
    ↓
report
```

Used for reporting workflows.

---

### Pattern 4 — SQL + Quality Validation

```text
sql_transform
    ↓
quality_check
```

Used for production-grade pipelines.

---

## Anti Patterns

Avoid the following designs:

### Monolithic SQL Node

Avoid placing all transformations into a single SQL node.

Bad:

```text
one_sql_node
```

Preferred:

```text
extract
    ↓
transform
    ↓
aggregate
```

---

### Circular Dependencies

Never create:

```text
A → B → C → A
```

---

### Hardcoded Runtime Configuration

Avoid embedding:

```sql
database.table
fixed_date
environment_name
```

when parameters can be used.

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
sql_node
```

Prefer staged aggregation.

---

## CLI Mapping

SQL nodes are managed through `wedatacli workflow task` and `wedatacli workflow apply`.

Supported operations include:

| Intent | Command |
|------------|----------|
| create node | `wedatacli workflow task create --task-type sql ...` |
| query node | `wedatacli workflow task get ...` |
| update parameters / description / resource / retry | `wedatacli workflow task update ...` |
| update dependencies | `wedatacli workflow task dependencies add|overwrite|clear ...` |
| update canvas position | `wedatacli workflow task move ...` |
| list available compute resources (only for explicit overrides) | `wedatacli workflow task support-resource-groups --task-type sql` |
| list dynamic parameter configs | `wedatacli workflow task parameter-configs --workflow-id <id> --task-type sql` |
| change SQL code file / version declaratively | `wedatacli workflow apply --file ...` |

---

## Design Checklist

Before creating a SQL node, verify:

- SQL file already exists
- Required workflow exists
- Node name is meaningful
- Dependencies have been reviewed by the model
- Parameters are defined
- Compute resource is auto-selected at creation; no manual resource selection unless the user explicitly requests an override
- Retry strategy is configured if needed
- Timeout behavior follows platform defaults until a dedicated update command is implemented
- DAG dependency design has been reviewed by the model

A SQL node is considered valid only when all required configuration is complete and model dependency review is complete.
