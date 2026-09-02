# AI Command Guide

This guide is the execution reference for `workflow-orchestration` after removing local helper scripts.

All workflow orchestration operations in this skill must use `wedatacli workflow` and `wedatacli workflow task`.

When the user wants to bind an existing alert channel, use `wedatacli notification list|get` first to discover or confirm the target `NotificationId` before calling workflow/task alarm mutation commands.

## 1. Goal

Use `wedatacli workflow` to inspect, create, update, validate, schedule, and run workflows.

Use `wedatacli workflow task` to create and manage workflow nodes.

Use `wedatacli workflow apply` when you need declarative, file-based workflow updates or type-specific task changes that are not exposed by imperative task update commands.

## 2. Core Rules for AI Agents

1. Query first, change second.
2. Prefer `wedatacli workflow get` or `wedatacli workflow task get` before mutating existing resources.
3. For the same `workflow_id`, create workflow tasks sequentially one by one. Do not run task creation in parallel for the same workflow.
4. After every mutation, run a follow-up query to verify the result.
5. Treat the command as successful only when the process exit code is `0` and the returned JSON payload confirms the expected effect.
6. Before `wedatacli workflow run`, show the target workflow and intended action, obtain explicit user confirmation for that exact step, then execute.
7. Use imperative commands for localized edits; use `wedatacli workflow apply` for declarative bulk changes, file-based synchronization, or type-specific task reference changes.

## 3. Output Contract

The modern CLI returns JSON envelopes like:

```json
{"status":"success","summary":"Created workflow demo","payload":{}}
```

Read fields in this order:

| Field | Meaning |
|---|---|
| `status` | `success` means the command finished successfully |
| `summary` | short human-readable summary |
| `payload` | returned data or mutation result |
| `warnings` | non-fatal warnings that still need operator attention |
| `error_code` / `error` | indicates failure |

## 4. Command Selection

### 4.1 Workflow Commands

| Command | Use it when you need to... |
|---|---|
| `wedatacli workflow list` | find existing workflows |
| `wedatacli workflow get` | inspect current workflow state before or after a change |
| `wedatacli workflow create` | create a new workflow |
| `wedatacli workflow update-meta` | update workflow metadata, parameters, labels, alarms, monitors, or concurrency |
| `wedatacli workflow alarm get` / `set` / `clear` | inspect, replace, or clear workflow alarm config |
| `wedatacli workflow monitor get` / `set` / `clear` | inspect, replace, or clear workflow monitor config |
| `wedatacli workflow schedule set` | create or update a schedule |
| `wedatacli workflow schedule pause` / `resume` | disable or re-enable schedules |
| `wedatacli workflow run` | trigger a manual run |
| `wedatacli workflow export` / `diff` / `apply` | manage workflow specs declaratively |

### 4.2 Task Commands

| Command | Use it when you need to... |
|---|---|
| `wedatacli workflow task create` | add a node to a workflow |
| `wedatacli workflow task get` | inspect task details |
| `wedatacli workflow task update` | update description, parameters, resource group, or retry policy |
| `wedatacli workflow task delete` | delete a node |
| `wedatacli workflow task dependencies get` | inspect upstream/downstream links |
| `wedatacli workflow task dependencies add` | append upstream dependencies |
| `wedatacli workflow task dependencies overwrite` | replace dependency settings |
| `wedatacli workflow task dependencies clear` | clear dependencies |
| `wedatacli workflow task move` | change task canvas position |
| `wedatacli workflow task alarm set/clear` | manage task alarms |
| `wedatacli workflow task monitor set/clear` | manage task monitors |

### 4.3 Discovery Commands

| Command | Purpose |
|---|---|
| `wedatacli workflow task support-resource-groups --task-type <type>` | list selectable resource groups for a task type (only needed for explicit resource overrides; node creation auto-selects compute resources) |
| `wedatacli workflow task parameter-configs --workflow-id <id> --task-type <type>` | list dynamic parameter configs |
| `wedatacli workflow task support-integration-tasks [--direction all|ingress|egress] [--keyword <kw>]` | list published offline integration tasks |
| `wedatacli workflow task support-quality-tasks` | list published quality tasks |
| `wedatacli workflow task support-workflows` | list nestable child workflows |
| `wedatacli workflow task child-workflow-parameters --nested-workflow-id <id>` | inspect child workflow parameters |
| `wedatacli notification list` / `get` | discover reusable notification channels and confirm `NotificationId` before `workflow alarm set` or `workflow task alarm set` |

## 5. Minimal Command Templates

### 5.1 Workflow

```bash
wedatacli workflow list --page 1 --page-size 50
wedatacli workflow get --workflow-id wf_001
wedatacli workflow create --name demo_wf --description "demo"
wedatacli workflow update-meta --workflow-id wf_001 --description "updated"
wedatacli workflow run --workflow-id wf_001
```

### 5.2 Workflow Schedule

```bash
wedatacli workflow schedule set \
  --workflow-id wf_001 \
  --scheduler-status ACTIVE \
  --trigger-mode TIME_TRIGGER \
  --timezone Asia/Shanghai \
  --config-mode COMMON \
  --cycle-type DAY_CYCLE \
  --cron "0 0 0 * * ? *" \
  --start-time "2026-07-01 00:00:00" \
  --end-time "2099-12-31 23:59:59"

wedatacli workflow schedule pause --workflow-id wf_001
wedatacli workflow schedule resume --workflow-id wf_001
```

### 5.3 SQL / Python / Notebook Tasks

Use exactly one selector: `--code-file-id` or `--code-file-path`.

```bash
wedatacli workflow task create \
  --workflow-id wf_001 \
  --task-type sql \
  --task-name sql_task \
  --code-file-path /Workspace/project/tasks/sql_task.sql

wedatacli workflow task create \
  --workflow-id wf_001 \
  --task-type python \
  --task-name py_task \
  --code-file-path /Workspace/project/tasks/py_task.py

wedatacli workflow task create \
  --workflow-id wf_001 \
  --task-type notebook \
  --task-name nb_task \
  --code-file-path /Workspace/project/notebooks/nb_task.ipynb
```

### 5.4 Offline Integration / Quality / Nested Workflow Tasks

```bash
wedatacli workflow task support-integration-tasks --page 1 --page-size 50 --direction all --keyword orders
wedatacli workflow task create --workflow-id wf_001 --task-type ingestion --task-name sync_task --integration-task-id integration_task_001

wedatacli workflow task support-quality-tasks --page 1 --page-size 50
wedatacli workflow task create --workflow-id wf_001 --task-type quality --task-name quality_check --quality-task-id quality_task_001

wedatacli workflow task support-workflows --page 1 --page-size 50
wedatacli workflow task child-workflow-parameters --nested-workflow-id nested_wf_001
wedatacli workflow task create --workflow-id wf_001 --task-type nested-workflow --task-name nested_task --nested-workflow-id nested_wf_001
```

Notes:
- `support-integration-tasks` supports optional `--keyword <kw>` filtering in addition to `--direction`.
- When the integration-task response is larger than 1024 bytes or contains more than 3 items, the CLI writes only `payload.items` to `output_file`; stdout keeps paging metadata, `direction`, `keyword`, and one `payload.items_example` sample item.
- The generated spill file is created in the system temp directory and uses a basename formatted as `<unix_timestamp>_<2 lowercase letters>.json`.

### 5.5 Parameter Discovery and Task Updates

```bash
wedatacli workflow task parameter-configs --workflow-id wf_001 --task-type sql

# resource groups are only needed for explicit resource overrides;
# task creation auto-selects compute resources
wedatacli workflow task support-resource-groups --task-type sql

wedatacli workflow task update \
  --workflow-id wf_001 \
  --task-id task_001 \
  --parameter-overrides bizdate={{workflow.start_time.day}} \
  --resource-group-id res_001

wedatacli workflow task move --workflow-id wf_001 --task-id task_001 --x 200 --y 160
```

### 5.6 Dependency Management

```bash
wedatacli workflow task dependencies get --workflow-id wf_001 --task-id task_001

wedatacli workflow task dependencies add \
  --workflow-id wf_001 \
  --task-id task_001 \
  --depend-on upstream_task_id

wedatacli workflow task dependencies overwrite \
  --workflow-id wf_001 \
  --task-id task_001 \
  --depend-on upstream_task_id \
  --depend-condition ALL_SUCCESS

wedatacli workflow task dependencies clear \
  --workflow-id wf_001 \
  --task-id task_001
```

### 5.7 Declarative Workflow Changes

Use `wedatacli workflow apply` when you need to:

- sync a workflow from YAML / JSON
- create or update multiple tasks in one spec
- change type-specific task references such as SQL code file, integration task, quality task, or nested workflow target
- keep workflow definitions under reviewable files

```bash
wedatacli workflow template --format yaml > workflow.yaml
wedatacli workflow export --workflow-id wf_001 --format yaml > current.yaml
wedatacli workflow diff --file desired.yaml --workflow-id wf_001
wedatacli workflow apply --file desired.yaml --workflow-id wf_001
```

## 6. Parameter Rules

### 6.1 `k=v` Flags

Use comma-separated or repeated `k=v` arguments where supported:

```bash
--parameters bizdate=2026-06-15,region=shanghai
--parameter-overrides bizdate={{workflow.start_time.day}}
```

### 6.2 Alarm / Monitor Structured Flags

Use structured flags for observability configuration. Do **not** use legacy `--alarm-json` or `--monitor-json` flags.

```bash
wedatacli notification list --channel-type webhook
wedatacli notification get --notification-id ch_ops

wedatacli workflow alarm set \
  --workflow-id wf_001 \
  --alarm-group ch_ops=FAILURE,MONITOR_INDICATOR_ALARM \
  --mute-when-manually-terminated true

wedatacli workflow monitor set \
  --workflow-id wf_001 \
  --monitor-metric RUN_DURATION=10800000:14400000 \
  --monitor-metric WAIT_RUN=300000:600000

wedatacli workflow task alarm set \
  --workflow-id wf_001 \
  --task-id task_001 \
  --alarm-group ch_ops=FAILURE|TIMEOUT \
  --mute-until-last-retry true

wedatacli workflow task monitor set \
  --workflow-id wf_001 \
  --task-id task_001 \
  --monitor-metric RUN_DURATION=1800000:3600000
```

Notes:
- Use `wedatacli notification list|get` before `workflow alarm set` / `workflow task alarm set` when the agent needs to reuse an existing channel and confirm the target `NotificationId`.
- Use repeated `--alarm-group` or `--monitor-metric` flags to configure multiple channels or metrics.
- Workflow-level alarm/monitor changes can also be co-edited through `wedatacli workflow update-meta`, but dedicated `alarm` / `monitor` subcommands are clearer when only observability settings need to change.

### 6.3 Position

```bash
--x 100 --y 200
```

## 7. AI Operating Flow

### 7.1 Create a Workflow

1. Create the workflow with `wedatacli workflow create`.
2. Query task candidates if needed. Do not query resource groups for node creation; the CLI auto-selects compute resources.
3. Create tasks sequentially for the same `workflow_id`.
4. Query workflow details and verify dependencies.
5. Configure schedule if needed.
6. Run the workflow manually only after explicit user confirmation.

### 7.2 Update a Workflow Schedule

1. Run `wedatacli workflow get` first.
2. Copy schedule fields that must remain unchanged.
3. Apply `wedatacli workflow schedule set`.
4. Run `wedatacli workflow get` again and verify status, cycle type, and cron.

### 7.3 Update Task Parameters Safely

1. Run `wedatacli workflow task get` first.
2. If only selected keys should change, prefer `--parameter-overrides`.
3. If the full target parameter set is known, use `--parameters`.
4. Query again and verify the final task parameter list.

### 7.4 Change Type-Specific Task References

When the user wants to change a task's referenced code file, integration task, quality task, or nested workflow target:

1. Export or query the current workflow/task definition.
2. Prepare the desired spec file.
3. Review with `wedatacli workflow diff` when appropriate.
4. Apply with `wedatacli workflow apply`.
5. Query the workflow again and verify the target task definition.

### 7.5 Configure Workflow / Task Observability

1. Query current workflow/task state first with `wedatacli workflow get`, `wedatacli workflow task get`, or dedicated `alarm get` / `monitor get` commands.
2. If the target alarm channel should reuse an existing notification target, run `wedatacli notification list|get` first and confirm the `NotificationId` that will be placed into `--alarm-group`.
3. Choose workflow-level or task-level scope explicitly.
4. Use structured flags such as `--alarm-group`, `--mute-when-*`, and `--monitor-metric`.
5. After mutation, query again and verify the resulting `Alarm` / `MonitorMetric` fields.
6. For critical workflows, confirm both schedule and observability configuration are complete before considering the orchestration finished.

## 8. Common Mistakes to Avoid

- Do not guess IDs; query them first.
- Do not overwrite schedules blindly; preserve required existing fields.
- Do not run task `create` commands concurrently for the same `workflow_id`.
- Do not treat `status=success` without payload verification as sufficient when the command changes state.
- Do not assume imperative `workflow task update` can change task-type-specific references; use `workflow apply` when needed.
- Do not skip post-change verification.

## 9. Quick Reference

```bash
# workflow
wedatacli workflow list --page 1 --page-size 50
wedatacli workflow get --workflow-id wf_001
wedatacli workflow create --name wf_name
wedatacli workflow update-meta --workflow-id wf_001 --description "desc"
wedatacli notification list --channel-type webhook
wedatacli notification get --notification-id <notification-id>
wedatacli workflow alarm set --workflow-id wf_001 --alarm-group ch_ops=FAILURE,MONITOR_INDICATOR_ALARM --mute-when-manually-terminated true
wedatacli workflow monitor set --workflow-id wf_001 --monitor-metric RUN_DURATION=10800000:14400000
wedatacli workflow schedule set --workflow-id wf_001 --scheduler-status ACTIVE --trigger-mode TIME_TRIGGER --timezone Asia/Shanghai --config-mode COMMON --cycle-type HOUR_CYCLE --cron "0 0 0/1 * * ? *"
wedatacli workflow run --workflow-id wf_001

# tasks
wedatacli workflow task create --workflow-id wf_001 --task-type sql --task-name sql_task --code-file-id code_file_001
wedatacli workflow task create --workflow-id wf_001 --task-type python --task-name py_task --code-file-path /Workspace/project/tasks/py_task.py
wedatacli workflow task create --workflow-id wf_001 --task-type notebook --task-name nb_task --code-file-path /Workspace/project/notebooks/nb_task.ipynb
wedatacli workflow task support-integration-tasks --direction all --keyword orders --page 1 --page-size 50
wedatacli workflow task create --workflow-id wf_001 --task-type ingestion --task-name sync_task --integration-task-id integration_task_001
wedatacli workflow task support-quality-tasks --page 1 --page-size 50
wedatacli workflow task create --workflow-id wf_001 --task-type quality --task-name quality_check --quality-task-id quality_task_001
wedatacli workflow task support-workflows --page 1 --page-size 50
wedatacli workflow task create --workflow-id wf_001 --task-type nested-workflow --task-name nested_task --nested-workflow-id nested_wf_001
wedatacli workflow task update --workflow-id wf_001 --task-id task_001 --description "desc"
wedatacli workflow task alarm set --workflow-id wf_001 --task-id task_001 --alarm-group ch_ops=FAILURE|TIMEOUT --mute-until-last-retry true
wedatacli workflow task monitor set --workflow-id wf_001 --task-id task_001 --monitor-metric RUN_DURATION=1800000:3600000
wedatacli workflow task dependencies add --workflow-id wf_001 --task-id task_001 --depend-on upstream_task_id
wedatacli workflow task move --workflow-id wf_001 --task-id task_001 --x 160 --y 120

# declarative sync
wedatacli workflow export --workflow-id wf_001 --format yaml > current.yaml
wedatacli workflow diff --file desired.yaml --workflow-id wf_001
wedatacli workflow apply --file desired.yaml --workflow-id wf_001
```
