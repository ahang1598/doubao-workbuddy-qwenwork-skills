---
name: workrally-ugc-try-on-video
version: 0.1.0
description: |
  用 WorkRally 画布产出成片的「服装试穿」UGC 竖版短视频（9:16）：一位出镜达人
  **穿上并展示**一件衣服 / 鞋 / 包 / 首饰 / 可穿戴配件，展示上身效果、版型与面料质感，
  全程锁同一个人物身份和同一件单品；说话声与口型来自支持原生音频的视频模型。
  当用户明确说「试穿」「上身」「穿搭视频」「OOTD」「穿搭展示」「拍一条我穿这件的视频」时命中。
  不处理：不含试穿的达人测评（用 workrally-ugc-review-video）、无人出镜的产品视频（用
  workrally-ugc-product-video）、开箱为主线、分步教程、SaaS / 网站录屏、普通广告片、
  剪辑已有素材。只要文字脚本 / 分镜表 / 穿搭建议时也不用本 skill——那是写作，不是视频生产。
---

# WorkRally UGC 试穿视频

产出**一条** 9:16 成片，一个锁定的达人身份 + 一件可穿戴单品。
每块分镜板是一张 21:9 大图，里面横排八个 9:16 竖格；一条视频把这八格变成八个叙事节拍，
之间是七个硬切。

## 运行约定

先读 `references/workrally-mcp-mapping.md`（工具与参数映射，本文不重复）。要点：

- 生图前调 `canvas_image_model_list`，生视频前调 `canvas_video_provider_config`，
  **禁止硬编码任何 model_id / provider**
- 每次生成一条独立提示词、一次独立调用，`count: 1`
- 提交后按 `task_ids` 逐个 `canvas_get_task` 轮询：生图间隔 3 秒，生视频间隔 3–5 秒
- 参考图放 `input_images`（生图）/ `reference_assets`（生视频），都收 **URL**；
  提示词里用「第一张图片 / 第二张图片 / 第三张图片」按下标引用
- 本地文件先 `upload_file(file_path=…)` 拿 URL；要进媒资库再 `asset_create`
- 提示词与口播用中文；单品吊牌 / 印花上的文字保留原文，逐字不改
- 下载 / ffmpeg / python / 抽帧 / 转写 / 拼接全走**本地 shell**，不要找 `sandbox_exec`；
  脚本随本 skill 分发在 `scripts/`
- 不需要调展示类工具，生成卡会自动渲染
- 没有计费 / 额度查询工具：不报价、不预估消耗、不编造价格
- 宿主没有专用提问工具（`ask_user_input_v3` 是 ChatGPT 宿主专有的）——正常对话里问一句就行

### 原生音画（本 skill 的核心）

达人的说话声和口型**就是视频模型自带的原生音轨**。从 `canvas_video_provider_config` 的
`subject_to_video_providers` 里按能力挑模型：**`support_audio: true`**，且
`max_video_duration` / `duration_options` 覆盖本条 clip 的秒数。

- `enable_sound` 不传即为 `true`，**不要显式传 false**
- **不要**拆成「静音视频 + 单独 TTS + 合轨」：那样口型必然对不上。
  不要调 `canvas_generate_audio` 再去合轨
- 本流程里第 4、6 格是无手参与的面料微距，那两拍是**画外音**，人物在镜头里不说话——
  这仍然由同一条原生音轨承载，不需要额外配音工具
- 没有任何 `support_audio: true` 的模型时：停下来如实告知用户「当前环境没有支持原生音频的
  视频模型，做不出口型对得上的试穿口播」，让用户决定是否继续，**不要**偷偷交付静音画面再说已完成

## 硬规则

- 全程复用同一个 `character_url`
- 板 1 第 1 格是「未穿」状态的中性居家着装 + 一个素色牛皮纸袋。第 2 格起单品已穿在身上，
  袋子**再不出现**
- **绝不**描写换装过程、打开纸袋、从袋里拿出单品。换装由硬切完成
- 第 4、6 格是无手参与的服装微距；不许有手碰到面料
- 没有镜子、没有倒影。锁死发型、脸、单品轮廓、颜色、印花与设计细节
- 分镜板**逐块顺序生成**；所有 clip 提示词写完之后才开始提交视频
- 每块板都要跑一遍去 AI 感（de-slop）图生图；只有该步两次都失败才允许用原始板
- **绝不**把文字烧进生成。可选文字只在成片之后加
- 没有 CTA 尾巴。在最后一句台词上自然收尾
- 中文口播优先（跟随用户语言）；用户明确指定语言 / 口音时按用户说的
- 不向用户暴露模型名、task_id、内部阶段和中间机制

## 安全闸门（与达人相关，生成前先跑）

只用生成的成年人（21 岁以上），或用户有权使用其形象、且已同意的非公众人物成年人。
用户给了一张照片**不等于**授权模仿照片里的人；第三方同意不明确时问一次。
公众人物、名人、未成年人、欺骗性身份使用一律拒绝。绝不克隆或模仿用户提供的人的声音。

生成的达人是演示者，**不是真实顾客**：绝不编造购买、拥有、穿着时长、效果、评分或亲身经历。
用户给的宣称白名单之外，不写任何数字或比较型宣称。有单品的成片对外说明为
品牌演示 / 达人概念片，用户要发布文案包时带上广告 / 合作声明。

## 时长与板的推进

| 总时长 | 板数 | 每条 clip 时长 |
| --- | ---: | --- |
| 4–15s | 1 | 总时长 |
| 16–19s | 2 | 两条都不少于 4s |
| 20–30s | 2 | 15、余下 |
| 31–45s | 3 | 15、15、余下 |
| 46–60s | 4 | 15、15、15、余下 |
| >60s | ceil(D/15) | 每条 15s，最后一条不少于 4s |

**表里的 15 秒是上限假设，不是承诺。** 实际每条 clip 的秒数必须落在所选模型的
`duration_options` 里。模型单条最长只有 10 秒时，按 `ceil(总时长 / 单条最大时长)` 重算板数，
并把重新切分后的板数与每条时长在动工前一句话告诉用户。

叙事角色：

- K=1 `BOARD_1_TRY_ON_CANONICAL`：未穿 → 已穿 → 正面姿态 → 面料特写 → 转身 → 细节 →
  造型姿态 → 最终定格
- K=2 `BOARD_2_TRY_ON_HOME_TOUR`：同一个家里换房间继续
- K=3 `BOARD_3_TRY_ON_OUTDOOR`：全户外；第 2 格起有小雨，头发保持干，湿面料微距，无倒影
- K=4 `BOARD_4_TRY_ON_HOME_REFLECT`：回到室内，落座下来的回味
- K≥5 `BOARD_K_TRY_ON_LOOP`：在已建立的场地与新的相容场地之间交替

## 阶段 0 — 收集输入

解析：单品照片或 URL、总时长、附带的达人照片或希望的达人性别，以及明确给出的场地、
外貌、情绪、语言、口音、宣称、文字选择。把 brief 分档为 `auto` / `guided` / `director`。

**只问真正的缺口**，一次问完：单品、时长（给 10s / 15s / 30s / 45s）、达人照片或性别。
只有 brief 本身透出地域来源或刻意特殊的人物气质时，才顺带给一个口音 / 小怪癖选项。
绝不追问模型、板数、宽高比、分辨率、音频、转场、身份训练。

单品、时长、达人输入没定之前不要开始付费生成。后面那次「要不要文字 / 要不要发布文案」
是唯一被允许的第二次追问。

## 阶段 1 — 单品归一化

读 `references/product-intake.md`。定下并逐字复用：`product_url`（可用的 HTTPS 图片 URL，
本地文件先 `upload_file`；生图与生视频**用同一个 URL**）、规范的可穿戴单品描述、
`tier`、`category`、材质、垂坠感、声明缺失的特征、可见的那一面。
绝不推断价格、宣称，也绝不编造看不到的那一面。

## 阶段 2 — 锁定达人

附了达人照片时：`upload_file` 拿 URL 直接用，不要再确认、不要去修图。

否则读 `references/ugc-character.md`，摇新的多样性骰子、写一条达人提示词，提交一次：

```jsonc
canvas_generate_image({
  model: "<canvas_image_model_list 返回的 model_id>",
  prompt: "<达人提示词>",
  count: 1,
  aspect_ratio: "3:4",
  resolution: 5,            // 2K
  task_name: "<单品>_creator"
})
```

轮询到 `state=4`，把 `output_assets[0].url` 锁为 `character_url`。除了下面那条有上限的
「人物重摇」，中途绝不换身份。

把你写下的特征（年龄段、发型、体型、居家着装锚点）记在自己的笔记里——后面无法再回看这张图，
**写下来的描述就是连续性契约**。

## 阶段 3 — 写口播

≤10s 约 12–20 个词，11–12s 约 20–28，13–15s 约 28–35（中文按字数折算：≤10s 约 25–40 字，
13–15s 约 55–70 字）。按板切段；clip 参考文件负责把一段分配到八个节拍上。

板 1 是一个「我为什么想要它」的个人小故事。后面的板从半句话接上。删掉 AI 味开场、
泛泛夸赞、重复、无依据的宣称，以及任何 CTA。每段的**第一个词就得是钩子内容**，
不能是清嗓子式的开场。

定稿逐字写到 `output/script.txt`；如果可能要烧钩子标题，把那句标题也写到 `output/hook.txt`。

## 阶段 4 — 逐块生成分镜板

读 `references/ugc-try-board.md`。K=1..N，每块写完整提示词后提交一次：

```jsonc
canvas_generate_image({
  model: "<canvas_image_model_list 返回的 model_id>",
  prompt: "<板 K 的提示词>",
  count: 1,
  aspect_ratio: "21:9",
  resolution: 5,            // 2K；模型不支持时退到它 resolution_options 的最高档
  input_images: ["<单品图URL>", "<character_url>"],   // K>1 时追加上一块清洗后的板 URL
  task_name: "<单品>_board<K>"
})
```

`input_images` 顺序：单品 → 达人 → 上一块清洗后的板。提示词里的「第一张图片 / 第二张图片 /
第三张图片」与数组顺序严格对应；数组长度不超过该模型的 `kontext_config.max_input_images`。
轮询到 `state=4` 再做 K+1，并保留这块板的结果 URL。

### 去 AI 感（de-slop，每块必跑）

拿这块板完成后的结果 URL 做一次图生图：同一批 `canvas_image_model_list` 模型，
`aspect_ratio: "21:9"`，`resolution: 5`，`input_images: [<原始板结果URL>]`，提示词固定为：

> 完整保留这张横向分镜大图以及其中每一个并排竖格的取景、构图、分格布局、镜头距离、姿态、
> 主体和产品——不要重新取景、不要缩放、不要裁切、不要重排版式，不要改动场景、不要改动
> 任何人的脸 / 头发 / 身体，也不要改动服装的设计。**只**改微观真实感，且每一格改得一样：
> 真实到毛孔级的皮肤质感与细小绒毛，真实的面料织纹与材质细节，均匀的自然日光带柔和的
> 高光滚降和轻微的真实传感器噪点，一张平实的手机直出照片，全景深。每张脸的形状 / 宽度 /
> 比例 1:1 保持——**不要**把任何一张脸压窄 / 变瘦 / 拉长。避免 AI 味：蜡质塑料皮肤、
> 磨皮到没有毛孔、美颜滤镜、过饱和、HDR 光晕 / 泛光 / 光环、过锐化、青橙调色、
> 浅景深、虚化、电影感 / 单反质感。服装保持无多余品牌标识的干净状态，不加任何文字，
> 不加水印，不烧分格标签。

清洗结果替换原始板，K+1 用清洗后的 K。被安全审核拦下时换同一批里另一个模型再试一次；
两次都失败就保留原始板继续，并在内部记下这是降级路径。

## 阶段 5 — 写并提交 clip

读 `references/ugc-try-clip.md`。**所有** clip 提示词写完之后才开始提交视频。每条带上
K、N、时长、叙事角色、**逐字**的口播段、具体程度档位、人物设定、服装契约与各参考图。
严格执行参考文件里的**六个口型拍 + 两个静默微距画外音拍**。

```jsonc
canvas_generate_video({
  mode: "SubjectToVideo",                 // 参考主体：锁达人身份 + 锁服装
  model: "<canvas_video_provider_config 里 support_audio:true 且时长够的 provider>",
  prompt: "<clip K 的提示词>",
  count: 1,
  duration: <本条秒数>,                    // 必须在该模型 duration_options 里
  aspect_ratio: "9:16",
  resolution: 4,                           // 1080P；以该模型 resolution_options 为准
  reference_assets: [
    { url: "<清洗后板 K 的 URL>", type: "image" },
    { url: "<character_url>",      type: "image" },
    { url: "<单品图URL>",          type: "image" }
  ],
  task_name: "<单品>_clip<K>"
})
```

提交第一条之前自查两件事：`mode` 是 `SubjectToVideo`，模型的 `support_audio` 是 `true`。
`enable_sound` 不传（默认开）。`reference_assets` 的条数不超过该模型的 `max_image_count`。
等所有 clip 都出结果；只重跑失败的那条。

## 阶段 6 — 抽帧质检

拼接之前把每条 clip 拉到本地抽帧看，尤其是服装特写和 2–3 帧说话中的画面：

```bash
curl -sL -o output/clip1.mp4 '<clip 结果URL>'
ffmpeg -y -i output/clip1.mp4 -vf fps=1 output/qa_clip1_%02d.png -loglevel error
```

要求：服装的轮廓 / 颜色 / 印花 / 设计细节全程一致；微距拍没有手；牛皮纸袋只在板 1 第 1 格；
没有镜子和倒影；每个人最多两只手；发型与脸稳定；唇部干净；没有烧进画面的文字。
有问题只修那一条重跑。

宿主看不了图时，**如实说明没做画面检查**，不要声称质量已通过。

## 阶段 7 — 拼接与导出

N=1 时那条 clip 的 URL 就是成片。N≥2 时在本地按 K 顺序下载、写显式 concat 清单、
硬切拼接、`ffprobe` 校验：

```bash
cd output
for i in $(seq 1 N); do curl -sL -o clip$i.mp4 "<clip i 的URL>"; echo "file 'clip$i.mp4'" >> clips.txt; done
ffmpeg -y -f concat -safe 0 -i clips.txt -c copy final.mp4
ffprobe -v error -show_entries format=duration,size -of default=nw=1 final.mp4
```

`-c copy` 报错（各条编码参数不一致）时才重编码一次：
`ffmpeg -y -f concat -safe 0 -i clips.txt -c:v libx264 -crf 18 -c:a aac final.mp4`。

成片要进媒资库就 `upload_file` + `asset_create`。拼接只走本地 ffmpeg，不要调用 `video_concat`。

## 阶段 8 — 可选文字与交付

用户还没表态时问一次：`字幕` / `钩子标题` / `两个都要` / `不要文字`（默认不要），
顺带问要不要发布文案包。

要文字就读 `references/subtitles.md`。时间轴必须来自**成片音轨**的词级转写。
脚本在本 skill 的 `scripts/` 下，跑在本地：

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
- 依赖：`ffmpeg` 在 PATH 上 + `python3 -m pip install faster-whisper`（首次运行要联网下模型）。
  任一缺失 → **不烧字幕**，交付干净成片并**如实说明**跳过了字幕及原因；绝不手写时间轴、
  绝不平均分配、绝不把没烧字的成片说成已加字幕
- 转写里没有语音时同样什么都不烧，交付 `final.mp4`
- `group_captions.py` 有硬闸门：字幕词不在脚本里时退出码 3。品牌和数字要在
  `output/script.txt` 里按上屏该有的样子写（数字写阿拉伯数字）

交付：给出一条成片 URL 和总时长。发布文案包**只在对话里给**：钩子文案、3–5 个话题标签、
一条置顶评论、一句循环点提示——绝不烧进视频。提示用户「视频由 AI 生成」。

## 人物重摇

同一块板或同一条 clip 连续两次失败、且失败形态像是人物过不了安全审核时：
用新的随机性重跑最初那次达人生成，丢掉依赖它的板，从分镜板阶段重新开始。
重摇最多两次。绝不带着缺失的素材继续。

## 已删掉的分支（WorkRally 没有对应能力）

- 计费 / 额度查询与开跑前报价 → 删掉，不要编造价格
- 服务端 preset / workflow 热更 → 模板全在本地 `references/`
- marketing studio、爆款预测、建站等 Higgsfield 专有工具 → 删掉
- `ask_user_input` / `ask_user_input_v3` 这类宿主专有提问工具 → 正常对话里问一句
- `unlim_choice` 额度选择、`jobs_wait` 批量等待、`show_generation_by_ids` 展示 → 无对应，
  改成 `canvas_get_task` 轮询；生成卡自动渲染
- 声音克隆 / 音色模仿 → 本流程一律禁止，与安全闸门一致

## 参考文件

- `references/product-intake.md`：可穿戴单品归一化
- `references/ugc-character.md`：达人提示词
- `references/ugc-try-board.md`：八格 21:9 试穿分镜板
- `references/ugc-try-clip.md`：八拍的视频提示词
- `references/subtitles.md`：可选的成片后文字

不要去读别的 UGC skill 的 references。
