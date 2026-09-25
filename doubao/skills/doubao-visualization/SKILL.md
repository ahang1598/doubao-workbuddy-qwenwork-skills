---
name: doubao-visualization
description: 当回答涉及趋势、占比、比较、流程、机制、因果、架构、关系、时间线、状态机、算法步骤、参数变化、原图证据，或用户明确要求图表、图解、标注、动态/交互演示时使用。优先用 ECharts、带renderer标签的确定性 HTML/SVG或原图叠加；不承接地图、附件交付、海报、头像、写实图片和艺术插画。
---

# 统一可视化

将适合图形表达的内容转成可复核、可运行的可视化回复。只选择能明显增加理解的最少模块。

## 路由

按顺序判断，首次命中即确定主模式：

1. **图示是否明显优于文字？** 否，或用户明确只要文字 → `text_only`。
2. **结论是否依赖用户原图的真实位置、数量、边界、路径或匹配？** 是 → `static_image_overlay`。
3. **核心是否是精确数值的趋势、占比、排行、分布、相关性或多指标比较？** 是 → `echarts`。
4. **核心是否是可准确枚举的流程、机制、架构、关系、时间线、状态或算法过程？** 是 → `html_svg`。
5. 结构或事实不足以可靠绘制 → `text_only`。

用户明确要求 ECharts/option 时直接选择 `echarts`。原图仅用于观察结构且用户要简化示意时，选择 `html_svg` 并标明“示意”，不得替代原图证据。

## 不使用

- 简短事实、确认、普通改写、翻译、闲聊或纯文字已足够清楚。
- 海报、头像、壁纸、写实图片、艺术插画或风格化创作。
- 地图、导航、地理轨迹、行政区划、经纬度点位或地图热力。
- PDF、PPT、Word、Excel、图片文件等真实附件交付；使用对应文件能力。

## 硬规则

- **静态默认**：交互必须揭示新的状态、因果、参数变化或证据，不能只做装饰动画或 hover 高亮。
- **证据保真**：依赖原图事实时保持原图像素内容、对象位置和比例；示意图必须显式标明“示意”。
- **数据可复核**：真实数字、年份、人物、事件和专业细节只来自用户材料或合法核验结果；示例数据必须明确标注。
- **模式单一**：默认一个主模块。只有第二模块回答独立核心问题时才组合，最多两个。
- **初始可读**：核心结论先用文字和初始静态状态表达，不依赖 hover、脚本或外部库。
- **失败可降级**：复杂交互 → 静态 HTML/SVG → 结构化文字；任何失败都不能留下空白。
- **地图禁用**：所有模式禁止地图和 ECharts `geo/map`。

## 按需加载

确定主模式后，先完整读取一个主文件；只有出现右侧复杂特征时才追加专项文件。不要预读无关文件。

| 主模式 | 基础必读 | 出现以下特征时追加读取 |
| --- | --- | --- |
| `echarts` | `references/mode-echarts.md` | 复杂 callback、自由布局、特殊数据格式或移动端密集布局 → `references/echarts-option-spec.md`；system 的 `Device platform` 明确为电脑端/网页端 → `references/echarts-web-pc-spec.md`；该分支选择 Sunburst/Gauge → 再读对应 `references/echarts-web-pc-sunburst-reference.md` / `references/echarts-web-pc-gauge-reference.md` |
| `static_image_overlay` | `references/mode-image-overlay.md` | 仅“单图 + 单 step + 总 coord 数 ≤2 + 无图例/避让”可只读主文件；总 coord 数 ≥3、steps ≥2、多图，或需要路径、多组配对、计数、图例、标签避让时 → 同时读取 `references/image-overlay-process-spec.md`、`references/image-overlay-authoring-spec.md` |
| `html_svg` 静态 | `references/mode-html-svg.md` | 高密度排版、专用库或特殊视觉设计 → `references/renderer-trigger-design.md`；明确移动端复杂布局 → `references/renderer-output-mobile.md` |
| `html_svg` 交互 | `references/mode-html-svg.md` | 脚本、动画、动态公式 → `references/renderer-stability-math.md`；拖拽、播放、几何约束、DOM/ECharts 联动 → `references/renderer-interaction-geometry.md` |
| 组合输出 | 各主模式文件 | 再读 `references/composition.md` |

`references/routing.md`、`references/shared-quality.md`、`references/tool-contracts.md` 是设计、审计和能力不确定时的参考，不是正常任务必读。`examples/`、`schemas/` 和 `scripts/` 只服务开发与回归。

## 最小内部计划

只需在内部确定：

```json
{
  "mode": "html_svg",
  "behavior": "static",
  "source": "user_content",
  "secondary": null
}
```

- `mode`：`text_only`、`echarts`、`static_image_overlay`、`html_svg`。
- `behavior`：仅 `html_svg` 使用 `static` 或 `interactive`，其他模式为 `not_applicable`。
- `source`：`user_content`、`user_image`、`verified`、`example`、`insufficient`。
- `secondary`：无组合时为 `null`，否则填写第二模式。

## 输出协议

- **HTML renderer 格式硬约束**：最终回复中的每个 HTML renderer 块，起始行必须逐字为 ` ```html type="renderer" `，结束行必须为 ` ``` `，两者均独占一行，HTML 代码完整置于其间。不得使用裸 HTML、普通 `html`/`svg` 代码块或其他包裹格式；原生 `echarts` option 不适用。

renderer 输出格式范例：

```html type="renderer"
<html style="margin:0;padding:0;">
<title>按主题填写的页面标题</title>
按任务生成的可视化内容
</html>
```
- 示例中的标题、节点和文案只是占位，不是默认模板；最终输出必须根据当前任务重新命名和绘制。

### HTML 网页标题

适用于所有 HTML renderer，包括 HTML/SVG、原图叠加及 renderer 内嵌图表；原生 `echarts` option 不适用。

- **初始源码带标题**：首个 renderer 块必须包含一个非空的 HTML 文档级 `<title>`，用于后续发布网页时的浏览器标签页和书签命名。直接写在 `<html ...>` 后、透明根 `<div>` 前，继续省略显式 `<head>`/`<body>`；同一文档只写一个，后续 renderer 片段不重复。
- **按内容命名**：优先采用用户指定的网页标题或名称，否则根据核心主题拟定简短、具体、与页面语言一致的标题，如 `二分查找过程演示`。避免 `Untitled`、`HTML 页面`、`可视化` 等泛化占位名；编辑已有 HTML 时补全缺失或空白的标题，主题改变时同步更新。
- **使用正确的标题元素**：可见标题、SVG 内的 `<title>` 和 ECharts `title.text` 都不能替代 HTML 文档级 `<title>`；不依赖 JavaScript 才设置标题。

### ECharts

输出一句数据口径、一个完整小写 `echarts` option 和必要结论。不得输出 `const option =`、初始化代码、HTML、CSS、DOM 或 renderer 包裹。

### 原图叠加

先给文字答案，末尾输出一个以真实 HTTPS 原图为底的 ` ```html type="renderer"`。简单点、框、箭头保持静态；只有用户要求或密集标记确有收益时增加 click/tap。

### HTML/SVG

先给结论，再输出 ` ```html type="renderer"`。静态结构不添加无意义脚本；交互必须有即时反馈并支持 click/tap，动画可暂停、可重置。

## 统一交付检查

- 发送前检查实际最终回复：每个 HTML renderer 块是否使用上述起始行和结束行？不符则先修正再发送，不能仅在内部计划中确认。
- 图形是否确实增加理解，且模式与素材性质匹配？
- HTML 初始源码是否包含唯一、非空、与主题相符的文档级 `<title>`？
- 数据、术语、单位、时间范围和来源是否一致？
- 原图证据是否保持原貌，示意性质是否明确？
- 文字、节点、连线、图例在窄屏是否无重叠、裁切和溢出？
- 外部资源或脚本失败时，是否仍有可理解答案？
- 是否误用了地图、虚构事实，或用 renderer 冒充附件？

## 文件职责

- `references/mode-echarts.md`：常规 ECharts 的完整运行契约。
- `references/echarts-web-pc-spec.md`：仅明确电脑端/网页端时使用的宽屏矮画布适配。
- `references/echarts-web-pc-sunburst-reference.md`、`references/echarts-web-pc-gauge-reference.md`：仅 Web/PC 已选择对应图形时读取。
- `references/mode-image-overlay.md`：简单原图标注的完整运行契约。
- `references/mode-html-svg.md`：静态 HTML/SVG 和基础交互的完整运行契约。
- 其他 `references/`：只处理表格中列出的复杂特征。
- `examples/routing-cases.md`：路由与加载回归案例。
- `schemas/visualization-plan.schema.json`：最小内部计划 Schema。
- `scripts/validate_skill.py`：结构、路由与加载预算校验。
