# 质量检查

模型判断和脚本结果分开报告：脚本只证明结构条件，不能证明观点正确、来源真实或成员贡献公平。

## Plan checks

先用 [`validate_brief.py`](../scripts/validate_brief.py) 检查 `AssignmentBrief`，再用
[`validate_task_graph.py`](../scripts/validate_task_graph.py) 检查任务图。退出码为 0 只证明下列可自动判断的
结构条件；日期可行性、任务粒度和评分理解仍需人工判断。

- 每个最终交付物都有任务；
- 每个任务都有唯一主责人或明确 `unassigned`；
- 依赖图无循环，所有依赖 ID 都存在；
- 评分标准均被任务覆盖，未覆盖项单列；
- 内部截止时间早于最终截止时间（日期已知时）；
- 合稿、审核和彩排有明确前置任务。

## Assignment checks

- 主责人可用时间满足截止要求，或风险显式标记；
- 高风险任务有协作者/替补或说明无法设置；
- 没有使用敏感属性或未经用户提供的性格推断；
- 工作量明显失衡时给出重新分配建议；
- 方案状态为 `proposed` 或 `team_review`，不会伪装成集体同意。

## Merge checks

整合前后分别用 [`audit_contributions.py`](../scripts/audit_contributions.py) 检查贡献集合和 `MergeResult`。
退出码为 1 时停止依赖该工件的后续工作；退出码为 0 但含 `[WARN]` 时，把警告保留在缺口或风险中。

- 每份提交可追溯到成员和任务；
- 每个事实/解释主张有来源或被标记为 `unresolved`；
- 每个建议主张有 rationale 或关联问题/主张；
- 跨成员共享证据保留原始证据所有者；
- 正文中的数字和百分比均能对应到 claim/evidence，或进入缺口清单；
- 重复、张力、冲突、缺口分别归类；同主题不直接当作重复或冲突；
- 每个合稿内容块都有 source claim IDs；
- 合稿没有把假设写成事实；
- 贡献映射不等同于成绩或责任裁定。

## Revision checks

- revision 比上一版递增；
- 未受影响的 task/claim/evidence/block ID 保持稳定；
- change log 列出请求、受影响 ID、变更和重新校验结果；
- 当前结论基于当前工件，不依赖不可见的旧会话状态。

## External handoff

当前版本只返回手工交接块，不报告外部动作已经完成。若用户要求 PPTX、Word、Excel、任务、消息、日历、
搜索或论文服务，先交付当前 Skill 能完成的结构，再列出目标、字段、权限和需要用户确认的事项。
