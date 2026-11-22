---
name: lark-meeting
version: 1.0.0
description: "飞书视频会议：查询会议记录与会议产物(纪要/逐字稿/妙记)、妙记搜索/上传/下载/编辑；基于 meeting_id、meeting_no、event_id、note_id、minute_token、vc-node-id 或妙记 URL 查询相关信息。预约会议、忙闲和会议室管理走 lark-calendar。实时发言、会议字幕及事件、会中互动、文档共享、录制控制和主持管理走 lark-meeting-realtime。"
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli vc --help;lark-cli minutes --help;lark-cli note --help"
---

# lark-meeting

会议正在进行中或当前处于会议侧边栏时，**必须先读取 [lark-meeting-realtime](../lark-meeting-realtime/SKILL.md)**，再按其行动指南执行。

本技能与 [lark-meeting-realtime](../lark-meeting-realtime/SKILL.md) **共同覆盖会议查询与会中操作**：本技能负责查询会议基础信息、会议记录、录音及录制产物，读取智能纪要、逐字稿及管理妙记；对方负责实时发言/聊天/共享内容问答、进行中会议状态查询、邀请参会人、会中文本/表情、会议聊天、倒计时、文档共享、录制控制、主持管理和个人笔记。涉及对方能力时，先读取对方 Skill，不因本技能未列出而判断功能不支持。

本产物所有命令自动以当前登录用户身份执行，无需传入身份参数，也没有身份选择或切换的需要。遇到未认证、token 或 scope 错误时，直接根据错误响应中的提示（如 `missing_scopes`、`console_url`）引导用户在应用后台补开权限后重试。

## 会中操作

交接时传递已有标识、用户目标和必要查询结果；已有唯一 `meeting_id` 时不重复发现会议。读取已生成的纪要或妙记仍由本技能处理。

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
## 场景手册

按任务目标选择一个主场景，只执行所需章节。已有 `chat_id` 且只需消息读写时直接使用 [lark-im](../lark-im/SKILL.md)；明确要日程绑定群时使用 [lark-calendar](../lark-calendar/SKILL.md)。

- [查询会议及其产物](scenes/query-meeting-and-artifacts.md)：按主题、时间、参会人或 `meeting_id` / `meeting_no` / `event_id` 定位历史会议；查询参会人、录像和会议关联的智能纪要或妙记；基于会议记录总结或复盘；查询会后群聊，或已有 `meeting_id`、未说明会议状态时只读查询当前绑定。
- [查询当前用户录音列表](references/lark-recording-list.md)：没有会议标识、需要列出自己的录音或按时间筛选录音时，使用 `recording +list`；通过录音关联的产物标识继续读取妙记或纪要。
- [查询妙记及其产物](scenes/query-minutes-and-artifacts.md)：已有妙记 URL / `minute_token`，或按标题、所有者、参与者搜索妙记；读取总结、待办、章节、关键词、逐字稿，下载原始音视频，或查询关联智能纪要。
- [生成和修改妙记、管理妙记权限](scenes/create-and-edit-minutes.md)：将本地音视频生成妙记、逐字稿、总结、待办或章节；修改妙记标题、总结、待办、关键词或说话人；申请妙记权限，或查看、分配妙记协作者权限。
- [查询智能纪要及关联产物](scenes/query-note-and-artifacts.md)：已有 `note_id`、智能纪要 Docx URL/token，或需要查询纪要正文、逐字稿、妙记和共享文档等关联产物。

## 命令参考

| 命令 | 用途 | 参考方式 |
|---|---|---|
| `vc +search` | 搜索历史会议 | [lark-vc-search](references/lark-vc-search.md) |
| `vc +detail` | 查询会议信息、可选 Chat 绑定及关联的 Note、Minutes 标识 | [lark-vc-detail](references/lark-vc-detail.md) |
| `vc meeting get` | 查询会议基础信息和参会人快照 | `lark-cli vc meeting get --help` |
| `recording +list` | 分页查询当前用户录音及关联产物 | [lark-recording-list](references/lark-recording-list.md) |
| `vc +recording` | 从会议定位录制及妙记 | [lark-vc-recording](references/lark-vc-recording.md) |
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

按“场景手册 → 命令参考”渐进加载：

1. 读取与目标匹配的一个主场景手册；主场景明确转交到下游场景时，只继续读取被引用的场景或章节，并按其中流程执行 CLI。
2. 仅当缺少具体参数、返回字段、特殊约束或异常处理方式时：有参考手册的命令读取对应文件；没有参考手册的命令运行表中列出的精确 `lark-cli ... --help`。场景或 reference 已给出精确命令时，不再调用 `--help`；仅在参数缺失、命令不识别或文档与运行结果冲突时调用。
