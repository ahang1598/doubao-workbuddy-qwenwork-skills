---
name: workrally-brand-asset-creation
version: 0.1.0
description: |
  用 WorkRally 画布生图 + 本地确定性脚本产出成套品牌视觉物料：logo、配色、字体系统、
  样机、周边、包装、门店标识、品牌手册、演示稿、社交图、海报与 Banner。
  从零建立视觉识别，或在用户已有官方素材上做延展与套用；已有素材原样保留，不重绘。
  当用户说「做个 logo」「做套 VI / 品牌识别」「品牌手册」「把 logo 放到杯子/包装/门头上」
  「品牌配色」「品牌字体」「品牌海报/物料」时命中。
  不处理：无品牌的产品摄影（用 workrally-product-photoshoot）、视频封面（用 workrally-thumbnail）、
  普通配图、网站实现、品牌战略与命名策划（除非用户明确要求做新识别）。
---

# WorkRally 品牌视觉物料

做一套彼此自洽的品牌图形。用户给的品牌事实与官方素材是**约束**，不是可以重新演绎的素材。

## 运行约定

先读 `references/workrally-mcp-mapping.md`，本文不重复工具与参数细节。要点：

- 生成前必须调 `canvas_image_model_list` 取模型，**禁止硬编码 model_id**；一组物料内不换模型
- 每个候选一次 `canvas_generate_image`，`count: 1`，各自独立提示词；不要用 `count:N` 凑候选
- 提交后按 `task_ids` 逐个 `canvas_get_task` 轮询，间隔 3 秒；`state=4` 时读 `output_assets`
- 参考图放 `input_images`（URL 数组），提示词里用「第一张图片 / 第二张图片」按下标引用
- 本地图片先 `upload_file` 拿 URL；`input_images` 不吃本地路径，也不吃 SVG
- 提示词用中文；图内文字保留用户原文，逐字不改，不要翻译
- 分辨率是枚举：`4`=1K `5`=2K `6`=4K，取值必须来自该模型的 `resolution_options`
- 比例只能用 `21:9 16:9 4:3 2:1 1:1 1:2 3:4 9:16`。**没有 `4:5` `2:3` `3:2`**——
  分别用 `3:4` `3:4` `4:3` 生成后本地裁切，并告诉用户裁过
- 脚本走**本地 shell**，不要找 `sandbox_exec`
- 不需要调展示工具，生图卡会自动渲染

## 图内文字（本 skill 最大的风险，先读）

logo、海报、包装、门店标识、PPT 页里全是文字，而**图内文字渲染质量在 WorkRally 侧尚未实测**。

默认走「**干净图 + 后期叠字**」：让模型出无文字的底图（提示词收尾写
`画面中没有任何文字、标签或水印。`），再用审定字体在本地把文案排上去（SVG / HTML 排版，
用 `rsvg-convert` 或 ImageMagick 转 PNG，或用 Playwright 整页截图）。这样文案精确、字体真实、
改字不用重新生成。

只有用户**明确**要求「把字烧进图里」才让模型渲字，渲完**逐字**核对，一个字错就算这张不合格。
永远不要把模型渲出来的字说成是用审定字体排的。

## 本地依赖

三个 Python 脚本**只用标准库**，不需要 pip 安装任何包（Python 3.9+）。但它们会调外部命令行工具：

| 能力 | 需要 | 缺失时 |
|---|---|---|
| `brandkit.py state` / `preview` | 仅 Python 3 | —— 无外部依赖 |
| 评审板截图 | Playwright + Chromium（`npm i -g playwright && npx playwright install chromium`） | 交出 HTML 路径让用户自己在浏览器打开，并说明你没看过渲染结果 |
| `brandkit.py logo-export` | `rsvg-convert`（librsvg）+ ImageMagick | 只交 SVG，说明 PNG 导出没跑 |
| `brandkit.py brandbook-build` | 上述两项 + LibreOffice(`soffice`) + Poppler(`pdffonts`) + fontconfig(`fc-cache`/`fc-match`)，**且能访问 `docs.google.com` 与 `fonts.googleapis.com`** | **说明品牌手册做不出来**，给出用户真正有的替代（非规范版演示稿，或单独交付各项已审定素材） |
| 非规范版演示稿（`presentation-deck.md`） | `pip install python-pptx` 或 `npm i pptxgenjs`（skill 不自带） | 装之前先问用户；不装就说演示稿没做，不要拿一组拍平图片冒充 |
| 文档/字体解析（PDF、PPTX、字体文件） | Poppler、LibreOffice、`fc-scan` 或 `pip install fonttools` | 说明这部分分析没做，别靠缩略图猜 |
| 尺寸裁切 | ffmpeg 或 ImageMagick | 说明没裁，交原始比例 |

macOS 安装：`brew install librsvg imagemagick poppler fontconfig` / `brew install --cask libreoffice`。

**如实告知，不要假装。** 没跑出 PDF 就说没跑出 PDF，不要拿别的东西冒充；不要自己写一个
PowerPoint 脚本去顶替 `brandbook-build`。

## 范围

默认做**图形生产**，不做品牌战略。

- 用户给的定位、受众、调性、文案、logo、颜色、字体、图形参考都是权威输入
- 不要发明或改写使命、价值观、定位、受众、语气、命名、传播口号，除非用户明确要求做品牌创建/战略
- 只有明确要求时才做新 logo 或更大范围的识别系统
- 方向选择用简单的视觉概念板。不做插画体系、摄影方向手册、动效、声音、3D 延展

## 用户可见的进度

- 内部流程保持私密。**永远不要**复述 Design Brain 推理、Creative DNA、机制、提示词增强、
  模型查询、工具选择、状态写入、校验轮次或阶段路由
- 每一批可见生成最多发一句状态，只讲在做什么产物，例如「我在生成三个 logo 方案」
- 那一句之后，直到评审或交付为止不要再发流程性文字
- 不要在每次调工具前预告一遍。工具活动界面上已经能看到
- 用户选定后简短确认，直接进入下一个可见产出。
  好：「选定 Berry Kiss。我在生成三个 logo 方案。」
  坏：「Design Brain 给出了三个机制，现在我把每个增强成生产提示词。」
- 跟成品一起给设计理由可以；边做边讲过程不行

## 脚本与状态

Brandkit 的审批账本是 `.brandkit/state.json`，落在**本次品牌任务的工作目录**里。
整个任务从头到尾用同一个目录（用户没指定就建 `./brandkit-work/<品牌名>/` 并告诉他在哪）。

```bash
cd <工作目录> && mkdir -p .brandkit brandkit
python3 <skill 目录>/scripts/brandkit.py state --action get_status
python3 <skill 目录>/scripts/brandkit.py state --action <写动作> --input brandkit/input.json
python3 <skill 目录>/scripts/brandkit.py preview --input brandkit/reviews.json
python3 <skill 目录>/scripts/brandkit.py logo-export --input brandkit/logo-export.json
python3 <skill 目录>/scripts/brandkit.py brandbook-build --input brandkit/brandbook.json
```

结构化入参一律用带引号的 heredoc 写文件（`cat > brandkit/input.json <<'JSON' … JSON`），
**绝不**把用户文本插进 shell 命令参数里。详见 `references/handoff.md`。

产物是本地文件。只有在用户要它进媒资库、或后续生成需要一个 HTTPS URL 时，才走
`upload_file` +（可选）`asset_create`。WorkRally 短链约 5 小时过期，**不要**把短链当作
已审定素材的持久记录——存本地路径。

## 核心流程

1. **判定请求类型。**
   - `apply-existing`：用已有官方素材做新图形
   - `extend-partial`：只补缺失的视觉决策
   - `create-identity`：仅在用户明确要求新 logo / 新识别时才允许
   - 记住首条消息里点名的交付物与约束，之后不要丢，也不要再让用户重选范围一次
2. **读审批状态。** 读 `references/handoff.md`，跑 `state --action get_status`。
   后面只加载当前阶段真正需要的那个模块，不要读无关状态，也不要拿「最新一次生成」当审批。
3. **读 `references/intake.md`。** 先解析首条消息与附件，再一次性问一组真正卡住产出的缺口。
   已经答过的不要重问，局部任务不要强推完整识别问卷。
4. **盘点、分析并锁定已有素材。** 读 `references/asset-analysis.md`。逐个检查素材，
   区分官方素材与灵感参考，用户声明为官方的 logo / 配色 / 字体立刻用对应的
   `lock_authoritative_*` 独立锁定，并用 `set_visual_axes` 存归一化的视觉轴。
5. **算出这次产出真正需要哪几个槽位。** 默认**不要**要求完整 Essential Kit：
   - 只要 logo → logo
   - 只要配色 → 配色
   - 只要字体 → 字体
   - 符号类样机 / 周边 / 无文案包装 → logo；涉及颜色或应用决策时加配色
   - 带文字的社交图、包装、海报、门店标识 → logo + 配色 + 字体
   - 品牌手册或演示稿 → logo + 配色 + 字体
6. **只补缺的必需槽位。** 读 `references/brandkit-design-brain.md`、`references/concept-boards.md`、
   `references/inline-widgets.md`，以及缺的那一个 `references/palette.md`、`references/logo.md`
   或 `references/typography.md`。用户选中某一项就立刻用 `approve_palette` / `approve_logo` /
   `approve_typography` 单独存，不要等合并审批。
7. **合并评审只在有用时做。** 用户要完整识别 / Brandkit，或主动要求一起看时，
   把各自已审定的槽位渲成一张合并 HTML 板。那是展示视图，不是又一道审批闸门。
8. **回到原始请求。** 必需槽位一审定就继续做首条消息里点名的交付物。
   除非原始范围确实有歧义，否则不要再问一次要做什么。
9. **只加载被请求的产出模块：**
   - logo 或 logo 规范 → `references/logo.md`
   - 配色 → `references/palette.md`
   - 字体推荐或字体系统 → `references/typography.md`
   - 品牌手册 → `references/brandbook.md`
   - 演示稿 → `references/presentation-deck.md`
   - 社交图 / 轮播 → `references/social-templates.md`
   - 海报 / Banner → `references/posters-banners.md`
   - 包装图稿 → `references/packaging.md`
   - 门店与空间标识 → `references/signage.md`
   - 周边图稿 → `references/merchandise.md`
   - 包装 / 设备 / 标识 / 周边 / 生活场景的可视化 → `references/mockups.md`
10. **走查并审批下游元素。** 读 `references/qa-and-iteration.md`。只修不合格的那一件。
    用户明确通过后才用 `approve_brandbook_element` 存最终页面 / 模板 / 样机，
    并如实传入这件产出实际用到的 `required_slots`。

## 路由守则

- **新识别**：只创建原始请求需要的元素。为了生成新 logo 而定的配色是必需的上游依赖，
  即便 logo 是唯一交付物；但只要 logo 时字体不是必需的。
- **交互式新 logo 顺序**：按 `references/concept-boards.md` 来——先给配色选项，等用户选，
  用 `approve_palette` 存下来，再生成三个 logo 候选。意向里的颜色 / 风格偏好只是偏好，
  **不等于**已选定配色，不构成跳过配色评审的理由。只有明确的自动 / 免打扰模式可以跳过评审，
  但仍必须选定一套确切配色、用 `approve_palette` 存成功之后，才能进入提示词增强与生图。
- **已有识别**：把用户给的官方元素各自独立锁定，必需槽位齐了就直接往下做。
  已有官方 logo 时，**永远不要**跑 logo 提示词增强或重新生成 logo。
- **部分识别**：保留每一个已审定 / 已提供的槽位，只创建这次产出缺的那些。
- 交互模式下，每次视觉评审之后**停下**等用户在聊天里正常回复。明确的自动 / 免打扰模式下，
  仍然要出评审、存下选中的槽位，然后不提问直接继续。
- **永远不要**从沉默或工具成功推断审批。只有在明确的自动 / 免打扰模式下才代用户做选择，
  并在审批小结里记下这项授权。
- 用户的明确选择只审批那一个具体元素，立刻用对应的 `approve_*` 存。
  不要顺带索要无关槽位或已审批槽位的批准。
- 局部产出**永远不要**卡在 `essential_kit` 上，只读它实际用到的槽位。
- 除非用户明确要求、或已确认的生产工艺要求，否则不要预告或生成单色 / 反白版本。

明确的自动 / 免打扰模式下，自己选定并存好必需槽位及其上游依赖，然后继续首条消息的交付物。
这个模式**不豁免**状态脚本与评审要求。任何槽位在其状态脚本调用成功之前，
不许说它已锁定 / 已选定 / 已审批 / 已保存。

## 一致性不变量

- 用户提供的官方素材立即固定。生成的配色 / logo / 字体在用户明确选中之前都只是草案。
- 必需的上游锁定没进 `.brandkit/state.json` 之前，不做品牌手册页、社交模板、演示稿、样机。
- 每一件被请求的物料都是独立模块，不要把专门的物料塞进通用模板流程。
- 每一处产出复用**同一份**已审定 logo 的素材引用。
- 把 Brand Lock 的值**原样**抄进每一条生成提示词：确切 hex、字体名与字重、形状语言、
  描边 / 圆角规则、间距、构图、禁用手法。
- 不要每件物料各推各的。所有模块吃同一份 Brand Lock，只改内容、格式与构图。
- 能直接放置或合成的 logo，**绝不**让模型重画。
- 已有官方 SVG 的纯改色一律走 `scripts/brandkit.py logo-export`；生成出来的位图 logo
  没有确定性改色路径，见「已知缺口」。
- 从像素识别字体永远不是确定结论。在拿到源数据或字体文件之前只能标注为「视觉匹配」。
- 生成的图像与可编辑排版层要分开。带文字的物料默认是「干净底图 + 本地叠字」。
- 原样保留用户文案。必须出现在物料上的文字不要改写。
- 已审定的 logo / 配色 / 字体一旦变更，所有依赖它的下游元素全部作废，需要重新审批。
- 改一个已审定槽位不会抹掉无关的已审定槽位。重新检查依赖关系，只重做真正依赖它的那些，
  用户提供的官方 logo 永远不重做。

## 失败策略

- 上传的 PDF/DOCX/XLSX/CSV 按 `references/asset-analysis.md` 的文档路线在本地解析。
  解析不了（或缺工具）就停下，要页面图片或源文件。
- 预览脚本报错，修正具体错误后重试一次；再失败就停下如实报告，**不要**用生成图片顶替 HTML 评审板。
- 增强后的 logo 提示词违反 `references/logo-prompt-enhancer.md` 的输出契约，
  按同一份候选规格重写一次；仍不合格就停。
- 生图请求失败，用同一条提示词重试一次；再失败就停，不要偷偷换模型。
- `logo-export` 报几何不匹配是硬停，绝不退回用生成式改 logo。
- 其他 `logo-export` 失败一律停下并报出脚本原话（脚本自己会列出源色）。
  **不要**用 `grep`、`cp`、`sed`、临时脚本或手改 SVG 当兜底。
- `brandbook-build` 报模板 / 契约 / 样式不匹配是确定性错误，立即停，不要重试也不要建议重试。
- `brandbook-build` 报转换器不可用、失败或超时就停，不要试第二条转换路线，
  也**不要**声称生成了 PDF。
- 没走 QA、没拿到必要审批之前，不要把生成物描述成「已通过」「已完成」或「很漂亮」。
- 不要编造使命、价值观、口味、价格、宣称、统计数据或战略内容。
- 不要只丢文件名。每一份 HTML/SVG/图片产出都要按 `references/inline-widgets.md` 出评审面，
  外加可下载的可编辑文件。

## 已知缺口（照实说，不要编替代品）

| 缺口 | 影响 | 处置 |
|---|---|---|
| WorkRally **没有矢量 / SVG 模型** | 生成的 logo 是位图，不是可编辑矢量 | 不许承诺 SVG / AI / EPS / Figma / PSD。位图 logo 的改色是「重新生成」不是「重新上色」，说清楚。用户要真矢量就如实说需要设计师描摹或用户自备矢量源 |
| `logo-export` 需要真 SVG 源 | 确定性改色 / 单色 / 反白 / 2048 PNG 只对**用户提供的官方 SVG**有效 | 见 `references/logo.md` |
| 品牌手册依赖 Google 域名 + 一堆本地二进制 | 内网或缺 LibreOffice 时完全做不出来 | 按「本地依赖」表预检，做不了就直说，给用户真正有的替代 |
| 图内文字质量未实测 | logo/海报/包装/PPT 里的文字可能出错字 | 默认干净图 + 本地叠字，见上文 |
| 没有计费 / 额度查询工具 | 开跑前无法报价 | **不做**「预估消耗」这一步，也不要编造价格 |
| 没有投放品牌包（brand kit）账号级管理 | 无法创建 / 更新 / 列出投放平台的品牌包记录 | 本 skill 不涉及该场景，用户问起就说没有 |

## 可编辑产出策略

按材料给合适的格式：

- 演示稿 → 可编辑 `.pptx`
- 社交贴、Story、轮播、Banner → 拍平的 `.png` / `.jpg`
- 海报、单个矢量版式 → 几何能忠实表达时给可编辑 `.svg`（**由本地排版生成，不是模型生成**）
- 数字版式 → 用户要求时给可编辑 HTML/CSS
- PDF 与 PNG/JPG 是预览 / 成品格式，不是可编辑源文件
- 生成出来的 logo → 位图，没有矢量源

不要承诺原生 Figma、Canva、PSD、AI、EPS。PPTX/SVG/PDF 可以导进别的编辑器，
但字体和版式会跑；自定义字体必须装在收件人机器上。

## 交付

品牌手册按 `references/brandbook.md` 里更严格的最终回复契约：只给两个文件链接 + 字体安装提示，
不要加下面的小结 / 清单，也不要逐页预览。

其他 Brandkit 产出只给用户要的东西，外加：

1. 一份紧凑的 Brand Lock 小结
2. 一份**只含被请求的**生成物 / 可编辑文件清单。内部用的源 logo、状态快照、字体样张
   不要列进去，除非用户明确要了这些文件
3. 字体安装、导入、矢量、logo 保真方面的限制
4. 每个变体一个清楚的名字，方便用户点名要改哪一个

没有做视觉检查就讲明。提示用户「图片由 AI 生成」。
不要暴露模型名、task_id、内部工艺参考和流程机制。
