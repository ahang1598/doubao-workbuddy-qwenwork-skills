---
name: video-redaction
description: 识别视频中的敏感对话（涉黄/涉毒/暴力/色情/脏话/骂人/合规违禁词）并打哔消音；如画面有硬字幕且含敏感词，则擦除后重压干净字幕，输出可过审发布的成片。仅处理"音频敏感词打哔 + 硬字幕敏感词擦除并重压"两条主线。不处理画面人脸/车牌/logo 打码、纯粹的字幕翻译或添加、视频剪辑、画幅转换。无音轨视频直接跳过并告知用户。
metadata:
  requires:
    bins:
      - mediakit-cli
---

# mediakit-cli 子命令归属速查(避免瞎试)

```shell
mediakit-cli --version
```

## 【强制前置】开工前必须先加载 byted-mediakit-shared 技能

**在本 skill 执行任何操作（含 setup、probe、抽帧、任意 mediakit-cli 命令）之前，必须先通过 Skill 工具加载 `byted-mediakit-shared` 技能，读完其中的 mediakit-cli 使用指南再继续。这是硬性前置、不是可选项——未加载该技能不得下任何 mediakit-cli 命令。**

**本 skill 额外固定要求：所有真实的 `mediakit-cli` 业务调用（含 `shared query-task`）都必须注入 `DOUBAO_MEDIAKIT_RUNTIME=scene-video-redaction`。这是本 skill 的固定值，不允许省略、改名、改值，也不要把它写成 CLI flag。** `--help` / `--schema` / `--domains` / `--version` 这类只读发现命令可不带。POSIX shell 直接写成 `DOUBAO_MEDIAKIT_RUNTIME=scene-video-redaction mediakit-cli ...`；PowerShell 先设 `$env:DOUBAO_MEDIAKIT_RUNTIME="scene-video-redaction"`，再执行 `mediakit-cli ...`。

**每个工具的子命令归属固定,不要凭直觉试**。以下是本 skill 用到的所有 mediakit-cli 工具的正确路径,不确定就先查这张表,不要盲跑 `--help`:

| 工具                         | 正确调用                                         | 常见错用                          |
| ---------------------------- | ------------------------------------------------ | --------------------------------- |
| 人声/背景音分离              | `mediakit-cli audio separate-voice`              | ❌ `video separate-voice`         |
| 探测视频元数据               | `mediakit-cli video probe-video-metadata`        | —                                 |
| 抽帧(含雪碧图)               | `mediakit-cli video extract-frames`              | —                                 |
| OCR(带 Subtitle/Others 分类) | `mediakit-cli video video-ocr --mode Detailed`   | —                                 |
| 字幕擦除                     | `mediakit-cli video erase-video-subtitle-pro`    | ❌ `erase-video-subtitle`(非 pro) |
| 句级 ASR                     | `mediakit-cli video asr-subtitles`               | ❌ `audio asr-subtitles`          |
| 视频理解                     | `mediakit-cli video video-understand-router`     | —                                 |
| 音视频合流                   | `mediakit-cli editing mux-audio-video`           | ❌ `video mux-audio-video`        |
| 压字幕                       | `mediakit-cli editing add-subtitle-to-video`     | ❌ `video add-subtitle-to-video`  |
| 任务轮询                     | `mediakit-cli shared query-task --poll-complete` | ❌ 各子命令下都没有 query-task    |

**归属逻辑**:`audio` = 只处理音轨(separate-voice);`video` = 输入是视频且输出仍是视频/元数据(probe/extract/ocr/erase/asr/understand);`editing` = 组合式后期(mux/字幕压制);`shared` = 通用任务轮询。

不确定时**先查此表**,再决定要不要跑 `--help`;不要一上来就 `mediakit-cli video XXX --help` 硬试。

# 使用前请阅读

**执行前必须先读 `reference/` 里对应阶段的文档,再下命令。** 不允许把报错当成探路手段:不要先随手跑一个命令、看到报错后再回来看文档;要先按文档确认子命令归属、输入输出、是否需要轮询、是否要下载中间产物,然后再直接执行。

**不做前置环境探测 ≠ 允许盲跑试错。** 本 skill 的含义是:不额外插一层独立的环境检查流程;但真正执行某一步前,仍然要先读该步对应文档,按文档给出的命令和参数一次性执行。环境若确实缺失,可以自然暴露缺什么;**但不能靠先跑错一次来确认该怎么做**。

**不要试图在一个进程里把全流程一次执行完。** 允许也鼓励按步骤拆开执行:某一步提交云任务后,记录 `task_id`,后续在**新的命令/新的轮询调用**里继续查结果;音频线、视觉线、合流、压字幕都可以分段衔接。**不要**把 probe / OCR / separate-voice / query-task / ffmpeg / mux 全塞进一个长 shell 或 Python 进程里硬跑到底。

**最小阅读顺序固定如下**:

0. **（硬性前置）任何步骤之前，先通过 Skill 工具加载 `byted-mediakit-shared` 技能并读完其 mediakit-cli 使用指南**——未完成此步不得执行下面任何一步
1. 开始任务先读 [安装.md](reference/安装.md) 和 [前置探测.md](reference/前置探测.md)
2. Gate 0 确认有音轨后、提交视频理解任务前读 [视频理解佐证.md](reference/视频理解佐证.md)；进入音频线前读 [音频处理.md](reference/音频处理.md) 和 [敏感词音频处理.md](reference/敏感词音频处理.md)
3. 进入视觉线前读 [字幕处理.md](reference/字幕处理.md)
4. 做敏感词裁定前读 [敏感词检测.md](reference/敏感词检测.md)
5. 有硬字幕时必须读 [文案校准.md](reference/文案校准.md) 和 [合并.md](reference/合并.md) 并完成重压；无硬字幕且用户明确需要新字幕时同样执行
6. **只要要调用 `mediakit-cli editing add-subtitle-to-video`，执行前必须再读 `byted-mediakit-editing/reference/add-subtitle-to-video.md`，尤其核对 `subtitle_pos_preset` / `subtitle_font_size` 的约束后再下命令；禁止沿用旧的固定 `45` 经验值**

# 注意事项

**开工前必须先锁定用户提供的输入路径 / URL，并全程原样使用。** 任何步骤发起前，先从用户消息里取出真实的输入视频/音频路径或 URL 存为唯一变量（如 `INPUT`），后续 probe、抽帧、`separate-voice`、`video-understand-router`、ffmpeg、下载、交付都直接引用它。**禁止**：凭空猜测或补写文件名/目录、把相对路径当绝对路径、擅自改写扩展名或规范化路径、用示例里的 `C:\path\video.mp4` / `<url>` 等占位符当真实输入、或在没有输入时先假设一个再跑。**含空格或中文的路径必须整体加引号**（bash/zsh 用双引号，PowerShell 用双引号）。用户只给了本地路径时按本地文件走、只给了 URL 时按 URL 走，不要互相臆造。**输入缺失、为空或明显不是可访问的路径/URL 时，先停下来向用户要准确输入，不要用假设值继续**——路径错配是最常见的异常来源。

**输入是 HTTP/HTTPS URL 时，必须先确认地址有效再 fan-out。** 锁定 `INPUT` 后、发起 Step 1/2 的并行云任务（probe / 抽帧 / `separate-voice` / `video-understand-router`）**之前**，先跑一条轻量探活确认该 URL 可达、未过期、返回的是视频而非报错页：优先用 1 字节 ranged GET 读 HTTP 状态码与 `content-type`（`curl -sS -L -r 0-0 --max-time 15 -o /dev/null -w '%{http_code} %{content_type}\n' "$INPUT"`，Windows 用自带 `curl.exe` 同参数）。**这是一条文档定义的预检，不是「先盲跑业务命令看报错」**——目的正是避免把一批付费云任务一次性打到失效链接上。状态码非 2xx、`content-type` 明显是 `text/html` / `application/json` 报错页、或超时/连接失败，都判定为无效：**停下来把结果告诉用户并索要有效地址，不要继续 probe 或任何云任务**。输入是本地路径时对应改为确认文件存在且可读（无需 curl）。

**不做独立前置环境探测**:环境检查全部内聚在 setup。mac/Linux 的 `scripts/setup.sh`、Windows 的 `scripts/setup.ps1` 会检查并安装 ffmpeg/ffprobe，再准备 FunASR；macOS 缺 ffmpeg 时用 Homebrew，Windows 缺 ffmpeg 时用 winget。FunASR 安装在会话一启动就作为独立命令进程发起,与 `probe-video-metadata`/抽帧的工具调用**并行**。**全程只启动这一次**——用 guard 文件(`.ready`/`.installing`)幂等,后续每步只读状态文件，禁止重复启动。Windows 安装器固定选择 Python 3.10-3.13，先安装 CMake/Ninja，并强制 `kaldi-native-fbank` 使用二进制 wheel，禁止缺 wheel 时回退源码编译。FunASR 依赖必装 `torch(CPU)` + `funasr` + `modelscope` + `kaldi-native-fbank`，**不装 torchaudio**。
**`scripts/setup.sh`（mac/Linux）与 `scripts/setup.ps1`（Windows）两个安装脚本都随本 skill 一起分发，始终同时存在。** 不要臆断某平台“只有 setup.sh / 缺少 setup.ps1”，也不要靠 `ls`/`Test-Path` 先去核验脚本是否存在——直接按平台执行对应入口即可。**“Windows 下找不到安装脚本”不是真实情况，更不能当作降级到句级插值的理由。** 若 `$SKILL_DIR\scripts\setup.ps1` 真的读不到，说明 `SKILL_DIR` 指错了目录：请把它重新指向当前 `video-redaction/SKILL.md` 的所在目录再执行，而不是改走降级。
**Setup 必须按平台选择唯一入口并作为独立工具调用执行：mac/Linux 用 `/bin/bash "$SKILL_DIR/scripts/setup.sh"`；Windows PowerShell 用 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$SKILL_DIR\scripts\setup.ps1"`。** `SKILL_DIR` 使用当前 skill 的绝对目录且始终加引号;不要外加 `nohup`、`&`、`Start-Job`、`cat` 或外部 guard。`setup.sh` 内部用 `nohup`、`setup.ps1` 内部用 `Start-Process` 持久化安装，入口命令会快速返回；两个脚本遵循相同的 `.ready` / `.python` / `.ffmpeg` / `.installing` 协议。
**除维护 `setup.sh` / `setup.ps1` / `asr_funasr.py` 外，禁止继续生成新的脚本写入到 skill 中**(脚本会漂移出评测视野,且本 skill 的混音统一走本地 `ffmpeg` 直调,不要再包一层 Python)
**禁止继续新增临时脚本**（同上；一次性组合逻辑优先写在 Agent 消息里而不是落盘）
**字幕敏感词需要 AI 进行识别**（硬字幕字体/花体差异大，正则匹配漏检率高，必须靠 OCR + 大模型语义判定）
**mediakit 任务仍由 Agent 直接执行，禁止用 Python 封装 `mediakit-cli`。** 人声分离、抽帧、擦除、合流、压制继续走 `mediakit-cli` 直调；**音频混合统一走本地 `ffmpeg` CLI 直调**,不要再引入 `ffmpeg-python` / `pydub` / `av` 之类 Python 包装层。
**`separate-voice` 的 `bgm.mp3` / 环境音 / 音效可能受源片质量、声道布局和用户环境影响而丢失部分内容。** 这不是一律视为流程错误。默认优先用 `vocals + bgm + beep`；若 `bgm` 明显丢失关键环境声/转场音效/游戏音效，可切到更保守的回退路线（如 `original_audio` 打孔 + beep，或 `original_audio` 打孔后再叠可用的 `bgm`），优先保住成片听感与环境声连续性。
**音频去敏固定分三步执行(已实测)**:① `vocals` 敏感区间静音后与 `bgm` 混成 `base.wav`;② 生成全程 1000Hz `sine`,用 `volume=0:enable='${NON_SENSITIVE_EXPR}'` 关闭所有非敏感区间,再补 `volume=18dB`,得到 `beep.wav`;③ `base.wav + beep.wav` 二次混成最终音频。`sine` 默认约 `-18dB`,所以 `+18dB` 不能省;禁止用 `volume=if(...)`,也不再使用 `output_1min.mp3` / `dd6a0e.mp3` / `-stream_loop -1` / 多路 `adelay` 作为正式路径。每步都保留 `-t "$DUR"`、`-fs 209715200`;所有 `amix` 必须写 `duration=first:normalize=0`,最终混音追加 `alimiter=limit=0.97:level=disabled`。**`beep.wav` 生成后直接进最终混音,不做 volumedetect 自检、不提交 MP3 试听片段给用户确认。** 详见 [敏感词音频处理.md](reference/敏感词音频处理.md)。
**`enable=` 时间表达式必须"外双内单"包好**:`-filter_complex "…volume=0:enable='between(t,1,2)+…'…"`。mac/Linux 用反斜杠续行；Windows PowerShell 用 `& $FFMPEG_BIN` 调用并使用反引号续行或单行命令，禁止把 Bash 的行尾 `\` 原样复制到 PowerShell。详见 [敏感词音频处理.md](reference/敏感词音频处理.md#翻车-4enable-表达式里的逗号没保护--no-such-filter-1)。
**词级时间戳必须跑 `scripts/asr_funasr.py`**（句级插值误差 ±150ms 会漏脏话打哔）；句级文案用 `mediakit-cli video asr-subtitles`；硬字幕文案用 `video-ocr` 校准。**禁止另写临时 ASR 脚本**（能省则省，冗余脚本反而造成对齐漂移，见 [文案校准.md](reference/文案校准.md)）
**ASR 结果必须校验**：`asr-subtitles` 终态必须有非空 `result.subtitles[]`，FunASR 必须有非空 `segments[]/words[]`；空数组、缺字段或全空文本都视为失败，不得继续生成候选、不得用视频理解臆造对白。FunASR 失败时必须让用户在“修环境 / 接受句级插值降级”中选择，**不得自行降级**；降级前必须已按平台真实执行过 `setup.sh` / `setup.ps1` 并贴出其报错，**不能以“Windows 没有安装脚本 / 找不到 setup.ps1”作为降级理由**（该脚本随 skill 分发，一定存在）。
**三个硬 Gate**：Gate 0 `probe-video-metadata` 无音轨即终止；Gate 1 候选敏感词必须在一个单独回复中展示并等待用户下一条消息明确确认；Gate 2 输入有硬字幕时，只有 `add-subtitle-to-video` 的终态结果才是可交付成片。用户最初说“处理视频”不算 Gate 1 确认，擦除后视频和 mux 后视频都只是中间产物。
**asr-subtitles 必须跑在人声分离后的 `vocals.mp3` 上**（**禁止**对原视频/原音轨直接跑；BGM/笑声/掌声/观众声会污染 ASR 导致漏识别脏话或同音字。`separate-voice` 是必跑前置，见 [音频处理.md](reference/音频处理.md)）
**字幕重建禁止跳过（Step 8-9）**：检测到原硬字幕后立即设置 `MUST_REBUILD_SUBTITLES=true`，不再询问“是否需要新字幕”。Gate 1 通过后必须走 [文案校准.md](reference/文案校准.md#校准逻辑agent-语义融合裁决) 产出 `subtitles.json`，再调用 `add-subtitle-to-video`；不允许直接用 asr-subtitles 原文，也不允许交付无字幕的 erase/mux 中间结果。只有原视频无硬字幕且用户明确不要新字幕时才可跳过。

# mediakit-cli 调用约定

本 skill 安装在**已经有 `mediakit-cli` 的宿主 Agent** 中。鉴权由宿主在每次调用工具时下发，临时 token 约 **9 分钟**，没有续期逻辑。

因此必须遵守：

1. 所有 `mediakit-cli` 命令由 Agent 在宿主里直接执行，不要用 Python 封装。
2. 本 skill 的所有真实 `mediakit-cli` 业务调用（含 `shared query-task`）都固定注入 `DOUBAO_MEDIAKIT_RUNTIME=scene-video-redaction`；不要写成 `--DOUBAO_MEDIAKIT_RUNTIME` 之类的业务 flag。POSIX shell 直接前缀在命令前；PowerShell 先设 `$env:DOUBAO_MEDIAKIT_RUNTIME="scene-video-redaction"` 再执行命令。
3. 沿用宿主已注入的其他环境，不要改写鉴权相关变量。
4. Cloud 异步任务：提交后读 `task_id`，再用

   ```bash
   DOUBAO_MEDIAKIT_RUNTIME=scene-video-redaction mediakit-cli shared query-task --task-id <task_id> --poll-complete
   ```

   CLI 会在约 **9 分钟**到时自动退出。未到终态时，用**同一个** `task_id` 再跑一次（宿主会下发新 token），不要重新提交任务。

5. **不要把整个流程包进一个长进程里。** 提交任务、轮询任务、下载产物、调用 ffmpeg、再发下一个 mediakit 任务，这些都可以拆成多次独立执行；跨步骤靠 `task_id`、本地文件路径、`result.*_url` 衔接即可。
6. **各个 mediakit 子命令的输入 flag 以各自文档为准，不要自行归纳统一规则。** 本 skill 只关注两种输入形态：**HTTP/HTTPS URL、本地文件路径**。其中 `video-understand-router` 有两个强制参数：输入固定用 `--video-urls`（复数），即使一次只传 1 个视频也不能写成 `--video-url`；同时必须传 `--prompt`，值必须使用 [视频理解佐证.md 的完整 Prompt](reference/视频理解佐证.md#prompt-要求)，不得省略、留 `<prompt>` 占位符或传空字符串。终态 `result.*_url` 是有效期约 24h 的 HTTP 临时链接，**mediakit → mediakit 的步骤把它原样传给下一步即可，不要下载中间产物**（省磁盘、省时间，也不受本地 PATH/权限影响）。**只有以下三种情况才下载到工作目录**：①喂给 **ffmpeg**（base/beep 分步混音）；②喂给本地 **FunASR 脚本**（`scripts/asr_funasr.py` 读本地路径）；③**Agent 要看图**（雪碧图判定硬字幕）或**最终成片交付**。链接会过期，要用就趁早下。

## 媒体输入

当业务参数需要公网可访问媒体，而用户仅提供本机文件路径时，CLI 的 Cloud 输入适配器会处理上传。无需新增上传命令或上传参数。

## JSON 参数传参

对象或对象数组参数必须传合法 JSON 字符串，不能用逗号分隔或裸文本。`array<string>` 仍用逗号分隔或重复 flag，不要套用本节。

POSIX / bash / zsh：用单引号整体包裹，保留 JSON 内部双引号。

```bash
DOUBAO_MEDIAKIT_RUNTIME=scene-video-redaction mediakit-cli editing add-subtitle-to-video --video-url "<url>" --subtitles '[{"start_time":0,"end_time":3,"subtitle_text":"大家好"}]'
```

Windows PowerShell：单引号或 `$json` 变量会使传给 CLI 的 JSON 丢失内部双引号，常见报错为 `invalid character 's'` / `'t'`。必须把 JSON flag 放在 `--%` 之后；整段 JSON 用双引号包裹，JSON 内部的 `"` 写成 `\"`。带空格的路径、prompt 及其他普通参数全部放在 `--%` 之前。`--%` 之后禁止使用 PowerShell 变量。

```powershell
$env:DOUBAO_MEDIAKIT_RUNTIME="scene-video-redaction"
mediakit-cli editing add-subtitle-to-video --video-url "C:\path\video.mp4" --subtitle-pos-preset bottom_center --subtitle-font-size <subtitle_font_size_px> --% --subtitles "[{\"start_time\":0,\"end_time\":3,\"subtitle_text\":\"大家好\"}]"
mediakit-cli video erase-video-subtitle-pro --video-url "C:\path\video.mp4" --mode Subtitle --model-version v5 --% --erase-ratio-location "[{\"top_left_x\":0,\"top_left_y\":0.56,\"bottom_right_x\":1,\"bottom_right_y\":0.69}]"
```

Windows 禁止以下写法：

- `'[{...}]'` 单引号 JSON
- `--flag $json` 或 `--flag "$json"`
- `Get-Content` 读取 JSON 后再作为 flag 传入
- `--flag @C:\file.json`
- `cmd /c` 多层转义

# 参考文档一览

所有使用指南存放在 `reference` 下。

- [环境准备.md](reference/环境准备.md) FunASR 安装(会话启动即与 probe/抽帧并行,最长杆前置);阶梯 系统 → venv → 告知用户,不做前置探测
- [安装.md](reference/安装.md) 环境入口摘要
- [前置探测.md](reference/前置探测.md) **最先执行**；probe-video-metadata + 抽帧决定后续分支
- [音频处理.md](reference/音频处理.md) 人声分离 + FunASR + asr-subtitles 校准
- [敏感词检测.md](reference/敏感词检测.md) 大模型敏感词处理；含**用户确认 Gate**
- [文案校准.md](reference/文案校准.md) OCR + asr-subtitles + FunASR + 视频理解 四路对齐
- [视频理解佐证.md](reference/视频理解佐证.md) 场景内敏感词判定
- [敏感词音频处理.md](reference/敏感词音频处理.md) base.wav + sine beep.wav 分步生成与最终混音
- [字幕处理.md](reference/字幕处理.md) 有硬字幕:`video-ocr --mode Detailed` 分析字幕位置 → 归纳成**一个框**(分散时合并成 ≤20 个框放同一次调用) → `erase-video-subtitle-pro` **一次擦完**(带框防误擦水印,不分时段、不发多任务)
- [合并.md](reference/合并.md) 音视频合流与成片
- `byted-mediakit-editing/reference/add-subtitle-to-video.md` 调 `add-subtitle-to-video` 前**必须重读**；位置预设、字号上限、宽度约束都以该 reference 为准

# 工作流程

顺序有三个硬 Gate，跨过前不得推进：

**Gate 0（前置探测）**：先跑 `probe-video-metadata`。

- `result.audio_stream_meta == null` → **直接终止**，本 skill 无有意义流程可跑（无音频既无对白打哔也无 ASR 校准）。回复用户"视频无音轨，无需去敏"。
- 有音轨才继续。**画布尺寸和 orientation 从 `probe-video-metadata` 的 `result.video_stream_meta.width/height` 读**(判横竖片,用于 `add-subtitle-to-video` 位置预设二选一)。**不用 cropdetect / content_box**,也不用从帧里读原字幕位置——那些规则容易把新字幕压到画面顶部。字幕擦除与压制**全部走 mediakit**:擦除走 [字幕处理.md](reference/字幕处理.md) —— `video-ocr --mode Detailed` 分析字幕位置 → 归纳成**一个擦除框**(位置分散时合并成 ≤20 个框放**同一次**调用的 `--erase-ratio-location`) → **一次** `erase-video-subtitle-pro` 擦完。**带框是为防误擦抖音水印/台标/UP 主标签**(裸发让服务端自动定位实测会误伤);**一次调用是因为** `--erase-ratio-location` 单次支持 20 框、Subtitle 模式只擦"框内∩下半屏∩OCR判定是字幕",不必按时段切多任务。压制用 `add-subtitle-to-video` 的 `--subtitle-pos-preset` + `--subtitle-font-size`（**执行前必须重读 `byted-mediakit-editing/reference/add-subtitle-to-video.md`；字号按 reference 的 height/width 约束计算或直接省略走工具默认值，禁止再写死 `45`；无自定义 x/y 坐标**；位置横屏 `bottom_center` / 竖屏 `lower_third`）。
- **雪碧图判定硬字幕**:用 Step 1 那张 5×5 雪碧图(25 格覆盖全片)判"有无硬字幕",任一格命中即判"有"。有则先跑 `video-ocr --mode Detailed` + OCR×ASR 交叉确认并归纳框；Gate 1 通过后再一次提交 erase。**禁止用本地 ffmpeg -ss 抽帧**,统一走 mediakit。

雪碧图判定画面是否有硬字幕:

- **无硬字幕** → 跳过 `erase-video-subtitle-pro` 和 `video-ocr`,在 Gate 1 候选确认回复中一并询问用户是否需要压制去敏字幕。
- **有硬字幕** → 立即设置 `MUST_REBUILD_SUBTITLES=true`。先跑 `video-ocr --mode Detailed` 并归纳擦除框，但 **Gate 1 前不提交 erase**；用户确认候选后再一次提交 `erase-video-subtitle-pro`，随后必须重建并压制 `subtitles.json`。

**Gate 1（敏感词用户确认）**：证据对齐产出候选敏感词清单后，必须以表格发给用户并立即结束当前回复。收到用户下一条消息明确确认/增删前，禁止继续调用 erase、ffmpeg、mux、字幕压制或交付工具；初始处理请求、沉默、默认策略、模型自判均不算确认。见 [敏感词检测.md](reference/敏感词检测.md)。

Gate 通过后，音频去敏走 [敏感词音频处理.md](reference/敏感词音频处理.md) 的三阶段方案：先生成 `base.wav`,再生成全程 sine 门控的 `beep.wav`,最后二次混音。全程使用本地 `ffmpeg` 直调；beep 与最终混音生成后直接进合流，不做 volumedetect 自检、不提交试听片段给用户确认。

## 工作流步骤（严格顺序 + 局部并行）

```
Step 1  【会话一启动就同时发】
          ① probe-video-metadata（秒级，判有无音轨）
          ② 雪碧图抽帧（5×5，25 格覆盖全片）
          ③ 独立命令执行 setup（ffmpeg + FunASR，本地环境准备，与 ①② 无数据依赖）
             —— 全程只启动这一次!用 guard 文件幂等,后面每步别再重复启动/播报(见 [环境准备.md](reference/环境准备.md#安装时机))
Step 2  probe 返回：
          无音轨 → 终止 skill（asr / video-understand 等付费云任务一个都不发；FunASR 安装进程自然结束并缓存供下次复用）
          有音轨 → 先读视频理解佐证文档，再并行发起 separate-voice（音频线打底）+ video-understand-router（必须传 --prompt，场景语义，只依赖原视频 URL）；同时按 width/height 判横竖屏、确定字幕预设位置
Step 3  雪碧图判定结果（任一格子有字幕即判"有"）：
          有硬字幕 → 设置 MUST_REBUILD_SUBTITLES=true → video-ocr --mode Detailed → 归纳擦除框；Gate 1 前不 erase
          无硬字幕 → 在 Gate 1 回复中一并询问是否压制去敏字幕
        （separate-voice 产 vocals.mp3 后并行 asr-subtitles + FunASR，与 Step 3 视觉线互不阻塞）
Step 4  先校验 ASR 非空，再生成敏感词候选：OCR + asr-subtitles + FunASR + 视频理解
        —— 直接吃各路原始证据，宁多勿漏；不做文本融合
        —— 兜底：若雪碧图判"无字幕"但 ASR 命中脏话，Agent 回看对应格子；命中则回补 OCR 和擦除框，Gate 1 后再 erase
Step 5  Gate 1：展示候选表并结束回复；等待用户下一条消息明确确认/增删
Step 6  确认通过 → erase（如有硬字幕，默认一次擦完即视为完成，不再抽验收帧）与 base/beep 混音并行
Step 7  mux-audio-video（beep.wav 生成后直接进最终混音，不自检、不提交试听片段）
Step 8  MUST_REBUILD_SUBTITLES=true 或无硬字幕但用户要字幕 → 文案校准并生成 subtitles.json
Step 9  add-subtitle-to-video；有硬字幕时此任务终态成功后才允许交付
```

**关键规则**：

- **雪碧图抽帧判定硬字幕**：一次 `extract-frames --enable-sprite=true --sprite-rows=5 --sprite-cols=5 --time-interval=<duration/25>` 出一张 25 格雪碧图，Agent 一次视觉判定就把全片时间轴扫一遍。任一格命中即判"有"——比抽 1 张或 3 张独立帧覆盖度高得多，token/延迟都更低。判定标准与排除项见 [前置探测.md § 3](reference/前置探测.md#3-雪碧图抽帧mediakit-extract-frames---enable-sprite判定有无硬字幕)。
- **兜底复检**：若雪碧图判"无字幕"但 ASR 命中脏话，Agent 回看雪碧图对应命中词 `start_time` 的格子二次判定；命中则回补 `video-ocr` 和擦除框，Gate 1 通过后再提交 erase。
- **字幕擦除一次调用擦完**：`video-ocr --mode Detailed` 拿 `Subtitle` / `Others` 分类,排除 `Others`(抖音水印 y ≈ 0.877-0.981/台标) → 把 `Subtitle` 条目归纳成**一个最小外包框**(位置明显分几簇才合并成 ≤20 个框,放**同一次**调用的 `--erase-ratio-location`) → **一次** `erase-video-subtitle-pro` 提交。带框防误擦水印;一次够是因为单次支持 20 框、Subtitle 模式只擦"框内∩下半屏∩OCR判定是字幕"。**不传 `--time-segment-filter`、不切多任务**;仅在成片阶段肉眼发现明显残留才补框重提一次。详见 [字幕处理.md § 擦除](reference/字幕处理.md#擦除ocr-定位一个框一次擦完走-mediakit)。
- **`asr-subtitles` 必须跑在 `vocals.mp3` 上**（`separate-voice` 前置必跑），禁止对原视频/原音轨直接跑。
- **敏感词候选（Step 4）吃原始多路证据**：OCR / asr-subtitles / FunASR 各自的文本都拉进候选，命中即入清单，交给用户在 Gate 1 增删。**不在这一步做文本融合**——多路冗余对"漏掉脏话"更保险。
- **文案校准（Step 8）**：有硬字幕时强制执行；无硬字幕时仅按用户选择执行。Agent 逐句用 OCR + asr-subtitles + FunASR + 视频理解融合裁决，直接产出 `add-subtitle-to-video --subtitles` 所需的 `subtitles.json`。
- **音频证据线**（`separate-voice` → `asr-subtitles` + FunASR）与**视觉证据线**（雪碧图判定 → OCR + 擦除框）互不阻塞；Step 4 汇合证据，实际 erase 必须等 Gate 1。
- **erase 默认一次擦完即视为完成**，不再抽验收帧、不做人工确认（仅在成片阶段肉眼发现明显残留时才补框重提一次）。
- **唯一强串行**：erase（如有硬字幕）+ base/beep 混音 → mux-audio-video → add-subtitle-to-video。base/beep 分步混音可与 erase 并行；文案校准可与 mux 并行（都是本地/CPU 任务）。

```mermaid
flowchart TD
  START([会话启动]) --> P[Step 1<br/>probe-video-metadata<br/>秒级]
  START --> BLIND[Step 1<br/>extract-frames<br/>雪碧图 5×5, 25 格]
  START --> INST[Step 1<br/>setup<br/>ffmpeg + FunASR]

  P --> ORI[Step 2<br/>判横竖屏<br/>确定字幕预设位置]
  P -->|有音轨| SV[Step 2<br/>separate-voice<br/>必跑]
  P -->|有音轨| UND[Step 2<br/>video-understand-router<br/>场景语义, 只依赖原视频 URL]
  P -->|无音轨| STOP([终止 skill<br/>asr/理解都不发])

  BLIND -->|有硬字幕| VOCR[Step 3<br/>video-ocr --mode Detailed<br/>Subtitle/Others 分类]
  VOCR --> BOX[Step 3<br/>归纳擦除框<br/>等待 Gate 1]
  BLIND -->|无硬字幕| Q[Step 3<br/>询问是否压新字幕]

  SV --> ASR[asr-subtitles<br/>对 vocals.mp3]
  SV --> FUN[FunASR 推理<br/>对 vocals.mp3 词级]
  INST -.安装就绪.-> FUN

  VOCR --> CAND[Step 4<br/>敏感词候选<br/>OCR + ASR + FunASR + 视频理解<br/>吃原始多路证据]
  ASR --> CAND
  FUN --> CAND
  UND --> CAND
  CAND -.->|雪碧图判无字幕<br/>但 ASR 有脏话| RECHECK[兜底复检<br/>Agent 回看雪碧图对应格子<br/>⌈start_time/(d/25)⌉]
  RECHECK -->|复检有字幕| VOCR
  RECHECK -->|复检有字幕| BOX
  CAND --> UG{Step 5<br/>Gate 1 人工确认}

  UG -->|下一条消息明确确认| MIX[Step 6<br/>base + sine beep 分步混音<br/>不自检不试听]
  UG -->|下一条消息明确确认且有硬字幕| D[Step 6<br/>erase-video-subtitle-pro<br/>一次擦完即完成]

  D --> H[Step 7<br/>mux-audio-video]
  MIX --> H

  H -->|必须或用户需要新字幕| F[Step 8<br/>文案校准<br/>Agent 语义融合<br/>subtitles.json]
  VOCR -.证据.-> F
  ASR -.证据.-> F
  FUN -.证据.-> F
  UND -.场景消歧.-> F
  Q -->|需要| F
  Q -->|不需要且原片无硬字幕| END[输出成片]

  F --> ADD[Step 9<br/>add-subtitle-to-video<br/>预设位置 + 像素字号]
  ADD --> END
```

## 并行策略（重要）

- **Step 1 并行（会话一启动就同时发，不要串行等）**：`probe-video-metadata`（秒级）、雪碧图抽帧（5×5，25 格，间隔 `duration/25`）、**setup（ffmpeg + FunASR）**作为三个独立工具调用同时启动。setup 只启动一次、guard 文件幂等，后续等待 `.ready` / `.python` / `.ffmpeg`。判定标准见 [前置探测.md § 3](reference/前置探测.md#3-雪碧图抽帧mediakit-extract-frames---enable-sprite判定有无硬字幕)。
- **Step 2 触发（都 gate 在"有音轨"之后，付费云任务不空跑）**：probe 返回**有音轨**后，先读 [视频理解佐证.md](reference/视频理解佐证.md)，再**并行**发起 `separate-voice` 与 `video-understand-router`。后者只依赖原视频 URL，但提交命令必须同时带 `--video-urls` 和非空 `--prompt`，Prompt 使用参考文档中的完整固定内容；Step 4 直接取场景结论。同时读 `width`/`height` 判横竖片、选字幕位置预设（横屏 `bottom_center` / 竖屏 `lower_third`）。若 probe 返回**无音轨** → 终止 skill,`asr` / `video-understand` 等付费云任务**一个都不发**;FunASR 安装进程自然结束,缓存留家目录下次复用。
- **Step 3 分叉**：雪碧图到手决定字幕路线。有硬字幕先 OCR 并归纳框，设置 `MUST_REBUILD_SUBTITLES=true`，但 erase 延后到 Gate 1 通过；无硬字幕则在 Gate 1 回复中询问是否新增字幕。
- **音频线独立**：`separate-voice` 产 `vocals.mp3` 后并行 `asr-subtitles` 和 FunASR，不阻塞视觉线。
- **Step 4 敏感词候选**：直接消费 OCR / ASR / FunASR 各自的文本，命中即入清单，**不做融合**。若雪碧图判“无字幕”但 ASR 命中脏话，回看对应格子；命中则回补 OCR 和擦除框，实际 erase 仍等 Gate 1。
- **video-understand-router** 在 Step 2（probe 确认有音轨后）与 `separate-voice` 并行发起（默认必发，最稳），提交时必须传 [视频理解佐证.md](reference/视频理解佐证.md#prompt-要求) 中的完整 `--prompt`，Step 4 直接取其场景结论做「词 × 场景」裁定。无音轨则和 asr 一样不发。
- **Step 6 base/beep 分步生成与最终混音** 可与 erase 并行；beep 轨和最终混音生成后直接可用，不做 volumedetect 自检、不提交 MP3 试听片段。
- **Step 7 mux** 强串行等 erase 完成 + amix 完成（erase 一次擦完即视为完成，不等验收帧）。
- **Step 8 文案校准**在有硬字幕时强制执行，可与 Step 7 mux 并行。
- **Step 9 add-subtitle** 依赖 Step 7 (mux 产物) + Step 8 (`subtitles.json`)；有硬字幕时 Step 9 失败必须报告失败，禁止降级交付无字幕中间视频。
