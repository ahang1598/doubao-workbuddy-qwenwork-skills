# Search 运行时（经营财务）

- 默认：`off`。`off` 表示仅用用户材料；`required` 仅在当前公共事实是必要输入时使用；`optional` 只补证；`blocked` 表示缺口只能由用户/私有系统补齐。
- 用户禁搜、closed fixture 或错误路由一律 `off`；对象、范围、时点、法域未冻结一律 `blocked`。Search 不能替代用户、账户、案卷或企业内部私有数据。
- 来源顺序：`user_material` → `authorized_private_data`。
- Critical claims：账簿、预算、实际与用户确认的情景假设。关键 Claim 必须由一手/官方来源承担；二手材料只可解释，不能承载关键事实。
- `unsupported` 必须改为 `unknown`；来源冲突需并列并说明裁决依据，无法裁决则保留未知。
- 低推理两阶段：先按以下阶段收集并压缩为 Claim 台账，再独立验证台账；验证通过后才分析，不注入完整搜索上下文。

## 查询阶段
1. 不执行公共 Search。

预算上限 `0` 次（optional 最多 `0` 次）。证据契约满足、预算耗尽、仅剩私有缺口或一手来源冲突不可裁决时立即停止；不得为用满预算扩大范围。

<!-- SEARCH-AUTONOMY:START -->
## 自主联网决策

模型先检查「差异瀑布与narrative | CFO执行摘要与行动项 | 毛利诊断与定价情景 | 滚动现金流与发薪可行性」这一核心交付依赖什么证据，自主调用
`runtime/search_router.py` 的 `infer_task_signals(payload)` 与 `plan(payload)`；
不询问用户“要不要联网”，也不要求宿主预填 `needs_*` 布尔值。用户明确禁搜是
override；宿主提供的结构化 flags 仅作为可信 override。

- 审计权威默认：`off`。
- `required`：无默认 required 路径。
- `optional`：公开利率或同行基准属于可选附录，不是典型主路径。
- `off`：依据 P&L、BS、GL、预算和现金流做经营解读。
- `blocked`：搜索企业私有财务、银行信息或用外部基准替代内部事实。公开 Search 不得替代私有或授权数据。

只有对象、法域、时点或范围不清且会改变检索方向或核心结论时，才进入
`blocked/intake_required` 并提出至多三个方向性问题；否则直接按任务语义决策。
输出必须包含 `decision_basis` 与 `inferred_signals`。
<!-- SEARCH-AUTONOMY:END -->
