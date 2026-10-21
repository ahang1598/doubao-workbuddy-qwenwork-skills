<a id="html-fixed-canvas-delivery"></a>

# HTML/CSS 固定画布与交付协议

页面自检统一遵循 [预览策略](../workflow/html-preview.md)：退出码 `1` 表示检查完成并发现问题，必须按 hint 与实际截图修正并重跑，不得改记为“预览未验证”；预览问题本身不阻断默认 Canvas 的 HTML 上传、Item 创建与回读，源码硬门禁和适用媒体门禁仍可独立阻断这些步骤。只有退出码 `3` 的执行失败可记录“预览未验证”并继续未被独立规则阻断的可完成部分。只有当前版本合格的同尺寸完整预览才进入 CDN＋Markdown 展示，不合格截图不得展示；预览或其他必要交付未闭环时不得宣称完整完成。Mobile 无合格预览时只说明可视交付未完成，不进入 Canvas。


本文件是本 Skill 的 最终 HTML唯一事实源，统一定义完整文档、固定画布、样式、尺寸测量、预览验收、上传、顶层 HTML Item 写入与回读。所有创建与编辑 workflow 只能引用本文件，不得另建相冲突的 HTML 协议。这里的 HTML 是完整作品源，不是 Frame 内的片段，也不是响应式网站默认模板。

### 文档与尺寸

- 每个作品生成一个完整 HTML 文档作为待上传源，包含 `<!DOCTYPE html>`、`html`、`head`、UTF-8 声明和 `body`；不得只生成片段、补丁或截图。多个真正独立的作品分别保存为独立 `.html` 文件，原始文件不直接交给用户。完整 VI 系统无论内部包含多少章节或分页，都视为一个作品，只能生成一个完整 HTML、上传一次并创建一个唯一顶层 HTML Item；内部页不得拆成多个文件或 Item。
- 除下述三个根节点的固定宽高须行内声明外，视觉样式可使用行内声明、普通 `<style>`、class／id 选择器或可加载的外部样式表。字体声明按 [Web 字体契约](../rendering/web-font-contract.md) 使用，不限定字体块名称、数量或与普通样式分离。
- 必须在 `<html>` 标签上输出 `data-canvas-width` 和 `data-canvas-height`，分别表示作品原始宽度和高度；值必须是十进制正整数字符串，默认单位为 px，不写 `px`、小数或百分号。例如：`<html lang="zh-CN" data-canvas-width="574" data-canvas-height="7920" style="width:574px;height:7920px;...">`。
- `<html>`、`<body>` 及唯一作品容器的行内 `style` 中，`width`、`height` 必须写成与上述属性完全一致的固定 `px` 值；确保实际边框盒与声明尺寸一致；不强制 `margin`、`padding` 或 `box-sizing` 的具体写法。不得只设置属性而遗漏根文档 CSS 尺寸，也不得让三者宽高不一致。不得在 `html`、`body` 或唯一作品容器上使用 `overflow:hidden` 隐藏超出边界的正文、模块或页尾；局部装饰容器仍可按设计需要裁切。
- 固定尺寸要求适用于 `<html>`、`<body>` 和唯一作品容器；这三处不能用 `max-width`、`min-height`、`height:auto` 代替固定宽高。内部内容容器可在已确定的可用宽度下使用正常流、Flex/Grid 和内容自适应高度；内部尺寸依据实际排版确定，不因根画布固定而统一写死。用户或构图明确锁定的内部区域须在其范围内重排，并满足 [容器内容框与间距](../style/coding/composition-layout.md#容器内容框间距与顶边)。不得使用 JavaScript、`vw`、`vh`、其他视口单位或媒体查询计算、推导或改变作品尺寸；也不得对根文档或整个作品容器执行随窗口变化的 `scale`、`zoom`。内部百分比布局可以相对固定画布计算；字号和布局不得因视口改变而产生不同的画布排版。
- 内容型章节优先按正常流撑高或使用 `min-height`；不得以固定高度配合 `overflow:hidden/clip` 或蒙版裁掉有效内容。明确锁定的构图区先验证内容容量，装饰裁切与内容层分开。溢出时修正所属容器及下游排布，不只取消裁切让内容越入下一章；未锁高长页在字体、图片就绪且章节完整后按下文测高并回填根画布，锁高作品在原尺寸内重排。
- `data-canvas-protocol`、`data-canvas-version` 和 `id="canvas-root"` 不属于本协议必填项。已有标记保留；只有目标接入规范明确要求时才新增，不把它们误认为宽高属性或 CSS 的替代。

属性最小示例：

```html
<html lang="zh-CN" data-canvas-width="574" data-canvas-height="7920" style="width:574px;height:7920px;margin:0;padding:0;box-sizing:border-box;">
```

### 尺寸选择与单位换算

本节统一 HTML 路径的尺寸选择与换算，不重新决定生产路线。优先使用用户明确尺寸及适用的已确认印厂／投放位规格；编辑任务继承原作品尺寸，除非用户要求改变。两项明确约束冲突时解决冲突，不用默认值覆盖。没有尺寸时采用当前品类 Spec 的推荐，并在既有 Brief 中记录用途、尺寸、单位与假设来源；示例画布不自动成为全品类默认值。

| 尺寸层 | 如何记录与使用 |
| --- | --- |
| 数字作品 | 目标宽高用 px，按品类／发布用途选定；默认 1 倍导出与画布同像素，额外倍率由实际导出需求决定 |
| 物理成品 | 裁切宽高、出血、折线与安全区用 mm；折叠品同时记录展开与闭合尺寸，保留真实毫米值 |
| HTML 排版 | 默认按 `1 in = 96 CSS px` 换算：`px = mm × 96 / 25.4`，`1 pt = 4/3 px`。固定根画布的宽高向上取整；元素及折线先保留精度，需整数边界时累计转换后求差 |
| 印刷位图导出 | 按目标 PPI 单独计算 `export_px = ceil(mm / 25.4 × PPI)`，不能把 96 CSS px/in 当成印刷分辨率。PPI 未确认时可用 300 作为设计测试目标，但须标为假设，不冒充印厂要求 |

CSS 绝对单位关系依据 [W3C CSS Values and Units](https://www.w3.org/TR/css-values-4/#absolute-lengths)。屏幕中的 CSS 毫米不保证与实物尺测毫米一致，物理成品按记录的实际尺寸核对。

出血不含在裁切尺寸内：已确定每边出血 `b mm` 时，出血版覆盖 `(裁切宽 + 2b) × (裁切高 + 2b)`，内容和折线相对裁切区定位，再整体偏移到出血画布。出血未知时不猜填；先完成裁切区设计，保留待确认项。clean artwork 不显示辅助线，production proof 可展示折线、裁切线和说明，两者不得混成同一个无标记成品。

按物理尺寸导出高分辨率位图时，从同一源按目标分辨率重新渲染；不靠修改 PPI 元数据或放大小截图宣称增加清晰度。导出目标像素从未取整的物理尺寸计算，核对边界与原比例；仅因 CSS 根尺寸取整产生的余量按边缘处理，不非等比拉伸。HTML 源保持自己的固定画布，不因导出倍率重写版式。尺寸和 PPI 齐全不等于具备印刷交付能力，实际色彩、出血和输出条件仍沿品类生产规范核验。

### 原始尺寸的确定

1. 已有作品显式指定固定尺寸时优先沿用，并检查声明、CSS 和内容边界是否相符；发现冲突时依据设计尺寸与实际内容修正，不能只补属性。
2. 原文件只有最大宽度和内容自适应高度时，先确定原设计宽度。在该宽度下等待字体、图片就绪，将入场元素置于最终排版状态，测量完整内容范围；自动高度测量发生在固定高度之前，避免已设定的高度掩盖内容溢出。绝对定位内容还需检查最下方元素边界。
3. 高度为小数时向上取整，再把同一个整数写入两个根节点、作品容器 CSS 与高度属性。例如完整内容为 `3453.3125px`，输出 `3454` 和 `3454px`。用户明确锁定高度时以锁定值为准，并在该高度内修正溢出。
4. 测量可使用开发／验证阶段的布局测量工具或临时脚本，最终文档不得保留用于自动适配作品尺寸的脚本。不得使用 `overflow:hidden` 掩盖正文或页尾超出；设计所需的局部装饰裁切可以保留。

已对齐的尺寸实例（不是所有作品的默认尺寸）：

| 作品 | 宽 × 高（px） | 尺寸处理 |
|---|---|---|
| 冲锋衣详情页 | 1080 × 6480 | 移除随窗口缩放画布的脚本 |
| 健康科普 | 480 × 3454 | 固定根文档与作品容器尺寸，不保留视口驱动的尺寸逻辑 |
| 波普拼贴养猫长图 | 1080 × 6480 | 固定根文档与作品容器尺寸 |

### 脚本与交互边界

- JavaScript 不得读取视口或元素尺寸来计算、推导、覆盖作品宽高，也不得执行自适应缩放、重排或媒体查询替代逻辑。
- 非尺寸用途的必要交互脚本只有在用户明确要求交互时才可保留；QA 检查不得临时注入样式掩盖原文件的问题。
- 不使用 CSS 动画作为默认实现。静态打开时所有内容必须完整可见，不得依赖脚本触发后才解除 `opacity:0` 等隐藏状态。

### 图片素材短链契约

- HTML 插入生成或编辑得到的图片时，必须逐字使用素材清单中已准出的最终 HTTP(S) 短链。图像工具原始结果可直接采用时使用其原始短链；经过抠图、裁切或其他会生成新文件的处理时，使用该处理步骤回填的最终短链。不得自行下载、复制、重新上传或换链。
- 该要求覆盖 `<img src>`、`<img srcset>` 的每个候选、实际生效的 CSS 背景／蒙版图片（含外部样式与伪元素），以及内嵌 SVG 的 `<image href>`／`xlink:href`。同一素材出现多次时复用同一条已准出短链，不复制成新的资产地址。
- 禁止在最终 HTML 中引用本地路径、相对文件路径、`file://`、`data:`、Base64、Blob URL、工具临时预览地址或尚未回填素材清单的占位 URL。用户提供或既有图片没有可持久访问的有效短链时，先取得并核验短链，再进入 HTML 组装。
- 短链可访问不等于素材正确。HTML 仍须绑定与 Brief 消费者、身份来源、版本、尺寸和 Alpha 状态一致的就绪资产；短链变化后同步更新素材清单和全部 HTML 消费位置，并重新预览验证。

### 可编辑文字、字体与文字效果

- Design Brief 标记为 Coding 的主副标题、章节标题、正文、数字、单位、标签、CTA、图注和来源必须逐字成为真实 HTML 文本节点，并能独立定位修改；可使用合适的选择器，不强制 `id`／`data-layer-id`。禁止将这些文字栅格化、烘焙进背景、用截图代替，或为了套用效果改写文案。
- 一体化 Hero 图内文案和独立艺术标题只有在 Brief 明确准入时才可作为图片；它们必须与 Coding 文字清单互斥，不能在图片与 DOM 中重复覆字，也不能声称图片内文字可编辑。
- 字体选择和实现参数只保存在最终 HTML。每个文字消费者以 CSS `font-family`、`font-weight`、`font-style`、`font-size`、`line-height`、`letter-spacing` 等落实；最终 family 必须按 [字体资源契约](../rendering/font-family-library.md) 在目标 HTML 渲染环境验证。远程字体必须按 [Web 字体契约](../rendering/web-font-contract.md) 解析，使用解析所得的真实 `@font-face`，可与其他样式合并或分块声明；只在开发机可见的本地字体文件或 CDN 下载不能作为上传后字体可用证据。
- 文字效果先按 `ref_key` 检索 CSS catalog，并把选中实现绑定到具体文字节点。描边使用 `-webkit-text-stroke` 并提供可读字色；阴影或发光使用受控 `text-shadow`；渐变文字同时写入 `background`、`background-clip:text`、`-webkit-background-clip:text` 与透明文字色；倾斜、错落、立体或逐字差异用真实嵌套 `span` 和 `transform`／阴影实现。前后装饰可使用伪元素；需要独立定位时使用真实装饰节点并设置 `aria-hidden="true"`。
- 效果不能牺牲编辑性、逐字准确性或可读性。复杂纹理、破损或自由轮廓若无法稳定作用于真实文本，优先简化为最接近且可编辑的 CSS 效果；只有 Brief 明确把该唯一大标题准入艺术字图片时才走图片路线。不得用图片替代所有 Coding 文字来追求视觉相似。
- 最终预览以真实文案检查字体 family、字重、换行、基线、孤字、描边内缩、阴影边界、渐变裁切和溢出。效果属性存在但肉眼不可见、字体静默回退或文字与图片关系未兑现，均视为未完成。

### 最小文档示例

示例仅展示固定尺寸结构，实际交付需包含作品的全部样式、内容和必要动效。

```html
<!DOCTYPE html>
<html lang="zh-CN" data-canvas-width="480" data-canvas-height="3454" style="width:480px;height:3454px;margin:0;padding:0;box-sizing:border-box;">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>作品标题</title>
</head>
<body style="width:480px;height:3454px;margin:0;padding:0;box-sizing:border-box;">
  <main style="position:relative;width:480px;height:3454px;box-sizing:border-box;"><!-- 实际产物放入完整作品内容，非根级宽高的样式可按需组织 --></main>
</body>
</html>
```

### HTML 验收与交付

- 先按 [HTML 检查](../workflow/html-validation.md) 检查完整源码、真实 DOM、字体与素材；生产流程保持 Brief → 素材清单（适用时）→ HTML。
- 通过 `scripts/runtime/shot.py` 执行 [shot.py](../workflow/html-preview.md)，取得 1 CSS px 对应 1 PNG 像素的完整预览；不把其他视口截图、拉伸、补白或裁掉内容当成合格预览。
- 页尾按实际排版保留合适空间，不要求指定收尾节点、属性或统一数值。用实际内容和留白测高，最后把同一高度写入声明、html、body 和作品根。用户锁定尺寸时在原尺寸内重排，不擅自增高。
- 合格预览图通过 FileBatchUpload 上传 CDN，核验返回的公网 HTTP(S) 链接，再使用该链接以 Markdown 图片语法展示。截图仅按上述预览方式展示，不创建 IMAGE Item，不进入画布资产目录。工具临时图、本地路径或普通链接不能替代。
- 默认 Canvas：Main Agent 使用 `FileBatchUpload` 独立上传完整 `.html`，再以短链执行 `design-cli ... +create` 创建顶层 `<item type="HTML">`，保存服务端 ID 并执行 `design-cli ... +get` 回读核对 type、path、title、brief、size、asset URL；禁止 HTML Frame、Frame 内 HTML、代码片段或直接交付源文件。`HTML` 是 Item 类型，不存在 `+HTML` 命令。将本次 Workspace ID 与该 Item ID 拼成 `<workspace_id>?item_id=<item_id>` 单值交给 present_files，逐项展示对应卡片；完整 VI 只能有一个对应卡片。
- system 明示 `Device platfrom: Mobile` 时，按 [Mobile 直接交付](../workflow/mobile-app-direct-delivery.md) 仅展示 CDN 预览，不上传 HTML、不创建或回读 Canvas 对象、不输出卡片。
- 原始 `.html` 不通过聊天文件链接、Markdown、附件、压缩包或 present_files 直接交付；`FileBatchUpload` 只是创建 HTML Item 的内部输入。退出码 `1` 表示页面存在问题，必须修正并重跑，但该预览问题本身不阻断默认 Canvas 的 HTML 上传、Item 创建、回读及既定画布卡片闭环；写入或卡片成功不表示问题已解决。只有退出码 `3` 的执行失败可明确记录“预览未验证”并继续未被独立规则阻断的可完成部分。合格预览及当前环境所有必要交付缺一不可；没有真实平台结果时保留未验证状态。另需正式媒体导出时按原媒体门禁处理。

## 平台对象与版本边界

- HTML 只能经 `FileBatchUpload` 取得短链后，创建为顶层 `<item type="HTML">`；完整载荷与调用方式见 [HTML Item 协议](../items/HTML.md) 和 [create 协议](../cli/create.md)。
- 禁止 `<frame type="HTML">`，也禁止把 HTML Item 放入 Frame 成员。一个完整长图、详情页或单件作品只对应一个完整 HTML 文件和一个顶层 HTML Item。
- `+update`／`+update-batch` 只允许修正顶层对象的 `brief`／`path`，不能替换 HTML 内容、尺寸、标题或资产短链。内容、样式、素材或尺寸变化时，必须重新上传完整 HTML 并 `+create` 新版本。
- 原始 `.html` 不通过 `present_files` 直接交付；平台闭环以预览图 CDN 上传与 Markdown 展示、上传短链、create 返回、get 回读和 Workspace 画布卡片为证据。
