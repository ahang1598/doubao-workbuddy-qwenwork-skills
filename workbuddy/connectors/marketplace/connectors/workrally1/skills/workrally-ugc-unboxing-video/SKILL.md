---
name: workrally-ugc-unboxing-video
version: 0.1.0
description: |
  用 WorkRally 画布生视频产出「达人拆快递」的 UGC 开箱短视频：从封好的箱子开始，
  以产品露出那一刻为高潮，靠视频模型的原生音轨与口型说话。
  当用户说「开箱」「拆箱」「拆快递」「unboxing」「开包裹」「第一眼反应」「好物开箱」时命中。
  不处理：没有开箱环节的测评种草、分步使用教程（用 workrally-ugc-tutorial-video）、
  网站/App 演示（用 workrally-ugc-website-video）、试穿、无人产品广告、只写脚本不出片、剪辑已有素材。
---

# WorkRally UGC 开箱视频

产出一条 9:16 竖版成片，全程同一个达人身份。每块分镜板是一张 21:9 横图，横排四个 9:16 竖格；
一次生视频调用把一块板变成含四个内部硬切的片段：**封箱 → 露出 → 产品特写 → 满足感**。

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

- 全程一个达人形象 URL，中途不重新生成
- 第 1 块板第 1 格永远是**封好、贴着胶带、还没打开的箱子，画面里没有产品**。第 2 格是露出瞬间；
  箱子在第 2 格里退到画面边缘或已经不在，第 3–4 格以及后续所有板里都不再出现
- 真实包装照是可选的。没有就用一个普通牛皮纸快递箱，**绝不编造包装上的品牌**
- 产品分析只做一次，之后逐字复用
- 分镜板串行生成；所有片段提示词写完之后再统一提交生视频
- 每块板都要过去味（de-slop）图生图；两次都被拦截才退回用原始板
- **绝不把文字烧进生成**，额外文字都是渲染后再叠
- 第 1 块板之后不再打招呼、不再自我介绍
- 默认自然口语普通话，用户明确要求才换语言或口音

## 时长与叙事弧

| 总时长 | 分镜板数 | 各段时长 |
| --- | ---: | --- |
| 4–15s | 1 | 全部时长 |
| 16–19s | 2 | 两段均分，每段不少于 4s |
| 20–30s | 2 | 15、余数 |
| 31–45s | 3 | 15、15、余数 |
| 46–60s | 4 | 15、15、15、余数 |
| >60s | ceil(D/15) | 每段 15，末段不少于 4s |

K=1 用 `BOARD_1_CANONICAL_UNBOXING`，K>1 用 `BOARD_K_POST_REVEAL`——后续板继续把玩、使用或演示产品。
各段时长还必须落在所选 provider 的 `duration_options` 里；provider 的 `max_video_duration`
小于 15 秒时，按它的上限重算分段数。

## 阶段 0 — 收集输入

从用户消息里取：产品图或产品链接 · 总时长 · 达人照片或期望性别 · 真实包装照 ·
可用的宣传口径 · 语言与口音 · 明确指定的外形或场景。把需求具体度分成 `auto` / `guided` / `director`。

缺失时**一次问完**：时长（给 10s / 15s / 30s / 45s 选项）、产品、达人照片或性别、有没有真实包装照。
用户说"有包装照"但没发，就再问一次要实际图片并等待——一句"有"不算包装素材。
**永远不要问**模型、分镜板数量、宽高比、分辨率、音频开关、转场、身份训练这些内部机制。

## 阶段 1 — 归一化产品与包装

读 `references/product-intake.md`，得到 `product_reference`（图片 URL）、规范产品描述、
档位、品类、使用机制、相对手掌的尺寸、可见面、以及"这个产品没有的功能"。

真实包装照 `upload_file` 一次拿 URL 存下来；没有就把包装参考置空，走通用纸箱约定。

## 阶段 2 — 锁定达人

用户给了达人照片：`upload_file` 拿 URL，原样使用，不再生成。

否则读 `references/ugc-character.md`，重新掷一组多样性随机数，写一条干净的达人提示词
（画面里不能有产品），提交：

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
一块板一段。第 1 段用一句"我认了"式的自嘲开场或其他能接上露出瞬间的钩子，
在露出那一刻给一个身体反应，中间一个转折，最后自然收束。后续段落接着上一句往下说。

去掉 AI 腔的铺垫、空泛夸赞、重复句和没有依据的功效宣称。
**每一段的第一个字就必须是钩子内容**。成片阶段把逐字口播词存到 `output/script.txt`。

## 阶段 4 — 串行生成分镜板

读 `references/ugc-unboxing-board.md`。K 从 1 到 N，每次一条 `canvas_generate_image`：
`aspect_ratio: "21:9"`、`resolution: 5`、`count: 1`，
`input_images` 顺序是产品 → 达人 →（有则）真实包装 →（K>1 时）上一块已去味的分镜板。
不存在的项直接省略并把后面的位置往前挪，提示词第一行写位置清单
（「参考图说明：第一张图片是产品，第二张图片是出镜达人……」）。

`input_images` 数量不能超过该模型的 `kontext_config.max_input_images`。
K 出结果之后再做 K+1，保留每块板的结果 URL。

### 必做的去味（de-slop）图生图

拿到每块原始板的结果 URL 后，用**同一批图生图模型**再跑一次，把该 URL 作为唯一
`input_images`，`aspect_ratio: "21:9"`、`resolution: 5`，提示词如下（照抄）：

> 完全保持这张横版分镜板的取景、构图、分格布局、镜头距离、人物姿态、主体和产品——不重新取景、
> 不缩放、不裁切、不重排版面，不改变场景、不改变任何人的脸/头发/身体、不改变产品设计。
> 只改变微观真实感，并在四个分格里同等施加：真实到毛孔级的皮肤质感与细软汗毛、真实的材质细节、
> 均匀的自然日光带柔和的高光滚降和极轻微的真实传感器噪点，像一张平实的手机直出照片，全画面清晰。
> 每张脸的形状/宽度/比例必须 1:1 保持——不要挤压、变窄、瘦脸或拉伸。避免 AI 味：蜡质塑料皮肤、
> 磨皮到没有毛孔、美颜滤镜、过饱和、HDR 光晕、过锐化、青橙调色、浅景深、虚化背景、电影感/单反感。
> 产品保持无品牌标识，不新增任何文字，不加水印，不出现任何分格标签。

去味结果 URL 取代原始板往下走。被内容安全拦截时用同一模型换一次种子重试；两次都失败就保留原始板，
不要卡住。K-1 的去味结果作为 K 的上一块参考。

## 阶段 5 — 写提示词并提交生视频

读 `references/ugc-unboxing-clip.md`。**所有片段提示词都写完之后再提交**。
每条提示词要带上 K、N、本段时长、叙事弧角色、逐字口播段落、具体度档位、
达人 / 产品 / 包装的连续性约束、以及允许使用的宣传口径。

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
  task_name: "<产品名_开箱_第K段>"
})
```

`reference_assets` 数量受该 provider 的 `max_image_count` 限制，超了先去掉产品图。
每段一条独立调用，逐个 `canvas_get_task` 轮询，间隔 3–5 秒；只重试失败的那一段。

## 阶段 6 — 抽帧自检

对每段抽等距帧、每个产品特写帧和 2–3 张说话中的帧，检查：画面里只有一个产品实例、最多两只手、
箱子按规则消失、使用机制/尺度/状态前后一致、没有乱码文字、没有竞品品牌、脸稳定、嘴唇干净、
没有烧进画面的文字。只重跑不合格的那一段。

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

用户还没表态就问一次：`字幕` / `钩子标题` / `两个都要` / `不要文字`（默认）。
要的话读 `references/subtitles.md`，时间轴来自成片音轨的逐字转写。

WorkRally **没有烧字幕工具**（只有 `canvas_generate_video` 的 `enable_erase_subtitles` 字幕抹除），
所以烧字走本地 ffmpeg + 本 skill 自带的 `scripts/`：

- 依赖：`ffmpeg`、`python3`、`python3 -m pip install faster-whisper`
- **中文字幕的字体必须有中文字形**：macOS 用 `PingFang SC`，或装 `Noto Sans SC`
  （`brew install --cask font-noto-sans-sc`）。用没有中文字形的字体会烧成一排方框
- 任一依赖缺失就**如实告知并交付无字幕的干净成片**，不要把没烧成的字幕说成已经烧好

交付一条成片 URL 和时长。用户要「发布物料」时，标题、3–5 个话题标签、置顶评论只在对话里给。

## 达人重掷

同一块板或同一次生视频连续两次以失败告终、且症状像是达人形象被内容安全拦截时：
换一组随机数重新生成达人，丢弃依赖它的分镜板，从分镜板生成重来。最多重掷两次。
**参考图缺失时绝不提交生视频**。

## References

- `references/product-intake.md`：产品归一化
- `references/ugc-character.md`：达人提示词规则
- `references/ugc-unboxing-board.md`：四格 21:9 分镜板与箱子规则
- `references/ugc-unboxing-clip.md`：四切口开箱片段提示词
- `references/subtitles.md`：渲染后可选文字

不要去读兄弟 UGC skill 的 references。

## 相对 Higgsfield 原版删掉的分支

- **计费与额度**：WorkRally 没有计费查询工具，不预估消耗、不报价
- **`ask_user_input` / `ask_user_input_v3`**：那是 ChatGPT 宿主专有的提问工具，本地 Agent 直接在对话里问
- **`unlim_choice` / 云端沙箱 / 服务端 preset 分发**：无对应，全部走本地
