# Workflow Guide

This guide consolidates workflow design, DAG dependency rules, workflow/task parameters, scheduling, and governance.

## 1. Design Baseline

- Keep orchestration and task logic separated: `wedatacli workflow` manages DAG, schedule, parameters, resource binding, and execution behavior only.
- Define clear `workflow_name` and `description` for every workflow; ownership/user fields should follow platform defaults or CLI response metadata.
- Prefer existing workflow and node patterns before introducing new structures.
- Review workflow structure before running.

## 2. Recommended Patterns

- Prefer atomic nodes and clear dependency chains.
- Keep DAG layered from source -> transform -> output.
- Use explicit task names to improve readability, parameter references, and troubleshooting.
- Reuse existing code files, integration tasks, and nested workflows where possible.

## 3. Dependency Rules

- Review DAG dependency consistency before saving, running, or enabling schedules; this is a model-reasoning step, not a dedicated CLI validation command.
- Avoid circular dependencies, self-loops, duplicate edges, and references to non-existing tasks.
- Create tasks under the same `workflow_id` sequentially one by one; wait for each task creation to finish successfully before creating the next node.
- Set dependencies at task level:
  - create-time: `wedatacli workflow task create --depend-on ...`
  - append new dependencies: `wedatacli workflow task dependencies add --depend-on ...`
  - replace existing dependencies or trigger policy: `wedatacli workflow task dependencies overwrite --depend-on ... --depend-condition ...`
  - clear dependencies: `wedatacli workflow task dependencies clear`
- Use `wedatacli workflow get --workflow-id ...` to inspect `Dependencies` and `TaskList[].DependOnList` after dependency changes.

### 3.1 Dependency Trigger Policies

`depend_on_run_condition` controls when a downstream task is triggered by upstream task states.

Supported values:

| Policy | Meaning | Trigger Timing |
|--------|---------|----------------|
| `ALL_SUCCESS` | All upstream tasks succeed | Wait for all upstream tasks to finish |
| `ALL_FAILED` | All upstream tasks fail | Wait for all upstream tasks to finish |
| `ALL_DONE` | All upstream tasks finish regardless of result | Wait for all upstream tasks to finish |
| `ALL_DONE_AT_LEAST_ONE_SUCCESS` | All upstream tasks finish and at least one succeeds | Wait for all upstream tasks to finish |
| `ALL_DONE_AT_LEAST_ONE_FAILED` | All upstream tasks finish and at least one fails | Wait for all upstream tasks to finish |
| `ALL_SKIPPED` | All upstream tasks are skipped | Wait for all upstream tasks to finish |
| `ONE_SUCCESS` | At least one upstream task succeeds | Trigger as soon as one upstream task succeeds |
| `ONE_FAILED` | At least one upstream task fails | Trigger as soon as one upstream task fails |
| `ONE_DONE` | At least one upstream task finishes | Trigger as soon as one upstream task finishes |
| `NONE_FAILED` | All upstream tasks finish and none fails | Wait for all upstream tasks to finish |
| `ALL_DONE_NONE_FAILED_AT_LEAST_ONE_SUCCESS` | All upstream tasks finish, none fails, and at least one succeeds | Wait for all upstream tasks to finish |
| `NONE_SKIPPED` | All upstream tasks finish and none is skipped | Wait for all upstream tasks to finish |

Default value is `ALL_SUCCESS`.

Failure states include failed-like upstream states such as `FAILED`, `TIMEOUT`, `TERMINATED`, and `UPSTREAM_FAILED`.

Use early-trigger policies (`ONE_SUCCESS`, `ONE_FAILED`, `ONE_DONE`) only when downstream tasks do not need all upstream outputs.

## 4. Workflow and Task Parameters

### 4.1 Parameter Model

- Workflow parameters and task parameters use key-value style (`ParamList`).
- Parameter names should be stable and readable because they are referenced by task code and downstream configuration.
- Parameter key constraints:
  - supports multiple languages, upper/lowercase letters, and digits
  - only `-` and `_` are supported as special characters
  - max length: 128
- Parameter value max length: 2048.

### 4.2 Parameter Priority

When the same parameter key exists in multiple places, the effective priority is:

1. Temporary runtime parameters supplied during rerun/run
2. Task parameters
3. Workflow parameters

### 4.3 Using Parameters in Tasks

- Task code should reference parameters through the syntax supported by its node type. Keep node-specific syntax and binding rules in the corresponding node guide.
- System built-in parameters should normally be mapped to stable custom parameter keys before being used in task code.
- Keep static business constants static unless the user explicitly asks to make them dynamic.
- Use workflow dynamic parameters for schedule-sensitive values, runtime context, workspace context, and task/upstream-task context.
- If the correct dynamic key is unclear, inspect the available parameter configuration for the target node type before choosing a value.
- Development-time/default parameter discovery is node-specific. Each node guide must define how to read parameters authored during node development.
- Dynamic replacement is shared conceptually: preserve unchanged defaults, override only selected keys with workflow/task/upstream dynamic expressions, then verify the final effective parameter list.
- Full replacement and partial override semantics are node-specific; follow the corresponding node guide before choosing command flags.

### 4.3.1 Parameter Binding Decision Rules

AI agents should classify each parameter before choosing a node command:

| Parameter Type | Example | Generic Handling |
|---|---|---|
| Static business constant | fixed region, environment, schema name | Keep as a task parameter or node artifact default |
| Schedule-sensitive value | business date, hour partition | Map to a workflow trigger/start-time parameter |
| Runtime override value | ad hoc rerun date or one-off flag | Pass at runtime or task level based on scope |
| Workspace/task context | workspace id, task run id | Use built-in workflow/task parameters |
| Upstream-derived value | upstream task output or result state | Use upstream-task references and ensure dependency exists |
| Unknown dynamic key | user asks for “workflow date” without naming the key | Query available parameter configs for the target node type |

Generic binding flow:

1. Identify the target node type.
2. Use the node guide to discover development-time/default parameters for that node type.
3. Classify which parameters are static and which should be dynamic.
4. Apply dynamic overrides only for selected keys.
5. Verify the final effective parameter list after create/update.

Do not blindly replace all static parameters with workflow built-ins. Prefer the minimal dynamic bindings required by the user's stated intent.

Node-specific details such as SQL code-file defaults, Notebook parameter handling, or Data Integration parameter syntax belong in their own node guides.

### 4.4 Built-in Parameter References

Common workflow-level built-ins include:

- `{{workflow.id}}`
- `{{workflow.name}}`
- `{{workflow.repair_count}}`
- `{{workflow.run_id}}`
- `{{workflow.start_time.year}}`, `{{workflow.start_time.month}}`, `{{workflow.start_time.day}}`, `{{workflow.start_time.hour}}`, `{{workflow.start_time.minute}}`, `{{workflow.start_time.second}}`
- `{{workflow.start_time.iso_date}}`, `{{workflow.start_time.iso_datetime}}`, `{{workflow.start_time.iso_weekday}}`, `{{workflow.start_time.timestamp_ms}}`
- `{{workflow.trigger.time.year}}`, `{{workflow.trigger.time.month}}`, `{{workflow.trigger.time.day}}`, `{{workflow.trigger.time.hour}}`, `{{workflow.trigger.time.minute}}`, `{{workflow.trigger.time.second}}`
- `{{workflow.trigger.time.iso_date}}`, `{{workflow.trigger.time.iso_datetime}}`, `{{workflow.trigger.time.iso_weekday}}`, `{{workflow.trigger.time.timestamp_ms}}`
- `{{workspace.id}}`, `{{workspace.url}}`

Common task-level built-ins include:

- `{{task.execution_count}}`
- `{{task.name}}`
- `{{task.run_id}}`
- `{{task.error_code}}`

Common upstream-task references include:

- `{{tasks.<upstream_task_name>.error_code}}`
- `{{tasks.<upstream_task_name>.execution_count}}`
- `{{tasks.<upstream_task_name>.result_state}}`
- `{{tasks.<upstream_task_name>.run_id}}`
- `{{tasks.<upstream_task_name>.values.<key>}}`
- `{{tasks.<upstream_task_name>.output.first_row}}`
- `{{tasks.<upstream_task_name>.output.first_row.<column_name>}}`
- `{{tasks.<upstream_task_name>.output.rows}}`

Upstream references require valid dependency relationships; the producing task should be an upstream node of the consuming task.

## 5. Scheduling Rules

### 5.1 Time Trigger

- Time-based scheduling uses Quartz cron expressions.
- Keep timezone explicit; default assumptions should not be hidden in workflow design.
- Typical trigger fields include:
  - `TriggerId`: existing trigger identifier used when updating an existing schedule
  - `TriggerMode`: `TIME_TRIGGER`
  - `SchedulerStatus`: `ACTIVE` or `PAUSED`
  - `SchedulerTimeZone`: for example `Asia/Shanghai`
  - `ConfigMode`: for example `COMMON`
  - `CycleType`: for example `DAY_CYCLE` or `HOUR_CYCLE`
  - `CrontabExpression`: Quartz cron expression
  - `StartTime` / `EndTime`: scheduling effective window
- Use `wedatacli workflow schedule set` for structured trigger changes.
- Use `wedatacli workflow schedule pause` / `resume` for schedule status changes.
- Prefer conservative frequency first, then tune based on runtime, SLA, and resource pressure.

### 5.1.1 Workflow Update Capabilities

`wedatacli workflow update-meta` is the imperative entrypoint for workflow metadata updates.

Recommended structured update fields:

- `--name` / `--description` -> `BaseInfo`
- `--parameters` -> `ParamList`
- `--labels` -> `LabelList`
- `--queue-mode` -> `AdvanceConfig.QueuingMode`
- `--max-concurrency` -> `AdvanceConfig.MaxConcurrentNum`
- `--monitor-metric` -> workflow monitor metrics when co-editing via `update-meta`
- `--alarm-group` + `--mute-when-*` -> workflow alarm config when co-editing via `update-meta`
- `wedatacli workflow monitor set` -> dedicated workflow monitor replacement entrypoint
- `wedatacli workflow alarm set` -> dedicated workflow alarm replacement entrypoint
- `--field-to-remove` -> `FieldToRemoveList`

Use `wedatacli workflow apply` when you need file-based synchronization, task-list level declarative changes, or type-specific task reference updates that are not exposed by imperative subcommands.

### 5.2 Continuous Arrival

- Use continuous-arrival scheduling only when the workflow is driven by continuous data arrival rather than a fixed cron window.
- If a workflow/task is configured as continuous arrival, tasks must not configure retry strategy.
- Treat continuous-arrival workflows as event/arrival driven and validate resource pressure carefully before important use.

### 5.3 Schedule Change Safety

- Review DAG dependency consistency with model reasoning before changing schedule.
- Record status changes explicitly (`ACTIVE` / `PAUSED`).
- Verify schedule changes with `wedatacli workflow get` before execution-sensitive changes.

## 6. Governance Rules

- Every workflow change should be traceable and reviewable.
- Maintain required monitoring metrics and alerts for critical workflows.
- When alarms reuse an existing notification target, resolve the channel with `wedatacli notification list|get` first and bind the resulting `NotificationId` via `--alarm-group`.
- Use consistent tags and concurrency settings for operational control.
- Inspect workflow configuration before executing important workflows.

## 7. Command Entry Points

- Workflow lifecycle, update, scheduling, run, and query: `wedatacli workflow <action> ...`
- Task creation and localized task mutations: `wedatacli workflow task <action> ...`
- Declarative workflow / task synchronization: `wedatacli workflow apply --file ...`
- Full command syntax and examples: `references/usage/command_usage_guide.md`

## 8. Quick Checklist

- [ ] Workflow metadata complete (`workflow_name` and `description`)
- [ ] DAG validated and acyclic
- [ ] All dependency references point to existing tasks
- [ ] Workflow/task parameters defined with clear priority expectations
- [ ] Built-in parameters mapped to custom keys before task-code usage
- [ ] Schedule verified (`cron`, timezone, active window, trigger status)
- [ ] Continuous-arrival tasks do not configure retry strategy
- [ ] Monitoring/alerts configured for critical workflows
- [ ] Commands verified via `wedatacli workflow ... -h` or `wedatacli workflow task ... -h`
