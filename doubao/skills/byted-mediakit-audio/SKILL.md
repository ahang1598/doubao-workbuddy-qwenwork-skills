---
name: byted-mediakit-audio
version: 0.2.0
license: MIT
description: "面向音频文件或视频中的音轨，处理音频媒资信息探测以及人声与背景声分离等目标。若对象和目标族已明确属于音频媒资探测或音轨分离，但具体做法不确定，可先加载本 Skill 探索；若只说有音频而未说明业务目标，应先澄清。音频裁剪、拼接、调速、淡入淡出、混音、从视频提取音轨或音视频合流等编辑合成诉求应路由到 editing；字幕生成、提取字幕、语音转字幕、视频理解、视频增强等应路由到 video。"
permissions:
- shell
metadata:
  requires:
    bins:
    - mediakit-cli
  cliHelp: mediakit-cli audio --help
  product: mediakit-cli-doubao/skills
  domain: audio
  capability_count: 2
---
# audio MediaKit Skill

## 使用规则

1. 先读取 `../byted-mediakit-shared/SKILL.md`，执行统一前置检查；该 Skill 缺失时停止并报告当前 Skill 包不完整。
2. 只从下表选择 `audio` 域工具；相似能力按各工具“能力描述”和参数边界区分。
3. 执行前按需读取对应 reference；参数与结果说明来自同一份已审核文案，完整机器合同以当前 CLI `--schema` 为准。
4. 缺少必填参数、鉴权环境变量或真实输入资源时，向用户索取；通用可选字段只能透传用户明确提供的值，其他可选字段可由明确意图准确确定，但不得伪造。

## 工具列表

| 工具 | 说明 | 支持模式 | 命令 | 参考 |
| --- | --- | --- | --- | --- |
| probe-audio-metadata | 探测输入音频 URL，输出标准化媒资元信息，用于获取音频元信息。 | Cloud | `mediakit-cli audio probe-audio-metadata` | [reference/probe-audio-metadata.md](reference/probe-audio-metadata.md) |
| separate-voice | 用于人声背景声分离，可将音频或视频文件中的人声与背景音精准分离，输出为两个独立的音频文件。 | Cloud | `mediakit-cli audio separate-voice` | [reference/separate-voice.md](reference/separate-voice.md) |
