# Task Playbook · 招聘运营录用

## 共用原则

1. 先锁 **mode + scope**，再取数。
2. 事实 / 推断 / 缺口 分列；禁止补造人数、率值、SLA、阈值。
3. 状态字段需 owner 与证据（系统状态名、时间戳、用户确认语）。
4. 写/发必须预览 → 确认 → 幂等执行 → 审计行。
5. 校招「未入库」口径：标注 `campus_source=non_warehouse`，结果仅作运营参考。

## recruiting_policy

**目标**：可溯源政策与准入说明。

步骤：
1. 抽取招聘政策主题（活水招聘准入、伯乐、Offer 效力、三方、实习转正等）；休假、福利、差旅、行为等全员政策路由员工政策服务。
2. 绑定适用身份：校招/社招/实习/活水调入/正式。
3. 输出：适用条件、材料、时限、常见误区、升级路径（HC/BP/法务/薪酬——角色名泛化）。
4. 声明：不构成律师意见；冲突条款标「待制度原文确认」。
5. 用户粘贴到制度全文则优先摘录要点+原文片段定位；无原文则 `degraded`。

## pipeline_track

**目标**：流程进度与卡点预警。

状态轴必须从用户流程配置映射；示意阶段只用于解释映射方法，不能硬编码为组织真实流程。

卡点类型：
- 时效：阶段停留超过用户给定 SLA；若无 SLA → 只报停留天数，不判「违规」。
- 字段：缺导师/上级/拟入职日/HC。
- 审批：当前节点停留、驳回。
- 候选人：Offer 未响应、延期。

输出表列：候选人标识（脱敏规则内）、岗位、阶段、owner、停留天数、风险级（信息/关注/紧急）、建议动作、证据。

无系统访问：接受 CSV/粘贴表；不足 → `intake_required` 或 `degraded`。

## offer_lifecycle

**目标**：Offer 草案→审批→发送→接受的录用生命周期。

分段清单：
1. 草案前：编制/HC、实体/法域、级别、经审批薪酬区间、正式模板与候选信息。
2. 草案：拆分 base/equity/bonus/benefits 等已确认组成；候选版与 hiring manager 内部备注分离。
3. 审批与发送：`can_draft_offer`、`can_request_offer_approval`、`can_send_offer` 分离；缺审批不得形成确定承诺。
4. 接受：记录正式回执、条款版本与日期；不得把口头意向写为 Accepted。
5. 交接：生成 Accepted handoff；完整 Pre-start、账号设备、Day 1/Week 1、30/60/90 路由入职融入管理。

每项：`owner_role`、`input`、`output_evidence`、`sla_hint(待确认可空)`。

## pre_accept_warming

**目标**：保温方案话术与回写结果计划。

1. 名单范围：届次/ORG/状态=待接受或签约交接前。
2. 分层：高风险（竞品/延期/导师空） / 常规 / 临近入职。
3. 话术：关怀进展、解答政策、连接导师；禁过度承诺薪资/职级。
4. 触达：建议频率与渠道（邮件/IM）；**发送前 confirmation_required**。
5. 回写字段建议：末次触达日、情绪标签、风险、补全导师/上级。
6. 无名单系统：用户上传；执行发送仅草稿除非确认。Accepted 后只保留交接通知，不继续做员工融入运营。

## recruiting_metrics

**目标**：指标结果与归因解读。

分流：
- **实时招聘运营指标**（阶段时长、环节转化、source effectiveness、offer 接受率、time-to-fill）：先复述口径公式、cohort、时间切与剔除规则。
- **历史/跨生命周期分析**（HC、流失、敬业度、晋升、公平性及长期招聘治理）：综合判断路由 `decision-analysis-report`，异常定位路由 `metric-anomaly-diagnostics`，指标口径设计路由 `kpi-measurement-design`；本 Skill 不计算。

最小诊断表：
- 漏斗各阶段必须使用同一 cohort 与时间口径；阶段人数不单调或跨期混用时先标口径冲突。
- 渠道分析至少并列 `进入量 / 有效推进量 / 录用或入职量 / 可得成本`；成本缺失时只谈转化，不虚构 ROI。
- Offer 接受异常需区分薪酬、决策时效、岗位预期、候选体验等**待验证假设**，并为每项绑定证据或补数动作。
- 外部基准数字只能在用户提供当前可核验来源时作为背景，不得直接当内部目标线。

归因结构：
- 事实：数据点
- 驱动：流程/供给/渠道/组织行为（标注推断）
- 缺口：缺权限、缺字段、样本不足
- 行动：可运营下一跳（与 pipeline/SOP/保温联动）

**禁止**：把实时「我的待办进度」伪造成大盘指标；实时进度归 `pipeline_track`。

完成率类：  
- 需求完成率 ≈ 录用或入职数 / 需求数（以用户口径锁定为准）  
- HC 达成率 ≈ 入职数 / HC（同上）  
口径未锁 → `intake_required` 或 `degraded`，不算最终率。

## accepted_handoff

仅输出正式条款版本、Accepted 证据、入职日期、岗位/经理、地点/用工信息与待完成合规材料。完整入职当前无 production 路由，标 `route_status=unavailable`；不得创建账号、下单设备、发 Day 1 邀请或设计 30/60/90。

## 写/发审计行格式

```
timestamp|actor|action|scope|idempotency_key|result|artifact_state
```

## 与相邻任务切割

| 信号 | 处理 |
|------|------|
| 约面/面评/搜简历 | routed |
| 每天自动发漏斗 | routed 自动化 |
| 竞对架构摸底 | routed mapping |
| 政策+指标同一句 | 仅招聘政策与实时招聘指标可组合；其余子任务分别 handoff |
| Accepted 后完整入职 | `route_status=unavailable` + handoff 包 |
| 全员薪酬/绩效/组织规划 | `route_status=unavailable` + handoff 包 |
| 招聘专属政策 | 本 Skill |
| 劳动法规/合规解释 | routed enterprise-compliance-review |
| 人才综合/异常/指标设计 | routed decision-analysis-report / metric-anomaly-diagnostics / kpi-measurement-design |
