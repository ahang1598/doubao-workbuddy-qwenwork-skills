# 纯生图步骤

> 先按主 SKILL 判断交付环境。system 明示 `Device platfrom: Mobile` 时遵循 [Mobile 直接交付](../mobile-app-direct-delivery.md)：Brief／素材记录留在本地，跳过本文全部 Workspace、Canvas CLI、Item 与卡片步骤，媒体逐项直接交付、HTML 预览走 CDN＋Markdown。其他环境执行本文默认 Canvas 分支。生产与编辑顺序不变。

用于已由主路由选定 `pure-image`、图像工具输出本身就是最终交付图片的任务，覆盖单张最终视觉成品、默认社媒套图／轮播，以及主 SKILL 指定纯生图的海报、社媒封面等场景。套图要求可编辑设计或文字时进入 ai-coding，已有 HTML 编辑保留原格式。

连续滚动长图、详情长图、A+ 长图预览、信息长图和社媒长图默认由主入口选择 AI + Coding；用户明确要求全部由图像模型生成、不要 HTML 排版，且主入口已锁定 `pure-image` 时，在本路线执行纯图长页分段与拼接，不退回 Coding。三折页、餐饮菜单、饮品单、酒单、套餐单、简历／CV 不进入本路线。“生成一张”“直接出图”或最终交付 PNG/JPG 本身不构成纯图长页例外。

纯生图不进入 `references/workflow/visual-kv-clarification.md`，即使图片生成成本较高或风格词宽泛，也不得先生成 KV 候选再生成终图。

未要求可编辑的社媒套图／轮播默认属于本流程。读取现有 pure-image 平台／媒体 Ref 和 [页序、分段与拼接](../pure-image-sequence.md)，在同一轻量 Brief 中先规划完整页链、逐页文案与共享视觉，再生成封面、内页及尾页的完整图片；不读取 Coding 套图 Spec／Social Visual，不建立 Coding 素材清单。

本文件只消费主入口已锁定的 `pure-image` 路线，不根据品类名称、文字密度、准确文字、字体或素材条件重新路由。普通海报、独立社媒封面／头图和单一 Logo 按已选路线生成完整终图，可见文字随图生成。通知／公告／喜报／捷报／成果战报／邀请函／节庆贺图和电商详情页等长页默认不在本文件执行；只有主入口根据用户明确要求全部由图像模型生成、不要 HTML 排版而锁定纯图时，才在此生产完整位图，长页按分段与拼接流程处理。Logo 系统和 VI 整体保持 AI + Coding，不因本文件存在品牌规范参考而转为纯图。真实事实不得编造；明确的逐层编辑或功能要求无法由位图满足时，在调用前说明具体冲突并澄清，不静默切换路线。

纯生图路线中的单张成品若使用纯色底，仍应按具体品类要求处理背景；单张 Amazon 主图等明确要求纯白底的非长图交付不受长图纹理规则影响。

## 读取路由

先完成意图理解、品类判断和执行路径判断；仅在已选 `pure-image` 时使用下表。读取只补足当前任务，不全量加载 ref。

| 顺序 | 必读／条件读取 | 目的 |
|---:|---|---|
| 1 | 主 `SKILL.md` 的设计 Brief 前置门禁；存在阻塞信息时读取 `references/workflow/clarification-strategy.md` | 定位或创建唯一任务 Brief，写入当前上下文与澄清回复，并在读取品类 Ref 前明确主题和商品 |
| 2 | 下方“品类 Ref 路由”对应的产物文件，必要时补充目标平台文件 | 在已有 Brief 上补充结构、内容角色、视觉语言、平台安全区与系列关系；若 Brief 缺失则先按当前上下文创建并填写，再继续扩充 |
| 3 | `references/style/shared/creative-concept-system.md`，仅需要新概念；`references/style/shared/composition-principles.md`，仅构图未锁定 | 补充创意与构图，不替代产物规则，不启动 KV 提案 |
| 4 | `references/style/pure-image/prompt-guide.md` | 建立完整成品指令合同，按其中规则最后读取一个模型改写 ref |
| 5 | `references/style/shared/image-quality-guide.md` | 检查画幅、身份、分辨率与质量；按终图角色检查，不读取 Coding 素材契约 |
| 6 | 按需读取 [字体推荐入口](../../rendering/font-recommendation-list.md)，只借用与当前画面有关的语种、文字角色、形态、气质、搭配和可读性建议；需要缩小范围时可把查询脚本用于候选、缺口和诊断 | 本路线在视觉建议处结束，不进入字体资源 Library、Resolver 或 HTML Web 字体门禁，不安装字体、不创建可编辑 DOM 或独立字体契约，也不承诺图像模型精确采用某个 family／face／weight；推荐清单不是封闭白名单，查询命中不表示资源可用，文字检查与修改仍按本路线执行 |

### 品类 Ref 路由

本表中的链接均指向 `references/style/pure-image/`。先确定明确产物，再判断品牌继承和平台补充；不因“品牌”一词跳过电商或信息图的专门结构。

| 当前交付物 | 读取 ref |
|---|---|
| Logo、字标、图形标、Logo 变体／规范图 | [brand-logo-system.md](../../style/pure-image/scenarios/brand-logo-system.md) |
| IP、吉祥物、角色设定、三视图、表情／贴纸 | [brand-ip-character-system.md](../../style/pure-image/scenarios/brand-ip-character-system.md) |
| 包装、礼盒、瓶标、包装概念图／SKU 视觉 | [brand-packaging-system.md](../../style/pure-image/scenarios/brand-packaging-system.md) |
| 品牌应用、继承品牌资产的海报／落地页效果图／折页等 | [brand-application-system.md](../../style/pure-image/scenarios/brand-application-system.md)，仅在需要平台规格时补对应 media ref |
| 独立品牌视觉规范位图／应用效果图（非完整 VI 系统） | 在已锁定的独立纯图任务范围内确定基础规范表达与应用清单；Logo 新建或变体读取 brand-logo-system，应用／视觉规范展示读取 brand-application-system；仅包含 IP 或包装时再读相应文件。完整 VI 系统留在 AI + Coding，不由本表改道，也不得用几张 Mockup 冒充完整 VI 系统 |
| 电商主图、单张卖点／对比图，以及主入口已锁定纯图的详情页、A+ 长图预览 | [ecommerce-design.md](../../style/pure-image/scenarios/ecommerce-design.md)；已授权纯图长页另读页序、分段与拼接流程，不重新路由 |
| 主入口已选纯图的信息图、知识／教学图、流程／关系图 | [infographic-design.md](../../style/pure-image/scenarios/infographic-design.md)；已授权纯图信息长图另读页序、分段与拼接流程。可编辑图解与分析型数据可视化不由本表转入纯图 |
| 小红书独立封面／单页、默认纯图套图及已授权纯图长图 | [media-xiaohongshu.md](../../style/pure-image/media/media-xiaohongshu.md)；套图另读 pure-image-sequence 先规划系列再逐页生成完整图片，已锁定纯图的长图执行分段与拼接 |
| 抖音 | [media-douyin.md](../../style/pure-image/media/media-douyin.md) |
| 快手 | [media-kuaishou.md](../../style/pure-image/media/media-kuaishou.md) |
| B 站 | [media-bilibili.md](../../style/pure-image/media/media-bilibili.md) |
| 微信朋友圈／九宫格 | [media-wechat-moments.md](../../style/pure-image/media/media-wechat-moments.md) |
| 微信公众号头图／单张配图及已授权纯图长页 | [media-wechat-official.md](../../style/pure-image/media/media-wechat-official.md)；长图文默认路线由主入口决定，已锁定纯图的长页执行分段与拼接，不重新路由 |
| 未指定平台或指定平台未被覆盖的横向 Banner／焦点图 | [media-banner.md](../../style/pure-image/media/media-banner.md) |
| 未指定平台或指定平台未被覆盖的海报／独立社媒封面、默认纯图套图及已授权纯图长页 | [media-poster.md](../../style/pure-image/media/media-poster.md)；套图另读 pure-image-sequence 先规划系列再逐页生成完整图片，已锁定纯图的长页按章节内容规划分段与拼接 |
| H5／移动端单屏视觉效果图及已授权纯图长页 | [media-h5.md](../../style/pure-image/media/media-h5.md)；已锁定纯图的长页执行分段与拼接。真实交互需求无法由位图满足时说明冲突并澄清，不在本表静默切换路线 |
| 通用产品摄影、插画、场景、壁纸等未命中产物 | 不强行套平台规则，直接由纯 AI 成品图指令指南编译 |

### 读取与执行边界

- pure-image Ref 供已锁定的纯生图任务使用，包括默认纯图套图；不同时读取 Coding 品类 Spec／Visual 重复决定结构，也不创建 `asset-manifest.json`。纯图套图复用现有平台 Ref 与 pure-image-sequence，不另建封面流程或 manifest。默认 AI + Coding 长页、三折页、菜单和简历在其父路线读取对应 Coding Spec；主入口已授权的纯图长页则在本路线消费品类内容约束与页序、分段、拼接流程，不读取 Coding Spec 重新决定路线。
- 用户指定的最终交付张数、文字和编辑范围优先于 ref 的推荐值；单张最终图片或 PNG/JPG 交付本身不授权长图、详情页或其他多页物料改道。社媒套图本身默认纯图，但明确要求可编辑设计或文字时由主路由选 ai-coding，指定区域包括封面文字必须原生实现；已有 HTML 编辑保留原格式。已锁定纯图的长页由本路线规划完整内容、按需分段生成并拼接；三折页、菜单和简历不属于该例外。画幅或清晰度限制需如实说明，禁止非等比拉伸或虚报尺寸。
- 纯生图 Logo／VI 交付是位图及其视觉规范表达；不承诺原生矢量、可编辑 Token／组件、实际印刷刀模或完整可执行设计系统。只缺真实旧资产时阻断身份复用；用户明确从零新建 Logo／IP 时，先创建用户要求的核心正式图，按原门禁写入、回读和交付，确认并通过身份检查后再将其用于衍生。此确认是母版身份确认，不插入多候选 KV 提案。
- 路由和 Prompt 编译不代替 Workspace 初始化。调用图像工具前，仍按主 SKILL 与 CLI 规则绑定／查询／创建 Workspace；本轮新建时必须由主 Agent 调用 `present_files(<workspace_id>)` 交付画布卡片，并登记本次需要的上传锚点。每个图像工具结果就绪后，同步启动“CLI 写入／get 回读”和“工具返回产物单项 present_files”两个分支，汇合前不开始依赖步骤；不得改成“生图 → 等 CLI 完成 → 再交付”。

连续身份失败仍沿用当前 pure-image 路线和原停止条件，不自动改为抠图合成或 Coding 排版；能力不足时如实说明，不无限重试。

## 执行与出口

1. 读取并继续完善前置门禁已经创建或定位的轻量 Brief；若 Brief 缺失，则立即按当前上下文在对应位置创建并先填写主题、商品和其他已知信息。随后区分“从零创建新 Logo／IP 核心图”和“复用既有商品、品牌或 Logo 身份”。前者记录新建意图及准确品牌源文字，不要求尚未生成的母版；后者按 [画布资产语义目录工作流](../canvas-asset-organization.md) 定位并确认母版，记录 `core_asset_id`、身份不变量和衍生用途；母版缺失、冲突或未确认时停止生产。继续在同一 Brief 中追加尺寸、目标宽高比、可见文字、主体框、焦点、安全裁切区、构图、风格、素材、真实事实、最低有效像素和禁止项，并按 [纯 AI 成品图指令指南](../../style/pure-image/prompt-guide.md) 输出指令合同。已有对应 Brief 时不得重复创建。
2. 创作型任务先形成视觉主张与可执行的构图、色彩、字体、材质和层级关系；至少 70% 画面遵循同一视觉家族，最多使用一种次级母题。
3. 从零新建核心图或不含既有核心身份时调用 image 工具生成完整最终图；复用已有核心商品、品牌或 Logo 时必须以锚点母版调用 `image_edit`，只改变已允许的环境、光线、镜头、道具、构图或材质，不得使用纯文本生成相似对象。调用前完成指令指南的可执行性自检；不拆素材、不进入 Coding 排版、不编译分层设计 HTML；电商 ref 规定的完整页面位图拼接保留。随后按 [交付门禁](../image-generation-delivery-gate.md) 选择串行或并行；每个结果都同步启动 CLI 写入／回读与工具产物直接单项 `present_files` 两个分支，串行时该结果汇合后才生成下一张，并行时整批汇合后才能继续。
4. 所有成功输出都必须同步完成持久化与工具产物直接 `present_files` 交付两个分支，包括效果不佳、错字或身份漂移的版本；串行项自身汇合、并行项整批汇合后再核对文字、主体身份、事实、源图／目标比例、是否等比缩放、有效分辨率、平台安全区和视觉关系。AI 图片内生成文字不准确、字形异常或可读性不佳时，只记录实际问题并等待用户提出修改要求，禁止过度反思或自动重生。含核心资产时逐张回查 `core_asset_id`、母版轮廓／结构／包装／品牌或 Logo 不变量及 `image_edit` 版本；身份漂移、比例或其他非文字质量问题仍按 Prompt 指南处理。每个用户明确要求的修正版仍是一张新的工具输出，继续服从当前执行模式。
5. 最终说明只引用已经独立 `present_files` 成功且完成 Canvas 持久化的版本。除用户明确要求外，不自动进行 Coding 覆字或格式转换。

## 已锁定纯图的长页与多结果

默认纯图社媒套图与主路由明确允许的纯图长页均读取 [页序、分段与拼接](../pure-image-sequence.md)。套图先规划完整系列，再逐页生成包含全部文案与画面的完整成品，不作为连续长页切片。纯图长页高度／宽度大于 16／9 时按内容接缝分段，统一宽度并保护完整文字和主体；已有 HTML 不因高度改道。段间依赖实际边缘时串行，无依赖固定批次才并行。交付分别按当前 Mobile 或默认 Canvas 环境处理。
