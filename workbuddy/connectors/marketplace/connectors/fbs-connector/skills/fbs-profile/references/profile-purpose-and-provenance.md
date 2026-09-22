# 画像用途、提案和来源

先通过[capability-routing](../../fbs-connector/references/capability-routing.md)。本文对应会员Gateway源码`172a42582630c3941976da534408378c0dcc675a`；隔离服务已ACTIVE且基础路由检查通过，完整授权业务矩阵与宿主证据另行验收。实际调用仍须已审核资源配置、当前tools/list/schema和授权。canonical mcp.json保持旧生产地址，没有自动启用画像。机器边界见[身份合同](../../fbs-mainline/references/identity-contract.json)的resourceProfiles.oauthProfileGateway。

账户来自本资源有效 OAuth，主体在同一 issuer 内不随客户端或组织改变；不在参数补 subject_id/userId/grant，不以匿名 binding、产品ID或昵称选择他人。contextRef只能由服务签发，绑定账号、当前client/grant、精确上下文和用途。不同grant各自网页同意后才共享本人同范围事实；新grant不能复用旧ref。共享连接器的productId仅为声明来源，不能实现按专家保密。

当前仅支持以下范围，不自动将事项事实提升为个人偏好，也不跨事项复制：

| contextType / contextId / purposeCode | 合法fieldKey |
|---|---|
| PERSONAL / personal / expert-personalization | work_role、industry、experience、goals、constraints、decision_style、preferred_language、output_preference、delivery_preference、collaboration_preference |
| CASE / 本人已有个人case-ID / decision-support | objective、constraint、decision、success_criteria、deadline |

组织画像、企业事项编号和organizationId覆盖明确拒绝，不能降级成个人。事项由本人门户已有流程选择/创建；本资源没有member_case_create等事项工具。只提出用户明确选择的最少短值，不上传聊天全文、原稿、媒体、文件路径、证件或凭据，不推断无关敏感标签。会员/账务信息不是可编辑画像字段。

`profile_manage_entry` 用完整四字段及operationId、contextType、contextId、purposeCode建立PENDING上下文并给manageUrl。用户在本人网页登录状态下明确同意用途后，才可读取/提案。当前用途有效期24小时；context.status为ACTIVE还须未过期且授权仍有效，不能仅凭状态字符串放行。

`profile_read` 除四字段外仅接收contextRef、可选fieldKeys和afterFactId。fieldKeys显式提供时为1–5个唯一合法字段；省略表示本用途范围，但任务辅助应主动选最少字段。每页最多2项，返回facts/count/hasMore/nextAfterFactId、consentVersion和auditOperationId；没有pageSize或通用cursor参数。每页检查当时当前版本，paginationConsistency=CURRENT_VERSIONS_PER_REQUEST，不承诺跨页快照。profile_status只列当前grant最多10个上下文，可传已知contextRef精确查询；不要自造分页参数或猜ref枚举。

事实条目含factId、fieldKey、value、evidence、source、revision、confirmedAt、confirmation、userCorrected。claimKind位于source内；没有每条事实expiresAt字段。到期与撤权看当前用途/授权，时间字段为Unix秒。仅返回最新ACTIVE且已经本人确认的事实，待审提案不当作事实。

`profile_propose` 必填operationId、contextRef、fieldKey、value、evidence、claimKind，每次一项。value/evidence各最多256个UTF-16字符单位；claimKind只能明确取user_statement（用户已陈述）、artifact_observation（本轮获准材料观察）、expert_inference（专家推断），缺失不得猜测或代填。sourceEvidenceTrust固定client_declared_unverified；本人确认或纠正后仍保留原kind/evidence，不因此证明观察客观正确。

operationId在首次明确动作前分配并保留，同号同载荷返回原回执，异归属/载荷/产品版本冲突则停止。ID格式为1–64字符，首位字母数字，其余字母数字或`._:-`；不要把个人信息放进编号，也不为生号运行未授权Shell或写记忆。MCP新增提案不接收callerOperationId、expectedVersion、amend或独立purpose参数。丢响应先按原operationId查profile_operation_receipt；同账号不同grant不能跨读该回执，需本人网页核对，不能另造新号。

提案不是确认。网页写操作使用本人Cookie、固定同源、X-Fbs-Profile:1及expectedVersion；这些由本人页面处理，模型不能手工搬运Cookie、伪造批准或向MCP塞accepted=true。当前没有另行暴露的一次性挑战参数。

| 本人网页动作 | expectedVersion对应对象 |
|---|---|
| CONSENT、WITHDRAW_PURPOSE | context.version |
| CONFIRM | proposal.version，且原consentVersion仍匹配 |
| CORRECT、WITHDRAW_FACT | fact.revision |

网页实际回执为operationId/action/status=COMPLETED/result/replayed/completedAt；网页操作通过本人网页核对，不是当前grant的MCP回执。确认是逐项动作，不能把用途同意当成全部草案确认。同字段已有有效事实时，新草案确认冲突，改走本人纠正。

单项撤回追加tombstone；用途撤回使该账号同上下文/用途的所有客户端同意失效，终止待确认草案并撤回对应事实。重新同意不自动复活旧值。解绑只撤销对应客户端；其他有有效同意的客户端仍可用。本人Cookie管理不因某个grant失效而失去纠正/撤回权限。当前是版本化撤回，不是hard-delete；删除和导出尚未实现，不承诺入口或已擦除。

每个新任务及纠正/撤回后重新读取，不用旧值补回。value/evidence不得进入长期记忆、日报、索引或案卷缓存；仅在用户已允许的持久记录内保留contextRef、purposeCode、consentVersion、factId/revision、operationId/auditOperationId等无值引用。新授权和引用都不隐含额外写权限。

每次成功读取（含空结果）产生新的READ_AUDIT技术观察：auditOperationId由服务生成，readOnlyHint=true表示不改画像正文/不扣费，idempotentHint=false反映每次审计号不同。回执记录读取者来源和准备返回的factId/revision，不存正文；deliveryStage=SERVICE_RESULT_PREPARED不是宿主收到、完整阅读、模型采用或成交证明。撤权后的失败读取不会生成成功读回执。

confirmation=ACCOUNT_OWNER只表明本人网页确认。当前产品/参与者仍是client_declared，hostExecutionProven、自然和产品信用标志保持false；没有宿主签名不妨碍本人已同意的画像闭环，但不授予专家保密权限或可信逐成员执行结论。
