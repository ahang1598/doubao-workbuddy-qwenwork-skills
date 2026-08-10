---
name: doubao-visualization
description: 当用户要求可视化、画图、图解、配图、信息图、趋势图、数据对比、原图标注、圈选连线、路径轨迹、动态图、动画讲解、交互演示、参数变化、关系图、流程图、时间线、结构图、知识科普或作品解读时使用；也用于判断图表、用户原图叠加、HTML/SVG 交互、基于原图二次生成或纯文字哪种表达最合适。地图、附件导出或纯文字明显更清楚时不强行可视化。
---

# 统一可视化

## 概述

将可视化视为“任务目标 × 素材策略 × 呈现方式”的组合，而不是在四种旧模式中机械四选一。先判断用户想讲清什么，再判断用户原图、数据和资料应如何使用，最后选择一个或多个互补的可视化模块。

核心原则：**精确信息用确定性渲染，原图证据保持原貌，生成图只负责解释，交互只在变化本身有价值时使用。**

## 使用场景

使用该 Skill 当用户明确要求画图、图解、配图、图表、标注、动画或交互，或者任务虽未明说“可视化”，但包含精确数据关系、原图视觉证据、需要观察的动态变化、复杂知识结构等明显适合图示的内容。

不要使用该 Skill 当纯文字明显更清楚、用户明确不要图，或任务核心是地图展示、真实附件生成、普通改写翻译和无需图形的简短问答。

## 核心流程

1. **判断收益**：用户明确要求可视化时默认触发；用户未明说，但任务涉及趋势、占比、视觉证据、动态变化或复杂知识结构且图示明显增益时也触发。文字已经足够时只回答文字。
2. **确定目标**：从 `数据分析`、`知识讲解`、`视觉证据`、`动态探索` 中选择一个主目标，可增加一个确有必要的辅助目标。
3. **盘点素材**：识别结构化数据、用户原图、文字资料和已核验资料。涉及用户原图时，必须判断是 `保持原图` 还是 `仅作生成参考`。
4. **选择呈现**：在 `ECharts`、`原图静态叠加`、`HTML/SVG 交互`、`生成式知识配图`、`纯文字` 中选择最少但足够的模块。用户明确指定合法格式时优先服从。
5. **通过加载门**：先读取 `references/routing.md` 完成路由；确定 presentation 后，必须完整读取下方对应的“模式文件组”，再开始写 option、HTML、process 或图片 Prompt。未读取对应深层规范不得生成。不要无条件读取四组全部文件。
6. **准备事实**：真实数据、年份、人物、事件、医学或工程细节必须来自用户材料或合法核验结果。无法核验时降级为空态、模板、取数方案或明确标注的示例，不编造。
7. **生成并检查**：按选定模式输出，检查准确性、移动端可读性、资源可用性、交互降级和图文对应。只重试或修复失败模块。

## 快速路由

```text
用户请求
├─ 核心是准确数值、趋势、占比、排行或分布 → ECharts
├─ 核心证据来自用户原图
│  ├─ 原图必须保持不变
│  │  ├─ 只需指出位置、区域、路径或匹配 → 原图静态叠加
│  │  └─ 需要点击、切换、播放或联动解释 → 原图 + HTML/SVG 交互
│  └─ 允许解释性重绘 → 原图作为参考，生成知识配图
├─ 核心是参数变化、算法步骤、状态迁移或动态几何 → HTML/SVG 交互
├─ 核心是概念、机制、流程、历史、角色关系或作品解读 → 生成式知识配图
└─ 可视化收益不足 → 纯文字
```

以上分支可以组合。例如“基于设备照片点击部件查看原理”使用 `保持原图 + HTML 交互`；“把产品照片重绘成剖面知识图”使用 `原图作参考 + 生成式配图`；“照片讲结构并展示参数变化”可使用 `原图交互 + ECharts`。

## 路由硬规则

- **用户格式优先**：明确要求 ECharts option、在原图上标注、交互演示或生成配图时，优先采用对应合法格式。
- **证据不可重绘**：当结论依赖用户原图中的真实位置、数量、边界、文字或路径时，保留原图；不得用生成图替代证据。
- **数据不可生图**：精确数值、比例、统计关系、坐标和可复核趋势不得交给生成式图片承担。
- **生成图不是证明**：参考原图生成的图片必须称为解释性重绘或示意图，不称为原图、官方图、精确结构图或事实证据。
- **交互必须有因果价值**：仅当点击、拖动、播放、切换或参数变化能增加理解时使用交互；不要把静态内容包装成无意义按钮。
- **允许组合但控制数量**：默认一个主模块；复杂任务最多加入必要的辅助模块。每个模块必须表达不同信息。
- **地图禁用**：不生成地图、行政区划、经纬度点位、地理轨迹、瓦片地图或 ECharts `geo/map`；改用文字、列表、非地图流程或取数方案。
- **附件另行处理**：PDF、PPT、Word、Excel、图片文件等真实附件交付必须使用对应文件能力，不用 renderer 冒充文件。

## 呈现模式与必读文件

> **强制渐进加载门**：表中的文件组不是补充资料，而是对应分支的执行规范。命中某分支后，必须完整读取该行全部文件；组合输出读取所有命中行，再读取 `references/composition.md`。仅做路由判断时先读 `references/routing.md`，不要提前加载无关分支。

| 呈现模式 | 进入条件 | 输出契约 | 必须完整读取的文件组 |
| --- | --- | --- | --- |
| ECharts | 精确数据图表，或用户明确要求 option | Markdown + 单个完整 `echarts` option | `references/mode-echarts.md` → `references/echarts-option-spec.md` → `references/shared-quality.md` |
| 原图静态叠加 | 原图是证据，只需点、框、线、路径、匹配 | 文字答案 + 末尾原图叠加 renderer | `references/mode-image-overlay.md` → `references/image-overlay-process-spec.md` → `references/image-overlay-authoring-spec.md` → `references/shared-quality.md` |
| HTML/SVG 交互 | 需要动态探索；可引用原图、数据或自绘结构 | 文字讲解 + 可操作 renderer | `references/mode-interactive.md` → `references/renderer-trigger-design.md` → `references/renderer-stability-math.md` → `references/renderer-interaction-geometry.md` → `references/renderer-output-mobile.md` → `references/shared-quality.md` |
| 生成式知识配图 | 解释概念或关系；原图可作为参考而非证据 | 分段正文 + 对应图片 | `references/mode-generated-illustration.md` → `references/generated-prompt-rules.md` → `references/generated-style-guide.md` → `references/generated-tool-contracts.md` → `references/shared-quality.md` |
| 组合输出 | 单一模式无法完整表达，且模块互补 | 按阅读顺序组合，不重复信息 | `references/composition.md` |

### 加载完成检查

开始生成前在内部确认：

```text
route_decided = true
required_files_loaded = true
output_contract_fixed = true
```

任一项为 false 时，继续路由或读取文件，不开始生成。工具参数不确定时额外读取 `references/tool-contracts.md`；需要实现参考时再读取对应 example，example 不能替代规范文件。

## 内部规划

执行前形成简短计划，不向用户展示内部字段：

```json
{
  "should_visualize": true,
  "goals": ["knowledge_explanation", "dynamic_exploration"],
  "assets": ["user_image", "verified_text"],
  "user_image_policy": "preserve",
  "presentations": ["interactive_html"],
  "required_files": [
    "references/mode-interactive.md",
    "references/renderer-trigger-design.md",
    "references/renderer-stability-math.md",
    "references/renderer-interaction-geometry.md",
    "references/renderer-output-mobile.md",
    "references/shared-quality.md"
  ],
  "required_files_loaded": true,
  "facts_status": "verified",
  "reason": "点击原图部件能直接解释工作原理"
}
```

字段值与组合约束见 `references/routing.md`。不要因为存在用户图片就自动走原图标注；先判断图片是证据、底图还是生成参考。

## 统一输出要求

- 先给用户最需要的结论，再给可视化和必要解读。
- 说明数据来源、事实口径、示例属性或生成图性质。
- 原图叠加默认把可视化放在文字答案之后；知识配图应紧跟对应段落；数据图表前后只保留必要说明。
- 组合任务按“结论 → 原始证据 → 精确数据 → 解释性图解”的阅读顺序组织；不要求每次全部使用。
- 工具或资源不可用时，保留文字答案并说明缺少什么；不得绕过官方工具、自行构造鉴权或猜测私有接口。

## 安全与事实边界

- 不编造统计数据、股价、财报、病例、排名、年份、人物身份、事件顺序或来源。
- 不在输出、Prompt、HTML 或日志中回显 token、cookie、AK/SK、JWT、私钥或无关个人信息。
- 用户原图包含敏感信息时，只标注完成任务所需区域；不复述无关手机号、证件号、住址或聊天内容。
- 搜索图片用于真实实体参考时，区分搜索图片、用户原图和生成图片；不把搜索结果描述为自有或官方素材。
- 医疗、工程、金融等高风险图示只能辅助说明，不替代专业判断；不让图示暗示未经证实的结论。

## 参考文件

- `references/routing.md`：目标、素材策略、呈现方式、组合路由和降级条件；每次使用必读。
- `references/shared-quality.md`：事实、移动端、资源、交互和输出质量检查；每次使用必读。
- `references/mode-echarts.md`：精确数据图表规则。
- `references/mode-image-overlay.md`：保持原图的静态证据标注规则。
- `references/mode-interactive.md`：纯自绘或基于原图的 HTML/SVG 交互规则。
- `references/mode-generated-illustration.md`：纯文本资料或原图参考的生成式知识配图规则。
- `references/echarts-option-spec.md`：原 ECharts Skill 的完整 option、移动端、自由布局和模板细则。
- `references/image-overlay-process-spec.md`、`references/image-overlay-authoring-spec.md`：原图标注的完整 process、坐标、两层舞台、视觉和交互细则。
- `references/renderer-trigger-design.md`、`references/renderer-stability-math.md`、`references/renderer-interaction-geometry.md`、`references/renderer-output-mobile.md`：原通用 renderer 的完整触发、设计、稳定性、公式、交互、几何和移动端规则。
- `references/generated-prompt-rules.md`、`references/generated-style-guide.md`、`references/generated-tool-contracts.md`：原知识配图的完整 Prompt、风格和工具规则。
- `references/composition.md`：多模式组合、顺序、去重和冲突处理。
- `references/tool-contracts.md`：可用工具能力、参数核验和工具不可用时的处理。
- `examples/routing-cases.md`：正例、反例、边界例和组合场景。
- `examples/image-overlay-gold-process.md`、`examples/image-overlay-gold-reply.md`：原图标注的完整 process 和 renderer 实现。
- `examples/generated-worked-example.md`：知识配图的完整三图规划与调用示例。
- `references/echarts-source.md`：ECharts 规则的原始来源说明。
- `references/migration-coverage.md`：四个原 Skill 共 18 个文件的迁移去向、保留状态和定点修订说明。
- `schemas/visualization-plan.schema.json`：内部规划结构的机器可检验 schema。
- `scripts/validate_skill.py`：检查 Skill 结构、链接、路由关键词和已知冲突。
