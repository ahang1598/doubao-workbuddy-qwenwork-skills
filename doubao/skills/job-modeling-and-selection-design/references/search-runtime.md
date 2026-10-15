# Search 运行时（岗位建模甄选）

- 默认：`off`；默认值只用于语义证据不足时，不覆盖任务判断。
- 来源顺序：`user_material` → `authorized_private_data` → `official_primary`。
- 核心交付：可发布JD | 岗位能力/胜任力模型 | 人才标准文档 | 面试题库题本与评分表 | 面评模板与质量审核建议。
- 公开 Search 不能替代用户材料、内部系统或授权私有数据。

## 查询阶段
1. 默认不执行公共 Search；仅在任务语义触发时改道。

预算上限 `0` 次（optional 最多
`0` 次）。证据契约满足、预算耗尽、仅剩私有缺口或
一手来源冲突不可裁决时停止。

<!-- SEARCH-AUTONOMY:START -->
## 自主联网决策

模型先检查「可发布JD | 岗位能力/胜任力模型 | 人才标准文档 | 面试题库题本与评分表 | 面评模板与质量审核建议」这一核心交付依赖什么证据，自主调用
`runtime/search_router.py` 的 `infer_task_signals(payload)` 与 `plan(payload)`；
不询问用户“要不要联网”，也不要求宿主预填 `needs_*` 布尔值。用户明确禁搜是
override；宿主提供的结构化 flags 仅作为可信 override。

- 审计权威默认：`off`。
- `required`：无默认 required 路径。
- `optional`：用户明确要公开市场薪酬或岗位基准时应路由专门研究。
- `off`：依据业务需求、职级和组织约束设计 JD、模型与面试方案。
- `blocked`：搜索个人敏感信息、歧视性筛选或非公开候选资料。公开 Search 不得替代私有或授权数据。

只有对象、法域、时点或范围不清且会改变检索方向或核心结论时，才进入
`blocked/intake_required` 并提出至多三个方向性问题；否则直接按任务语义决策。
输出必须包含 `decision_basis` 与 `inferred_signals`。
<!-- SEARCH-AUTONOMY:END -->
