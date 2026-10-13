---
name: doubao-creative-design
description: 当用户要求从零生成或设计商业、品牌、社交媒体及知识表达类创意图片，编辑、复刻或审查已有视觉成品，或进行系列延展、多比例适配、多资产视觉系统设计时使用。触发任务包括做图、出图、生成图片、设计海报、主视觉／KV、Banner、封面、社媒配图、社媒长图、电商主图、详情页、产品图、Logo、IP 角色、吉祥物、包装、品牌应用物料、活动物料、宣传册、落地页、知识科普海报、信息图、教学图、教材插图、课件配图、思维导图、知识图谱、流程图、数据图表、科学结构图、公式推导图、工程图纸，以及分图层 HTML/CSS 视觉设计。
---

# doubao-creative-design

## 最高优先级：按请求类型立即完整读取 Ref，禁止懒加载

**这个非常影响用户体验，是一件很重要的事情，千万不要忽略。**

每次进入本 Skill，必须先根据当前用户请求与 system 上下文识别请求类型，并在执行任何 Workspace、Brief 写入、澄清提问、生成、编辑、Coding、上传、CLI 或交付动作前，立即确定并完整读取本次任务所需的 reference 集合。**禁止懒加载任务策略 Ref**：不得等到即将调用工具、进入某个阶段、发生错误或准备交付时才补读；不得只凭主 Skill 摘要、历史记忆、文件名、标题、局部摘录或旧版本经验执行。

初始路由至少同时判断以下维度，并据此建立本次 `required_refs` 清单：

1. **交付环境**：默认 Canvas 或 system 明确标记的 `Device platfrom: Mobile`。
2. **操作类型**：新建、整体重做、编辑已有图片、编辑已有 HTML、编辑已有 XML、选区编辑、批量／系列延展、审查或仅提供方案。
3. **生产轨道**：`pure-image`、`ai-coding`（可编辑设计）或 `pure-coding`；已有源格式优先决定编辑输出格式。
4. **品类**：Logo、VI、海报、社媒套图、详情页、连续长图、菜单、三折页、简历、信息图、思维导图、流程图、知识图谱、包装、品牌应用等实际命中品类。
5. **媒介与平台**：画幅、目标平台、移动端、社媒渠道、印刷／屏幕、HTML 固定画布及长页预览等实际约束。
6. **特殊能力与出口**：图像／视频生成、`image_edit` 身份锚点、HTML 组装、CLI 写入、CDN＋Markdown 预览、`present_files`、Subagent 或其他本任务明确要求。

路由确定后，必须在首次实质动作前一次性完整读取所有已命中的任务策略 Ref：对应 creation／editing workflow、品类 Spec、Visual／System 或 pure-image scenario、适用平台／media ref、交付环境与交付门禁，以及本任务必需的 CLI、HTML、预览、字体、素材或验证契约。读取完成后才可执行；后续阶段可以回读，但不得把“后面再看”作为首次读取时机。

**VI 专属 HTML 入口**：命中 VI／品牌视觉识别系统时，初始 `required_refs` 必须直接包含 [VI HTML 交付规范路由入口](references/workflow/vi-html-delivery-route.md)，并立即完整读取该入口列出的公共 HTML Ref 与当前默认 Canvas／Mobile 分支；禁止等到 Subagent 组装 HTML、`shot.py` 或交付时才首次读取。

若当前信息不足以确定请求类型，只允许先读取 [澄清流程](references/workflow/clarification-strategy.md) 和所有不依赖待确认答案的公共门禁，然后提出会改变路由的必要问题；用户回答后立即补齐并完整读取最终 `required_refs`，再开始实质执行。不得为避免选择而把多个互斥品类 Ref 全部加载，也不得跳过选择直接生成。

“禁止懒加载”针对会决定行为、内容、视觉、格式、工具和交付的任务策略 Ref；不要求提前通读未命中品类、未选平台、未采用候选，以及尚未选定的 CSS／SVG／模板实现正文。后者仍在设计决策形成后精确读取，但凡已被选中并将用于实现的正文与依赖，必须在写代码或组装产物前完整读取。每次执行应能明确回答：本任务属于什么类型、命中了哪些 Ref、这些 Ref 是否已经完整读完。

HTML 需要远程字体时，先读 [Web 字体契约](references/rendering/web-font-contract.md)，通过 Resolver 输出白名单字体声明；只允许 head 内唯一 `style data-web-fonts`，其余视觉样式仍须行内。字体选择不改变产物路由，自检仍只用 `scripts/runtime/shot.py`。

## 零、先确定交付环境

在能力预检、Workspace 绑定、Brief 存储或任何生成／编辑前，检查 system 是否明确包含 `Device platfrom: Mobile`。命中时读取 [Mobile 直接交付](references/workflow/mobile-app-direct-delivery.md)，使用本地唯一 Brief 与适用的素材清单，禁止全部 Canvas CLI／Workspace 操作。媒体逐项 `present_files`；HTML 只交付上传 CDN 后的同尺寸 Markdown 预览图，不上传 HTML 或创建 Item。不得从手机尺寸或作品用途推断该环境。

没有该标记时采用下方默认 Canvas 规则。交付环境只改变存储和交付，不改变品类路线、Brief → 素材清单 → HTML 的生产顺序。下文所有 Workspace、画布目录、Item 写入／回读与画布卡片要求均只适用于默认 Canvas 环境；HTML 专用预览截图在两种环境中都只走 CDN＋Markdown，不走媒体双通道。

## 最高优先级：画布写入与文件交付双通道同步

本节是所有图片／视频生成与编辑任务的硬门禁，覆盖中间素材、候选、草稿、改稿和最终产物。执行细节读取 [交付门禁](references/workflow/image-generation-delivery-gate.md) 与 [CLI 策略](references/cli/README.md)。

### 全局输出主体：所有产物由主 Agent 交付

所有生成、编辑、衍生、渲染或导出的用户可见产物，无论由主 Agent、子 Agent、异步任务或外部工具实际生产，都必须汇回当前任务的 **主 Agent**，并由主 Agent 按本 Skill 规定的出口亲自完成交付。该约束覆盖 Workspace ID、图片、视频、候选图、草稿、改稿、中间素材、渲染／导出结果、HTML 同尺寸预览图和画布卡片；产物质量不佳也不改变交付主体。

- 图片、视频及其他规定使用 `present_files` 的产物，必须由主 Agent 直接取得对应工具结果并亲自调用 `present_files`；子 Agent／异步任务不得代为调用，也不得把自己的工具预览、路径、URL 或交付状态当成主 Agent 已交付。
- HTML 同尺寸预览仍遵循 CDN＋Markdown 专用出口，但 CDN 结果的核验与最终 Markdown 图片展示必须由主 Agent 完成；默认 Canvas 的 `<workspace_id>?item_id=<item_id>` 画布卡片也必须由主 Agent 亲自调用 `present_files`。不得为满足本条把 HTML 预览改走媒体 `present_files`。
- 子 Agent／异步任务只可生产、编辑、校验并把未改写的真实产物句柄、短链、文件或 ID 返回主 Agent。主 Agent 未完成对应出口前，不得把子任务的完成、CLI stdout、日志、Markdown、普通聊天文字或工具自带预览视为用户已收到。

### 0. 正式生产能力预检

用户要求实际创作或编辑产物时，在写 Brief、调用媒体工具或编写 HTML 前，先按交付环境核对能力。默认 Canvas 环境需要 `design-cli`、`present_files` 与 `FileBatchUpload`；Mobile 按其专用预检，不要求 Canvas CLI。两种环境均按本次素材计划检查实际需要的图像生成、编辑和抠图能力；纯 Coding 不要求无关媒体工具。HTML 页面自检仅运行 `scripts/runtime/shot.py`，内部通过 Playwright 直接使用系统 chromium-1169，配合 Pillow 完成测量与截图；HTML 必须在 html 标签声明 data-canvas-width 和 data-canvas-height 正整数属性，预览图仍需 CDN 上传能力。只有脚本返回退出码 `3`、确认属于执行失败时，才允许跳过自检并记录“预览未验证”，按 [预览策略](references/workflow/html-preview.md) 继续可完成的交付；退出码 `1` 必须修正并重跑。不调用 artifact-preview／artifacts-preview Skill，也不另行操作浏览器自检。能力可以由已安装 CLI、原生工具或运行环境注入，但名称相似的普通文件展示、浏览器截图、Markdown 链接和上传命令不能冒充。

任一必需能力缺失时，立即停止正式生产，返回 `RUNTIME_CAPABILITY_MISSING`，逐项列出缺失能力及其阻断阶段；不得创建 Workspace、生成媒体、写入画布、先做半套 HTML，或宣称可以完成交付闭环。只做方案、提示词、审查或 Skill 维护时不要求这些生产能力。后续发现环境新增了全部能力后，从本预检重新开始。

### 1. 绑定 Workspace

新建 Workspace 的主 Agent 必须调用 `present_files(<workspace_id>)` 交付 Workspace 画布卡片；这与 HTML Item 回读后使用 `<workspace_id>?item_id=<item_id>` 交付 Item 卡片是两个不同阶段，不得混用。

- 对话中存在唯一、有效且指向当前目标的 `canvas_workspace_id`：绑定为 `active_workspace_id` 并复用。
- 不存在：按 [CLI 策略](references/cli/README.md) 直接执行 `design-cli design-workspace +workspace-create --title "<title>"`。凡通过 CLI 创建 Workspace，必须由当前任务的 **主 Agent** 读取创建响应，并由主 Agent 亲自调用 `present_files`，把响应中的原始 ID 作为唯一交付内容；禁止让子 Agent／异步任务代为调用或只把 ID 回传给主 Agent 后用聊天文字、CLI stdout、Markdown、工具日志交付。不得先调用 `+get-workspace`，不得创建中间文件，也不得把 ID 包装成字段、HTML、JSON 或说明。此阶段禁止输出其他用户可见内容。主 Agent 的 `present_files` 调用成功前不得生成／编辑媒体，也不得写入资产。
- 存在多个冲突 ID：先让用户确认。不得使用猜测值、空值、历史任务 ID 或查询结果代替当前 ID。
- 除非用户明确切换，后续产物始终写入同一个 `active_workspace_id`。

### 2. 设计 Brief 前置门禁

公共字段、各品类内容与视觉字段、未命中品类的通用字段统一参考 [任务 Brief](example/brief.md)；只完善当前任务对应条目，不复制整份字段目录。纯 Coding 由冻结 Brief 直接进入 HTML；AI + Coding 在正式图片调用前建立 [轻量素材清单](example/asset-manifest.md)。

用户提出实际创作产物需求后，必须在读取任何品类 Spec、Visual System 或 media ref 前，按 [画布资产语义目录工作流](references/workflow/canvas-asset-organization.md) 在 `active_workspace_id` 中定位本任务对应的设计 Brief。新任务在对应语义位置创建一份；连续轮次或已有任务读取并更新原 Brief，禁止另建同主题副本。先把当前对话上下文与待补项写入同一最小 Brief，再进入通用澄清；后续每次取得澄清回复，都立即增量回写这份 Brief，再继续下一步。

连续长页先在 [任务 Brief](example/brief.md#整体方案与逐单元内容) 记录相邻屏的叙事关系与交接，由对应品类 Visual 决定同一母图延展、结构化分隔或切屏；渐变、mask 与 blend 仅按 [HTML 组装的屏间过渡路由](references/workflow/html-assembly.md#屏间过渡路由基础方案优先) 处理背景层并经 [屏间过渡验收](references/workflow/html-validation.md#屏间过渡路由验收) 复核，两张独立完整主图不得直接像素融合。

画面应以真实内容为主体，避免无职责的大块留白；优先调整内容编排、栏宽、模块尺寸和间距；保留服务阅读的留白，不以拉高空壳、放大装饰或虚构内容补空；排版合理美观。

进入品类 Ref 前，设计 Brief 至少必须明确：

1. **主题**：本次设计实际表达的主题。
2. **商品**：商品名称、类型及对应真实素材／身份来源；没有实体商品时明确记录“无实体商品／不适用”，并写明实际核心对象。

主题或商品仍不明确时，先按 [澄清流程](references/workflow/clarification-strategy.md) 完成通用澄清，不得读取品类 Ref。Brief 始终使用自然语言描述内容和视觉方案，除短采用记录的 ID、源版本、范围和内容映射外，不输出坐标、色值表或 CSS 参数副本；这些实现值直接落入最终 HTML，AI 图片调用参数只进入素材清单。品类 Ref 原则上只在已有 Brief 上追加品类内容结构、视觉意图和人类可读的验收重点；若进入品类 Ref 时发现本任务确实没有 Brief，不得停止或空跑，必须立即按当前上下文在对应语义位置创建，先补齐主题、商品和其他已知信息，再继续品类扩充。已经存在对应 Brief 时禁止重复创建。主 `SKILL.md` 内的请求类型与生产轨道判断不属于品类 Ref，可以在本门禁前完成。只要用户要的是实际创作产物，无论请求发生在新开轮还是连续轮次，都必须经过本门禁；只要方案、提示词、脚本、分镜、建议或审查时不创建产物 Brief。

### 3. 每个产物执行双通道闭环

每个生成／编辑结果就绪后，必须在同一调度点同步启动并等待以下两个分支：

1. **画布分支**：使用工具返回的原始短链，通过 `design-cli` 写入 `active_workspace_id`，再用 `+get` 回读确认。新资产或内容修改后的新版本均用 `+create`；`+update` 仅修改协议允许的顶层 `brief`／`path`。
2. **交付分支**：由主 Agent 将工具直接返回的该项产物单独交给 `present_files`；每次只交付一个产物。

两个分支均成功后，该产物才算完成。不得先完成一个分支再启动另一个；工具预览、缩略图、URL、Markdown 图片或文本路径均不能替代 `present_files`。

画布持久化是硬门禁：`present_files`、HTML 中的媒体引用和最终 HTML Item 都不能替代媒体结果自身的 `design-cli +create`／`+get`。主视觉确认后的正式生产同样覆盖候选、未采用版本、抠图源和中间素材；全部结果逐项闭环、固定并行批次汇合且素材清单回填前，不得开始 HTML 组装，也不得事后集中补写。

媒体工具产出的 IMAGE／VIDEO 必须把原始短链逐字写入 `<asset url>`；不得为交付而下载、复制、重传或换链。只有未经过媒体工具且仅存在于本地的用户上传资产或渲染／导出产物，才可先上传取链。

### 4. 串行与并行

- `serial`：当前产物的两个分支汇合前，不得开始下一个生成或编辑。
- `parallel`：只并发预先锁定且互不依赖的固定批次；每个结果各自建立双分支闭环，整批汇合前不得选图、追加生成或继续下游步骤。同一锚点衍生 N 个变体时发起 N 次独立 `image_edit`，每次传入同一张已确认锚点，不用单次多结果调用代替。Mobile 每项只汇合自身直接交付状态。

### 5. 质量与失败出口

- 成功产出的内容即使效果不佳、文字错误或身份漂移，也必须先完成双通道闭环；禁止静默丢弃或先修复再交付。
- `image_gen`／`image_edit` 生成的产物必须直接通过 `present_files` 交付；AI 图片内文字不准确时，交付后只记录问题并等待用户提出修改要求，禁止过度反思或自主重生。Coding 的原生 DOM 文字仍须正常修正。
- `present_files` 失败时，立即停止后续生成、编辑、选图及依赖步骤。任一分支失败都保留另一分支的真实状态，不得把未完成闭环的产物视为已交付。

## 一、场景路由策略

先用已有信息判断请求类型与生产轨道。只有缺失信息会改变三类产物路由、结构、事实、成本或交付形式时，才读取 [澄清流程](references/workflow/clarification-strategy.md) 补齐；不得在路由尚未确定时先做视觉提案或调用生成工具。

### 1. 新建与生成：按品类与意图确定路线

先按完整产物的载体与阅读结构确定品类，再结合用途和用户明确意图选择路线及图片输出角色。连续长图不因“活动、促销、公告”等用途措辞套用单张公告规则；段落方位描述只说明内容顺序，不决定生产路线或图片比例。路由必须在读取任何生产路线或平台 Ref 前完成；下游 workflow、Spec、Visual System、平台／媒体 Ref 和模型 Ref 只能约束已选路线内的执行，不能重新裁定或扩大路线。文字数量、素材是否现成、PNG/JPG 交付和实现便利均不单独决定路线。

| 品类与意图 | 生产路线 | 输出角色 |
|---|---|---|
| 通知／公告／喜报／捷报／成果战报／邀请函／节庆贺图（含婚礼、活动、开业邀请） | ai-coding（可编辑设计） | 高质量无字底图／主视觉素材＋HTML 原生文字排版 |
| 用户明确要求纯代码制作通知／邀请函，或简洁文字公告且无摄影／复杂材质需求 | pure-coding | 原生文字与必要的规则图形 |
| 海报（上述通知／公告／喜报／捷报／成果战报／邀请函／节庆贺图除外）、未要求可编辑的单张社媒封面、单一 Logo、独立 IP 角色／表情／动作图片，以及独立摄影／插画／产品视觉 | pure-image | 按请求范围生成完整图片，不因角色图数量较多扩成系统手册 |
| 社媒套图／轮播图（未要求可编辑） | pure-image | 先以同一轻量 Brief 规划整套页序、文案与共享视觉，再逐页生成包含封面在内的完整成品图片；读取现有 pure-image 平台 Ref 与 pure-image-sequence，不读取 Coding Spec／Visual |
| 社媒套图／轮播图，用户要求可编辑设计或文字 | ai-coding（可编辑设计） | 同一 Spec／Visual Brief 统筹整套，封面与内页均以图片素材＋HTML 原生文字组装；仅指定局部可编辑时，该区域必须为原生文字，封面不例外 |
| 详情页、连续长图、Logo 系统、VI／IP 视觉系统 | ai-coding（可编辑设计） | 按需生成视觉素材，由 HTML 组织可编辑文字与布局；VI 除完整 HTML 生成／修改与 `shot.py` 自检必须调用 Subagent 外，其余规划、Logo、首屏、素材、MediaKit、检查、上传、CLI 与交付均由 Main Agent 亲自完成。VI 禁止直接交付 `.html` 源文件：用户只收到 CDN＋Markdown 同尺寸预览，以及默认 Canvas 中由 `FileBatchUpload` 上传后经 `design-cli ... +create`／`+get` 闭环的唯一顶层 HTML Item 画布卡片；Mobile 仅预览。Logo 确认并告知规划后，第一项正式图像生产必须以该 Logo 为唯一输入直接调用 `image_edit` 生成符合 VI 首屏定义的完整首屏效果；Logo 作为独立层进入排版前必须用 MediaKit 去除图片背景并核验真实 Alpha，禁止混合模式代替；全板采用大图、大字、低空白策略。未指定载体时采用 1600px 宽的模块化长板，以约 16:9 横向视域组织章节 |
| 用户明确要求全部由图像模型生成且不要 HTML 排版的通知／公告／喜报／捷报／成果战报／邀请函／节庆贺图／长图／详情页／IP 系统 | pure-image | 完整位图；目标高度／宽度 > 16／9 时分段生成后拼接 |
| 三折页、菜单、简历等结构化设计 | ai-coding（可编辑设计） | 按对应品类 Spec 规划素材与 HTML |
| 要求可编辑的图文信息图、解释性图解 | ai-coding（可编辑设计） | 图片承载实物／场景／插画，HTML 承载准确数据、标签与关系 |
| 未命中专用品类、但明确要求文字或设计可编辑的单页视觉 | ai-coding（可编辑设计） | 读取通用视觉兜底策略；图片承担复杂视觉，指定可编辑内容由 HTML 原生实现 |
| 数据看板、分析报告、可视化报表或以图表分析为主体的销售／赛事数据战报 | pure-coding | 使用真实数据生成可编辑 DOM／SVG 图表与说明 |
| 未命中上述品类的确定性代码图形／功能表达 | pure-coding | 已有资产、DOM／SVG 与代码图形 |

“生成一张”“导出 PNG”“用 AI 做”不等于明确要求纯生图；只有“全部用图像模型生成、不要 HTML 排版”等明确制作方式才覆盖主表列明的默认路线。传播型成果海报、销售喜报、成交捷报、赛事赛果、获奖／签约／晋升／录取喜报及演出／项目成果战报都属于公告海报家族并默认 ai-coding；需要筛选、比较、趋势或多图表分析的数据战报属于 pure-coding，不能只按“战报”二字判断。

单一 Logo 或独立角色图片是视觉资产；Logo 系统组织主标、变体、组合与用法，IP 系统组织角色设定、身份规则、必要延展与应用，VI 则按需求整合品牌识别体系。系统是否成立取决于交付职责，不取决于图片数量；仅做角色或表情包不扩成手册。Logo 系统与 VI 保持 ai-coding，IP 系统默认 ai-coding、明确要求纯图时按主表执行。母版可新建或复用，不因此改变整套路线；独立 IP 系统不要求附带 Logo。可编辑说明与布局由 HTML 承担，角色位图不承诺内部图层可编辑。

单张社媒封面未要求可编辑时走 pure-image；明确要求文字或设计可编辑时按通用可编辑单页策略进入 ai-coding，不读取套图 Spec。社媒套图默认 pure-image，以同一轻量 Brief 统筹封面与内页，每页生成完整成品；用户要求可编辑设计或文字时进入 ai-coding，封面与内页均按图片素材＋HTML 原生文字制作。仅指定局部可编辑时，该区域必须使用原生文字，封面不得绕过；非目标区域可沿用既有艺术标题准入规则，真实照片内的标签不必重画。已有 HTML 编辑保留完整 HTML。套图是逐页独立阅读，长图是连续滚动阅读，不能按素材张数混淆。

#### 套图路线与整套完成条件

路线一经主表选定即成为父路线锁，直到本次任务完成都不得由后续文件改写。下游 workflow、Spec、Visual、平台和模型文件只补充当前路线的生产要求；与主表冲突时，以主表和父路线锁为准。

社媒套图／轮播图默认走 `pure-image`，读取现有 pure-image 平台／媒体 Ref 与 [页序、分段与拼接](references/workflow/pure-image-sequence.md)，以同一轻量 Brief 规划完整页链、逐页文案和共享视觉，封面、内页与尾页均为完整图片，不读取 Coding 套图 Spec／Social Visual，也不建立 Coding 素材清单。

用户要求可编辑设计或文字时，套图走 `ai-coding`，才读取 Coding 套图 Spec／Social Visual。封面与内页遵循正常素材生产、HTML 组装和 DOM／渲染检查；要求可编辑的文字必须由原生文本承载，不能以完整封面位图替代。仅指定局部可编辑时，该区域同样必须原生排字，非目标区域沿既有艺术标题准入与真实照片身份保留规则处理。已有 HTML 编辑保留原格式。两条路线均须完成全部页次、逐页与系列检查及原门禁要求的整套交付，不能以封面完成代替任务完成。

HTML 创建／整体重做在 Spec 形成内容骨架、Visual 提出可调整的方向草案后，按 [组合参考筛选](assets/templates/css/README.md#brief-combination-match) 评估同品类、同作用范围的整页关系；简历风格查询按其 Visual 先召回适配布局并比较关联组合，其他品类优先比较 CSS 组合。先看整体信息层级、图文关系与视觉语言能否适配用户内容，再用原子补足或替换局部。用户锁定项和事实保持不变；模型自选的栏数、卡片形状或照片位置仍可随组合比较调整，不能先锁死再据此排除候选。最终 Brief 写适配后的可见关系及短 CSS 采用记录，不复制技术参数；确无适用组合时才转原子组装或自主实现，沿原流程推进。

1. **pure-image**：已选 pure-image 的任务读取 [纯生图创建](references/workflow/creation/pure-image.md)，按品类读取现有 pure-image Ref，以轻量 Brief 编译完整成品 Prompt；社媒套图默认进入本项，读取对应纯图平台 Ref 与 [页序、分段与拼接](references/workflow/pure-image-sequence.md)，先规划整套再逐页生成完整图片，不读取 Coding Spec／Visual。其他纯生图多张系列按需增加页序计划，纯图长页增加分段计划。必要输入齐备后直接生成，不进入可编辑设计的 KV 提案、素材清单或 HTML 组装。准确文案来自用户或授权来源；Prompt／模型 Ref 不得因文字密度、价格、日期或字体要求重新决定路线。套图明确要求可编辑设计或文字时由主路由选择 ai-coding；仍有互相冲突的制作或功能要求时，说明具体冲突并按澄清流程解决，不静默切换。
2. **ai-coding（可编辑设计）**：读取 [可编辑设计创建](references/workflow/creation/ai-coding.md)。电商详情页／社媒长图的新建与整体重做由品类和操作类型触发强制 KV 门禁，执行：内容骨架、逐屏方案与完整候选 Brief → 风格选择 → [视觉 KV 生成、展示与确认](references/workflow/visual-kv-clarification.md)（生成要点见 [素材 Prompt 指南](references/style/coding/ai-coding/asset-prompt-guide.md#kv-visual-generation)）→ 完整 Brief → 轻量素材清单 → 素材生产 → HTML 组装；方向已锁定时生成 1 个 KV，仍须展示并等待用户明确批准当前版本。其他品类执行 Brief → 轻量素材清单 → 素材生产 → HTML 组装，不插入 KV。“直接开始”“其他你决定”以及普通参考图或已有素材都不构成确认依据，只能减少前置文字询问；当前版本的确认依据必须是展示后的用户明确批准，或按 KV 专项规范登记的等价既有确认设计。续做上述两类任务时，先核验确认依据与当前版本、范围相匹配；依据有效后继续，否则回展或更新 KV 并等待确认。本路线的新建／整体重做默认必须结合图像生成或图像编辑工具，禁止整份作品仅靠 Coding 完成。生成／编辑产物须承担主视觉、场景、插画、材质或其他明确视觉职责，并实际绑定到最终作品；只调用工具却弃用结果不算完成。核心身份衍生用 image_edit，新摄影／插画／场景／复杂材质用 image_generate，准确文字、数据与规则图形用 DOM／CSS／SVG。一般新建任务已有素材不免除计划中必要的图像生产；通知／公告／喜报／捷报／成果战报／邀请函／节庆贺图已有合适底图且不需要其他新图时，允许原素材直接复用，不为凑调用生成无关图片。局部改字、间距等沿用原素材，不为满足调用次数重生无关图像。只有用户明确限制图像工具时才遵守该限制，不主动增加制作方式澄清；素材决策不改变品类路线。
3. **pure-coding**：仅执行主表允许的代码任务及对应源编辑，读取 [纯 Coding 创建](references/workflow/creation/pure-coding.md)。已进入 ai-coding 的新建／整体重做不得因素材现成或代码可实现而改走 pure-coding；仅沿用素材的局部修改也不改变原路线。含实物摄影、设备展示、品牌应用场景或解释性插画的 VI／信息图，按 [对象与素材分工](references/workflow/creation/ai-coding.md#asset-responsibility) 处理；“可编辑”不要求把图像对象重画为代码。

通知／公告／喜报／捷报／成果战报／邀请函／节庆贺图优先按 [底图与文字分工](references/style/coding/scenarios/announcement-poster-spec.md#announcement-hybrid) 制作：复用合适的真实底图或生成无字主视觉，标题、正文、姓名、日期、地点、结果数字、单位和行动信息默认全部原生排版；只有明确需要艺术字的主标题才按艺术标题准入另行处理。底图已有不改变 ai-coding 路线，也不为路线名称强行重新生图。

HTML 路线在最终 Brief 冻结前，按 [组合参考筛选](assets/templates/css/README.md#brief-combination-match) 完成组合比较、适配判断和必要的原子补充；CSS 库已随 Skill 提供，不依赖用户另行上传或点名。冻结后按 [实现绑定](references/workflow/html-assembly.md#css-recipe-binding) 读取选中正文与依赖，展开真实 DOM、行内样式和内嵌 SVG，预览时核对实际效果；后续变化只复查受影响部分。

新建可编辑设计的正式源为完整 HTML，按 [HTML 固定画布与交付协议](references/html/coding-rendering.md#html-fixed-canvas-delivery) 实现。既有 HTML 源编辑保持完整 HTML，不因上述新建品类规则压平或迁移；独立图片编辑沿图片路线。

前置文字澄清只处理会改变品类、意图或结果的真实歧义；Style、字体、模型改写和验收文件不得重新裁定路线，也不替代适用品类的 KV 展示确认。

可编辑长图的背景、首屏和跨段关系按 [素材分工与背景决策](references/workflow/creation/ai-coding.md#background-visual-responsibility) 形成可执行计划，再由 [HTML 组装](references/workflow/html-assembly.md#4-素材合成与实际测量) 绑定素材、共享场域与过渡。背景颜色不替代背景表现方式，逐屏说明不替代接缝实现；以实际合成结果核验。

#### HTML 路线唯一生产顺序

所有纯 Coding 与 AI + Coding 新建任务必须按下列顺序执行。Workspace 绑定、用户锚点登记和历史资产回读是基础设施前置动作，不改变设计阶段的先后，也不授权提前生成素材。

1. **获取需求并路由**：提取产物、用途、对象、受众、真实内容、参考、尺寸、可编辑范围和交付要求，判断唯一品类与生产轨道。此时不生图、不选 CSS／SVG、不写 HTML。
2. **创建 Brief**：新任务创建唯一 `brief.md`，连续任务更新原 Brief。先记录已知需求、事实来源、主题、商品／核心对象和待补项；不得等待品类 Ref 读完才创建，也不得另建视觉 Brief。
3. **按需澄清**：只询问会改变产物、结构、事实、身份、成本或交付的阻塞项；可安全决定的视觉细节由 Agent 处理。回复立即写回当前任务的同一 Brief。
4. **读取品类 Ref、完成视觉草案并校验 CSS 能力**：先读唯一品类 Spec 补齐内容、页面／章节职责、准确文案和硬约束；有设计参考时加入 11 维底稿、逐块绑定、七类机制与六步重建；再读对应 Visual System 补齐风格、构图、图文组合、字体角色与效果意图。Visual 草案形成后，先按 [组合参考筛选](assets/templates/css/README.md#brief-combination-match) 未知候选按品类 Visual 召回整页关系：简历风格查询用 `search --kind layout` 并比较关联组合，其他查询用 `search --kind combination`，已知或召回的候选用 `describe` 比较摘要，必要时用 `get <ID> --prose` 补读设计正文，比较可复用的整体关系并适配真实内容；再查询组合未覆盖或需要替换的局部原子，不把示例人物、配色或栏目数量当成必须照搬的条件，也不因库里存在某种效果新增无职责装饰。Brief 逐项说明需要哪些图片、每张图表现什么、与哪段文字如何组合，以及哪些 Coding 文字必须保持可编辑；写校验后的可见结果，并按 example/brief.md 保存选中 CSS ID、源路径与版本、范围和内容映射；不复制参数或查询过程。
5. **执行适用品类的 KV 展示确认并冻结最终 Brief**：AI + Coding 电商详情页、社媒长图的新建与整体重做由品类和操作类型触发，不以 Agent 判断方向是否存在分歧为条件。候选 Brief 完整描述 1–2 个可执行方向、准确文字、参考继承、KV 用途和验收标准后，生成并展示 KV；方向已锁定时生成 1 个 KV，仍须等待用户明确批准当前版本。用户选择、修改或混合方向后，把唯一采用方向写回同一 Brief；KV 发生变化时重新展示并等待当前版本获批，再冻结最终 Brief。确认依据及续做规则按本路线第 2 项执行。其他品类不生成候选 KV，直接确认内容结构、全部准确可见文案、决策优先级、视觉命题与注意力路径、逐单元相对构图、图文占比、图片层级与背景关系、字体角色、容器与表面、跨单元连续、载体适配、极端内容与降级、素材生产意图和人类可读验收标准已经闭合。
6. **按路线准备实现输入**：pure-coding 不创建中间参数文件，直接复用冻结 Brief。ai-coding 按 [轻量素材清单](example/asset-manifest.md) 登记正式图片的用途、生产方式、参考输入、身份来源、Prompt、比例、尺寸、安全区、消费者与准出标准，并执行 `validate_asset_manifest.py`；不得记录 DOM 坐标、字号、颜色或 CSS 参数。
7. **AI + Coding 生产并准出正式图片**：只生成素材清单中已登记的正式图片；普通可编辑文字、规则容器和简单图形不得转交生图。新生成与复用素材在使用前都按 [素材使用规范](references/style/coding/ai-coding/asset-prompt-guide.md#6-独立素材与图片编辑)判断是否需要抠图，完成必要处理并核验实际背景／透明状态后才准出；由 Agent 判断并记录，不增加逐图用户确认。每个结果准出后在原记录回填真实 URI、尺寸、Alpha 和版本，编写 HTML 前执行 `validate_asset_manifest.py --require-ready`；声明校验通过不替代实际素材核验。用户反馈若改变内容、主构图或视觉方向，先更新同一 Brief 并保留版本记录，再更新受影响素材记录。
8. **编译完整 HTML**：直接按冻结 Brief 和就绪素材生成一个固定画布 HTML5 文档。消费第 4 步已比较的 CSS／SVG 候选；选中实现及依赖在 Brief 冻结后使用 `query-css-library.py get <ID> --dependencies` 读取，必要结构用 `template` 精确提取。素材就绪后的组装阶段校核实现与真实素材、作用范围和消费者的绑定，把参数落实为真实 DOM、行内样式与内嵌 SVG；已有读取结果可复用，修改只回查受影响部分。Brief 标记为 Coding 的标题、正文、数字、标签、CTA 和注释必须是可编辑真实 DOM 文字；只有 Brief 明确准入的一体化图内文案或艺术标题可使用图片。HTML 是坐标、层级、字体、样式和资产消费位置的唯一实现事实源。
9. **页面自检**：交付前仅运行 `python3 <SKILL_DIR>/scripts/runtime/shot.py <html_path>`；修改后重跑。先读 JSON 中的错误、hint 和自然高度，再看完整截图；主图读失败才看分片。简历、三折页及用户锁定尺寸的作品先在固定纸幅内预留安全区并分配主体空间，测高只用于诊断容量；仅未锁高长页参考实际测量回填四处高度。按 [内容容量与留白](references/style/coding/composition-layout.md#容器内容框间距与顶边) 分别核对整页、各栏／折面和容器内部，背景覆盖或页尾落底不代表内容分布合理。退出码 `1` 必须按实际问题修正并重跑；只有退出码 `3` 的执行失败可跳过并记录“预览未验证”。不调用其他预览 Skill 或 Browser Use，不伪造检查通过。
10. **修正与交付闭环**：按实际 DOM 和截图修正完整 HTML；同尺寸完整预览图上传 CDN、核验公网链接并以 Markdown 图片展示；预览截图不创建 IMAGE Item、不调用 `present_files`。默认 Canvas 环境再上传完整 HTML、创建顶层 HTML Item 并 `+get` 回读，将 `<workspace_id>?item_id=<item_id>` 作为单值传给 `present_files` 输出对应画布卡片；Mobile 环境到预览展示即止，不上传 HTML、不执行 CLI 或 Item／卡片步骤。失败返回 Brief、素材或 HTML 的最小责任阶段，不通过删改 Brief 目标迁就错误实现。

跳过不适用项只能记录“不适用”并保持顺序，例如大多数品类第 5 步为“无需 KV”、pure-coding 第 6–7 步为“无需素材清单／无生图资产”；不得在 Spec 内容骨架和 Visual 可见方向形成前查询模板来替代设计，不得把 CSS 参数副本写入 Brief；选中 CSS ID 必须进入短采用记录，也不得先生成正式图片再补素材记录或边写 HTML 边补 Brief。KV 是唯一允许早于正式素材清单的图像生成例外，并且必须由已完成的候选 Brief 驱动。

所有连续滚动长图、详情长图、A+ 长图预览、信息长图和其他长页，须用有职责的影像、材质、光影、纹理、渐变或空间关系建立作品级背景系统；整页及连续背景组不得因素材缺失或实现方便退回无变化纯色加小图卡片。CSS 渐变与原生材质可以直接兑现背景职责，不强制生图。稳定纯色仅限有明确信息职责的局部信息区，并须说明增加纹理会削弱主体或版式；不得通过拆屏或拆容器把连续背景组伪装成多个局部例外。电商按当前 Spec／Visual 的背景职责与叙事关系核验，各品类均记录设计依据、范围和实际视觉证据。该规则不改变任何品类路由、CLI 或交付流程。

#### 开工前上下文收集

轨道初步确定后、执行对应 workflow 前，完成与任务规模相称的上下文收集：

- 提取受众、任务目标、核心信息、必备内容、品牌或审美约束、目标设备、交付形式与验收标准。
- 对现有项目先检查技术栈、目录、组件、设计变量、依赖和未提交改动；扩展现有结构，不平行重建同类系统。
- 阅读用户提供的全部参考，区分主参考与次参考：主参考决定整体视觉关系，次参考只提供局部母题，不能反向覆盖主参考。只要上传图承担模板、版式、风格或局部效果参考，就必须读取 [参考图解析与继承](references/style/coding/ai-coding/reference-analysis.md)，把清理后的 11 维底稿、逐块图文绑定、七类同源机制和六步目标重建写入同一自然语言 Brief。
- 此阶段只收集上下文，不承诺视觉方向，也不开始生图或 Coding。上下文齐备后才执行已选轨道；AI 原生视觉随后直接生成最终产物，仍不得插入视觉提案阶段。

新建与生成存在两条不可跳过的交付门禁：

1. **文件必须直接呈现**：图片、视频等成品与可视中间产物必须通过 `present_files` 呈现，不能只在文字中描述路径。每张结果都同步启动“CLI 写入／回读”和“工具产物直接单项交付”两个并行分支；串行模式在该结果汇合后再生成下一张，并行模式等待整批汇合。分图层 Coding + AI 生图的 HTML 是内部编译与 CLI 写入载荷，不是用户交付物：不得在对话中粘贴 HTML，不得把 `.html` 文件直接交给用户，也不得用 `present_files` 把 HTML 冒充为最终成品。
2. **必须完成当前环境的 HTML 交付闭环**：按 [HTML 检查执行流程](references/workflow/html-validation.md) 取得严格同尺寸且完整的预览。同尺寸完整预览图上传 CDN、核验公网链接并以 Markdown 图片展示；预览截图不创建 IMAGE Item、不调用 `present_files`。默认 Canvas 环境再上传完整 HTML、创建顶层 HTML Item 并 `+get` 回读，将 `<workspace_id>?item_id=<item_id>` 作为单值传给 `present_files` 输出对应画布卡片；Mobile 环境到预览展示即止，不上传 HTML、不执行 CLI 或 Item／卡片步骤。禁止 HTML Frame、按章节拆 Item 或直接交付原始 HTML。预览问题不阻断默认 Canvas 的 HTML 上传与写入，但当前环境的合格预览、CDN／Markdown 及所需卡片未完成时不得宣称完成。

分图层 Coding 必须先在候选 Brief 中明确本次主视觉及其可选方向。若场景触发视觉 KV，KV 视觉澄清画面应包含与当前产品、主题或核心内容直接相关的准确主标题，用于让用户确认主视觉与字形风格；不得生成随机英文、占位口号或未经授权的产品事实。确认结果写回并冻结最终 Brief，再执行 Brief → HTML。被确认的 KV 主标题只作为后续艺术字生成的字形、笔画、材质、边缘和色板参考，不得把压平 KV 文字直接当作独立标题层；社媒长图 Hero 可按品类规则整体复用满足正式槽位的 KV，不能假称其内部文字可拆。

主视觉和风格确认后，先按生产单元分配文字：社媒长图按[一体化 Hero](references/style/coding/scenarios/social-long-image-spec.md#一体化-hero-与第-2-屏衔接)把主标题随首屏生成，小字倾向入图，可编辑要求优先；其余内容建立原生文字 DOM。下文仅规定独立艺术标题素材，不要求一体化 Hero 拆字。艺术字不是按标题级别批量生成：只允许用于**首屏／首图的主标题**，以及每个独立图片产物中被明确选为唯一最高视觉优先级的**最重要大标题**；同一图片默认最多一个艺术字主标题，没有明确第一标题时全部使用真实文本节点。章节标题、模块标题及其他一级标题即使语义层级为 H1，也不得因此自动生成为艺术字。简历和三折页的姓名及全部标题保持真实 DOM 文字，不进入独立字图生成／接入流程。其他品类命中准入的主标题按自己的准确源文字执行 [AI + Coding 艺术标题策略](references/workflow/creation/ai-coding.md#艺术标题改写策略)，并读取 [艺术标题 Prompt 与材质库](references/style/coding/ai-coding/art-title-prompt-library.md)；生成结果采用中粗、粗或特粗视觉重量，经均匀纯色底生成、逐字检查，并按最终消费者选择节点级混合模式或真实透明抠图后作为独立图片 DOM 层使用。除已明确分配到一体化 Hero 内的文案外，所有未命中独立艺术标题准入的标题与正文、参数、标签、图注和来源，统一从 [字体推荐入口](references/rendering/font-recommendation-list.md) 按语种、角色、形态和气质形成候选，以真实文案试排完成视觉判断；推荐清单不是封闭白名单，`select_fonts.py` 的结果只负责候选、缺口和诊断。候选进入正式 HTML 前，再按 [字体资源与执行契约](references/rendering/font-family-library.md) 核验实际 family、face、weight／style、许可、目标字形覆盖和 Web 加载并建立回退栈；用户锁定精确字体时，任一门禁失败都必须请求确认，不得静默替换。

新建与已有 HTML 编辑中的独立艺术字统一按最终消费者分流：只用于已知、稳定的 HTML 背景时可保留纯色底并使用节点级混合模式，深色字体使用纯白底＋行内 `mix-blend-mode: multiply`，浅色字体使用纯黑底＋行内 `mix-blend-mode: screen`；需要透明导出、跨多个背景复用、背景未知或严格保持原字色时使用抠图透明 PNG。混合模式不得设在父容器或整页；两条路径都必须逐字、边缘、对比度、最终显示尺寸和完整画面验收。

### 2. 编辑已有画布内容

编辑分成两个部分，顺序不可颠倒：

1. **CLI 内容读取与更新**：先读 [CLI 命令与执行策略](references/cli/README.md)。按需使用 `+tree`、`+ls`、`+get` 定位并读取已有内容。HTML 编辑必须取得完整源文件作为基线；内容、样式、素材或尺寸变化后重新上传并 `+create` 新 HTML Item。`+update`／`+update-batch` 只允许在协议范围内修正顶层 `brief`／`path`，不能修改内容。当前仓库版本尚未实现 `find`；在 `references/cli/` 出现正式契约前禁止伪造调用。
2. **执行策略**：读取 [画布编辑执行策略](references/workflow/canvas-editing-strategy.md)，先区分“目标和修改已明确”“目标或修改意图不明确”“根目录未命名资产整理”，再按源类型进入 `references/workflow/editing/` 中对应流程。不明确的已有资产编辑必须先读取、向用户说明修改范围并取得确认，确认前禁止生成或写回；根目录未命名资产必须交给独立异步任务 `OrganizeAgent` 整理 brief 与 path。
3. **完整 HTML 不得降级**：输入或 `+get` 回读的是 HTML Item 时，编辑后的内部输出仍必须是保留未授权 DOM、素材、画布尺寸与交互边界的完整 HTML 文档，禁止压平为单张图片、输出代码片段或改造成 HTML Frame。优先按 DOM `id`／`data-layer-id`、实际素材 URI 与语义职责唯一匹配目标；无法唯一匹配时停止确认。若目标图片层原本含透明通道或承担叠加职责，替换资产仍须检查 Alpha、边缘和内部孔洞。完整规则见 [画布编辑执行策略](references/workflow/canvas-editing-strategy.md) 与 [AI + Coding 再编辑](references/workflow/editing/ai-coding.md)。

用户提供模板、源设计或既有交付物并要求沿用、改版或复刻时，先读 [模板改写](references/workflow/template-rewrite.md)，再进入上述编辑流程。

### 3. 画布资产语义目录策略

使用可多级嵌套的树状目录维护 Brief、图片、视频和最终交付物等画布资产，不得把目录固定为两层。所有写入 CLI 的顶层 Item／Frame `path` 必须是以 `/` 开头的画布绝对路径；Frame 成员不填 `path`。顶层先区分 `/user-anchors`、`/core-assets`、`/generated-assets` 与 `/deliverables`，再按任务、身份、用途、资产角色、变体或版本建立必要层级。目录属于 Agent 内部资产索引，用户不感知其存在；`path` 不得影响 `transform`、`z_index`、对象内容或 Frame 边界。

目录是多轮创作的持久资产记忆。继续创作、修改、衍生、做同系列或恢复历史任务时，必须先用 `+tree → +ls → +get` 回读相关目录，恢复历史上传锚点、核心母版、可复用生成资产、既有交付物及版本／衍生关系；只有确认没有适用资产或用户明确要求全新方向时才允许重新生成。

创建、编辑、衍生、批量生成或重新整理资产时，必须读取 [画布资产语义目录工作流](references/workflow/canvas-asset-organization.md)。归类只使用当前真实可得信息，证据优先级为：

```text
用户显式意图
>
用户上传的原始资产锚点（如有）
>
资产生成 / 编辑关系
>
共同创作任务
>
Generation Batch
>
资产内容语义
>
创建时间关系
>
资产类型及其他 Metadata
```

“用户上传的原始资产锚点”是条件证据：仅在用户确实上传且已登记为初始视觉锚点时参与判断；不存在时直接跳过。高优先级证据覆盖低优先级证据。用户上传视觉锚点、Logo 或产品图时，不得只在临时上下文中引用：必须先写入目录成为可回读的初始视觉锚点，再开始生成或编辑。一旦建立资产锚点或品牌锚点，它就是后续图片创作中该身份的唯一视觉锚点；跨轮次回读时必须优先恢复并继续使用，未经用户明确要求不得替换母版、另建竞争锚点、只凭文字重绘或偏移受保护的视觉身份。衍生结果通过 `+create` 写入时，还必须在 `<source_ids>` 中填写经 `+get` 核验的锚点 Item／Frame ID，使画布同时保存真实血缘并把新版本落在来源右侧；没有来源时省略整个标签，禁止填空标签或猜测 ID。每次还要判断是否存在核心商品、品牌或 Logo；存在时建立 `/core-assets/<语义名>/master` 母版锚点。核心资产确认后，所有需要保持一致性的衍生图片默认使用该唯一锚点执行 `image_edit`，并记录 `derived_from_core_asset_id`；只有不承载该身份的独立素材才可使用 `image_generate`。详细的触发条件、brief、读写、回读、核心资产及 `OrganizeAgent` 规则全部以该 workflow 为准。

## 二、参考文档地图

只加载当前任务需要的文件。每份 reference 的唯一职责如下。

### Workflow：执行流程

| 文件 | 定义 |
|---|---|
| `references/workflow/clarification-strategy.md` | 判断哪些信息会阻塞生产，以及如何完成文本与视觉澄清。 |
| `references/workflow/image-generation-delivery-gate.md` | 所有模式下 CLI／交付双通道同步、串并行汇合、坏图及部分失败状态的门禁。 |
| `references/workflow/creation/pure-image.md` | 纯图片最终成品的创建流程。 |
| `references/workflow/creation/pure-coding.md` | 不使用图像生成工具的创建流程。 |
| `references/workflow/creation/ai-coding.md` | AI 生成中间素材、HTML/CSS 分层组装、首屏／单图最重要艺术主标题及其他字体库文字的创建流程。 |
| `references/workflow/editing/pure-image.md` | 已有纯图片成品的编辑流程。 |
| `references/workflow/editing/pure-coding.md` | 已有纯 Coding 源的编辑流程。 |
| `references/workflow/editing/ai-coding.md` | 已有分层 AI + Coding 产物的完整 HTML 往返、目标层原位回贴，以及按消费者选择艺术字纯色底混合或透明抠图的流程。 |
| `references/workflow/canvas-editing-strategy.md` | 明确／不明确编辑、多图层 HTML 不降级与原位回贴，以及根目录未命名资产的 `OrganizeAgent` 异步整理策略。 |
| `references/workflow/canvas-asset-organization.md` | 内部资产索引、Semantic Cluster 证据、用户上传的原始资产锚点、核心资产锚点、brief、目录读写与异步整理流程。 |
| `references/workflow/template-rewrite.md` | 用户模板、源设计或既有交付物的继承与改写边界。 |
| `references/workflow/validation.md` | 创建、大改和编辑后的协议、视觉、事实、多图层结构、原位与透明层校验。 |
| `references/workflow/troubleshooting.md` | CLI、HTML、资产、字体和渲染失败时的排障与回退顺序。 |
| `references/workflow/html-assembly.md` | 自然语言 Brief 与 最终 HTML 到 CSS／SVG／DOM 的组装流程。 |
| `references/workflow/html-validation.md` | HTML 源码、实际预览、视觉目标与平台闭环检查。 |
| `references/workflow/vi-html-delivery-route.md` | VI 专属 HTML 交付规范路由入口；命中 VI 时在初始 `required_refs` 阶段读取，并立即补齐公共 HTML Ref 及默认 Canvas／Mobile 分支，禁止推迟到组装阶段。 |
| `references/workflow/html-preview.md` | `shot.py` 的唯一默认 HTML 预览与截图策略。 |

### Style：效果参考、生成规范与品类场景

品类 Spec 与对应 Visual 使用同一份任务 Brief，但职责不可互换：Spec 查找或创建 Brief，只确定事实、内容、载体／页面结构、职责、顺序和硬约束；Visual 找不到唯一 Brief，或事实、内容结构及必要硬约束尚未齐备时返回 Spec；仅视觉字段待补不触发返回，由 Visual 在原 Brief 中完善，不另建 Brief 或自行补写事实。Visual 仅在原 Brief 中补充或更新决策优先级、视觉命题、注意力路径、风格、艺术手法、字体、配色、相对构图、图文占比、背景／前景、图像层级、跨单元连续、载体适配、素材生产意图和可观察验收，保存后再进入素材、布局与最终 HTML。Spec 中出现的视觉 QA 只描述下游结果必须满足的约束，不授权 Spec 提前选择视觉方案。

所有品类的 Visual 在方向草案形成后，先按公共 CSS 查询顺序比较能覆盖整体关系的组合；只对组合未覆盖或需要替换的局部，再按布局、字形、形状、表面、配色和作用对象拆解自然语言能力词并校验候选。需要补充或替换的容器原子先查具体结构词加 `--kind shape`，例如“文件夹 页签 袋口”“卷纸 卷边 长文承托”“档案页 折痕 分栏”“撕纸 胶带 衬纸”；只有 Brief 明确需要中性圆角、玻璃或塑料时才查询这些词。泛化“卡片／容器／面板”查询会优先列出结构型轮廓，不能以“高级卡片”直接采用圆角配方。品类 Visual 中的能力表只表达常用视觉机制，不维护库 ID、文件路径、参数或依赖；查询结果用于确认可实现性与降级边界。最终 Brief 写经过校验的可见结果，真实实现引用统一进入后续最终 HTML。

所有品类进入 Visual 阶段后，还必须在原 Brief 每屏／页／卡面／折页面板／视图的对应条目内输出“容器与开放排版视觉决策”。先判断内容是否需要边界；无需容器时写“开放排版、无容器”及对齐、分隔、留白和图文组织方式。需要容器时按 [容器视觉语法](references/style/coding/composition-layout.md#容器视觉语法开放排版优先语义容器按需) 逐个说明承载内容、容器家族、主次与相对尺度、轮廓、结构部件、材质、边缘工艺、厚度／阴影、内部安全区及与图像和底图的关系。同页优先一个主家族和一到两个变体；普通白色圆角矩形只用于中性功能分组，不得铺满页面，也不得卡片嵌套。只用自然语言描述，不新增参数表或槽位契约；各品类 Visual 负责具体效果与验收，不能留到最终 HTML 阶段才决定。

社媒长图与可编辑套图直接使用中文内容／视觉 Brief，不额外输出品类机器计划、系列合同、布局枚举表或资产矩阵，也不将这些旧字段移入 HTML。视觉效果写成自然语言；规划 Brief 只记录颜色职责，公共 HTML 在实现阶段记录实际色值、尺寸、图层与素材引用。可编辑套图的 Coding 一致性与差异性配额仍是硬门禁，不能以自然语言规划或按内容试排为由取消。默认纯图套图使用轻量 Brief 与 pure-image-sequence 的共享系列规划，不读取 Coding Spec／Visual 或其配额。

个人卡片、菜单、三折页、简历、Logo、VI 与关系图使用各自 Spec／Visual 的中文 Brief 字段，不要求填写旧模板编号或额外品类 JSON。公共最终 HTML 仍由实现阶段消费同一内容生成，不反向扩充用户 Brief。个人卡片、菜单、三折页、简历、VI 与关系图的 Coding 文案与艺术标题按 Visual 用 HTML/CSS 实现；Brief 为普通配图记录生产意图，素材清单再把它编译为以具体风格开头、只描述画面的完整 Prompt。已有 Logo／包装中的字标作为身份资产保留。Logo 主标与组合标是例外：默认由生图／图片编辑工具生成，素材清单中的 Prompt 逐字描述品牌名及字形，并以确认主标继续派生单色、反白和组合状态；展示页标签与说明仍由 Coding 完成。此约定不改变纯生图母版路线、社媒长图或电商 Hero 的既有例外，也不改变交付门禁。套图按主路由区分默认纯图与可编辑分支；可编辑分支的封面没有整图文字例外，明确要求可编辑的文字必须原生实现。

生产和验收规范也是 Brief 输出，不是脱离 Brief 的第三套规则：品类 Spec 在同一 Brief 中写入“内容结构生产规范”和“内容结构验收规范”；对应 Visual 写入“视觉效果生产规范”和“视觉效果验收规范”。实现文件只消费两类已经准出的 Brief 字段，不重新决定内容结构或视觉方向。

Visual 能力校验与 Brief 冻结后的执行绑定均先读取 [`assets/templates/ref-bindings.json`](assets/templates/ref-bindings.json) 将品类解析为稳定 `ref_key`，再用 [CSS catalog](assets/templates/css/catalog.json) 与 [SVG catalog](assets/svg/catalog.json) 限定候选范围；未知名称由 `query-css-library.py` 进行词面召回，已知候选先比较摘要。卡片容器、渐变、弥散、蒙版、纸纹、玻璃、文字效果等只有在 最终 HTML 绑定真实消费者、读取实现正文与依赖并展开为实际行内代码后才算采用；默认关联、名称命中或 Visual 阶段通过可实现性校验都不构成实现。Brief 的短采用记录保存选中候选的 ID、源版本、范围与内容映射，不表示已完成实现采用；参数只在 HTML 维护。

| 文件 | 定义 |
|---|---|
| `references/style/README.md` | Style reference 的 shared、pure-image、coding 三路职责索引。 |
| `references/style/shared/style-generation-spec.md` | 把效果参考转成可执行视觉参数的总规范。 |
| `references/workflow/visual-kv-clarification.md` | 需要先生成真实 KV 并等待确认的范围、交付与验收门禁；生成要点统一读取素材 Prompt 指南的 KV 章节。 |
| `references/style/shared/creative-concept-system.md` | 创意命题、视觉隐喻和主要创意机制。 |
| `references/style/shared/explicit-style-terms.md` | 跨品类明确风格词、别名与最低视觉指纹；实际可用子集由品类文件决定。 |
| `references/style/shared/composition-principles.md` | 主轴、视角、留白、密度、叠压、裁切和阅读动线。 |
| `references/style/shared/content-truth.md` | 授权文案创作与必须有来源的真实事实边界。 |
| `references/style/shared/brand-color-planning-reference.md` | 品牌规划候选色系、颜色职责、面积关系、选用边界与跨载体验收。 |
| `references/style/shared/image-quality-guide.md` | 纯生图与分层路线共用的比例、身份、清晰度和质量门禁。 |
| `references/style/coding/concept-production.md` | 将公共创意映射为 Coding 资产、生成素材和原生图层。 |
| `references/style/coding/composition-layout.md` | 分层容器、文字、间距、表面融合与几何验收规则。 |
| `references/style/coding/generic-visual-fallback.md` | 未命中专用品类时的通用视觉兜底。 |
| `references/style/coding/ai-coding/asset-prompt-guide.md` | 从轻量素材记录编译图像 Prompt 及生成后的质量准出。 |
| `references/style/coding/ai-coding/reference-analysis.md` | AI + Coding 参考图的布局、字形、取色与材质解析，继承约束、Brief／素材清单 映射及原图对照验收。 |
| `references/style/pure-image/prompt-guide.md` | 纯生图最终成品的 Prompt 组织和质量检查补充。 |
| `references/style/pure-image/media/*.md` | 纯生图各平台媒介的尺寸、裁切和交付补充规则。 |
| `references/style/pure-image/media/media-banner.md` | Banner 纯生图媒介补充规则。 |
| `references/style/pure-image/media/media-bilibili.md` | 哔哩哔哩纯生图媒介补充规则。 |
| `references/style/pure-image/media/media-douyin.md` | 抖音纯生图媒介补充规则。 |
| `references/style/pure-image/media/media-h5.md` | H5 纯生图媒介补充规则。 |
| `references/style/pure-image/media/media-kuaishou.md` | 快手纯生图媒介补充规则。 |
| `references/style/pure-image/media/media-poster.md` | 海报纯生图媒介补充规则。 |
| `references/style/pure-image/media/media-wechat-moments.md` | 朋友圈纯生图媒介补充规则。 |
| `references/style/pure-image/media/media-wechat-official.md` | 微信公众号纯生图媒介补充规则。 |
| `references/style/pure-image/media/media-xiaohongshu.md` | 小红书纯生图媒介补充规则。 |
| `references/style/pure-image/models/model-4.5.md` | 4.5 模型的纯生图能力与改写规则。 |
| `references/style/pure-image/models/model-5.0-pro.md` | 5.0 Pro 模型的纯生图能力与改写规则。 |
| `references/style/pure-image/scenarios/brand-application-system.md` | 品牌应用系统纯生图规则。 |
| `references/style/pure-image/scenarios/brand-ip-character-system.md` | 品牌 IP 角色系统纯生图规则。 |
| `references/style/pure-image/scenarios/brand-logo-system.md` | 品牌 Logo 系统纯生图规则。 |
| `references/style/pure-image/scenarios/brand-packaging-system.md` | 品牌包装系统纯生图规则。 |
| `references/style/pure-image/scenarios/ecommerce-design.md` | 电商视觉纯生图规则。 |
| `references/style/pure-image/scenarios/infographic-design.md` | 信息图纯生图规则。 |
| `references/style/coding/ai-coding/art-title-prompt-library.md` | 分图层 Coding 的艺术标题字形路线、立体结构、材质模块、完整 Prompt 骨架与效果门禁。 |
| `references/style/coding/platforms/xiaohongshu.md` | 小红书 Coding／编辑分支的平台补充规则；纯图套图读取对应 pure-image 平台 Ref。 |
| `references/style/coding/systems/social-visual-system.md` | Coding 社媒长图与可编辑社媒套图共享的视觉系统；默认纯图套图不读取。 |
| `references/style/coding/systems/ecommerce-visual-system.md` | 电商详情页的媒介、色彩、布局、影像和艺术标题系统。 |
| `references/style/coding/systems/tri-fold-visual-system.md` | 三折页展开与折叠状态下的视觉系统。 |
| `references/style/coding/systems/menu-visual-system.md` | 菜单的视觉方向、字体、配色、图文关系、食物影像和载体适配系统。 |
| `references/style/coding/systems/resume-visual-system.md` | 简历阅读模式约束下的视觉系统。 |
| `references/style/coding/systems/personal-card-visual-system.md` | 名片、会员卡及权益卡的正反面、系列、材质和卡面视觉系统。 |
| `references/style/coding/systems/diagram-visual-system.md` | 思维导图、流程图、知识图谱共享的布局、关系编码、视觉审查与配图系统。 |
| `references/style/coding/systems/announcement-poster-visual-system.md` | 通知、喜报、邀请函与战报的底图、字体、配色和构图系统。 |
| `references/style/coding/systems/vi-visual-system.md` | VI 的字体、色彩、图像、背景、应用与品牌联动视觉系统。 |
| `references/style/coding/systems/logo-visual-system.md` | Logo 的创意策略、结构机制、提案背景、配色和应用推导系统。 |

#### Scenarios：品类事实与结构

| 文件 | 定义 |
|---|---|
| `references/style/coding/scenarios/logo-spec.md` | Logo 的品牌事实、标志结构、响应式变体、提案与交付。 |
| `references/style/coding/scenarios/vi-spec.md` | VI 的视觉 DNA、品牌系统、应用系统和交付。 |
| `references/style/shared/logo-ip-wordmark-background-reference.md` | Logo IP 角色压缩、角色与品牌名锁定、字标描边层级、身份容器及白底／黑底／透明背景处理规则；Logo、Logo 系统和 VI 命中时与对应品类 Ref 一并完整读取。 |
| `references/style/coding/scenarios/announcement-poster-spec.md` | 通知、喜报、邀请函和节庆贺图的事实与版式职责。 |
| `references/style/coding/scenarios/social-long-image-spec.md` | 社媒长图的信息链、章节职责和 Brief。 |
| `references/style/coding/scenarios/social-carousel-spec.md` | 可编辑社媒套图／轮播的页链、角色页和平台补充；默认纯图套图不读取。 |
| `references/style/coding/scenarios/ecommerce-detail-page-spec.md` | 电商详情页的购买决策链、逐屏职责和事实保护。 |
| `references/style/coding/scenarios/resume-spec.md` | 简历事实、职业路由、ATS、人像和页面结构。 |
| `references/style/coding/scenarios/tri-fold-spec.md` | 三折页折法、面板语义、展开顺序和内容结构。 |
| `references/style/coding/scenarios/menu-spec.md` | 菜单的类别、菜品、规格价格关系和点单阅读结构。 |
| `references/style/coding/scenarios/mind-map-spec.md` | 思维导图的节点、关系依据、结构和展示视图。 |
| `references/style/coding/scenarios/flowchart-spec.md` | 流程图的步骤、条件、泳道、循环与异常路径。 |
| `references/style/coding/scenarios/knowledge-graph-spec.md` | 知识图谱的实体、关系、来源、时间与冲突状态。 |
| `references/style/coding/scenarios/personal-card-spec.md` | 名片、会员卡及权益卡的事实字段、正反面职责和系列变量。 |

### Rendering：渲染能力协议

| 文件 | 定义 |
|---|---|
| `references/rendering/font-recommendation-list.md` | 字体视觉选型的统一入口；按语种、角色、形态和气质形成候选并以真实文案试排。 |
| `references/rendering/font-family-library.md` | 字体来源、许可、Catalog、CDN、回退和可用性契约。 |
| `references/rendering/shape-library.md` | 原生图形选择、组合、复用 token 与降级规则。 |

### 可复用 CSS：分阶段查询与读取

Spec 内容骨架与 Visual 草案形成后，按品类 Visual 查询整页候选摘要（简历可由适配布局进入关联组合），必要时读取设计正文，再补局部原子；Brief 冻结后才读取选中实现、依赖与必要模板，素材就绪组装时校核绑定。以下为按需定位入口，不要求在视觉能力校验时通读实现；不要先跳过本库，再将其判断为“未提供配方”：

- [组件布局与字体](assets/templates/css/layouts/layout-and-type.md)：留白、字级、行高、错位与两种内部密度；页面布局从分类入口读取；
- [容器形状](assets/templates/css/shapes/containers.md)：结构、圆角、页签、文件夹轮廓与遮罩；
- [材质与光照](assets/templates/css/surfaces/materials.md)：塑料、玻璃、纸纹、SVG 资源短引用与光照参数；
- [配色](assets/templates/css/colors/palettes.md)：颜色职责、默认值与完整配色覆盖；
- [组合配方](assets/templates/css/combinations/recipes.md)：原子组成、局部覆盖与可复制模板。

新增的配色、页面布局、光场、织纹和轮廓分支见 [CSS 分类入口](assets/templates/css/README.md#按视觉分类直接读取)，按需求读取对应文件。各文件直接保存参数、默认值、依赖、代码和用法。未知候选使用 [`scripts/runtime/query-css-library.py`](scripts/runtime/query-css-library.py) 限量 `search`，已知候选先用 `describe` 比较摘要，摘要不足时用 `get <ID> --prose` 补读设计正文；Brief 冻结后再对选中实现用 `get --dependencies` 读取正文与依赖，必要结构用 `template` 精确提取。不要从目录寻找参数，也不要在一次并行请求中同时完成首次候选比较和依赖该结果的实现读取。作品的品类 Spec 与视觉系统仍按原流程选择。风格词的拆解、候选筛选和节点绑定见 [Brief → HTML → CSS](assets/templates/css/README.md#brief-routing)；目录只负责召回与定位，不按一个风格名强制整套套用。

现成组件按组合配方定位行内 article，再应用所选配色、密度和局部参数；改原子时以分类正文中的 CSS 代码块为源，同步受影响模板。索引路径相对 Skill 根目录，正文链接相对当前文件。将所选 ID、作用元素与覆盖值记入现有 HTML，优先级遵循 [HTML 组装规则](references/workflow/html-assembly.md)。

可复用 SVG 统一随包存于 [assets/svg](assets/svg)，分类正文与源模板只写 `asset:svg/文件名.svg` 短引用；不要默认读取 SVG 原文或输出编码长串。组装完成后运行 [内嵌脚本](scripts/runtime/inline-svg-assets.py)，具体用法见 [SVG 资源调用](assets/templates/css/README.md#svg-assets)。脚本根据自身位置找资源，无需固定本地路径；需要改变 SVG 内部几何时才按需读取对应文件。 可编辑弧形文字使用 [SVG 路径排字](assets/templates/css/layouts/layout-and-type.md#text.arc) 的生成与 DOM 插入步骤；普通纹理仍走 URL 内嵌。

保留原固定画布、字体和交付协议；伪元素展开为实际节点，正式 HTML 只含行内样式与内嵌 SVG，不保留 asset: 引用、外部 CSS、资源文件或索引运行时依赖。新组合按实际阅读尺寸检查长文案、字体、透明背景和遮罩边界。

### CLI：画布读写

| 文件 | 定义 |
|---|---|
| `references/cli/README.md` | 命令总览、公共调用契约，以及读取、写入、回读、失败对账和停止策略；同步自仓库根 CLI reference。 |
| `references/cli/get-workspace.md` | `+get-workspace` 仅用于显式查询、恢复或排障；不是无 ID 创作任务的初始化入口。 |
| `references/cli/workspace-create.md` | `+workspace-create` 建一张新画布并返回画布 ID。 |
| `references/cli/tree.md` | `+tree` 的参数、请求和返回。 |
| `references/cli/ls.md` | `+ls` 的参数、请求和返回。 |
| `references/cli/get.md` | `+get` 的 ID 限制、请求和完整内容返回。 |
| `references/cli/create.md` | `+create` 单对象写入。 |
| `references/cli/create-batch.md` | `+create-batch` 多对象写入。 |
| `references/cli/update.md` | `+update` 只改顶层 Item / Frame 的 `brief`、`path` 等元数据；HTML 内容或样式变化需重新上传并创建新的顶层 HTML Item。 |
| `references/cli/update-batch.md` | `+update-batch` 多对象更新。 |

`find` 是编辑读取策略的预留命令，当前没有对应 reference 文件；只有仓库实现并提供正式契约后才能调用。

### Items：画布元素协议镜像

| 文件 | 定义 |
|---|---|
| `references/items/README.md` | Item／Frame 公共属性、`title`／`brief`、绝对 path 和 batch 结构。 |
| `references/items/fonts.md` | 字体相关协议入口。 |
| `references/items/image.md` | IMAGE 的资产短链、创建与替换规则。 |
| `references/items/video.md` | VIDEO 的资产短链、创建与限制。 |
| `references/items/text.md` | TEXT 统一样式、混合样式拆为独立 Item、内容与排版字段。 |
| `references/items/shape.md` | SHAPE 类型、填充与描边。 |
| `references/items/line.md` | LINE 点位、箭头与描边。 |
| `references/items/HTML.md` | 顶层 HTML Item 的上传、创建、回读和版本边界。 |

### HTML：Coding 渲染定义

| 文件 | 定义 |
|---|---|
| `references/html/coding-rendering.md` | HTML5 文档结构、CSS 布局、文字、素材、实际渲染与交付契约。 |

`references/html/coding-rendering.md` 是 最终 HTML的唯一协议事实源。`references/items/` 仅在任务仍需同步写入 Canvas Workspace 时提供平台 Item 参考，不约束 HTML DOM 结构。

### 新增执行资源

- [Mobile 直接交付](references/workflow/mobile-app-direct-delivery.md)：环境前置分流、本地 Brief 与媒体／HTML 专用交付。
- [纯图套图与长页拼接](references/workflow/pure-image-sequence.md)：主路由已锁定 pure-image 的社媒套图及已授权纯图长页读取。
- [固定画布预览适配器](scripts/runtime/shot.py)：直接使用 Playwright／Chromium、校验页尾与完整 PNG 尺寸。
- [等宽拼接](scripts/runtime/stitch-images.py)：拼接已核验的等宽图片，不负责改图或修接缝。
- [字体推荐入口](references/rendering/font-recommendation-list.md)：精选候选、确定性查询诊断、真实文案试排与正式 HTML 资源门禁的顺序。

## 三、统一生产契约

pure-image 任务只维护轻量 Brief、Prompt 与实际产物记录；默认纯图套图在同一 Brief 中维护共享系列与逐页计划，其他纯图系列／长页按需维护页序／分段计划。可编辑套图在同一完整 Brief 与共享素材清单中规划封面及内页素材，所有页面按正常素材生产与 HTML 组装执行，不设首页完整终图单元。所有 HTML 路线维护完整自然语言 Brief，且由该 Brief 直接驱动最终 HTML。纯 Coding 不创建素材清单或全量实现参数副本；DOM 坐标、层级、字体、颜色、CSS/SVG 和资产消费位置只在 HTML 中维护。

AI + Coding 在首次正式图像调用前建立轻量 `asset-manifest.json`，只冻结：

1. 所消费 Brief 的路径、版本与冻结状态；
2. 每张正式图片的用途、生产方式、参考输入、Prompt、比例、尺寸、安全区和消费者；
3. 核心商品、品牌或 Logo 的唯一母版来源与身份不变量；
4. 后处理要求、准出标准和未解决阻断项。

素材就绪后在原记录回填真实 URI、尺寸、Alpha 与版本，不再建立第二个就绪态规划文件。KV 视觉澄清是唯一允许早于正式素材清单的图像生成例外，由完整候选 Brief 与 `kv-contract.json` 驱动。不得先做任意比例素材，再靠非等比拉伸塞入版面。

过程文件保存在当前项目 `.creative-design/<task-id>/`，按需包含 `brief.md`、`asset-manifest.json`、`prompt-log.md`、版本化 HTML 和验证记录。用户原始文件不得覆盖。

艺术标题不按新建／编辑区分处理方式：消费者背景已知且稳定时可用纯色底＋节点级混合模式；需要透明复用、跨背景使用、背景未知或严格保色时使用抠图。其他主体和透明素材继续按自身消费者判断，不因艺术字路线自动切换。

## 四、校验、排障与交付

页面自检执行失败时统一读取 [预览策略](references/workflow/html-preview.md)：允许跳过自检并继续可完成的交付，但必须明确记录预览未验证；下文预览必展要求以存在可用预览为前提。Mobile 无预览时如实说明可视交付未完成。

`shot.py` 退出码 `1` 表示检查已完成且发现问题，必须修正并重跑；退出码 `1` 本身不阻断默认 Canvas 的 HTML 上传、Item 创建与回读。只有退出码 `3` 的执行失败可记录为“预览未验证”。

创建、大改或编辑完成后执行 [交付校验](references/workflow/validation.md)。失败时读 [排障流程](references/workflow/troubleshooting.md)，回到最小失败单元修复，不盲目整页重建。

分图层 Coding 只使用标准 HTML/CSS，并遵循 `references/html/coding-rendering.md`。复杂自由路径可内嵌 SVG；禁止使用自定义 Canvas 协议、JSX 或整图压平替代可编辑 DOM。每个完整详情页、长图或其他独立作品只生成一个固定画布 HTML5 文档；同尺寸完整预览图上传 CDN、核验公网链接并以 Markdown 图片展示；预览截图不创建 IMAGE Item、不调用 `present_files`。默认 Canvas 环境再上传完整 HTML、创建顶层 HTML Item 并 `+get` 回读，将 `<workspace_id>?item_id=<item_id>` 作为单值传给 `present_files` 输出对应画布卡片；Mobile 环境到预览展示即止，不上传 HTML、不执行 CLI 或 Item／卡片步骤。禁止 HTML Frame，也禁止把内部章节拆成平台 Item。社媒长图 Hero 按品类规则成为整体图片层，其内部文案不假称独立可编辑；其余分层区域仅准入的唯一艺术主标题可以按最终消费者选择节点级混合模式或真实透明抠图，并通过对应背景效果、字形和边缘验收后作为图片层使用，其余标题与正文保持为可追溯、可编辑的真实文本 DOM。

交付时说明视觉主张、可编辑范围、素材替换方式、HTML 预览状态、Workspace 写入与回读结果，以及仍存在的已知限制。原始 `.html` 不通过 `present_files` 直接交付；同尺寸完整预览图必须经 CDN＋Markdown 展示；默认 Canvas 的 HTML Item 回读后必须将同一 Workspace ID 与刚回读的 HTML Item ID 拼成 `<workspace_id>?item_id=<item_id>` 单值交给 `present_files` 输出对应卡片。用户另需图片或视频时，只向 `present_files` 提交实际渲染／导出成品。
