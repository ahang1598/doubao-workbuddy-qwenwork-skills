# 任务计划契约

## 目录

- [TaskPlan](#taskplan)
- [任务字段与依赖规则](#任务字段与依赖规则)

从 [任务计划模板](../assets/task-plan.template.json) 复制结构。每个任务使用稳定且唯一的 `task_id`。

```json
{
  "tasks": [
    {
      "task_id": "T01",
      "title": "建立案例背景和问题定义",
      "deliverable": "800字背景稿和3条问题定义",
      "owner": "M01",
      "collaborators": [],
      "backup": null,
      "depends_on": [],
      "due_at": null,
      "acceptance_criteria": ["覆盖R1", "给出来源定位"],
      "rubric_links": ["R1"],
      "status": "todo"
    }
  ],
  "rubric_criteria": ["R1"]
}
```

`owner` 在规划阶段可为 `unassigned`；提出分工后应为成员代号。依赖只能引用同一计划内存在的任务 ID，
不得形成自依赖或循环。每项任务必须有非空 `acceptance_criteria`，且 `rubric_links` 必须为数组。
`rubric_criteria` 非空时，脚本会把未出现在任何 `rubric_links` 中的评分项报告为警告。

保存 JSON 后运行：

```bash
python3 scripts/validate_task_graph.py path/to/task-plan.json
```

脚本只校验 ID、依赖、循环和评分项覆盖等结构条件；任务粒度、日期可行性和分工公平性仍需人工检查。

## 任务字段与依赖规则

每项任务必须有 `task_id`、非空 `title`、`owner`、`acceptance_criteria`、`rubric_links`、`depends_on` 和 `status`。`depends_on` 只能引用同一任务图中存在的 ID，不得自依赖或形成循环。`owner` 可以是 `unassigned`，但不能缺失；`status` 只能是 `todo`、`doing`、`submitted`、`accepted` 或 `blocked`。
