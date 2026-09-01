---
name: doubao-visualization
description: 当回答涉及趋势、占比、比较、流程、机制、因果、架构、关系、时间线、状态机、算法步骤、参数变化、原图证据，或用户要求图表、图解、信息图、标注、动态/交互演示时使用。优先用 ECharts、确定性 HTML/SVG 或原图叠加；不承接海报、头像、壁纸、写实图片和艺术插画创作。
---

# 统一可视化

## 概述

本 Skill 将适合图形表达的内容转成可复核、可运行的可视化回复。先判断任务目标和素材性质，再选择最少但足够的呈现模块。

核心原则：

- **精确数据用 ECharts。**
- **原图证据保持原貌。**
- **知识结构优先用确定性 HTML/SVG。**
- **静态图解优先；交互只有在操作或变化能增加理解时启用。**
- **无法可靠画清时回退文字，不用不可复核的图片兜底。**

## 使用场景

满足以下任一条件时进入可视化规划：

- 用户明确要求图表、图解、信息图、流程图、关系图、时间线、结构图、标注、动画或交互。
- 内容包含趋势、占比、排行、分布、相关性或多指标对比。
- 内容包含可准确枚举的阶段、步骤、模块、角色、层级、因果、状态或连接关系。
- 答案依赖用户原图中的对象、位置、数量、区域、路径、匹配或差异。
- 参数变化、算法过程、状态迁移、物理过程或动态几何需要观察过程。

以下情况不使用：

- 简短事实、确认、普通改写、翻译、闲聊或纯文字明显更清楚。
- 用户明确只要文字。
- 海报、头像、壁纸、写实图片、艺术插画或风格化创作。
- 地图、导航、地理轨迹和行政区划展示。
- PDF、PPT、Word、Excel、图片文件等真实附件交付；应使用对应文件能力。

## 核心流程

1. **判断收益**：可视化是否比文字明显更容易理解；否则输出文字。
2. **确定目标**：从 `data_analysis`、`knowledge_explanation`、`visual_evidence`、`dynamic_exploration` 中选择一个主目标，可增加一个必要的辅助目标。
3. **盘点素材**：识别结构化数据、用户原图、文字上下文和已核验资料。
4. **处理原图**：原图是证据时选择 `preserve`；只需提取可观察结构画示意图时选择 `observe_for_schematic`。
5. **选择呈现**：从 `echarts`、`static_image_overlay`、`html_svg`、`text_only` 中选择。
6. **通过加载门**：先完整读取 `references/routing.md`；确定模式后完整读取对应文件组。
7. **准备事实**：真实数字、年份、人物、事件和专业细节必须来自用户材料或合法核验结果。
8. **生成并检查**：检查准确性、结构、移动端、降级和图文一致性。

## 快速路由

```text
用户请求
├─ 准确数值、趋势、占比、排行、分布、相关性 → ECharts
├─ 核心证据来自用户原图
│  ├─ 只需指出位置、区域、路径、数量或匹配 → 原图静态叠加
│  └─ 需要点击、切换、逐步高亮或联动解释 → 保持原图 + HTML/SVG 交互
├─ 流程、机制、架构、关系、时间线、状态机、比较、算法步骤
│  ├─ 静态结构足够 → HTML/SVG 静态信息图
│  └─ 操作或变化本身有解释价值 → HTML/SVG 交互演示
└─ 图示收益不足或无法可靠表达 → 纯文字
```

## 路由硬规则

- **结构可确定就用 HTML/SVG**：流程、机制、架构、关系、时间线和状态机不得因缺少图片创作能力而直接放弃图解。
- **静态默认**：能用一张静态图说明的，不增加无意义按钮、hover 或动画。
- **交互有增益才启用**：点击、拖动、播放、切换或参数变化必须揭示新的状态、因果或过程。
- **证据不可改写**：结论依赖原图真实位置、数量、文字、边界或路径时，必须保持原图。
- **示意必须标明**：根据原图可观察特征自绘的 SVG 只能称为“示意”，不能替代原图事实或精确测量。
- **数据必须可复核**：精确数值、比例、统计关系、坐标和趋势由 ECharts 或确定性 HTML/SVG 承担。
- **地图禁用**：不生成地图、行政区划、经纬度点位、地理轨迹、瓦片地图或 ECharts `geo/map`。
- **允许组合但控制数量**：默认一个主模块；第二模块必须表达独立信息，最多两个 presentation。

## 呈现模式与必读文件

> **强制渐进加载门**：命中某模式后，必须完整读取该行全部文件；组合输出再读取 `references/composition.md`。只做路由时不要提前加载无关文件。

| 呈现模式 | 进入条件 | 输出契约 | 必须完整读取 |
| --- | --- | --- | --- |
| ECharts | 精确数据图表，或用户明确要求 option | Markdown + 一个完整 `echarts` option | `references/mode-echarts.md` → `references/echarts-option-spec.md` → `references/shared-quality.md` |
| 原图静态叠加 | 原图是证据，只需点、框、线、路径或匹配 | 文字答案 + 原图叠加 renderer | `references/mode-image-overlay.md` → `references/image-overlay-process-spec.md` → `references/image-overlay-authoring-spec.md` → `references/shared-quality.md` |
| HTML/SVG | 静态知识图解，或确有增益的动态探索 | 文字结论 + 静态或交互 renderer | 静态：`references/mode-html-svg.md` → `references/renderer-trigger-design.md` → `references/renderer-output-mobile.md` → `references/shared-quality.md`；交互时额外读取 `references/renderer-stability-math.md` → `references/renderer-interaction-geometry.md` |
| 组合输出 | 单一模式遗漏独立核心目标 | 按阅读顺序组合，不重复信息 | `references/composition.md` |

### 加载完成检查

开始生成前在内部确认：

```text
route_decided = true
required_files_loaded = true
output_contract_fixed = true
```

任一项为 false 时，不开始生成。

## 内部规划

执行前形成简短计划，不向用户展示内部字段：

```json
{
  "should_visualize": true,
  "goals": ["knowledge_explanation"],
  "assets": ["text_context"],
  "user_image_policy": "not_applicable",
  "presentations": ["html_svg"],
  "html_svg_behavior": "static",
  "required_files": [
    "references/mode-html-svg.md",
    "references/renderer-trigger-design.md",
    "references/renderer-output-mobile.md",
    "references/shared-quality.md"
  ],
  "required_files_loaded": true,
  "facts_status": "user_provided",
  "reason": "流程节点和顺序可以被确定性图形准确表达"
}
```

完整字段与组合约束见 `references/routing.md` 和 `schemas/visualization-plan.schema.json`。

## 统一输出要求

- 先给核心结论，再给可视化和必要解读。
- 说明数据来源、事实口径、示例属性或“示意”性质。
- 原图证据优先于数据图表；数据图表优先于辅助知识图解。
- HTML/SVG 初始静态状态必须可读，核心答案不依赖 hover 或脚本。
- 外部库、图片或脚本失败时保留文字和静态主结构，不能空白。
- 工具或资源不可用时说明限制，不猜测私有接口，不绕过鉴权。

## 安全与事实边界

- 不编造统计数据、股价、财报、病例、排名、年份、人物身份、事件顺序或来源。
- 不在输出、HTML 或日志中回显 token、cookie、AK/SK、JWT、私钥或无关个人信息。
- 用户原图包含敏感信息时，只标注完成任务所需区域。
- 医疗、工程、金融等高风险图示只能辅助说明，不替代专业判断。
- 自绘示意不能暗示未经证实的因果、精度、官方结构或科学测量结果。

## 参考文件

- `references/routing.md`：每次使用必读；负责目标、素材、模式、组合和降级。
- `references/shared-quality.md`：每次输出必读；负责事实、移动端、可访问性和降级。
- `references/mode-echarts.md`：精确数据图表。
- `references/mode-image-overlay.md`：保持原图的静态证据标注。
- `references/mode-html-svg.md`：静态信息图和交互演示。
- `references/echarts-option-spec.md`：ECharts option 与移动端细则。
- `references/image-overlay-process-spec.md`、`references/image-overlay-authoring-spec.md`：原图叠加 process 与 renderer 细则。
- `references/renderer-trigger-design.md`、`references/renderer-output-mobile.md`：静态和交互 HTML/SVG 共用的设计与移动端规则。
- `references/renderer-stability-math.md`、`references/renderer-interaction-geometry.md`：只在 `html_svg_behavior=interactive` 时额外读取的稳定性、动态公式、几何和交互规则。
- `references/composition.md`：多模式组合。
- `references/tool-contracts.md`：搜索、事实核验和 renderer 能力。
- `examples/routing-cases.md`：触发、不触发、边界和组合案例。
- `examples/image-overlay-gold-process.md`、`examples/image-overlay-gold-reply.md`：原图标注实现参考。
- `schemas/visualization-plan.schema.json`：内部规划 Schema。
- `scripts/validate_skill.py`：本地结构与边界校验。
