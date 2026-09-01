---
name: byted-mediakit-shared
version: '0.2.1'
license: 'MIT'
description: 'MediaKit 是面向音视频与图像处理的专业工具集，覆盖音视频剪辑与合成、音频媒资探测与人声分离、视频理解与增强、图像增强与内容理解等工作流。用户明确提出叠加、字幕压制、滤镜、运镜、提取字幕、语音转字幕、裁剪、拼接、调速、混音、音视频处理、图片增强或擦除、视频分析或画质增强目标时，先加载本 Skill，再按对象和目标选择 audio、editing、image 或 video。不承担具体能力参数说明。'
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

## 能力范围

- **视频剪辑与合成**：裁剪、拼接与转场、调速、音量调整、画面翻转和滤镜、运镜、图片叠加、字幕压制、混音、音视频提取与合流、淡入淡出、文字滚屏、图转视频以及多画面编排。
- **音频与音轨处理**：音频转码与媒资信息探测、语音边界定位，以及人声与背景声分离。
- **图像处理与内容理解**：尺寸缩放与体积治理、元信息探测、裁剪旋转翻转与圆角、颜色与锐化、负片、模糊与打码、水印、背景移除、文字识别、画质评估与智能裁剪等。
- **视频理解与增强**：视频内容理解、剧情/剧本与高光拆条、画质增强与画质检测、抽帧、从视频提取字幕、语音转字幕、字幕识别与擦除、水印与隐私保护、人像或绿幕抠像与换脸、媒资探测、场景与语义分段、画面文字识别、转码转封装等。

## 能力选择与优先加载

按用户的处理对象和明确目标选择领域 Skill：

| 用户目标                                                                                                         | 优先加载                 |
| ---------------------------------------------------------------------------------------------------------------- | ------------------------ |
| 对现有素材进行裁剪、拼接或转场、调速、滤镜、运镜、叠加、混音、合流或图转视频                                     | `byted-mediakit-editing` |
| 探测音频媒资信息、音频转码，或分离音频或视频中的人声与背景声                                                     | `byted-mediakit-audio`   |
| 处理单张图片的尺寸体积治理、增强擦除、打码水印、文字识别、画质评估或背景移除                                     | `byted-mediakit-image`   |
| 进行视频理解或高光拆条、抽帧、提取字幕、语音转字幕、字幕识别或擦除、画质增强或检测、抠像换脸、媒资探测或场景分段 | `byted-mediakit-video`   |

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

直接把用户提供的输入值传给工具参数。本机文件请传本地文件路径（如
`/path/to/file.jpg` 或 `./file.jpg`），不要自行添加 `mediakit://` 前缀；CLI
的 Cloud 输入适配器会处理上传。无需新增上传命令或上传参数。

## 异步任务

异步能力返回 `task_id` 后，使用下列查询协议获取状态和终态业务结果。

豆包场景下 `query-task` **单次轮询最长 9 分钟**。使用 `--poll-complete` 时，到点后 CLI **正常退出**（`exit_code 0`），返回最后一次查询结果；`status` 仍可能为 `running`/`queued`，**不是状态异常**。未达终态时用**同一 task_id** 再次 query-task，长耗时任务（如 8K 画质增强）通常需多轮。暂不支持通过 CLI 调整该上限。

**Agent 禁止**将「exit 0 + running」当作故障排查；详见 [reference/query_task.md](reference/query_task.md) 的「Agent 行为」一节。

| 协议       | 说明                                    | 命令                             | 参考                                               |
| ---------- | --------------------------------------- | -------------------------------- | -------------------------------------------------- |
| query-task | 查询 Cloud 异步任务状态与终态业务结果。 | `mediakit-cli shared query-task` | [reference/query_task.md](reference/query_task.md) |
