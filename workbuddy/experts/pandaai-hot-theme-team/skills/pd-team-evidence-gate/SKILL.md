---
name: pd-team-evidence-gate
description: "Use when the PD hot-theme WorkBuddy team must validate member handoffs, minimum PandaData routes, evidence references, empty-result retries, and unresolved conflicts before producing a final consultation report."
---

# 专家团事实审查

用于 `PD-热点龙头捕捉团` 的成员交接和最终事实闸门。它不分析市场，只检查多 Agent 会诊是否具备可追溯证据。

## 使用顺序

1. 主理人先根据 [team-route-matrix.md](references/team-route-matrix.md) 选择路由并真实调用成员。
2. 每位成员按 [evidence-handoff-schema.md](references/evidence-handoff-schema.md) 返回结构化交接。
3. 主理人将交接和拟采用的最终结论合并为一个 JSON 文件。
4. 最终回答前必须执行：

```bash
python skills/pd-team-evidence-gate/scripts/validate_evidence.py --input .pd-team-evidence.json
```

5. 只有输出中的 `final_allowed` 为 `true` 才能形成数据型最终结论。失败时按 `errors` 补调成员、复查数据或报告阻塞。
6. 通过后按 [consultation-output-contract.md](references/consultation-output-contract.md) 收敛用户可见结果。

## 不可绕过的规则

- 当前行情、题材、资金、候选、排名和风险事实必须引用本轮业务调用的 `evidence_id`。
- 必须保留原始 `user_request`；候选、比较或资金验证请求不得降级到更轻的路由。
- `background_knowledge` 只能解释概念，不能携带当前日期、数值、排名、候选或市场状态。
- 必需成员没有 `completed`、`DATA_GATE=OPEN` 和成功认证时，数据型会诊失败关闭。
- 数据型最终结论必须覆盖每位必需成员至少一个 `evidence_id`，不能只调用专家却忽略其结论。
- 0 行调用只有标为 `empty_after_retry` 且 `retry_count >= 1` 才可接受。
- 未解决分歧必须披露，并把最终等级限制为“继续观察”或“证据不足”。
- 事实闸门通过不代表投资结论正确，只证明报告中的当前事实具有本轮调用证据。
