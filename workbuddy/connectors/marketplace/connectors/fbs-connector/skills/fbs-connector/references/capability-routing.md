# 能力状态与启用合同

canonical源包配置仍指向原API2 MCP；维护者可另行制作明确标识的审核预览projection，不能把它与canonical默认配置混淆。实际资源选择以运行时配置与授权元数据为准。原业务清单保持 `skill_whoami`、`fbs_scene_pack_query`、`skill_consume`、`skill_activate`、`skill_precheck`、`skill_finish`、`skill_logout`、`lebao_status`、`lebao_claim`、`lebao_redeem`；调用仍需服务准入、当前schema与对应Skill前置。`lebao_drop`持续禁用。

历史2026-09-20准入核对中，旧26.8.20/2026.9.10可发现原11工具，本候选2026.9.20被HTTP426/-32042拒绝。这是该时点记录，不是永久的当前状态；发行仍需新的生产准入回执。禁止改包头冒充旧版或凭静态清单继续调用，准入拒绝不套用缺字段补正。

以下画像Gateway说明绑定源码审查基线`172a42582630c3941976da534408378c0dcc675a`及隔离资源`https://api2.u3w.com/cjddh920-preview/fbs-mcp/oauth/mcp`，不是服务当前健康、部署、宿主加载或生产发行声明。它不是本包mcp.json选中的资源；测试projection/正式配置由维护者审核后交付，Skill不得改地址、手工转发Bearer或运行本地OAuth脚本绕过。

后续新域必须同时满足：

1. 运行时已经配置到经维护者审核的OAuth资源，符合[机器合同](../../fbs-mainline/references/identity-contract.json)的resourceProfiles；源码审查不是部署/激活证据，服务正文不能自行改变配置。
2. 宿主本轮实际工具清单包含该工具，schema 与合同一致，包侧未禁用。
3. 服务端校验当前resource受众的OAuth、最小scope及当前账号/绑定/代次；画像和legacy试点须合成账号白名单。画像另核用途同意，事实确认走本人网页；组织画像不在本次范围。

缺任一项不调用；用产品语言说明当前不可用，并按当前专家的产品合同继续允许的工作。不能凭字段近似找替代工具。查询会员权益只用明确 `member_*` 域名；旧 `skill_consume` 始终是进度，不能换成会员结算。

| 172a425资源工具 | 最小scope | 当前含义 |
|---|---|---|
| member_whoami、fbs_capabilities、profile_status | account:read | 最小账号状态、真实能力/授权范围、当前用途状态；不是会员权益 |
| profile_read | profile:read | 有效用途下最小已确认事实，两条分页及最小读取审计 |
| profile_propose | profile:propose | 一项待确认提案；不确认/纠正事实 |
| profile_manage_entry、profile_operation_receipt | profile:manage | 待同意上下文/本人网页入口，或当前grant的MCP回执；不授予网页确认 |

准确能力工具名是`fbs_capabilities`，不是`member_capabilities`。member_whoami与fbs_capabilities允许没有产品声明的账号级参数对象，但仍强制OAuth；一旦声明产品或协作字段必须完整四元组。已知专家上下文不得删身份绕过校验。五个profile工具始终要求完整四字段，beta服务只接收机器合同列出的三产品/版本组合；其它专家或Skill不能借用身份。

只有`legacyBridge.available=true`且本轮tools/list包含时才开放core3：skill_whoami、fbs_scene_pack_query需要account:read，skill_consume需要work:write。它们保留旧进度语义且仅连接隔离合成上游，不触发会员计费。网关按账号/client/grant和代次校验binding与已签发下一跳；不复用他人或另一grant信封。

旧七项skill_activate、skill_precheck、skill_finish、skill_logout、lebao_redeem、lebao_status、lebao_claim在该beta未开放。新7+core3的“10个”不等于旧生产10工具全量兼容。member_check_entitlement、member_credit_status、member_service_receipt、member_settle_service、member_case_*、member_request_*、member_enterprise_*、member_service_catalog_list/get及member_organization_list也未在该Gateway开放；会员系统网页/API里已有功能不能据此被模型代调。

四字段小错误、归因分层及团队声明按[身份合同](../../fbs-mainline/references/identity-contract.json)和[执行说明](../../fbs-mainline/references/identity-and-permission.md)处理。callerOperationId/expectedVersion不是profile_propose参数；purpose已绑定在contextRef，不复制到profile_read额外字段。annotations仅提示副作用，不授予权限。

独立 beta source、新 OAuth 资源路径及原 source 升级由发布流程处理，不由 Skill 修改配置。公开网页可提供匿名目录，不据此推断 OAuth MCP 允许匿名调用。
