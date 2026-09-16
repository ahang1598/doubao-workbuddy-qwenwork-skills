---
name: workrally-ugc-tutorial-video
version: 0.1.0
description: |
  用 WorkRally 画布生视频产出「达人手把手教你用」的 UGC 教程短视频：一个固定出镜达人，
  按真实使用顺序分步演示产品，每一步画面上带「步骤N · 小标题」角标，靠视频模型的原生音轨与口型说话。
  当用户说「教程视频」「教学视频」「使用教程」「怎么用」「how-to」「分步演示」「上手指南」
  并且要真人出镜时命中。
  不处理：开箱与拆包（用 workrally-ugc-unboxing-video）、网站/App 演示（用 workrally-ugc-website-video）、
  纯测评种草、试穿、无人产品广告、只写脚本不出片、剪辑已有素材。
---

# WorkRally UGC 教程视频

产出一条 9:16 竖版成片，全程同一个达人身份。每块分镜板是一张 21:9 横图，横排四个 9:16 竖格，
每格是一个真实的产品使用步骤，并在画面上带一条「步骤N · 小标题」角标。
一次生视频调用把一块分镜板变成一条含四个内部硬切的片段。

## 运行约定

先读 `references/workrally-mcp-mapping.md`，本文不重复工具与参数细节。要点：

- **模型一律动态取**：生图前调 `canvas_image_model_list`，生视频前调 `canvas_video_provider_config`，
  **禁止硬编码 model / provider ID**。源 skill 里的 `soul_2` / `gpt_image_2` / `seedream_*` /
  `seedance_2_5` 在 WorkRally 全不存在
- **口播靠原生音画**：从 `canvas_video_provider_config` 里挑 `support_audio: true`
  且 `max_video_duration` 够本段时长的 provider，`enable_sound` 不传即默认 `true`。
  **不要**拆成「静音视频 + TTS + 合轨」
- 参考图走 URL：生图放 `input_images`，生视频放 `reference_assets[].url`。本地文件先 `upload_file`
- 多图引用用**位置文本**：提示词里写「第一张图片」「第二张图片」，与数组下标一一对应
- 分辨率是枚举：生图 `5`=2K、`6`=4K；生视频 `3`=720P、`4`=1080P，取值须来自该模型的 `resolution_options`
- 提交后按 `task_ids` 逐个 `canvas_get_task` 轮询：生图间隔 3 秒，生视频 3–5 秒
- 不需要调展示类工具，生成卡会自动渲染
- 提示词与台词用**简体中文**；ffmpeg / python 一律走**本地 shell**，不要找 `sandbox_exec`
- 追问最多一轮，问题合并成一次问完

## 硬规则

- 产品使用方式分析是必做项，绝不能编一个产品做不到的动作
- 全程一个达人形象 URL，中途不重新生成
- 步骤编号是全局的：第 J 块板承载步骤 `4*(J-1)+1` 到 `4*J`
- 每格画面上只允许一条「步骤N · 小标题」角标，不允许任何其他生成文字
- 最后一块板最后一个切口的末尾约 0.5–1 秒是口播 CTA（「链接在评论区」「关注我」），
  它不是第五个步骤，也不出现在角标里
- 分镜板串行生成；所有片段提示词写完之后再统一提交生视频
- 每块板都要过去味（de-slop）图生图，且必须保留已有的步骤角标
- 额外的钩子字幕 / 口播字幕都是**渲染后**再烧，不进生成

## 时长与步骤数

| 总时长 | 分镜板数 | 各段时长 | 总步骤 |
| --- | ---: | --- | ---: |
| 4–15s | 1 | 全部时长 | 4 |
| 16–19s | 2 | 两段均分，每段不少于 4s | 8 |
| 20–30s | 2 | 15、余数 | 8 |
| 31–45s | 3 | 15、15、余数 | 12 |
| 46–60s | 4 | 15、15、15、余数 | 16 |
| >60s | ceil(D/15) | 每段 15，末段不少于 4s | 4N |

各段时长还必须落在所选 provider 的 `duration_options` 里；provider 的 `max_video_duration`
小于 15 秒时，按它的上限重算分段数。

## 阶段 0 — 收集输入

从用户消息里取：产品图或产品链接 · 总时长 · 使用说明书或操作要点 · 达人照片或期望性别 ·
可用的宣传口径 · 语言与口音 · 明确指定的场景或外形。

缺失时**一次问完**：产品、时长（给 10s / 15s / 30s / 45s 选项）、达人照片或性别。
只有用户的描述里已经透出口音或人设倾向时才追问口音。
**永远不要问**模型、分镜板数量、宽高比、分辨率、音频开关、转场、身份训练这些内部机制。

## 阶段 1 — 归一化产品与步骤

读 `references/product-intake.md`，得到 `product_reference`（图片 URL）、规范产品描述、
档位、品类、使用机制、可见面、以及"这个产品没有的功能"。

构造 `total_steps = 4*N` 个按时间顺序、物理上真实成立的使用步骤。自然流程不够长就补上真实的
准备步骤和收尾步骤；太长就合并相邻的微动作。用户自己给了步骤清单就一一对应，不改顺序。
产出 `step_captions[]`，每条形如「步骤N · 二到六字小标题」，四条一组。

## 阶段 2 — 锁定达人

用户给了达人照片：`upload_file` 拿 URL，原样使用，不再生成。

否则读 `references/ugc-character.md`，写一条干净的达人提示词（画面里不能有产品），提交：

```jsonc
canvas_generate_image({
  model: "<canvas_image_model_list 返回的 model_id>",
  prompt: "<达人提示词，中文>",
  aspect_ratio: "3:4",
  resolution: 5,        // 2K；该模型不支持就退到它 resolution_options 的最高档
  count: 1
})
```

轮询到 `state: 4`，把 `output_assets[0].url` 锁成 `character_url`，全程复用。

## 阶段 3 — 写口播词

按约 4.5–5.5 汉字/秒估算：≤10s 约 45–55 字，11–12s 约 55–65 字，13–15s 约 65–80 字。
按板拆成 N 段，每段再拆四个步骤节拍。用口语讲**达人此刻手上在做什么**，
主线是教程步骤本身，不是套路化的故事弧。去掉 AI 腔、重复句和没有依据的功效宣称。

末尾留约 0.5–1 秒给 CTA。时间紧就压缩讲解句，**不要**砍掉一个步骤。
成片阶段把逐字口播词存到 `output/script.txt`（烧字幕要用它对齐）。

## 阶段 4 — 串行生成分镜板

读 `references/ugc-tutorial-boards.md`。K 从 1 到 N，每次一条 `canvas_generate_image`：
`aspect_ratio: "21:9"`、`resolution: 5`、`count: 1`，
`input_images` 顺序是产品 → 达人 →（K>1 时）上一块已去味的分镜板，
提示词第一行写位置清单（「参考图说明：第一张图片是产品，第二张图片是出镜达人……」），
并带上这一块的四条步骤角标文案。

`input_images` 数量不能超过该模型的 `kontext_config.max_input_images`；超了就先砍产品图之外的可选项。
K 出结果之后再做 K+1，保留每块板的结果 URL。

### 必做的去味（de-slop）图生图

拿到每块原始板的结果 URL 后，用**同一批图生图模型**再跑一次，把该 URL 作为唯一
`input_images`，`aspect_ratio: "21:9"`、`resolution: 5`，提示词如下（照抄）：

> 完全保持这张横版分镜板的取景、构图、分格布局、镜头距离、人物姿态、主体、产品，以及画面上已有的
> 步骤角标文字——不重新取景、不缩放、不裁切、不重排版面，不改变场景、不改变任何人的脸/头发/身体、
> 不改变产品设计、不改变已有的画面文字。只改变微观真实感，并在四个分格里同等施加：真实到毛孔级的
> 皮肤质感与细软汗毛、真实的材质细节、均匀的自然日光带柔和的高光滚降和极轻微的真实传感器噪点，
> 像一张平实的手机直出照片，全画面清晰。每张脸的形状/宽度/比例必须 1:1 保持——不要挤压、变窄、
> 瘦脸或拉伸。避免 AI 味：蜡质塑料皮肤、磨皮到没有毛孔、美颜滤镜、过饱和、HDR 光晕、过锐化、
> 青橙调色、浅景深、虚化背景、电影感/单反感。产品保持无品牌标识，不新增任何文字，不加水印。

去味结果 URL 取代原始板往下走。被内容安全拦截时用同一模型换一次种子重试；两次都失败就保留原始板，
不要卡住。K-1 的去味结果作为 K 的上一块参考。

## 阶段 5 — 写提示词并提交生视频

读 `references/ugc-tutorial-clip-prompt.md`。**所有片段提示词都写完之后再提交**。
每条提示词要带上 K、N、本段时长、四条步骤角标、逐字口播段落、`is_last_board`、
达人与产品的连续性约束、以及允许使用的宣传口径。

先调 `canvas_video_provider_config`，在 `subject_to_video_providers` 里挑一个
`support_audio: true`、`max_video_duration` ≥ 本段时长的 provider：

```jsonc
canvas_generate_video({
  mode: "SubjectToVideo",     // 产品与人物一致性走参考主体
  model: "<上面挑出来的 provider>",
  prompt: "<片段提示词，中文>",
  count: 1,
  duration: 15,               // 取自该 provider 的 duration_options
  aspect_ratio: "9:16",
  resolution: 4,              // 1080P，取值须在该 provider 的 resolution_options 里
  enable_sound: true,         // 原生音轨 + 口型；不传也是 true
  reference_assets: [
    { type: "image", url: "<去味后的分镜板URL>" },
    { type: "image", url: "<达人形象URL>" },
    { type: "image", url: "<产品图URL>" }
  ],
  task_name: "<产品名_教程_第K段>"
})
```

`reference_assets` 数量受该 provider 的 `max_image_count` 限制，超了先去掉产品图。
每段一条独立调用，逐个 `canvas_get_task` 轮询，间隔 3–5 秒；只重试失败的那一段。

## 阶段 6 — 抽帧自检

对每段抽等距帧、产品特写帧和 2–3 张说话中的帧，检查：产品使用机制正确、画面里只有一个产品实例、
最多两只手、状态与尺度前后一致、脸和嘴唇没有崩坏、步骤角标清晰可读且没被改写、没有多余的新增文字。
只重跑不合格的那一段。

宿主看不到像素时，**如实说明没做视觉检查**，不要声称质量已通过。

## 阶段 7 — 拼接导出（本地）

N=1 直接用那段的结果 URL。N≥2 在本地 shell 里做：

```bash
mkdir -p output
curl -sL -o output/clip_1.mp4 '<第1段结果URL>'   # …按 K 顺序全部下载
: > output/clips.txt; for K in $(seq 1 N); do echo "file 'clip_${K}.mp4'" >> output/clips.txt; done
ffmpeg -y -f concat -safe 0 -i output/clips.txt -c copy output/final.mp4
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 output/final.mp4
```

本机没有 `ffmpeg` 就如实说明，把各段分别交付，不要假装已经拼好。
成片要入媒资库时走 `upload_file` + `asset_create`。

## 阶段 8 — 可选的额外文字与交付

用户还没表态就问一次要不要额外文字：`字幕` / `钩子标题` / `两个都要` / `不要文字`（默认）。
要的话读 `references/subtitles.md`。**画面顶部的步骤角标要保留**，字幕留在底部安全区，
顶部钩子只在明显不压住步骤角标时才加。

WorkRally **没有烧字幕工具**（只有 `canvas_generate_video` 的 `enable_erase_subtitles` 字幕抹除），
所以烧字走本地 ffmpeg + 本 skill 自带的 `scripts/`：

- 依赖：`ffmpeg`、`python3`、`python3 -m pip install faster-whisper`
- **中文字幕的字体必须有中文字形**：macOS 用 `PingFang SC`，或装 `Noto Sans SC`
  （`brew install --cask font-noto-sans-sc`）。用没有中文字形的字体会烧成一排方框
- 任一依赖缺失就**如实告知并交付无字幕的干净成片**，不要把没烧成的字幕说成已经烧好

交付一条成片 URL 和时长。用户要「发布物料」时，标题、3–5 个话题标签、置顶评论只在对话里给。

## References

- `references/product-intake.md`：产品归一化
- `references/ugc-character.md`：达人提示词规则
- `references/ugc-tutorial-boards.md`：四格 21:9 带角标分镜板
- `references/ugc-tutorial-clip-prompt.md`：四切口教程片段提示词与 CTA
- `references/subtitles.md`：渲染后可选文字

不要去读兄弟 UGC skill 的 references。

## 相对 Higgsfield 原版删掉的分支

- **计费与额度**：WorkRally 没有计费查询工具，不预估消耗、不报价
- **`ask_user_input` / `ask_user_input_v3`**：那是 ChatGPT 宿主专有的提问工具，本地 Agent 直接在对话里问
- **`unlim_choice` / 云端沙箱 / 服务端 preset 分发**：无对应，全部走本地
