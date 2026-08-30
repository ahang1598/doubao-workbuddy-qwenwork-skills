---
name: picsetai-video-generate
displayName: Picset AI 商品带货视频生成
name_en: picsetai-video-generate
description: >
  用于 Picset AI 电商商品视频生成。适用于用户提供商品图，并希望生成商品带货视频、种草视频、口播视频、产品演示视频、开箱视频、痛点解决视频、品牌广告视频或其他电商短视频的场景。支持 UGC 种草、产品口播、带货短剧、产品演示、开箱种草、痛点解决、TVC 品牌广告等类型。该 Skill 会根据用户提出的视频要求，智能规划并提供多个脚本大纲方向，供用户选择，用户确认后交由服务端生成完整脚本并生成最终视频。
description_en: >
  Handle Picset AI ecommerce product video generation requests from product images and user creation requirements.
argument-hint: 商品图片、卖点、视频时长、比例、语言、国家和可选视频类型
---

# Picset AI 商品视频生成

本子 Skill 负责商品视频生成流程。执行时必须使用共享协议：

- `../shared/handoff-protocol.md`
- `../shared/credit-confirmation-protocol.md`

从主 Skill 接收上下文后，只处理商品视频生成相关步骤，并将结果写回共享上下文。

## 输入规则

- 商品图必填。缺少商品图时，只询问并引导用户提供商品图，不追问其他生成信息。
- 若用户提供本地商品图路径或本地附件，先基于已收集素材意图和必要需求给出三个大纲方向，等待用户确认方向或大纲；用户确认方向或大纲后，若脚本工具需要远端素材引用，必须再向用户确认上传素材用于生成脚本。用户确认上传后进入生成脚本前素材准备，上传、登记并记录所有服务端需要的参考素材引用。不得在用户确认方向或大纲前请求上传确认；不得在用户确认上传素材前上传、登记或处理本地素材。不得使用 OSS SDK，不得使用 oss2，不得引入第三方上传依赖。
- 上传素材用于生成脚本不等于确认开始生成视频，不得跳过脚本确认、积分预估和最终生成确认。
- `project_id` 只内部保存和透传，不展示给用户；`create_video_script` 未传 `project_id` 时由服务端自动创建或恢复真实 `project_id` 并返回，收到后必须保存；未返回时保存 `script_id`。预估或生成前必须具备后端返回的有效 `project_id` 或可让后端恢复项目归属的 `script_id`。没有后端返回的 `project_id` 时，使用 `script_id` 或 `replica_script_id` 让后端恢复项目归属。不得传空字符串作为 `project_id`，不得臆造项目归属、不得用脚本任务 ID 冒充 `project_id`、不得用历史项目标识试探。不得围绕 `project_id` 要求用户提供、修正或查找。
- `video_type` 可选。未提供 `video_type` 时，不得阻塞流程，不自动默认 `video_type`。
- `duration_sec` 必须是 4-15 整数秒；3、16、10.5 均为无效值，需要请用户改为 4 到 15 之间的整数秒。
- 只处理商品视频生成，不得执行场景图生成，不得宣称场景图生成。

## 大纲方向

在本地素材意图和必要需求齐备后，先给用户三个大纲方向。三个大纲方向只是创意方向摘要，不是完整脚本，不是最终 prompt，也不是逐镜头分镜。此阶段不得请求上传确认、不得上传、不得登记、不得调用 `create_video_script`。

用户选择方向后，脚本工具需要远端素材引用时，必须先向用户确认上传素材用于生成脚本；用户确认后，调用 `get_reference_image_upload_token`、公共上传脚本和 `register_reference_image` 准备商品图引用并记录到 `VideoHandoffContext.assets`，再调用 `create_video_script` 让服务端生成完整脚本。若返回 `script_id` 且 `status` 不是 `success`，即使同时出现 `script_or_plan` 也不得当作完整脚本，必须保存 `script_id` 并调用状态查询工具直到取得 `status=success` 且完整 `script_or_plan` 后再展示给用户确认。完整脚本必须由服务端生成，不得把大纲方向、处理中占位文本、最终 prompt 或逐镜头分镜当作完整脚本。

## 生成顺序

内部执行顺序为：先给用户三个大纲方向 -> 用户确认方向或大纲 -> 用户确认上传素材用于生成脚本 -> 生成脚本前素材准备 -> 生成脚本 -> 必要时查询完整脚本 -> 用户确认脚本 -> 预估积分 -> 用户确认开始生成视频 -> 提交最终生成 -> 查询生成进度。

脚本确认先于 `estimate_video_generation`：用户确认服务端生成的完整脚本前，不得预估积分。

`estimate_video_generation` 返回具体积分后，必须用 `estimated_credits` 向用户确认具体积分消耗；确认具体积分先于 `generate_video`，用户确认预计消耗积分前，不得生成视频。

积分确认先于 `generate_video`：用户确认预计消耗积分前，不得生成视频。

生成脚本前素材准备只允许发生在用户明确确认上传素材用于生成脚本后、`create_video_script` 前：此时才按服务端给出的直传地址上传商品图等所有本地素材，通过 HTTP PUT 写入 OSS，再调用 `register_reference_image` 登记素材引用并写入 `VideoHandoffContext.assets`。用户确认完整脚本后的积分预估阶段不得再次上传、登记或处理本地素材。

如果 `create_video_script`、`estimate_video_generation` 或其他工具 schema 看起来需要远端素材引用，仍不得绕过对应确认门；不得用空字符串、占位项目、历史项目、臆造项目标识或脚本任务 ID 试探 `project_id`。缺少服务端返回的有效项目归属且缺少可用于恢复项目归属的 `script_id`，或缺少可在当前阶段合法使用的素材引用时，停止后续工具调用，只向用户说明暂时无法继续处理。

用户明确确认预计积分后，才调用 `generate_video` 执行最终生成；用户确认预计积分前不得调用 `generate_video`。`generate_video` 先于 `poll_video_status`，必须保存返回的 `task_id` 到 `VideoHandoffContext.service_state.generation_task_ids`。如果流程中断或需要重试，恢复 task_id 后继续调用 `poll_video_status`，不得重新生成。每次轮询 poll 状态都要保存或更新到 `VideoHandoffContext.results`，并只向用户展示可理解的生成状态和结果。

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
