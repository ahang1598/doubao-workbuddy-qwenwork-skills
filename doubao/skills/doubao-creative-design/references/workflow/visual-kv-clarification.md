# 视觉 KV 澄清

> 先按主 SKILL 判断交付环境。system 明示 `Device platfrom: Mobile` 时遵循 [Mobile 直接交付](mobile-app-direct-delivery.md)：Brief／素材记录留在本地，跳过本文全部 Workspace、Canvas CLI、Item 与卡片步骤，媒体逐项直接交付、HTML 预览走 CDN＋Markdown。其他环境执行本文默认 Canvas 分支。生产与编辑顺序不变。

本规范仅适用于 **AI + Coding 路径中新建或整体重做的电商详情页、社媒长图**。它是完整候选 Brief 之后、最终 Brief 冻结和 正式素材清单之前的视觉澄清门：用 1–2 个真实关键画面消除候选视觉路线的歧义，不是正式资产批量生产。社媒套图默认 pure-image，读取现有纯图平台 Ref 与 pure-image-sequence，以同一轻量 Brief 规划共享系列后逐页生成完整图片，不读取 Coding Spec／Visual。要求可编辑设计或文字时才走 AI + Coding，封面与内页均按同一完整 Brief 执行正常素材生产、HTML 原生文字组装与 DOM 检查；指定可编辑区域必须原生排字，封面不例外。两种套图分支均不进入本候选 KV 流程，已有 HTML 编辑保留原格式。

```yaml
visual_clarification_scope:
  execution_path: ai_coding
  eligible_deliverables:
    - ecommerce_detail_page
    - social_long_image
  operations:
    - create
    - major_redesign
```

纯生图、纯 Coding、其他 AI + Coding 品类、局部文字或素材替换、不改变既有视觉路线的小改均不进入。用户明确提供可作为确认 KV 的既有设计时，保存为 `external_reference`，提取路线后直接继续。

## 进入顺序

先确定执行路径与品类，完成文字与事实澄清，并严格经过以下前置门禁后再执行：

```text
创建唯一 Brief
→ 读取品类 Spec，补齐事实、准确文案、内容链与页面责任
→ 有设计参考时写入 11 维内部视觉底稿、逐块图文绑定、七类同源机制和重建方案
→ 读取对应 Visual System，补齐风格、构图、图文组合、字体角色、逐图职责和效果意图
→ 形成完整候选 Brief；写清 1–2 个候选方向、KV 用途、输入、准确文案和人类可读准出标准
→ 按 [素材 Prompt 指南：KV 视觉素材生成](../style/coding/ai-coding/asset-prompt-guide.md#kv-visual-generation) 将候选方向编译为生成 Prompt
→ 判断生成 1 个还是 2 个 KV
→ 选择 serial 或 parallel 执行模式
→ 串行：逐个生成；每个结果同步启动持久化／回读与工具产物直接单图交付，汇合后生成下一个
→ 并行：每个结果同步启动持久化／回读与工具产物直接单图交付，整批汇合
→ KV 视觉验收（参考任务同时核对已锁定特征）
→ 停止并等待用户确认
→ 将唯一采用方向、修改意见、实际参考和复用边界写回同一 Brief
→ 删除未采用路线的歧义，冻结最终 Brief
→ 建立轻量素材清单
→ 按素材清单继续其余正式资产生产
→ 直接编写完整 HTML
```

- 社媒长图的候选 Brief 必须已经消费 [Social Visual System](../style/coding/systems/social-visual-system.md)；电商详情页必须已经消费 [Ecommerce Visual System](../style/coding/systems/ecommerce-visual-system.md) 与详情页 Spec。进入本文件后不再补写第一版视觉规划。
- 选择依据、系统来源、适配理由、必须继承特征、可探索范围、KV 用途和候选差异先以自然语言写入同一候选 Brief；输入、Prompt、真实输出和交付状态写入 `kv-contract.json`、资产清单及确认记录。KV 阶段尚未执行 正式素材清单，禁止另建 `kv-asset-manifest.json`、参数化 Brief 或第二份视觉 Brief。
- KV 前允许等待的只能是图像工具输出 URI、实际像素等结果依赖字段；内容、逐屏职责、1–2 个可执行视觉方向、准确文字、构图关系、字体角色、参考继承、KV 用途与生成输入必须已经完整。此处的“完整”指候选方向各自完整，不代表已选出最终方向。
- 禁止先生成 KV，再倒推视觉系统。
- KV 与正式素材共用 `asset-prompt-guide.md`：候选阶段读取其「KV 视觉素材生成」，按本流程使用候选 Brief 与 `kv-contract.json`；确认后的正式素材使用冻结 Brief 与素材清单。不得把正式素材清单前置为 KV 的生成条件，也不得借用 pure-image 模型 Ref 改写路线。
- 每个 KV 图片执行 [交付门禁](image-generation-delivery-gate.md)。结果就绪后必须同步启动 CLI 写入／回读与工具产物直接单项 `present_files` 两个分支。串行时第 1 个 KV 的双分支汇合前不得生成第 2 个；两个候选相互独立且已预先锁定时可并行生成，并等待整批 join barrier 汇合。所有成功输出包括效果不佳版本都完成双分支闭环前，不得让用户选图或开始修复。KV 不得用 HTML／Coding 拼装，但生成后的完整 KV 图片仍须作为单个顶层 IMAGE Item 写入 Workspace。

KV 候选上屏后停止正式资产与 HTML 生产，等待用户通过普通对话确认、修改或提出混合意见。它与前置的事实／范围澄清分开，但仍属于视觉澄清。确认后先把采用路线写回同一 Brief，再冻结最终版本；随后建立轻量素材清单、生产正式素材并直接编写完整 HTML，不创建 `planned`／`ready` 中间 HTML。若用户反馈改变主构图、风格、内容职责或图文关系，就更新候选 Brief 并在需要时重新生成 KV，不能让旧候选或旧确认继续驱动生产。新发现不可替代素材缺失时，暂停受影响步骤并说明阻塞，不伪造输入。

## KV 数量

优先探索并提供 2 个合理 KV，让用户有选择；两个方向均须符合需求，且在风格、文字排版、配色、布局或材质质感中**至少一个维度有突出、可感知且值得用户选择的差异**，不要求多个维度同时变化。最多 2 个，不为凑数制造相似变体。只有用户明确只要一个、方向已被明确锁定，或在允许范围内探索后仍无法形成有价值的差异时，才提供 1 个；锁定品牌色或某个局部特征不等于整体方向已锁定。

突出差异应改变整体视觉感受或主次关系，例如深色高对比与浅色柔和、巨字主导与影像主导、粗粝纸感与通透玻璃。轻微调色、换同类建筑／主体动作、挪动装饰、微调字号或圆角只算同方向变体；不同风格名称、配方 ID 或 Prompt 措辞不证明画面有差异。

生成前结合 Spec／Visual 的相关候选主动比较不同方向，在既有选择依据中用一句话写明两个方向的突出差异及其选择价值，并分别落实到 Prompt。初选过于相似时先检查未锁定维度中的其他合理方向，仍无有效差异才收敛为 1 个并简记原因，不展开全库或无限探索。双候选共享主题、主体身份、核心内容、比例和事实，用户与参考锁定项保持不变，不为制造差异突破约束。

## KV 生产

候选生成只读取 [素材 Prompt 指南：KV 视觉素材生成](../style/coding/ai-coding/asset-prompt-guide.md#kv-visual-generation) 的候选输入与参数规则，不套用正式 Hero 的生成示例。先从完整 Brief 提取本张候选的必要内容，再生成横版完整关键画面；其余逐屏规划在确认后消费。本文件管理候选范围、数量、完整画面要求、交付、验收与确认；生成构图及 Prompt 写法由素材指南统一维护。

每个 KV 必须是可独立观看的完整关键画面，由图像生成或图像编辑工具直接完成。禁止使用 Coding、HTML、Canvas、图层协议或渲染脚本拼装；禁止用 Moodboard、色板、素材散图或文字 A/B 方案代替。

KV 应包含一条可辨认的主标题，让主视觉、产品内容和字形气质在同一张关键画面中被确认。用户要求文字可编辑时，KV 图内文字只作方向预览，不能作为正式文字资产；正式指定区域按已选路线原生排字。主标题按以下优先级取值：用户已提供或确认的标题 > 从已核验的产品名称、核心卖点或主题命题中提炼的准确短标题 > 用户已授权的传播文案拓展。每条都必须记录 `source_text`、`source_type`、内容依据和是否可改写；不得为展示字体而随机生成英文、占位口号、虚构卖点或与产品无关的文字。

KV Prompt 的准确文字与中文双引号规则统一见 [KV 视觉素材生成](../style/coding/ai-coding/asset-prompt-guide.md#kv-visual-generation)；本工作流核对文案来源、实际结果及确认记录。

### 结果验收与代表范围

按所选执行模式完成 Canvas 写入、回读和交付后，再逐字核对 KV 中全部指定文案，不只核对主标题。生图结果文字错误或效果不佳时，仍须同步完成 CLI 写入／回读与工具产物直接 `present_files` 两个分支，然后标记 `delivered_with_text_issue`、不进入可选方向并停止；禁止过度反思、自动修正或重生，必须等待用户提出明确修改要求后再开始新的编辑轮次。价格、参数、日期、规格、功效、CTA、Logo 等准确事实不得依赖 KV 图片文字。身份敏感的商品、人物和品牌资产在本次调用前必须实际传入对应身份图，不能只传风格图或 Prompt 提及；调用后对照原图检查，身份错误的 KV 不能进入确认候选。包装原有文字与 Logo 按身份保留，不属于新编事实文案。

双候选还须对照实际画面核验生成前声明的突出差异，不能只检查 Prompt。若结果仍为同方向变体，按当前环境规则完成已有结果交付后如实说明，并推荐更符合需求的一张，不包装成两个独立方向、不自动追加生成。

代表范围：

- **电商详情页**：固定 `1920×1080（16:9）` 横版关键画面，以连续场景中的商品 Hero 与准确主标题确认视觉方向和字体气质。辅助内容按下方“KV 辅助内容：三选一”选择，不要求展示后续素材／卡片样本；不是半张竖向详情页或说明板。
- **社媒长图**：固定 `1920×1080（16:9）`，首段关键屏，并露出可观察的下一章节入口。

### KV 辅助内容：三选一

详情页 KV 先以商品 Hero 与准确主标题建立第一焦点，不为辅助样本预留固定面积，也不以缩小商品换取样本展示。裁切、调色、边缘、光线与材质首先通过主体和场景确认；辅助内容按真实职责选择一种：

- **无卡片**：没有必要辅助内容时，只保留成立的主体、标题与场景，不补样本或空容器。
- **素材装饰**：确有主题或构图作用的素材直接参与同一场景，不包装成小卡片，不冒充商品证据。
- **单卡片**：仅在真实且必要的辅助内容需要明确归属、比较或阅读隔离时使用一张卡片；说明边界解决的问题，不使用空玻璃板、伪参数或任意素材填槽。

三种选择均由图像生成或编辑工具在同一张完整 KV 中完成，不改变 KV 禁止 Coding 拼装的要求。移除辅助内容后，主体与场景仍须成立；后续页面按各段购买问题重新组织构图，不复制 KV 的示例卡片或物件位置。

## 交付后验收

逐图持久化与交付闭环成功后，先看整体，再检查局部和缩略图。任一失败都将当前版本标记为 `revision_required`，不进入用户选图集合；收到用户明确修改要求后，再只修正受影响候选；修正版继续按交付门禁执行同步双分支，以及串行逐项或并行整批汇合：

- 画面不是完整连续的视觉世界，存在拼接缝、透视或光向冲突；
- 商品、人物、Logo 或包装身份漂移；
- 主标题与产品／主题无关、来源不可追溯、存在任何错字或字序错误，规划文字泄露，或手机尺度下必要文字不可读；
- 主视觉没有第一焦点，素材样本只是填槽；
- 容器无信息职责，卡片或素材与场景没有关系；
- 文件不可打开、实际尺寸或比例不符合本次横版 KV 要求，或当前输出与记录版本不一致；核对真实调用参数和输出像素，不能用正式 Hero 的尺寸记录代替。

KV 验收不能只依赖文件存在、Prompt 完整或脚本退出成功，必须检查实际图片。

## 文件与版本

每个候选保存到 `.creative-design/<task-id>/kv/<kv-id>/v001/`，改稿使用新版本，不覆盖已展示或确认的版本：

```text
kv-contract.json
kv.png
prompt-log.md
validation.md
kv-reuse-manifest.json
```

`kv-contract.json` 记录输入参考、完整 Prompt、输出参数、KV 主标题的 `source_text`、`source_type`、内容依据和可改写权限、视觉参数、候选差异和身份门禁。`kv-reuse-manifest.json` 以 `kv_id`、版本和 SHA-256 标识候选，并记录：

- `reference_asset`：被确认的完整 KV；
- `visual_parameters`：配色职责、字体气质、媒介、光线、材质、边缘和容器语法；
- `kv_title_style_reference`：KV 主标题的原文、字形、材质、边缘和色板，仅供后续通过准入的首屏／单图唯一艺术主标题引用；其他标题从字体库选择真实字体；
- `reuse_mode`：`direct | derive | reference_only | exclude`；
- `constraints`：身份、事实、文字准确性和适用页面；
- `consumer_bindings`：目标页／段、`slot_id`、采用方式与版本；
- `derived_from` 与 `verification_status`。

压平 KV 默认是 `reference_only`，不得假称能从中拆出独立图层。KV 主标题可裁切为 `kv_title_style_reference` 用作字形视觉参考，但裁切图仍不是最终可用标题资产；仅当目标品类允许独立标题图片且该标题通过准入时，才按准确源文字重新生成、抠图和验收；要求原生文字的品类区域及用户指定可编辑文字均原生排字。一体化社媒长图 Hero 可整体 `direct` 复用已确认 KV，但需逐项满足正式 Hero 的身份、全部图内文案、目标比例、有效分辨率及第 2 屏衔接；任何不满足时按确认风格另行生产，不把方向样张拉伸到正式槽位。除上述满足条件的一体化 Hero 外，只有本身独立且通过身份、权限、比例、分辨率和目标槽位检查的真实资产才可 `direct`；派生项必须保留原始源和新版本。

## 展示与确认

每个候选由图片工具产出后都必须同步完成 Canvas 持久化与工具产物直接独立 `present_files` 上屏，不能只提供路径、Prompt、参数或文字描述。串行候选逐项完成同步双分支，并行候选分别建立同步双分支并在 join barrier 汇合。全部候选闭环成功后，再使用稳定 `kv_id` 与一句可观察差异说明让用户选择。进入选择后立即停止正式生产。

状态仅允许：

```yaml
approval_status: pending | approved | revision_required | hybrid_requested
```

- 单 KV 的“确认”“OK”“按这个继续”等明确回复可批准当前版本。
- 双 KV 必须明确选中 `kv_id`。
- 混合多个候选特征时，先生成新的合并 KV，再次上屏确认。
- KV 图片变化后旧确认失效。

批准后保存 `approval.json`，记录用户原始回复、时间、`kv_id`、版本、图片哈希和复用清单引用。

## `selected_visual_route`

社媒长图确认后，在同一 Brief 用自然语言展开需沿用的风格、字体气质、颜色职责、材质、图文关系和接续方式，记录实际参考与确认状态即可；不在 Brief 提取参数或输出下方机器视觉路线。实际色值与几何由随后结构化转译形成的 最终 HTML 落实。KV 版本、真实输入输出与交付记录继续保留，它们不是第二份视觉 Brief。

以下机器执行约定只在最终 Brief 冻结后写入仍采用它的电商品类 最终 HTML 或审批记录，不得写回自然语言 Brief，也不应用于社媒长图或套图：

```yaml
selected_visual_route:
  status: approved
  source:
    kv_id:
    kv_version:
    kv_asset:
    kv_sha256:
    approval_record:
    approved_at:
  visual_intent:
    primary_impression:
    emotional_tone:
    visual_family:
    visual_branch:
    first_anchor:
  typography:
    kv_title_source_text:
    kv_title_style_reference:
    typography_character:
    resolved_font_family:
    resolved_font_weights:
    fallback:
    title_behavior:
    body_behavior:
  palette:
    background:
    surface:
    text:
    muted:
    primary:
    secondary:
    accent:
    area_relationships:
    semantic_roles:
  material_creation_reference:
    primary_medium:
    subject_treatment:
    image_treatment:
    illustration_or_photo_language:
    texture:
    grain:
    edge_treatment:
    shadow_and_light:
    depth_and_perspective:
  composition_language:
    spatial_character:
    hierarchy:
    image_text_relationship:
    container_or_card_grammar:
    density_rhythm:
    continuity_mechanism:
    recurring_motifs:
  continuation:
    required_anchors:
    selectively_inherited:
    allowed_variations:
    forbidden_drift:
    semantic_adaptation_rule:
  factual_boundaries:
    identity_constraints:
    editable_text_policy:
    unverified_content_policy:
```

`resolved_font_family` 必须映射到真实可用字体；配色要记录语义职责和面积关系；素材参考要覆盖媒介、光线、材质、颗粒和边缘；构图语言记录空间关系，不冻结具体坐标。

## 接续创作与最终验收

正式生产前回读确认 KV 与对应记录；社媒长图读取原 Brief 的自然语言效果与资产复用说明，不依赖机器视觉路线。后续页面延续字体气质、配色职责、素材媒介、主体处理、材质边缘、整体情绪和共同母题，具体构图、景别、图文比例、密度和过渡按内容重新组织。

不得逐页复制 KV 构图。只有通过艺术字准入的主标题显式引用 `kv_title_style_reference`，并使用自己的准确 `source_text`；其他标题只继承协调关系，实际字体从字体库选择。KV 参考不得成为批量生成所有 H1 的理由。
