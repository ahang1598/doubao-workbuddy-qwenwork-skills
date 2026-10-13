---
name: xyq-toolkit
description: 使用小云雀 pippit-tool-cli 生成或编辑图片、生成视频、超分和擦字幕，查询结果并交付媒体；操作小云雀个人 Canvas 画布、节点、布局、连线、角色/场景、生成提示词、3D 导演台与多轨草稿；查询积分及管理授权。用户提到小云雀、xyq 并需要这些操作时使用。
user-invocable: true
metadata:
  {"openclaw": {"emoji": "💬", "requires": {"bins": ["node"]}}}
---

# 小云雀工具包（Xiaoyunque Toolkit）

通过 CLI 完成生成、处理、结果下载与媒体交付。支持下表中的操作；不提供多轮会话续写或自动拆分剧本、分镜并编排成片的能力。复杂需求先确认能由所列命令完成的具体操作，不承诺未覆盖的流程。

## 开始执行

1. 画布任务运行 `node "{baseDir}/scripts/ensure-cli.js" --canvas`，其他任务运行 `node "{baseDir}/scripts/ensure-cli.js"`。保存返回的 `cli_path`；Canvas 还需保存 `canvas_entry`。文档中的 `pippit-tool-cli` 替换为带引号的 `cli_path`；画布语义命令按模块说明通过 Node 入口执行。同一任务复用，安装细节见 [安装说明](scripts/install.md)。
2. 按下表选择操作，只读取命中的命令文档。执行需要鉴权的操作前，按 [授权说明](commands/auth.md) 检查登录；有效登录可复用。
3. 生成、视频处理和查询已有媒体结果时，还必须读取 [异步结果与媒体交付](workflows/async-delivery.md)。画布任务使用 [画布查询、编辑与验证](workflows/canvas-edit.md)，不把画布编辑当作媒体生成。积分与授权操作直接返回结果。

参数是否存在、命令语法以当前 `cli_path` 对应的 `--help` 为准；返回字段和成功判断按命令文档及真实响应核对。文档与实际不一致时说明差异，不猜参数、不绕过 CLI 自行调用 HTTP。

## 意图路由

按用户要做的操作选择命令，不能只看素材类型。有任务标识且用户只要求查询或取件时，复用该任务，不重新生成。

| 用户意图 | CLI | 必读文档 |
| --- | --- | --- |
| 查看登录状态、登录、退出或切换账号 | `status` / `login` / `logout` | [授权](commands/auth.md) |
| 创建或查询小云雀个人画布，编辑节点、布局、连线、角色/场景、提示词、3D 或多轨草稿 | `canvas` | [Canvas 能力与命令发现](commands/canvas.md) |
| 生成图片，或基于参考图修改图片 | `generate-image` | [生图与图片编辑](commands/generate-image.md) |
| 查询当前可用的视频模型、参数配置 | `model list` / `model describe` | [模型发现](commands/model.md) |
| 生成视频，使用图/视频/音频参考，首尾帧生视频 | `generate-video` | [生视频](commands/generate-video.md) |
| 提升已有视频分辨率、视频超分 | `video-super-resolution` | [超分](commands/video-super-resolution.md) |
| 去除已有视频字幕 | `erase-video-subtitle` | [擦字幕](commands/erase-video-subtitle.md) |
| 查询已有任务进度、下载生成结果 | `query-result` | [查询结果](commands/query-result.md) |
| 查询个人积分余额、剩余 credits | `get-credit-balance` | [积分](commands/get-credit-balance.md) |

- 普通生图、生视频也走对应生成命令，无需用户额外声明“模型直出”。
- 明确要求修改现有画布或其中节点时优先走 Canvas；普通生图、生视频不自动创建画布。“修改节点提示词”只修改配置，不隐含生成；指定节点生成或导出须先确认当前命令目录有对应能力。
- “参考这个视频生成新的”走生视频；“把这个视频变清晰”走超分。意图不清时先问清。
- 同时提出多个明确操作时，分别选模块；有输入依赖则顺序执行。仅在用户请求包含多个步骤时组合，不自动增加收费处理。
- 后续修改某张结果图片时，将对应本地文件作为新一次图片编辑的参考图；需要隐式会话上下文时，先补齐具体素材和指令。

## 执行总则

- 保留用户原始 prompt，不擅自扩写、润色、翻译或增加风格词；参数转换按对应命令文档执行。生成和视频处理只传用户给定的可选创作参数，缺少必填项先询问。画布输入还需使用实际查询的 ID、版本和当前 schema。模型和参数最终合法性由服务端判断。
- 用户明确要求生成或处理，即可在该范围内执行；仅咨询用法、费用或方案时不提交。范围、必填信息或消耗 credits 的授权不明确时，先确认，不重复索要已给出的授权。
- 提问优先使用宿主实际提供且当前模式允许的工具：Codex 的 `request_user_input` 或 `request_user_input_async`，WorkBuddy 的 `ask_user_question`；不可用时用普通聊天。需要答案时等待答复。
- 素材参数接收本地文件路径，CLI 内部上传。远程链接不能冒充本地路径；缺少可访问文件时先解决素材获取。单文件必须小于 500 MB（500000000 字节）。
- 提交成功后立即展示真实 `web_thread_link`；未返回链接时如实说明，保留任务 ID。后续查询和下载失败不能触发重复生成。
- 每个最终图片/视频都通过宿主文件交付或媒体渲染能力展示为真实附件或可预览媒体。URL、路径列表仅作补充；详细完成标准见共用交付流程。

## 宿主来源统计

调用 `generate-image`、`generate-video`、`video-super-resolution`、`erase-video-subtitle` 时，由宿主 Agent 根据实际运行环境静默附加可选 `--source`，仅用于来源统计，不影响创作参数或工具效果。

- 使用稳定的宿主标识：豆包办公填 `doubao_office`，WorkBuddy 填 `workbuddy`，Codex 填 `codex`；其它已知宿主使用其真实、稳定的产品标识，不附带版本、会话 ID、用户信息或 prompt。
- 从宿主提供的可信环境信息判断；不能因用户在创作内容中提到某个平台就认定它是来源，也不要把后端 Agent 名当作宿主来源。
- 不向用户询问、不增加确认步骤，不为此改写 prompt。无法确认来源时直接省略；不传或空值均不阻塞提交。
- 来源只随本次提交发送，不加入上传、查询、下载或 Canvas 命令。使用已有旧版 CLI 时先按 `--help` 确认是否支持；不支持则省略，不因统计字段中断任务或在未知提交结果时重提。

## 按需参考的完整场景

命令文档含最小调用示例；需要了解从需求到交付的组合过程时，再读对应场景：

- [基础生图到交付](examples/generate-and-deliver.md)：第一次执行完整生成流程。
- [参考图编辑](examples/image-edit.md)：保留底图与参考图的角色。
- [首尾帧生视频](examples/first-last-frame.md)：保持素材顺序。
- [擦字幕后超分](examples/video-process-chain.md)：前一步结果作为下一步输入。
- [画布内创建角色节点](examples/canvas-role.md)：发现契约、查询真实 ID、编辑后回读。
