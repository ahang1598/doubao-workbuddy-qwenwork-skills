---
name: workrally-video-editing
version: 0.1.0
description: |
  对已有视频做编辑与成片装配：按提示词改画面（VideoEdit）、替换视频里的物体或人物（SmartEdit）、
  延长视频（ExtendVideo），以及本地 ffmpeg 的裁剪、拼接、调速、变比例、混音、烧字幕。
  当用户说「改一下这个视频」「把视频里的 X 换成 Y」「视频接长一点」「剪掉前三秒」
  「把这几段拼起来」「换个比例」「配个 BGM」「加个片头标题卡」时命中。
  不处理：从零生成视频（用文生视频/图生视频流程）、视频封面（用 workrally-thumbnail）、
  语音字幕烧制（用 workrally-subtitles）、旁白配音（用 workrally-narrator）、
  只是让你看视频做总结/点评/转写、字幕翻译校对。
---

# WorkRally 视频编辑

编辑已有素材，不是从零生成。两条腿走路，先判断走哪条：

- **生成式编辑** —— 画面内容要变（换物体、换人、改画面、接长）。走 `canvas_generate_video`，异步、按次计费、结果不完全可控。
- **确定性剪辑** —— 时间、几何、音轨、字幕要变（裁剪、拼接、调速、变比例、混音、烧字）。走**本地 ffmpeg**，同步、免费、逐帧可控。

**能用 ffmpeg 解决的，绝不要走生成式编辑。**裁掉三秒不需要模型重画一遍。

## 运行约定

先读 `references/workrally-mcp-mapping.md`，本文不重复工具与参数细节。要点：

- 生成前必须调 `canvas_video_provider_config` 取模型，**禁止硬编码 model_id**；
  不同环境可用模型完全不同
- 提交后按 `task_ids` 逐个 `canvas_get_task` 轮询，间隔 3 秒；`state=4` 时读 `output_assets`
- 本地视频先 `upload_file` 拿 URL，再 `asset_create` 拿 **asset_id**——
  三种编辑模式吃的都是 **asset_id**，不是 URL、不是本地路径
- `project_id` 是**画布ID**（`canvas_manage` 获取），不是短番项目ID，两者不能互换
- 提示词用中文；画面里要保留的文字用用户原文
- 本地脚本走**本地 shell**，不要找 `sandbox_exec`
- 不需要调展示工具，生成卡会自动渲染

追问最多一次，一到三个问题，每题两三个互斥选项，推荐项放第一个。

## 选路

| 用户想要 | 走哪条 | 看哪份参考 |
|---|---|---|
| 把画面里的某个物体/人物换掉 | `SmartEdit` | `references/generative-edit.md` |
| 整体改画面（风格、天气、服装、场景元素） | `VideoEdit` | `references/generative-edit.md` |
| 视频不够长，往后接 | `ExtendVideo` | `references/generative-edit.md` |
| 裁剪、掐头去尾、抽段 | ffmpeg | `references/ffmpeg-recipes.md` |
| 多段拼成一条 | ffmpeg | `references/assembly.md` |
| 变速、倒放、抽帧、改帧率 | ffmpeg | `references/ffmpeg-recipes.md` |
| 换比例 / 裁成竖版 / 加黑边 | ffmpeg | `references/clip-geometry.md` |
| 配 BGM、换音轨、压低原声、静音 | ffmpeg | `references/assembly.md` |
| 加片头标题卡、下三分之一条、屏幕标注 | ffmpeg + ASS | `references/title-animation.md` |
| 烧**语音字幕**（跟着人说话走） | 交给 `workrally-subtitles` | —— |
| 已有时间码的文字要压进画面 | ffmpeg + ASS | `references/caption-systems.md` |
| 抹掉视频里已有的硬字幕 | `enable_erase_subtitles` | `references/generative-edit.md` |
| 定镜头怎么描述、要什么运动 | —— | `references/motion-language.md`、`references/shot-blueprints.md` |
| 出问题了 | —— | `references/failure-modes.md` |

不要吞掉相邻场景：从零造视频不归本 skill；封面归 `workrally-thumbnail`；
跟着人说话走的语音字幕归 `workrally-subtitles`（它自带 Whisper 取词级时间轴）；
旁白配音归 `workrally-narrator`；只让你看视频做总结/点评的请求**不要**激活本 skill。

## 第 0 步：源视频必须先探测

三种生成式模式都要 asset_id，`SmartEdit` 还硬性要求 `width` / `height` / `duration`（**毫秒**），
少一个或为 0 后端直接拒。ffmpeg 那条腿也要靠这些数才能算裁剪和比例。

```bash
bash <skill 目录>/scripts/probe_video.sh <本地文件或URL>
```

输出一行 JSON：`{"width":1920,"height":1080,"duration_ms":12480,"fps":30,"has_audio":true,...}`，
`duration_ms` 可直接填进 `source_video.duration`。

本地文件还要入库：

```
upload_file(file_path=<绝对路径>)  → CDN url
asset_create(asset_url=<url>, project_id=<短番项目ID>)  → asset_id
```

用户没指定项目时用 `project_list` 找「默认项目」。**不要**把探测出来的秒数当毫秒填，
这是本 skill 最高频的报错来源。

## 生成式编辑

三种模式的必填项、模型来源与提示词写法全在 `references/generative-edit.md`，这里只放骨架。

| mode | 必填 | 模型取自 | prompt |
|---|---|---|---|
| `VideoEdit` | `origin_video`（asset_id） | `video_edit_providers` | 必填 |
| `SmartEdit` | `source_video{asset_id,width,height,duration}` | `smart_edit_providers` | 可为空 |
| `ExtendVideo` | `source_video{asset_id}` + `duration`（延长秒数） | `subject_to_video_providers` | 可为空 |

```jsonc
canvas_generate_video({
  mode: "SmartEdit",
  prompt: "<中文编辑指令；SmartEdit / ExtendVideo 可留空>",
  model: "<canvas_video_provider_config 返回的 provider>",
  source_video: { asset_id: "<源视频素材ID>", width: 1920, height: 1080, duration: 12480 },
  reference_assets: [{ type: "image", url: "<替换目标的参考图URL>" }],
  count: 1,
  project_id: "<画布ID，可选；传了会自动在画布上建占位节点>",
  task_name: "<素材名_编辑意图>"
})
```

- **分辨率枚举与生图不同**：`1`=480P `2`=540P `3`=720P `4`=1080P `5`=1440P `6`=2160P。
  取值必须来自该模型的 `resolution_options`；不传则自动取首个可用档。
  `VideoEdit` 不吃 `resolution`，不要传。
- `enable_sound` 不传默认 `true`。源视频原声不需要模型再配音时显式传 `false`。
- `count` 1–4，后端一个任务只出一个视频，MCP 会并发发 N 个独立任务，返回 N 个 task_id，**逐个轮询**。
- 模型 `support_erase_subtitles` 为真时才可以传 `enable_erase_subtitles`，用来抹掉画面里已有的硬字幕。
  WorkRally **只有抹字幕，没有烧字幕**——烧字走 ffmpeg。

已完成的任务**冻结**，不要重复提交；轮询超时不等于生成失败。同一个诉求轮询满 12 轮仍无结果就停下，
保留 task_id 告诉用户还在生成中，下一轮对话再查。技术性失败每个任务最多重试一次；
遇到安全、权限、配额类错误直接停下说明，不要重试。

## 确定性剪辑

本地 ffmpeg。开工前确认本机有 `ffmpeg` / `ffprobe`：

```bash
command -v ffmpeg ffprobe
```

缺失时**降级并如实告知用户**（macOS `brew install ffmpeg`），不要假装剪过了。

随 skill 分发的脚本（路径相对本 skill 目录，按实际安装位置补全）：

| 脚本 | 用途 |
|---|---|
| `scripts/probe_video.sh` | 探测宽高、时长（毫秒）、帧率、有无音轨 |
| `scripts/burn_captions.sh` | 把 SRT/ASS 烧进画面，带中文字体栈 |
| `scripts/concat_clips.sh` | 多段拼接，自动统一分辨率与帧率 |

手写命令的配方在 `references/ffmpeg-recipes.md`（裁剪/调速/变比例/混音）。
**默认优先无损流拷贝**（`-c copy`），只有必须重编码时才重编码，并告知用户重编码过。

产物在本地。需要入媒资库或喂回生成式编辑时，走 `upload_file` + `asset_create`。

## 混合流程（最常见）

真实需求通常两条腿都要走，顺序很关键：

1. **先剪后生成** —— 只需要改其中一段时，先 ffmpeg 切出那一段，只对它做生成式编辑，
   再拼回去。别把整条 10 分钟视频丢进模型。
2. **先生成后烧字** —— 字幕永远最后烧。生成式编辑会重画画面，先烧的字会被抹掉或糊掉。
3. **比例最后调** —— 生成模型按自己的尺寸出片，最终交付比例用 ffmpeg 定。

每次跨腿传递都要重新 `probe_video.sh`：生成式编辑的产物尺寸/时长**未必**等于源视频。

## 交付

给出最终视频，用一句话说明走了哪条路、改了什么、有没有重编码。
生成式编辑的产物要提示用户「视频由 AI 生成/编辑」。

宿主看不到画面时，**如实说明未做视觉检查**，不要声称效果已确认。
某一段没成功时如实报告，不要声称整条已完成。
不要暴露模型名、task_id、graph_template 这类内部机制。

## 不做的事

以下能力 WorkRally 没有，遇到直接说明，**不要编造替代品**：

- **没有时间线工程 / 关键帧动画引擎。**没有可编程的 NLE：没有图层树、没有帧编排、
  没有 GLSL 着色器节点、没有 2.5D 摄像机、没有共享计数器。复杂动态图形请如实告知做不了，
  或退化成 ffmpeg 能表达的静态叠加 + 简单淡入淡出。
- **没有可托管的工程文件 / 在线编辑器链接。**交付的是成片文件，不是可继续编辑的工程。
- **本 skill 不做语音转写。**压文字进画面需要用户提供 SRT/ASS 或逐句文本加时间码；
  要从音轨自动取时间轴请转 `workrally-subtitles`。
- **没有计费查询。**开跑前无法报价，不要臆造价格或额度。
- **没有服务端风格预设分发。**所有模板都在本地 `references/`。

## 参考索引

- 生成式编辑：[三种模式与提示词](references/generative-edit.md)
- 确定性剪辑：[ffmpeg 配方](references/ffmpeg-recipes.md)、[几何与比例](references/clip-geometry.md)、[装配与音轨](references/assembly.md)
- 文字：[字幕系统](references/caption-systems.md)、[标题与下三分之一条](references/title-animation.md)
- 手艺：[运动语汇](references/motion-language.md)、[镜头蓝图](references/shot-blueprints.md)
- 排障：[失效模式与诊断](references/failure-modes.md)
- 来源：[移植出处](references/provenance.md)
