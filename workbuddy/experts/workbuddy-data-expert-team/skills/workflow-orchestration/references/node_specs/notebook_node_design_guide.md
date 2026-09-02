# Notebook Node Design Guide

## Purpose

This guide defines how Notebook Task nodes should be designed, configured, and orchestrated within workflows.

A Notebook node represents a workflow task that executes a notebook code file selected by `code_file_id` or `code_file_path`.

This guide focuses on workflow orchestration and node configuration.

It does NOT describe notebook implementation details.

Notebook authoring, cell organization, package dependency design, and business logic implementation belong to `studio-development`.

---

## Node Responsibilities

A Notebook node is responsible for:

- Executing a notebook code file
- Participating in workflow DAG execution
- Consuming workflow parameters
- Consuming upstream dependencies
- Producing outputs for downstream tasks
- Configuring execution resources
- Configuring retry policy and relying on platform-default timeout behavior

A Notebook node is NOT responsible for:

- Writing notebook code or cells
- Designing package dependencies
- Managing secrets or credentials
- Implementing business logic semantics
- Managing datasource connections

---

## Required Configuration

A Notebook node must provide the following configuration:

| Field | Description |
|---------|-------------|
| workflow_id | Target workflow |
| task_name | Notebook node name |
| code_file_id or code_file_path | Exactly one selector for the Notebook code file |

A Notebook node cannot be created without `workflow_id`, `task_name`, and exactly one code-file selector. Workspace selection is resolved from the default `wedatacli` workspace context.

---

## Optional Configuration

A Notebook node may additionally configure:

| Field | Description |
|---------|-------------|
| notebook_path | Notebook path. If omitted, it is resolved from the selected code file |
| resource_group_id | Optional execution resource override (Job resource only); if omitted, the CLI auto-selects a default execution resource at creation |
| parameters | Full task parameter list |
| parameter_overrides | Partial task parameter overrides |
| depend_on | Upstream task ids |
| depend_condition | Dependency trigger policy (default: `ALL_SUCCESS`; supported values are listed in `workflow_guide.md`) |
| retry settings | Retry configuration |
| x / y | Node position in workflow canvas |

---

## Notebook Reference Design Rules

`code_file_id` or `code_file_path` identifies the notebook code file used by the workflow task.

`notebook_path` can be provided explicitly. If omitted, the script resolves it from the selected code file.

Recommended:

```text
code_file_id = notebook_code_file_id
or
code_file_path = /Workspace/project/notebooks/user_profile.ipynb
notebook_path = /Workspace/project/notebooks/user_profile.ipynb
```

Avoid:

```text
notebook_path = /Users/name/local_notebook.ipynb
notebook_path = tmp.ipynb
```

Rules:

- Use stable notebook files that remain valid across workflow versions
- Keep notebook references explicit and reviewable
- Prefer versioned or platform-managed notebook artifacts over local-only paths
- Keep production notebooks deterministic and reproducible
- Avoid embedding secrets or environment-specific credentials in notebook cells
- Use runtime parameters or environment-managed secrets instead of hardcoded values

---

## Dependency Design Rules

Notebook nodes should only depend on required upstream tasks.

Prefer simple and explicit dependency relationships.

Recommended:

```text
ingestion
    ↓
notebook_feature_prepare
    ↓
sql_publish
```

Avoid:

```text
source_a
  ↘
    notebook_task
  ↗
source_b
```

when dependencies are unnecessary.

Rules:

- Avoid circular dependencies
- Avoid hidden dependencies through external side effects
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
input_table
output_table
sample_ratio
```

Prefer parameterization over hardcoded values.

Avoid:

```python
dt = "2025-01-01"
input_table = "dev.tmp_table"
```

Prefer:

```python
dt = "${dt}"
input_table = "${input_table}"
```

### Notebook Code-File Parameter Binding

For Notebook tasks, `wedatacli workflow task create --task-type notebook` resolves the selected notebook file and, when `--notebook-path` is omitted, auto-fills the notebook path from the selected code file.

Discovery path:

```text
code_file_id or code_file_path -> wedatacli workflow task create --task-type notebook -> resolved CodeFileId / NotebookPath
```

When the user provides a Notebook `code_file_id` or `code_file_path`, follow these rules:

| User Intent | AI Action |
|---|---|
| Create Notebook node from a selected code file and no parameter intent is mentioned | Create the task normally and do not invent extra task parameters |
| User asks which dynamic parameters are available | Run `wedatacli workflow task parameter-configs --workflow-id <id> --task-type notebook` first |
| User provides the complete desired parameter set | Use `--parameters`; treat it as full replacement |
| Existing Notebook node should only change selected parameter keys | Use `wedatacli workflow task update --parameter-overrides ...` |
| Notebook file or notebook path must change | Prefer `wedatacli workflow apply` (or recreate the task if the change is isolated) |

Do not blindly convert every Notebook parameter into a workflow dynamic parameter. Static business constants should remain static unless the user explicitly asks to make them dynamic.

Recommended pattern:

```bash
wedatacli workflow task create \
  --workflow-id wf_001 \
  --task-type notebook \
  --task-name notebook_customer_profile \
  --code-file-path /Workspace/project/notebooks/notebook_customer_profile.ipynb \
  --parameter-overrides bizdate={{workflow.start_time.day}}
```

Use `--parameters` when you want to provide the complete task parameter list explicitly.
Use `wedatacli workflow task parameter-configs` to inspect workflow/task dynamic parameter keys available to Notebook tasks.
Use `wedatacli workflow apply` when the desired Notebook task definition change is broader than parameter/resource/retry edits.

#### Verification Rules

After creating or updating Notebook parameters, query the node or workflow and verify:

- `ParamList` contains the expected keys
- Selected dynamic parameters use workflow expressions such as `{{workflow.start_time.day}}`
- Static parameters remain unchanged
- No unintended internal Notebook execution parameters are added to `ParamList`

---

## Resource Configuration Rules

Compute resources are auto-selected at node creation. When `resource_group_id` is omitted from `wedatacli workflow task create --task-type notebook`, the CLI resolves an available default execution resource automatically.

Notebook nodes only support compute resources with `ResourceType` 2 (Job). Analytics resources (`ResourceType` 3) are not selectable for Notebook nodes.

Rules:

- Do not query or select a resource group when creating a Notebook node; the tool selects it automatically.
- Only pass `resource_group_id` when the user explicitly requests a specific execution resource.
- For explicit overrides, use `wedatacli workflow task support-resource-groups --task-type notebook` to list selectable resources and pick a valid one.
- Resource changes after creation go through `wedatacli workflow task update --resource-group-id ...`.

Avoid allocating excessive resources for lightweight notebooks when an explicit override is chosen.

---

## Retry Strategy Rules

Retries should be configured only when failures are expected to be transient.

Examples:

Suitable for retry:

- Temporary infrastructure issues
- Resource contention
- Network instability
- Temporary upstream service unavailability

Not suitable for retry:

- Notebook cell syntax errors
- Missing modules or incompatible dependencies
- Invalid parameters
- Permission errors
- Non-idempotent writes without rollback protection
- Invalid business logic

Recommended:

```text
retry_times = 3
retry_interval = 5 minutes
```

Avoid unlimited retries.

Notebook tasks with side effects should be idempotent before retry is enabled.

---

## Timeout Strategy Rules

> **Note**: Timeout strategy configuration is not yet exposed as a dedicated Notebook node command.
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
notebook_feature_prepare
notebook_user_profile_etl
notebook_model_score_daily
```

Avoid:

```text
notebook1
test_task
tmp
```

Naming should remain stable across workflow versions.

---

## Workflow Placement Patterns

### Pattern 1 — Notebook Transformation

```text
source
    ↓
notebook_transform
```

Used for notebook-based custom transformation logic.

---

### Pattern 2 — Ingestion + Notebook + SQL Publish

```text
ingestion
    ↓
notebook_prepare
    ↓
sql_publish
```

Used when a notebook performs preprocessing before SQL publication.

---

### Pattern 3 — Feature Engineering Pipeline

```text
raw_features
    ↓
notebook_feature_engineering
    ↓
model_or_report
```

Used for feature engineering or advanced computation workflows.

---

### Pattern 4 — Notebook Validation Task

```text
upstream_task
    ↓
notebook_validate
    ↓
downstream_task
```

Used for custom validation or quality checks.

---

## Anti Patterns

Avoid the following designs:

### Exploration Notebook Used Directly in Production

Avoid using notebooks that contain ad-hoc cells, manual steps, or unstable execution order.

Bad:

```text
notebook contains exploratory cells and manual state assumptions
```

Preferred:

```text
notebook has deterministic top-to-bottom execution and explicit parameters
```

---

### Non-Idempotent Side Effects

Avoid tasks that repeatedly write duplicate or inconsistent results when retried.

Bad:

```text
notebook appends output without partition or deduplication
```

Preferred:

```text
notebook writes deterministic partition output
```

---

### Hidden External Dependencies

Avoid relying on undeclared local files, local packages, or machine-specific paths.

Bad:

```text
/Users/name/local_notebook.ipynb
local_config.json
```

Preferred:

```text
platform-managed code file selector + explicit parameters
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

```python
database = "prod_db"
token = "secret"
dt = "2025-01-01"
```

when parameters or environment-managed secrets can be used.

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
notebook_node
```

Prefer staged aggregation or validation.

---

## CLI Mapping

Notebook nodes are managed through `wedatacli workflow task` and `wedatacli workflow apply`.

Supported operations include:

| Intent | Command |
|------------|----------|
| create node | `wedatacli workflow task create --task-type notebook ...` |
| query node | `wedatacli workflow task get ...` |
| update parameters / description / resource / retry | `wedatacli workflow task update ...` |
| update dependencies | `wedatacli workflow task dependencies add|overwrite|clear ...` |
| update canvas position | `wedatacli workflow task move ...` |
| list available compute resources (only for explicit overrides) | `wedatacli workflow task support-resource-groups --task-type notebook` |
| list dynamic parameter configs | `wedatacli workflow task parameter-configs --workflow-id <id> --task-type notebook` |
| change Notebook file / path declaratively | `wedatacli workflow apply --file ...` |

---

## Design Checklist

Before creating a Notebook node, verify:

- Notebook code file already exists
- Notebook path is provided or resolvable from the selected code file
- Required workflow exists
- Node name is meaningful and valid
- Dependencies have been reviewed by the model
- Parameters are defined
- Compute resource is auto-selected at creation; no manual resource selection unless the user explicitly requests an override
- Retry strategy is configured only for idempotent or transient-failure-safe tasks
- Timeout behavior follows platform defaults until a dedicated update command is implemented
- DAG dependency design has been reviewed by the model

A Notebook node is considered valid only when all required configuration is complete and model dependency review is complete.
