# Child Agent Targets

本 Skill 只定义 SuperAgent 到子 Agent 的 handoff target，不把 5 个子 Agent 作为常驻 Skill 一次性注入。

## product-validation

用于商品机会判断、ASIN/产品可做性、风险、利润、供应链、合规初筛。输出应是验证结论、风险和证据引用。

## market-analysis

用于市场初步分析、竞品分析、关键词调研、趋势、需求、竞争格局。输出应是市场判断、机会与风险。

## image-generation

用于商品图、广告图、A+ 图、主图/场景图创意 brief、提示词和图片 artifact。若图片生成 runtime 不可用，输出 brief 与 blocker。

## video-generation

用于短视频脚本、storyboard、镜头规划、视频 brief 和视频 artifact。若视频生成 runtime 不可用，输出脚本/分镜与 blocker。

## listing-generation

用于标题、五点、长描述、A+ 文案、关键词布局、listing draft。输出应是结构化 listing artifact，不直接写回商品库。

## Routing Rules

- 普通问题留在主 Agent。
- 深度任务才 handoff。
- 用户明确指定目标 Agent 时优先尊重。
- 一个 handoff 只指向一个 targetAgent。
- 多目标任务先由主 Agent 拆解顺序，再逐个 handoff。
