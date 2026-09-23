---
name: workrally-ugc-website-video
version: 0.1.0
description: |
  用 WorkRally 画布生视频产出「虚拟达人口播 + 真实网页截图」的网站 / App 宣传短视频：
  达人全程正脸出镜连续说话，本地无头浏览器抓下来的真实页面截图作为悬浮卡片叠在人像上。
  当用户说「给我的网站拍个视频」「官网宣传片」「落地页推广视频」「SaaS 种草」「App 演示视频」
  「产品页视频」并且要真人出镜时命中。
  不处理：建站与部署（那是 website-builder 类流程，本 skill 只截图不发布）、
  实体产品开箱（用 workrally-ugc-unboxing-video）、分步使用教程（用 workrally-ugc-tutorial-video）、
  纯测评种草、试穿、只写脚本不出片、剪辑已有素材、生成假的 UI 界面。
---

# WorkRally UGC 网站视频

产出一条 9:16 竖版成片。一个达人全程在镜头里连续说话，指定 URL 的**真实**移动端截图
作为大号静态卡片叠在人像上。**没有分镜板，也绝不生成任何 UI 界面**。

这个 skill 是「给已有的网站/App 拍宣传视频」，**不是**建站、不是部署。
需要的只是网页截图能力，本地 Playwright 就能做。

## 运行约定

先读 `references/workrally-mcp-mapping.md`，本文不重复工具与参数细节。要点：

- **模型一律动态取**：生图前调 `canvas_image_model_list`，生视频前调 `canvas_video_provider_config`，
  **禁止硬编码 model / provider ID**。源 skill 里的 `soul_2` / `seedream_*` / `seedance_2_5`
  在 WorkRally 全不存在
- **口播靠原生音画**：从 `canvas_video_provider_config` 里挑 `support_audio: true`
  且 `max_video_duration` 够本段时长的 provider，`enable_sound` 不传即默认 `true`。
  **不要**拆成「静音视频 + TTS + 合轨」
- 参考图走 URL：生图放 `input_images`，生视频放 `reference_assets[].url`。本地文件（含网页截图）
  先 `upload_file`
- 多图引用用**位置文本**：提示词里写「第一张图片」「第二张图片」，与数组下标一一对应
- 分辨率是枚举：生图 `5`=2K；生视频 `3`=720P、`4`=1080P，取值须来自该模型的 `resolution_options`
- 提交后按 `task_ids` 逐个 `canvas_get_task` 轮询：生图间隔 3 秒，生视频 3–5 秒
- 不需要调展示类工具，生成卡会自动渲染
- 提示词与台词用**简体中文**；网页截图、ffmpeg、python 一律走**本地 shell**，不要找 `sandbox_exec`
- 追问最多一轮，问题合并成一次问完

## 硬规则

- 屏幕内容永远是从指定站点抓下来的**真实像素**，或用户自己发的截图。
  **绝不生成、重绘、动画化或编造 UI**
- 绝不让用户去录屏。绝不用网络搜索或其他来源去补页面内容
- 达人全程在镜头里，提供连续的音轨主线。截图卡片是叠在达人身上的，不是全屏、不滚动
- 正片段落画面里**不出现实体产品**；只有结尾段可以出现，且必须来自该页面上的真实图片
- 每段都用同一个达人形象 URL，绝不重新生成
- 字幕默认开；只有用户明说"不要字幕"才跳过
- 首次抓取失败立刻给用户一个二选一：自己发截图，或做纯口播版。**不要静默重试**
- 不向用户暴露模型名、task_id、内部阶段和中间文件

## 时长

| 总时长 | 段数 | 各段时长 |
| --- | ---: | --- |
| 4–15s | 1 | 全部时长 |
| 16–19s | 2 | 两段均分，每段不少于 4s |
| 20–30s | 2 | 15、余数 |
| 31–45s | 3 | 15、15、余数 |
| 46–60s | 4 | 15、15、15、余数 |
| >60s | ceil(D/15) | 每段 15，末段不少于 4s |

各段时长还必须落在所选 provider 的 `duration_options` 里；provider 的 `max_video_duration`
小于 15 秒时，按它的上限重算分段数。

## 阶段 0 — 收集输入与边界判断

从用户消息里取：**必需的 URL** · 总时长 · 达人照片或期望性别 · 外形与场景指定 ·
站点类型 / 受众 / 主打功能 · 语言 · 可用的宣传口径 ·
`caption_mode`（默认 `两个都要`，可选 `字幕` / `钩子标题`）。

用户点名要 SaaS 种草 / 站点导览，或者要求「页面必须出现在画面里」，就留在本 skill。
电商产品页链接**只要页面会出现在画面里**也留在这里；页面不出现才交给实体产品向的 UGC skill。
用户要的是"把网站做出来 / 部署上线"就不是本 skill。

缺失时**一次问完**：URL、时长（给 10s / 15s / 30s / 45s 选项）、达人来源、字幕模式。
**不要提供**生成 UI、滚动效果、全屏页面、模型选择、宽高比、音频开关、段数分叉这些选项。

## 阶段 1 — 抓取站点

读 `references/website-capture.md`。在**本地 shell** 里跑本 skill 自带的 `scripts/capture_site.mjs`，
产出：

- 一张移动端整页截图，用来建立段落地图；
- 6–10 张有用的分区截图：首屏/产品、功能、控制台/搜索/编辑器、评价、参数、定价或套餐。

**依赖：Playwright + Chromium。** `npm i -g playwright && npx playwright install chromium`。
脚本在缺依赖时以退出码 `3` 报错并给出安装提示——这是真失败，走下面的失败路径并如实告知用户，
**绝不能把没抓到说成抓到了**。

每张有用的截图 `upload_file` 拿 CDN URL 存下来。跳过导航栏、页脚、logo 墙这类填充内容。
建立一份自上而下的段落地图，同一顺序驱动口播节拍和卡片顺序。

抓取报错、被机器人墙拦、需要登录、页面空白，或可用卡片少于 3 张时，立刻问一次：
**「我自己发截图」** 还是 **「不要网站画面，直接出片」**。
真实截图始终没来就继续做纯口播版，并在最终交付里说明网站画面没能呈现。

## 阶段 2 — 锁定达人

用户给了达人照片：`upload_file` 拿 URL，原样使用，跳过去味那一步。

否则读 `references/ugc-character.md` 和 `references/saas-ugc-character.md`，重新掷一组多样性随机数，
写一条干净的、不含任何产品的达人提示词，提交：

```jsonc
canvas_generate_image({
  model: "<canvas_image_model_list 返回的 model_id>",
  prompt: "<达人提示词，中文>",
  aspect_ratio: "3:4",
  resolution: 5,
  count: 1
})
```

轮询到 `state: 4` 之后，对结果 URL 做一次去味图生图（同一批图生图模型，该 URL 作为唯一
`input_images`，`aspect_ratio: "3:4"`、`resolution: 5`），提示词照抄：

> 完全保持这张竖版人像的取景、构图、姿态、主体与身份——不重新取景、不缩放、不裁切，
> 不改变这个人的脸/头发/身体/服装。只改变微观真实感：真实到毛孔级的皮肤质感与细软汗毛、
> 真实的材质细节、均匀的自然日光带柔和的高光滚降和极轻微的真实传感器噪点，
> 像一张平实的手机前置自拍，全画面清晰。脸的形状/宽度/比例必须 1:1 保持——不要挤压、变窄、
> 瘦脸或拉伸。避免 AI 味：蜡质塑料皮肤、磨皮到没有毛孔、美颜滤镜、过饱和、HDR 光晕、过锐化、
> 青橙调色、浅景深、虚化背景、电影感/单反感。不加文字，不加水印。

被内容安全拦截时换一次种子重试；仍失败就用原始达人图。最终那个 URL 锁成 `character_url`，
每段都用它。

## 阶段 3 — 写口播词与卡片计划

读 `references/saas-monologue.md`。中文写作。结构是**钩子 → 网站解决了它 → 结果 / 行动**。
第一个正片节拍点出站点名，后续正片节拍按抓到的卡片顺序走，结尾段不配卡片。

按约 4.5–5.5 汉字/秒估算：≤10s 约 50 字，11–12s 约 62 字，13–15s 约 75 字，语速在段内要有变化。
存下逐字的 `output/script.txt`、一句 ≤12 字的 `output/hook.txt`，
以及有序的 `{段落标签, 字数}` 节拍表。

## 阶段 4 — 生成口播片段

读 `references/saas-clip-prompt.md`。**所有片段提示词都写完之后再提交**。
每段都是一个连续镜头：没有分镜板、没有分格、没有内部硬切、正片段落里没有网站/UI 画面、没有实体产品。
每条提示词都要重申锁定的身份、9:16 中景取景、头部居中、自然口语普通话（无播音腔）、
有变化的活泼语速、手机麦克风音质、与画面匹配的环境音、无背景音乐。

结尾段要出实体产品时，只能从该页面上取一张真实产品图，`upload_file` 后作为第二个
`reference_assets` 条目，提示词里用「第二张图片」引用。页面上没有可用产品图就换成一个中性的收尾手势。

```jsonc
canvas_generate_video({
  mode: "SubjectToVideo",     // 人物一致性走参考主体
  model: "<canvas_video_provider_config 里 support_audio:true 的 provider>",
  prompt: "<单镜头提示词，中文>",
  count: 1,
  duration: 15,               // 取自该 provider 的 duration_options
  aspect_ratio: "9:16",
  resolution: 4,              // 1080P，取值须在该 provider 的 resolution_options 里
  enable_sound: true,         // 原生音轨 + 口型；不传也是 true
  reference_assets: [
    { type: "image", url: "<达人形象URL>" }
  ],
  task_name: "<站点名_口播_第K段>"
})
```

结尾段被内容安全拦截时，只重跑它、去掉产品参考、达人不变。**绝不重新生成达人**。

提交前逐条自查：正片提示词里出现 `硬切` / `Cut 1` / `分格` / `分镜板` / 实体产品 /
渲染出来的网站、UI、屏幕、浏览器，一律改写后再提交。

## 阶段 5 — 抽帧自检

对每段抽等距帧和 2–3 张说话中的帧，检查：只有一个达人、最多两只手、身份稳定、嘴唇干净、
没有生成出来的 UI、正片段落里没有实体产品、没有烧进画面的文字。只重跑不合格的那一段。

宿主看不到像素时，**如实说明没做视觉检查**。

## 阶段 6 — 合成（本地）

读 `references/screen-broll-and-composite.md`。在**本地 shell** 里 `curl` 下各段片段和卡片图，
按顺序拼接，再在写好的字时间锚点上叠卡片：

- 开头约 1–2 秒的钩子和结尾段不叠卡片；
- 每张卡片约 1.2–1.5 秒，卡片之间留约 0.3–0.5 秒的干净人脸；
- 等比缩放进 ~0.78W × ≤0.60H 的框里，水平居中并略微上移；
- 底部约 15% 留给字幕；
- 音轨直接 copy，视频只编码一次。

没有站点卡片时就只拼口播段落。本机没有 `ffmpeg` 就如实说明并把各段分别交付。
本阶段的产物是 `output/final.mp4`。不要调用 `video_concat`：它不在核心版，也做不了定时叠加。

## 阶段 7 — 字幕

读 `references/subtitles.md`。字幕默认开。用成片音轨的逐字转写做时间轴，
按 `两个都要` / `字幕` / `钩子标题` 一次烧完。**绝不凭空推算时间轴**；转写里没有语音就不烧，
直接交付干净成片。

WorkRally **没有烧字幕工具**（只有 `canvas_generate_video` 的 `enable_erase_subtitles` 字幕抹除），
所以烧字走本地 ffmpeg + 本 skill 自带的 `scripts/`：

- 依赖：`ffmpeg`、`python3`、`python3 -m pip install faster-whisper`
- **中文字幕的字体必须有中文字形**：macOS 用 `PingFang SC`，或装 `Noto Sans SC`
  （`brew install --cask font-noto-sans-sc`）。用没有中文字形的字体会烧成一排方框
- 任一依赖缺失就**如实告知并交付无字幕的干净成片**，不要把没烧成的字幕说成已经烧好

## 阶段 8 — 交付

交付一条成片 URL 和时长。站点抓取失败、成片是纯口播版时必须讲明。
成片要入媒资库时走 `upload_file` + `asset_create`。

## References

- `references/website-capture.md`：真实页面抓取与失败闸门
- `references/ugc-character.md`：达人提示词规则
- `references/saas-ugc-character.md`：站点向选角与片段承接
- `references/saas-monologue.md`：口播弧线与卡片顺序
- `references/saas-clip-prompt.md`：连续单镜头口播提示词
- `references/screen-broll-and-composite.md`：截图叠加配方
- `references/subtitles.md`：默认字幕烧制

不要去读实体产品向 UGC skill 的 references。

## 相对 Higgsfield 原版删掉的分支

- **TikTok 发布链路**（`tiktok_accounts` / `tiktok_connect` / `tiktok_prepare_publish` /
  `tiktok_publish` / `tiktok_publish_status`）：WorkRally 无对应工具，整段删除，交付到 URL 为止
- **计费与额度**：WorkRally 没有计费查询工具，不预估消耗、不报价
- **`ask_user_input` / `ask_user_input_v3`**：那是 ChatGPT 宿主专有的提问工具，本地 Agent 直接在对话里问
- **`unlim_choice` / 云端沙箱 / 服务端 preset 分发**：无对应，全部走本地
