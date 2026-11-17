# vc +meeting-countdown

设置、延长、提前结束或关闭会中倒计时窗口。

本 skill 对应 shortcut：`lark-cli vc +meeting-countdown`（调用 `POST /open-apis/vc/v1/bots/countdown`）。

## 适用场景

- 用户要求在正在进行中的会议里设置倒计时，例如“设置 5 分钟倒计时”。
- 用户要求延长当前倒计时，例如“再延长 2 分钟”。
- 用户要求提前结束或关闭当前倒计时。
- 只用于正在进行中的会议；已结束会议不支持。

## meeting_id 来源

`meeting_id` 必须来自 `+meeting-list-active` 发现的当前登录用户所在会议，或用户直接提供的长数字会议 ID；不要凭空构造。

## 参数

| 参数 | 说明 |
| --- | --- |
| `--meeting-id` | 必填，长数字 `meeting_id`，不是 9 位会议号 |
| `--action` | 必填，`set`、`prolong`、`end_in_advance` 或 `close_window` |
| `--duration` | 倒计时时长，单位是分钟；`set` 和 `prolong` 必填 |
| `--need-play-audio-at-end` | 仅 `set` 可用，表示倒计时结束时播放提示音 |
| `--reminder-before-end` | 仅 `set` 可用，提醒点单位是分钟；只支持传一个值 |

`duration` 和 `reminder_before_end` 都是分钟；提醒时间必须大于 0 且小于 `duration`。

## 设置倒计时

```bash
lark-cli vc +meeting-countdown \
  --meeting-id <meeting_id> \
  --action set \
  --duration 5 \
  --need-play-audio-at-end \
  --reminder-before-end 1
```

Dry-run 请求体示例：

```json
{
  "meeting_id": "<meeting_id>",
  "action": "set",
  "duration": 5,
  "need_play_audio_at_end": true,
  "reminder_before_end": 1
}
```

## 延长倒计时

```bash
lark-cli vc +meeting-countdown \
  --meeting-id <meeting_id> \
  --action prolong \
  --duration 2
```

## 提前结束或关闭倒计时

```bash
lark-cli vc +meeting-countdown --meeting-id <meeting_id> --action end_in_advance
lark-cli vc +meeting-countdown --meeting-id <meeting_id> --action close_window
```

提前结束或关闭倒计时窗口时不要传 `--duration`、`--need-play-audio-at-end` 或 `--reminder-before-end`。

## 9 位会议号处理

如果用户给的是 9 位会议号并要求操作倒计时：

1. 先执行 `+meeting-list-active`。
2. 在返回结果中按 `meeting_no` 匹配该 9 位会议号。
3. 匹配到唯一会议后取长数字 `meeting_id`，再执行 `+meeting-countdown`。

匹配失败时说明当前登录用户没有发现该会议号对应的进行中会议，不要凭空构造 `meeting_id`。

## 权限和前置条件

- 当前登录用户必须正在该会议中。
- 需要 `vc:meeting.interaction:write` 权限；权限不足时，直接根据错误响应中的提示（如 `missing_scopes`、`console_url`）引导用户在应用后台补开权限后重试。

## 相关

- [lark-vc-meeting-list-active](lark-vc-meeting-list-active.md) — 发现当前进行中会议 ID
- [lark-vc-meeting-events](lark-vc-meeting-events.md) — 读取会中事件
- [lark-vc-meeting-message-send](lark-vc-meeting-message-send.md) — 发送会中文本或 reaction
