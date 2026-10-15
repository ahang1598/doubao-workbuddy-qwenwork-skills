# Search 运行时（招聘运营录用）

- 默认：`optional`；默认值只用于语义证据不足时，不覆盖任务判断。
- 来源顺序：`official_primary` → `company_primary` → `platform_primary` → `reputable_secondary`。
- 核心交付：可溯源政策与准入说明 | 流程进度与卡点预警 | Offer入职试用SOP | 保温方案话术与回写结果 | 指标结果与归因解读。
- 公开 Search 不能替代用户材料、内部系统或授权私有数据。

## 查询阶段
1. `freeze_scope`
2. `targeted_primary_lookup`
3. `resolve_material_conflicts`

预算上限 `3` 次（optional 最多
`2` 次）。证据契约满足、预算耗尽、仅剩私有缺口或
一手来源冲突不可裁决时停止。

<!-- SEARCH-AUTONOMY:START -->
## 自主联网决策

模型先检查「可溯源政策与准入说明 | 流程进度与卡点预警 | Offer入职试用SOP | 保温方案话术与回写结果 | 指标结果与归因解读」这一核心交付依赖什么证据，自主调用
`runtime/search_router.py` 的 `infer_task_signals(payload)` 与 `plan(payload)`；
不询问用户“要不要联网”，也不要求宿主预填 `needs_*` 布尔值。用户明确禁搜是
override；宿主提供的结构化 flags 仅作为可信 override。

- 审计权威默认：`off`。
- `required`：无默认 required 路径。
- `optional`：若任务实为公开劳动法规核验，应路由合规 Skill。
- `off`：处理内部政策、pipeline、Offer SOP、保温与招聘指标。
- `blocked`：搜索候选隐私、违法背调或未授权 HR 数据。公开 Search 不得替代私有或授权数据。

只有对象、法域、时点或范围不清且会改变检索方向或核心结论时，才进入
`blocked/intake_required` 并提出至多三个方向性问题；否则直接按任务语义决策。
输出必须包含 `decision_basis` 与 `inferred_signals`。
<!-- SEARCH-AUTONOMY:END -->
