---
name: video-creator
display_name: 视频模型指南
display_name_en: Video Model Guide
description: "本技能应在用户需要生成、编辑或延长视频，尚未指定模型、需要视频模型选型，或需要统一执行视频任务时使用。用户明确指定 Seedance、Happyhorse、H3 等模型时，可加载对应专属技能补充提示词知识，但工具调用仍由本技能负责。"
description_zh: "通过 AI-HIVE 的 100+ 模型能力完成视频选型、素材上传、参数确认、生成与任务跟踪。"
description_en: "Routes video tasks across AI-HIVE's 100+ model capabilities and executes the selected video workflow."
category: media
version: 1.1.1
author: 极睿科技（Infimind）/ AI-HIVE 团队
permissions:
  provisional: true
  read:
    - 仅限当前对话中用户主动选择的本地图片、视频与音频
  network:
    - 仅通过已启用的 AI-HIVE Connector 调用 get_user_info、list_models、upload_media_from_path、generate_video 与 get_generation_task
triggers:
  - "生成视频"
  - "编辑视频"
  - "延长视频"
  - "图生视频"
  - "参考生视频"
  - "视频模型选型"
---

# 视频模型指南

## 职责边界

本技能负责视频任务的通用执行。Seedance 2.5 等模型专属技能负责编译该模型的 Prompt 和模型知识，不得复制工具协议。

用户只要咨询、脚本、分镜或 Prompt 时不调用付费工具。Connector 未连接、素材未授权、参数未确认或实时目录无可用模型时停止执行。

## 任务与媒体映射

| 任务 | 媒体字段 |
|---|---|
| 文生视频 | 三类媒体数组均为空。 |
| 图像参考 | 图片放入 `imageMediaIds`。 |
| 视频参考、编辑或延长 | 视频放入 `videoMediaIds`。 |
| 音色、旁白、音乐或音效参考 | 音频放入 `audioMediaIds`。 |
| 首帧或首尾帧 | 使用 `firstFrameMediaId`、`lastFrameMediaId`。 |

同一媒体只进入与其真实类型一致的字段。具体组合必须同时满足所选模型的实时 `videoConfig`。

音频执行必须满足以下门禁：

- 只上传 MP3 或 WAV；单文件不得超过 15 MiB，并确认上传结果为 `mediaType=AUDIO`。
- 计划使用音频时，先确认运行时 `generate_video` schema 包含 `audioMediaIds`；字段缺失时停止音频执行，并提示用户升级或更新 Connector。
- Seedance 2.0 参考音频不能作为唯一参考输入；至少搭配所选模型支持的一份图片或视频参考，否则停止并请用户补充素材或改为无音频方案。
- Connector 上传限制与实时模型的数量、时长、大小或组合限制不一致时，取更严格的限制。
- 音频只作为视频生成参考，不用于 `chat_text`、聊天音频、语音转写、TTS 或音频生成。

## 工作流

1. 明确生成、编辑或延长目标，以及主体、场景、动作、声音、时长、画幅和素材职责。
2. 需要执行时调用 `get_user_info`，再调用 `list_models` 并设置 `modelType=VIDEO`。
3. 只从实时结果选择模型、路由、价格快照和支持参数。
4. 经用户授权上传素材，按真实媒体类型保存 `mediaId`；音频还要核对 `mediaType=AUDIO`。
5. Prompt 只描述可观察的视频内容；分辨率、时长、比例、音频和格式放入 `params`。
6. 展示模型、路由、主要参数、素材职责和价格摘要，取得用户确认。
7. 调用 `generate_video`，用真实 `taskId` 查询结果。

完整字段见 [工具契约](../references/tool-catalog.md)，素材准备见 [媒资准备](../references/material-prep.md)。

## 任务跟踪与付费安全

- `PENDING`、`SUBMITTED`、`PROCESSING` 只查询原任务。
- 图片类观察规则不适用于视频；视频最长观察 10 分钟，超出后报告仍在处理和 `taskId`。
- `COMPLETED` 时检查结果 URL 和工具返回元数据。
- `FAILED` 时展示 `failure.code`、`failure.summary`、`failure.suggestion`。
- 不存在取消能力时不得声称取消任务。
- 任何再次生成都是新付费任务，必须展示变化和价格并重新取得用户确认。

## 输出

- 执行前：模型、路由、Prompt 摘要、参数、素材职责、价格摘要。
- 完成后：`taskId`、结果 URL、返回元数据和复用建议。
- 处理中：真实状态、`taskId` 和继续查询方式。
- 失败：用户可见失败字段及可选修正方案。
