---
name: workrally-product-photoshoot
version: 0.1.0
description: |
  用 WorkRally 画布生图产出成品级产品图与产品向品牌静帧：棚拍白底图、电商/详情页主图、生活场景图、
  产品特写带人、Pinterest 竖图、Banner 头图、社交轮播、静态广告变体、虚拟模特试穿、CGI 概念图、风格重绘。
  当用户说「产品图」「白底图」「电商图」「packshot」「产品海报」「给这个产品拍一组图」时命中。
  不处理：亚马逊合规主图套图、视频封面/缩略图（用 workrally-thumbnail）、视频广告、人像写真、UGC 视频。
---

# WorkRally 产品图

产品是画面主角。流程：**选模式 → 读参考文件 → 组提示词 → 生成 → 可选自检 → 交付**。
只针对观察到的缺陷或用户明确指出的问题做修正。

## 运行约定

先读 `references/workrally-mcp-mapping.md`，本文不重复工具与参数细节。要点：

- 生成前必须调 `canvas_image_model_list` 取模型，**禁止硬编码 model_id**
- 每个变体一次 `canvas_generate_image`，`count: 1`，各自独立提示词；不要用 `count:N` 凑变体
- 提交后按 `task_ids` 逐个 `canvas_get_task` 轮询，间隔 3 秒
- 参考图放 `input_images`（URL 数组），提示词里用「第一张图片 / 第二张图片」按下标引用
- 本地图片先 `upload_file` 拿 URL；不要把本地路径塞进 `input_images`
- 提示词用中文；图内文字保留用户原文
- 不需要调展示工具，生图卡会自动渲染

追问最多一次，一到三个问题，每题两三个互斥选项，推荐项放第一个。

## 模式

| 模式 | 意图 | 读 |
|---|---|---|
| `product-shot` | 棚拍白底 / 电商 / 目录 | `references/product-shot.md` |
| `lifestyle-scene` | 产品在真实环境或使用中 | `references/lifestyle-scene.md` |
| `closeup-product-with-person` | 产品特写 + 手部或局部人物 | `references/closeup-product-with-person.md` |
| `pinterest-pin` | Pinterest 竖版 | `references/pinterest-pin.md` |
| `hero-banner` | 宽幅网页 / 邮件 / 活动头图 | `references/hero-banner.md` |
| `social-carousel` | 3–10 张连贯轮播 | `references/social-carousel.md` |
| `ad-creative-pack` | 成套静态投放变体 | `references/ad-creative-pack.md` |
| `virtual-model-tryout` | 生成的成年模特穿戴/使用产品 | `references/virtual-model-tryout.md` |
| `conceptual-product` | 超现实 / 悬浮 / 泼溅 / 雕塑感 / CGI | `references/conceptual-product.md` |
| `restyle` | 保留主体，只换美学风格 | `references/restyle.md` |

不要吞掉相邻场景：亚马逊合规主图与 A+ 内容需要专门的合规流程；会动的产品广告是视频生成；
视频封面归 `workrally-thumbnail`；达人测评 / 开箱 / 教程 / 试穿视频归对应 UGC 流程（尚未移植）。

## 意图收集

先从用户已给的信息里解析：产品描述或确认过的产品图、模式/用途、变体数量、视觉方向、
宽高比、图内确切文案、品牌色、是否要求全自动。

用户说「全自动」「不要问」「直接做」且给了产品图或可用的产品描述时，一个都不要问，
按下面静默补齐，用一句话说明最终配方后开工，**不要写成问句**：

- 3 个变体
- 未指定的棚拍走 `clean-studio`
- 用途未暗示其他比例时用 `1:1`
- 配色取产品自身可见颜色或对话里说过的，否则中性
- 工艺描述词从 `references/photographer-references.md` 匹配

只有下列会卡住生成的信息缺口才问，按此顺序：

1. `product`：既没有确认的产品图，也没有可用的视觉描述
2. `style`：从产品或投放位推不出合适预设
3. `count`：数量会实质改变交付物
4. `ratio`：指名的投放位确实有歧义
5. `revision`：用户否定了结果但没说是哪里不对

**永远不要问**模型、分辨率、提示词结构、负向提示词、精修、摄影师、镜头、色温、光圈、
布光术语这类内部机制。

## 输入素材

- 纯文字产品可以做，前提是品类、形态、包装、材质、颜色、标签处理、辨识特征描述得够清楚
- `restyle`、`virtual-model-tryout`、`closeup-product-with-person` **必须**有真实产品图，不要凭空编
- 只用对话里已有的品牌与产品事实。不要编造材质、定价、颜色、标签文案或产品功能

## 选模式与读参考

按交付物意图选。平台/格式优先于环境：Pinterest 图优先于生活场景，Banner 优先于生活场景，
轮播优先于单场景，产品带人特写优先于泛生活场景。`restyle` 只在主体与构图基本不变时用。

生成前读这些（**不要**十个模式文件全读）：

1. 选中的 `references/<mode>.md`
2. `references/typography.md`
3. `references/photography-vocabulary.md`
4. `references/photographer-references.md`
5. `references/negative-prompts.md`
6. `references/refinement-pass.md`

## 提示词约定

首次提交前调一次 `canvas_image_model_list`，挑一个 `kontext_config.max_input_images ≥ 1`
且 `resolution_options` 含 2K（枚举 5）的模型。同一组图内**不要中途换模型**。

- 按选中模式的分区模板组装（`[SUBJECT]` `[COMPOSITION]` `[LIGHTING]` …），分区结构保留，内容写中文
- `resolution: 5`（2K）。该模型不支持 2K 时退到它 `resolution_options` 里的最高档，并告知用户
- 模型 `infer_quality_options` 非空时可传 `quality`；为空时**不要**传这个字段
- 追加 `references/negative-prompts.md` 里适用的约束段
- 按 `typography.md` 的三种情况处理文字；用户没要求预留文字区时不要硬留空白带
- 变体之间要在构图、预设、钩子或场景上**实质不同**

摄影师、刊物、零售商、竞品、第三方影棚名称只是内部工艺锚点。组提示词前必须翻译成具体的
光线、配色、构图、材质、摄影语汇。**这些名字不得出现在**提示词、追问、进度、报错、日志或交付说明里。
用户自己的品牌名只有在它是产品上要保留的实体文字时才可以出现。

每次提交前自检：提示词里没有摄影师名、刊物名、零售商/竞品名、内部预设代号。

## 一组图里保持同一个产品

纯文字产品要出多个视角时：先生成第 0 张并等它完成，把**它的结果 URL** 作为后续每个变体的
`input_images[0]`，提示词里用「第一张图片」引用。整组只改场景、光线、镜头。

用户给了产品图时，全组首轮都用那张图，不要另外生成一张"参考图"。
换成不相关的新产品时另起一组，不要借用上一个产品的参考图。

## 生成与精修

首轮每一项形如：

```jsonc
canvas_generate_image({
  prompt: "<按模式模板组装的中文提示词>",
  model: "<canvas_image_model_list 返回的 model_id>",
  aspect_ratio: "<模式指定比例>",
  resolution: 5,
  count: 1,
  input_images: ["<产品图 URL；纯文字产品首轮省略>"],
  task_name: "<产品名_模式_变体N>"
})
```

用返回的 `task_ids` 轮询。已完成的变体**冻结**，不要重复提交；轮询超时不等于生成失败。

需要精修时读 `references/refinement-pass.md`，只修那一个变体：沿用它的比例，
把**该变体最新一次完成的结果 URL** 作为唯一 `input_images`，写一条聚焦的修正指令，
明确「改什么」和「必须保持不变的是什么」。每个变体最多两次精修。
轮播或广告套图要先看整组一致性，只修坏掉的那几张。

没有观察到缺陷、用户也没提具体修改时，直接交付首轮结果。
用户笼统说不满意又无法看图时，问一句要改什么，不要自己编一个缺陷出来。

## 等待与停止

维护一个「变体序号 → task_id → 最后状态」的台账。同一组图轮询满 12 轮仍未出结果就停下，
保留 task_id，告诉用户哪些还在生成中；下一轮对话再继续查，**不要**为慢任务重新提交。

超时或临时查询失败不构成重新生成的理由。技术性失败或提交被拒每个变体最多重试一次；
遇到安全、权限、配额、计费类错误直接停下并说明，不要重试。
失败提交与精修都计入每个变体总计 3 次提交的预算，重写提示词不重置这个预算。

## 可选的视觉自检

看图是可选项，不是生成或交付的前置条件。宿主能看图且结果可访问时，比对产品形状、
标识、颜色、材质、构图和图内文字是否符合需求与参考图。

拿不到像素时，**如实说明未做视觉检查**，不要声称质量已通过，也不要凭空花额度做臆测性精修。
缩略图看不清的小字和全分辨率锐度，不要声称已验证。用户明确指出的修改点即使没看图也可以执行。

额度用尽时交付现有最好的一版，并说明已知的遗留问题。某个变体一张都没成功时，
如实报告失败或仍在生成，**不要**声称整组已完成。

## 交付

按请求顺序给出最终图，每个序号恰好一张。用一句话说明模式、预设、比例和做过的修正。
未做视觉检查要讲明。提示用户「图片由 AI 生成」。

不要暴露模型名、task_id、内部工艺参考和流程机制。用户笼统否定时问一个简短的定位问题；
指名了具体问题就只改那一处。
