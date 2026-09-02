# 证据交接协议

成员必须返回简短专业结论和一个 `evidence_handoff` JSON 代码块。JSON 对象格式：

```json
{
  "member_id": "concept-rotation",
  "status": "completed",
  "data_gate": "OPEN",
  "auth_status": "success",
  "calls": [
    {
      "evidence_id": "concept-rotation-CALL-01",
      "method": "get_last_trade_date",
      "params": {"exchange": "SH"},
      "status": "success",
      "row_count": 1,
      "date_range": "20260820",
      "fields": ["date"],
      "retry_count": 0
    }
  ],
  "claims": [
    {
      "claim_id": "concept-rotation-CLAIM-01",
      "claim_type": "expert_judgment",
      "text": "示例题材处于扩散阶段",
      "evidence_ids": ["concept-rotation-CALL-02", "concept-rotation-CALL-03"]
    }
  ],
  "risks": ["示例风险"],
  "data_gaps": [],
  "needs_review": []
}
```

## 字段约束

- `member_id` 必须是路由登记成员。
- 数据任务的 `status` 必须为 `completed`，`data_gate` 必须为 `OPEN`，`auth_status` 必须为 `success`。
- `calls` 只记录 `call_pandadata` 的真实业务方法，不把 `auth_status`、`search_methods` 或 `get_method_doc` 当作业务证据。
- `status=success` 时 `row_count` 必须大于 0。
- 真实 0 行只能使用 `status=empty_after_retry`，并且 `retry_count` 至少为 1。
- `date_range` 必须来自返回数据或明确写 `not_returned`，不得推断。
- `fields` 只记录真实返回或确认缺失的关键字段。
- `data_fact`、`derived_calculation`、`expert_judgment` 都必须引用至少一个本成员 `evidence_id`。
- `background_knowledge` 不得描述当前市场事实。
- 成员被阻塞时返回 `status=blocked`、`data_gate=CLOSED` 和 `block_reason`，不得继续生成数据结论。

## 主理人汇总对象

主理人提交验证器的顶层 JSON 还必须包含：

```json
{
  "schema_version": "pd-team-evidence/1",
  "user_request": "找出有资金确认但还没有明显过热的题材龙头候选",
  "task_type": "candidate_shortlist",
  "data_required": true,
  "final_status": "continue_observe",
  "member_reports": [],
  "final_claims": [],
  "conflicts": [],
  "unsupported_claims": []
}
```

`final_status` 允许：`priority_research`、`continue_observe`、`caution`、`evidence_insufficient`。

`user_request` 必须保留用户原始问题。验证器会检查候选、比较、资金验证和纯教育类请求是否被降级到错误路由。
