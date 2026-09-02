# Professional Agent Card Routing

当需要判断“留在主 Agent、推荐一个或多个专业 Agent 卡片、还是进入 Skill 创作路径”时，读取本 reference。

## Main Session First

除非缺少必要信息，否则主 Agent 必须先给出有用结果。

有用结果可以是：

- 初步结论
- 可执行 checklist
- 草稿文案
- 报告结构
- 文件或 artifact 说明
- 下一步建议
- 需要确认的 blocker

不要只回答“我可以帮你转到另一个 Agent”。

## No Re-entry Guard

`default-superagent-loop` 是单轮收尾决策，不是可持续执行的工作流。每个用户回合最多调用一次。

如果当前回合已经调用过 `default-superagent-loop`，调用方必须直接渲染已有 decision，并结束本轮；不要再次读取本 reference 或再次调用本 skill。

如果图片、媒体、报告、CSV、JSON、下载文件等业务产物已经成功生成，本轮已经进入最终渲染阶段。此时只输出产物协议、结果摘要、`<linkfox-suggestion-ask>` 和可选 `<linkfox-suggestion-agent>`，不要为了补充推荐卡片再调用 `default-superagent-loop`。若已生成的视频、图片或 Listing 仍有同方向优化建议，调用方应直接输出对应专业 Agent 标签，不经过本 skill。

特别是图片生成成功并已输出 `Saved full response: [...]` 时，不要再召回本 skill；否则容易把“收尾推荐”当成新任务，形成循环。

特别是视频生成成功并已输出本地视频产物时，不要再召回本 skill；若后续建议包含换模型、改时长、补提示词、多参考图、重生成、口播或分镜优化，直接输出 `linkfox-video-agent` 卡片。

## Professional Agent Cards

只有主 Agent 已经给出有用初步结果，或完成长任务 intake 后，才推荐专业 Agent 卡片。

一个卡片对应一个 `<linkfox-suggestion-agent>` 推荐。只有多个卡片代表不同的高置信度后续方向时，才允许输出多个卡片。

专业 Agent 卡片只能使用下表五个 `mode_id`。不要把工具 skill、数据源、JSON 文件、任务产物卡片或 `linkfox-sellersprite-*` 之类的原子工具结果当作专业 Agent 推荐。

| mode_id | Use when the next step is | Card title |
| --- | --- | --- |
| `linkfox-product-selection-agent` | 选品、找产品、判断能不能做、预算/供应链适配、爆款预测、关键词选品、候选品筛选 | 选品分析｜验证预算、供应链和切入机会 |
| `linkfox-market-analysis-agent` | 市场调研、竞品格局、评论痛点、趋势、合规/IP、关键词、深度报告 | 市场分析｜深挖竞品格局和评论痛点 |
| `linkfox-listing-agent` | 标题、五点、A+、描述、Listing 优化、对标复刻、埋词检查 | Listing 生成｜继续优化标题、五点和埋词 |
| `linkfox-image-agent` | 主图、场景图、白底图、卖点图、A+ 图、商品图、产品图、模特展示图、真人模特图、上身图、穿搭图、图片复刻或出图提示词 | 图片生成｜提炼主图和卖点图方向 |
| `linkfox-video-agent` | 图转视频、口播、TikTok 短视频、视频广告、分镜脚本、视频复刻、爆款视频 | 视频生成｜生成脚本、分镜和视频方案 |

卡片标题和 `<linkfox-suggestion-agent>` 标签正文必须使用上表 `Card title`，或按“推荐名称｜8-24 字简短说明”生成。不要只写“Listing 生成”，也不要只写“深度优化标题/五点埋词、撰写A+内容”这类动作描述。

最终回答中，专业 Agent 推荐只能通过 `<linkfox-suggestion-agent>` 标签输出，不得以普通正文、列表项、标题或裸文本出现。例如不要单独写 `图片生成｜提炼主图和卖点图方向`；必须写完整标签：

```xml
<linkfox-suggestion-agent modeId="linkfox-image-agent" context="业务上下文摘要">图片生成｜提炼主图和卖点图方向</linkfox-suggestion-agent>
```

多个 Agent 推荐标签必须连续相邻，并作为回答最后一个区块集中输出；不要被后续建议、正文或其他说明隔开。

普通问答、简单建议、纯数据抓取、原始字段导出、CSV/JSON/下载请求、用户显式指定工具调用时，不要强行推荐专业 Agent。若数据抓取后已经形成业务判断、关键词趋势结论、竞品格局判断或下一步专业深挖方向，不再视为纯数据抓取，可按高置信度方向推荐专业 Agent。

推荐专业 Agent 时，必须按用户想要的最终产物优先判断，而不是只按关键词。以下边界必须保留：

- “图片分析 / 视觉分析 / 产品图分析”不等于推荐 `linkfox-image-agent`；只有用户目标是生成图片、修改图片、复刻图、场景图、白底图、卖点图、模特展示图、真人模特图、上身图、穿搭图等图片产物时，才推荐图片 Agent。基于商品图片做市场研究、竞品视觉分析、产品演进、材质工艺或趋势预测时，优先市场分析。
- IP / 专利 / 版权 / 商标 / 侵权风险类任务先执行对应检测 skill；只有用户要求风险解读、合规报告或竞品合规分析时，才推荐 `linkfox-market-analysis-agent`。
- Listing 任务中出现“不能侵权”“不能出现品牌词”“避免违规词”时，这些是写作约束，不改变主任务；仍按 Listing 任务处理。
- 中置信度只输出后续建议引导下一步；低置信度或多意图冲突先自然语言追问或准备 `AskUserQuestion`，不要强行推荐单一 Agent。

如果主会话已经给出“值不值得做 / 能不能做 / 建议继续验证 / 需要深挖竞争格局”等初步判断，通常至少考虑：

- `linkfox-product-selection-agent`：继续做预算、供应链、候选品和小团队适配验证。
- `linkfox-market-analysis-agent`：继续做竞品格局、评论痛点、趋势和市场规模深挖。

例如“美国站宠物慢食碗，预算不多，先判断值不值得继续”这类 case，主会话给出初判后，优先推荐 `linkfox-product-selection-agent`；如果还提到竞争格局、评论痛点或市场规模，可再推荐 `linkfox-market-analysis-agent`。

如果主会话已经完成关键词搜索量、趋势、PPC 竞争、竞品数量、头部 ASIN、销量、价格带或评论痛点的初步分析，并在正文或后续建议中提出 Keepa、卖家精灵、亚马逊搜索、竞品格局、销量价格带、评论深挖等动作，至少推荐 `linkfox-market-analysis-agent`。如果同一回答还在判断入场、切入空间、预算或供应链可行性，再同时推荐 `linkfox-product-selection-agent`。

如果主会话已经成功生成图片、视频或 Listing，且后续建议仍围绕同类产物继续优化、换模型、改提示词、加素材、做多版本或扩展投放，必须推荐对应专业 Agent。视频产物对应 `linkfox-video-agent`，图片产物对应 `linkfox-image-agent`，Listing 产物对应 `linkfox-listing-agent`。

## Multi-Card Rule

返回 0-3 个卡片：

- 0 个：没有高置信度专业后续方向。
- 1 个：有一个最明确的专业后续方向。
- 2-3 个：当前任务已完成，且多个不同后续方向都有价值。

不要用多个卡片逃避必要的优先级确认。如果必须等用户选择方向才能执行，准备 `AskUserQuestion`。当用户同时提出分析、Listing、图片等多个方向并询问“先从哪个开始”时，即使还缺 ASIN 或站点，也要用 `AskUserQuestion` 先确认优先方向并提示补参，不要只用普通文本问缺失 ASIN。

## Context Rule

每个卡片必须带一个用于点击进入目标 Agent 的 `context` 业务摘要：

- 包含用户原始目标、已确认参数、当前结论、推荐下一步和约束条件。
- 保持简短，建议 80-180 个中文字符。
- 不包含系统内部字段、工具调用 JSON、协议细节或内部原始字段。

## Skill Creation Intent

如果用户主动要求保存、创建、封装、优化或复刻 Skill，不推荐五个专业 Agent。将 loop 标记为 `linkfox-ecommerce-skill-creator` 路径。

触发例子：

- `帮我把这次会话保存为 Skill`
- `基于这段对话创建一个 Skill`
- `把这个流程沉淀/封装成 Skill`
- `做一个亚马逊评论分析 Skill`
- `优化/复刻这条电商 Skill`

非触发例子：

- `帮我分析这个 ASIN`
- `帮我写 Listing`
- `做一份市场分析报告`
- `帮我做商品图/短视频`
- `给我一个 SOP 或 checklist`
