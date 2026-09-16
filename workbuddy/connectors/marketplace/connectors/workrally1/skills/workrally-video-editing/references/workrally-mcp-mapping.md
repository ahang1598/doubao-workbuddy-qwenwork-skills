# Higgsfield → WorkRally MCP 映射

本插件的 skill 由 Higgsfield 官方 skill（Codex 插件 v1.5.0）移植而来。
**所有 skill 共用这一份工具与参数映射**，各 SKILL.md 不再重复。

移植判据见 `grail-ai/backend/docs/higgsfield-skill-port-triage.md`。

## 1. 工具映射

| Higgsfield | WorkRally MCP | 说明 |
|---|---|---|
| `generate_image` | `canvas_generate_image` | 返回 `task_ids`，异步 |
| `generate_image_batch` | 多次 `canvas_generate_image` | 每个变体一次调用，`count:1` |
| `jobs_wait` / `job_status` | `canvas_get_task` 轮询 | 间隔 3 秒 |
| `show_generation_by_ids` / `job_display` | `canvas_show_image` / `canvas_show_video` | 只读展示已成功的图/视频卡。提交卡已在自轮询时不要再调。见 §5 |
| `models_get` / `models_search` / `models_explore` | `canvas_image_model_list` | 生视频用 `canvas_video_provider_config`；音频用 `canvas_audio_model_list`；提示词优化用 `canvas_gen_content_model_list`（四个都在核心版） |
| `media_upload` + `media_confirm` | `upload_file` → `asset_create` | 见 §4 |
| `media_upload_and_confirm` | 同上 | 无合并工具 |
| `media_import_url` | 直接把 URL 放进 `input_images` | 需在 CDN 白名单内 |
| `sandbox_exec` | **本地 shell** | 见 §6 |
| `generate_video` / `generate_video_batch` | `canvas_generate_video` | 6 种驱动模式 |
| `generate_audio` | `canvas_generate_audio` | `mode: audio` / `music`。无脸频道与旁白 skill 的配音都走这里 |
| `list_voices` / TTS | **禁止调用** `voice_list` / `tts_create` | 音色从 `canvas_audio_model_list` 的 `fields.voice` 取 |
| `reframe` / `upscale_image` / `upscale_video` | **禁止调用** `toolbox_manage` | 核心版无对应；放大/裁切走本地 ffmpeg |
| `virality_predictor`、`marketing_studio_*`、`website_*` | **无对应** | 移植时删除该分支 |

## 2. 模型：一律动态获取，禁止硬编码

Higgsfield 的 `nano_banana_pro` / `gpt_image_2` / `seedream_v5_pro` / `soul_2` / `seedance_2_5`
在 WorkRally **全部不存在**。每次生成前必须先调 `canvas_image_model_list`，从返回的
`models[].model_id` 里选，且不同环境（开发 / 预发 / 正式）可用模型不同。
列表工具返回 JSON 模型配置；选好 model / 分辨率等后再调生成工具。
CLI / Skill 只读 JSON content。

选型口径（按 skill 需要，从模型列表里挑，不要写死 ID）：

| 需求 | 挑选依据 |
|---|---|
| 主渲染、多参考图 | `kontext_config.max_input_images` 足够大，且 `resolution_options` 含 2K/4K |
| 出图快、成本低 | 名称含「极速 / lite」一档 |
| 需要质量档位 | `infer_quality_options` 非空（可传 `quality: high/medium/low`） |

模型的人读名（`models[].name`，如「季宝2.5-极速版」）用于向用户展示；`model_id` 只在调用里用，不要暴露。

## 3. 参数映射

### 分辨率

`resolution` 是 protobuf 枚举，取值必须来自该模型的 `resolution_options[].value`：

| 枚举 | 含义 |
|---|---|
| 4 | 1K / 1080P |
| 5 | 2K |
| 6 | 4K |

Higgsfield 的 `resolution:"2k"` → `resolution: 5`；`"4k"` → `resolution: 6`。
**不要传 0/1/2**，那是旧档位兼容值。

### 宽高比

WorkRally 支持：`21:9` `16:9` `4:3` `2:1` `1:1` `1:2` `3:4` `9:16`（以模型列表返回的 `aspect_ratios` 为准）。

Higgsfield 常用但 WorkRally **没有**的比例，references 里已按下表替换过：

| 原比例 | 替换为 | 场景 |
|---|---|---|
| `4:5` | `3:4` | Instagram 竖版 |
| `2:3` | `3:4` | Pinterest |
| `3:2` | `4:3` | 横版编辑 |
| `3:1` / `4:1` | `21:9` | 超宽 banner |

需要平台原生尺寸时，生成后用本地 ffmpeg 裁切，并告知用户做过裁切。

### 参考图

`input_images` 收的是 **URL 数组**，不是 `asset_id`、也不是本地路径。可接受：

- WorkRally 短链（`/s/xxx`，5 小时有效）
- CDN 白名单内的 HTTPS 图片 URL
- 上一次生成结果的 URL（用于图生图 / 局部修改）

数量上限取该模型的 `kontext_config.max_input_images`，不要写死。

### 多图引用写法（与 Higgsfield 不同，重要）

Higgsfield 用 `IMAGE REFERENCES: image 1 = ...` 清单。
**WorkRally 用位置文本**：提示词里写「第一张图片」「第二张图片」，与 `input_images` 数组下标一一对应。

```
input_images = [人物脸部图URL, 品牌logoURL]
prompt = "第一张图片里的人物站在展台前，展台上放着第二张图片的品牌 logo…"
```

### 提示词语言

WorkRally 主力模型（季宝 / 多宝 / 元宝 / 美宝 等）是中文模型，**中文提示词优先**，不必像
Higgsfield 那样强制翻译成英文。references 里的英文模板按语义组织成中文即可，
结构（分区块、镜头/光线/材质词汇）保持不变。图内文字保留用户原文，不要翻译。

## 4. 上传本地文件

```
upload_file(file_path=<本地绝对路径>)        → CDN url
asset_create(asset_url=<url>, project_id=<短番项目ID>)  → asset_id
```

生成只需要 URL，`asset_create` 是为了入媒资库、让 web 端可见。用户没指定项目时，
用 `project_list` 找「默认项目」。画布场景另需 `canvas_id`（`canvas_manage` 获取），
与短番 `project_id` 是两套 ID，不能互相替代。

## 5. 轮询与结果展示

```
canvas_generate_image(...) → { task_ids: [...] }
canvas_get_task(task_id)   → state: 1排队 2运行 3暂停 4成功 5失败 6取消
```

间隔 3 秒轮询，`state=4` 时读 `output_assets`（含 `asset_id` / `url` / 宽高）。

**提交卡会自动展示**：宿主若支持 MCP Apps，`canvas_generate_image` / `canvas_generate_video` 会挂上对应结果卡，卡片内部自行轮询 `canvas_get_task`。刚提交过的 task **不要再调** `canvas_show_*`。

要对用户亮一张**已经成功**、当前对话没有提交卡的图/视频（下载 / 编辑 / 参考生视频）时：

- 图片 → `canvas_show_image(task_id)`
- 视频 → `canvas_show_video(task_id)`

排队中、失败、音频 / 3D / 提示词文本都不要 show。不支持 MCP Apps 的宿主拿到的是一行文本摘要。

## 6. sandbox_exec → 本地 shell

Higgsfield 的 `sandbox_exec` 是它的云端沙箱（ffmpeg / ImageMagick / python3 / node）。
本插件面向本地 IDE Agent（Cursor / Codex / CodeBuddy），**直接用本地 shell 即可**，
不要去找 `sandbox_exec` 这个工具。

- 脚本随 skill 分发，放在各 skill 的 `scripts/` 下，不再依赖 `$HF_WORKFLOWS`
- 运行前确认本机有 `ffmpeg` / `node` / `python3`；缺失时降级并如实告知用户
- 产物在本地，需要入库时走 §4

## 7. 视频生成（`canvas_generate_video`）

`mode` 六选一，与 Higgsfield 的用法对应：

| 需求 | mode | 必填 |
|---|---|---|
| 纯文生视频 | `Text` | 不传图 |
| 单图驱动 | `Text` | `single_image_url` |
| 首尾帧 | `FirstLastFrame` | `first_frame_url` / `last_frame_url` |
| 参考主体（人物 / 产品保持一致） | `SubjectToVideo` | `reference_assets[]` |
| 编辑已有视频 | `VideoEdit` | `origin_video`（素材ID） |
| 智能编辑（替换物体 / 人物） | `SmartEdit` | `source_video`（含 width/height/duration 毫秒） |
| 延长视频 | `ExtendVideo` | `source_video`，`duration` 为延长秒数 |

分辨率枚举与生图不同：`1`=480P `2`=540P `3`=720P `4`=1080P `5`=1440P `6`=2160P。
以 `canvas_video_provider_config` 返回的该模型 `resolution_options` 为准。

### 原生音画（重要）

`seedance-2.0` / `seedance-2.5` 的 `support_audio: true`，即**视频自带原生音轨**
（seedance-2.0 描述为「多参考融合，原生音画电影级成片」）。UGC 类口播视频靠这个，
**不要**再单独走 TTS 再合轨。`enable_sound` 不传默认 `true`，显式 `false` 才关闭。

模型能力字段全部从 `canvas_video_provider_config` 读，不要写死：
`can_upload_image/video/audio`、`max_image_count`、`max_video_duration`、
`extend_duration_range`、`support_erase_subtitles`。

## 8. 配音与拼接

核心版没有 `voice_list` / `tts_create` / `video_concat` / `toolbox_manage` /
`generate_images_result`。本插件所有 skill **禁止**调用它们，也不要让用户去切全量版。

- 旁白：`workrally-faceless-video`、`workrally-narrator` 走 `canvas_generate_audio` `mode:"audio"`
  （先 `canvas_audio_model_list`，音色写在 `audio_field_values.voice`；轮询 `canvas_get_task`）
- 拼接、混音、放大、裁切：一律本地 ffmpeg
- 不要把全量版接口名写进正路径，也不要当「连了全量版就可以用」的降级方案

字幕：WorkRally 只有字幕**抹除**（`canvas_generate_video` 的 `enable_erase_subtitles`），
**没有烧字幕工具**。要烧字幕走本地 ffmpeg，脚本随 skill 分发。

### 中文字体陷阱（实测，会静默出错）

macOS 上 `PingFang SC` 位于 SIP 保护的 `PrivateFrameworks` 下，**fontconfig 解析不到**：
`fc-match "PingFang SC"` 会返回 Verdana 之类完全无关的字体，libass 于是把中文
**静默烧成方框，ffmpeg 不报错、退出码为 0**。

所以凡是走 ffmpeg / libass 烧中文字幕的脚本：

- 不要把 `PingFang SC` 当默认或兜底
- 每个候选字族都要过 `fc-match` 回读校验：回来的族名对得上、文件可读，才算可用
- 一个都过不了就**报错退出**，不要烧出方框还说成功
- 实测可用的回落顺序：`Noto Sans CJK SC` → `Noto Sans SC` → `Source Han Sans SC` →
  `Hiragino Sans GB` → `STHeiti`

浏览器 canvas 路线（Chromium + `document.fonts`）不受此限，`PingFang SC` 在那边正常。

## 9. 已知缺口

| 缺口 | 影响 | 处置 |
|---|---|---|
| 无计费 / 额度查询工具 | 无法在开跑前报价 | 删掉「预估消耗」步骤，不要编造价格 |
| 无服务端 preset / workflow 分发 | 模板不能热更 | 全部落在本地 `references/` |
| 无烧字幕工具 | 只有字幕**抹除** | 本地 ffmpeg 烧 |
| 无 `voice_change`（音色替换） | 已有视频改不了音色 | 口播音色由视频模型原生音轨决定，或重新生成 |
| 无矢量出图 | logo 只能出位图，不能出 SVG | 如实降级并披露，不要承诺印刷母版 |
| 原生音轨**能力已确认、质量未标定** | 口播口型准确度、中文咬字未实测 | 可以移植，但每块产出必须验证；不达标就如实降级，不许假装配好了 |
