---
name: byted-mediakit-audio
version: 0.2.2
license: MIT
description: "面向音频文件或视频中的音轨，处理语音边界定位、音频媒资信息探测、音频转码与码流封装适配、人声与背景声分离等目标。若对象和目标族已明确属于音频内容理解、音频转码、音频格式治理或音轨分离，但具体做法不确定，可先加载本 Skill 探索。"
permissions:
- shell
metadata:
  requires:
    bins:
    - mediakit-cli
  cliHelp: mediakit-cli audio --help
  product: mediakit-cli-doubao/skills
  domain: audio
  capability_count: 4
---
# audio MediaKit Skill

## 最高优先级交付门禁

当工具结果或 `query-task` 终态结果返回 `agent_hint.type=mediakit_artifact_delivery` 时，按以下硬约束执行：

1. 中间产物：仅当该产物 URL 会被本工作流下一步工具直接作为输入时，继续执行，不展示、不确认；最终产物生成后再统一确认一次。
2. 最终产物：本轮必须且只能调用 `agent_hint.next_tool`（`interaction_ask`），参数原样使用 `agent_hint.arguments`，向用户确认“当前链接有效期为 24 小时，是否需要转存为 7 天有效期链接？”。用户作出选择前，禁止调用 `present_files` 或 RichMediaCard、禁止在回复正文给出任何产物 URL、禁止用纯文本提问代替 `interaction_ask`、禁止声明任务完成。
3. 用户选择 `keep_24h`：交付工具结果中的真实原始产物 URL。
4. 用户选择 `transfer_7d`：依次下载 MediaKit 临时产物为本地正式文件、调用 `FileBatchUpload` 上传，并对每个正式文件立即单独调用一次 `present_files`，不得囤积。
5. 必须实际交付最终产物后才能声明任务完成；交付失败时必须使用同一个正式文件重试，不得改用其它交付格式、不得声称成功，也不得无故退出。

## 使用规则

1. 先读取 `../byted-mediakit-shared/SKILL.md`，执行统一前置检查；该 Skill 缺失时停止并报告当前 Skill 包不完整。
2. 只从下表选择 `audio` 域工具；相似能力按各工具“能力描述”和参数边界区分。
3. 执行前按需读取对应 reference；参数与结果说明来自同一份已审核文案，完整机器合同以当前 CLI `--schema` 为准。
4. 缺少必填参数、鉴权环境变量或真实输入资源时，向用户索取；通用可选字段只能透传用户明确提供的值，其他可选字段可由明确意图准确确定，但不得伪造。
5. 工具执行完成后，若结果返回 `agent_hint.type=mediakit_artifact_delivery`，必须遵守该提示和 shared Skill 的最高优先级交付门禁。

## 音视频元数据前置探测

当目标工具的限制或参数选择依赖音频时长、文件大小、封装、编码、码率、采样率或声道，而用户没有提供可信元信息时，先使用 `probe-audio-metadata`。如果输入实际是视频且需要判断视频流或画面属性，同时使用 video 域的 `probe-video-metadata`。将探测结果与目标工具 reference 的限制逐项比较；确认超限或不兼容时停止并要求更换或调整输入，不得盲目调用。探测结果不能替代目标工具的专属约束，也不保证后端一定处理成功。

## 澄清与跨域路由

若只说有音频而未说明业务目标，应先澄清。音频裁剪、拼接、调速、淡入淡出、混音、从视频抽取音轨或音视频合流等编辑合成诉求应路由到 editing；字幕生成、视频理解、视频增强等应路由到 video。

## 工具列表

| 工具 | 说明 | 支持模式 | 命令 | 参考 |
| --- | --- | --- | --- | --- |
| detect-voice-activity | 识别音频或视频中的有效人声片段，定位每段人声的起止时间并返回时间戳列表，可用于为后续语音识别、分析、剪辑或训练筛选更干净的音频输入。 | Cloud | `mediakit-cli audio detect-voice-activity` | [reference/detect-voice-activity.md](reference/detect-voice-activity.md) |
| probe-audio-metadata | 探测输入音频 URL，输出标准化媒资元信息，用于获取音频元信息。 | Cloud | `mediakit-cli audio probe-audio-metadata` | [reference/probe-audio-metadata.md](reference/probe-audio-metadata.md) |
| separate-voice | 从音频或视频中分离人声与其他声音：通用或音乐场景输出人声和背景音两轨，短剧或口播场景可进一步输出人声、音乐和音效三轨，便于剪辑、二次创作、人声优化、语音识别或声音复刻。 | Cloud | `mediakit-cli audio separate-voice` | [reference/separate-voice.md](reference/separate-voice.md) |
| transcode-audio | 将音频转换为另一种封装与编码配置，并可调整采样率、码率、声道和响度，以及保留、新增或覆盖元信息，用于适配播放终端、网络传输和媒资库响度标准化。 | Cloud | `mediakit-cli audio transcode-audio` | [reference/transcode-audio.md](reference/transcode-audio.md) |
