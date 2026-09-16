---
name: workrally-ugc-review-video
version: 0.1.0
description: |
  用 WorkRally 画布产出成片的「达人出镜口播」UGC 竖版短视频（9:16）：一位成年达人
  **对着镜头讲解 / 演示 / 念用户给定的文案**，全程锁同一个人物身份，口型与人声来自
  支持原生音频的视频模型。产品可有可无（也支持纯场景 / 生活方式口播）。
  当用户说「达人测评视频」「真人出镜口播」「口播带货」「TikTok / 抖音风格产品展示」
  「种草视频」「找个达人讲一下这个产品」时命中。
  不处理：无人出镜的产品独角戏（用 workrally-ugc-product-video）、服装试穿上身（用
  workrally-ugc-try-on-video）、开箱为主线、分步教程、SaaS / 网站录屏、纯画外音无人出镜、
  伪造真实用户证言或冒充特定真人、只要脚本不要成片、剪辑已有素材。
---

# WorkRally UGC 达人口播视频

产出**一条** 9:16 成片。全程只有一个达人身份，贯穿每一块板、每一条 clip。
每块分镜板是一张 21:9 大图，里面横排八个 9:16 竖格；一条视频把这八格变成八个内部硬切。

## 运行约定

先读 `references/workrally-mcp-mapping.md`（工具与参数映射，本文不重复）。要点：

- 生图前调 `canvas_image_model_list`，生视频前调 `canvas_video_provider_config`，
  **禁止硬编码任何 model_id / provider**
- 每次生成一条独立提示词、一次独立调用，`count: 1`
- 提交后按 `task_ids` 逐个 `canvas_get_task` 轮询：生图间隔 3 秒，生视频间隔 3–5 秒
- 参考图放 `input_images`（生图）/ `reference_assets`（生视频），都收 **URL**；
  提示词里用「第一张图片 / 第二张图片 / 第三张图片」按下标引用
- 本地文件先 `upload_file(file_path=…)` 拿 URL；要进媒资库再 `asset_create`
- 提示词与口播用中文；产品包装上的文字保留原文，逐字不改
- 下载 / ffmpeg / python / 抽帧 / 转写 / 拼接全走**本地 shell**，不要找 `sandbox_exec`；
  脚本随本 skill 分发在 `scripts/`
- 不需要调展示类工具，生成卡会自动渲染
- 没有计费 / 额度查询工具：不报价、不预估消耗、不编造价格
- 宿主没有专用提问工具（`ask_user_input_v3` 是 ChatGPT 宿主专有的）——正常对话里问一句就行

### 原生音画（本 skill 的核心）

达人的说话声和口型**就是视频模型自带的原生音轨**，不是后期配上去的。从
`canvas_video_provider_config` 的 `subject_to_video_providers` 里按能力挑模型：
**`support_audio: true`**，且 `max_video_duration` / `duration_options` 覆盖本条 clip 的秒数。

- `enable_sound` 不传即为 `true`，**不要显式传 false**
- **不要**拆成「静音视频 + 单独 TTS + 合轨」：那样口型必然对不上。
  不要调 `canvas_generate_audio` 再去合轨
- 没有任何 `support_audio: true` 的模型时：停下来如实告知用户「当前环境没有支持原生音频的
  视频模型，做不出口型对得上的口播」，让用户决定是否继续，**不要**偷偷交付静音画面再说已完成

## 硬规则

- 全程复用同一个 `character_url`。绝不中途重新生成，也绝不用一段文字描述顶替它
- 分镜板**逐块顺序生成**；所有 clip 提示词写完之后才开始提交视频
- **绝不**把文字烧进生成。只在成片出来后、且用户明确要了才烧
- 每块板都要跑一遍去 AI 感（de-slop）图生图；只有该步两次都失败才允许用原始板
- 有产品时，板 1 之后不要再打招呼或重新介绍产品；后面每段都从半句话接上
- 中文口播优先（跟随用户语言）；用户明确指定语言 / 口音时按用户说的
- 不向用户暴露模型名、task_id、内部阶段和中间机制

## 安全与真实性闸门 —— 在收集输入或生成之前先跑

下面任何一条不过，就不生成，也不绕过闸门：

- **达人授权**：只用生成的成年人（21 岁以上），或用户有权使用其形象、且已同意的
  非公众人物成年人。用户给了一张照片**不等于**授权模仿照片里的人。第三方同意不明确时
  问一次；公众人物、名人、未成年人、欺骗性身份使用一律拒绝。绝不克隆或模仿用户提供的人的声音
- **可推广范围**：拒绝政治说服，拒绝推广受限或年龄限制的商品与服务，包括成人性内容 /
  用品 / 服务、赌博、违法或管制药品与器具、处方药、烟草或尼古丁、武器爆炸物或有害物品、
  假冒或非法商品、极端主义商品、欺骗性或高风险金融服务、恶意软件或间谍软件、诈骗、
  隐蔽监控。中立的科普提及不算产品推广，也不属于本流程
- **真实宣称**：`approved_claims` 是用户给的产品宣称**完整白名单**。逐字保留每条，
  绝不加强、合并、推断或派生新的宣称。没有白名单时，只写关于可见材质、控件、使用方式、
  包装等**直接可观察机构**的无宣称文案
- **不做合成证言**：生成的达人是主持人 / 演示者，**不是真实顾客**。绝不编造购买、
  拥有、使用、效果、前后对比结果、评分、评价、社交证明、关系或亲身经历。
  第一人称经历只有在用户提供逐字脚本并确认那是他自己的经历时才允许
- **透明表述**：有产品的成片对外说明为品牌演示 / 达人概念片 / 商业创意，
  **不是**自然发生的顾客测评。用户要发布文案包时，带上合适的广告 / 合作声明

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

板的角色分配：

- N=1：`FULL_ARC`（钩子 → 主体 → 收尾）
- N=2：`HOOK+SETUP`，然后 `APPLY+CLOSER`
- N=3：`HOOK`、`MAIN`、`CLOSER`
- N=4：`HOOK`、`REVEAL`、`APPLY`、`CLOSER`
- N>4：首块 `HOOK`，末块 `CLOSER`，中间是 `REVEAL` / `APPLY`

## 阶段 0 — 收集输入

安全与真实性闸门通过之后，解析：可选的产品照片或 URL、总时长、达人照片或指定性别，
以及明确给出的场地、发型、族裔、着装档位、情绪、道具、语言、口音、音乐、
`approved_claims`、片上文字。

把 brief 的具体程度分档：

- `auto`：1–5 个词、没有场景 → 整套处理方式由你来定
- `guided`：1–3 句语气或大致流程 → 保留这个方向
- `director`：4 句以上、有场景 / 分镜表 / 场地序列 → 把用户给的节拍一对一映射到各格

**只问真正的缺口**，一次问完：时长（给 10s / 15s / 30s / 45s）和缺失的达人照片 / 性别。
用户没给产品时**绝不**因此追问产品——把 `product_url` 和 `product_description` 都锁成 null，
按达人主导、场景驱动的 UGC 继续。只有 brief 本身透出地域来源或刻意特殊的人物气质时，
才顺带给一个口音 / 小怪癖选项。绝不追问模型、宽高比、板数、分辨率、音频、批量、身份训练。

达人输入和时长没定之前不要开始付费生成。后面那次「要不要文字 / 要不要发布文案」是唯一被允许的第二次追问。

## 阶段 1 — 归一化可选的产品

用户给了产品照片或 URL 时，读 `references/product-intake.md` 并严格照做。一次性定下：

- `product_url`：可用的 HTTPS 图片 URL（本地文件先 `upload_file`）。生图的 `input_images`
  和生视频的 `reference_assets` **用同一个 URL**
- 规范的 `product_description`
- `tier`：`luxury` / `premium` / `drugstore`，只从包装的视觉线索读，绝不查价格
- `category` 以及确切的使用 / 开启机构
- `approved_claims`：用户给的原句，或空列表

这些值后面逐字复用。绝不推断价格、绝不编造宣称或达人经历、绝不用图库图或生成图顶替
打不开或内容单薄的产品页。没有产品时跳过本阶段，两个产品字段都留 null，
并走 `ugc-board.md`、`ugc-clip.md`、`monologue-craft.md` 里的无产品分支。

## 阶段 2 — 锁定达人

安全闸门确认用户有权使用附件里的达人照片时：`upload_file` 拿 URL，存为 `character_url`，
不要再重复确认。

否则读 `references/ugc-character.md`，摇完必要的多样性骰子、写好达人提示词，提交一次：

```jsonc
canvas_generate_image({
  model: "<canvas_image_model_list 返回的 model_id>",
  prompt: "<达人提示词>",
  count: 1,
  aspect_ratio: "3:4",
  resolution: 5,            // 2K
  task_name: "<选题>_creator"
})
```

轮询到 `state=4`，把 `output_assets[0].url` 存为 `character_url`。这个 URL 是**每块板的必需输入**，
也是每条 clip 的人物参考。除非故事明确换了场景，服装保持不变。

把你写下的特征（年龄段、发型、体型、服装锚点）记在自己的笔记里——后面无法再回看这张图，
**写下来的描述就是连续性契约**。

## 阶段 3 — 逐块生成分镜板

读 `references/ugc-board.md`。K=1..N，每块写完整提示词后提交一次：

```jsonc
canvas_generate_image({
  model: "<canvas_image_model_list 返回的 model_id>",
  prompt: "<板 K 的提示词>",
  count: 1,
  aspect_ratio: "21:9",
  resolution: 5,            // 2K；模型不支持时退到它 resolution_options 的最高档
  input_images: ["<产品图URL>", "<character_url>"],   // K>1 时追加上一块清洗后的板 URL
  task_name: "<选题>_board<K>"
})
```

`input_images` 顺序：产品 → 达人 → 上一块清洗后的板。没有产品时去掉那一项，
并把提示词里的「第一张图片 / 第二张图片」整体前移，与数组顺序严格对应。
数组长度不超过该模型的 `kontext_config.max_input_images`。轮询到 `state=4` 再做下一块。

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

无产品的场次，把提示词里所有「保留产品」的从句换成
`不要引入任何产品、包装、品牌或销售道具`。

清洗结果替换原始板，后面一律用清洗后的 URL。被安全审核拦下时换同一批里另一个模型再试一次；
两次都失败就保留原始板继续，并在内部记下这是降级路径。

## 阶段 4 — 写口播

读 `references/monologue-craft.md`。只保留白名单里的用户宣称和用户要的语气，
绝不编造达人的经历或使用史。按它的信息密度、钩子、人物设定、故事形状、口音、反 AI 味规则来写。

最终口播切成 N 段，每块板一段。定稿逐字写到 `output/script.txt`；
如果可能要烧钩子标题，把那句标题也写到 `output/hook.txt`。

## 阶段 5 — 写并提交 clip

读 `references/ugc-clip.md`。**所有** clip 提示词写完之后才开始提交视频。每条带上
K、N、时长、板角色、**逐字**的口播段、具体程度档位、人物设定，以及板 / 达人 / 产品参考。

```jsonc
canvas_generate_video({
  mode: "SubjectToVideo",                 // 参考主体：锁达人身份 + 锁产品
  model: "<canvas_video_provider_config 里 support_audio:true 且时长够的 provider>",
  prompt: "<clip K 的提示词>",
  count: 1,
  duration: <本条秒数>,                    // 必须在该模型 duration_options 里
  aspect_ratio: "9:16",
  resolution: 4,                           // 1080P；以该模型 resolution_options 为准
  reference_assets: [
    { url: "<清洗后板 K 的 URL>", type: "image" },
    { url: "<character_url>",      type: "image" },
    { url: "<产品图URL>",          type: "image" }   // 没有产品就去掉这一项
  ],
  task_name: "<选题>_clip<K>"
})
```

提交第一条之前自查两件事：`mode` 是 `SubjectToVideo`，模型的 `support_audio` 是 `true`。
`enable_sound` 不传（默认开）。`reference_assets` 的条数不超过该模型的 `max_image_count`；
去掉某一项时提示词里的位置引用要同步前移。

等所有 clip 都出结果；只重跑失败的那条，成功的重跑替换掉该位置的旧 URL。

## 阶段 6 — 抽帧质检

拼接或展示之前把每条 clip 拉到本地抽帧看，尤其是产品特写和 2–3 帧说话中的画面：

```bash
curl -sL -o output/clip1.mp4 '<clip 结果URL>'
ffmpeg -y -i output/clip1.mp4 -vf fps=1 output/qa_clip1_%02d.png -loglevel error
```

要求：有产品时全程只有一个主产品、没有克隆；每个人最多两只手（含镜面与画面边缘）；
声明缺失的特征确实缺失；盖子 / 按钮 / 道具状态一致；标签不是乱码、不镜像、不是别的真实品牌；
有产品时产品尺寸与握持的手匹配；没有双重唇边、脸部漂移、烧进画面的文字或字幕。

摆位问题就只修那一条重跑。口型有伪影时优先删减该处台词。烧进了文字先重跑一次，
再不行就后期去掉。通过的每一条**冻结**，不要重复提交。

宿主看不了图时，**如实说明没做画面检查**，不要声称质量已通过。

## 阶段 7 — 拼接与导出

N=1 时那条 clip 的 URL 就是成片，不需要拼接。

N≥2 时在本地按板序下载、写显式 concat 清单、硬切拼接、`ffprobe` 校验：

```bash
cd output
for i in $(seq 1 N); do curl -sL -o clip$i.mp4 "<clip i 的URL>"; echo "file 'clip$i.mp4'" >> clips.txt; done
ffmpeg -y -f concat -safe 0 -i clips.txt -c copy final.mp4
ffprobe -v error -show_entries format=duration,size -of default=nw=1 final.mp4
```

`-c copy` 报错（各条编码参数不一致）时才重编码一次：
`ffmpeg -y -f concat -safe 0 -i clips.txt -c:v libx264 -crf 18 -c:a aac final.mp4`。

成片要进媒资库就 `upload_file` + `asset_create`。拼接只走本地 ffmpeg，不要调用 `video_concat`。

## 阶段 8 — 可选文字与发布文案

brief 里没答过就问一次：`字幕` / `钩子标题` / `两个都要` / `不要文字`（默认不要），
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
- 依赖：`ffmpeg` 在 PATH 上 + `python3 -m pip install faster-whisper`（首次运行要联网下模型）。
  任一缺失 → **不烧字幕**，交付干净成片并**如实说明**跳过了字幕及原因；绝不手写时间轴、
  绝不平均分配、绝不把没烧字的成片说成已加字幕
- 转写里没有语音时同样什么都不烧，交付 `final.mp4`
- `group_captions.py` 有硬闸门：字幕词不在脚本里时退出码 3。品牌和数字要在
  `output/script.txt` 里按上屏该有的样子写（数字写阿拉伯数字）

发布文案包**只在对话里给**：一句留了未解开悬念的评论钩子文案、3–5 个话题标签、
一条能解答或补充可观察细节的置顶评论、有产品的商业内容要带广告 / 合作声明、
一句循环点提示。绝不烧进视频。

## 交付

给出一条成片 URL 和总时长。要了字幕就交 `final_captioned.mp4`，同时留着 `final.mp4`
作干净母版。不要暴露 task_id 和中间产物。提示用户「视频由 AI 生成」，
有产品时按「透明表述」那条说清这是品牌演示 / 达人概念片。

## 已删掉的分支（WorkRally 没有对应能力）

- 计费 / 额度查询与开跑前报价 → 删掉，不要编造价格
- 服务端 preset / workflow 热更 → 模板全在本地 `references/`
- marketing studio、爆款预测、建站等 Higgsfield 专有工具 → 删掉
- `ask_user_input` / `ask_user_input_v3` 这类宿主专有提问工具 → 正常对话里问一句
- `unlim_choice` 额度选择、`jobs_wait` 批量等待、`show_generation_by_ids` 展示 → 无对应，
  改成 `canvas_get_task` 轮询；生成卡自动渲染
- 声音克隆 / 音色模仿 → 本流程一律禁止，与安全闸门一致

## 参考文件

- `references/product-intake.md`：产品归一化与摆位契约
- `references/ugc-character.md`：达人提示词与连续性规则
- `references/monologue-craft.md`：口播密度、口吻、钩子与故事形状
- `references/ugc-board.md`：八格 21:9 分镜板提示词
- `references/ugc-clip.md`：八段硬切的视频提示词
- `references/subtitles.md`：可选的按转写时间烧字

不要去读别的 UGC skill 的 references——它们的只有产品、开箱、教程、试穿、SaaS 契约
与本 skill 的达人出镜口播定位冲突。
