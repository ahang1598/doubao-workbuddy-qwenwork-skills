# 纯 Coding 步骤

> 先按主 SKILL 判断交付环境。system 明示 `Device platfrom: Mobile` 时遵循 [Mobile 直接交付](../mobile-app-direct-delivery.md)：Brief／素材记录留在本地，跳过本文全部 Workspace、Canvas CLI、Item 与卡片步骤，媒体逐项直接交付、HTML 预览走 CDN＋Markdown。其他环境执行本文默认 Canvas 分支。生产与编辑顺序不变。

用于主 `SKILL.md` 已选定 pure-coding 路线、可以完全由真实资产、准确文字、HTML/CSS 与内嵌 SVG 表达的设计。选定的父路线在本次任务中保持不变；不得因素材现成、代码可实现或实现方便，将 ai-coding 的新建、整体重做或局部修改改判为 pure-coding。用户明确要求全部由图像模型生成且不要 HTML 排版的长图／详情页属于主入口的 pure-image 例外，不进入本流程。

## 读取顺序

1. 先服从主 `SKILL.md` 的 Design Brief 前置门禁。Brief 使用自然语言，写明主题、核心对象、受众、内容、画幅、视觉意图、图文关系、可编辑范围与验收重点。
2. 有上传参考图或模板时读取 [参考图解析与继承](../../style/coding/ai-coding/reference-analysis.md)，把过滤后的观察与目标重建方案写回同一 Brief。
3. 读取当前品类 Spec 与 Visual System；无专属规则时读取 [通用视觉规则](../../style/coding/generic-visual-fallback.md)。含文字时读取字体主题与字体资源文档。
4. Visual 草案后按 `ref_key` 和实际效果职责先比较同品类、同作用范围的 CSS 组合并适配真实内容，再用 CSS／SVG 原子补足或替换局部；确无适用组合时才转原子组装或自行实现。最终 Brief 冻结后读取选中实现正文与依赖。
5. 直接按 [Brief → HTML 组装](../html-assembly.md) 编写完整固定画布 HTML。纯 Coding 不创建 `asset-manifest.json`、素材参数副本、字体计划副本或手填几何投影。
6. 编码、实际 DOM 几何、预览、上传和平台写入服从 [HTML/CSS 固定画布与交付协议](../../html/coding-rendering.md)。

## Brief → HTML

1. **冻结自然语言 Brief**：确认最终可见文案、内容顺序、参考继承范围、主焦点、图文关系和内容容量。
2. **读取实现能力**：用 `query-css-library.py get <ID> --dependencies` 读取选中 CSS/SVG 正文和依赖，必要结构使用 `template`；未命中时按 Visual System 自行实现并记录原因。
3. **组装完整 HTML**：准确文字进入真实 DOM，复杂自由路径使用内嵌 SVG，所有样式展开为元素行内 `style`。稳定 `id`／`data-layer-id` 直接写在需要定位和编辑的 DOM 上。
4. **测量并锁定画布**：保留 `data-canvas-width` 及 `html`、`body`、唯一作品容器的既定宽度。在最终宽度、真实文字和字体就绪后，按 [DOM 测高](../html-dom-measurement.md) 测量语义内容自然高度与独立页尾安全区的合计高度，向上取整，仅将同一正整数同步到 `data-canvas-height` 和 `html`、`body`、唯一作品容器的 `height`，再以正式固定高度复测。用户已锁定高度时保留该高度，在锁定尺寸内重排并检查溢出，不以测量值擅自覆盖。
5. **检查与闭环**：按 [HTML 检查执行流程](../html-validation.md) 做源码和 `shot.py` 检查；连续长页给顶层区段设置唯一 `data-section-id`，由 shot.py 报告提供实际测量。随后完成预览图 CDN 上传与 Markdown 展示、HTML 上传、顶层 HTML Item 回读和 Workspace 画布卡片交付。
6. **版本规则**：HTML 内容、样式、素材或尺寸变化时修改完整源、重新上传并 `+create` 新 HTML Item；`+update` 只可在协议允许时修正顶层 `brief`／`path`。

原始 `.html` 和本地路径不通过 `present_files` 直接交付；同尺寸完整预览截图按 CDN 上传与 Markdown 图片展示作为必交可视产物。
