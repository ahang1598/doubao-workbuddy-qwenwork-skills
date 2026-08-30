---
name: picsetai-model-generate
displayName: Picset AI 模特图生成
name_en: picsetai-model-generate
description: >
  用于 Picset AI 电商视频流程中的模特图生成和模特形象确认。适用于用户希望商品视频、带货视频、种草视频、口播视频、广告视频或爆款复刻视频中出现固定模特形象，但没有提供模特图，或希望先生成可确认的模特图片作为视频素材的场景。该 Skill 会根据用户要求和电商短视频语境等需求，生成可用于后续视频生成或视频复刻流程的模特图片引用。
description_en: >
  Handle Picset AI model image generation, preview, confirmation, and handoff for ecommerce video creation and recreation flows.
argument-hint: 原视频任务上下文、模特要求和商品信息
---

# Picset AI 模特图生成

本子 Skill 负责视频流程内的模特图生成与确认。执行时必须使用共享协议：

- `../shared/handoff-protocol.md`
- `../shared/credit-confirmation-protocol.md`

从主 Skill 或视频子流程接收上下文后，只处理模特图生成相关步骤。模特图确认前，不得回到最终视频生成提交。

## 输入与默认值

- 读取原视频任务的 `VideoHandoffContext`，复用已确认商品信息、商品图 refs、国家、语言、视频类型、时长、比例和固定模特需求。
- `project_id` 只内部保存和透传，不展示给用户；服务端自动创建或恢复真实 `project_id` 并返回后，必须内部保存并绑定到本次模特生成归属。视频或复刻流程中已有 `script_id` 或 `replica_script_id` 时，可让后端恢复同一项目归属；生成前必须具备后端返回的有效 `project_id`、`script_id` 或 `replica_script_id`。没有后端返回的 `project_id` 时，使用 `script_id` 或 `replica_script_id` 让后端恢复项目归属。不得传空字符串作为 `project_id`，不得臆造项目归属、不得用脚本任务 ID 冒充 `project_id`、不得用历史项目标识试探。不得围绕 `project_id` 要求用户提供、修正或查找。
- 如果模特生成需要用户提供的输入图，收到输入图后，必须按服务端给出的直传地址通过 HTTP PUT 上传到 OSS，再把上传后的素材引用写入 `VideoHandoffContext.assets`。不得使用 OSS SDK，不得使用 oss2，不得引入第三方上传依赖。
- 没有明确人物要求时，默认人物要求为：中国模特、简体中文语境、中国电商短视频表达。
- 如果用户补充人物要求，只记录可读的人物要求摘要到 `VideoHandoffContext.drafts.model.person_requirements` 和 `person_summary`，不得记录最终模特 prompt。

## 模特生成流程

模特生成由普通后端网页端 API service 支撑，MCP 只是复用同一 service。素材和人物要求齐备后，必须先调用 `generate_model_image` 并传 `preflight_only=true`、`confirmed=false` 做预估；展示返回的 `estimated_credits` 和可理解的计费说明，等待用户确认后才允许再次调用 `generate_model_image` 并传 `preflight_only=false`、`confirmed=true` 进入生成。Skill 不得跳过先预估、用户确认、后生成的顺序，不得在确认前直接生成模特图。

服务端生成最终模特 prompt 并生成模特图；Skill 不得生成、不得展示最终模特 prompt，也不得把最终模特 prompt 写入 `VideoHandoffContext`。`generate_model_image` 默认 `estimated_credits=0`，后端可配置计费；如果预估返回非零 `estimated_credits` 或非零积分，必须先让用户确认具体积分，非零积分确认先于 `preflight_only=false`、`confirmed=true` 的 `generate_model_image` 生成调用；未确认非零 `estimated_credits` 或非零积分时，不得调用 `generate_model_image` 进入生成。只展示可理解的计费说明，不展示内部任务 ID 或最终模特 prompt。

服务端可能同步返回结果，也可能异步生成。同步返回结果时，必须把同步结果中的 `model_image_ref` 保存到 `VideoHandoffContext`。异步返回时，必须把 `model_task_id` 保存到 `VideoHandoffContext.service_state.model_task_id`，再调用 `poll_model_status` 查询结果；恢复、继续或重试时，恢复 `model_task_id` 后继续调用 `poll_model_status`，不得重复调用 `generate_model_image` 造成重复生成。

生成完成后，只展示模特图给用户确认，不展示最终模特 prompt、不展示内部任务 ID、不展示服务端请求参数。

## 确认与回填

用户确认模特图后，必须把模特图引用以 `asset_role=model_image` 写入 `VideoHandoffContext.assets`，并回填原视频任务使用的 `model_image_ref`。`model_image_ref` 可复用于普通视频生成或商品视频生成，也可复用于复刻 replica 流程。确认模特图先于最终视频生成：未确认模特图时，不得生成最终视频，不得提交 `generate_video`。

如果用户拒绝模特图或修改人物要求，必须把 `VideoHandoffContext.drafts.model.status` 置为 `awaiting_confirmation` 或重新生成，丢弃旧的 `model_image_ref`，不得继续使用未确认模特图生成最终视频。

## WorkBuddy 连接器补充规则

回复语言默认使用简体中文；用户明确使用英文时可用英文回复。解释工具字段、错误和确认信息时保持用户可理解，不展示内部任务 ID、完整密钥、敏感素材 URL 或 `project_id`。

`project_id` 只内部保存和透传，不展示给用户；脚本或方案工具未传 `project_id` 时由服务端自动创建或恢复真实 `project_id` 并返回，收到后必须保存；未返回时保存 `script_id` 或 `replica_script_id`。预估或生成前必须具备后端返回的有效 `project_id` 或可让后端恢复项目归属的脚本任务 ID。没有后端返回的 `project_id` 时，使用 `script_id` 或 `replica_script_id` 让后端恢复项目归属。不得传空字符串作为 `project_id`，不得臆造项目归属、不得用脚本任务 ID 冒充 `project_id`、不得用历史项目标识试探。不得围绕 `project_id` 要求用户提供、修正或查找。

## 用户回复规则

普通用户回复不得展示英文工具名、字段名、内部状态名、接口错误码或原始错误字段；工具名和字段名只可在内部执行或开发文档中使用。不得向用户说明底层上传实现细节、临时凭据、存储路径、内部素材引用或参数字段。向普通用户说明进度时，改用中文动作表达，例如：生成脚本、预估积分、可以上传、我会继续处理素材、素材已准备好、开始生成视频、查询生成进度。

不要说“我先确认某个内部方法在脚本阶段如何引用这张图”这类实现说明；应改说“我先根据这张图整理视频脚本，再给你确认”。

不要解释底层上传、存储、登记和参数传递细节；应改说“可以上传，我会继续处理素材”或“素材已准备好，现在继续生成”。

不得向用户说明内部执行动作、工具准备过程、服务端错误码或自动恢复细节。不说不会扣积分，只说正在预估积分；不说服务端项目错误或重试细节，只说我会继续处理；不说具体素材处理动作，只说素材已准备好。

预估失败时，只说暂时无法完成积分预估；状态说明只使用自然中文，不展示原始字段或状态值。

## WorkBuddy 内部执行规则

WorkBuddy streamableHttp 远程工具只声明服务端工具，不要求也不得调用本地 stdio 辅助工具。

远程工具：

- `get_reference_image_upload_token`
- `register_reference_image`
- `estimate_video_generation`
- `create_video_script`
- `create_replica_script`
- `generate_model_image`
- `generate_video`
- `poll_video_status`
- `poll_model_status`
- `get_video_task_status`

模型：

- `Seedance 2.0`：默认模型。
- `Seedance 2.0 Fast`：快速模型。
- `Seedance 2.0 Mini`：轻量模型。

WorkBuddy 用户提供本地商品图或目标视频时，必须先基于已收集素材意图和必要需求给出三个大纲方向，等待用户确认方向或大纲；不得在用户确认方向或大纲前请求上传确认、上传、登记或调用脚本/方案工具。用户确认方向或大纲后，若脚本或方案工具需要远端素材引用，必须再向用户确认上传素材用于生成脚本或方案；上传素材用于生成脚本不等于确认开始生成视频，不得跳过脚本或方案确认、积分预估和最终生成确认。用户确认上传素材后，才上传并登记本地素材；不得在用户确认上传素材前上传、登记或处理本地素材，不得把上传登记作为用户可见的独立步骤。生成脚本或方案前，必须先准备并记录所有服务端需要的参考素材引用。用户确认完整脚本或方案后的积分预估阶段不得再次上传、登记或处理本地素材。内部执行时，先调用远程工具 `get_reference_image_upload_token`，必须通过工具结果原文或临时文件原样传给上传脚本标准输入，执行 `python3 scripts/picset_video_client.py upload --file <本地图片路径>`；不得把上传 token 写入 shell heredoc，不得手工改写、摘抄或重组 token JSON。脚本返回 `oss_path` 后再调用远程工具 `register_reference_image` 登记素材引用，并把登记后的素材引用写入后续服务端参数。

WorkBuddy 复刻流程中的本地目标视频也使用同一个公共上传脚本，并且只在用户确认复刻方案方向或大纲、再确认上传素材用于生成方案后上传登记：先调用远程工具 `get_reference_image_upload_token`，执行 `python3 scripts/picset_video_client.py upload --file <本地目标视频路径>`，脚本返回 `oss_path` 后调用远程工具 `register_reference_image` 登记为目标视频素材，并把登记后的引用写入 `video_refs`。用户未确认完整脚本或方案时不得调用 `estimate_video_generation`；用户未确认预计积分时，不得调用 `generate_video`。如果用户提供的是本地路径，不得把本地文件路径填入服务端 refs 字段。

调用 `estimate_video_generation` 和 `generate_video` 时，`duration_sec` 必须是 JSON 数字，例如 `"duration_sec": 4`，不得传字符串 `"duration_sec": "4"`。`product_image_refs` 必须是字符串数组，不得传对象 `"product_image_refs": { "item": "https://..." }`，也不得传字符串 `"product_image_refs": "https://..."`。

硬性停止条件：未收集到至少 1 张商品参考图或本地商品图意图时，不得预估或生成；用户确认具体积分后上传或登记失败时，不得继续调用 `generate_video`。脚本生成、复刻分析或预估失败时，不得继续调用后续步骤。用户修改脚本、方案、素材、时长、比例、数量或参考图后，必须重新 estimate 并重新请求明确确认。正式生成时生成稳定的 UUID 作为 `request_id`，同一次重试复用同一个 `request_id`。

状态恢复：`generate_video` 返回 `task_id` 后必须保存；如果流程中断或轮询超时，保留 `task_id` 并说明之后可继续查询，恢复后使用已有 `task_id` 调用状态查询，不得重复生成。
