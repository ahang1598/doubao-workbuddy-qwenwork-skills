# 原四个 Skill 迁移覆盖表

## 复核基线

复核日期：2026-07-31。

| Skill ID | 名称 | 版本 | 原文件数 |
| --- | --- | --- | ---: |
| 342971979522 | doubao-visualization | v7 | 5 |
| 349722639874 | doubao-echarts | 1.0.0 | 3 |
| 349722681858 | self-visualization-process | 1.0.1 | 5 |
| 353026578690 | doubao-knowledge-visualize | 1.0.1 | 5 |

总计 18 个文件。四个 Skill 的平台文件树中均没有 `scripts/`；融合包中的 `scripts/validate_skill.py` 是新增加的本地校验器，不是源 Skill 脚本迁移。

状态含义：

- **完整保留**：原详细文件复制进入融合包，仅增加作用域说明或不改变规则含义的修订。
- **定点修订**：主体细则完整保留，但修复了已确认矛盾、环境依赖或过时工具假设。
- **吸收至主路由**：原 SKILL.md 的触发、流程、输出和边界已经进入融合 `SKILL.md` 与 mode 文件，不机械保留第二份入口，避免多个入口互相冲突。

## 342971979522 · doubao-visualization

| 原文件 | 融合去向 | 状态 | 说明 |
| --- | --- | --- | --- |
| `SKILL.md` | `SKILL.md`、`routing.md`、`mode-interactive.md` | 吸收至主路由 | 白名单触发、renderer 输出、安全、地图和附件边界均保留；普通数据图改由 ECharts 分支负责。 |
| `references/visualization-trigger-design.md` | `references/renderer-trigger-design.md` | 定点修订 | 完整保留设计哲学、令牌、库分层、色板和设计原则；把“命中任意可视化都必须 HTML”限定为 renderer 分支，并移除“分栏只能 1 或偶数”的非必要限制。 |
| `references/visualization-stability-math.md` | `references/renderer-stability-math.md` | 完整保留 | IIFE、try/catch、CDN 降级、防死循环高度、数学公式和地图边界均保留。 |
| `references/visualization-echarts-interaction.md` | `references/renderer-interaction-geometry.md` | 定点修订 | ECharts renderer、交互形态和几何证明细则完整保留；明确内嵌 ECharts 只用于 HTML 交互联动，普通图表走原生 option。 |
| `references/visualization-output-mobile.md` | `references/renderer-output-mobile.md` | 定点修订 | 两个完整 renderer 示例和移动端规则保留；增加普通 ECharts 数据图不使用此 HTML 协议的说明。 |

## 349722639874 · doubao-echarts

| 原文件 | 融合去向 | 状态 | 说明 |
| --- | --- | --- | --- |
| `SKILL.md` | `SKILL.md`、`routing.md`、`mode-echarts.md` | 吸收至主路由 | 生成、修改、检查 option 的触发和唯一输出格式均保留。 |
| `references/fornax-echarts-rules.md` | `references/echarts-option-spec.md` | 完整保留 | 图表类型、唯一格式、真实数据、tooltip、ES5 callback、移动端、自由布局、特殊数据、完整模板均保留。 |
| `references/source.md` | `references/echarts-source.md` | 完整保留 | 保留规则来源与抽取范围，便于追溯。 |

## 349722681858 · self-visualization-process

| 原文件 | 融合去向 | 状态 | 说明 |
| --- | --- | --- | --- |
| `SKILL.md` | `SKILL.md`、`routing.md`、`mode-image-overlay.md` | 吸收至主路由 | 原图证据、HTTPS URL、零泄漏输出、隐私和降级均保留；删除强制写本地 `svp_process.json` 的副作用。 |
| `references/process-spec.md` | `references/image-overlay-process-spec.md` | 定点修订 | schema、0-999 坐标、六类标注和路径密采完整保留；修正 label 与“纯计算不应打点”的矛盾，并澄清做题触发边界。 |
| `references/authoring-prompt.md` | `references/image-overlay-authoring-spec.md` | 定点修订 | 两层舞台、SVG/HTML 分工、视觉标准、配色、图例、多图和自检完整保留；统一 `<img>` 尺寸，加入 tap/click，修正“JS 失败仍必有标记”的错误承诺。 |
| `examples/gold-process.md` | `examples/image-overlay-gold-process.md` | 完整保留 | 保留四类标注组合和完整 process。 |
| `examples/gold-reply.md` | `examples/image-overlay-gold-reply.md` | 定点注释 | 14k 字完整实现保留；文件头明确 Gold 中缺 `final_answer`、仅 hover 等旧问题，正式输出以修订 spec 为准。 |

## 353026578690 · doubao-knowledge-visualize

| 原文件 | 融合去向 | 状态 | 说明 |
| --- | --- | --- | --- |
| `SKILL.md` | `SKILL.md`、`routing.md`、`mode-generated-illustration.md` | 吸收至主路由 | 工具路由、图文规划、动态尺寸、Prompt、质检、失败处理和输出顺序均保留。 |
| `references/prompt_rules.md` | `references/generated-prompt-rules.md` | 定点修订 | 事实边界、标题、可见文字、母题、布局、多图、时间线、负面约束、模板均保留；模型版本检查改为读取当前 schema。 |
| `references/style_guide.md` | `references/generated-style-guide.md` | 完整保留 | 教材、高级信息图、工程、科学、人文、历史风格及失败模式均保留。 |
| `references/tool_contracts.md` | `references/generated-tool-contracts.md` | 定点修订 | image_gen/general_search/image_search 参数与错误处理保留；固定 Seedream 字段改为“当前 schema 支持且业务要求时传入”。 |
| `references/worked_example.md` | `examples/generated-worked-example.md` | 定点修订 | 三国三图的正文拆分、尺寸、构图、Prompt 和检查完整保留；模型版本使用占位符，避免过时硬编码。 |


## 逐文件文本保留核验

对 14 个详细 reference/example 文件与源文件做逐行相似度检查：

- 5 个文件 100% 原样保留；
- 其余文件仅修改 1-8 个规则片段或增加作用域说明；
- 最低相似度为 `image-overlay-authoring-spec.md` 的 93.55%，差异全部来自已记录的图片尺寸、移动端 tap/click 和 JS 降级修正；
- 没有任何源 reference/example 被概括后删除。

详细文件基线与定点修改由 `scripts/validate_skill.py` 的必需文件清单和本表共同约束。

## 明确删除或替换的规则

以下不是遗漏，而是经复核后的主动修复：

1. 删除“所有可视化命中后必须 HTML renderer”，改为按路由选择 ECharts、原图叠加、交互或生成图。
2. 删除强制写入 `svp_process.json`；保留同一 process 驱动和 schema 校验，但不要求本地文件副作用。
3. 删除无条件固定 `seedream_5.0_pro`；保留业务指定模型能力，但必须先核对当前工具 schema。
4. 将原图标注从仅 hover 改为 hover + click/tap，核心答案不依赖交互。
5. 统一竖图 `<img>` 为 `width:auto;max-width:100%;max-height:720px`。
6. 修正动态生成标记场景中“JS 失败标记仍必然可见”的不实降级描述。
7. 不再强制分栏数量只能为 1 或偶数；保留响应式换行和防拥挤要求。

## 完整性结论

融合包保留了所有原 reference/example 文件对应的详细内容。原 SKILL.md 没有原样复制为四个并列入口，而是被统一入口和四个 mode 吸收，以避免重复触发与协议冲突。任何后续修改都应同步更新本表和 `scripts/validate_skill.py` 的必需文件清单。
