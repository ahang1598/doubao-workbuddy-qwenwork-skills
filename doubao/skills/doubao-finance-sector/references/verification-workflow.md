# 核验工作流 v2

```text
python3 scripts/sector_workflow.py INPUT.json
python3 scripts/sector_workflow.py -
python3 scripts/sector_workflow.py --schema
python3 scripts/sector_workflow.py --receipt RECEIPT.json INPUT.json
python3 scripts/sector_workflow.py --receipt RECEIPT.json -
python3 scripts/sector_workflow.py --freeze-expectation REQUEST.json EXPECTATION.json RECEIPT.json
```

v2 有意加强 claim、scenario 和 delivery 合同；不接受 v1 输入。原 `metrics` 字段继续使用 `sector_metrics.py` 契约，事件字段保留原时点含义。新增 `rolling_metrics` 使用 [滚动窗口契约](rolling-metrics.md)。两个数值输入的 `as_of` 都必须等于工作流根截止时点。

## 根对象

固定要求 `version: sector-workflow-v2`、带时区 `as_of`、`claims`、`final_uses_complete: true`、`final_uses`、`calendars`、`events` 和 `scenarios`。可选 `metrics`、`rolling_metrics`、`delivery`。缺少某类任务时使用空数组，不制造占位事实。

## Claims

每项 claim 要求：

- `id`、`proposition_id`、`proposition`、布尔 `decisive`。
- `claim_type=market_finding|research_priority|market_sequence`。
- `status=supported|unverified|contradicted|conditional`。
- `quantifier=bounded|universal|unique|necessary`。
- `scope={objects,market,taxonomy,start,end,coverage}`。
- `evidence`、`independent_required`、`competing_explanations_complete`、`competing_explanations`、`inferences`、`excluded_channels`、非空 `canonical`。

非条件 claim 必须满足 `scope.start < scope.end <= as_of`。每项 evidence 要求全局唯一 `id`、`type`、`source`、可为 null 的 `observed_at` 与 `available_at`、布尔 `direct`、`coverage`、`group`、`targets`、`role=support|contradict|context|isolated`、布尔 `decisive` 和 `supports`。不合资格证据必须标为 `isolated`。

决定性支持与决定性直接反证不能同时存在。`supported` 需要合资格决定性支持，`contradicted` 需要合资格决定性直接反证，`unverified` 不得携带任一类决定性证据，`conditional` 不得携带决定性直接反证。独立性只统计决定性支持的不同 group。只有状态为 `supported` 的全称、唯一和必要结论需要完整范围与覆盖；被反驳或尚未验证的强量词命题可以保留真实状态。受支持的唯一和必要结论还要求竞争解释集合完整且全部被直接反驳。

`investor_identity`、`investor_intent`、`actual_net_capital` 推断需要同名直接支持标签。排除渠道需要 `exclude_channel:<channel>`。研究优先 claim 不得声明 `market_sequence` 推断。`consecutive_session_acceleration` 另要求 `comparison={calendar_id,left_session_id,right_session_id}`，左右 session 必须在声明日历中相邻；用于支持该推断的 evidence 还必须用 `session_ids` 绑定这两个 session，且 `observed_at` 落在各自 session 内。

`final_uses` 每项含 `id`、`claim_id`、`location`、`kind`、`value`。只能引用 `decisive=true` 的 claim，且 value 必须与 canonical 的 JSON 类型和值同时一致；布尔 `true`、整数 `1`、小数 `1.0` 和字符串 `"1"` 不互认。每个决定性 claim 至少有一个 use。

## Scenarios

每项 scenario 含 `id`、`claim_id`、`condition`、`window`、`evaluation=met|not_met|unknown`、`evidence_ids`、`action` 和 `uses`。condition 含相同 `proposition_id`、`state=reinforcement|invalidation|missing_data`、可观察 `signal`、`operator`、`expected` 和可为 null 的 `unit`。用于判定 `met` 的强化或失效证据必须针对同一 proposition，且 `observed_at` 位于 scenario window 内。

`action.authorization` 固定为 `research_only`。强化只允许 `raise_priority|maintain_priority|gather_data`；失效或缺数只允许 `lower_priority|suspend_conclusion|gather_data`。任何 `evaluation=met` 的强化情景都只兼容 `supported` 或显式条件化的 `conditional` claim，并需要窗口内、命题特定、`decisive=true` 的合资格支持；`conditional` claim 的 action 还必须带 `conditional: true`。该要求不因动作方向是维持或继续取证而豁免。已满足的失效需要直接反证和 `contradicted` claim；已满足并降级的缺数情景需要 `unverified` claim。所有 scenario uses 必须按类型和值复用完整 action。

## Delivery

仅在用户明确请求文件时提供。规划阶段把 `{request, artifacts}` 写入请求文件，再用 `--freeze-expectation REQUEST.json EXPECTATION.json RECEIPT.json` 独占创建不可覆盖的 `sector-expectation-v1` 与 `sector-expectation-receipt-v1`。receipt 含 `query_digest`、request、expectation ID、expectation 路径、`frozen_at`、`producer` 和 `receipt_digest`（哈希不含 `frozen_at`）。交付必须由外部运行计划注入 `--receipt`；stdin 中的路径或 ID 只能与 receipt 交叉核对，不能另选一份自洽 expectation。

规范 JSON 区分 `true`、`1`、`1.0` 和 `"1"`：整数保持整数 token，Decimal 始终带小数点或指数，解析用 `parse_int=int` 与 `parse_float=Decimal`。哈希、渲染、解析和 binding 共用该类型模型。

冻结 expectation 与实际产物的路径集合必须完全相同。每个 expected artifact 含 `path`、`format=json|text|csv`、非空 `required_fields`、带 `{name, role}` 的 `schema_fields`、`canonical_bindings`、`sources`、`calculations`；text 另有 `value_role`，缺省为 `canonical`。角色为 `identifier|observation|source_excerpt|canonical`。produced artifact 含同一路径、格式、内容及依赖。required field 使用 `kind=json|csv|text` 与 selector，并可含类型严格的 `expected`。JSON key 与 CSV header 必须精确来自冻结 schema 名称。缺少任何期望文件、角色、依赖或 canonical 值即失败。

复现对象含 `raw_inputs` 和覆盖全部期望路径的 `outputs`。raw input 带唯一 id、`kind=identifier|numeric_observations|observation_table|source_excerpt` 和 JSON content。字段按角色收值，而不是按词语黑名单猜结论：

- `identifier` 只接受 identifier 短码。
- `observation` 只接受 numeric_observations 或 observation_table 的观测值。
- `source_excerpt` 只进入摘录字段。
- `canonical` 只接受 `$claim`、`$final_use`、`$scenario_action`。

输出 builder 支持：

- `json`：递归模板；`$ref` 只能进入匹配角色的字段，决定性值用 canonical 指令。
- `text`：批准的短 `{literal}`，加上与 `value_role` 匹配的 canonical、观测或标识片段；分析正文默认 `canonical`，raw 摘录不可直出。
- `csv`：按列 pointer 投影，列角色必须与冻结 schema 一致。

每个决定性 claim、final use 和 scenario action 必须声明 artifact field binding，并由 builder 使用相应 canonical 指令；所有必需对象恰好覆盖一次。校验同时检查类型和值。文本 literal 仍只能是逐项批准、长度不超过 24 的短标签或分隔符。`reproduction.calculations` 以唯一 id 声明二元 `add|subtract|multiply|divide`；两个整数保持整数运算，涉及小数则返回 Decimal，除法始终为 Decimal。输出须在全新目录中重建。JSON 的 `ignore_pointers` 规则保持不变。程序不执行生成代码或外部命令，也不再声明或接受未形成闭环的 base64 产物。

manifest 路径不得与产物路径相同或形成父子冲突，任意两个目标也不得重复或形成文件/目录父子冲突。暂存复读和期望检查通过后才预检全部目标；用户提供的原始 root 路径在解析前逐组件拒绝既有符号链接，目标及其既有父目录也不得是符号链接，并在提交前复检。提交前备份原文件，manifest 最后提交。失败时恢复原文件并与备份逐块比较、删除新文件和本次新建目录；任何恢复、验证或清理错误都会显式返回并保留事务目录。

## 最小示例

以下片段展示关系，不是固定报告模板：claim 必须有命题文本，final use 必须声明位置与类型，scenario 必须保留信号、窗口、证据和用途；文件交付还应先生成冻结 expectation，并通过 canonical 指令映射决定性值。

```json
{
  "claims": [{"id": "c1", "proposition_id": "p1", "proposition": "相对强度获支持"}],
  "final_uses": [{"id": "u1", "claim_id": "c1", "location": "summary", "kind": "conclusion", "value": {"state": "supported"}}],
  "scenarios": [{"id": "s1", "claim_id": "c1", "condition": {"proposition_id": "p1", "state": "reinforcement", "signal": "宽度扩张", "operator": "observed", "expected": true, "unit": null}, "window": {"start": "2026-09-01T00:00:00Z", "end": "2026-09-02T00:00:00Z"}, "evaluation": "unknown", "evidence_ids": [], "action": {"authorization": "research_only", "direction": "gather_data", "description": "继续取证"}, "uses": [{"location": "summary", "kind": "scenario_action", "value": {"authorization": "research_only", "direction": "gather_data", "description": "继续取证"}}]}],
  "reproduction": {"raw_inputs": [], "outputs": [{"path": "answer.json", "kind": "json", "template": {"state": {"$claim": "c1"}}}]}
}
```

成功输出只标记 `structurally_reproduced`，并明确返回 `raw_provenance_verified: false` 与 `substantive_correctness_verified: false`。schema、hash 和重建不能验证输入是否真是原始观察、来源真实性、claim 完整性、自然语言支持关系或情景动作的专业适配，这些仍必须语义审查。`--schema` 输出机器可读根 I/O 合同；本文件定义嵌套字段与状态。
