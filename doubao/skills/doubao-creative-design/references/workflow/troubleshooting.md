# 故障处理与回退顺序

> 先按主 SKILL 判断交付环境。system 明示 `Device platfrom: Mobile` 时遵循 [Mobile 直接交付](mobile-app-direct-delivery.md)：Brief／素材记录留在本地，跳过本文全部 Workspace、Canvas CLI、Item 与卡片步骤，媒体逐项直接交付、HTML 预览走 CDN＋Markdown。其他环境执行本文默认 Canvas 分支。生产与编辑顺序不变。

遇到生成失败、验证失败、空白／破损渲染、资产缺失、布局错乱或协议错误时，不假设前一步完全失败或完全成功。

## 读取路由

1. 读取当前失败点所属的 workflow、原始 Brief／最终 HTML、错误输出和当前源；先确定是创建、编辑、模板还是验证阶段失败。
2. 图片／资产错误读取对应 `creation/` 或 `editing/` 路径；涉及低清、比例错配、非等比拉伸、`IMAGE_LOW_RESOLUTION`、`IMAGE_ASPECT_MISMATCH`、`ASSET_CONFLICT` 或 Prompt 失配时额外读取 `references/style/coding/ai-coding/asset-prompt-guide.md`；艺术标题出现廉价描边／辉光、材质混乱、立体厚度／光向不一致或透视损害字形时读取 `references/style/coding/ai-coding/art-title-prompt-library.md`，只修当前失败维度后重生。艺术字问题不按新建／编辑判断：先核对消费者和接入方式；混合路线检查纯白底＋`multiply`／纯黑底＋`screen` 是否成对及真实背景融合，抠图路线检查 Alpha、内部孔洞和深浅底色边。只有消费者条件改变时才切换路线，不用混合模式掩盖应透明复用的资产，也不为稳定单背景无条件增加抠图。文字挤贴、异常换行、尾字消失或 `TEXT_OVERFLOW` 读取 `references/style/shared/composition-principles.md` 并回查最终 HTML 内容框。字体故障先按证据定位：字形、气质、角色或搭配不合适，读取 [字体推荐入口](../rendering/font-recommendation-list.md) 并用真实文案重新判断视觉候选；family／face／weight、许可或字形覆盖无法解析，读取 [字体资源与执行契约](../rendering/font-family-library.md) 并运行 Resolver；浏览器未加载目标字体，读取 [Web 字体契约](../rendering/web-font-contract.md)；字体已加载但换行、基线、伪粗体或裁切异常，回查最终 HTML、`shot.py` 和构图内容框。查询脚本只能诊断候选，不能证明资源可用；用户锁定精确字体或关键字形时，任一资源门禁失败都必须请求确认。`TRUNCATED_HTML`、固定画布、样式或完整文档错误读取 `references/html/coding-rendering.md`，平台 XML 载荷错误读取 `references/cli/README.md` 与 `references/items/HTML.md`。
3. 场景验证失败重读该场景 spec；回读核对或布局失败重读 `references/workflow/validation.md` 中相应检查项。

1. 保存错误信息、当前源、生成资产和已知版本；不要覆盖用户源文件。
2. 回读实际输出，确认哪些页面、图层、资产或字段已经成功写入。
3. 先分类错误：事实／素材、Brief／最终 HTML、图片生成、字体、HTML 协议、画布写入、布局或场景验收。
4. 只修复最小失败单元：局部元素用对应 `editing/` 流程；结构性错误才重建整屏；不要为一个标题错误重做整套产物。
5. 常见回退：AI 资产漂移时使用已验证用户资产或重新生成单项素材；比例或分辨率失败时按目标比例和最低像素重生，已有真实素材则扩图或用 `object-fit`／`object-position` 做安全裁切，不以非等比 transform 拉伸；`ASSET_CONFLICT` 时核对真实身份，只有同一素材才共用一条 `asset_id` 记录，否则拆成不同素材记录；文字溢出时增高内容框、调整行宽或语义断行，不用根级裁切、删除尾字或全局缩字掩盖；`TRUNCATED_HTML` 必须重新取得完整源，不删除标记或手工补闭合；字体不可用或无法提供真实文案所需的全部字形时，用户未锁定精确字体才可在同语种、同角色、同关键形态与气质内重选候选，并在真实 DOM 与 `shot.py` 中重新验证；已锁定时停止并请求确认，不得仅靠字体名、浏览器回退或静默替代声明成功。
6. `image_gen`／`image_edit` 已经成功产出的结果即使未通过，也必须按交付门禁在满足当前环境的 Workspace ID 规则后通过 `RichMediaCard` 直接交付；“未通过”不能作为隐藏原结果的理由，且不得重复创建媒体 Item 或在直交前回读；直交后的目录归档仍按公共门禁执行。非文字问题按最小失败单元生成修正版。若问题来自 AI 图片内生成文字的准确性、字形或可读性，只标记 `delivered_with_text_issue` 并等待用户提出修改要求，禁止过度反思、自动改 Prompt、自动编辑或重生；准确文字资产在等待期间不得进入下游组装。用户明确要求修改后的新版本继续执行同一门禁；若缺少不可替代的真实资产或事实，回到澄清策略一次性询问。
## CLI 写入失败：对账与停止条件

失败时保留原命令、完整 stdout／stderr、退出码和 logid，再分类处理：

- 参数或 XML 错误：对照对应命令页和 Item schema 修正；同一修正后的请求最多再尝试一次。
- HTML Item 资产错误：本地路径、空 URL、`file://`、`data:` 或不可访问短链都必须先停止写入，用 `FileBatchUpload` 上传完整 `.html` 取得持久短链后再创建顶层 HTML Item。
- `+update` 失败：重新 `+get` 目标；`+update` 只处理顶层 `brief`／`path`。HTML 内容变化必须基于最新完整源重新编译、上传并 `+create` 新版本，不能覆盖未知改动。
- `+create-batch` / `+update-batch` 失败：**整批是全成或全败，不存在部分生效**。收到失败就按「这一批一个都没写进去」处理 —— 修正后整批重提，不要逐个回读对账、也不要只补写其中几个（那会在整批已回滚的前提下写出一个残缺的集合）。批内对象数上限 50、`input` 上限 1MB，超限同样是整批拒。
- `+update-batch` 报 ID 重复：同一个顶层 `item_id`／`frame_id` 在一批里只能出现一次。把针对同一对象的 `brief`／`path` 修改合并成一条，不要拆成两条。
- `source_ids` 解析失败：重新用 `+ls`／`+get` 取得本 Workspace 中真实且可见的来源 Item／Frame ID；任一来源无效都会使整个 `+create`／`+create-batch` 请求失败。不得删除本应保留的来源来绕过落位／血缘要求，也不得把 `+get` 返回的旧 `<source_ids>` 原样复制为新版本来源；按本次真实派生关系重建。

网络断开或响应丢失时，服务端可能已经完成 create。先用 `+tree`／`+ls` 定位目标 path，再根据 brief、类型和资产 URL 核对；只有确认对象不存在后才能重试，避免重复创建。

出现以下任一情况时停止写入，保存诊断信息并交给上层排障 workflow：同一修正请求连续失败两次、无法确认 create 是否生效、缺少有效短链／鉴权／Workspace ID／正式命令契约，或回读与返回 ID、类型、对象数量不一致。不得伪造成功、跳过回读或只交付本地文件。


## HTML 高度、预览与各端出口排障

- `preview_size_mismatch`：读取 `expectedHeight`、`renderedHeight`、`deltaHeight`，检查正常流、Flex、固定／最小高度、外边距折叠、裁切和资源加载后变化。连续两次相同非零差值时停止反复增减声明高度；制作只含根尺寸、主内容、可疑 Flex、页尾与安全区的最小隔离 HTML，定位共同原因再修复。完整方法见 [HTML 预览协议](html-preview.md)。
- `HTML_PREVIEW_CDN_UNAVAILABLE`／`HTML_PREVIEW_MARKDOWN_MISSING`：保留当前源码、截图和真实上传状态，只补当前失败出口；必须取得公网可访问链接并以 Markdown 图片展示，不能用本地路径、普通链接或 IMAGE Item 代替。
- 默认 Canvas 的 HTML 已写入但卡片失败：使用刚回读的真实 Workspace／Item ID，只重试 `<workspace_id>?item_id=<item_id>` 单值卡片展示，不再次 create 同内容。多 HTML 作品逐项核对，不用 Workspace 总卡片代替各作品卡片。
- Mobile 缺少媒体直接交付或 HTML 预览／CDN 能力时，记录具体缺失能力并停止依赖步骤，不转入 Workspace、CLI 或 Item 流程。
