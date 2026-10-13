# 输出合同：pipeline_growth_operating_pack

<!-- delivery-hygiene-v4 -->
> **以下 JSON 是内部结构，用于工具校验与状态控制，不得整体或逐字段呈现给用户。**
> 用户可见交付要求见本文件末尾「用户可见交付」，以及 SKILL.md 的「交付卫生」段。

## 内部顶层字段（仅供运行时）

```json
{
  "artifact_type": "pipeline_growth_operating_pack",
  "artifact_state": "ready|degraded|intake_required|confirmation_required|routed|stopped",
  "delivery_tier": "direct|brief|full",
  "mode": "discovery_enrichment|account_signal_monitor|account_action_view|research_to_outreach|signal_sequence|pipeline_health|account_expand_retain|combined",
  "period": "用户给定或待确认",
  "scope": "产品线/区域/团队说明",
  "generated_at": "ISO8601或用户会话日期",
  "permission_status": "none_required|awaiting_confirmation|denied|granted_partial",
  "limitations": [],
  "assumptions": []
}
```

## 内部装配顺序（不是用户正文模板）

1. **元信息** — artifact_state、delivery_tier、mode、period、scope、permission_status  
2. **执行摘要** — 3–7 条优先结论与本周动作  
3. **账户/线索视图** — 按模式输出字段来源、身份置信、信号或 `优先跟进|持续观察|暂停触达`；只有排名门通过才含 rank  
   - 不可用时：区块保留并写 `section_status: skipped_missing_leads`  
4. **拓客序列** — 按分段/人群：step, channel, interval_hint, message_draft, exit_criteria  
5. **管道健康与收入情景** — 覆盖/老化/卡点；low-mid-high 或明确无点预测  
6. **干预商机清单** — 优先有序动作表  
7. **账户扩建与保有 / QBR 框架** — 风险户、扩建路径、QBR 议程  
8. **确认与审计清单** — 若需写回/发送：action_type, object_ids, payload_summary, idempotency_key  
9. **局限、假设、数据缺口**  
10. **完整收尾** — final_state, next_human_actions[], open_questions[]

## 写法约束

- 表格优先；金额与比率未知写「待确认」，禁止臆造。  
- 分层枚举和阈值来自冻结的用户/组织口径；缺字段时使用 `unknown/unscored`，不得隐性排序。  
- 关键结论需有 Claim ledger；CRM 字段与 supporting evidence 分开。  
- forecast 数值只引用确定性工具输出；full JSON 落盘，compact 仅入上下文。  
- `artifact_state=ready` 时至少含非空执行摘要 +（外呼清单或管道/账户段之一有实质行）。  
- `degraded` 必须在 limitations 说明降级原因。  
- `confirmation_required` 时不得声称已发送/已更新 CRM。  
- `routed`/`stopped` 时仍给简短原因与建议去处，不硬填空表充数。  

## 压缩优先级

与 runtime `output_budget.compression_order` 一致：先保核心表与状态收尾，再压缩长文案。

## 工件回执

`forecast_full_json|forecast_compact_json|forecast_final_json|claim_ledger` 必须全部真实落盘。四个 JSON 的 manifest 状态、计数和 runtime 固定全集必须一致；独立 gate 逐一验证真实路径与 `expected_sha256`，不接受调用方名称集合。


<!-- delivery-hygiene-v4 -->
## 用户可见交付

用户正文必须自包含；外部文档、表格或附件只能附加，移除链接后仍能复核核心结论。按这个顺序组织，用业务语言和中文表头：

1. **结论先行**：先给判断、关键风险或矛盾点，一段话说清。
2. **核心主工件**：按任务直接放账户行动表、外联草稿、预测/缺口表、渠道预算表、漏斗复盘或 QBR 框架，不能只写“已生成”。每个比率保留分子/分母，每个金额保留币种和期间。
3. **证据与来源**：列结论、依据材料、来源角色、截止时间和核验状态；CRM 事实与外部信号分开。
4. **风险与待确认**：列未知阶段、归属冲突、抑制、容量、财季口径和样本限制对结论的影响；缺关键字段时不给隐性排序或完整预测。
5. **下一步**：只写待人工复核/授权的动作草案，明确内部核验、内部协调或可外联；没有完成证据不写已执行。

固定约束顺序为账户身份、owner、suppression、在跑商机、容量、信号、动作。局部附件或连接器失败时仍交付已读取、可计算部分，并单列缺失范围、业务影响和补件方式。

不出现：哈希、内部文件名、schema、路由、英文机器字段与裸状态词，以及「主张台账 / Hard Gate / 能力槽 / 工件索引」这类内部术语标题。
