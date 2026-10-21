# 纯 Coding 再编辑

> 先按主 SKILL 判断交付环境。system 明示 `Device platfrom: Mobile` 时遵循 [Mobile 直接交付](../mobile-app-direct-delivery.md)：Brief／素材记录留在本地，跳过本文全部 Workspace、Canvas CLI、Item 与卡片步骤，媒体逐项直接交付、HTML 预览走 CDN＋Markdown。其他环境执行本文默认 Canvas 分支。生产与编辑顺序不变。

用于只修改已有 HTML 的真实文本、HTML 结构、CSS 或内嵌 SVG，且不需要生成／编辑图片资产的任务。

1. 先按 [HTML 画布编辑策略](../canvas-editing-strategy.md) 取得完整源、锁定目标和授权范围。
2. 在同一自然语言 Brief 中写明修改意图、保留项和可见验收结果；参数、CSS/SVG ID 与几何只写入 最终 HTML。
3. 若改变品类效果或组件机制，按 `ref-bindings.json → CSS/SVG catalog → 实现正文与依赖` 重新匹配受影响部分；未变化部分沿用原实现。
4. 只修改目标 DOM 及其必要邻居，准确文字保留为真实文本节点，沿用已有样式组织方式。禁止输出补丁片段、压平图片或 HTML Frame。
5. 对完整文档执行 [HTML 检查](../html-validation.md)，有当前版本合格的同尺寸完整预览时，将预览图上传 CDN、核验公网链接并以 Markdown 图片展示（截图仅按上述预览方式展示，不创建 IMAGE Item）；默认 Canvas 按独立门禁上传并 `+create` 新顶层 HTML Item，创建 XML 的 `<source_ids>` 记录经 `+get` 核验的旧 HTML Item ID，立即 `+get` 回读新对象，最后将同一 Workspace ID 与刚回读的 HTML Item ID 拼成 `<workspace_id>?item_id=<item_id>` 单值交给 `present_files` 输出对应卡片。退出码、失败处理与交付完成条件遵循 [HTML 预览](../html-preview.md)。旧 Item 保留，`+update` 不能修改内容。
