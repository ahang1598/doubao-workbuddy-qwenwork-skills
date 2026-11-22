---
name: lark-meeting-realtime
version: 1.0.0
description: "基于会议或关联录音的实时发言、聊天和共享内容回答问题；查询进行中的飞书会议，邀请参会人，发送会中文本/表情，管理会议聊天、倒计时、文档共享、录制、本人麦克风、主持操作及个人笔记。"
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli vc --help"
---

# lark-meeting-realtime

本技能与 [lark-meeting](../lark-meeting/SKILL.md) **共同覆盖会议查询与会中操作**：本技能负责实时发言/聊天/共享内容问答、进行中会议状态查询、邀请参会人、会中文本/表情、会议聊天、倒计时、文档共享、录制控制、主持管理和个人笔记；对方负责查询会议基础信息、会议记录、录音及录制产物，读取智能纪要、逐字稿及管理妙记。涉及对方能力时，必须读取对方 Skill 并按其流程执行，不因本技能未列出而判断功能不支持。

交接时传递已有标识、用户目标和必要查询结果，不重复发现会议。预约会议、忙闲和会议室管理使用 [lark-calendar](../lark-calendar/SKILL.md)。

本产物所有命令自动以当前登录用户身份执行，无需传入身份参数，也没有身份选择或切换的需要。遇到未认证、token 或 scope 错误时，直接根据错误响应中的提示（如 `missing_scopes`、`console_url`）引导用户在应用后台补开权限后重试。

操作本人麦克风使用 `+meeting-self-mute` 或 `+meeting-self-unmute`，不要使用参会人管理命令；`request_submitted` 表示申请已提交，不表示已开麦。

## 标识与操作边界

- `meeting_id`：会议 ID。长数字字符串，不是 9 位会议号。
- `meeting_no`：9 位纯数字会议号；标识按字符串原样传递，不能与 `meeting_id` 相互替代。
- `chat_id`：会议当前绑定的 IM 聊天 ID，通常以 `oc_` 开头，可能是复用的私聊；绑定查询与创建/复用属于 VC，消息读写属于 IM。已有 `chat_id` 且只需消息读写时直接使用 [lark-im](../lark-im/SKILL.md)。
- 即时会议可以没有 Calendar `event_id`；明确要日程绑定群时使用 lark-calendar。
- `vc +meeting-end` 结束所有参会人的整场会议；只移出指定参会人时使用 `vc +meeting-participant-kickout`。
- 移出参会人的 `kickout_users[].id` 默认按 open_id 解释，可用 `--user-id-type union_id|user_id` 切换；`user_type` 必须来自目标会议的参会人快照，不得根据昵称或设备信息猜测。
- 闭麦与请求开麦按用户 ID 操作；CLI 不接受或展开 `device_id`。请求开麦的成功响应只确认请求已发送，目标参会人是否实际开麦是后续状态。
- 转移主持人、结束会议和移出参会人都必须先确认用户的明确目标；真实执行只有在确认后才传 `--yes`。预览按需使用 `--dry-run`。
- 会中事件不能替代已结束会议的参会人快照、纪要、逐字稿或录制；会后产物转交 lark-meeting。

共享文档时，评论面板优先按用户要求设置；未指定时，由 Agent 按当前任务需要决定是否展开。详见 [文档共享参考](references/lark-vc-meeting-share.md)。

## 快速行动

### 根据当前状态判断是否拉取会中事件并给出引导
当最新用户信息明确显示「AI 总结」未开启且没有「关联录音」时，**不要**查询会中事件，明确告知用户并按客户端类型引导：

判断「AI 总结」是否开启、是否存在「关联录音」时，**必须以用户最新消息为准，禁止通过对话上下文推断**。

- **电脑端**：按下面「电脑端标准话术」原样整段输出，不要修改：

> 目前无法获取会议信息，原因是当前会议的 AI 总结未开启，且没有关联录音，我无法获取到会议的发言和内容。
>
> 请选择以下任一方式解决：
> 1. **开启会议「AI 总结」** — 你在会议界面中找到 AI 总结功能并开启，开启后我可以读取会议内容并为你总结。
> 2. **开启「录音转写」** — 我可以帮你发起录音转写，记录本次会议内容。
>
> 需要我帮你发起录音转写吗？

得到用户的肯定回复或开启录音的意图时，使用 `doubao-record` 技能为用户开启录音。

- **手机端**：手机端不支持会议进行中同时开启录音，**不要**建议开启录音转写，只提示开启会议「AI 总结」。手机端标准话术，原样整段输出，不要修改：

> 目前无法获取会议信息，原因是当前会议的 AI 总结未开启，且没有关联录音，我无法获取到会议的发言和内容。
>
> 请在会议界面开启会议的「AI 总结」功能。

### 查询进行中的会议或关联录音的内容
`vc +meeting-events` 是**会中**的实时数据源：实时转写发言、共享文档、聊天、入离会等都在事件流里，内容随会议进行动态增长，每次查到的是当下最新快照。纪要(Note)、妙记(Minutes)则是会议**结束后**才生成的产物，会中尚未生成是常态——不要因为纪要/妙记还没生成而放弃获取会中发言内容。
**注意**：如果会议在进行中，或用户当前处于会议侧边栏，直接用 `lark-cli vc +meeting-events` 获取会中内容，不要使用其他方式；会议有关联录音时同样用该命令获取录音内容。

```bash
# 当前用户所在会议
lark-cli vc +meeting-list-active

# 确定唯一 meeting_id 后查询会中事件
lark-cli vc +meeting-events --meeting-id <meeting_id> --page-all --format pretty
```

已有 `meeting_id` 时直接查询事件，不重复发现会议。

- `--page-all` 参数必传，一次性获取所有事件，避免分页查询。
- `--page-all` 和 `--page-token` 可同时传
- `--page-token <returned_page_token>`
- 使用 `--page-token` 拉取增量，page-token 为上一页或上一次查询结果中保存的 page_token；建议持久化保存，便于下次继续拉取新增事件

同时有多场会议时，需要先选择要查询的会议；只有一场会议时，直接查询该场会议的会议事件。返回空不代表当前用户没有在开会，只能说明没有找到该接口可发现的进行中会议。

**事件时间**：`vc +meeting-events` 的 pretty 时间线中，`[hh:mm:ss]` 表示**距会议开始的相对时间**，如 `[00:01:32]` 表示会议开始后 1 分 32 秒；向用户引用时说明“会议开始后”或“距会议开始”。

当用户在会议中或处于会议侧边栏时，优先使用会中事件回答用户的问题。

### 判断用户是否要做会议笔记

仅当用户有明确表达记录意图（「写 / 划 / 记 / 标记 / 备忘 / 摘抄」等）时，才进入**会议笔记**场景（见场景手册「会议个人笔记」），创建并追加个人笔记文档。

- 意图不明确时先询问、要求用户给出明确指令，**不主动建文档**。
- 用户只说「总结一下」时走会议总结，不要误判为会议笔记。

## 会议场景约定

会议场景下常见的意图判定与动作约定。

消息开头的 `[会议](链接)` 是系统自动加的 skill 入口标签，锚文本（「会议」）不是用户输入的内容，不要把它和后面的文字拼起来当成一句话解析。

### 会中共享文档

会中可能有人共享文档（通过 `vc +meeting-events` 可读到共享的 Doc token）。当用户说「总结文档 / 整理文档 / 看下文档」等时：

- **有共享文档**：默认理解为「总结会中共享的文档」，读取该 Doc 内容并总结，**不要**新建文档。
- **没有共享文档**：意图不明确，可询问用户想总结哪个文档，或按常规文档生成流程处理。

### 文档评论

用户说「总结评论 / 看下评论 / 评论有哪些」等时，默认指**会中共享文档里的评论**（与「总结文档」同源）：

- **有共享文档**：读取该 Doc 的评论，关注未解决状态的评论。
- **没有共享文档**：意图不明确，询问用户想总结哪个文档的评论。

## 场景手册

按任务目标选择一个主场景，只执行所需章节。

- [会中事件、互动与主持管理](scenes/live-meeting-interact.md)：查询当前登录用户所在的活跃会议、查看发言/聊天/共享内容、按需读取当前会议画面；获取正在进行的会议绑定群、创建/复用会议聊天并按需转 IM，或发送文本/表情、查询或操作倒计时、控制文档共享；用户明确要求转移主持人、结束会议、移出参会人、闭麦或请求开麦时，也从这里路由到对应命令。
- [会议个人笔记](scenes/lark-meeting-personal-note.md)：仅当用户有明确表达记录意图（「写/划/记/标记/备忘/摘抄」等）时创建并追加个人笔记飞书文档；意图不明确时先询问、要求用户给出明确指令，不主动建文档；会议结束后基于完整会议内容自动整理完善。

## 命令参考

| 命令 | 用途 | 参考方式 |
|---|---|---|
| `vc meeting get` | 查询会议基础信息、当前聊天绑定和参会人快照 | `lark-cli vc meeting get --help` |
| `vc +meeting-recording-start` | 开始当前会议录制 | [lark-vc-recording-control](references/lark-vc-recording-control.md) |
| `vc +meeting-recording-stop` | 停止当前会议录制 | [lark-vc-recording-control](references/lark-vc-recording-control.md) |
| `vc +meeting-list-active` | 发现当前可见的进行中会议 | [lark-vc-meeting-list-active](references/lark-vc-meeting-list-active.md) |
| `vc +meeting-events` | 读取会中或关联录音事件和共享内容 | [lark-vc-meeting-events](references/lark-vc-meeting-events.md) |
| `vc +meeting-chat` | 会中创建或复用会议群聊（会议群/群组），仅需 `meeting_id` | [lark-vc-meeting-chat](references/lark-vc-meeting-chat.md) |
| `vc +meeting-message-send` | 发送会中文本消息或表情 | [lark-vc-meeting-message-send](references/lark-vc-meeting-message-send.md) |
| `vc +meeting-screenshot` | 获取视频会议截图 | [lark-vc-meeting-screenshot](references/lark-vc-meeting-screenshot.md) |
| `vc +meeting-countdown` | 查询、设置、延长、提前结束或关闭会中倒计时 | [lark-vc-meeting-countdown](references/lark-vc-meeting-countdown.md) |
| `vc +meeting-share` / `vc +meeting-share-status` | 控制会中文档共享并查询当前共享快照 | [lark-vc-meeting-share](references/lark-vc-meeting-share.md) |
| `vc +meeting-transfer-host` | 将会议主持人权限转移给指定参会人 | [lark-vc-meeting-transfer-host](references/lark-vc-meeting-transfer-host.md) |
| `vc +meeting-end` | 结束整场进行中的会议 | [lark-vc-meeting-end](references/lark-vc-meeting-end.md) |
| `vc +meeting-participant-kickout` | 移出一至十个指定参会人 | [lark-vc-meeting-participant-kickout](references/lark-vc-meeting-participant-kickout.md) |
| `vc +meeting-self-mute` / `vc +meeting-self-unmute` | 操作当前登录用户本人的麦克风 | [lark-vc-self-microphone](references/lark-vc-self-microphone.md) |
| `vc +meeting-participant-mute` | 将指定参会人闭麦 | [lark-vc-meeting-participant-audio](references/lark-vc-meeting-participant-audio.md) |
| `vc +meeting-participant-unmute` | 请求指定参会人开麦 | [lark-vc-meeting-participant-audio](references/lark-vc-meeting-participant-audio.md) |
| `vc +meeting-invite` | 邀请指定用户加入会议 | [lark-vc-meeting-invite](references/lark-vc-meeting-invite.md) |

## 渐进加载规则

按“快速行动 → 场景手册 → 命令参考”渐进加载：

1. 用户目标符合“快速行动”的进入条件时，直接执行对应 CLI；不要预读场景手册、命令参考、`--help` 或 schema。
2. 不符合快速行动条件，或缺少关键标识、需要消歧、涉及写操作时，读取与目标匹配的一个主场景手册；主场景明确转交到下游场景时，只继续读取被引用的场景或章节，并按其中流程执行 CLI。
3. 仅当缺少具体参数、返回字段、特殊约束或异常处理方式时：有参考手册的命令读取对应文件；没有参考手册的命令运行表中列出的精确 `lark-cli ... --help`。场景或 reference 已给出精确命令时，不再调用 `--help`；仅在参数缺失、命令不识别或文档与运行结果冲突时调用。
