# Nested Workflow Node Design Guide

## Purpose

This guide defines how Nested Workflow Task nodes should be designed, configured, and orchestrated within workflows.

A nested workflow node represents a workflow task that invokes another workflow by `nested_workflow_id`.

This guide focuses on workflow orchestration and node configuration.

It does NOT describe the implementation details of the referenced child workflow.

Child workflow design, task logic, and internal DAG design belong to their own workflow design documents.

---

## Node Responsibilities

A nested workflow node is responsible for:

- Referencing a child workflow through `nested_workflow_id`
- Participating in parent workflow DAG execution
- Consuming parent workflow parameters
- Passing task parameters explicitly to the nested workflow task context
- Consuming upstream dependencies in the parent workflow
- Producing completion status for downstream parent workflow tasks
- Relying on the child workflow's own task resource configuration
- Configuring retry policy and relying on platform-default timeout behavior

A nested workflow node is NOT responsible for:

- Creating or modifying the child workflow
- Managing child workflow internal tasks
- Designing child workflow business logic
- Configuring execution resource groups; nested workflow nodes do not need `resource_group_id`
- Replacing parent workflow dependency review
- Managing runtime instances or execution logs

---

## Required Configuration

A nested workflow node must provide the following configuration:

| Field | Description |
|---------|-------------|
| workflow_id | Parent workflow identifier |
| task_name | Nested workflow node name |
| nested_workflow_id | Referenced child workflow identifier |

A nested workflow node cannot be created without these fields. Workspace selection is no longer a CLI argument; the script uses the default workspace resolved by `wedatacli`.

---

## Optional Configuration

A nested workflow node may additionally configure:

| Field | Description |
|---------|-------------|
| parameters | Full task parameter list |
| parameter_overrides | Partial task parameter overrides |
| include_child_workflow_params | Include child workflow parameters in the create response for inspection |
| depend_on | Upstream task ids in the parent workflow |
| depend_condition | Dependency trigger policy (default: `ALL_SUCCESS`; supported values are listed in `workflow_guide.md`) |
| retry settings | Retry configuration |
| x / y | Node position in workflow canvas |

Do not configure `resource_group_id` for nested workflow nodes. Resource requirements belong to tasks inside the referenced child workflow.

---

## Nested Workflow Reference Rules

`nested_workflow_id` identifies the child workflow invoked by the parent workflow task.

Use `get_support_workflows` to list selectable workflows before creating a nested workflow node.

Recommended:

```text
parent_workflow
    ↓
nested_workflow_node(nested_workflow_id = child_workflow_id)
```

Avoid:

```text
workflow_a → nested workflow_a
workflow_a → workflow_b → workflow_a
```

Rules:

- Do not reference the same workflow as its own child
- Avoid recursive parent-child workflow chains
- Keep parent-child boundaries clear
- Prefer stable child workflow IDs
- Ensure the child workflow is owned and maintained independently
- Ensure child workflow parameters are explicitly documented

---

## Dependency Design Rules

Nested workflow nodes should only depend on required upstream tasks in the parent workflow.

Prefer simple and explicit dependency relationships.

Recommended:

```text
prepare_data
    ↓
nested_child_workflow
    ↓
publish_result
```

Avoid:

```text
a
b
c
 \|/
nested_child_workflow
```

when fan-in dependencies are not necessary.

Rules:

- Avoid circular dependencies in the parent workflow DAG
- Avoid hidden dependencies between parent and child workflows
- Prefer explicit dependency configuration
- Minimize fan-in complexity
- Keep parent workflow DAG understandable

---

## Parameter Design Rules

Workflow-wide configuration should be defined as parent workflow parameters.

Parameters required by the child workflow should be passed explicitly through the nested workflow node task parameters.

Examples:

Parent workflow parameter:

```text
dt
env
region
```

Nested workflow task parameter:

```text
child_dt
child_env
batch_id
```

Prefer explicit parameter propagation over implicit child workflow assumptions.

Avoid:

```text
child workflow reads undeclared parent runtime state
```

Prefer:

```text
parent dt -> nested task parameter child_dt
parent env -> nested task parameter child_env
```

### Child Workflow Parameter Binding

For nested workflow tasks, development-time/default parameters come from the referenced child workflow's workflow parameters.

Discovery path:

```text
nested_workflow_id -> wedatacli workflow task child-workflow-parameters -> child workflow parameter map
```

When the user provides a `nested_workflow_id`, follow these rules:

| User Intent | AI Action |
|---|---|
| Create nested workflow node from `nested_workflow_id` and no parameter intent is mentioned | Create the task normally and do not invent extra task parameters |
| Inspect child workflow parameters before deciding | Run `wedatacli workflow task child-workflow-parameters --nested-workflow-id ...` |
| User provides the complete desired parameter set | Use `--parameters`; treat it as full replacement |
| Existing nested workflow node should only change selected parameter keys | Use `wedatacli workflow task update --parameter-overrides ...` |
| Child workflow reference itself must change | Prefer `wedatacli workflow apply` (or recreate the task if the change is isolated) |
| User asks which dynamic parameters are available in the parent task context | Run `wedatacli workflow task parameter-configs --workflow-id <id> --task-type nested-workflow` first |

Do not blindly convert every child workflow parameter into a dynamic parent workflow expression. Static business constants should remain static unless the user explicitly asks to make them dynamic.

Recommended pattern:

```bash
wedatacli workflow task create \
  --workflow-id wf_001 \
  --task-type nested-workflow \
  --task-name nested_customer_profile \
  --nested-workflow-id child_wf_001 \
  --parameter-overrides bizdate={{workflow.start_time.day}}
```

Use `--parameters` when you want to provide the complete task parameter list explicitly.
Use `wedatacli workflow task child-workflow-parameters` to inspect default parameters defined by the child workflow.
Use `wedatacli workflow task parameter-configs` to inspect workflow/task dynamic parameter keys available to nested workflow tasks..

#### Verification Rules

After creating or updating nested workflow parameters, query the node or workflow and verify:

- `ParamList` contains the expected keys
- Selected dynamic parameters use parent workflow expressions such as `{{workflow.start_time.day}}`
- Static child workflow parameters remain unchanged
- No child workflow parameter is omitted unless intentionally removed

---

## Resource Configuration Rules

Nested workflow nodes do not configure `resource_group_id`.

A nested workflow node only references and triggers a child workflow. Execution resources are defined by tasks inside the referenced child workflow, not by the parent nested workflow node.

Therefore:

- Do not request, infer, or auto-fill a resource group when creating or updating nested workflow nodes
- Do not call `wedatacli workflow task support-resource-groups --task-type nested-workflow` as part of nested workflow node design
- If the user mentions resource requirements, apply them to the child workflow task design instead

---

## Retry Strategy Rules

Retries should be configured only when failures are expected to be transient and the child workflow can tolerate reruns.

Examples:

Suitable for retry:

- Temporary infrastructure issues
- Resource contention
- Network instability
- Temporary child workflow scheduling failure

Not suitable for retry:

- Child workflow logic errors
- Invalid child workflow parameters
- Permission errors
- Non-idempotent child workflow side effects
- Parent-child contract mismatch

Recommended:

```text
retry_times = 3
retry_interval = 5 minutes
```

Avoid unlimited retries.

Child workflows should be idempotent before retry is enabled on the nested workflow node.

---

## Timeout Strategy Rules

> **Note**: Timeout strategy configuration is not yet exposed as a dedicated Nested Workflow node command.
> Timeout behavior currently follows platform defaults. Update this section when `update_timeout_strategy` is implemented.

---

## Enabled Flag Rules

The current `wedatacli workflow task create --task-type nested-workflow` flow does not expose a dedicated `enabled` flag.

If the node enablement state must be managed as part of a larger workflow refactor, prefer editing the workflow spec and applying it through `wedatacli workflow apply`.

---

## Naming Conventions

Task names should be:

- Business meaningful
- Stable
- Easy to identify
- Valid according to the script rule: Chinese, English, digits, `_`, and `-` only

Recommended:

```text
nested_daily_feature_pipeline
run_child_order_workflow
subflow_user_profile_build
```

Avoid:

```text
nested1
test_task
tmp
```

Naming should remain stable across workflow versions.

---

## Workflow Placement Patterns

### Pattern 1 — Parent Delegates Child Pipeline

```text
prepare_context
    ↓
nested_child_pipeline
    ↓
collect_result
```

Used when a parent workflow delegates a cohesive child pipeline.

---

### Pattern 2 — Reusable Child Workflow

```text
workflow_a ─┐
            ↓
      nested_quality_check
            ↑
workflow_b ─┘
```

Used when multiple parent workflows reuse a common child workflow.

---

### Pattern 3 — Domain Boundary Split

```text
sales_prepare
    ↓
nested_finance_workflow
    ↓
sales_publish
```

Used when child workflow ownership belongs to another domain or team.

---

### Pattern 4 — Large DAG Decomposition

```text
stage_1
    ↓
nested_stage_2_workflow
    ↓
stage_3
```

Used to keep parent workflow DAG readable and maintainable.

---

## Anti Patterns

Avoid the following designs:

### Recursive Workflow References

Never create direct or indirect recursive nested workflow chains.

Bad:

```text
workflow_a → workflow_b → workflow_a
```

Preferred:

```text
workflow_a → workflow_b → workflow_c
```

with no cycle.

---

### Hidden Parent-Child Contract

Avoid child workflows that rely on undocumented parent state.

Bad:

```text
child workflow reads implicit runtime state from parent
```

Preferred:

```text
parent passes explicit task parameters to nested workflow node
```

---

### Over-Nesting

Avoid using nested workflows for trivial single-task logic.

Bad:

```text
parent → nested workflow containing only one simple task
```

Preferred:

```text
parent → direct task node
```

---

### Non-Idempotent Child Workflow Retry

Avoid retrying nested workflows that produce duplicate side effects.

Bad:

```text
retry nested workflow that appends duplicate outputs
```

Preferred:

```text
child workflow writes deterministic partition output
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
nested_workflow_node
```

Prefer staged aggregation or validation.

---

## CLI Mapping

Nested workflow nodes are managed through `wedatacli workflow task` and `wedatacli workflow apply`.

Supported operations include:

| Intent | Command |
|------------|----------|
| create node | `wedatacli workflow task create --task-type nested-workflow ...` |
| query node | `wedatacli workflow task get ...` |
| update parameters / description / retry | `wedatacli workflow task update ...` |
| update dependencies | `wedatacli workflow task dependencies add|overwrite|clear ...` |
| update canvas position | `wedatacli workflow task move ...` |
| list selectable child workflows | `wedatacli workflow task support-workflows ...` |
| inspect child workflow parameters | `wedatacli workflow task child-workflow-parameters --nested-workflow-id ...` |
| list dynamic parameter configs | `wedatacli workflow task parameter-configs --workflow-id <id> --task-type nested-workflow` |
| change child workflow reference declaratively | `wedatacli workflow apply --file ...` |

---

## Design Checklist

Before creating a nested workflow node, verify:

- Referenced child workflow exists
- Child workflow is not the same as the parent workflow
- Parent-child workflow chain is not recursive
- Required parent workflow exists
- Node name is meaningful and valid
- Required child parameters are explicitly mapped
- Dependencies have been reviewed by the model
- No `resource_group_id` is configured on the nested workflow node
- Retry strategy is configured only for idempotent or transient-failure-safe child workflows
- `enabled` is set intentionally if provided
- Timeout behavior follows platform defaults until a dedicated update command is implemented
- Parent workflow DAG dependency design has been reviewed by the model

A nested workflow node is considered valid only when all required configuration is complete and model dependency review is complete.
