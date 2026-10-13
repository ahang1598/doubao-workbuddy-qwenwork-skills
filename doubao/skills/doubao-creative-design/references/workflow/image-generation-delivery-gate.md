# 交付门禁

**HTML 预览截图例外**：`shot.py` 为完整 HTML 作品生成的专用预览截图不适用下文媒体双通道。按 [HTML 预览协议](html-preview.md) 上传 CDN、核验公网 HTTP(S) 链接并用 Markdown 图片展示；截图不调用 `present_files`，不创建 IMAGE Item，不写入画布或资产目录。其他生成／编辑图片、视频和另行导出媒体仍按本门禁执行；不得把普通媒体改称 HTML 预览来绕过交付。

本文件只适用于 system 上下文不包含 `Device platfrom: Mobile` 的默认 Canvas 交付环境。若包含该标记，禁止执行本文件的 Workspace 与双通道步骤，改读 [`mobile-app-direct-delivery.md`](mobile-app-direct-delivery.md)。

本门禁适用于本 Skill 产生并通过 `present_files` 交付的所有图片和视频产物，包括生成／编辑工具输出、核心资产、KV、候选、草稿、改稿、中间素材、分批结果、Canvas 渲染图、导出图和最终成品。每个结果都必须同步执行 Canvas 持久化与用户交付两个分支，并在汇合点核对两边结果；串行或并行只决定多个生成任务之间是否并发，不改变双通道同步规则。

图片／视频生成或编辑工具返回成功结果时，保留两类原始数据：供 Workspace 使用的 `source_asset_url`，以及供 `present_files` 直接接收的 `generated_artifact`。Workspace `<asset url>` 逐字使用工具原始短链；`present_files` 直接接收工具返回的对应产物。禁止为交付另行下载、复制或重新上传产物，也禁止把工具预览、Markdown 链接或普通文本 URL 当作已经完成 `present_files`。只有从未经过图片／视频生成或编辑工具、且产出工具确实只返回本地文件的渲染／导出结果，才可先通过 `FileBatchUpload` 取得 Workspace 短链；`present_files` 仍直接接收该产出工具返回的文件。

## 0. 对话级 Workspace 前置门禁

在调用任何图片／视频生成或编辑工具前先读取当前对话上下文：

- 当前对话包含唯一有效且明确作为当前目标的 `canvas_workspace_id`：绑定为 `active_workspace_id`，所有产物写入该 Workspace；不得重复创建。
- 当前对话不包含 Workspace ID：直接执行 `design-cli design-workspace +workspace-create --title "<title>"`，从响应读取 ID，绑定为 `active_workspace_id`，再由主 Agent 调用 `present_files(<workspace_id>)`；输入值只能是该原始 ID，由此次调用交付新建画布卡片。不得先调用 `+get-workspace`，不得创建 `workspace-id.txt` 或其他中间文件，也不得加入字段名、标题、版本、XML、JSON 或说明。画布卡片交付阶段只能产生该次 `present_files` 用户可见输出，禁止同时或随后输出聊天文字、Markdown、路径、CLI stdout、日志或总结。创建或画布卡片交付失败时禁止调用生成／编辑工具。
- 当前对话出现多个 Workspace ID 且没有明确当前目标：停止并向用户确认，不得凭创建时间、出现次数或猜测选择。

`+get-workspace` 只用于显式查询、恢复或排障，不得在当前对话缺少 ID 时替代强制 `+workspace-create`。已有对话 ID 不需要重新交付画布卡片；只有本轮新创建的 Workspace 执行 `present_files(<workspace_id>)` 卡片交付门禁。不得把 ID 同时复制到普通回复、文件或其他交付通道。

## 1. 执行模式与最高优先级不变量

取得 `active_workspace_id` 后记录 `execution_mode=serial | parallel`。默认使用串行；只有多个任务已经预先锁定、相互独立、彼此输出不作为下一项输入时，才使用并行。不得在执行中途为了抢时间，把存在依赖的串行步骤临时改成并行。

**画布持久化是硬门禁**：默认 Canvas 环境中，图像／视频生成或编辑工具成功返回的每个结果，都必须使用原始短链通过 `design-cli` 创建独立画布对象并 `+get` 回读。它与 `present_files` 是同一结果的两个必需出口，二者互不替代；只完成用户交付、只嵌入 HTML、只创建最终 HTML Item，或计划整批结束后集中补写，都不算完成。缺少写入 ID、回读结果或原始短链一致性时，立即停止下一批及 HTML 组装。

- **每个结果的同步双分支**：结果可用后，在同一调度阶段启动 `persistence` 与 `delivery`。`persistence` 使用原始短链执行 `design-cli design-workspace +create` 和 `+get`；`delivery` 直接执行 `present_files(generated_artifact)`。不得等待任一分支结束后才启动另一分支。
- **串行生成**：一次只生成一个结果；该结果的两个分支都汇合后，才允许修复、选图、生成或编辑下一张。
- **并行生成**：只允许并发预先锁定且互不依赖的固定批次；每个结果各自建立同步双分支，整批在 join barrier 等待全部分支，不得边执行边追加新任务。并行生成 N 个同源编辑版本时，必须发起 N 次独立 `image_edit`，不得用一次多结果调用代替。单参考变体每次只传入同一张已确认参考图；当前合成成品需独立身份母版的复合编辑，每次固定传入同一当前成品作为编辑目标、同一已确认母版作为身份参考，不用母版替代成品。所有版本属于同一预先锁定批次，输入版本、顺序与授权职责固定，不混入无关参考，也不把某个并行结果作为另一项输入；实际工具不能同时接受必要参考时，说明限制并停止依赖该能力的编辑。

### HTML 正式生产门禁

主视觉确认后进入 HTML 正式生产时，全部图片／视频工具结果仍受本门禁约束，不因被标记为“HTML 素材”“中间素材”“候选”或“未采用版本”而豁免。每个结果返回后立即同步启动 `design-cli +create`／`+get` 与 `present_files(generated_artifact)`；画布分支必须取得真实对象 ID 并完成回读，不能用排队状态、待补写记录、HTML 内 URL 或最终 HTML Item 代替。串行结果先汇合再生成下一项，并行固定批次等全部结果完成各自双通道闭环后再开始下一批。只有本轮正式生产已返回的全部媒体结果均闭环、素材清单已回填且不存在待处理分支时，才允许进入 HTML 组装；禁止先组装再集中补写媒体。
- **单项交付**：一次 `present_files` 只能包含 1 张图片；一次工具调用返回多张时，也必须按稳定返回顺序为每张建立独立交付调用和持久化分支。

交付和持久化队列汇合前，禁止让用户选图、确认方向，或继续抠图、扩图、合成、排版、视觉澄清、核心资产延展、HTML 组装和结果汇总。

图片工具返回成功且提供可用结果，即视为“成功产出”。即使该图审美不佳、错字、身份漂移、比例错误或预计需要返工，也必须先同步执行双通道并等待汇合。不得静默丢弃、隐藏或先生成修正版再补交原结果。

### AI 图片生成文字：交付后等待用户

AI 图片内出现错字、缺字、多字、伪文字、字形异常或可读性不佳时，完成双通道汇合后只记录实际问题并将该版本标记为 `delivered_with_text_issue`。禁止因这些文字问题继续长篇反思、反复改 Prompt、自主 `image_edit`、自动重生或先做修正版；必须停止相关修改，等待用户明确提出修改要求后再启动一次新的编辑。若它是可编辑设计的中间艺术标题或其他必须准确的文字资产，则不得进入 HTML 组装。保持已交付状态并暂停依赖步骤。用户提出修改后，新版本继续执行同一双通道门禁。此规则不降低 Coding/DOM/TEXT 原生文字的准确性要求，也不阻止修复与文字无关的身份、结构、比例、分辨率或协议错误。

## 2. 每个结果的同步时序

```text
生成／编辑工具成功返回 result[i]
→ 同一调度阶段同步启动：
   ├─ persistence[i]：source_asset_url + 已核验 source_ids（如有）→ design-cli design-workspace +create --canvas-workspace-id active_workspace_id → +get
   └─ delivery[i]：generated_artifact → present_files（仅该产物）
→ join barrier：等待 persistence[i] 与 delivery[i]
→ 检查并记录通过／未通过
→ 才可启动依赖该结果的后续步骤
```

同步执行指两个分支在结果可用后的同一调度阶段启动，并由同一个 join barrier 等待；不要求毫秒级同时结束。禁止把某一分支延后到另一分支完成之后，或等整批同类操作全部完成后再启动另一类操作。

`persistence` 分支遵守以下规则：

1. 从生成／编辑工具原始响应读取 `source_asset_url`；它必须是 CLI 可用的持久短链。
2. 所有命令显式使用当前 `active_workspace_id`。每个生成或编辑结果都是新的内容版本，使用 `+create` 写入且不携带旧 ID；`+update` 只用于顶层对象的 `brief`／`path`，不得用它替换 IMAGE／VIDEO 内容或资产 URL。
3. XML `<asset url>` 必须与 `source_asset_url` 逐字一致。禁止写入本地路径、`file://`、`data:`、预览地址或另行上传产生的新短链。
4. 写入稳定 path 与 brief。普通资产归入对应 Semantic Cluster；最终渲染图或导出图归入 `/deliverables/<任务语义>/exports`，brief 记录用途、版本以及可得的来源 Frame／Item ID。若结果来自画布既有 Item／Frame 的编辑、参考或衍生，在 `<source_ids>` 中填写通过 `+get` 确认的来源 ID；无来源则省略标签。不同结果需要分别贴近不同来源时不得塞入同一个 `+create-batch`。
5. 保存写命令返回 ID，并立即用 `+get` 回读资产 URL、path、brief、类型与 transform；回读 URL 仍须与 `source_asset_url` 逐字一致。

`delivery` 分支直接把工具返回的对应 `generated_artifact` 交给 `present_files`。不得先下载成本地文件，不得用短链、预览、缩略图、Markdown 图片、聊天内联图或普通文本路径替代 `present_files` 调用。

## 3. 汇合、失败与坏图处理

join barrier 后按每个结果分别处理：

- 两个分支都成功：记录 `canvas_persistence_status=persisted` 与 `delivery_status=delivered`，该结果闭环完成。
- CLI／回读失败但交付成功：记录“用户已收到但画布持久化失败”，不得伪造 Canvas ID；停止新的生成、编辑、选图和所有依赖步骤。
- CLI／回读成功但交付失败：保留已写入的 Canvas Item，记录“已持久化但用户未收到”；停止后续依赖步骤。
- 两个分支都失败：分别保留两侧诊断信息，不盲目重放整批。
- 一个分支失败时，不取消已经运行的同级分支；等待其真实结果后再汇合。已经启动的其他结果可以完成，但汇合后不得进入选图、修复或下一批。

效果不佳或必然需要修复的结果也不得在汇合前筛掉。双通道完成后记录 `validation_status=failed` 与失败原因；非文字问题可按对应 workflow 生成修正版，修正版继续执行同一门禁。若失败仅来自 AI 图片内生成文字，改记 `validation_status=delivered_with_text_issue` 并等待用户提出修改要求，禁止自动生成修正版。

## 4. 成功判据与记录

只有 `present_files` 对单项产物返回成功，才将其记为 `delivery_status=delivered`。工具自己的预览、缩略图、CDN URL、Markdown 图片、聊天内联图或普通文本路径都不算交付。

每个生成结果至少记录：

- `execution_mode`；并行时额外记录 `batch_id`、预先锁定的任务集合、预期数量与稳定顺序；
- `generation_result_index` 与生成／编辑调用标识；
- 工具原始 `source_asset_url` 与 `generated_artifact` 标识；
- 本结果使用的 `active_workspace_id` 及其来源 `conversation_context | workspace_create`；
- Canvas 写入返回 ID、实际写入 URL、`+get` 回读结果；
- 独立 `present_files` 调用结果，以及与持久化分支共同的 `sync_group_id` 和 join barrier 结果；
- `validation_status=passed | failed | delivered_with_text_issue`；失败时保留两侧证据并关联后续修复版本，AI 图片生成文字问题则记录可见问题并等待用户要求；
- 若失败，失败发生在生成、短链取得、交付、写入还是回读阶段。

后续选图、确认、衍生、排版和最终交付只能引用 `delivery_status=delivered`、`canvas_persistence_status=persisted` 且已记录 Canvas Item ID 与 `+get` 回读结果的产物。
