# calendar +rsvp

回复日程，更新当前用户的 RSVP 状态（接受、拒绝或待定）。只能回复当前用户受邀的日程。

| 日程类型 | `event_id` 形式 | 说明 |
|----------|-----------------|------|
| Normal（普通日程） | `{uid}_0` | 无重复规则（`recurrence` 为空） |
| Master（重复性日程本体） | `{uid}_0` | 有重复规则（`recurrence` 非空） |
| Instance（重复性日程实例） | `{uid}_{ts>0}` | 由主日程重复规则展开的某次发生点，`is_exception=false` |
| Exception（重复性日程例外） | `{uid}_{ts>0}` | 保存某次独立变更，仍属于原序列，`is_exception=true` |

`ts` 是该次在原序列中的时间戳（`originalTime`，Unix 秒）。

查询得到的 `event_id` 原样传入，命令负责日程类型判断、目标定位和范围校验；按返回的 hint 补充范围或实例 ID。

## 回复意图

- 范围不确定时，默认选择 `all` 并显式传 `--apply-to=all`，无需与用户确认；用户明确只回复某一次时使用 `single`。
- 日期用于定位日程，范围由回复意图决定：「明天 XX 这个重复会议全部接受」→ 定位明天实例，传 `--apply-to=all`；「仅明天这一次拒绝」→ `single`。
- 范围只有 `single` / `all`；「此次及后续」「从明天起全部回复」在 RSVP 中按 `all` 执行，反馈明确**已回复整个重复序列，包含过去实例和已有例外**。
- 同一重复序列命中多条时去重，整组只调用一次 `+rsvp --apply-to=all`，禁止逐条回复模拟整组。

## 命令

```bash
# 普通日程接受（使用当前用户主日历）
lark-cli calendar +rsvp --event-id evt_xxx_0 --rsvp-status accept

# 仅拒绝这一次
lark-cli calendar +rsvp --event-id evt_xxx_1776679200 --rsvp-status decline --apply-to single

# 整组待定
lark-cli calendar +rsvp --event-id evt_xxx_1776679200 --rsvp-status tentative --apply-to all

# 指定其他日历下的重复性日程，整组接受
lark-cli calendar +rsvp --calendar-id cal_xxx --event-id evt_xxx_0 --rsvp-status accept --apply-to all
```

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--event-id <id>` | **是** | 日程 ID，原样传入 `+agenda` / `+search-event` 查询结果 |
| `--rsvp-status <status>` | **是** | 回复状态：`accept`（接受）、`decline`（拒绝）、`tentative`（待定） |
| `--calendar-id <id>` | 否 | 日历 ID；省略或传 `primary` 时使用当前用户的主日历 |
| `--apply-to <scope>` | 条件必填 | 回复范围：`single`（仅此次）或 `all`（整个重复序列，含已有例外）；「此次及后续」也使用 `all`；普通日程可省略，默认 `single`；重复日程必须传入此参数 |

## 输出与反馈

成功结果保留输入 `event_id`，返回实际回复目标 `resolved_event_id`、有效范围 `apply_to`，以及 `calendar_id` 和 `rsvp_status`。根据返回结果直接反馈：`single` 是这一次，`all` 是整个重复序列（含已有例外及过去实例），不要声称只修改了未来。

## 参考

- [lark-calendar](../SKILL.md) -- skill 入口与路由
