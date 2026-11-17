# vc +meeting-list-active

列出当前进行中的会议，用来发现 `+meeting-events` 需要的长数字 `meeting_id`。

本 skill 对应 shortcut：`lark-cli vc +meeting-list-active`（调用 `GET /open-apis/vc/v1/bots/user_active_meeting`）。

## 命令

```bash
# 查询当前登录用户正在参加的会议
lark-cli vc +meeting-list-active --format json
```

## 返回范围

只返回当前登录用户正在参加的会议；返回空不代表当前用户没有在开会，只能说明没有找到该接口可发现的进行中会议。

## 多会议选择

- 如果返回多个会议，不要自动挑第一个。
- 向用户展示每个候选的 `meeting_title` / `meeting_no` / `meeting_id`，等待用户选择。
- 选择后执行 `+meeting-events` 读取事件。

## 9 位会议号匹配

用户提供 9 位会议号时，把会议号当作 active meeting 的筛选条件，而不是写操作指令。

匹配规则：

- 在返回会议中匹配 `meeting_no == <9位会议号>`。
- 匹配到唯一会议：取该项的长数字 `meeting_id`，后续调用 `+meeting-events`。
- 匹配到多个会议：展示候选，让用户选择。
- 没有匹配：说明当前登录用户没有发现该会议号对应的 active meeting。

## 常见错误与排查

| 错误现象 | 根本原因 | 解决方案 |
|---------|---------|---------|
| 返回空列表 | 当前登录用户没有可见的进行中会议 | 确认用户是否在会中，或是否切错 profile |
| 无权限 / 不可见 | 当前登录用户没有可见的进行中会议，或凭证异常 | 确认用户是否在会中、是否切错 profile；若凭证缺失由 agent 平台补齐用户凭证后重试 |

## 相关场景
- [会中事件与会中互动](../scenes/live-meeting-interact.md)
