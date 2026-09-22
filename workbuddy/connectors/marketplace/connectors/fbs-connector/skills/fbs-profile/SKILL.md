---
name: fbs-connector-profile
description: "说明本人画像的可用条件；默认连接器仅提供指引，经审核OAuth资源实际开放并获用途授权后才读取或提案。"
description_zh: "默认仅说明画像授权与管理方式；仅在经审核资源实际开放后执行。"
description_en: "The default connection provides profile guidance only; execute purpose-limited reads or proposals only on an approved, available resource with consent."
version: "2026.9.20"
author: "FBSir"
---

# 本人画像

配置仍为旧生产 URL 时，本技能是 `configured_legacy_endpoint_guidance_only`。以下记录已审查的画像Gateway协议基线，不宣称服务当前部署或宿主授权状态。只有配置到经维护者审核的OAuth资源，且本轮工具、schema、授权和合成测试账号准入均满足[能力门](../fbs-connector/references/capability-routing.md)后才执行；本文不修改mcp.json，不代替完整业务或宿主验收。

先读[画像用途与提案](references/profile-purpose-and-provenance.md)。基线 `172a425` 的五个画像工具均在实际 arguments 顶层要求完整专家四字段；只带当前 schema 接受的额外参数：

- `profile_status`（account:read）：可选 contextRef；核对当前账号和用途状态，不返回事实值。
- `profile_read`（profile:read）：必填 contextRef；可选 fieldKeys（1–5个唯一、本用途合法字段）和 afterFactId。固定最多2条，使用 hasMore/nextAfterFactId 接续，不另传 purpose/page/pageSize。
- `profile_propose`（profile:propose）：必填 operationId、contextRef、fieldKey、value、evidence、claimKind；每次新增一项待确认草案。value/evidence各最多256字符；不传 callerOperationId、expectedVersion 或 amend。
- `profile_manage_entry`（profile:manage）：必填 operationId、contextType、contextId、purposeCode，建立待同意上下文并返回本人网页入口；这一步有元数据写入，不确认事实。
- `profile_operation_receipt`（profile:manage）：按原 operationId 查询当前 client/grant 的 MCP 操作或读取审计；不用于查询另一 grant 或网页操作。

先网页同意用途，再逐项网页确认；claimKind必须明确为user_statement、artifact_observation或expert_inference，确认不升级sourceEvidenceTrust。纠正与单项/用途撤回也在本人网页按expectedVersion执行；当前没有profile_confirm、删除、导出工具或已实现的删除/导出页面。撤回保留版本和审计，不称数据已擦除。

每个新任务及纠正/撤回后重新读当前事实；不把value/evidence写长期记忆，仅在获准持久记录范围保留ID/版本引用。读回执的SERVICE_RESULT_PREPARED不证明宿主收到或模型采用。无当前同意或工具时按原产品合同继续允许的首值，不猜替代接口。
