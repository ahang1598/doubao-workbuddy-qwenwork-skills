---
name: doubao-visualization
description: 当回答涉及趋势、占比、比较、流程、机制、因果、架构、关系、时间线、状态机、算法步骤、参数变化、原图证据、地理空间关系，或用户明确要求图表、图解、知识配图、标注、地图、动态/交互演示时使用。优先用 ECharts、带renderer标签的确定性 HTML/SVG或原图叠加；解释性知识配图和原图参考重绘可用生成式知识配图；地图由包内 map-create 能力承接；不承接附件交付、海报、头像、写实图片和纯艺术插画。
---

# 统一可视化

将适合图形表达的内容转成可复核、可运行的可视化回复。只选择能明显增加理解的最少模块。

## 路由

按顺序判断，首次命中即确定分支或主模式；`text_only` 无需加载绘制分支：

1. **图示是否明显优于文字？** 否，或用户明确只要文字 → `text_only`。
2. **核心是否是可准确枚举的流程、机制、架构、关系、时间线、状态或算法过程？** 是 → `html_svg`。
3. **结论是否依赖用户原图的真实位置、数量、边界、路径或匹配？** 是 → `static_image_overlay`。
4. **核心是否是精确数值的趋势、占比、排行、分布、相关性或多指标比较？** 是 → `echarts`。
5. **核心是否需要解释性插画、视觉隐喻或明确允许的原图参考重绘？** 是，且不要求精确连线、逐字文字或交互 → `generated_illustration`；普通可枚举知识结构继续下一步。
6. **是否需要地理底图承载核心信息？** 真实位置、空间分布、距离方位、路线、区域或地理形态有助于理解与决策时 → `map-create`，不要求用户明确说“地图”。仅提到地名、只比较数值，或仅在原图上圈注且无需地理定位时继续后续判断。
7. 结构或事实不足以可靠绘制 → `text_only`。

用户明确要求 ECharts/option 且不需要地理底图时直接选择 `echarts`；地图需求仍使用包内 `map-create`。原图仅用于观察结构且用户要简化示意时，选择 `html_svg` 并标明“示意”，不得替代原图证据。
地图分支完整读取 `map-create/SKILL.md`，复用用户原始请求、已有数据和约束，以 `map-create/` 为 `SKILL_DIR`，其引用和脚本路径均相对此目录解析，任务输入与输出放在本次工作目录。地图的执行、验收、交付与失败处理遵循该入口；下文的非地图计划、呈现、组合及 HTML 编写规则不传递给地图分支。

## 不使用

- 简短事实、确认、普通改写、翻译、闲聊或纯文字已足够清楚。
- 海报、头像、壁纸、写实图片、纯艺术插画或与知识讲解无关的风格化创作。
- PDF、PPT、Word、Excel、图片文件等真实附件交付；使用对应文件能力。

## 硬规则

- **证据保真**：依赖原图事实时保持原图像素内容、对象位置和比例；示意图必须显式标明“示意”。
- **数据可复核**：真实数字、年份、人物、事件和专业细节只来自用户材料或合法核验结果；示例数据必须明确标注。
- **数据不可生图**：精确数据由对应确定性分支承载；地理坐标与几何使用 `map-create`，生成图只作解释性示意。
- **地图路由**：地图仅由包内 `map-create` 承接；其他模式仍禁止绘制地图和使用 ECharts `geo/map`。

以下呈现规则仅适用于非地图分支；地图按其入口处理，正文仍须完整回答用户问题：

- **静态默认**：交互必须揭示新的状态、因果、参数变化或证据，不能只做装饰动画或 hover 高亮。
- **模式单一**：默认一个主模块。只有第二模块回答独立核心问题时才组合，最多两个；生成式多图确需更多时按章节拆分。
- **初始可读**：核心结论先用文字和初始静态状态表达，不依赖 hover、脚本或外部库。
- **失败可降级**：复杂交互 → 静态 HTML/SVG → 结构化文字；任何失败都不能留下空白。

## 按需加载

选定绘制分支后，先完整读取对应入口，再按其要求加载当前任务所需依赖；已读取的不重复读取，不预读无关分支。

| 分支 / 主模式 | 基础必读 | 追加读取条件 |
| --- | --- | --- |
| `echarts` | `references/mode-echarts.md` | 复杂 callback、自由布局、特殊数据格式或移动端密集布局 → `references/echarts-option-spec.md`；system 的 `Device platform` 明确为电脑端/网页端 → `references/echarts-web-pc-spec.md`；该分支选择 Sunburst/Gauge → 再读对应 `references/echarts-web-pc-sunburst-reference.md` / `references/echarts-web-pc-gauge-reference.md` |
| `static_image_overlay` | `references/mode-image-overlay.md` | 仅“单图 + 单 step + 总 coord 数 ≤2 + 无图例/避让”可只读主文件；总 coord 数 ≥3、steps ≥2、多图，或需要路径、多组配对、计数、图例、标签避让时 → 同时读取 `references/image-overlay-process-spec.md`、`references/image-overlay-authoring-spec.md` |
| `html_svg` 静态 | `references/mode-html-svg.md` | 高密度排版、专用库或特殊视觉设计 → `references/renderer-trigger-design.md`；明确移动端复杂布局 → `references/renderer-output-mobile.md` |
| `html_svg` 交互 | `references/mode-html-svg.md` | 脚本、动画、动态公式 → `references/renderer-stability-math.md`；拖拽、播放、几何约束、DOM/ECharts 联动 → `references/renderer-interaction-geometry.md` |
| `generated_illustration` | `references/mode-generated-illustration.md` | 本分支必须再完整读取 `references/generated-prompt-rules.md`、`references/generated-style-guide.md`、`references/generated-tool-contracts.md`、`references/shared-quality.md` |
| 地图 `map-create` | `map-create/SKILL.md` | 后续参考与数据协议按该入口的读取要求加载；不套用下列非地图分支的依赖或通用降级规则 |
| 非地图组合输出 | 各主模式文件 | 再读 `references/composition.md`；地图不参与此组合协议 |

根目录的 `references/routing.md` 用于路由审计；`references/shared-quality.md`、`references/tool-contracts.md` 用于非地图分支审计或能力不确定时参考，生成式分支按表必读。根目录的 `examples/`、`schemas/` 和 `scripts/` 只服务开发与回归；`map-create/` 内的脚本与协议是地图运行依赖，由其入口管理。

## 最小内部计划

仅非地图分支使用以下计划；地图使用子入口的任务输入，不填写本计划的 `mode` 或 `secondary`：

```json
{
  "mode": "html_svg",
  "behavior": "static",
  "source": "user_content",
  "secondary": null
}
```

- `mode`：`text_only`、`echarts`、`static_image_overlay`、`html_svg`、`generated_illustration`。
- `behavior`：仅 `html_svg` 使用 `static` 或 `interactive`，其他模式为 `not_applicable`。
- `source`：`user_content`、`user_image`、`verified`、`example`、`insufficient`。
- `secondary`：无组合时为 `null`，否则填写第二模式。

## 输出协议

地图：执行 `map-create/SKILL.md` 的验收与交付规则，正常回答后在末尾原样附上成功产物的唯一 renderer；不手工添加标题、重包 HTML 或追加其他可视化模块。以下格式示例、HTML 网页标题及分模式编写要求仅适用于非地图输出。

- **HTML renderer 格式硬约束**：最终回复中的每个 HTML renderer 块，起始行必须逐字为 ` ```html type="renderer" `，结束行必须为 ` ``` `，两者均独占一行，HTML 代码完整置于其间。不得使用裸 HTML、普通 `html`/`svg` 代码块或其他包裹格式；原生 `echarts` option 不适用。

renderer 输出格式范例：

```html type="renderer"
<html style="margin:0;padding:0;">
<meta charset="utf-8">
<title>按主题填写的页面标题</title>
按任务生成的可视化内容
</html>
```
- 示例中的标题、节点和文案只是占位，不是默认模板；最终输出必须根据当前任务重新命名和绘制。

### HTML 网页标题

适用于非地图 HTML renderer，包括 HTML/SVG、原图叠加及 renderer 内嵌图表；原生 `echarts` option 不适用。

- **初始源码带标题**：首个 renderer 块必须包含 `<meta charset="utf-8">` 和一个非空的 HTML 文档级 `<title>`，用于后续发布网页时的浏览器标签页和书签命名。依次写在 `<html ...>` 后、透明根 `<div>` 前，继续省略显式 `<head>`/`<body>`；同一文档只写一个，后续 renderer 片段不重复。
- **按内容命名**：优先采用用户指定的网页标题或名称，否则根据核心主题拟定简短、具体、与页面语言一致的标题，如 `二分查找过程演示`。避免 `Untitled`、`HTML 页面`、`可视化` 等泛化占位名；编辑已有 HTML 时补全缺失或空白的标题，主题改变时同步更新。
- **使用正确的标题元素**：可见标题、SVG 内的 `<title>` 和 ECharts `title.text` 都不能替代 HTML 文档级 `<title>`；不依赖 JavaScript 才设置标题。

### ECharts

输出一句数据口径、一个完整小写 `echarts` option 和必要结论。不得输出 `const option =`、初始化代码、HTML、CSS、DOM 或 renderer 包裹。

### 原图叠加

先给文字答案，末尾输出一个以真实 HTTPS 原图为底的 ` ```html type="renderer"`。简单点、框、箭头保持静态；只有用户要求或密集标记确有收益时增加 click/tap。

### HTML/SVG

先给结论，再输出 ` ```html type="renderer"`。静态结构不添加无意义脚本；交互必须有即时反馈并支持 click/tap，动画可暂停、可重置。

### 生成式知识配图

先形成正文与配图计划，再按当前工具 schema 生成；图片紧跟对应段落并标明“解释性图解”，不套 renderer。工具不可用或重试后仍失败时，保留文字；结构可准确表达时可改用静态 HTML/SVG。

## 交付检查

- 发送前检查实际最终回复：每个 HTML renderer 块是否使用上述起始行和结束行？不符则先修正再发送，不能仅在内部计划中确认。
- 图形是否确实增加理解，且模式与素材性质匹配？
- HTML 初始源码是否包含唯一、非空、与主题相符的文档级 `<title>`？
- 数据、术语、单位、时间范围和来源是否一致？
- 原图证据是否保持原貌，示意性质是否明确？
- 文字、节点、连线、图例在窄屏是否无重叠、裁切和溢出？
- 外部资源或脚本失败时，是否仍有可理解答案？
- 是否误用了地图、虚构事实，或用 renderer 冒充附件？

## 文件职责

- `map-create/SKILL.md`：地图分支入口，管理其目录内的参考、数据协议、执行脚本及验收交付。
- 根目录 `references/`：非地图分支运行规范及主入口路由参考，按加载表和分支入口读取。
- `examples/routing-cases.md`：路由与加载回归案例。
- `schemas/visualization-plan.schema.json`：仅非地图分支的最小内部计划 Schema。
- `scripts/validate_skill.py`：结构、路由与加载预算校验。
