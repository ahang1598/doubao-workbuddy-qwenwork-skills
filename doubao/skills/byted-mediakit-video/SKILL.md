---
name: byted-mediakit-video
version: 0.2.0
license: MIT
description: "面向视频文件或其中音轨的智能处理、媒资理解和画质治理目标，适用于视频内容分析、剧情与高光理解、从视频提取字幕、语音转字幕、字幕识别与擦除、视频增强、人像或绿幕抠像、媒资探测、场景切分和画面文字识别。若对象和目标族已明确属于视频增强、视频分析理解、视频内容结构化、从视频提取字幕、语音转字幕、视频字幕识别或擦除、视频媒资探测或抠像，但具体能力不确定，可先加载本 Skill 探索；若只说有视频而未说明业务目标，应先澄清。明确要把字幕或图片叠加压制到成片、或做裁剪、拼接、混音、合流、调速、转场或画面翻转的成片编辑诉求应路由到 editing；单张图片处理应路由到 image；音频媒资探测或人声分离应路由到 audio。"
permissions:
- shell
metadata:
  requires:
    bins:
    - mediakit-cli
  cliHelp: mediakit-cli video --help
  product: mediakit-cli-doubao/skills
  domain: video
  capability_count: 16
---
# video MediaKit Skill

## 使用规则

1. 先读取 `../byted-mediakit-shared/SKILL.md`，执行统一前置检查；该 Skill 缺失时停止并报告当前 Skill 包不完整。
2. 只从下表选择 `video` 域工具；相似能力按各工具“能力描述”和参数边界区分。
3. 执行前按需读取对应 reference；参数与结果说明来自同一份已审核文案，完整机器合同以当前 CLI `--schema` 为准。
4. 缺少必填参数、鉴权环境变量或真实输入资源时，向用户索取；通用可选字段只能透传用户明确提供的值，其他可选字段可由明确意图准确确定，但不得伪造。

## 工具列表

| 工具 | 说明 | 支持模式 | 命令 | 参考 |
| --- | --- | --- | --- | --- |
| analyze-video-highlights | 支持短剧 Miniseries 和小游戏 Game 两种分析模型，用于高光片段提取，并输出精准时间戳、高光打分、OCR 文本和画面描述，供二次开发或内容分析。 | Cloud | `mediakit-cli video analyze-video-highlights` | [reference/analyze-video-highlights.md](reference/analyze-video-highlights.md) |
| analyze-video-storyline | 用于剧情故事线分析，基于大模型视频理解分析单个或多个长视频并生成结构化剧情数据。分析结果包含两部分：按时间顺序排列的剧情片段，以及基于视频片段整理和归纳出的高光故事线。 | Cloud | `mediakit-cli video analyze-video-storyline` | [reference/analyze-video-storyline.md](reference/analyze-video-storyline.md) |
| asr-subtitles | 从视频或音频的语音中识别并提取带时间戳的字幕文本；适用于提取视频字幕、语音转字幕、听写对白等诉求。识别对象是音轨中的语音内容，不是画面上已烧录的硬字幕。 | Cloud | `mediakit-cli video asr-subtitles` | [reference/asr-subtitles.md](reference/asr-subtitles.md) |
| enhance-video | 用于视频画质增强。利用 AI 算法对输入视频进行分析，并智能执行包括但不限于视频去噪、色彩增强、清晰度提升、瑕疵修复和超分辨率的一系列优化操作。提供 standard 和 professional 两种版本：standard 兼顾处理速度与视频画质，内置高频使用的 10 余种增强算法，适用于视频分发场景的画质增强；professional 提供极致画质增强，内置 30 余种深度 AI 增强算法，适用于影视级视频制作。不同版本会影响增强算法的强度、适用场景与计费。 | Cloud | `mediakit-cli video enhance-video` | [reference/enhance-video.md](reference/enhance-video.md) |
| enhance-video-fast | 集成轻量级超分与智能画质增强，采用速度优先策略，高效兼顾处理效率与画面效果，尤其适用于处理时延敏感的业务场景。 | Cloud | `mediakit-cli video enhance-video-fast` | [reference/enhance-video-fast.md](reference/enhance-video-fast.md) |
| enhance-video-generative | 基于 Diffusion 扩散大模型技术提供生成式视频增强与修复，通过深度语义理解，智能补全和生成符合视频内容的真实细节，可修复视频在压缩或老化过程中损失的像素，最终产出自然、高保真的视频画面。 | Cloud | `mediakit-cli video enhance-video-generative` | [reference/enhance-video-generative.md](reference/enhance-video-generative.md) |
| erase-video-subtitle | 智能检测并擦除视频画面中已有的硬字幕，保留原始背景。<br>支持格式：主流视频格式如mp4、flv、ts、avi、mov、wmv、mkv。 | Cloud | `mediakit-cli video erase-video-subtitle` | [reference/erase-video-subtitle.md](reference/erase-video-subtitle.md) |
| erase-video-subtitle-pro | 用于字幕擦除（精细化版），对视频字幕进行高质量无痕擦除，并最大程度还原视频画面。 | Cloud | `mediakit-cli video erase-video-subtitle-pro` | [reference/erase-video-subtitle-pro.md](reference/erase-video-subtitle-pro.md) |
| generate-highlights-microdrama | 可用于短剧高光智剪，基于输入剧集的角色和剧情故事线理解提取高光片段，并按时长、产出个数、顺剪或跳剪等要求生成高光混剪、单集预告等视频。 | Cloud | `mediakit-cli video generate-highlights-microdrama` | [reference/generate-highlights-microdrama.md](reference/generate-highlights-microdrama.md) |
| generate-highlights-minigame | 支持识别小游戏录屏视频中的核心玩法与高光事件，例如连击、通关、极限操作，并快速生成用于买量推广的视频素材。可选提供游戏名称、玩法描述和高光定义，辅助更精准地识别精彩内容。 | Cloud | `mediakit-cli video generate-highlights-minigame` | [reference/generate-highlights-minigame.md](reference/generate-highlights-minigame.md) |
| matte-greenscreen-video | 可对绿幕或纯色背景的视频进行抠图，自动识别并保留主体，最终生成背景透明或纯色背景的视频。 | Cloud | `mediakit-cli video matte-greenscreen-video` | [reference/matte-greenscreen-video.md](reference/matte-greenscreen-video.md) |
| matte-portrait-video | 自动识别视频中的人物主体，移除原始背景，并生成背景透明或纯色背景的视频文件，适用于背景替换等后期处理场景。 | Cloud | `mediakit-cli video matte-portrait-video` | [reference/matte-portrait-video.md](reference/matte-portrait-video.md) |
| probe-video-metadata | 探测输入的视频 URL，输出标准化的媒资元信息。 | Cloud | `mediakit-cli video probe-video-metadata` | [reference/probe-video-metadata.md](reference/probe-video-metadata.md) |
| segment-scenes | 依据视频的转场和画面内容变化自动切分多个场景片段，输出每个场景片段的时间轴信息与对应的独立视频文件。 | Cloud | `mediakit-cli video segment-scenes` | [reference/segment-scenes.md](reference/segment-scenes.md) |
| video-ocr | 用于视频字幕识别（OCR），识别输入视频画面中的字幕信息，输出带时间戳的结构化文本数据。 | Cloud | `mediakit-cli video video-ocr` | [reference/video-ocr.md](reference/video-ocr.md) |
| video-understand-router | 基于视觉大模型，对输入的视频 URL 列表进行通用视频内容分析，输出视频级别的结构化理解结果，适用于内容审核、视频检索、标签生成等场景。 | Cloud | `mediakit-cli video video-understand-router` | [reference/video-understand-router.md](reference/video-understand-router.md) |
