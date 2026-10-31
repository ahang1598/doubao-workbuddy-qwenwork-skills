# 表单展示、提交与运行配置

## 职责与阅读依赖
维护表单展示、提交限制、通知、结果页、跳转和抽奖配置。配置目标、授权与验收按 [Form Scene](../scenes/form.md#展示与运行目标)，复用已确定的目标。

### 提交、通知、提交后动作与抽奖的共同前置
从对应 Get 取得现值、版本号和只读信息；已有且仍有效的结果可复用。按对应章节传更新参数并保留未改内容。

## 填写页展示（+form-display-settings-get / +form-display-settings-update）
用 `+form-display-settings-get` 读取分页方式；用 `+form-display-settings-update` 在所有题目同页连续排列与一页一题间切换。

### 展示范围与前置条件
本组命令只管分页。当前 CLI 不支持主题色和背景；标题和描述用 `+form-update`；题目用 `+form-questions-*`，见[题目创建与属性协议](form-questions.md)。

### 展示配置参数、取值与示例
| 参数 | 适用 | 必填 | 规则 |
|---|---|---|---|
| `--base-token` | 两条命令 | 是 | 表单所属 Base |
| `--table-id` | 两条命令 | 是 | 表单所属 Table |
| `--form-id` | 两条命令 | 是 | 表单 ID |
| `--display-mode` | update | 是 | `traditional`：所有题目同页；`one_question_per_page`：一页一题 |
| `--revision` | update | 否 | 当前版本整数；传入值必须与服务端一致，省略则跳过版本校验 |

```bash
lark-cli base +form-display-settings-get \
  --base-token "<base_token>" --table-id "<table_id>" --form-id "<form_id>"
lark-cli base +form-display-settings-update \
  --base-token "<base_token>" --table-id "<table_id>" --form-id "<form_id>" \
  --display-mode traditional --revision 12
```

不做版本校验时省略 `--revision`，只传 `--display-mode one_question_per_page`（或 `traditional`）。

### 展示配置请求、返回与回读
GET 与 PATCH 的 `data` 同形；带版本的请求也使用此结构：

```json
{"display_mode":"one_question_per_page","revision":13}
```

省略 `--revision` 时请求体完全不发该字段：

```json
{"display_mode":"traditional"}
```

`display_mode` 是字符串；不得在回复、日志或文档透出 SDK 内部数字枚举。写后独立 Get，读取已保存模式和新 `revision`。

### 展示配置错误与重试
| 情况 | 表现 | 处理 |
|---|---|---|
| `--revision` 与服务端不一致 | conflict | 重新 Get 最新 `revision`，确认无他人并发改动后用新值重试 |
| `--display-mode` 不在枚举内 | 本地拒绝 | 仅用 `traditional` / `one_question_per_page` |
| `--revision` 为负数 | 本地拒绝 | 省略参数以跳过版本校验 |

成功写入会推进 `revision`；旧值重试必然继续 conflict，重试前必须重新读取。

## 提交设置（+form-submission-settings-get / +form-submission-settings-update）
更新前执行共同前置。update 每次只能修改一个顶层组：

| 组 | 规则 |
|---|---|
| `submission_period` | 开启时同时提供开始时间、结束时间和 IANA 时区；更新其他字段时可原样带回已过去的已有开始时间，由服务端最终判断 |
| `user_submit_limit` | 次数 1～999；周期为 `total`、`day`、`week` 或 `month` |
| `total_submit_limit` | 总次数 1～100000 |
| `allow_modify_submission` | 允许或禁止修改已提交记录 |
| `ai_voice_input` | 允许或禁止语音输入 |

关闭限制时只传该组启停参数，不得携带已停用组的时间、次数或周期。

### 填写有效期与 Base 时区
`submission_period.timezone` 必须等于 Get 返回的 Base 时区，不得替换。空值表示 Base 未设时区：按 [Base 时区流程](../scenes/base.md#更新-base-时区)定目标，执行 `+base-update --time-zone <IANA 时区>`；重读后用相同时区开启有效期。
时间格式与参数见 [Base 时区协议](base-commands.md#更新-base-时区)。

## 通知配置（+form-notifications-get / +form-notifications-update）

更新前执行共同前置。一次只更新 `on-submission` 或 `scheduled`；启用时提供 1～100 个 `receiver-open-id`。定时通知还须提供未来的 RFC3339 时间、与 Base 相同的 IANA 时区，以及 `no_repeat`、`day`、`week`、`month`、`year`、`workday` 之一。

`revision` 控制并发；Get 返回时，Update 应带回当前非负值。

## 提交结果页与跳转（+form-submit-actions-get / +form-submit-actions-update）

更新前执行共同前置。一次只更新 `result-page` 或 `redirect`。启用结果页时标题必填且最多 12 个字符；启用跳转时只接受 HTTP 或 HTTPS URL。

`--description` 接受文本和 Markdown 链接，对应描述的 `text` / `url`；主动写入不得构造人员 `mention`。省略则保留当前描述（含已有 `mention`），传空字符串则清空；只改标题时不得重写描述。

`revision` 控制并发；Get 返回时，Update 应带回当前非负值。

## 抽奖配置（+form-lottery-get / +form-lottery-action）

更新前执行共同前置。`--agree-lottery-terms` 表示条款已获同意；按 [Scene 的抽奖授权](../scenes/form.md#填写有效期与抽奖)核对同意条件后传入。

- `enable`、`update` 必须提交完整 `--config-json`；`update` 还必须带 Get 返回的非负 `version`。
- `probability` 是 0～10000 的整数；`awards` 必须含 1～7 个奖品。
- 每个奖品必须有唯一 `position`，仅限 `0`、`1`、`2`、`3`、`5`、`6`、`7`；数组顺序不决定九宫格位置。
- `enable` 禁止携带 `award_id`。`update` 保留已有奖品时带回 Get 的 `award_id`，新增奖品时省略。
- `disable` 不接受 `--config-json`。
- `relink-winning-table` 可省略 `--config-json`；提供时不得含 `awards`。
- `icon_token`、`winning_table` 是只读信息，不得写回。
