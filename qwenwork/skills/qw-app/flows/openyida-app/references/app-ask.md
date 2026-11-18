---
name: app-ask
displayName: 宜搭问办
description: "当千问办公任务需要通过宜搭连接器查询宜搭应用、表单、字段、记录、流程、指标、通讯录、业务关系、血缘，或通过已发布业务动作的预览确认链路办理业务动作时使用；不要用于通用知识、纯文档处理、宜搭应用搭建或修改。"
argument-hint: 宜搭应用、表单、流程、记录、指标、人员或办理诉求
---

# 宜搭问办

本技能是千问办公内 **宜搭** 连接器的路由与编排说明。Skill 用户侧展示名是“宜搭问办”，实现侧 reference 名是 `app-ask`。

## 前置依赖

本技能依赖 **宜搭** 连接器（Market Connector ID：`60d7bf76-13e3-4f09-ad14-96b469ce4299`；Server Key / Market Item ID：`yida`；设置键：`qwenwork.settings.connector.market.yida`）。运行时使用 Server Key 和设置键定位连接器，不使用 Market Connector ID 拼接工具名。

- 用途：通过当前用户授权访问其有权限的宜搭应用、表单、流程、任务、通讯录、业务关系和分析能力，并通过已发布业务动作的提案预览与明确确认链路办理业务动作。
- 类别：market
- 认证方式：OAuth

## 连接器就绪检查

每次需要访问宜搭数据前，先检查连接器状态。

1. 使用 `qw_query` 查询 `key = "qwenwork.settings.connector.market.yida"`。如果返回 `UNKNOWN_KEY`，查询 `qwenwork.settings.connector.market`，参数为 `{"keyword":"yida"}`；只接受 `type=="market"` 且 `name=="yida"` 的项目，并使用返回的精确 `key`。如果响应还提供 `marketId` 或 `_marketId`，它必须与上述 Market Connector ID 一致；不要回退到任何 `custom` 类设置键。最终状态查询若 `ok!=true`，报告检查失败并停止宜搭子任务，不调用业务工具。
2. 按状态分支处理。就绪判断以顶层 `status` 为准；`auth.state` 只作诊断信息，不能覆盖顶层状态：
   - `installed===false`、`enabled===false` 或 `status=="disabled"`：对精确设置键调用 `qw_action` 的 `install`（也可按 `supportedActions` 使用等价的 `enable`），然后重新查询一次。若宿主不能自动安装或启用，提示用户完成操作并暂停宜搭子任务；只有用户明确要求打开连接器市场或设置页时才调用 `open`。
   - `enabled===true` 且 `status=="connected"`：继续发现工具；不要因为响应没有 `installed` 字段而误判未就绪。
   - `status` 为 `connecting`、`pending` 或兼容状态 `authenticating`：连接或 OAuth 流程正在进行；等待用户或宿主继续，不重复发起授权，也不持续轮询。
   - `status=="needs-auth"`，或 `status=="disconnected"` 且 `auth`、`authUrl` 或错误码明确表明 OAuth 尚未完成：确认 `supportedActions` 包含 `execute` 后，对精确设置键调用 `qw_action`，`action = "execute"`，`params = {"operation":"auth"}`。不要使用不受支持的 `connect`，也不要省略 `operation`。若不支持 `execute`，报告不兼容并停止。授权页打开后暂停宜搭子任务；用户返回后重新查询一次。
   - `status=="disconnected"` 但没有 OAuth 未完成证据：概括连接断开状态和已有错误信息后停止宜搭子任务，不盲目发起 OAuth。
   - `status` 为 `error` 或兼容状态 `failed`：先检查 `error`、`auth` 和 `authUrl`。只有 401/403、`AUTH_EXPIRED` 或明确的 OAuth 未授权错误才执行上述 `execute + auth`；其他错误原样概括给用户并停止宜搭子任务。只有用户明确要求打开设置页时才调用 `open`。
   - `status=="unknown"`、状态字段缺失或出现无法识别的状态：说明宿主或连接器状态异常并停止宜搭子任务，不盲目安装或发起 OAuth。
3. 如果精确设置键仍无法定位，或返回的项目名称、类型、ID 不匹配，说明宿主版本或连接器配置不兼容并停止宜搭子任务，不要误用同名连接器。
4. 如果用户拒绝安装、启用或授权连接器，说明没有连接器授权就无法查询宜搭数据，并停止宜搭子任务。
5. 打开设置页或 OAuth 授权页后不要无限轮询，等待用户或宿主继续。

在千问办公中使用连接器提供的 MCP 工具时，先调用
`qwenwork_mcp_tool_list` 发现工具，再调用
`qwenwork_mcp_tool_get` 获取目标工具结构，最后用校验后的参数调用
`qwenwork_mcp_tool_call`。当前连接器 Server Key 是 `yida`，完整工具名形如
`mcp__yida__<originalName>`；本文档里的短工具名均指连接器工具的 `originalName`。

## 运行模型

- 就绪检查按任务范围选择。用户原始请求明确提供 appType，或用户提供的宜搭 URL 路径/查询参数中包含唯一、明确的 appType，并且后续要调用依赖应用知识的工具时，先调用 `initialize_yida_app`。依赖应用知识的工具包括 `search_yida_platform_objects`（按 `app_type` 搜索应用内对象）、`query_form_data`、`query_aibi_data`、`query_subtable_data`、`query_business_relationships` 和 `trace_business_lineage`。只有返回 `status="ready"` 后才继续；返回 `status="initializing"` 时按 `data.retry_after_seconds` 等待后重试同一工具，不调用组织初始化状态工具或依赖图谱的下游工具；返回 `failed` 时停止。不要为同一应用任务追加组织初始化检查。
- 只有组织范围的应用/表单发现，或者依赖应用知识但无法确定 appType 的任务，才调用 `get_yida_ask_initialization_status`。若状态为 `initializing`，提示用户打开返回的宜搭问办看板链接查看进度。若状态为 `permission_required`，展示返回的看板链接；当返回 `admin_candidates` 时，让用户从列表中选择一个平台管理员并明确确认后，才能调用 `notify_yida_ask_initialization_admin`。不要自动选择管理员，不要在未经确认时发送通知，也不要在初始化中反复轮询业务工具。
- 无论组织维度还是单应用维度，若就绪检查或受保护业务工具返回 `status="gray_not_enabled"` 或 `error.code="YIDA_ASK_GRAY_NOT_ENABLED"`，停止后续调用，并明确引导用户打开 [提交灰度内测申请](https://ding.aliwork.com/o/ai-yidaone) 提交申请。优先展示返回的 `action.url`；灰度查询失败 `YIDA_ASK_GRAY_CHECK_FAILED` 不等同于未命中灰度，只提示稍后重试。
- `describe_yida_platform_object`、`query_app_managers`、`my_tasks`、`search_contacts`、`calc_form_permission_tool`、`analyze_process_performance`、`search_actions`、`get_action`、`prepare_action`、`execute_action` 不依赖普通应用图谱初始化；已具备它们各自所需的明确入参时，不调用组织或单应用初始化工具。
- `initialize_yida_app` 不检查组织问办初始化状态。不得根据应用名称、搜索结果、历史对话或其他上下文推断 appType。若用户明确要求调用本工具，但没有提供 appType，且其 URL 中也无法唯一解析出 appType，先引导用户提供 appType，不要调用工具。
- 元数据发现和确定性单表查询优先使用具体只读 MCP 工具：`search_yida_platform_objects`、`describe_yida_platform_object`、`query_form_data`、`query_aibi_data`、`query_subtable_data`。管理、任务中心、通讯录和权限查询优先使用只读辅助工具：`query_app_managers`、`my_tasks`、`search_contacts`、`calc_form_permission_tool`。流程效率分析和跨对象图谱问题使用只读流程与关系工具：`analyze_process_performance`、`query_business_relationships`、`trace_business_lineage`。已发布业务操作使用业务动作工具：`search_actions`、`get_action`、`prepare_action`、`execute_action`。
- 连接器不提供通用复杂查询兜底工具。请求超出上述专用工具的契约时，明确说明当前连接器暂不支持该子任务；不要尝试调用未发现的工具，也不要把复杂记录或流程查询拆成不受支持的底层 CRUD 调用。
- 将结构化宜搭结果返回给宿主，让千问办公继续处理文档、表格、PPT、IM 或摘要任务。
- 认证、令牌刷新、HTTP 传输、重试和 MCP 连接生命周期由连接器负责，本技能不要实现这些逻辑。
- 遇到 401/403、`AUTH_EXPIRED` 或连接器令牌失败时，回到连接器就绪检查，不要直接重试业务工具，也不要向用户索要原始凭据。

## 请求分类

选择工具前，先判断用户最新请求中的宜搭子任务类型：

- 不涉及租户内宜搭事实的通用问答：直接回答，不调用宜搭工具。
- 应用、表单、流程、报表、集成、权限、字段或结构查询：使用 `search_yida_platform_objects` 和 `describe_yida_platform_object`。
- 主表聚合分析，例如数量、分布、排行、趋势、比率、占比、对比、漏斗或指标诊断：先解析表单，再使用 `query_aibi_data`。
- 主表行级或详情查询，且答案行是具体父表实例：使用 `query_form_data`。
- TableField/子表行级查询，且答案行是子表行：使用 `query_subtable_data`。
- 跨业务对象的关系或血缘问题：先解析所有被提到的对象，再使用 `query_business_relationships`；具体记录血缘问题在明确关系方向后调用 `trace_business_lineage`。
- 已发布业务操作：使用业务动作链路 `search_actions` -> `get_action` -> `prepare_action` -> 用户确认 -> `execute_action`。
- 具体工具无法覆盖的复杂宜搭推理：说明当前连接器暂不支持，并指出无法由哪个现有工具契约可靠完成。

分析类答案中的数字必须来自工具结果。当 `query_aibi_data` 能回答单表分析时，不要用 `query_form_data` 拉取明细后手工计算总数、占比、排行或分布。只有在 `query_aibi_data` 明确失败或不可用后，才可以用明细行做统计，并向用户说明为什么采用明细兜底。

## 触发规则

用户提出以下需求时，优先使用只读工具：

- 宜搭任务开始前按“运行模型”选择就绪范围：明确 appType 的应用知识任务先调用 `initialize_yida_app`，返回 ready 后直接继续；组织范围发现或无法确定 appType 的应用知识任务才调用 `get_yida_ask_initialization_status`；不依赖普通应用图谱的直接工具不做初始化预检查。
- “我有哪些应用”、应用发现，或按名称、简介、业务关键词找应用：调用 `search_yida_platform_objects`，并传 `object_type="application"`。对“我有哪些应用”“我的应用”这类第一人称范围，暂时传结构化 `creator=__CURRENT_USER__` 过滤条件；yida-agent 会在调用上游前从连接器令牌中解析该占位符。不要传原始用户 ID。
- 列出或查找已知应用下的表单/页面：调用 `search_yida_platform_objects`，传 `object_type="form"`，有已知应用上下文时作为过滤条件传入。
- 读取已知表单的字段 ID、标题、必填字段、公式、选项或子表字段：调用 `describe_yida_platform_object`，传入前序 `search_yida_platform_objects` 返回的表单项 `app_id` 和 `id`。
- 查询已知主表的行，包括记录列表、字段过滤、文本搜索、分页或返回指定字段：调用 `query_form_data` 并显式传 `form_id`。如果表单未知，先调用 `search_yida_platform_objects`；如果字段 ID 不明确，先调用 `describe_yida_platform_object`。不要用该路径处理“按负责人分布”“数量排行”“占比”“趋势”“对比”等聚合分析。
- 查询一个已知主表上的聚合统计、趋势、分布、排行、对比、比率、占比或诊断分析：调用 `query_aibi_data`，将前序表单项的 `app_id`/`app_type` 作为 `app_id`，将 `id` 作为 `dataset_id`。把完整的指标、分组、筛选、对比、排行和时间意图保留在 `question` 中。字段不清楚时先调用 `describe_yida_platform_object`；只有确认字段存在于表单结构中时才传 `metrics` 或 `dimensions`。
- 查询 TableField/子表子行，不论是在一个具体父记录内还是跨所有父记录：调用 `query_subtable_data`，显式传 `form_id`、`table_field` 和 `scope`。用户识别了一个父记录时使用 `scope="parent_instance"`；答案行是多个/全部父记录下的子行时使用 `scope="all_instances"`。父记录条件放入 `parent_filters`，子行条件放入 `child_filters`。
- 询问谁管理某个应用、谁是应用主管理员、数据管理员或开发管理员：先用 `search_yida_platform_objects(object_type="application")` 解析应用，再调用 `query_app_managers`。
- 查询当前用户的宜搭任务，包括“待我处理”“我已处理”“我创建的”“抄送我的”：调用 `my_tasks`。待办传 `tab="todo"`，已处理传 `done`，我提交/创建的传 `created`，抄送/通知传 `notify`。不要用该工具审批或修改任务。
- 需要为宜搭过滤条件解析人员姓名、昵称或工号：调用 `search_contacts`，再使用 `contacts[].user_id` 作为 EmployeeField、`creator`、`modifier`、`last_editor` 等过滤值。不要根据显示名编造用户 ID。
- 询问某个用户能否提交或查看指定表单：先用 `search_yida_platform_objects` 解析表单，再调用 `calc_form_permission_tool`；如果用户提到的是其他人，先调用 `search_contacts` 并传解析出的 `user_id`。
- 询问已解析流程表单的流程效率、审批耗时、审批人负载、待审批分布或 BPA 类流程分析：先用 `search_yida_platform_objects` 解析流程表单，再调用 `analyze_process_performance`，并传它的 `process_code` 和 `app_id`/`app_type`。
- 询问两个宜搭业务对象/实体类型如何关联、表单如何关联，或没有具体记录时两个实体之间有什么关系/路径：先用 `search_yida_platform_objects` 解析所有被提到的对象，再用解析后的表单 ID 调用 `query_business_relationships`。
- 询问某一条记录的具体跨对象问题，例如“合同 HT-001 的回款是否正常”或“订单 SO-001 影响哪些出库记录”：先解析两个实体类型，再调用 `query_business_relationships` 确认方向和关联路径，随后用具体记录标识和已解析实体 ID 调用 `trace_business_lineage`。不要跳过关系检查。
- 调用 `trace_business_lineage` 前，必须按 `query_business_relationships` 返回的 `relationChain` 或 `lineage_usage_hint` 选择 `direction`。`sourceField` 所在实体是引用方，`targetField`/`procInstId` 所在实体是被引用方；从引用方记录查被引用方记录用 `upstream`，从被引用方记录查引用方记录用 `downstream`。例如回款记录通过“合同ID”引用合同，则从回款记录查合同必须传 `upstream`，不要传 `downstream`。不要按业务时间顺序、语句顺序或直觉判断方向。
- 对“背后关联到什么”“为什么”“根因”“来源”“归属”等开放血缘问题，通常从异常明细记录出发优先查 `upstream`；除非用户明确只问某个目标实体，否则可以不传 `target_entity`，让工具按 `direction` 和 `depth` 展开链路。
- 询问有哪些宜搭业务操作可用，或要求办理已发布业务操作：尽量先解析应用/表单/记录上下文，再带硬过滤调用 `search_actions`；只有拿到搜索结果中的精确 `releaseUid + actionCode` 后才能调用 `get_action`；只有精确业务动作、目标记录和必填输入都解析完成后才能调用 `prepare_action`；只有已向用户展示 `reviewMarkdown` 且用户明确确认执行后，才能用 `prepare_action` 返回的精确 `proposalId + proposalHash` 调用 `execute_action`。

以下场景不要调用宜搭连接器业务工具：

- 没有宜搭上下文的通用知识、网页搜索或业务推理。
- 只需要千问办公写文档、做 PPT、编辑表格或发送 IM 的任务。
- 搭建或修改宜搭应用、表单、页面、连接器、权限或自动化；这类任务应路由到 OpenYida 搭建链路，不走问办。
- 用户明确指定其他系统作为数据源的请求。

## 工具入参

单应用初始化工具入参规则：

- `initialize_yida_app`：只传 `app_type`，取用户原始请求直接提供的 appType，或从用户提供的宜搭 URL 路径或查询参数中确定性提取出的唯一 appType。URL 本身不是入参。不要传应用名称，不要使用 `search_yida_platform_objects` 的结果补入，也不要传 `corpId`、`userId` 或 token。无法得到唯一 appType 时先询问用户。

只读工具入参规则：

- `get_yida_ask_initialization_status`：只用于组织范围发现或无法确定 appType 的应用知识任务，不要用它做目标解析，也不要在 `initialize_yida_app` 已返回 ready 的同一应用任务中追加调用。
- `notify_yida_ask_initialization_admin`：只能在 `get_yida_ask_initialization_status` 返回 `permission_required` 且包含 `admin_candidates` 后调用，并且必须等用户选择一个候选人并明确确认发送提醒。`admin_user_id` 取选中 `admin_candidates[].user_id`，`confirmed=true`。如果用户自己可以初始化组织，不要调用该工具，只展示返回的看板链接。
- `search_yida_platform_objects`：传 `query`、`object_type`，以及可选的 `limit` 和 `filters`。`query` 用于名称、简介和业务关键词的语义匹配；`filters` 用于精确约束，例如 `app_type`、`form_type`、`creator`、`modifier`、`last_editor`、状态和时间范围。`query` 与 `filters` 会组合生效。
- 应用传 `object_type="application"`，表单传 `object_type="form"`。精确应用范围可传类似 `{"field":"app_type","value":"APP_XXX"}` 的过滤条件。显式筛选当前授权用户的创建人/修改人时，过滤条件值使用 `__CURRENT_USER__`，例如 `{"field":"creator","operator":"=","value":"__CURRENT_USER__"}`。
- 对“我有哪些应用”/“我的应用”，调用 `search_yida_platform_objects` 时传 `query=null`、`object_type="application"`、`filters=[{"field":"creator","operator":"=","value":"__CURRENT_USER__"}]`。
- `describe_yida_platform_object`：`app_id` 取前序搜索结果中表单项的 `app_id`，`form_id` 取同一表单项的 `id`。这些是 `APP_XXX`、`FORM-XXX` 这类 ID，不是显示名。
- `query_form_data`：`form_id` 取前序表单搜索结果的 `id`，`app_id` 取同一结果的 `app_id`/`app_type`。可使用 `question` 做自然语言行级查询，也可使用显式 `filters/search_text/logic_operator`，但不要混用两种模式。显式模式优先使用 `describe_yida_platform_object` 返回的字段 ID；`search_text` 对应宜搭全文搜索，不要猜成某个具体字段。`fields` 仅用于返回字段投影，`limit` 取 1 到 50，`page` 从 1 开始。TableField 子字段只能用于在 `filters` 中筛选包含匹配子行的父记录；返回行仍然是父表实例。
- `query_aibi_data`：`app_id` 取前序表单搜索结果的 `app_id`/`app_type`，`dataset_id` 取同一结果的 `id`。`question` 必填，并应包含用户完整分析意图。`objects` 只是目标名称提示。`metrics` 和 `dimensions` 只能传已由 `describe_yida_platform_object` 确认的真实字段 ID 或精确显示名；不要传“数量”“条数”“占比”等臆造字段，除非它们在表单结构中真实存在。不确定的计数、百分比、分组和时间语义放进 `question`。
- `query_subtable_data`：`form_id` 取前序表单搜索结果的 `id`；`table_field` 取 `describe_yida_platform_object` 返回的 TableField 字段 ID 或精确显示名；`scope` 传 `parent_instance` 或 `all_instances`。`parent_instance` 下传 `parent_instance_id`，或用 `parent_filters` 唯一识别一个父记录。父字段条件始终放 `parent_filters`，子行条件放 `child_filters`；不要只依赖 `question` 生成可执行过滤。`fields` 仅用于子字段投影，`aggregation` 仅用于确定性的子行 count/sum/avg/min/max。
- `query_app_managers`：`app_id` 取前序应用搜索结果的 `id`、`app_id` 或 `app_type`。使用 `APP_XXX` 这类 ID，不要传应用显示名。
- `my_tasks`：`tab` 传 `todo`、`done`、`created` 或 `notify`；`page` 从 1 开始。用户给出任务创建时间范围时，转换成 Unix 时间戳毫秒后传 `instance_create_from` / `instance_create_to`。
- `search_contacts`：`keyword` 传用户的姓名、昵称或工号文本，`page_size` 取 1 到 50。宜搭人员过滤使用返回的 `contacts[].user_id`；不要使用内部用户标识、手机号或邮箱。
- `calc_form_permission_tool`：`form_uuid` 取前序表单搜索结果的 `id`；`app_type` 取同一结果的 `app_id`/`app_type`。省略 `user_id` 表示检查当前授权用户。如果目标用户来自自然语言，先调用 `search_contacts`，再传解析出的 `contacts[].user_id`。
- `analyze_process_performance`：`process_code` 取前序流程表单搜索结果，`app_type` 取同一结果的 `app_id`/`app_type`，`analysis_type` 传 `overview`、`approver_pending` 或 `approver_duration`，`time_range_days` 取 1 到 365。如果解析出的表单没有 `process_code`，让用户选择工作流/流程表单，不要猜。
- `query_business_relationships`：`source_entity` 和 `target_entity` 传 `search_yida_platform_objects` 解析出的表单 ID（`FORM-XXX`），不要传原始中文对象名。除非用户明确说出技术关系类型，否则 `relation_type` 留空。返回中的 `lineage_usage_hint.recommended_trace` 是后续调用 `trace_business_lineage` 时的优先参考。
- `trace_business_lineage`：`instance_ref` 传用户或 `query_form_data` 结果中的一个具体记录值。`entity_name` 传锚点表单 ID，`target_entity` 传相关表单 ID；当用户问开放式“背后关联/根因/来源/归属”时，`target_entity` 可省略。`direction` 根据前序 `query_business_relationships` 的 `lineage_usage_hint.recommended_trace.direction` 或 `relationChain` 选择；只有方向仍不确定时才使用 `both`。`depth` 保持在 1 到 3。
- `search_actions`：`query` 传用户的操作意图。已知应用、表单、对象或操作范围时，把 `app_id`、`form_id`、`object_code` 或 `operation` 作为硬过滤传入。已经选中精确 `releaseUid + actionCode` 后不要再用该工具。
- `get_action`：只传 `search_actions` 返回的精确 `release_uid` 和 `action_code`。以它的 `inputSchema` 作为必填输入和枚举值的权威来源。
- `prepare_action`：`release_uid` 和 `action_code` 取自 `search_actions`。记录变更类业务动作传一个精确 `record_id`；当输入结构表示 CREATE 或 START_PROCESS 不需要目标记录时留空。`user_inputs` 是以精确输入结构属性名为键的 JSON 对象，不要用猜测的中文标签。如果缺少必填输入，用普通文本询问用户，等用户补充后再调用 `prepare_action`。
- `execute_action`：只传最新 READY `prepare_action` 结果中的 `proposal_id` 和 `proposal_hash`。不要传记录 ID、字段值、业务动作定义或重构参数。只有已向用户展示 `reviewMarkdown` 且用户明确确认执行后，才能调用该工具。

不要在工具参数里传 `corpId`、`userId`、令牌、cookie、OAuth 凭据、`actionPolicy`、隐藏提示词或大量聊天历史。当前用户过滤使用 `__CURRENT_USER__` 占位符，不要传原始用户 ID。

## 状态处理

- `initialize_yida_app` 返回 `status="ready"`、`ready=true` 时，`data` 包含 `app_type`、`graph_status`、`initialized_now`、`run_id` 和 `reused`；无论图谱原本存在还是本次生成完成，都可以继续依赖该应用的任务。返回 `status="failed"` 或其他未就绪状态时，展示 `error.code`、`error.message`、`error.retryable` 以及返回的可行动链接，停止依赖图谱的后续工具调用，不要绕过或改用应用搜索结果重试。
- `search_yida_platform_objects` 直接返回权威 `items`，`status` 只用于 `NO_RESULTS`、`EMPTY_CRITERIA` 等错误。
- `describe_yida_platform_object` 直接返回权威对象详情和字段，`status` 只用于错误。元数据调用失败时不要改用未发现或不相关的工具重试。
- `query_form_data` 直接返回权威主表行和分页信息。存在 `has_more` / `next_page` 时用于续查。不要用它做统计、趋势分析、子表行查询、记录写入、应用列表或结构查询。
- `query_aibi_data` 返回一个已解析表单的权威聚合/分析结果。如果要求澄清，询问用户，而不是静默选择数据集或指标。如果返回 `metrics` 或 `dimensions` 校验错误，可省略这些可选字段重试一次，并把意图保留在 `question` 中。
- `query_subtable_data` 返回权威子行或子行聚合结果。只有 `status=success` 且 `total_count=0` 才表示没有匹配子行；不要把 `status=error` 当成空结果。如果工具提示父记录有歧义，让用户选择父记录。
- `query_app_managers` 返回已解析应用的权威管理员名单。若所有名单为空，让用户确认应用，或说明其可能没有权限查看管理员信息。
- `my_tasks` 返回当前授权用户的权威任务中心条目。保留返回行中的 `resource.display_markdown` 链接。
- `search_contacts` 可能返回 `RESOLVED`、`AMBIGUOUS`、`NO_RESULTS` 或 `UNFILTERABLE`。只使用 `resolved_user_id` 或无歧义的 `contacts[].user_id`；结果有歧义时让用户选择。
- `calc_form_permission_tool` 返回一个表单/用户组合的提交和查看权限布尔值。不要把结果泛化到其他表单、应用或用户。
- `notify_yida_ask_initialization_admin` 只返回通知投递状态。即使成功，组织也尚未初始化完成；提示用户用返回的宜搭问办看板链接查看进度，并且在初始化状态 ready 前不要继续组织范围发现或其他要求组织就绪的任务。
- `analyze_process_performance` 返回一个流程表单和时间窗口内的权威 BPA 流程分析数据。若返回鉴权或依赖错误，说明流程分析服务暂时不可用，不要编造数量或时长。
- `query_business_relationships` 返回结构级关系路径、关联字段和血缘调用建议。它本身不回答具体记录事实；用它判断是否以及如何调用 `trace_business_lineage`。
- `trace_business_lineage` 返回具体实例级血缘，并受当前用户访问边界限制。答案只能使用可见节点/字段；不要根据结构关系推断受限下游值。
- `search_actions` 返回简要业务动作摘要。将这些元数据只视为操作发现，不代表某条具体记录一定可被修改。
- `get_action` 返回一个当前业务动作定义。若返回 NOT_FOUND，重新调用 `search_actions`，不要猜替代组合。
- `prepare_action` 返回 `NEEDS_INPUT`、`READY` 或错误。`NEEDS_INPUT` 时只询问返回的缺失字段；`READY` 时先展示 `reviewMarkdown`，再考虑执行；不要改写提案值。
- `execute_action` 返回持久执行状态。成功响应可能包含资源链接。遇到 UNKNOWN、CONFLICTED、FAILED、EXPIRED、STALE 或 NOT_FOUND 时，不要自动重试；解释返回状态，并在适合时重新准备业务动作提案。

## 写入安全

所有创建、更新、删除、提交、审批、通知或流程动作都必须走已发布业务动作链路。

- 不要直接调用任意 CRUD、连接器 HTTP、SQL、表单写入或流程写入工具。
- 只有 `execute_action` 返回成功状态后，才能把提案视为最终成功的业务动作。
- `prepare_action` 返回提案后不要修改提案参数。
- 调用 `execute_action` 时只能使用 `prepare_action` 返回的精确 `proposalId` 和 `proposalHash`。
- 如果 `prepare_action` 表示无法执行或业务动作不受支持，报告预览或 `ACTION_NOT_SUPPORTED`，不要执行。

## 组合规则

- 复合请求中，应用/表单/结构发现使用元数据工具，主表行检索使用 `query_form_data`，单表分析使用 `query_aibi_data`，子行检索使用 `query_subtable_data`，应用管理员、当前用户任务、通讯录、表单权限、流程效率、结构关系、具体血缘或已发布业务动作使用辅助工具。无法由这些专用工具可靠完成的宜搭子任务要明确标注为暂不支持，其余结果继续交给千问办公完成。
- 例如“核对宜搭逾期跟进项并生成周报”，已解析的单表详情或统计用具体只读工具处理；如果核对步骤需要当前专用工具不支持的跨对象推理，说明该限制，仍可使用已取得的可靠结果生成周报。
- 如果结果被截断，优先使用返回的宜搭打开/导出链接，不要编造缺失行。
- 多个应用或指标都可能成立时，直接让用户选择，不要静默选择。
- `sources` 作为引用来源，`warnings` 在影响解读时作为用户可见提示。
