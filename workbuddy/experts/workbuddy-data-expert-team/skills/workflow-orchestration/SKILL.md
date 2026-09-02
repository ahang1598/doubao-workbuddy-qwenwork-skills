---
name: workflow-orchestration
type: execution
tags: [data-development]
user-invocable: false
description: Used to create, modify, configure, schedule, and trigger workflows. This skill focuses on workflow orchestration only and does not implement task logic. Trigger this skill when workflow structure, node orchestration, dependency management, scheduling, parameter configuration, observability configuration, or failure strategy configuration is required.
---

# Workflow Development

## Purpose

Use this skill to design, construct, and manage workflow definitions.

A workflow is an orchestration of data tasks, dependencies, schedules, and execution policies.

This skill is responsible for workflow orchestration and structure only.

It MUST NOT implement task logic.

---

## Runtime Boundary

This skill manages workflow definitions and orchestration.

It does NOT manage workflow runtime instances after a workflow execution has already been created.

Important boundary:

* Starting / triggering / manually running a workflow belongs to `workflow-orchestration`
* Inspecting, diagnosing, rerunning, backfilling, or terminating an existing execution belongs to `production-operations`

The following responsibilities belong to `production-operations` once the execution already exists:

* Query workflow runs
* Query task runs
* View execution logs
* Analyze failures
* Retry failed runs
* Kill running instances
* Backfill existing schedules or executions
* SLA analysis
* Runtime performance analysis

---

## When To Use

Use this skill when the user intent involves workflow orchestration decisions.

### Workflow Lifecycle

* Create workflows
* Modify workflows
* Archive workflows
* Trigger workflow execution

### Workflow Structure

* Add workflow nodes
* Remove workflow nodes
* Reorganize workflow structure
* Split workflows
* Merge workflows
* Configure dependencies

### Scheduling & Policies

* Configure schedules
* Configure retries
* Configure concurrency
* Configure queue policies
* Configure timeout policies
* Configure failure strategies

### Node Orchestration

* Select node types
* Configure node parameters
* Override node compute resources only when explicitly requested; compute resources are auto-selected at node creation
* Configure node execution strategies

### Governance & Observability

* Configure workflow or task observability settings when needed
* Validate monitoring thresholds and notification targets
* Validate workflow safety
* Validate workflow governance requirements

---

## When NOT To Use

Do NOT use this skill when the user intent is:

* Writing SQL logic → studio-development
* Writing Python logic → studio-development
* Notebook implementation → studio-development
* Creating datasource connections → connection-manage
* Designing business solutions → solution-design
* Managing existing workflow runtime instances → production-operations

---

## Core Responsibilities

This skill owns the workflow orchestration layer.

### Workflow Orchestration

* DAG construction
* DAG modification
* Node composition
* Dependency management

### Workflow Lifecycle

* Create workflows
* Update workflows
* Trigger workflows

### Scheduling & Policies

* Create schedules
* Modify schedules
* Enable schedules
* Disable schedules
* Validate schedules
* Schedule configuration
* Retry strategy configuration
* Concurrency configuration
* Timeout strategy configuration
* Failure policy configuration


### Governance

* DAG structure review
* Cycle risk review
* Dependency consistency review
* Workflow compliance review

### Node Orchestration

* Select node types
* Configure node relationships
* Configure node execution behavior

---

## Supported Node Types

* SQL Task
* Python Task
* Notebook Task
* Offline Data Integration Task (data ingestion/access and data egress)
* Data Quality Task
* Nested Workflow Task

---

## Available Commands

### Workflow Lifecycle

Primary entrypoint:

`wedatacli workflow`

Responsibilities:

* create workflow
* query workflow
* update workflow metadata
* manage schedules, parameters, labels, resource groups, and observability settings
* trigger workflow execution
* export / diff / apply workflow specs

Alarm / monitor mutations are part of this skill, but detailed command choices and examples stay in `references/usage/command_usage_guide.md`.
When reusing an existing notification channel, resolve the target first with `wedatacli notification list|get`.

### Node Management

Workflow nodes are created and managed through:

`wedatacli workflow task`

Currently supported task types:

* `sql`
* `python`
* `notebook`
* `ingestion`
* `quality`
* `nested-workflow`

Supported task operations include:

* create / get / delete
* update description, parameters, resource group, and retry policy
* manage dependencies
* move canvas position
* manage task-level observability when needed
* discover task candidates; resource groups only need to be queried for explicit resource overrides

Dependencies are configured through `wedatacli workflow task dependencies ...`.

Workflow dependencies are inspected through `wedatacli workflow get`.

### Usage

Detailed command syntax, flags, and examples are available in:

`references/usage/`

---

## References

Before designing workflows, consult references in the following order.

### Layer 1 — Workflow Design Rules

Defines workflow orchestration principles and governance constraints.

* references/design/workflow_guide.md

### Layer 2 — Node Specifications

Defines behavior and configuration rules for individual node types.

* references/node_specs/sql_node_design_guide.md
* references/node_specs/python_node_design_guide.md
* references/node_specs/notebook_node_design_guide.md
* references/node_specs/ingestion_node_design_guide.md
* references/node_specs/nested_workflow_node_design_guide.md

### Layer 3 — Commands & Execution

Defines command syntax and execution behavior.

* references/usage/command_usage_guide.md

---

## Execution Rules

1. Prefer existing workflow patterns before creating new workflow structures.
2. Review workflow DAG consistency before saving.
3. Use model reasoning to avoid circular dependencies.
4. Use model reasoning to ensure referenced nodes exist.
5. Validate scheduling configuration before execution.
6. Require workflow owner and description.
7. Reuse existing workflow definitions whenever possible.
8. Reuse existing task definitions whenever possible.
9. Keep workflow orchestration separate from task implementation.
10. For the same `workflow_id`, create workflow nodes sequentially one by one; do not run node `create` commands in parallel or batch them, because the platform may fail concurrent node creation for the same workflow.
11. Before changing workflow or task alarms/monitors, query the current workflow/task definition or the current alarm/monitor config first; when `--alarm-group` needs an existing channel, resolve the target with `wedatacli notification list|get` and verify the result again after mutation.
12. Before triggering the manual-run command `wedatacli workflow run`, show the target workflow and intended action, then obtain explicit user confirmation for that specific execution step.
13. When creating workflow nodes, do not select compute resources manually; `wedatacli workflow task create` auto-selects a default execution resource. Only pass `--resource-group-id` when the user explicitly requests a specific resource.

---

## Success Criteria

A workflow is considered valid when:

* DAG dependency design has been reviewed by the model
* Nodes are correctly typed
* Dependencies are complete and reference intended upstream nodes
* Scheduling configuration is valid
* Workflow configuration is queryable
* Workflow can be triggered successfully
* Monitoring is configured when needed
* Alerts are configured when needed
* Failure strategies are configured when needed
* Retry strategies are configured when needed
* Governance requirements are satisfied
