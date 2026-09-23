---
name: workrally-ugc-product-video
version: 0.1.0
description: |
  用 WorkRally 画布产出成片的「产品独角戏」UGC 竖版短视频（9:16）：产品是每一格的主角，
  画面里最多出现辅助的手 / 局部身体 / 第一人称视角，**没有人出镜说话**，解说是画外旁白，
  由支持原生音频的视频模型直出。
  当用户说「产品口播视频」「无人出镜的带货视频」「产品演示短视频」「产品当主角的 UGC」
  「只拍产品不要真人」时命中。
  不处理：达人出镜测评（用 workrally-ugc-review-video）、服装试穿上身（用
  workrally-ugc-try-on-video）、开箱为主线、分步教程、SaaS / 网站录屏、普通品牌广告片、
  只要脚本不要成片、剪辑已有素材。明确要「纯无声 / 不要解说」时也不用本 skill，走普通视频生成。
---

# WorkRally UGC 产品视频

产出**一条** 9:16 成片。产品是主角；画面里出现的人始终是辅助的、且**不说话**。
每块分镜板是一张 21:9 大图，里面横排四个 9:16 竖格；一条视频把这四格变成四个内部硬切。

## 运行约定

先读 `references/workrally-mcp-mapping.md`（工具与参数映射，本文不重复）。要点：

- 生图前调 `canvas_image_model_list`，生视频前调 `canvas_video_provider_config`，
  **禁止硬编码任何 model_id / provider**
- 每次生成一条独立提示词、一次独立调用，`count: 1`
- 提交后按 `task_ids` 逐个 `canvas_get_task` 轮询：生图间隔 3 秒，生视频间隔 3–5 秒
- 参考图放 `input_images`（生图）/ `reference_assets`（生视频），都收 **URL**；
  提示词里用「第一张图片 / 第二张图片」按下标引用
- 本地文件先 `upload_file(file_path=…)` 拿 URL；要进媒资库再 `asset_create`
- 提示词用中文；产品包装上的文字保留原文，逐字不改
- 下载 / ffmpeg / python / 抽帧 / 转写 / 拼接全走**本地 shell**，不要找 `sandbox_exec`；
  脚本随本 skill 分发在 `scripts/`
- 不需要调展示类工具，生成卡会自动渲染

### 原生音画（本 skill 的核心）

画外旁白**就是视频模型自带的原生音轨**。从 `canvas_video_provider_config` 的
`subject_to_video_providers` 里按能力挑模型：**`support_audio: true`**，且
`max_video_duration` / `duration_options` 覆盖本条 clip 的秒数。

- `enable_sound` 不传即为 `true`，**不要显式传 false**
- **不要**再单独调 `canvas_generate_audio` 然后合轨
- 没有任何 `support_audio: true` 的模型时：停下来如实告知用户「当前环境没有支持原生音频的
  视频模型，只能出无声画面」，让用户决定是否继续，**不要**偷偷降级成静音成片再说已完成

## 硬规则

- 画外解说属于本流程范围。用户要的是纯无声广告 → 转普通视频生成，不要改造本流程
- **必须有真实产品参考图**。绝不凭空编造或替换产品
- 每一格产品都是主角。人可以不出现、只有手、局部身体或第一人称视角，
  但绝不锁身份、绝不成为焦点主体
- 只有画外音：没有出镜对白、没有口型、没有打招呼、没有说话的嘴
- 分镜板**逐块顺序生成**；所有 clip 提示词写完之后才开始提交视频
- 每块板都要跑一遍去 AI 感（de-slop）图生图；只有该步两次都失败才允许用原始板
- **绝不**把文字烧进生成。可选的钩子 / 字幕只在成片出来之后加
- 中文旁白优先（跟随用户语言）；用户明确指定语言 / 口音时按用户说的
- 不向用户暴露模型名、task_id、内部阶段和中间机制

## 时长与叙事弧

| 总时长 | 板数 | 每条 clip 时长 |
| --- | ---: | --- |
| 4–15s | 1 | 总时长 |
| 16–19s | 2 | 两条都不少于 4s，如 18 → 14+4 |
| 20–30s | 2 | 15、余下 |
| 31–45s | 3 | 15、15、余下 |
| 46–60s | 4 | 15、15、15、余下 |
| >60s | ceil(D/15) | 每条 15s，最后一条不少于 4s |

**表里的 15 秒是上限假设，不是承诺。** 实际每条 clip 的秒数必须落在所选模型的
`duration_options` 里。模型单条最长只有 10 秒时，按 `ceil(总时长 / 单条最大时长)` 重算板数，
并把重新切分后的板数与每条时长在动工前一句话告诉用户。

板 1 恒定走 `产品亮相 → 演示A → 演示B → 效果收尾`。后续板换成实质不同的演示角度，
以上一块**清洗后**的板为条件延续。

## 阶段 0 — 收集输入

从用户消息里取：产品照片或产品页 URL、总时长、语言与口音、已授权的宣称清单、
是否要音乐、明确指定的场景或演示方式。

**只问缺失的产品和时长**，一次问完。时长给 10s / 15s / 30s / 45s 四个选项。
绝不追问模型、宽高比、分辨率、板数、音频、批量、身份、转场这类内部机制。

产品和时长没定之前不要开始付费生成。后面那次「要不要文字 / 要不要发布文案」是唯一被允许的第二次追问。

宿主没有专用的提问工具（`ask_user_input_v3` 之类是 ChatGPT 宿主专有的，本插件没有）——
**在正常对话里问一句就行**。

WorkRally 也**没有计费 / 额度查询工具**：不要报价、不要预估消耗、不要编造价格。

## 阶段 1 — 产品归一化

读 `references/product-intake.md` 并严格照做。一次性定下：

- `product_reference`：可用的 HTTPS 图片 URL（本地文件先 `upload_file`）。
  生图的 `input_images` 和生视频的 `reference_assets` **用同一个 URL**，没有第二套 ID 要换
- 规范的 `product_description`：机构、手持相对尺寸、可见的那一面、缺失特征、标签处理、一个真实瑕疵
- `tier`、`category`、`voice_gender`

这些值后面逐字复用。绝不推断价格、绝不编造宣称、绝不用图库图或生成图顶替打不开的产品页。

## 阶段 2 — 写旁白

只写画外旁白。≤10s 约 12–20 个词，11–12s 约 20–28，13–15s 约 28–35
（中文按字数折算：≤10s 约 25–40 字，13–15s 约 55–70 字）。
总文案按板切成 N 段，每段再切成四个节拍短句。

用感官或机械上的具体细节，不要泛泛的夸赞。删掉打招呼、重复的意思、AI 味套话、无依据的宣称。
用户给了已授权宣称清单时，只保留清单里的原句，逐字不改。

把最终定稿逐字写到 `output/script.txt`（烧字幕要用它对齐，见阶段 7）。

## 阶段 3 — 逐块生成分镜板

读 `references/ugc-product-boards.md`。K=1..N，每块写完整提示词后提交一次：

```jsonc
canvas_generate_image({
  model: "<canvas_image_model_list 返回的 model_id>",
  prompt: "<板 K 的提示词>",
  count: 1,
  aspect_ratio: "21:9",
  resolution: 5,            // 2K；模型不支持时退到它 resolution_options 的最高档
  input_images: ["<产品图URL>"],   // K>1 时追加上一块清洗后的板 URL
  task_name: "<产品名>_board<K>"
})
```

K>1 时把上一块**清洗后**的板 URL 追加到 `input_images` 末尾，并让提示词里的
「第一张图片 / 第二张图片」与数组顺序一一对应。轮询到 `state=4` 再做下一块。

### 去 AI 感（de-slop，每块必跑）

拿这块板完成后的结果 URL 做一次图生图：同一批 `canvas_image_model_list` 模型，
`aspect_ratio: "21:9"`，`resolution: 5`，`input_images: [<原始板结果URL>]`，提示词固定为：

> 完整保留这张横向分镜大图以及其中每一个并排竖格的取景、构图、分格布局、镜头距离、姿态、
> 主体和产品——不要重新取景、不要缩放、不要裁切、不要重排版式，不要改动场景、不要改动
> 任何人的脸 / 头发 / 身体，也不要改动产品设计。**只**改微观真实感，且每一格改得一样：
> 真实到毛孔级的皮肤质感与细小绒毛，真实的材质细节，均匀的自然日光带柔和的高光滚降和
> 轻微的真实传感器噪点，一张平实的手机直出照片，全景深。每张脸的形状 / 宽度 / 比例
> 1:1 保持——**不要**把任何一张脸压窄 / 变瘦 / 拉长。避免 AI 味：蜡质塑料皮肤、
> 磨皮到没有毛孔、美颜滤镜、过饱和、HDR 光晕 / 泛光 / 光环、过锐化、青橙调色、
> 浅景深、虚化、电影感 / 单反质感。产品保持无品牌标识的干净状态，不加任何文字，
> 不加水印，不烧分格标签。

清洗结果替换原始板，后面一律用清洗后的 URL。被安全审核拦下时换同一批里另一个模型再试一次；
两次都失败就保留原始板继续，并在内部记下这是降级路径。

## 阶段 4 — 写并提交 clip

读 `references/ugc-product-clip-prompt.md`。**所有** clip 提示词写完之后才开始提交视频。
每条带上 K、N、时长、叙事角色、对应的旁白段、`voice_gender`、产品描述、板参考、已授权宣称。

```jsonc
canvas_generate_video({
  mode: "SubjectToVideo",                 // 参考主体：锁产品一致性
  model: "<canvas_video_provider_config 里 support_audio:true 且时长够的 provider>",
  prompt: "<clip K 的提示词>",
  count: 1,
  duration: <本条秒数>,                    // 必须在该模型 duration_options 里
  aspect_ratio: "9:16",
  resolution: 4,                           // 1080P；以该模型 resolution_options 为准
  reference_assets: [
    { url: "<清洗后板 K 的 URL>", type: "image" },
    { url: "<产品图URL>",          type: "image" }
  ],
  task_name: "<产品名>_clip<K>"
})
```

提交第一条之前自查两件事：`mode` 是 `SubjectToVideo`，模型的 `support_audio` 是 `true`。
`enable_sound` 不传（默认开）。等所有 clip 都出结果；只重跑失败的那条，成功的替换掉旧 URL。

## 阶段 5 — 抽帧质检

拼接之前把每条 clip 拉到本地抽帧看：

```bash
curl -sL -o output/clip1.mp4 '<clip 结果URL>'
ffmpeg -y -i output/clip1.mp4 -vf fps=1 output/qa_clip1_%02d.png -loglevel error
```

逐帧检查：有且只有一个主产品；每个人最多两只手；机构、尺寸、盖子 / 按钮 / 道具状态一致；
声明缺失的特征确实缺失；没有乱码、镜像或不相关的品牌标识；没有烧进画面的文字；
辅助人物的嘴始终闭着。有问题只修那一条重跑。

宿主看不了图时，**如实说明没做画面检查**，不要声称质量已通过。

## 阶段 6 — 拼接与导出

N=1 时那条 clip 的 URL 就是成片，不需要拼接。

N≥2 时在本地按 K 顺序下载、写显式 concat 清单、硬切拼接、`ffprobe` 校验：

```bash
cd output
for i in $(seq 1 N); do curl -sL -o clip$i.mp4 "<clip i 的URL>"; echo "file 'clip$i.mp4'" >> clips.txt; done
ffmpeg -y -f concat -safe 0 -i clips.txt -c copy final.mp4
ffprobe -v error -show_entries format=duration,size -of default=nw=1 final.mp4
```

`-c copy` 报错（各条编码参数不一致）时才重编码一次：
`ffmpeg -y -f concat -safe 0 -i clips.txt -c:v libx264 -crf 18 -c:a aac final.mp4`。

成片要进媒资库就 `upload_file` + `asset_create`。拼接只走本地 ffmpeg，不要调用 `video_concat`。

## 阶段 7 — 可选文字与交付

用户还没表态时问一次：`字幕` / `钩子标题` / `两个都要` / `不要文字`（默认不要），
顺带问要不要发布文案包。

要文字就读 `references/subtitles.md`。时间轴必须来自**成片音轨**的词级转写，
绝不用计划里的节拍。脚本在本 skill 的 `scripts/` 下，跑在本地：

```bash
python3 <skill 目录>/scripts/transcribe_words.py output/final.mp4 -o output/words.json --lang zh
python3 <skill 目录>/scripts/group_captions.py output/words.json -o output/segments.json \
  --video output/final.mp4 --script output/script.txt
python3 <skill 目录>/scripts/make_captions.py output/segments.json -o output/captions.ass \
  --font "PingFang SC" --size 52
ffmpeg -y -i output/final.mp4 -vf "ass=output/captions.ass" -c:a copy output/final_captioned.mp4
```

- WorkRally **只有字幕抹除**（`canvas_generate_video` 的 `enable_erase_subtitles`），
  **没有烧字幕工具**，所以烧字一定走本地 ffmpeg
- **中文字幕必须用有中文字形的字体**：默认 `PingFang SC`（macOS 自带）；
  Linux 装 `fonts-noto-cjk` 后用 `--font "Noto Sans SC"`。用 Montserrat / Metropolis
  这类纯西文字体会渲染成方框或直接丢字，烧之前用 `fc-list :lang=zh` 确认
- 依赖：`ffmpeg` 在 PATH 上 + `python3 -m pip install faster-whisper`（`transcribe_words.py`
  用 faster-whisper 取词级时间戳，首次运行要联网下模型）。任一缺失 → **不烧字幕**，
  交付干净成片并**如实说明**跳过了字幕及原因；绝不手写时间轴、绝不平均分配、
  绝不把没烧字的成片说成已加字幕
- 转写里没有语音时同样什么都不烧，交付 `final.mp4`
- `group_captions.py` 有硬闸门：字幕词不在脚本里时退出码 3。品牌和数字要在
  `output/script.txt` 里按上屏该有的样子写（数字写阿拉伯数字）

交付：给出一条成片 URL 和总时长。加了字幕就交 `final_captioned.mp4`，同时留着
`final.mp4` 作干净母版。用户要发布文案包时**只在对话里给**：一句评论钩子文案、
3–5 个话题标签、一条置顶评论、一句循环点提示——绝不烧进视频。提示用户「视频由 AI 生成」。

## 已删掉的分支（WorkRally 没有对应能力）

- 计费 / 额度查询与开跑前报价 → 删掉，不要编造价格
- 服务端 preset / workflow 热更 → 模板全在本地 `references/`
- marketing studio、爆款预测、建站等 Higgsfield 专有工具 → 删掉
- `ask_user_input` / `ask_user_input_v3` 这类宿主专有提问工具 → 正常对话里问一句
- `unlim_choice` 额度选择、`jobs_wait` 批量等待、`show_generation_by_ids` 展示 → 无对应，
  改成 `canvas_get_task` 轮询；生成卡自动渲染

## 参考文件

- `references/product-intake.md`：产品归一化
- `references/ugc-product-boards.md`：四格 21:9 分镜板提示词
- `references/ugc-product-clip-prompt.md`：四段硬切的视频提示词
- `references/subtitles.md`：可选的按转写时间烧字

不要去读别的 UGC skill 的 references——它们的达人出镜、开箱、教程、试穿、网站契约
与本 skill 的「只有产品」定位冲突。
