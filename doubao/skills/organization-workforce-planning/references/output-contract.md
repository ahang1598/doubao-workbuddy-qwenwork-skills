# Output Contract

<!-- delivery-hygiene-v4 -->
> **以下 JSON 是内部结构，用于工具校验与状态控制，不得整体或逐字段呈现给用户。**
> 用户可见交付要求见本文件末尾「用户可见交付」，以及 SKILL.md 的「交付卫生」段。

`organization_workforce_plan_pack` 必含：

```json
{
  "artifact_state": "ready|degraded|intake_required|confirmation_required|routed|stopped",
  "delivery_tier": "direct|brief|full",
  "frozen_scope": {},
  "capabilities": {"allowed": [], "missing": [], "blocked_slots": []},
  "privacy_policy": {"minimum_group_size": null},
  "claim_ledger": [],
  "baseline": {},
  "capability_demand": [],
  "scenarios": [],
  "cost_bridge": [],
  "structure_options": [],
  "transition_route": [],
  "unknowns": [],
  "risks_and_counterpoints": [],
  "action_previews": [],
  "limitations": [],
  "next_steps": [],
  "artifact_index": {}
}
```

情景行含 `scenario_id`、`baseline_hc`、`hc_delta`、`ending_hc`、`recurring_cost_delta`、`one_time_cost`、`currency`、`period`、`assumption_ids` 和 `hc_bridge`。`hc_bridge` 固定含期初、招聘、离职、调入、调出、净增量、期末、完整性和 unknown；缺流量分项不得用净增量填招聘。

成本槽独立降级。缺经常性单位成本时仅 `recurring_cost_delta=null`；缺正向 HC 的一次性单位投入时仅 `one_time_cost=null`；缺币种或期间时两类成本均保持 null。任何缺失都写入标准 unknown，不得填 0。HC 净增和期末 HC 仍可计算。

`capability_demand` 必须形成能力需求→工作量→岗位依赖骨架。`structure_options` 每项含情景依据、能力覆盖、工作量支持、岗位依赖、HC 成本、可逆性、风险、unknown 和 `reporting_lines`；缺结构基线时后者为 null。`transition_route` 只使用条件阶段与 decision gates。`risks_and_counterpoints` 必含最大反方。

Full 与 compact 均声明 `artifact_type=organization_workforce_plan_pack`（full 通过 `artifact_index`），文件名分别为 `organization-workforce-plan.full.json` 和 `organization-workforce-plan.compact.json`。compact 包含完整核心槽位、`full_sha256` 与对 compact 自身无哈希字段 payload 计算的 `compact_payload_sha256`；validator 独立复算并深比较。

`ready` 至少需要一个情景；空 `scenarios` 必须为 `degraded` 并带 `unknown-scenarios`。validator 必须从角色明细重算 HC、两类成本和流量桥，再逐情景核对 `cost_bridge` 与结构选项中的 HC/成本镜像。finalizer 不得用空 claims 或空槽覆盖非空主工件，完成后必须重新通过同一 validator。


<!-- delivery-hygiene-v4 -->
## 用户可见交付

给用户的正文按这个顺序组织，用业务语言，中文表头：

1. **结论先行**：先给判断、关键风险或矛盾点，一段话说清。
2. **支撑主体**：表格或分点，来源直接标在结论后面（例：「差额 2 万（银行流水第 3 行重复入账）」）。
3. **证据与来源**（归档 / 审计 / 合规留痕类任务）：用中文表头列出结论、依据材料、来源角色、日期、状态；未知来源角色或日期保持待确认，不补造。
4. **待确认项**：缺什么、影响哪个结论、找谁补、补上能得到什么。
5. **可直接使用的正文**：清单 / 通知 / 邮件 / 分录草稿等，给完整内容，不给名目。

不出现：哈希、内部文件名、schema、路由、英文机器字段与裸状态词，以及「主张台账 / Hard Gate / 能力槽 / 工件索引」这类内部术语标题。

简单算术题不强制展开完整包，只给公式、结果、取整和关键假设。复杂题即使另附文档，正文仍须包含全部核心表和唯一有效版本，不得只给链接或工具运行摘要。
