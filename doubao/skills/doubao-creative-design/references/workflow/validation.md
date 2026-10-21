# 创建／大改后的交付验证

页面自检统一遵循 [预览策略](html-preview.md)：退出码 `1` 表示检查完成并发现问题，必须按 hint 与实际截图修正并重跑，不得改记为“预览未验证”；预览问题本身不阻断默认 Canvas 的 HTML 上传、Item 创建与回读，第 2 节源码硬门禁和适用媒体门禁仍可独立阻断这些步骤。只有退出码 `3` 的执行失败可记录“预览未验证”并继续未被独立规则阻断的可完成部分。只有当前版本合格的同尺寸完整预览才进入 CDN＋Markdown 展示，不合格截图不得展示；预览或其他必要交付未闭环时不能宣称完整完成。Mobile 无合格预览时只说明可视交付未完成，不进入 Canvas。


本文件沿用源版的源码、真实预览、媒体交付和 Canvas 回读验收；输入适配 short 的唯一自然语言 Brief、适用素材清单与完整 HTML，不要求另建 Design IR，不恢复 XML 设计源流程。验收只核对已锁定目标，不重新选择路线。

通知／公告／喜报／捷报／成果战报／邀请函／节庆贺图已有合适底图且无需新图时，按主 SKILL 的复用例外核验真实来源、质量与最终可见消费者，不强制新生成／编辑记录；其余新建 AI Coding 仍核对必要的图像生产。

## 1. 环境与产物分流

- system 明示 `Device platfrom: Mobile` 时读取 [Mobile 直接交付](mobile-app-direct-delivery.md)：跳过本文 Workspace 创建、Canvas CLI、Item、画布卡片和 HTML 上传要求；已有唯一有效 Workspace ID 仍须传入每次图像工具调用，无 ID 时不创建；媒体使用 `RichMediaCard` 逐项交付，HTML 预览上传 CDN 后以 Markdown 图片展示。只支持静态出口，交互需求须在冻结前按该文档处理。
- 纯图／视频：读取同一 Brief、真实工具结果、准确事实与身份来源，核对内容、尺寸、质量、身份、功能内容及媒体门禁，随后检查当前环境的交付状态；不要求 HTML、DOM、字体契约或 shot.py。纯图编辑核对目标范围与未授权变化。成功但有缺陷的结果仍先交付，是否可继续组装另行判定。
- HTML：读取当前完整源、同版本素材、唯一 Brief 与用户验收要求，执行第 2、3 节和当前环境的交付检查。普通文字保持可编辑；品类明确准入的图内文案按已确认边界验收。禁止因没有模板 ID、CSS ID、坐标或参数而将自然语言 Brief 判失败。
- 只有图片且要求重建 HTML 的任务使用对应创建流程；真实已有 HTML 才使用源编辑流程。验收依据实际输入与授权范围，不假造源结构。

## 2. HTML 源码与编辑边界

HTML 校验首先执行不可降级的源码门禁：`<html>` 必须带十进制正整数 `data-canvas-width` 与 `data-canvas-height`；`html`、`body` 和唯一作品容器必须在各自的行内 `style` 中声明与属性完全一致的固定 px 宽高。其余视觉样式可使用行内声明、普通 `<style>`、class／id 选择器或可加载的外部样式表；字体声明遵循 [Web 字体契约](../rendering/web-font-contract.md)，不限定字体块名称、数量、位置或与普通样式分离，不因这些写法阻断。正式 HTML 使用 JavaScript、`vw`、`vh`、其他视口单位或媒体查询计算、推导或改变作品尺寸时，以 `HTML_CANVAS_SIZE_NOT_FIXED` 阻断；浏览器测量副本中执行页面 JavaScript 读取自然高度并临时解除根级尺寸限制不属于此禁令，临时变更不得写回正式源。根画布使用 `overflow:hidden` 掩盖正文、模块或页尾溢出时，以 `HTML_ROOT_OVERFLOW_CLIPPED` 阻断。页尾按实际内容与版式留足空间，不要求特定安全区节点、属性或固定最小值。

核对完整 `<!DOCTYPE html>`、head、UTF-8、body 与闭合文档。一个连续作品只对应一个 HTML；独立作品分别交付。实际 URL、准确 DOM 文字、层级和替换关系完整。纯 Coding 不套用 AI 素材生产门禁；AI Coding 核对原素材清单与实际图片消费者，仅展示后弃用、未登记准出或未绑定正式消费者的 KV，以及隐藏装饰，不能充当正式素材完成证据；已按品类规则登记准出并实际用于正式 Hero 的 KV 可以计入。

编辑后保留未授权 DOM、文案、素材、画布尺寸和关系；用合适的选择器、真实资产 URI 与语义唯一定位目标，不强制 DOM id／data-layer-id。选区不能唯一对应时先确认；透明叠加图片仍须有真实 Alpha、深浅底边缘与孔洞检查。独立艺术字不按新建／编辑分流：消费者仅为已知稳定 HTML 背景时可选择纯色底混合，需要透明导出、跨背景复用、背景未知或严格保色时选择抠图。混合路线中深色字体未使用纯白底＋目标节点的 `mix-blend-mode: multiply`，浅色字体未使用纯黑底＋目标节点的 `mix-blend-mode: screen`，或混合模式误设在父容器／整页时，以 `ART_TITLE_BLEND_MODE_INVALID` 阻断；抠图路线缺少真实 Alpha、内部孔洞或深浅底边缘检查时，以 `ART_TITLE_ALPHA_INVALID` 阻断。图像生成／编辑结果未通过第 4 节的 Workspace ID 与直接交付检查，或抠图等其他媒体未完成其产出工具的适用交付协议时阻断。HTML 内容变化重新上传并 create 新 Item，update 不修改内容。

## 3. 真实预览与视觉目标

HTML 最终视觉验收必须读取 [`shot.py` 预览与检查](html-preview.md)，并记录该脚本对当前完整本地 HTML 的渲染结果。未调用 `shot.py`、改用 Agent 手动浏览器预览或普通网页截图时，记录 `HTML_PREVIEW_MISSING`。最终截图像素宽高未分别严格等于 `data-canvas-width` 和 `data-canvas-height`，宽高比不一致，或因默认宽度、DPR、缩放、拉伸和补白导致尺寸变化时，统一记录 `HTML_PREVIEW_SIZE_MISMATCH`；只满足相同比例但像素尺寸不同仍不通过尺寸校验。单屏作品未覆盖完整画布，或长图、详情页等连续作品存在截断、重复、缺段、页尾内容未完整显示和资源加载失败时，记录 `HTML_PREVIEW_INCOMPLETE`。文档、字体、图片或布局高度在超时前未稳定时记录 `HTML_PREVIEW_NOT_STABLE`；控制台异常、网络／字体／资源失败或本地文件引用记录 `HTML_PREVIEW_RUNTIME_ERROR`；横向溢出、文字重叠或非预期裁切记录 `HTML_PREVIEW_LAYOUT_ERROR`。这些记录不得阻止 FileBatchUpload 或 `design-cli design-workspace +create`，但不合格截图不得展示；尺寸与内容合格但预览图未成功上传 CDN，或返回链接不是可访问的 HTTP(S) URL 时，记录 `HTML_PREVIEW_CDN_UNAVAILABLE`。缺少使用该 CDN URL 的标准 Markdown 图片展示时，以 `HTML_PREVIEW_MARKDOWN_MISSING` 阻断最终完成。预览截图仅走 CDN＋Markdown，不创建 IMAGE Item 或写入画布。

按 [HTML 检查执行流程](html-validation.md)，需要测高时由 shot.py 内部执行页面 JavaScript，完成自然高度与页尾内容边界测量、未锁高时的四处高度回填及正式固定高度复测；锁高越界返回排版。`scripts/runtime/shot.py` 在一次调用中完成自然高度测量、固定高度复核与严格截图。不影响高度的局部修改不强制整体测高。以当前完整预览检查图文关系、渐变文字安全区、字形局部对比、素材作用、实际阅读尺寸和接缝；DOM 与资源诊断使用 shot.py 实际返回的报告，未输出的字体明细不得自行推断。未提供的诊断如实标记未验证；自动通过不等于视觉通过。

逐项对照 Brief → 实际素材／HTML 承载 → 渲染效果，核验实际引用版本在最终显示尺寸下的主体、文字与必要细节清晰度，不以像素数值代替目视检查。低清未解决则视觉验收失败；生成／编辑工具返回的图片或视频问题版本仍按媒体门禁交付并说明，HTML 预览不合格时不得展示该预览，必须修正并重跑。问题版本均不得作为合格成品或宣称完成。结构完成与视觉完成分别记录。CSS／SVG 必须有真实消费者、依赖和可見效果；未命中库可按设计目标自定义，不虚构条目。失败回到素材或 HTML，不降低 Brief 目标迁就实现。参考任务按 [参考解析与对照](../style/coding/ai-coding/reference-analysis.md) 复查锁定特征；局部编辑复查受影响区与相邻布局，全局变化重看全图。

简历、三折页的姓名与标题按各自 Visual 保持原生可编辑；其他品类独立艺术标题仅用于准入的唯一最高主标题，须有准确源文字、消费者、接入方式、最终文件与缩放验收。混合路线核验纯白底＋`multiply` 或纯黑底＋`screen` 的成对实现、完整画面融合和对比度；抠图路线核验透明通道、内部孔洞及深浅底边缘。一体化 Hero 不重复覆字；用户明确要求文字独立可编辑时按相应分层边界核验。三折页检查展开与折叠，简历检查事实与线性阅读，Logo／VI 检查身份。

## 4. 默认 Canvas 写入与媒体交付

以下 Workspace 创建与 Canvas 动作仅用于默认环境；图片直交检查适用于两种环境。Mobile 已有唯一有效 Workspace ID 时仍须透传，无 ID 时记录该事实并直接交付，不以缺少 ID 阻断，也不创建 Workspace。ID 冲突、工具参数不支持或校验失败按主 SKILL 停止，不允许省略已有 ID 后重试。

2. **Workspace 与媒体结果核对**：先确认生产前已从当前对话绑定唯一 `active_workspace_id`；对话无 ID 时，必须存在本轮 `+workspace-create` 响应，以及主 Agent 将响应中的原始 ID（`workspace_id`）原样作为 `present_files` 单值输入并成功交付 Workspace 画布卡片的记录，否则以 `WORKSPACE_CARD_NOT_PRESENTED` 阻断。该卡片成功前不得开始生产。不得在无 ID 时先调用 `+get-workspace`，不得为 ID 创建中间文件、添加包装、改用数组或拆分调用；自创建响应返回至卡片成功交付，只允许主 Agent 执行上述单值调用，不得混入其他用户可见文字、链接、路径、日志、CLI 输出、总结、其他产物或重复 ID 交付，否则以 `WORKSPACE_CARD_DELIVERY_NOT_EXCLUSIVE` 阻断。初始化卡片只使用原始 Workspace ID，不与后续 HTML Item 卡片的拼接值混用。每次 `image_gen`／`image_edit` 必须显式传入同一 `active_workspace_id`，工具成功结果使用 `RichMediaCard` 直接逐项交付；禁止为该结果执行重复的 `design-cli +create`、`FileBatchUpload` 或另建 IMAGE Item，也不得在直接交付前插入媒体 `+get`；交付后的目录读取与 path 更新按第 5 节执行。完整 HTML 和其他非图像工具产物仍按各自 workflow 执行上传、创建与回读。

3. **渲染与呈现文件**：逐项核对 [交付门禁](image-generation-delivery-gate.md) 记录。图片／视频（含正式渲染／导出成品）核对 `RichMediaCard` 已展示正确版本的真实结果；只有生成成功、资源 URL 或文字说明不算交付。HTML 预览继续按下文 CDN＋Markdown 验收，Workspace／HTML Item 卡片仍按 `present_files` 协议验收，不互相替代。每张图片分别交付，交付对象必须是 `image_gen`／`image_edit` 返回的对应原始产物；先下载、复制、重新上传，或仅展示工具 URL、预览、缩略图、Markdown 图片和普通文本路径时，以 `TOOL_ARTIFACT_NOT_PRESENTED_DIRECTLY` 阻断。缺少适用环境要求的 Workspace ID 透传记录（Mobile 无 ID 的合法情形除外）、工具结果句柄或单项交付结果时，以 `MEDIA_DELIVERY_BARRIER_INCOMPLETE` 阻断。效果不佳、错字、身份漂移或预计返工的成功输出也必须先直接交付；静默过滤以 `IMAGE_RESULT_HIDDEN_BEFORE_REPAIR` 阻断。AI 图片内生成文字问题须标记 `delivered_with_text_issue` 并等待用户提出修改要求；若它承担准确文字，下游组装保持暂停。交付失败后仍开始依赖步骤，以 `MEDIA_DELIVERY_FAILURE_IGNORED` 阻断。

   **HTML Item 校验**：上述媒体门禁既不适用于原始 `.html`，也不适用于 `shot.py` 产出的 HTML 预览截图。可编辑设计的 `.html` 调用 `shot.py`，把像素宽高严格等于声明画布且内容完整的预览图用 `FileBatchUpload` 上传 CDN；核验返回的公网可访问 HTTP(S) 链接后，以该链接用标准 Markdown 图片语法展示。截图仅走 CDN＋Markdown，不创建 IMAGE Item 或写入画布。再另行经 `FileBatchUpload` 上传 HTML，以 HTML 文件短链创建并回读顶层 HTML Item；不得混用预览图 URL 与 HTML 源 URL。预览失败或不完整不阻断 HTML 上传和写入，但合格预览图尚未完成 CDN 上传及 Markdown 展示时不得完成。HTML Item 回读成功后，必须把同一 `active_workspace_id` 与该回读对象的 `item_id` 拼成 `<active_workspace_id>?item_id=<item_id>` 单值并原样传给 `present_files` 输出对应画布卡片；拆成两个参数、数组或两次调用，只传 Workspace ID，缺少任一 ID、两者不属于同一回读对象，或误用旧版本 Item ID，均以 `HTML_WORKSPACE_CARD_NOT_PRESENTED` 阻断。批量创建时每个 HTML Item 分别验证自己的拼接值卡片。完整 VI 只能创建一个顶层 HTML Item，分页或章节不得拆 Item；完整 VI 的 CDN、HTML 上传、CLI、回读与卡片交付必须由 Main Agent 执行，Subagent 只负责完整 HTML 生成／修改及 `shot.py` 自检。禁止创建 HTML Frame，也禁止通过聊天、Markdown、附件、压缩包或 `present_files` 直接交付原 `.html`。缺少 HTML 上传、HTML Item 写入或回读任一步，以 `HTML_ITEM_DELIVERY_INCOMPLETE` 阻断。

**HTML 正式生产门禁**：主视觉确认后，正式生产中的任一 `image_gen`／`image_edit` 结果缺少适用环境要求的 Workspace ID 透传记录（Mobile 无 ID 的合法情形除外）或通过 `RichMediaCard` 逐项交付，均以 `MEDIA_DELIVERY_BARRIER_INCOMPLETE` 阻断；媒体已嵌入 HTML 或最终 HTML Item 已创建，不能补偿媒体自身未交付。任一结果或固定并行批次尚未完成交付就开始 HTML 组装，以 `HTML_ASSEMBLY_BEFORE_MEDIA_BARRIER` 阻断。候选、未采用版本和 HTML 中间素材同样纳入检查；禁止先积攒素材再集中交付，或在 HTML 组装后补写媒体记录。

禁止通过 `present_files` 直接交付原 `.html`；完整 VI 还禁止通过聊天、Markdown、附件或压缩包直接交付 HTML 源文件。

## 5. 历史资产与锚点

内部资产索引还必须按 [画布资产语义目录工作流](canvas-asset-organization.md) 检查：延续、修改或衍生任务在生成前已执行 `+tree → +ls → +get`，恢复历史上传锚点、当前核心母版、可复用生成资产、已有交付物和版本／衍生关系；未读目录便重新生成已有资产、绕过现有锚点或因对话遗忘导致目标偏移，以 `ASSET_INDEX_NOT_READ_BEFORE_GENERATION` 阻断。每个顶层 Item／Frame 的 `path` 必须以 `/` 开头；提交相对路径时以 `CANVAS_PATH_NOT_ABSOLUTE` 阻断。顶层领域必须区分 `/user-anchors`、`/core-assets`、`/generated-assets` 与 `/deliverables`，复杂资产集合按身份、任务、用途、角色、变体或版本建立必要层级，不得固定两层，也不得出现空层或无检索价值的深层目录。用户上传锚点须通过真实 Item、`source_anchor_id`／`core_asset_id` 和 `+get` 回读确认，不能被 Agent 候选冒充；brief、来源、衍生关系及对象未修改字段必须保持可追溯。手工创建的画布现有对象编辑、参考或衍生版本还必须在创建 XML 中写入与回读来源一致的 `<source_ids>`；缺失、猜测、跨 Workspace、不可见或失效 ID 以 `CANVAS_SOURCE_IDS_INVALID` 阻断。无来源时必须省略整个标签；`+update` 不得承担修改血缘的职责。

默认 Canvas 的本轮生成结束后还必须存在产后目录证据：图片结果已先通过 `RichMediaCard` 直接交付，HTML 已完成平台写入与首次回读；随后 `+tree`／`+ls` 定位真实对象、`design-cli design-workspace +get` 读取本轮内容、`+update`／`+update-batch` 仅写入稳定绝对 path，并再次回读确认对象内容与布局未改变。缺少该闭环以 `ASSET_INDEX_NOT_ORGANIZED_AFTER_GENERATION` 记录；不得以补建 IMAGE Item、第二个 HTML Item、空目录 Item 或虚构 `mkdir` 消除该问题。Mobile 不执行此项。

身份任务必须恢复已确认母版与来源、保护范围及允许变化；返回的 core_asset_id／source_anchor_id 保存在已有任务／资产记录，母版自身 brief 不要求尚未返回的自身 ID。图像工具衍生物记录可用的来源 ID 或可追溯的等价母版句柄，不为补 ID 重复创建对象，并使用实际母版图片作为工具身份输入；并行同源变体按门禁独立调用，不把上一张衍生图提升为母版。Mobile 使用可回读的本地关联，不要求 Canvas ID。

## 6. 结果与失败出口

在最终交付说明中简要记录：`image_gen`／`image_edit` 使用的 Workspace ID、工具结果与 `RichMediaCard` 媒体交付状态；HTML 或其他显式创建对象的 Item ID 与 `+get` 回读；以及渲染／导出结果。保证每个交付文件可追溯；任一阻断项失败，转入 `references/workflow/troubleshooting.md`，修复后重新验证。

Mobile 记录本地源版本、媒体直接交付、预览 CDN 与 Markdown 状态；不伪造 Workspace 字段。预览问题本身不阻断 HTML 上传、Item 创建与回读，源码硬门禁和适用媒体门禁仍可独立阻断持久化；退出码 `1` 或预览不合格时必须修正并重跑，不合格预览不得展示，也不得宣称完整完成。退出码 `3` 可记录“预览未验证”并继续未被独立规则阻断的可完成部分。若已授权的交互尚未在支持运行的目标端验证，保留未验证状态，不能用截图代替。
