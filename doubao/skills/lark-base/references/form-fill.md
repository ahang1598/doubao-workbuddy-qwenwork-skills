# 分享表单详情与提交协议

## 目录

- [职责与阅读依赖](#职责与阅读依赖) · [操作导航](#操作导航) · [填写前置与分享标识](#填写前置与分享标识)
- [读取表单详情](#读取表单详情form-detail) · [构造提交内容](#构造提交内容) · [提交表单](#提交表单form-submit)

## 职责与阅读依赖

维护通过分享链接读取详情、构造内容和提交表单的协议。提交授权、真实答案准备和验收范围按 [Form Scene](../scenes/form.md#填写与提交)，复用已确认目标。

## 操作导航

| 动作 | 入口 |
|---|---|
| 定位表单 | 从分享链接[提取 `share_token`](#提取分享标识share_token) |
| 读取题目、必填、显隐、附件所需 Base token | `+form-detail` |
| 构造普通值、附件、时区 | `fields`、`attachments`、`--timezone` |
| 提交或预览 | `+form-submit`、`--dry-run` |

## 填写前置与分享标识

### 提交边界、权限与限流

- 仅通过分享模式 `share_token` 填写普通字段、上传本地附件；不接受 `base_token + table_id + view_id` 管理定位。`form_id` 仅用于管理，不得用 Base、table 或 form ID 拼分享链接。
- `+form-submit` 是 `high-risk-write`：传 `--yes`；否则返回 `confirmation_required` 并以非零码退出。`--dry-run` 除外。该 CLI flag 不扩大 Scene 授权。
- 权限：`base:form:update`；有 `attachments` 时还需 `docs:document.media:upload`。限流：单应用 20 QPS、单用户 5 QPS。
- 提交依赖当前有效的 `+form-detail` 结果：核对类型、必填、显隐并取得附件所需 `base_token`；结果仍有效时不重复读取。

### 提取分享标识（share_token）

取分享 URL 路径最后一段作为 `--share-token`：

```text
https://www.example.com/share/base/form/shrbcvST8eZy0vk8zjVZ1CAXNye
```

上例 `share-token` 为 `shrbcvST8eZy0vk8zjVZ1CAXNye`。

## 读取表单详情（+form-detail）

只读读取题目结构、必填、显示条件及附件所需 Base token：

```bash
lark-cli base +form-detail --share-token "<share_token>" --format pretty
```

### 详情返回与读取重点

| 字段 | 动作/含义 |
|---|---|
| `base_token` | 有附件时传给 `+form-submit --base-token` |
| `questions[].id` | 题目标识，通常对应字段 ID |
| `questions[].title` | 按真实返回作为提交字段名/题目名 |
| `questions[].type` | 按[普通字段值](#普通字段值fields)构造 |
| `questions[].required` | 判断必填 |
| `questions[].filter` | 判断可见性；不提交隐藏题 |

类型动态配置包括 `select.options` / `select.multiple`、`number.style`、`datetime.style.format`、`user.multiple`；详情还可能含 `link.link_table`、`formula.expression`、`lookup.from/select/where/aggregate` 等元数据。

出现元数据不代表该类型可创建为题目或可手动提交，按下文写入边界处理。

### 填写时的显示条件（filter）

```json
{"conjunction":"and","conditions":[{"field_name":"状态","operator":"is","value":["已确认"]},{"field_name":"金额","operator":"isGreater","value":[1]}]}
```

- `conjunction`：`and` 表示全部满足，`or` 表示任一满足；`field_name` 引用其他题目的 `title`。
- `operator`：`is`、`isNot`、`contains`、`doesNotContain`、`isEmpty`、`isNotEmpty`、`isGreater`、`isGreaterEqual`、`isLess`、`isLessEqual`；`isEmpty` / `isNotEmpty` 不传 `value`。
- 附件题的 filter 仅适用 `isEmpty` / `isNotEmpty`。当前填写值不满足 filter 时视为隐藏，不放入 `--json.fields` 或 `--json.attachments`。

## 构造提交内容

`--json` 为对象，按需包含 `fields` 和 `attachments`。

### 普通字段值（fields）

- 仅提交当前分享表单真实存在、可见、可填写的题目。文本、数字、日期、人员、地理位置复用 [Record CellValue](record-cell-values.md)；Form 单选传字符串，多选传字符串数组。
- 创建/复用题目仅按[题目支持类型](form-questions.md#创建请求与支持类型)，不得从值示例反推创建能力。公式、Lookup、系统字段不手动填写。
- 自动编号、公式、创建/修改人、创建/修改时间由系统填入。
- 旧表单或其他入口创建的特殊题型，先按当前详情和服务端能力核实可填写性，再传对应 CellValue。本地 dry-run 或普通记录支持该类型，不证明表单提交支持。
- 不支持的关联收集走[输入与业务关联](../scenes/form.md#输入与业务关联)。

```json
{"文本字段":"内容","电话字段":"13800000000","网址文本题":"https://example.com","数字字段":12.5,
 "单选字段":"选项A","多选字段":["选项A","选项B"],"时间字段":"2026-04-27 14:30:00",
 "人员字段":[{"id":"ou_7094d131420c8749632145f08fbf114a"}],
 "地理位置字段":{"lng":116.397428,"lat":39.90923}}
```

附件不得放入 `fields`，也不得在其中传 `file_token` 或其他附件格式。

### 附件上传（attachments）

把附件字段放在顶层 `attachments`，值为本地文件路径数组（不是 token）：

```json
{"attachments":{"附件字段名":["./report.pdf","./photo.png"],"另一个附件字段":["./doc.docx"]}}
```

CLI 依次执行：校验全部文件存在、大小 ≤2GB 且为常规文件；以并发上限 5 上传到 Base Drive Media，并对跨字段重复路径去重；取得 `file_token` 后合并进最终提交。JSON 含 `attachments` 时必须传详情返回的 `--base-token`。

区别于 [Record 附件协议](record-attachments.md)：Record 用独立命令 `+record-upload-attachment`；`+form-submit` 只接收 `attachments` 中的本地路径并自动完成校验、上传、取 Token、合并写入。

### 相对日期与填写人时区（--timezone）

仅在日期题的 `input_range_limit.earliest/latest` 为相对日期 `dynamic`（今天 / 本周一 / 本月初等），且确切知道填写人时区时传 `--timezone`；用 `+form-detail` 或 `+form-questions-list` 判断。`fixed_ms` 为固定日期，不传。

传 IANA 时区名并保持规范大小写，如 `Asia/Shanghai`、`Asia/Tokyo`；CLI 本地校验，报错后按提示改为规范写法。Base 文档时区优先，存在时忽略传入值；未传且 Base 无文档时区时回落东八区。

## 提交表单（+form-submit）

提交前完成上述授权确认、当前详情读取和 JSON 构造。

### 提交参数与示例

| 参数 | 必填 | 含义 |
|---|---|---|
| `--share-token <token>` | 是 | 分享 URL 路径最后一段 |
| `--base-token <token>` | 有附件时 | 指定附件上传的目标 Base |
| `--json <json>` | 是 | 含 `fields` 和/或 `attachments` 的对象 |
| `--timezone <IANA>` | 否 | 仅用于上述相对日期边界 |
| `--yes` | 是 | 确认高风险写；`--dry-run` 时免传 |
| `--format` | 否 | `json`（默认）/ `pretty` / `table` / `ndjson` / `csv` |
| `--as` | 否 | 本环境仅支持 `user` |
| `--dry-run` | 否 | 预览 API 调用，不执行 |

普通值、附件及相对日期一次提交：

```bash
lark-cli base +form-submit \
  --share-token "<share_token>" --base-token "<base_token_from_form_detail>" \
  --timezone Asia/Shanghai \
  --json '{"fields":{"状态":"已确认","金额":5,"日期":"2026-09-16 12:00:00"},"attachments":{"附件":["./report.pdf"]}}' \
  --yes
```

预览不执行且无需 `--yes`：

```bash
lark-cli base +form-submit --share-token "<share_token>" --json '{"fields":{"状态":"已确认","金额":5}}' --dry-run
```

### 提交返回结构

成功结果仅表示平台接受本次提交。`can_submit_again`（bool）只表示当前身份能否再次填写，不作为记录回读证据；业务验收按 [Scene](../scenes/form.md#按操作回读与验收)。

```json
{"ok":true,"data":{"can_submit_again":true}}
```
