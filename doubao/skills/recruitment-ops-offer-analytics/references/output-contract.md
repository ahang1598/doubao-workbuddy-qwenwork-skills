# Output Contract · recruitment_ops_decision_pack

<!-- delivery-hygiene-v4 -->
> **以下 JSON 是内部结构，用于工具校验与状态控制，不得整体或逐字段呈现给用户。**
> 用户可见交付要求见本文件末尾「用户可见交付」，以及 SKILL.md 的「交付卫生」段。

## 形状

```json
{
  "artifact_type": "recruitment_ops_decision_pack",
  "artifact_state": "ready|degraded|intake_required|confirmation_required|routed|stopped",
  "mode": "recruiting_policy|pipeline_track|offer_lifecycle|pre_accept_warming|recruiting_metrics|accepted_handoff",
  "complexity": "direct|brief|full",
  "executive_summary": "string",
  "route": {"selected_skill": "string", "intent": "string", "route_status": "selected|partial|routed|stopped"},
  "frozen_scope": {},
  "capability_slots": {},
  "claim_ledger": [],
  "tool_audit": {"schema_version": "hr-recruitment-tool/1.0", "full_artifact_path": "string", "full_sha256": "string", "compact_status": "ready|degraded|intake_required|confirmation_required|routed|stopped"},
  "recruiting_policy": {},
  "pipeline": {"configured_stage_map": [], "items": [], "blockers": [], "alerts": []},
  "offer": {"terms": [], "total_comp_components": [], "candidate_version": null, "internal_notes": null, "approval_state": "unknown", "send_state": "not_requested"},
  "warming": {"segments": [], "message_drafts": [], "send_status": "not_requested|draft_only|confirmation_required|sent_logged|blocked"},
  "recruiting_metrics": {"metric_defs": [], "results": [], "facts": [], "inferences": [], "gaps": []},
  "accepted_handoff": {"accepted_evidence": null, "terms_version": null, "start_date": null, "manager": null, "compliance_checklist": [], "route_status": "unavailable"},
  "actions": [
    {
      "id": "string",
      "type": "read|write|send|escalate|clarify",
      "title": "string",
      "owner_role": "string",
      "requires_confirmation": false
    }
  ],
  "confirmations": [],
  "audit": [],
  "limitations": [],
  "next_steps": [],
  "routing": {
    "target": "string|null",
    "reason": "string|null"
  }
}
```

`claim_ledger` 每行必含 `claim_id/claim/claim_type/critical/object_id/period/unit/source_ids/source_tier/confidence/conflict_state`。关键 Offer、审批、接受与指标结论须有 primary/official 来源；unknown 或开放冲突不得进入强结论。

## 呈现（对人）

1. 状态徽章 + 一句话结论（executive_summary）
2. 与 mode 对应的核心区块（表优先）
3. actions / confirmations
4. limitations + next_steps
5. 非当前 mode 的键保留为 null 对象并注 `omitted_for_mode`

## 状态填充规则

- `intake_required`：executive_summary 列出缺失字段；questions ≤ 3
- `confirmation_required`：confirmations 含 payload 摘要与 idempotency_key
- `degraded`：limitations 必含降级原因码
- `routed`：routing.target 必填；不假装完成业务
- `stopped`：limitations 含硬停原因；无假数据
- `degraded` 还必须包含当前判断、冻结范围、可答/暂停 slots、条件式模板、最大风险、3–5 个补证项及其结论影响、下一动作与工件索引

## Hard gates（输出前自检）

- 未确认不得标记 send/write 成功
- 不得输出律师意见口吻或保证录用
- 指标数字必须能指回用户数据或显式「待确认」
- PII 默认掩码
- 主工件键集完整
- Accepted 后不得出现账号/设备执行、Day 1/Week 1、30/60/90 或试用期完整计划
- 全员薪酬、绩效、组织规划、全员政策和跨生命周期人才分析必须 route/handoff
- 路由目标必须存在于 production manifest；不存在时只允许 `route_status=unavailable`，不得输出虚构 slug
- 招聘专属政策留在本 Skill；劳动法规/合规解释路由 `enterprise-compliance-review`
- 人才综合判断/异常定位/指标设计分别路由 `decision-analysis-report` / `metric-anomaly-diagnostics` / `kpi-measurement-design`


<!-- delivery-hygiene-v4 -->
## 用户可见交付

给用户的正文按这个顺序组织，用业务语言，中文表头：

1. **结论先行**：先给判断、关键风险或矛盾点，一段话说清。
2. **支撑主体**：表格或分点，来源直接标在结论后面（例：「差额 2 万（银行流水第 3 行重复入账）」）。
3. **证据与自检**（归档 / 审计 / 合规留痕类任务）：用中文表头列出结论、依据材料、来源角色、日期、状态；关键项自检写清通过与否和卡点。
4. **待确认项**：缺什么、影响哪个结论、找谁补、补上能得到什么。
5. **可直接使用的正文**：清单 / 通知 / 邮件 / 分录草稿等，给完整内容，不给名目。

不出现：哈希、内部文件名、schema、路由、英文机器字段与裸状态词，以及「主张台账 / Hard Gate / 能力槽 / 工件索引」这类内部术语标题。
