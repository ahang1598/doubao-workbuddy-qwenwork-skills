# Quality Node Design Guide

## Purpose

This guide defines how Data Quality monitoring nodes should be designed, configured, and orchestrated within workflows.

A quality node represents a workflow task that executes a published data quality task by `quality_task_id`.

This guide focuses on workflow orchestration and node configuration.

It does NOT describe rule authoring, datasource setup, table profiling, alert policy design, or quality rule implementation details.

---

## Node Responsibilities

A quality node is responsible for:

- Referencing a published data quality task through `quality_task_id`
- Resolving the published quality task template path
- Resolving required quality aspect configuration
- Participating in workflow DAG execution
- Consuming workflow parameters
- Consuming upstream dependencies
- Configuring execution resources
- Configuring retry policy and relying on platform-default timeout behavior

A quality node is NOT responsible for:

- Creating data quality tasks
- Designing quality rules
- Designing alert policies
- Managing datasource connections
- Managing runtime instances or execution logs

---

## Required Configuration

A quality node must provide the following configuration:

| Field | Description |
|---|---|
| workflow_id | Target workflow identifier |
| task_name | Quality node name |
| quality_task_id | Published data quality task identifier |

A quality node cannot be created without these fields. Workspace selection is resolved from the default `wedatacli` workspace context.

---

## Optional Configuration

A quality node may additionally configure:

| Field | Description |
|---|---|
| resource_group_id | Optional execution resource override; if omitted, the CLI auto-selects a default resource at creation |
| parameters | Task parameters |
| depend_on | Upstream task ids |
| depend_condition | Dependency trigger policy (default: `ALL_SUCCESS`; supported values are listed in `workflow_guide.md`) |
| retry settings | Retry configuration |
| x / y | Node position in workflow canvas |

---

## Quality Task Reference Rules

`quality_task_id` identifies the published quality monitoring task executed by the workflow node.

Use `wedatacli workflow task support-quality-tasks` to list selectable published quality tasks.

During creation, `wedatacli workflow task create --task-type quality` resolves the required workflow node properties from `ListDataQualityTasksForWorkflow`:

1. Match `quality_task_id` against selectable quality tasks.
2. Ensure the selected task has `TaskConfig.PublishedCosPath`.
3. Resolve `AspectInfo.ExecutionType`.
4. Copy `AspectInfo.BeforeAspect` and `AspectInfo.AfterAspect` when present.
5. Write the required quality task reference into the node configuration.

Required workflow task properties:

```text
TaskTypeName = DATA_QUALITY
SourceUniqueId = published quality task id
Source = 4
ExecutionType = AspectInfo.ExecutionType
TemplatePath = TaskConfig.PublishedCosPath
BeforeAspect = AspectInfo.BeforeAspect, when present
AfterAspect = AspectInfo.AfterAspect, when present
```

Rules:

- Only use published quality tasks with a valid `PublishedCosPath`.
- If the selected quality task is not published, publish it first before creating the quality node.
- Keep quality rule authoring outside this workflow orchestration node.
- Do not handcraft `BeforeAspect` or `AfterAspect`; resolve them from the selected published task.
- Do not run quality tasks without an explicit upstream dependency when they validate upstream output.

---

## Dependency Design Rules

Quality nodes are commonly used after ingestion or transformation tasks.

Recommended:

```text
ingestion_source
    ↓
sql_transform
    ↓
quality_check
    ↓
publish_result
```

Avoid:

```text
quality_check
```

when the quality check implicitly depends on upstream data readiness.

Rules:

- Avoid circular dependencies.
- Prefer explicit dependencies from the task that produces the checked table or partition.
- Keep quality checks close to the data-producing node they validate.
- Use `depend_on_run_condition = ALL_SUCCESS` unless a fallback or audit pattern explicitly requires another condition.

---

## Parameter Design Rules

Workflow-wide configuration should be defined as workflow parameters.

Task-specific configuration should be defined as task parameters only when the published quality task supports it.

Common workflow parameters:

```text
dt
env
region
```

Common quality task parameters:

```text
biz_date
partition_value
run_mode
```

Prefer parameterization over hardcoded partitions.

---

## Resource Configuration Rules

Quality nodes use job or analytics execution resources with `ResourceType` 2 (Job) or 3 (Analytics); RAY cluster resources are excluded.

Compute resources are auto-selected at node creation. When `resource_group_id` is omitted from `wedatacli workflow task create --task-type quality`, the CLI prefers an available Job resource (`ResourceType` 2) and falls back to an Analytics resource (`ResourceType` 3) only when no Job resource is available.

Rules:

- Do not query or select a resource group when creating a quality node; the tool selects it automatically.
- Only pass `resource_group_id` when the user explicitly requests a specific execution resource. For such overrides, use `wedatacli workflow task support-resource-groups --task-type quality` to list selectable resources and pick a valid one.
- If `resource_group_id` is provided, the script validates that the resource is available before updating the node.

---

## Retry Strategy Rules

Retries should be configured only when failures are expected to be transient.

Examples:

```json
{"MaxRetryTime":3,"RetryBetweenWaitTime":5}
```

Avoid retrying deterministic rule failures where the quality task correctly identifies invalid data.

---

## Commands

List selectable quality tasks:

```bash
wedatacli workflow task support-quality-tasks --page 1 --page-size 50
```

Create a quality node:

```bash
wedatacli workflow task create \
  --workflow-id wf_001 \
  --task-type quality \
  --task-name quality_check \
  --quality-task-id quality_task_001 \
  --depend-on upstream_task_id
```

Update description, parameters, resource group, or retry policy:

```bash
wedatacli workflow task update \
  --workflow-id wf_001 \
  --task-id task_001 \
  --description "quality gate for upstream output"
```

Change the referenced quality task declaratively when needed:

```bash
wedatacli workflow apply --file desired_workflow.yaml --workflow-id wf_001
```

Query supported dynamic parameters:

```bash
wedatacli workflow task parameter-configs --workflow-id wf_001 --task-type quality
```

---

## Validation Checklist

Before saving or running a workflow containing quality nodes:

- `TaskTypeName` is `DATA_QUALITY`.
- `SourceUniqueId` equals a selectable published quality task id.
- `TemplatePath` is not empty.
- `ExecutionType` is not empty.
- `AfterAspect` or `BeforeAspect` is copied from the selected quality task when returned by the platform.
- `ResourceGroupId` points to an available job or analytics execution resource, either selected explicitly or resolved by the script.
- Dependencies represent the actual data readiness relationship.
- Retry strategy does not mask deterministic quality rule failures.
