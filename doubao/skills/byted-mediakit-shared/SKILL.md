---
name: byted-mediakit-shared
version: '0.2.2'
license: 'MIT'
description: 'MediaKit 是面向音视频与图像处理的专业工具集，覆盖音视频剪辑与合成、音频媒资探测与人声分离、视频理解与增强、图像增强与内容理解等工作流。用户明确提出叠加、字幕压制、滤镜、运镜、提取字幕、语音转字幕、裁剪、拼接、调速、混音、音视频处理、图片增强或擦除、视频分析或画质增强目标时，先加载本 Skill，再按对象和目标选择 audio、editing、image 或 video；仅说明媒体类型而未说明处理目标时先澄清。不承担具体能力参数说明。'
permissions:
  - shell
metadata:
  requires:
    bins: ['mediakit-cli']
  cliHelp: 'mediakit-cli --help'
  product: 'mediakit-cli-doubao/skills'
  domain: shared
  capability_count: 0
---

# MediaKit 专业媒体处理入口

MediaKit 是面向音视频与图像处理的专业工具集。它将常见的媒体加工、内容理解和
智能增强能力统一到 `mediakit-cli`，适合从素材处理到成片制作的完整工作流。

## 鉴权

- Cloud 调用所需鉴权、日志标识与端点配置由当前运行环境注入；缺失或不可用时停止执行。
- 不在命令、Skill、配置文件或输出中写入鉴权值。

## 最高优先级交付门禁

当工具结果或 `query-task` 终态结果返回 `agent_hint.type=mediakit_artifact_delivery` 时，按以下硬约束执行：

1. 中间产物：仅当该产物 URL 会被本工作流下一步工具直接作为输入时，继续执行，不展示、不确认；最终产物生成后再统一确认一次。
2. 最终产物：本轮必须且只能调用 `agent_hint.next_tool`（`interaction_ask`），参数原样使用 `agent_hint.arguments`，向用户确认“当前链接有效期为 24 小时，是否需要转存为 7 天有效期链接？”。用户作出选择前，禁止调用 `present_files` 或 RichMediaCard、禁止在回复正文给出任何产物 URL、禁止用纯文本提问代替 `interaction_ask`、禁止声明任务完成。
3. 用户选择 `keep_24h`：交付工具结果中的真实原始产物 URL。
4. 用户选择 `transfer_7d`：依次下载 MediaKit 临时产物为本地正式文件、调用 `FileBatchUpload` 上传，并对每个正式文件立即单独调用一次 `present_files`，不得囤积。
5. 必须实际交付最终产物后才能声明任务完成；交付失败时必须使用同一个正式文件重试，不得改用其它交付格式、不得声称成功，也不得无故退出。

## 能力范围

- **视频剪辑与合成**：裁剪、拼接与转场、调速、音量调整、画面翻转和滤镜、运镜、字幕压制、混音、音视频提取与合流、淡入淡出以及多画面编排。
- **音频与音轨处理**：音频转码与媒资信息探测、语音边界定位，以及人声与背景声分离。
- **图像处理与内容理解**：尺寸缩放与体积治理、元信息探测、裁剪旋转翻转与圆角、颜色与锐化、负片、模糊与打码、水印、背景移除、文字识别、画质评估与智能裁剪等。
- **视频理解与增强**：视频内容理解、剧情/剧本与高光拆条、画质增强与画质检测、抽帧、从视频提取字幕、语音转字幕、字幕识别与擦除、水印与隐私保护、人像或绿幕抠像、媒资探测、场景与语义分段、画面文字识别、转码转封装等。

## 能力选择与优先加载

按用户的处理对象和明确目标选择领域 Skill：

| 用户目标                                                                                                         | 优先加载                 |
| ---------------------------------------------------------------------------------------------------------------- | ------------------------ |
| 对现有素材进行裁剪、拼接或转场、调速、滤镜、运镜、字幕压制、混音或合流                                     | `byted-mediakit-editing` |
| 探测音频媒资信息、音频转码，或分离音频或视频中的人声与背景声                                                     | `byted-mediakit-audio`   |
| 处理单张图片的尺寸体积治理、增强擦除、打码水印、文字识别、画质评估或背景移除                                     | `byted-mediakit-image`   |
| 进行视频理解或高光拆条、抽帧、提取字幕、语音转字幕、字幕识别或擦除、画质增强或检测、抠像、媒资探测或场景分段 | `byted-mediakit-video`   |

如果一个请求同时包含多个阶段，先加载与主要产出最匹配的领域 Skill，再按工作流
需要加载其他领域 Skill。只说明“处理一个视频”或“处理一张图片”而没有说明目标
时，先向用户澄清，不要根据媒体类型猜测具体能力。

选定领域后，必须先读取该领域 Skill，再读取最终选定工具的完整 reference，最后
依据当前 CLI 的机器合同构造参数。共享入口只负责能力导航和通用 CLI 使用方式，
不重复具体工具的参数、枚举或结果字段。

## 可用性检查

```bash
mediakit-cli --version
mediakit-cli --help
mediakit-cli --domains
```

## 使用流程

1. 按对象和目标选择领域 Skill；只说明媒体类型而未说明目标时，先向用户澄清。
2. 选定工具后，先读取该工具的完整 reference，再读取实时 `--help` 与 `--schema`。
3. 必填参数必须来自用户真实输入；可选参数只在用户明确提供，或可从意图准确确定时填写。不能准确确定时省略，确为完成任务所必需时先澄清；不得伪造 URL、文件、枚举或业务参数。
4. 对象或对象数组参数按下方「JSON 参数传参」构造；Windows PowerShell 不得套用 bash 单引号。

## 命令发现

```bash
mediakit-cli --domains
mediakit-cli <domain> --help
mediakit-cli <domain> <tool> --help
mediakit-cli <domain> <tool> --schema
```

`--schema` 只读取当前 Cloud 机器合同，不发起业务调用；顶层包含 `name`、
`description`、`input_schema` 和 `output_schema`。

## 媒体输入

当业务参数需要公网可访问媒体，而用户仅提供本机文件路径时，CLI
的 Cloud 输入适配器会处理上传。无需新增上传命令或上传参数。

## 音视频元数据前置探测

- 当目标工具的限制依赖音视频时长、分辨率、文件大小、封装、编码、码率、采样率或声道，而用户没有提供可信元信息时，先加载对应领域 Skill：音频使用 `probe-audio-metadata`，视频使用 `probe-video-metadata`；editing 按实际输入类型复用这两个工具。
- 探测后必须将结果与最终目标工具 reference 的限制逐项比较；确认超限或不兼容时停止并要求用户更换或调整输入，不得盲目调用。
- 元数据探测不能保证后端一定处理成功，也不替代目标工具的专属约束；图片格式、大小和尺寸由图片 CLI 的工具级前置检查执行。

## JSON 参数传参

对象或对象数组参数必须传合法 JSON 字符串，不能用逗号分隔或裸文本。
`array<string>` 仍用逗号分隔或重复 flag，不要套用本节。

支持四种载荷写法：

- 内联 JSON：直接把 JSON 作为 flag 值传入。
- `@文件`：从本机 JSON 文件读取，例如 `--subtitles @./subtitles.json`。
- `-` stdin：从标准输入读取；同一命令全局至多一个 `-`。
- `file://`：从文件 URL 读取，例如 `file://./subtitles.json` 或 `file:///abs/path/subtitles.json`。

POSIX / bash / zsh：内联 JSON 用单引号整体包裹，保留 JSON 内部双引号；大 JSON 优先使用 `@文件` 或 stdin。

```bash
mediakit-cli editing add-subtitle-to-video --video-url "<url>" --subtitles '[{"start_time":0,"end_time":3,"subtitle_text":"大家好"}]'
mediakit-cli editing add-subtitle-to-video --video-url "<url>" --subtitles @./subtitles.json
jq -nc '[{"start_time":0,"end_time":3,"subtitle_text":"大家好"}]' | mediakit-cli editing add-subtitle-to-video --video-url "<url>" --subtitles -
```

Windows PowerShell：单引号或 `$json` 变量都会把 JSON 里的 `"` 剥掉，CLI 会报
`invalid character 's'` / `'t'`。必须把 JSON flag 放在 `--%` 之后；整段 JSON
用双引号包裹，JSON 内部的 `"` 写成 `\"`。带空格的路径等普通参数放在 `--%`
之前。`--%` 之后不要使用 PowerShell 变量。文件载荷也放在 `--%` 之后，优先使用
`file:///C:/...` 或 `@C:\...`。

```powershell
mediakit-cli editing add-subtitle-to-video --video-url "C:\path\video.mp4" --% --subtitles "[{\"start_time\":0,\"end_time\":3,\"subtitle_text\":\"大家好\"}]"
mediakit-cli video erase-video-subtitle-pro --video-url "C:\path\video.mp4" --mode Text --% --erase-ratio-location "[{\"top_left_x\":0,\"top_left_y\":0,\"bottom_right_x\":1,\"bottom_right_y\":0.2}]"
mediakit-cli editing add-subtitle-to-video --video-url "C:\path\video.mp4" --% --subtitles file:///C:/path/subtitles.json
```

Windows 内联 JSON 禁止：

- `'[{...}]'` 单引号 JSON
- `--flag $json` 或 `--flag "$json"`
- `Get-Content` 读出 JSON 后再当 flag 传入
- `cmd /c` 多层转义

## 异步任务

异步工具返回 `task_id` 后，使用：

```bash
mediakit-cli shared query-task --task-id <task_id>
```

完整轮询与结果约定见 [reference/query_task.md](reference/query_task.md)。
