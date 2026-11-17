# 创建／大改后的交付验证

本文件检查交付文件、格式能力和当前环境的交付状态；源码遵循 [HTML 协议](../html/coding-rendering.md)，画面检查按 [HTML 检查](html-validation.md)，脚本调用与失败处理按 [预览流程](html-preview.md)。


核对当前 Brief、适用素材清单、完整源和实际交付文件，保持已确定的路线与目标。

通知／公告／喜报／捷报／成果战报／邀请函／节庆贺图已有合适底图且无需新图时，按主 SKILL 的复用例外核验真实来源、质量与最终可见消费者，不强制新生成／编辑记录；其余新建 AI Coding 仍核对必要的图像生产。

## 交付文件与用途

在同一 Brief 中确定交付类别及文件范围，完成后逐项核对。下表规定交什么，现有 Canvas／Mobile 和媒体出口规定怎么交。

| 交付类别 | 文件要求 |
| --- | --- |
| 单图／多尺寸图 | 每个用途、尺寸独立适配并交付，不直接拉伸替代适配。 |
| 有序套图／多页 | 按阅读顺序编号、逐页交付；合并文档按品类与约定格式提供。 |
| 商品详情页／电商长图／A+ | 一个完整长图 HTML Item 及同尺寸完整预览；用户另需整图、分屏或切片时交付同源渲染结果。 |
| 其他长图／切片（营销／信息长图） | 完整长图与顺序切片来自同一最终版本；按发布端限制与内容边界切分，等宽、无漏段或重复，避开文字、商品主体及完整信息组。 |
| 正反面／折叠面 | 每面独立制作和交付，标明面序与方向。HTML 路线每面使用独立 HTML 画布并提供同尺寸预览图；Canvas 环境逐面创建 HTML Item。折叠类每个完整展开面为一份，并明确展开尺寸和折法。 |
| 独立素材包 | 素材及所需变体分别导出，保证可独立使用；透明素材检查真实透明通道与边缘。 |
| 异形／生产展开稿 | 按约定提供效果图或平面展开稿；生产稿依据真实结构、尺寸和工艺资料制作。 |

- **文件完整**：核对数量、尺寸、格式、顺序和最终版本。多文件按“序号＋用途／面别＋尺寸”命名。
- **印刷用途**：确认毫米尺寸、出血、安全区、色彩和生产方要求，再导出生产 PDF／指定格式；资料或验证不足时标明“设计示意／待生产确认”。
- **二次使用**：说明实际可编辑范围。透明 PNG 须有真实 Alpha；称为矢量的文件须有可编辑路径；HTML 中的图片文字仍属于位图。
- **能力预检**：生产前确认约定格式的导出、合并和交付能力；缺失时说明限制并确认替代方案。约定文件须实际生成、打开检查后交付，不以改扩展名代替转换。

验收同时检查交付文件本身与展示效果；缺件或未验证部分如实说明。本文的媒体直交、HTML 预览和画布出口保持不变，交互网站／H5 按自身运行与交付要求处理。

## 1. 环境与产物分流

- system 上下文明确标记为移动端交付时读取 [Mobile 直接交付](mobile-app-direct-delivery.md)：跳过本文所有 Workspace、Canvas CLI、Item、画布卡片和 HTML 上传要求；媒体逐项 RichMediaCard，HTML 预览上传 CDN 后以 Markdown 图片展示。只支持静态出口，交互需求须在冻结前按该文档处理。
- 纯图／视频：读取同一 Brief、真实工具结果、准确事实与身份来源，核对内容、尺寸、质量、身份、功能内容及媒体门禁，随后检查当前环境的交付状态；不要求 HTML、DOM、字体契约或 shot.py。纯图编辑核对目标范围与未授权变化。成功但有缺陷的结果仍先交付，是否可继续组装另行判定。
- HTML：读取当前完整源、同版本素材、唯一 Brief 与用户验收要求，执行第 2、3 节和当前环境的交付检查。普通文字保持可编辑；品类明确准入的图内文案按已确认边界验收。禁止因没有模板 ID、CSS ID、坐标或参数而将自然语言 Brief 判失败。
- 只有图片且要求重建 HTML 的任务使用对应创建流程；真实已有 HTML 才使用源编辑流程。验收依据实际输入与授权范围，不假造源结构。

## 2. HTML 源码与编辑边界

按 [HTML 协议](../html/coding-rendering.md) 核对完整文档、画布声明、根节点固定行内尺寸、样式、真实资源和页尾安全区。尺寸随视口或脚本改变记 `HTML_CANVAS_SIZE_NOT_FIXED`；根画布裁切正文记 `HTML_ROOT_OVERFLOW_CLIPPED`；缺少或无效收尾区记 `HTML_BOTTOM_SAFE_AREA_MISSING`。上述源码问题阻断写入，测量副本的临时高度调整不属于正式源变更。

核对完整 `<!DOCTYPE html>`、head、UTF-8、body 与闭合文档。一个连续作品只对应一个 HTML；独立作品分别交付。实际 URL、准确 DOM 文字、层级和替换关系完整。纯 Coding 不套用 AI 素材生产门禁；AI Coding 核对原素材清单与实际图片消费者，仅展示后弃用、未登记准出或未绑定正式消费者的 KV，以及隐藏装饰，不能充当正式素材完成证据；已按品类规则登记准出并实际用于正式 Hero 的 KV 可以计入。

编辑后保留未授权 DOM、文案、素材、画布尺寸和关系；用 DOM id／data-layer-id、真实资产 URI 与语义唯一定位目标。选区不能唯一对应时先确认；透明叠加图片仍须有真实 Alpha、深浅底边缘与孔洞检查。独立艺术字不按新建／编辑分流：消费者仅为已知稳定 HTML 背景时可选择纯色底混合，需要透明导出、跨背景复用、背景未知或严格保色时选择抠图。混合路线中深色字体未使用纯白底＋目标节点 `mix-blend-mode: multiply`，浅色字体未使用纯黑底＋目标节点 `mix-blend-mode: screen`，或混合模式误设在父容器／整页时，以 `ART_TITLE_BLEND_MODE_INVALID` 阻断；抠图路线缺少真实 Alpha、内部孔洞或深浅底边缘检查时，以 `ART_TITLE_ALPHA_INVALID` 阻断。任一路线的最终媒体须完成第 4 节的直接交付。HTML 内容变化时重新上传并创建新 HTML Item；图像工具结果直接交付后归档，`+update` 仅维护目录元数据。

## 3. 真实预览与视觉目标

按 [HTML 检查](html-validation.md) 核对同版本源、素材、技术报告与实际画面，确认可编辑范围、内容完整性和视觉目标；预览失败按 [预览流程](html-preview.md#交付与失败) 处理。问题版本不得作为合格成品。

合格预览未上传或链接不可访问时记录 `HTML_PREVIEW_CDN_UNAVAILABLE`；未用上传结果作 Markdown 图片展示时记录 `HTML_PREVIEW_MARKDOWN_MISSING`。两者均影响最终完成，平台写入与媒体展示另按第 4 节核对。

## 4. 默认 Canvas 写入与媒体交付

以下 Canvas 动作仅用于默认环境。Mobile 的媒体改按本地真实资产记录与逐项直接交付验收；其中成功结果不可隐藏、图内错字等待授权和失败停止依赖步骤的原则仍适用。

1. **Workspace 绑定**：先确认生产前已从当前对话绑定唯一 `active_workspace_id`；对话无 ID 时，必须存在本轮 `+workspace-create` 响应，以及主 Agent 将响应中的原始 ID（`workspace_id`）原样作为 `present_files` 单值输入并成功交付 Workspace 画布卡片的记录，否则以 `WORKSPACE_CARD_NOT_PRESENTED` 阻断。该卡片成功前不得开始生产。不得在无 ID 时先调用 `+get-workspace`，不得为 ID 创建中间文件、添加包装、改用数组或拆分调用；自创建响应返回至卡片成功交付，只允许主 Agent 执行上述单值调用，不得混入其他用户可见文字、链接、路径、日志、CLI 输出、总结、其他产物或重复 ID 交付，否则以 `WORKSPACE_CARD_DELIVERY_NOT_EXCLUSIVE` 阻断。初始化卡片只使用原始 Workspace ID，不与后续 HTML Item 卡片的拼接值混用。默认 Canvas 的每次 `image_gen`／`image_edit` 调用须显式透传该 Workspace ID，记录实际调用参数。

2. **媒体直接交付**：按 [交付门禁](image-generation-delivery-gate.md) 核对每个成功结果以 `<RichMediaCard>{"refs":["真实资源引用"]}</RichMediaCard>` 逐项展示；图片每张一张卡，使用工具返回的原始引用。仅存在于本地的正式渲染／导出文件先经 `FileBatchUpload` 取得引用；已有工具引用直接使用。缺少展示、引用不对应或以 Markdown／普通链接代替媒体卡片时，以 `TOOL_ARTIFACT_NOT_PRESENTED_DIRECTLY` 阻断依赖步骤。候选、未采用及质量不佳的成功结果同样交付；静默隐藏以 `IMAGE_RESULT_HIDDEN_BEFORE_REPAIR` 阻断。工具失败时记录实际错误，不伪造媒体卡片。交付失败时保留真实结果，仅修复交付，不重新生成。

   图内文字有问题时标记 `delivered_with_text_issue` 并等待用户修改授权；承担准确文字的素材暂停下游组装。串行任务在当前结果交付后继续；并行任务在固定独立批次全部交付后汇合。未交付成功即继续依赖步骤，以 `MEDIA_DELIVERY_FAILURE_IGNORED` 阻断。

3. **产后目录整理**：按 [画布资产语义目录](canvas-asset-organization.md) 在本轮媒体直接交付完成后，或 HTML Item 创建并首次回读后，执行 `+tree／+ls → +get → +update`，只更新本轮对象的 `path`，再回读确认内容、来源和布局未变。图像工具结果使用平台已关联对象，不另行 `+create`；对象映射不明时记录真实缺口，不猜测 ID 或重复创建。归档回读不作为媒体交付或 HTML 组装前提；HTML 的产后整理须在最终 Item 卡片展示前完成。用户上传锚点及其他手工创建对象仍按各自 CLI 协议创建并回读。

   **HTML Item 校验**：上述媒体门禁既不适用于原始 `.html`，也不适用于 `shot.py` 产出的 HTML 预览截图。可编辑设计的 `.html` 调用 `shot.py`，把像素宽高严格等于声明画布且内容完整的预览图用 `FileBatchUpload` 上传 CDN；核验返回的公网可访问 HTTP(S) 链接后，以该链接用标准 Markdown 图片语法展示。截图不得调用 `present_files`、创建 IMAGE Item 或写入画布。再另行经 `FileBatchUpload` 上传 HTML，以 HTML 文件短链创建并回读顶层 HTML Item；不得混用预览图 URL 与 HTML 源 URL。预览失败或不完整不阻断 HTML 上传和写入，但合格预览图尚未完成 CDN 上传及 Markdown 展示时不得完成。HTML Item 回读成功并完成产后目录整理后，必须把同一 `active_workspace_id` 与该回读对象的 `item_id` 拼成 `<active_workspace_id>?item_id=<item_id>` 单值并原样传给 `present_files` 输出对应画布卡片；拆成两个参数、数组或两次调用，只传 Workspace ID，缺少任一 ID、两者不属于同一回读对象，或误用旧版本 Item ID，均以 `HTML_WORKSPACE_CARD_NOT_PRESENTED` 阻断。批量创建时每个 HTML Item 分别验证自己的拼接值卡片。完整 VI 只能创建一个顶层 HTML Item，分页或章节不得拆 Item；完整 VI 的 CDN、HTML 上传、CLI、回读与卡片交付必须由 Main Agent 执行，Subagent 只负责完整 HTML 生成／修改及 `shot.py` 自检。禁止创建 HTML Frame，也禁止通过聊天、Markdown、附件、压缩包或 `present_files` 直接交付原 `.html`。缺少 HTML 上传、HTML Item 写入或回读任一步，以 `HTML_ITEM_DELIVERY_INCOMPLETE` 阻断。

**HTML 正式生产门禁**：当前获准范围的正式媒体（含候选、未采用版本和中间素材）须逐项完成 RichMediaCard 直接交付，并按素材清单核验采用版本。串行当前结果或固定并行批次尚未交付完成就开始依赖的 HTML 组装，以 `HTML_ASSEMBLY_BEFORE_MEDIA_BARRIER` 阻断；图片已嵌入 HTML 或 HTML Item 已创建不能代替媒体交付。素材准出沿用内容、身份和用途检查，生成结果的 Item ID 与产后 `+get` 不作为组装前提。

默认 Canvas 环境通过 HTML Item 画布卡片交付可编辑作品；原始 HTML 文件及其上传链接仅用于平台写入。Mobile 仍按专用预览出口交付。

## 5. 历史资产与锚点

内部资产索引还必须按 [画布资产语义目录工作流](canvas-asset-organization.md) 检查：延续、修改或衍生任务在生成前已执行 `+tree → +ls → +get`，恢复历史上传锚点、当前核心母版、可复用生成资产、已有交付物和版本／衍生关系；未读目录便重新生成已有资产、绕过现有锚点或因对话遗忘导致目标偏移，以 `ASSET_INDEX_NOT_READ_BEFORE_GENERATION` 阻断。每个顶层 Item／Frame 的 `path` 必须以 `/` 开头；提交相对路径时以 `CANVAS_PATH_NOT_ABSOLUTE` 阻断。顶层领域必须区分 `/user-anchors`、`/core-assets`、`/generated-assets` 与 `/deliverables`，复杂资产集合按身份、任务、用途、角色、变体或版本建立必要层级，不得固定两层，也不得出现空层或无检索价值的深层目录。用户上传锚点须通过真实 Item、`source_anchor_id`／`core_asset_id` 和 `+get` 回读确认，不能被 Agent 候选冒充；brief、来源、衍生关系及对象未修改字段必须保持可追溯。手工创建的画布编辑、参考或衍生对象须在创建 XML 中写入与回读来源一致的 `<source_ids>`；缺失、猜测、跨 Workspace、不可见或失效 ID 以 `CANVAS_SOURCE_IDS_INVALID` 阻断。无来源时必须省略整个标签；`+update` 不得承担修改血缘的职责。

身份任务必须恢复已确认母版与来源、保护范围及允许变化；返回的 core_asset_id／source_anchor_id 保存在已有任务／资产记录，母版自身 brief 不要求尚未返回的自身 ID。图像工具衍生物记录可用来源 ID 或等价母版句柄，并使用实际母版图片作为工具身份输入；并行同源变体按门禁独立调用，不把上一张衍生图提升为母版。Mobile 使用可回读的本地关联，不要求 Canvas ID。

## 6. 结果与失败出口

在最终交付说明中简要记录媒体真实引用与 RichMediaCard 展示状态、HTML 预览 CDN＋Markdown 状态，以及默认 Canvas 的 HTML Item 创建／回读和产后归档结果；任一阻断项失败，转入 `references/workflow/troubleshooting.md`，修复后重新验证。

Mobile 记录本地源版本、媒体展示和预览 CDN＋Markdown 状态；Canvas 记录真实上传、Item 回读与卡片结果。当前环境所需交付未齐不得宣称完成；已授权交互仍须在支持运行的目标端验证，截图不代表交互通过。
