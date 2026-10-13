# 作业简报与成员契约

## 目录

- [通用修订字段](#通用修订字段)
- [AssignmentBrief](#assignmentbrief)
- [TeamMember](#teammember)
- [Assign 最小成员契约](#assign-最小成员契约)

## 通用修订字段

主要工件可包含以下字段。增量修改时保留未受影响的任务、主张、证据和内容块 ID，只为新增对象分配新 ID。

```json
{
  "artifact_id": "A-001",
  "revision": 1,
  "previous_artifact_id": null,
  "change_request": null,
  "change_log": []
}
```

## AssignmentBrief

从 [作业简报模板](../assets/assignment-brief.template.json) 复制结构。模板是起点，不代表字段已经确认。

```json
{
  "mode": "plan",
  "assignment": {
    "title": "课程小组作业标题",
    "course": "课程名",
    "assignment_type": "case_study",
    "objective": "要解决的问题或完成目标",
    "deliverables": [
      {"type": "report", "format": "markdown", "length_or_size": "3000字"},
      {"type": "slides", "format": "outline", "length_or_size": "10分钟"}
    ],
    "rubric": [
      {"id": "R1", "criterion": "问题分析", "weight": 40}
    ],
    "deadlines": {"final": null, "internal": []},
    "constraints": [],
    "ai_policy": "unknown",
    "status": "draft"
  },
  "team": [],
  "contributions": []
}
```

`mode` 只允许 `plan`、`assign` 或 `merge`。`title`、`objective` 和非空 `deliverables` 是脚本必填字段，
每个交付物至少要有非空 `type` 与 `format`；
`assign` 还要求非空 `team`，`merge` 还要求非空 `contributions`。

保存 JSON 后运行：

```bash
python3 scripts/validate_brief.py path/to/assignment-brief.json
```

## TeamMember

```json
{
  "member_id": "M01",
  "display_name": "成员A",
  "strengths": ["资料整理"],
  "preferences": ["愿意负责文献部分"],
  "availability": "周三晚和周末",
  "current_load": "unknown",
  "constraints": []
}
```

只使用用户明确提供的成员信息。没有资料时使用 `M01` 等代号，不猜测真实姓名、性格或能力。

## Assign 最小成员契约

`assign` 输入的 `team` 至少包含 1 名成员；每名成员必须提供非空 `member_id`、`availability`、`strengths`、`preferences` 和 `constraints` 字段。未知信息必须显式写成 `unknown`，不得用空对象、空字符串或缺失字段代替。`current_load` 可使用 `unknown`，但必须保留该字段。
