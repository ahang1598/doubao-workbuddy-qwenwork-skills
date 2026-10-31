# 表单分享、二维码与查询入口

## 目录

- [职责与阅读依赖](#职责与阅读依赖)
- [分享设置](#分享设置form-share-get--form-share-update)
- [分享二维码](#分享二维码form-share-qrcode-get--form-share-qrcode-download)
- [提交后查询页](#提交后查询页form-query-page-get--form-query-page-create)

## 职责与阅读依赖

访问范围、开启分享和交付按 [Form Scene](../scenes/form.md#分享范围)，复用已定目标。

## 分享设置（+form-share-get / +form-share-update）

get 读取，update 修改。题目、显隐顺序、布局、二维码分别走 `+form-questions-*`、`+view-set-visible-fields`（见[可见题目与排序](form-questions.md#可见题目与排序)）、`+form-display-settings-*`、`+form-share-qrcode-*`。分享链接从 get 返回读取，不得拼 URL。

### 分享设置参数

| 参数 | 命令 | 规则/值 |
|---|---|---|
| `--base-token` | 两条 | 必填；Base；string |
| `--table-id` | 两条 | 必填；Table；string |
| `--form-id` | 两条 | 必填；表单 ID；string |
| `--enabled` | update | 后四项必须且只能传一项；总开关；bool |
| `--access-scope` | update | 同上；`invite` 仅受邀者 / `tenant` 组织成员 / `anyone` 持链接者 |
| `--allow-anonymous` | update | 同上；身份是否匿名；bool |
| `--require-login` | update | 同上；提交前是否登录；bool |

### 登录、匿名与系统创建人

`--allow-anonymous` 与 `--require-login` 独立，改一项不改另一项。只有登录且非匿名提交时，`created_by` 承接真实身份；免登录或匿名提交只记录“访客 12345”类访客身份，不能标识真人。身份收集与自填身份处理见 [Scene 的身份方案](../scenes/form.md#提交时间与填写人身份)。

### 分享布尔参数的等号写法

`--enabled`、`--allow-anonymous`、`--require-login` 必须用等号，如 `--enabled=true`、`--require-login=false`。空格形式在请求前报 `positional arguments are not supported (got ["true"]); pass values via flags`（括号显示所传值），不改设置；保留原值移到等号后，不得把 `false` 改成 `true`。非布尔 flag 可用空格或等号。

### 分享设置示例

update 一次只改一项；多项分多条，之间无需重读，最后 get 回读。

```bash
lark-cli base +form-share-get --base-token "<base_token>" --table-id "<table_id>" --form-id "<form_id>"
lark-cli base +form-share-update --base-token "<base_token>" --table-id "<table_id>" --form-id "<form_id>" --enabled=true
```

update 是 PATCH：只发送显式字段，其他字段不变。`enabled`、`access_scope` 在顶层，另两项在 `settings`；以下为独立 JSON，不得合并发送：

```jsonc
{"enabled":true}
{"access_scope":"anyone"}
{"settings":{"allow_anonymous":true}}
{"settings":{"require_login":false}}
```

get 回显分享状态、访问范围、settings 和分享链接。交付填写入口时，回读验收 `enabled=true`、`share_url` 非空、范围和 settings 符合目标；这只证明已保存，不证明真实提交已测。父级 `base --help` 未列命令时，用 `+form-share-get --help`、`+form-share-update --help` 核对，不得据父级帮助判定不存在。

### 分享设置错误与重试

| 情况/表现 | 动作 |
|---|---|
| 多项：`share update accepts exactly one field; do not combine --enabled, --access-scope` | 拆成多条依次执行 |
| 无项：`exactly one share field must be provided` | 补一个待改 flag |
| 布尔空格形式：`positional arguments are not supported (got ["true"])` | 保留原值，改用等号 |
| `--access-scope` 非枚举值；本地拒绝 | 只用 `invite` / `tenant` / `anyone` |

## 分享二维码（+form-share-qrcode-get / +form-share-qrcode-download）

两条命令发同一 GET，无请求体和 query 参数；get 原样返回，download 校验后落盘 PNG。

### 二维码前置：分享必须已开启

命令只读，不开启分享；未开启返回 `invalid_request`。先用 share-get 查状态；仅获 [Scene 分享决策](../scenes/form.md#分享范围)授权时用 share-update `--enabled=true` 开启。

### 二维码参数与路径限制

| 参数 | 命令 | 规则 |
|---|---|---|
| `--base-token` / `--table-id` / `--form-id` | 两条 | 均必填；Base / Table / 表单 ID |
| `--output` | download | 可选；文件或目录；省略则按返回的 `file_name` 写当前目录，目录则拼 `file_name` |
| `--overwrite` | download | 可选；默认 `false`；覆盖同名文件 |

`--output` 只能位于当前工作目录、`/tmp`、`~/files` 内。

### 二维码返回结构

get 的 `data`：

```json
{"share_url":"<validated-url>","file_name":"form-vewForm-qrcode.png","mime_type":"image/png","content_base64":"iVBORw0KGgo..."}
```

download 不返回 `content_base64`，只返回落点：

```json
{"saved_path":"/tmp/form-qrcode.png","file_name":"form-qrcode.png","mime_type":"image/png","size_bytes":4213,"share_url":"<validated-url>"}
```

### 二维码落盘前的三道校验

download 写任何字节前依次校验；任一失败即报错且不产生文件：

1. `mime_type` 必须为 `image/png`。
2. `content_base64` 必须能 Base64 解码。
3. 解码结果必须以 PNG 头 `\x89PNG\r\n\x1a\n` 开头。

### 二维码校验与落盘恢复

| 情况/表现 | 动作 |
|---|---|
| 未开分享：`invalid_request` | 按前置处理；本命令不自动开启 |
| 非法 PNG：`invalid_response`，未写文件 | 重试；连续失败则上报，不得手工拼 base64 落盘 |
| output 越出白名单，未写文件 | 改到当前目录、`/tmp` 或 `~/files` |
| `/tmp/qr` 等不存在目录被当作文件，生成无 `.png` 后缀文件 | 先建目录或以分隔符结尾（`/tmp/qr/`）；只有已存在的路径才识别为目录 |
| 同名：`output file <path> already exists`，未写文件 | 默认换 output；仅用户确认替换后加 overwrite。省略 output 时服务端名称重复必冲突，须显式换路径 |
| file provider 不支持独占提交：`cannot commit files exclusively`，未发请求 | 换路径无效；用户同意覆盖则加 overwrite，否则换环境 |
| 权限、磁盘满等本地写入失败，未写文件 | 换可写且空间足的 output 重跑；GET 重发无副作用 |

写盘失败不代表二维码、分享开关或接口权限异常；换 output 重跑 download，不得改用 get 取 base64 自行写盘。

## 提交后查询页（+form-query-page-get / +form-query-page-create）

查询页供提交者回查内容，由查询视图承载，ID 即 `query_view_id`；每表单最多关联一个。get 读取，create 新建或恢复关联。查询页不设置修改提交权限，修改权限用[提交设置](form-settings.md#提交设置form-submission-settings-get--form-submission-settings-update)的 `allow_modify_submission`。

### 查询页参数

| 参数 | 命令 | 规则 |
|---|---|---|
| `--base-token` / `--table-id` / `--form-id` | 两条 | 均必填；Base / Table / 表单 ID |
| `--query-view-id` | create | 可选；省略则发 `{}` 新建，传已有非空 ID 则恢复关联；空串被本地拒绝并提示省略，不发请求 |

### 查询页首次创建与关联恢复

首次尝试前先 get；仅 `configured=false` 且 `query_view_id=null` 时执行无 ID 的 create。`configured=true` 时沿用已有 ID，不重复创建。已尝试且失败时，按[部分成功与未知状态恢复](#查询页部分成功与未知状态恢复)处理：有恢复 ID 就原样带回，不得套用首次创建许可。

### 查询页返回结构

get 已关联/未关联及 create 的 `data`：

```jsonc
{"query_view_id":"vewQuery","configured":true}
{"query_view_id":null,"configured":false}
{"query_view_id":"vewQuery","configured":true,"reused":false}
```

`reused=false` 表示首次新建；`reused=true` 表示用传入 ID 恢复关联，未新建视图。

### 查询页部分成功与未知状态恢复

创建失败时，CLI 把恢复信息写入错误 `hint`：

```text
error.value={"completed_steps":["create"],"failed_step":"associate","query_view_id":"vewQuery"}
```

错误信封无 `data`：服务端 `data` 在错误分支丢弃，这些键从服务端 `data.error.value` 摘入 `hint`。解析 `error.value=` 后的 JSON。

| 字段/枚举 | 含义 |
|---|---|
| `query_view_id` | 已建视图 ID；重试时原样传给 `--query-view-id` |
| `completed_steps` | 已完成步骤列表 |
| `failed_step` | 失败步骤；顺序仅为 `create` 创建、`associate` 关联、`readback` 回读校验 |

| 判定 | 动作 |
|---|---|
| `failed_step=associate` 或 `readback` | 视图已建，必须带 ID 重试 |
| `failed_step=create` 且无 ID | 才能用空 POST 重建 |
| 有 ID、无 `failed_step` | 必须带 ID；恢复标识过长会退化为仅此键，按有无 ID 判定 |
| 超时/网络错误、无服务端错误体，hint 无 `error.value=` | 状态未知，不得空 POST；先 get，如实告知用户，由用户决定。即使 `configured=false` 也不能证明未建，不得自动新建 |

任何情况都不得先删再建。状态未知时仅 get 读现状，首次创建许可不适用。
