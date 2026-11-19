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

## 媒体产物直接交付（强制）

1. 本 Skill 的媒体产物必须使用本次 CLI 成功结果中真实、可消费的输出链接交付。同步结果直接读取实际输出字段；异步提交仅有 task_id 时先查询原任务，只有成功终态的真实媒体结果可交付。不得把输入素材地址、任务 ID、示例或推测地址当作产物。
2. 面向用户的视频和图片交付，必须是一句简短的已完成说明，紧接对应 RichMediaCard。refs 仅使用 CLI 此次真实返回、当前卡片可消费的资源引用，不新增宿主未声明的字段。卡片表达式独立成行，不放代码块、行内代码、引号或 Markdown 链接，不转义标签。
3. 视频和图片的资源地址只作为卡片内部引用。禁止在卡片外输出裸 URL、Markdown 媒体链接、下载链接栏或文件路径；不得用文字总结替代卡片，不为发卡额外要求 present_files。默认不附生成参数、Prompt、工具名、日志、任务 ID 或未经验证的质量结论。
4. 禁止为了交付下载媒体、转存、重新上传、缩短／拼接／改写链接，或通过其他工具和本地文件替代 CLI 的真实输出入口。用户已提供的本地输入与 CLI 自身的输入上传适配不属于产物转存，保留原有能力；CLI 所需技术读取与宿主卡片读取也不因此被禁用。
5. 多步骤处理中，仍需交付的每个成功视频／图片结果立即逐项展示；后续 CLI 操作直接使用前一步真实输出地址作为输入，不先下载为本地文件。完成已确认后期后，最终成片使用最后一次实际处理结果交付，不能拿早期片段或输入地址代替。
6. 编辑、剪辑或纯技术处理配文使用“已经为你完成……”并概括实际改动；新生成使用“已经为你生成……”。片段标明序号，最终拼接结果说明为完整视频，不将处理原片说成重新生成，不重复已确认规格。
7. 不新增审片、评分、自动修复或重生；已确认的后续制作照既定授权执行。查询真实任务状态、检查资源入口以及原本所需的前置技术读取不属于内容验收，不借此寻找缺陷或额外处理。
8. 内部回传真实链接不等于用户交付。实际交付方仍按宿主既定的视频负责执行方／图片 mainagent 分工执行，任何实际交付方都必须遵守上述卡片格式。已交付状态随交接保留，mainagent 不重复代发已经交付的视频。
9. 若既有流程委派 OrganizerAgent，hint 必须明确工具与全部已确认参数、适用的 RichMediaCard 格式，以及成功产物立即直交、禁止内容审查和自动修复重生的约束，不能只给规则链接。工具路由、视频确认、每批两项限制和异步委派保持宿主原合同，不在本 Skill 新建另一套编排流程。
10. 卡片展示不可用、入口不可消费或明确展示失败时，保留原结果和错误，仅恢复该项展示；不得降级链接／下载交付，也不得重新生成、重复处理或新建媒体对象。按原宿主规则由原交付方恢复，依赖该交付的后续步骤暂停，无依赖且已授权任务可继续；技术重试遵守已有上限，不新增数值、不循环重试。
11. 用户已取消或明确拒收的结果不发卡、不恢复后续制作，内部记录真实状态，不能将其记为 delivered。已有展示成功的同一产物不重复发送；原始结果直接采用为最终成片时复用交付记录并注明采用关系。
12. 没有展示成功反馈时，不把输出标签直接记为 delivery_status=delivered，也不据此重复发卡；片段交付不等于最终成片交付。状态与真实引用合并进已有制作记录，不额外建立多套清单。


卡片格式：`<RichMediaCard>{"refs":["本次 CLI 实际返回且可消费的媒体引用"]}</RichMediaCard>`。此处仅为规范结构示意；实际交付必须使用真实引用，并将卡片独立成行，不包裹代码或引号。

音频、字幕等其他媒体文件也必须使用 CLI 原始结果引用，展示格式按宿主原有规范执行，不推断额外卡片类型。没有媒体产物的文字、JSON、元信息等结果照常说明，不发空卡片。CLI 的 HTML、画布及其预览截图继续按原有 CLI 协议执行，不适用本媒体交付格式。

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
