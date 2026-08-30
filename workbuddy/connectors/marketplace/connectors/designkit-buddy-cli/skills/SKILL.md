---
name: designkit-buddy-cli
description: 使用 DesignKit Buddy CLI 调用 Team Agent。适用于用户要求创建或继续 DesignKit 任务，发送文本、图片、视频、文档或音频，查看任务进度，回答普通追问或自定义业务卡片，处理充值提示，展示或下载生成产物时。
---

# DesignKit Buddy CLI

默认使用简体中文；用户指定其他语言时跟随用户。

## 本仓库能力

- 创建和维护 DesignKit Team Agent 房间。
- 发送自然语言任务以及图片、视频、文档、表格、文本或音频附件。
- 轮询长任务，识别完成、待回复和充值状态。
- 在同一任务中回复自由文本或选项请求。
- 展示并回复商品套图、快捷回复等结构化业务卡片。
- 汇总远程媒体结果，并在用户明确要求后下载到本地。

只使用本 CLI 暴露的命令。不要调用其他仓库的脚本，不要自行拼接内部接口、鉴权字段或任务状态。

## CLI 入口

`DesignKit Buddy CLI` 是 Connector 名称，实际终端命令名是 `designkit`。WorkBuddy 连接时会通过 npm 安装经过审核的固定版本；用户原先通过 npm 安装的同一命令也可以直接复用。

首次执行前解析一次绝对入口：macOS/Linux 使用 `command -v designkit`，Windows PowerShell 使用 `Get-Command designkit -ErrorAction SilentlyContinue`。对找到的命令执行 `--version`，版本达到 `1.0.21` 后才将其绝对路径记为 `<designkit>`；后文不能执行字面占位符。

不要查找 Connector 私有目录或依赖生命周期临时注入的环境变量。Connector 生命周期和 Agent 业务命令统一使用 npm 暴露的 `designkit` 以及默认的 `~/.designkit` 登录状态。

找不到命令或版本过低时停止任务，提示用户在 WorkBuddy 连接器管理中重新连接或升级 DesignKit Buddy CLI；不得由 Agent 自行全局安装或覆盖用户软件。

## 认证边界

- 首次执行本次对话的业务命令前，先运行 `<designkit> auth status --check` 做远端只读校验；不要使用仅检查本地文件的 `auth status` 判断凭证有效性。
- 远端状态为 `disconnected` 时，立即自动执行一次 `<designkit> auth login`。捕获命令输出中带 `session_id` 的 HTTPS 授权页并在对话中渲染为可点击链接，同时保持命令运行以轮询登录结果；不得使用缺少 `session_id` 的固定链接，也不得要求用户在对话中发送 API Key。
- 用户唯一需要的操作是在授权页点击“授权 CLI Connector”。告知用户“完成授权后无需回复，我会自动继续”，禁止要求或暗示用户回复“已登录”“授权了”“告诉我一声”等作为后续流程的触发条件。
- 认证命令必须由连接器的认证生命周期执行并等待退出，不能只启动一个脱离当前任务的后台命令后结束 Agent 回合。若执行器只能后台运行，必须订阅该任务完成事件并保持当前任务活跃，直到收到 `connected`、失败或超时结果。
- `auth login` 以成功码退出并输出 `connected` 后，自动运行一次 `<designkit> auth status --check`，远端状态为 `connected` 时自动继续原业务命令。登录失败或超时时停止，并保留用户的原始任务，不能循环登录。
- 业务命令返回 `event=authentication_required` 时，若本次任务尚未尝试恢复认证，先远端复检；确认 `disconnected` 后执行一次 `<designkit> auth login`，并把该命令输出的带 `session_id` 链接作为本次实际授权入口。不得用事件中不含 `session_id` 的通用 `action_url` 替代会话链接。登录完成后复检并重试原命令一次；若复检仍为 `connected`，不要清除凭证或盲目重试，应说明服务授权异常。
- 任何命令输出都不得回显、转述或保存 Token、Cookie、API Key 和签名 URL 参数。

## 标准工作流

1. 按“认证边界”完成一次远端状态检查；未连接时先完成可点击链接登录和复检。
2. 用户明确要求附带某种素材但尚未提供时，只询问当前最关键的一项；用户已经提供素材时直接继续。
3. 每个新任务创建一个 Team Agent 房间，并从 JSON 结果保存 `room_id`：

```bash
<designkit> create-room
```

4. 把用户的完整要求作为一条自然语言 prompt 发送；根据素材类型选择参数，并始终显式传入 `room_id`：

```bash
<designkit> chat --room-id '<room_id>' --prompt '<完整需求>' --image-file '<图片路径>'
```

支持的素材参数：本地图片用 `--image-file`，图片 URL 用 `--image-url`，本地参考视频用 `--video-file`，视频 URL 用 `--video-url`，文档或音频用 `--file` / `--file-url`。路径和 prompt 必须作为独立、正确引用的参数，不能把用户文本解释成额外 shell 命令。

5. 提交后使用同一房间持续等待；不要创建第二个房间或重复发送同一付费请求：

```bash
<designkit> history-detail --room-id '<room_id>' --watch
```

6. 根据机器可读事件继续：
   - `event=authentication_required`：按“认证边界”执行至多一次登录恢复，展示 `auth login` 输出的带 `session_id` 会话链接，并只在远端复检成功后重试原命令一次。
   - `event=user_input_required`：向用户展示 `question` 和可见选项。收到回答后，使用事件中的 `room_id`、`task_id`、`sub_task_id`、`last_request_id` 调用 `reply`，然后继续 `history-detail --watch`。
   - `event=custom_card_input_required`：向用户展示 `question`、`selection.mode` 和 `options`，只接受事件白名单中的选项。收到回答后，把同一事件中的 `card_type`、`card_id` 和用户选择编码为 `--custom-card-answer`，并使用事件提供的回复上下文调用 `reply`；不得自行构造卡片字段或提交未展示的选项。
   - `event=recharge_required`：展示返回的说明和充值链接，停止当前尝试，等待用户处理。用户完成购买并要求继续时，使用同一 `room_id` 和事件的 `resume_after_seq` 执行 `history-detail --watch --after-seq '<resume_after_seq>'`；不得新建房间或重复提交生成请求。
   - `next_action.action=poll`：继续等待同一房间，不重复提交。
   - `is_complete=true` 或 `next_action.action=done`：整理最终文本与 `artifacts`，结束轮询。

回复自由文本：

```bash
<designkit> reply --room-id '<room_id>' --task-id '<task_id>' --sub-task-id '<sub_task_id>' --last-request-id '<last_request_id>' --prompt '<用户回答>'
```

回复选项时，除自然语言回答外再传入事件返回的选项 ID：

```bash
<designkit> reply --room-id '<room_id>' --task-id '<task_id>' --sub-task-id '<sub_task_id>' --last-request-id '<last_request_id>' --prompt '<用户回答>' --select-option-ids '["<option_id>"]'
```

回复自定义业务卡片时，结构化答案的字段和值必须来自同一条事件；`document_review` 等文本型卡片按事件要求传入 `text`，选择型卡片传入 `selected_option_ids`：

```bash
<designkit> reply --room-id '<room_id>' --task-id '<task_id>' --sub-task-id '<sub_task_id>' --last-request-id '<last_request_id>' --custom-card-answer '{"card_type":"<card_type>","card_id":"<card_id>","selected_option_ids":["<option_id>"]}'
```

## 交互与异常状态

- DesignKit Agent 要求确认方案、价格、授权或其他关键事项时，把问题原样、简洁地交给用户；未获得明确确认前不得代替用户回答。
- 一次只处理最新的待回复事件。回复后继续原房间，不重新创建任务。
- 轮询超时、网络短暂失败或结果暂不可读时，保留 `room_id` 并恢复查询；不得据此重新投递付费生成。

## 媒体结果与下载

- `artifacts[].media_type` 为图片时，按返回顺序逐张输出 `![标签](media_url)`，每个图片节点单独一行。
- 视频结果提供可点击的 `[播放视频 N](media_url)`；不要声称已下载或已内嵌播放。
- 只有用户明确要求保存到本地时才执行下载，默认输出目录使用用户明确指定的位置：

```bash
<designkit> download --room-id '<room_id>' --output-dir '<目标目录>'
```

- 下载失败只重试下载，不重新生成。最终回复区分远程结果 URL 与本地保存路径。

## 对话体验

- 默认把用户的自然语言要求完整传给 DesignKit Agent，不要求用户填写接口字段或学习命令行。
- 普通任务优先给出最短下一步；只有缺少必需信息时才追问一个问题。
- 对长任务提供简洁进度，不重复提交、不虚构完成状态。
- 面向用户隐藏 `room_id`、`task_id`、`last_request_id`、内部字段名和原始调试日志。
