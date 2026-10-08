---
name: lark-meeting
version: 1.0.0
description: "飞书视频会议：查询会议记录与会议产物(纪要/逐字稿/妙记)、妙记搜索/上传/下载/编辑、会议录制控制；查询进行中的会议、实时会议内容(发言/聊天/共享文档)问答(会上/会里)、发送会中聊天/表情、查询或创建会议绑定聊天，以及主持人结束会议、移出参会人、闭麦或请求开麦；基于 meeting_id、meeting_no、event_id、note_id、minute_token、vc-node-id 或妙记 URL 查询相关信息。预约会议、忙闲和会议室管理走 lark-calendar。"
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli vc --help;lark-cli minutes --help;lark-cli note --help"
---

# lark-meeting

飞书视频会议业务的统一入口，支持查询会议记录、查询或创建会议群聊、实时会议互动、管理妙记、阅读智能纪要等操作。本技能负责领域关系、任务路由和跨命令编排。

本产物所有命令自动以当前登录用户身份执行，无需传入身份参数，也没有身份选择或切换的需要。遇到未认证、token 或 scope 错误时，直接根据错误响应中的提示（如 `missing_scopes`、`console_url`）引导用户在应用后台补开权限后重试。

## 领域模型与概念

```text
[会议来源]

Calendar 日程 (event_id) ──预约或关联──┐
即时会议（无 event_id）────────────────┴──► 会议 (meeting_id)

Calendar 日程 ──meeting_note────────────► Doc（用户纪要，独立于 AI 智能纪要）

[会议产物]

会议 (meeting_id)
├── 当前聊天绑定 ──► IM Chat (chat_id，可选，可能复用私聊)
├── AI 总结 ──► Note 智能纪要 (note_id)
│               ├── 智能纪要文档 ───────────► Doc (note_doc_token)
│               ├── 逐字稿
│               │   ├── normal  ──────────► Doc (verbatim_doc_token)
│               │   └── unified ──────────► note +transcript（非独立 Doc）
│               └── 共享文档 ──────────────► Doc (shared_doc_tokens)
│
└── 录制 ──► Minutes 妙记 (minute_token)
                 ├── AI 产物：Summary / Todo / Chapter / Keyword
                 ├── Transcript（文字记录，别名：「转写」「逐字稿」「文字记录」）
                 └── 原始音视频

本地音视频 ─────────────────────────────► Minutes 妙记 (minute_token)
```

| 对象 | 主标识 | 概念与关系 |
|---|---|---|
| Calendar 日程 | `event_id` | 日历上的日程，包含时间、参与人、会议室和 RSVP，可预约或关联 VC 会议；不是完整的会议记录。日程上的 `meeting_note` 是用户手工绑定的 Doc，与 AI 智能纪要无关。 |
| Meeting 会议 | `meeting_id` | 实际发生的视频会议，可以来自 Calendar，也可以是没有日程的即时会议。会议主题、时间、参会人快照和会中事件属于会议数据；Note 与 Minutes 是它可能关联的会后产物。 |
| IM Chat 会议聊天 | `chat_id` | 会议当前绑定的聊天，可能是群或复用的私聊；绑定查询与创建/复用属于 VC，消息读写属于 IM。 |
| Note 智能纪要 | `note_id` | 开启 AI 总结后形成的逻辑产物集合。`note_display_type` 决定获取逐字稿中文字记录的不同方式。 |
| Minutes 妙记 | `minute_token` | 由会议录制或本地音视频上传生成，包含总结、待办、章节、关键词、文字记录(别名：「转写」「逐字稿」「文字记录」)和原始音视频；可以关联 VC 会议，也可以独立存在。 |
| Doc 文档 | Doc token | 内容载体，不是会议标识。`note_doc_token`、`shared_doc_tokens` 和部分 `verbatim_doc_token` 指向 Doc；Doc token 不能当作 `note_id` 或 `meeting_id`。 |

### 核心标识

- `meeting_id`：会议 ID。长数字字符串，不是 9 位会议号。
- `meeting_no`：会议号。9 位纯数字；CLI 参数名为 `--meeting-number`。
- `chat_id`：IM 聊天 ID，通常以 `oc_` 开头；从会议详情或创建/复用结果取得，不能用 `meeting_id` 替代。
- `minute_token`：妙记 Token。小写字母数字串，通常取自妙记 URL `/minutes/<minute_token>`。

以上标识均按字符串原样传递，不能相互替代。

### 领域不变量

- Note 与 Minutes 分别来自 AI 总结和录制两条独立链路。一场会议可能同时有两类产物、只有其中一类，也可能都没有；不能根据 `note_id` 推断必然存在 `minute_token`，反之亦然。
- Minutes 可以由本地音视频直接生成，因此不一定关联 `meeting_id` 或 Calendar `event_id`。
- Calendar `meeting_note`、Note `note_id`、Minutes `minute_token` 和各类 Doc token 标识不同对象，不能互换、代入其他域的命令或从一者反推另一者。
- 结束会议和移出参会人都必须先确认用户的明确目标；预览使用 `--dry-run`，真实执行只有在确认后才传 `--yes`。

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

**注意**：如果会议在进行中且有关联录音，直接用 `lark-cli vc +meeting-events` 获取录音内容，不要使用其他方式。

```bash
# 当前用户所在会议
lark-cli vc +meeting-list-active

# 确定唯一 meeting_id 后查询会中事件
lark-cli vc +meeting-events --meeting-id <meeting_id> --page-all --format pretty
```
- `--page-all` 参数必传，一次性获取所有事件，避免分页查询。
- `--page-all` 和 `--page-token` 可同时传
- `--page-token <returned_page_token>`
- 使用 `--page-token` 拉取增量，page-token 为上一页或上一次查询结果中保存的 page_token；建议持久化保存，便于下次继续拉取新增事件

同时有多场会议时，需要先选择要查询的会议；只有一场会议时，直接查询该场会议的会议事件。返回空不代表当前用户没有在开会，只能说明没有找到该接口可发现的进行中会议。

当用户在会议中时，优先使用会中事件回答用户的问题。

## 场景手册

当任务目标与场景匹配时，阅读对应的场景手册，按流程执行任务。

- [查询会议及其产物](scenes/query-meeting-and-artifacts.md)：按主题、时间、参会人或 `meeting_id` / `meeting_no` / `event_id` 定位历史会议；查询参会人、录像和会议关联的智能纪要或妙记；基于会议记录总结或复盘；查询会后群聊，或已有 `meeting_id`、未说明会议状态时只读查询当前绑定。
- [查询妙记及其产物](scenes/query-minutes-and-artifacts.md)：已有妙记 URL / `minute_token`，或按标题、所有者、参与者搜索妙记；读取总结、待办、章节、关键词、逐字稿，下载原始音视频，或查询关联智能纪要。
- [生成和修改妙记、管理妙记权限](scenes/create-and-edit-minutes.md)：将本地音视频生成妙记、逐字稿、总结、待办或章节；修改妙记标题、总结、待办、关键词或说话人；申请妙记权限，或查看、分配妙记协作者权限。
- [查询智能纪要及关联产物](scenes/query-note-and-artifacts.md)：已有 `note_id`、智能纪要 Docx URL/token，或需要查询纪要正文、逐字稿、妙记和共享文档等关联产物。
- [会中事件与会中互动](scenes/live-meeting-interact.md)：查询当前登录用户所在的活跃会议、查看发言/聊天/共享内容、按需读取当前会议画面；获取正在进行的会议绑定群、创建/复用会议聊天并按需转 IM，或发送文本/表情、操作倒计时；用户明确要求结束会议、移出参会人、闭麦或请求开麦时，也从这里路由到对应命令。
- [会议个人笔记](scenes/lark-meeting-personal-note.md)：仅当用户有明确表达记录意图（「写/划/记/标记/备忘/摘抄」等）时创建并追加个人笔记飞书文档；意图不明确时先询问、要求用户给出明确指令，不主动建文档；会议结束后基于完整会议内容自动整理完善。

## 命令参考

| 命令 | 用途 | 参考方式 |
|---|---|---|
| `vc +search` | 搜索历史会议 | [lark-vc-search](references/lark-vc-search.md) |
| `vc +detail` | 查询会议信息、可选 Chat 绑定及关联的 Note、Minutes 标识 | [lark-vc-detail](references/lark-vc-detail.md) |
| `vc meeting get` | 查询会议基础信息和参会人快照 | `lark-cli vc meeting get --help` |
| `vc +recording` | 从会议定位录制及妙记 | [lark-vc-recording](references/lark-vc-recording.md) |
| `vc +meeting-recording-start` | 开始当前会议录制 | [lark-vc-recording-control](references/lark-vc-recording-control.md) |
| `vc +meeting-recording-stop` | 停止当前会议录制 | [lark-vc-recording-control](references/lark-vc-recording-control.md) |
| `vc +meeting-list-active` | 发现当前可见的进行中会议 | [lark-vc-meeting-list-active](references/lark-vc-meeting-list-active.md) |
| `vc +meeting-events` | 读取会中或关联录音事件和共享内容 | [lark-vc-meeting-events](references/lark-vc-meeting-events.md) |
| `vc +meeting-chat` | 会中创建或复用会议群聊（会议群/群组），仅需 `meeting_id` | [lark-vc-meeting-chat](references/lark-vc-meeting-chat.md) |
| `vc +meeting-message-send` | 发送会中文本消息或表情 | [lark-vc-meeting-message-send](references/lark-vc-meeting-message-send.md) |
| `vc +meeting-screenshot` | 获取视频会议截图 | [lark-vc-meeting-screenshot](references/lark-vc-meeting-screenshot.md) |
| `vc +meeting-countdown` | 设置、延长、提前结束或关闭会中倒计时 | [lark-vc-meeting-countdown](references/lark-vc-meeting-countdown.md) |
| `vc +meeting-end` | 结束整场进行中的会议 | [lark-vc-meeting-end](references/lark-vc-meeting-end.md) |
| `vc +meeting-participant-kickout` | 移出一至十个指定参会人 | [lark-vc-meeting-participant-kickout](references/lark-vc-meeting-participant-kickout.md) |
| `vc +meeting-participant-mute` | 将指定参会人闭麦 | [lark-vc-meeting-participant-audio](references/lark-vc-meeting-participant-audio.md) |
| `vc +meeting-participant-unmute` | 请求指定参会人开麦 | [lark-vc-meeting-participant-audio](references/lark-vc-meeting-participant-audio.md) |
| `vc +meeting-invite` | 邀请指定用户加入会议 | [lark-vc-meeting-invite](references/lark-vc-meeting-invite.md) |
| `minutes +search` | 搜索妙记 | [lark-minutes-search](references/lark-minutes-search.md) |
| `minutes minutes get` | 查询妙记基础信息 | `lark-cli minutes minutes get --help` |
| `minutes +detail` | 读取妙记信息和指定产物 | [lark-minutes-detail](references/lark-minutes-detail.md) |
| `minutes +download` | 下载妙记原始音视频 | [lark-minutes-download](references/lark-minutes-download.md) |
| `minutes +upload` | 从云空间音视频生成妙记 | [lark-minutes-upload](references/lark-minutes-upload.md) |
| `minutes +update` | 修改妙记标题 | [lark-minutes-update](references/lark-minutes-update.md) |
| `minutes +speaker-replace` | 替换妙记逐字稿说话人 | [lark-minutes-speaker-replace](references/lark-minutes-speaker-replace.md) |
| `minutes +summary` | 替换妙记 AI 总结 | [lark-minutes-summary](references/lark-minutes-summary.md) |
| `minutes +todo` | 增删改妙记 AI 待办 | [lark-minutes-todo](references/lark-minutes-todo.md) |
| `minutes +apply-permission` | 申请妙记查看或编辑权限 | [lark-minutes-apply-permission](references/lark-minutes-apply-permission.md) |
| `minutes +share-permission` | 将一条妙记一键分享给会议参会人 | [lark-minutes-share-permission](references/lark-minutes-share-permission.md) |
| `drive +member-list` | 查看妙记协作者及其权限 | [lark-drive-member-list](../lark-drive/references/lark-drive-member-list.md) |
| `drive +member-add` | 给指定成员分配妙记查看或编辑权限 | [lark-drive-member-add](../lark-drive/references/lark-drive-member-add.md) |
| `minutes +word-replace` | 批量替换妙记逐字稿关键词 | `lark-cli minutes +word-replace --help` |
| `note +detail` | 查询智能纪要及关联文档标识 | [lark-note-detail](references/lark-note-detail.md) |
| `note +transcript` | 获取 unified 智能纪要逐字稿 | [lark-note-transcript](references/lark-note-transcript.md) |

## 渐进加载规则

按“快速行动 → 场景手册 → 命令参考”渐进加载：

1. 用户目标符合“快速行动”的进入条件时，直接执行对应 CLI；不要预读场景手册、命令参考、`--help` 或 schema。
2. 不符合快速行动条件，或缺少关键标识、需要消歧、涉及写操作时，读取与目标匹配的一个主场景手册；主场景明确转交到下游场景时，只继续读取被引用的场景或章节，并按其中流程执行 CLI。
3. 仅当缺少具体参数、返回字段、特殊约束或异常处理方式时：有参考手册的命令读取对应文件；没有参考手册的命令运行表中列出的精确 `lark-cli ... --help`。场景或 reference 已给出精确命令时，不再调用 `--help`；仅在参数缺失、命令不识别或文档与运行结果冲突时调用。
