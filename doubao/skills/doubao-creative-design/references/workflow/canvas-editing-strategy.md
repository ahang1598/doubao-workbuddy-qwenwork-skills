# HTML 画布编辑执行策略

> 先按主 SKILL 判断交付环境。system 明示 `Device platfrom: Mobile` 时遵循 [Mobile 直接交付](mobile-app-direct-delivery.md)：Brief／素材记录留在本地，跳过本文全部 Workspace、Canvas CLI、Item 与卡片步骤，媒体逐项直接交付、HTML 预览走 CDN＋Markdown。其他环境执行本文默认 Canvas 分支。生产与编辑顺序不变。

用于编辑 Canvas Workspace 中已有的顶层 HTML Item。HTML 内容变化采用新版本创建语义；本文件不授权把 HTML 改成 Frame、成员 Item 或压平图片。

## 1. 读取与定位

1. 绑定当前 `canvas_workspace_id`，用 `+tree → +ls → +get` 定位目标顶层 HTML Item；禁止使用尚未实现的 `find`。
2. 回读并核对 `item_id`、`type=HTML`、`path`、`title`、`brief`、`size` 与 `<asset url>`，取得该短链对应的完整 `.html` 源文件。没有完整源文件时不得根据截图重建后声称是原位编辑。
3. 解析唯一作品根容器、`data-canvas-width`／`data-canvas-height`、稳定 DOM `id`／`data-layer-id`、素材 URL、真实文本和行内样式；将其与同版本 Brief、最终 HTML 和资产清单对齐。

## 2. 授权边界

- 目标和修改已明确：只改授权的 DOM 元素、文本、素材、样式或关系，并重查受影响邻居。
- 目标或修改意图不明确：先说明当前识别到的目标和拟修改范围，取得确认后再改。
- 用户提供模板、参考图或要求同款：先读 [模板改写](template-rewrite.md) 与 [参考图解析](../style/coding/ai-coding/reference-analysis.md)，把获准继承内容写入同一自然语言 Brief。
- 未授权 DOM、文案、身份资产、画布尺寸和交互保持不变。无法唯一匹配目标时停止确认，不按视觉相似度猜元素。

## 3. Brief 与素材清单 更新

Brief 只用自然语言增量记录“为什么改、改成什么、哪些不变、最终画面应看到什么”，不补模板 ID、坐标、色值表或机器校验字段。最终 HTML 记录具体元素 ID、几何、CSS／SVG 引用、资产版本、消费者和受影响验收项。

涉及品类或视觉效果变化时，从 [`assets/templates/ref-bindings.json`](../../assets/templates/ref-bindings.json) 解析 `ref_key`，再查 CSS／SVG catalog；已有实现可复用时读取正文与依赖，不按名字盲抄。普通测量和参数修正回写 HTML，不把实现偏差改写成 Brief 目标。

## 4. 艺术字接入方式与原位回贴

HTML 编辑中若需要新生成或重新生成独立艺术字，必须按最终消费者选择接入方式；该分流与新建流程一致：

1. 从目标 DOM 与 Brief 读取准确源文字、原位置、消费者、视觉职责和允许修改范围；无法唯一定位目标时先确认。
2. 只用于已知、稳定的 HTML 背景时可选 `blend`：深色字体使用纯白背景，浅色字体使用纯黑背景；不得使用渐变、纹理或近似色背景。需要透明导出、跨多个背景复用、背景未知或严格保色时选 `alpha-cutout`：使用高反差均匀纯色底并执行真实抠图。
3. 生成源图完成 `design-cli` 写入／`+get` 回读与 `present_files` 交付；选择抠图时，抠图结果作为新的媒体结果继续完成同一双通道闭环。
4. 逐字检查文字准确性，并核验字面、裁边和实际显示尺寸；混合路线检查背景纯度、真实背景融合与对比度，抠图路线检查 Alpha、内部孔洞及深浅底边缘。未通过时不得回贴。
5. 使用所选路径最终准出的 HTTP(S) 短链替换完整 HTML 中原艺术字节点，保留未授权 DOM、容器、层级、画布尺寸和相邻内容。混合路线中深色字体图片节点设置行内 `mix-blend-mode: multiply`，浅色字体图片节点设置行内 `mix-blend-mode: screen`，不得放到父容器或整页；抠图路线使用透明 PNG 且不附加混合模式。回贴后在完整实际背景上检查融合／透明边缘、可读性和层叠关系。Base64、本地路径、预览地址或接入方式与最终文件不匹配的版本禁止进入 HTML。

## 5. 完整文档修改与新版本

1. 在完整源文件中修改目标，保留 `<!DOCTYPE html>`、固定画布根属性、三层一致尺寸和所有未授权内容。
2. 所有视觉样式仍为元素行内 `style`；准确文字仍是真实 DOM 文本；复杂自由路径才使用内嵌 SVG。
3. 按 [HTML 组装](html-assembly.md)、[固定画布协议](../html/coding-rendering.md) 和 [HTML 检查](html-validation.md) 验证完整文档。
4. 用 `FileBatchUpload` 上传新 `.html`，再 `design-cli design-workspace +create` 一个不带旧对象 ID 的顶层 HTML Item；创建 XML 的 `<source_ids>` 记录经 `+get` 核验的旧 HTML Item ID，并立即 `+get` 回读新对象。保存旧、新 Item ID 和版本关系。
5. `+update`／`+update-batch` 只可在协议允许时修正顶层 `brief`／`path`，不能替换 HTML、资产短链、标题或尺寸。禁止 `<frame type="HTML">`。

`shot.py` 失败或不可用时记录真实未验证范围，但继续上传、创建和回读；不得以截图、路径或代码片段代替平台闭环。
