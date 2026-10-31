# Base 生命周期与设置命令

## 命令速查

`+base-get` 读取本体，`+base-create` 新建 Base 并配置初始表，`+base-copy` 复制整个 Base，`+base-update` 只更新时区。表、字段、视图另用各自命令。

## 读取 Base

执行 `+base-get --base-token "<base_token>"`；token 输入限制见 [Base 解析协议](base-resolve.md)。成功后从 `data.base` 读名称、owner、权限、token；下文返回字段均在 `data` 内。本体不含表、字段、记录和模块内容。链接用实际返回的 `url`，不拼接域名。

## 创建 Base 与初始表

初始字段先按 [Field 决策](../scenes/field.md#字段决策)选型，派生字段走 [Formula / Lookup](../scenes/field-formula-lookup.md#计算决策)。

```bash
lark-cli base +base-create --name "项目管理" --table-name "任务" --fields '[{"name":"任务名称","type":"text"},{"name":"状态","type":"select","options":[{"name":"待办"},{"name":"完成"}]}]' --as user
```

|参数|规则|
|---|---|
|`--name`|必填；Base 名|
|`--table-name`／`--fields`|分别指定初始表名和字段 JSON 数组；字段对象复用 [字段创建协议](field-commands.md#创建字段field-create)与[字段定义](field-config.md)；数组应非空，首项成为主字段|
|`--folder-token`|可选；云空间文件夹 token，非 Base 内 `--parent-id`|
|`--time-zone`|可选；创建时区|

同时传 `--table-name` 和 `--fields` 时，CLI 依次创建 Base、建指定 schema 的表、删平台默认表，不保证原子完成。成功返回 `base`、`created`、`table`、`fields`、`default_table_deleted`、`deleted_default_table_id`。

两者都省略时用默认 schema。只传 `--table-name` 时只重命名默认表，字段不变，返回 `table`、`default_table_renamed`、`renamed_default_table_id`。只传 `--fields` 时表名默认 `Table 1`。主字段删除限制见 [字段删除协议](field-commands.md#删除字段与主字段限制)，不能靠删除默认主字段无损改造 schema。

## 复制 Base

```bash
lark-cli base +base-copy --base-token "<源 Base token>" --name "<新 Base 名>" --as user
```

`--base-token` 指源 Base；返回 `base`、`copied`，后续用新 token。仅支持 Base，不接受 BaseApp／应用模式 token；公开模板的 token 来源与预览边界见 [模板协议](base-templates.md#复制参数与能力边界)。
默认含内容；仅结构传 `--without-content`。可选 `--name`、`--folder-token`（云空间文件夹）、`--time-zone`。
不得移植 `+table-copy` 的 `--range`／`--wait`；表复制及异步状态见 [Table 复制协议](table-commands.md#复制数据表)。

## 身份与返回

创建／复制从 `base.base_token` 取 token，兼容旧名 `app_token`；该字段名不代表 BaseApp，结合调用、资源类型判断；应用模式 token 不得作经典 Base token。VM 只用 `--as user`。
`permission_grant` 仅可能由上游 bot 创建／复制后尝试授权产生，非 user 必返；缺失不表示失败，不得为此换身份；出现时只述实值，不推断额外授权成功。
替换初始表后，`table` 是业务表，`deleted_default_table_id` 是已删默认表；后续用业务表真实 ID。

## 更新 Base 时区

### 命令与参数

```bash
lark-cli base +base-update --base-token "<base_token>" \
  --time-zone Asia/Shanghai --as user
```

`--base-token` 必填，是 Base Token，不是 Workspace Token；`--time-zone <iana-time-zone>` 必填，如 `Asia/Shanghai`；`--as user` 可选。

### 响应

|证据|含义／限制|
|---|---|
|更新响应|`base.revision`、`base.time_zone`、`updated: true` 表示服务端接受新版本、时区|
|写后 `+base-get`|返回 backend Base；有 `base.time_zone` 时独立核对；CLI 不补缺失，缺失不证明写失败|
|已有表单|以 `+form-submission-settings-get` 读取；字段位置与空值含义见 [提交设置协议](form-settings.md#提交设置form-submission-settings-get--form-submission-settings-update)|

缺失的读取字段不能用请求参数或写响应补填。

### 请求协议与限制

`PATCH /open-apis/base/v3/bases/:base_token`

```json
{"time_zone":"Asia/Shanghai"}
```

只提交 `time_zone`，其他设置由服务端保留。backend 按 IANA 时区校验，时区缩写不合法；允许与当前值相同。不要放表、字段或视图参数。`--dry-run` 只检查请求、不调用写接口，不能证明生效。

## 部分成功与未知结果

|故障|状态与恢复|
|---|---|
|`+base-create` 中途失败|前序 API 可能已成功，错误不保证含完整结果；凭真实 ID，以 `+base-get`、`+table-list`、`+field-list` 区分 Base、业务初始表、默认表现状|
|`+base-copy` 超时／丢响应|结果未知，非成功退出不证明副本不存在；有新 token 时以 `+base-get` 读取|
|时区更新丢响应|按“响应”一节读现值；允许同值不等于能从字段缺失判原请求失败|

目标识别、部分完成和重复对象见 [Scene 恢复](../scenes/base.md#创建结果未知与重复对象)；时区按 [Base 验收](../scenes/base.md#按操作核对证据)核对。
