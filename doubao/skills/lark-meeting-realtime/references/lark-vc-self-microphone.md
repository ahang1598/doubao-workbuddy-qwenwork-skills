# vc +meeting-self-mute / +meeting-self-unmute

操作当前登录用户本人在进行中会议里的麦克风，并说明对应的麦克风状态事件。只操作自己；操作其他参会人使用 [vc +meeting-participant-mute / +meeting-participant-unmute](lark-vc-meeting-participant-audio.md)。

## 命令

```bash
# 先预览，不调用会议 API
lark-cli vc +meeting-self-mute --meeting-id <meeting_id> --dry-run
lark-cli vc +meeting-self-unmute --meeting-id <meeting_id> --dry-run

# 用户已经明确会议和动作后执行
lark-cli vc +meeting-self-mute --meeting-id <meeting_id>
lark-cli vc +meeting-self-unmute --meeting-id <meeting_id>
```

## 参数与权限

| 参数 | 必填 | 说明 |
|---|---|---|
| `--meeting-id <id>` | 是 | 会议开始后产生的长正整数会议 ID，不是 9 位会议号 |

- 要求 `vc:meeting.interaction:write` scope。命令风险级别为 `write`；真实执行前需用户明确会议和动作。
- 不需要也不接收 `device_id`。普通用户会对其所有在会设备逐一执行。

## OpenAPI 契约

两个命令都调用 `POST /open-apis/vc/v1/bots/set_self_microphone`，无 query，body 只包含 `meeting_id` 和布尔值 `is_muted`：`+meeting-self-mute` 发送 `true`，`+meeting-self-unmute` 发送 `false`。先用 `--dry-run` 核对路径和 body。

## 输出与状态边界

结构化结果包含 `meeting_id`、`is_muted`（本次请求的目标状态）和服务端返回的 `result`：

| `result` | pretty 输出 | 含义 |
|---|---|---|
| `muted` | `Microphone muted.` | 已闭麦 |
| `unmuted` | `Microphone unmuted.` | 已开麦 |
| `request_submitted` | `Unmute request submitted; ...` | 主持人禁止自行开麦，已提交举手申请；麦克风仍是关闭状态，需等待主持人处理 |

- `request_submitted` 不表示已开麦，不要据此报告开麦成功。
- 输出中的 `is_muted` 是请求的目标值，不是实时状态。主持人同意申请也不保证已开麦，应结合后续事件中的 `is_muted` 判断。
- 普通用户有多个在会设备时，某个设备操作失败会让命令整体失败，但之前已处理的设备不会回滚；失败后按需重新查询状态，不要自动循环重试。
- API 失败保持为 CLI 结构化错误，保留错误码和 `log_id`；超时表示结果未知。

## 麦克风状态事件

若已获得 `vc.meeting.microphone_state_changed_v1` 事件，载荷包含 `meeting`、`participant`、`is_muted` 和 `request_status`：

- `is_muted` 是会控的实际麦克风状态。
- `request_status` 为 `none`、`pending`、`approved`、`rejected` 或 `not_required`，和 `is_muted` 分开解释；`approved` 不等于已开麦。
- 实际推送的事件头使用 `create_time` 表示事件时间，精确到毫秒；可参考它判断同一会议、同一参会人的事件先后，但不能保证严格顺序。
- 载荷不含单调版本号，事件可能乱序或重复到达；命令结果只反映当次处理，不能保证代表当前状态。需要准确状态时，应查询会议中的当前状态。
