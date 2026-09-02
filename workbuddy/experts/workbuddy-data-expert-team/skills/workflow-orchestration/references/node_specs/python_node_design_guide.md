# Python Node Design Guide

## Purpose

This guide defines how Python Task nodes should be designed, configured, and orchestrated within workflows.

A Python node represents a workflow task that executes a Python code file selected by `code_file_id` or `code_file_path`.

This guide focuses on workflow orchestration and node configuration.

It does NOT describe Python implementation details.

Python code authoring, package dependency design, and business logic implementation belong to `studio-development`.

---

## Node Responsibilities

A Python node is responsible for:

- Executing a Python code file resolved to `SourcePath`
- Participating in workflow DAG execution
- Consuming workflow parameters
- Consuming upstream dependencies
- Producing outputs for downstream tasks
- Configuring execution resources
- Configuring retry policy and relying on platform-default timeout behavior

A Python node is NOT responsible for:

- Writing Python code
- Designing Python package dependencies
- Managing secrets or credentials
- Implementing business logic semantics
- Managing datasource connections

---

## Required Configuration

A Python node must provide the following configuration:

| Field | Description |
|---------|-------------|
| workflow_id | Target workflow |
| task_name | Python node name |
| code_file_id or code_file_path | Exactly one selector for the Python code file |

A Python node cannot be created without `workflow_id`, `task_name`, and exactly one code-file selector. Workspace selection is resolved from the default `wedatacli` workspace context.

---

## Optional Configuration

A Python node may additionally configure:

| Field | Description |
|---------|-------------|
| source_path | Python source path. If omitted, it is resolved from the selected code file |
| resource_group_id | Optional execution resource override (Job resource only); if omitted, the CLI auto-selects a default execution resource at creation |
| parameters | Full task parameter list |
| parameter_overrides | Partial task parameter overrides |
| depend_on | Upstream task ids |
| depend_condition | Dependency trigger policy (default: `ALL_SUCCESS`; supported values are listed in `workflow_guide.md`) |
| retry settings | Retry configuration |
| x / y | Node position in workflow canvas |

---

## Code File Reference Design Rules

`code_file_id` or `code_file_path` identifies the Python code file used by the workflow task.

`source_path` can be provided explicitly. If omitted, the script resolves it from the selected code file and uses the resolved path for Python task creation.

Recommended:

```text
code_file_id = python_code_file_id
or
code_file_path = /Workspace/olist/dws/dws_sales_external_sync.py
source_path = /Workspace/olist/dws/dws_sales_external_sync.py
```

Avoid:

```text
source_path = /Users/name/local_script.py
source_path = tmp.py
```

Rules:

- Use stable Python code files that remain valid across workflow versions
- Keep code file references explicit and reviewable
- Prefer platform-managed code file artifacts over local-only paths
- Avoid embedding secrets or environment-specific credentials in Python code
- Use runtime parameters or environment-managed secrets instead of hardcoded values

---

## Dependency Design Rules

Python nodes should only depend on required upstream tasks.

Prefer simple and explicit dependency relationships.

Recommended:

```text
ingestion
    ↓
python_transform
    ↓
sql_publish
```

Avoid:

```text
source_a
  ↘
    python_task
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
input_path
output_path
batch_size
```

Prefer parameterization over hardcoded values.

Avoid:

```python
dt = "2025-01-01"
input_path = "/tmp/local.csv"
```

Prefer:

```python
dt = "${dt}"
input_path = "${input_path}"
```

### Python Code-File Parameter Binding

For Python tasks, `wedatacli workflow task create --task-type python` resolves the selected code file and, when `--source-path` is omitted, auto-fills the Python source path from the selected file metadata.

Discovery path:

```text
code_file_id or code_file_path -> wedatacli workflow task create --task-type python -> resolved CodeFileId / SourcePath
```

When the user provides a Python `code_file_id` or `code_file_path`, follow these rules:

| User Intent | AI Action |
|---|---|
| Create Python node from a selected code file and no parameter intent is mentioned | Create the task normally and do not invent extra task parameters |
| User asks which dynamic parameters are available | Run `wedatacli workflow task parameter-configs --workflow-id <id> --task-type python` first |
| User provides the complete desired parameter set | Use `--parameters`; treat it as full replacement |
| Existing Python node should only change selected parameter keys | Use `wedatacli workflow task update --parameter-overrides ...` |
| Python code file or source path must change | Prefer `wedatacli workflow apply` (or recreate the task if the change is isolated) |

Do not blindly convert every Python code-file parameter into a workflow dynamic parameter. Static business constants should remain static unless the user explicitly asks to make them dynamic.

Recommended pattern:

```bash
wedatacli workflow task create \
  --workflow-id wf_001 \
  --task-type python \
  --task-name python_customer_profile \
  --code-file-path /Workspace/olist/dws/python_customer_profile.py \
  --parameter-overrides bizdate={{workflow.start_time.day}}
```

Use `--parameters` when you want to provide the complete task parameter list explicitly.
Use `wedatacli workflow task parameter-configs` to inspect workflow/task dynamic parameter keys available to Python tasks.
Use `wedatacli workflow apply` when the desired Python task definition change is broader than parameter/resource/retry edits.

#### Verification Rules

After creating or updating Python parameters, query the node or workflow and verify:

- `ParamList` contains all expected static parameters.
- Overridden keys contain workflow dynamic expressions such as `{{workflow.trigger.time.iso_date}}`.
- Non-overridden Python file defaults remain unchanged.
- The node still points to the expected selected code file and `source_path`.

---

## Resource Configuration Rules

Compute resources are auto-selected at node creation. When `resource_group_id` is omitted from `wedatacli workflow task create --task-type python`, the CLI resolves an available default execution resource automatically.

Python nodes only support compute resources with `ResourceType` 2 (Job). Analytics resources (`ResourceType` 3) are not selectable for Python nodes.

Rules:

- Do not query or select a resource group when creating a Python node; the tool selects it automatically.
- Only pass `resource_group_id` when the user explicitly requests a specific execution resource.
- For explicit overrides, use `wedatacli workflow task support-resource-groups --task-type python` to list selectable resources and pick a valid one.
- Resource changes after creation go through `wedatacli workflow task update --resource-group-id ...`.

Avoid allocating excessive resources for lightweight scripts when an explicit override is chosen.

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

- Python syntax errors
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

Python tasks with side effects should be idempotent before retry is enabled.

---

## Timeout Strategy Rules

> **Note**: Timeout strategy configuration is not yet exposed as a dedicated Python node command.
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
python_user_profile_etl
feature_extract_daily
risk_score_batch
```

Avoid:

```text
python1
test_task
tmp
```

Naming should remain stable across workflow versions.

---

## Workflow Placement Patterns

### Pattern 1 — Python Transformation

```text
source
    ↓
python_transform
```

Used for custom transformation logic that is not expressed as SQL.

---

### Pattern 2 — Ingestion + Python + SQL Publish

```text
ingestion
    ↓
python_clean
    ↓
sql_publish
```

Used when Python performs preprocessing before SQL publication.

---

### Pattern 3 — Feature Engineering Pipeline

```text
raw_features
    ↓
python_feature_extract
    ↓
model_or_report
```

Used for feature extraction or advanced computation workflows.

---

### Pattern 4 — Python Validation Task

```text
upstream_task
    ↓
python_validate
    ↓
downstream_task
```

Used for custom validation or quality checks.

---

## Anti Patterns

Avoid the following designs:

### Non-Idempotent Side Effects

Avoid tasks that repeatedly write duplicate or inconsistent results when retried.

Bad:

```text
python_task writes append-only output without partition or deduplication
```

Preferred:

```text
python_task writes deterministic partition output
```

---

### Hidden External Dependencies

Avoid relying on undeclared local files, local Python packages, or machine-specific paths.

Bad:

```text
/Users/name/local_script.py
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
python_node
```

Prefer staged aggregation or validation.

---

## CLI Mapping

Python nodes are managed through `wedatacli workflow task` and `wedatacli workflow apply`.

Supported operations include:

| Intent | Command |
|------------|----------|
| create node | `wedatacli workflow task create --task-type python ...` |
| query node | `wedatacli workflow task get ...` |
| update parameters / description / resource / retry | `wedatacli workflow task update ...` |
| update dependencies | `wedatacli workflow task dependencies add|overwrite|clear ...` |
| update canvas position | `wedatacli workflow task move ...` |
| list available compute resources (only for explicit overrides) | `wedatacli workflow task support-resource-groups --task-type python` |
| list dynamic parameter configs | `wedatacli workflow task parameter-configs --workflow-id <id> --task-type python` |
| change Python code file / source path declaratively | `wedatacli workflow apply --file ...` |

---

## Design Checklist

Before creating a Python node, verify:

- Python code file already exists
- Source path is provided or resolvable from the selected code file
- Required workflow exists
- Node name is meaningful and valid
- Dependencies have been reviewed by the model
- Parameters are defined
- Compute resource is auto-selected at creation; no manual resource selection unless the user explicitly requests an override
- Retry strategy is configured only for idempotent or transient-failure-safe tasks
- Timeout behavior follows platform defaults until a dedicated update command is implemented
- DAG dependency design has been reviewed by the model

A Python node is considered valid only when all required configuration is complete and model dependency review is complete.
