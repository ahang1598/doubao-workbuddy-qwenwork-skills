# 纯 Coding 步骤

> 先按主 SKILL 判断交付环境。system 上下文明确标记为移动端交付时遵循 [Mobile 直接交付](../mobile-app-direct-delivery.md)：Brief／素材记录留在本地，跳过本文全部 Workspace、Canvas CLI、Item 与卡片步骤，媒体逐项直接交付、HTML 预览走 CDN＋Markdown。其他环境执行本文默认 Canvas 分支。生产与编辑顺序不变。

用于主 `SKILL.md` 已选定 pure-coding 路线、可以完全由真实资产、准确文字、HTML/CSS 与内嵌 SVG 表达的设计。选定的父路线在本次任务中保持不变；不得因素材现成、代码可实现或实现方便，将 ai-coding 的新建、整体重做或局部修改改判为 pure-coding。用户明确要求全部由图像模型生成且不要 HTML 排版的长图／详情页属于主入口的 pure-image 例外，不进入本流程。

## 规则应用顺序

1. 按主 `SKILL.md` 完成命中规则的前置读取，再创建或更新唯一 Brief，记录已知需求与待补项。
2. 有上传参考图或模板时应用 [参考图解析与继承](../../style/coding/ai-coding/reference-analysis.md)，把过滤后的观察与目标重建方案写回同一 Brief。
3. 应用当前品类 Spec 与 Visual System；无专属规则时按 [通用视觉规则](../../style/coding/generic-visual-fallback.md) 完善内容，字体按公共选型与资源规则处理。
4. Visual 草案后按 `ref_key` 和实际效果职责先比较同品类、同作用范围的 CSS 组合并适配真实内容，再用 CSS／SVG 原子补足或替换局部；确无适用组合时才转原子组装或自行实现。最终 Brief 冻结后读取选中实现正文与依赖。
5. 直接按 [Brief → HTML 组装](../html-assembly.md) 编写完整固定画布 HTML。纯 Coding 不创建 `asset-manifest.json`、素材参数副本、字体计划副本或手填几何投影。
6. 编码、实际 DOM 几何、预览、上传和平台写入服从 [HTML/CSS 固定画布与交付协议](../../html/coding-rendering.md)。

## Brief → HTML

1. **冻结自然语言 Brief**：确认最终可见文案、内容顺序、参考继承范围、主焦点、图文关系和内容容量。
2. **读取实现能力**：用 `query-css-library.py get <ID> --dependencies` 读取选中 CSS 正文和依赖，必要结构使用 `template`；静态 SVG 按主入口的读取规则使用。未命中时按 Visual System 自行实现并记录原因。
3. **组装完整 HTML**：准确文字进入真实 DOM，复杂自由路径使用内嵌 SVG，样式按 HTML 协议组织。稳定 `id`／`data-layer-id` 直接写在需要定位和编辑的 DOM 上。
4. **测量与预览**：HTML 完成后按 [预览流程](../html-preview.md) 运行一次 shot.py，取得自然高度、固定画布复核和截图。未锁高时仅在确需改高后同步四处高度并重跑；锁高时在原尺寸内重排。
5. **检查与闭环**：按 [HTML 检查执行流程](../html-validation.md) 复核源码、上一步的报告与截图；连续长页给顶层区段设置唯一 `data-section-id`，由 shot.py 报告提供实际测量。随后完成预览图 CDN 上传与 Markdown 展示、HTML 上传、顶层 HTML Item 回读、产后目录整理和 Workspace 画布卡片交付。
6. **版本规则**：HTML 内容、样式、素材或尺寸变化时修改完整源、重新上传并 `+create` 新 HTML Item；`+update` 只可在协议允许时修正顶层 `brief`／`path`。

默认 Canvas 环境通过 HTML Item 画布卡片交付可编辑作品；原始 HTML 文件及其上传链接仅用于平台写入。同尺寸完整预览图在 Canvas 与 Mobile 环境均通过 CDN＋Markdown 展示，Mobile 不执行平台写入或卡片交付。
