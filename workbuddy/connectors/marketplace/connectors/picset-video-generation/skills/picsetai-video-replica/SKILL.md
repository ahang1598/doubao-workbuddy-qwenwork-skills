---
name: picsetai-video-replica
displayName: Picset AI 爆款视频复刻
name_en: picsetai-video-replica
description: >
  用于 Picset AI 电商爆款视频复刻与相似视频改编。适用于用户上传目标视频、爆款视频、竞品视频或参考视频，并希望用自己的商品图、可选模特图或场景图生成相似带货视频、电商短视频、种草视频、广告视频、产品展示视频或口播视频的场景。该 Skill 会收集商品图和目标视频，处理视频复刻需求，分析目标视频并生成复刻脚本或方案，在用户确认后进行视频生成。
description_en: >
  Handle Picset AI ecommerce target-video recreation and similar video adaptation requests.
argument-hint: 商品图片、目标视频、复刻要求、时长和比例
---

# Picset AI 视频复刻

本子 Skill 负责目标视频参考复刻流程。执行时必须使用共享协议：

- `../shared/handoff-protocol.md`
- `../shared/credit-confirmation-protocol.md`

从主 Skill 接收上下文后，只处理复刻相关步骤，并将结果写回共享上下文。

## 输入规则

- 商品图必填。缺少商品图时，只询问并引导用户提供商品图，不追问其他复刻信息。
- 目标视频必填。目标视频是用户提供的参考视频、爆款视频或竞品视频，用于服务端复刻分析，不是由本地 Agent 解析的视频脚本。
- 若用户提供本地商品图、目标视频路径或本地附件，先基于已收集素材意图和必要需求给出三个复刻方案方向，等待用户确认方向或大纲；用户确认方向或大纲后，若方案工具需要远端素材引用，必须再向用户确认上传素材用于生成方案。用户确认上传后进入生成方案前素材准备，上传、登记并记录所有服务端需要的参考素材引用。不得在用户确认方向或大纲前请求上传确认；不得在用户确认上传素材前上传、登记或处理本地素材。后端已支持目标视频 refs；目标视频登记后写入 `VideoHandoffContext.assets`，使用 `target_video` asset role，并作为 `video_refs` 传给后续请求。不得把目标视频内容改写成本地 prompt。
- 上传素材用于生成方案不等于确认开始生成视频，不得跳过方案确认、积分预估和最终生成确认。
- `project_id` 只内部保存和透传，不展示给用户；`create_replica_script` 未传 `project_id` 时由服务端自动创建或恢复真实 `project_id` 并返回，收到后必须保存；未返回时保存 `replica_script_id`。预估或生成前必须具备后端返回的有效 `project_id` 或可让后端恢复项目归属的 `replica_script_id`。没有后端返回的 `project_id` 时，使用 `script_id` 或 `replica_script_id` 让后端恢复项目归属。不得传空字符串作为 `project_id`，不得臆造项目归属、不得用脚本任务 ID 冒充 `project_id`、不得用历史项目标识试探。不得围绕 `project_id` 要求用户提供、修正或查找。
- 不得使用 OSS SDK，不得使用 oss2，不得引入第三方上传依赖。
- 不得本地分析目标视频镜头，不得本地推断目标视频比例，不得本地推断目标视频时长。禁止行为标记：agent_analyzes_shots、agent_inferrs_ratio、agent_inferrs_duration。
- 只处理商品图 + 目标视频复刻，不得执行场景图生成，不得宣称场景图生成。
- 目标视频可能出现人物或模特，但目标视频不得强制触发模特图生成；只有用户明确提出固定模特请求时，才进入模特图生成流程。

## 复刻方案

需求和本地素材意图齐备后，先给用户三个复刻方案方向。三个复刻方案方向只是创意方向摘要，不是完整复刻方案，不是最终 prompt，也不是逐镜头分镜。此阶段不得请求上传确认、不得上传、不得登记、不得调用 `create_replica_script`。用户选择方向后，方案工具需要远端素材引用时，必须先向用户确认上传素材用于生成方案；用户确认后，调用 `get_reference_image_upload_token`、公共上传脚本和 `register_reference_image` 准备商品图与目标视频引用并记录到 `VideoHandoffContext.assets`，再调用服务端复刻分析或 `create_replica_script`，让服务端基于用户需求、商品图说明和目标视频说明产出完整复刻方案或完整复刻脚本。若返回 `replica_script_id` 且 `status` 不是 `success`，即使同时出现 `script_or_plan` 也不得当作完整方案，必须保存 `replica_script_id` 并调用状态查询工具直到取得 `status=success` 且完整 `script_or_plan` 后再展示给用户确认。服务端复刻分析结果记为 server_replica_plan。

服务端复刻分析先于方案确认：用户确认服务端返回的复刻方案前，不得预估积分，不得生成视频。

完整复刻方案必须展示给用户先于方案确认，不能只展示摘要后直接进入 plan_confirmation；若服务端返回完整复刻脚本，也必须展示给用户先于方案确认。

## 生成顺序

内部执行顺序为：先给用户三个复刻方案方向 -> 用户确认方向或大纲 -> 用户确认上传素材用于生成方案 -> 生成方案前素材准备 -> 服务端复刻分析 -> 必要时查询完整方案 -> 用户确认方案 -> 预估积分 -> 用户确认开始生成视频 -> 提交最终生成 -> 查询生成进度。

可执行接口顺序为：先给用户三个复刻方案方向 -> 用户确认方向或大纲 -> 用户确认上传素材用于生成方案 -> 生成方案前素材准备 -> 服务端复刻分析或 `create_replica_script` -> 必要时状态查询取回完整 `script_or_plan` -> 方案确认 -> `estimate_video_generation` -> 用户确认开始生成视频 -> `generate_video` -> `poll_video_status`。

方案确认先于 `estimate_video_generation`：用户确认复刻方案前，不得预估积分。

`estimate_video_generation` 返回具体积分后，必须用 `estimated_credits` 向用户确认具体积分消耗；确认具体积分先于 `generate_video`，用户确认预计消耗积分前，不得生成视频。

积分确认先于 `generate_video`：用户确认预计消耗积分前，不得生成视频。

生成方案前素材准备只允许发生在用户明确确认上传素材用于生成方案后、`create_replica_script` 前：此时才按服务端给出的直传地址上传商品图和目标视频等所有本地素材，通过 HTTP PUT 写入 OSS，再调用 `register_reference_image` 登记素材引用；目标视频登记后写入 `video_refs`。用户确认完整方案后的积分预估阶段不得再次上传、登记或处理本地素材。

如果 `create_replica_script`、`estimate_video_generation` 或其他工具 schema 看起来需要远端素材引用，仍不得绕过对应确认门；不得用空字符串、占位项目、历史项目、臆造项目标识或脚本任务 ID 试探 `project_id`。缺少服务端返回的有效项目归属且缺少可用于恢复项目归属的 `replica_script_id`，或缺少可在当前阶段合法使用的素材引用时，停止后续工具调用，只向用户说明暂时无法继续处理。

调用 `generate_video` 时必须包含 `video_refs` 和 `target_video` 信息，并包含已确认的复刻方案、商品图、时长、比例和数量。

用户明确确认预计积分后，才调用 `generate_video` 执行最终生成；用户确认预计积分前不得调用 `generate_video`。`generate_video` 先于 `poll_video_status`，必须保存返回的 task_id 到 VideoHandoffContext。若流程中断、恢复、继续或重试，恢复 task_id 后继续调用 `poll_video_status`，不得重新生成。每次轮询 poll 状态都要保存或更新到 VideoHandoffContext，并只向用户展示可理解的生成状态和结果。

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
