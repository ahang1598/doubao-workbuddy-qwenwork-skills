# vc +meeting-invite

通过会议邀请 API 邀请指定用户加入会议。

```bash
# 邀请指定用户
lark-cli vc +meeting-invite --meeting-id 7628568141510692381 --type SELECTED --open-ids ou_xxx,ou_yyy
```

## 参数

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `--meeting-id` | 是 | 长数字 Meeting ID，不是 9 位会议号。 |
| `--type` | 是 | 固定为 `SELECTED`。 |
| `--open-ids` | 是 | 用户 `open_id`（`ou_xxx`），支持逗号分隔或重复传入，最多 200 个。 |

本 skill 对应 shortcut：`lark-cli vc +meeting-invite`（调用 `POST /open-apis/vc/v1/bots/invite`）。本产物所有命令自动以当前登录用户身份执行。

- `SELECTED` 显式发送用户 `open_id`；本地会在请求前拒绝超过 200 个 ID 的输入。
- 请求契约：发送 `invite_type=2`、`invitees=[{"id":"ou_xxx","user_type":1}]` 和查询参数 `user_id_type=open_id`。
- 返回契约：可返回显式受邀人的 `invite_results`；CLI 会按响应 `id` 展示每项 `invited` 或 `failed` 状态。

## 权限与前置条件

- 调用方必须已在目标会议中。
- 仅包含一名受邀人的 `SELECTED` 复用普通单点邀请策略，普通会中参会人也可能有权邀请该用户。
- 多用户 `SELECTED` 使用批量邀请策略，调用者应为当前 host 或 co-host。
