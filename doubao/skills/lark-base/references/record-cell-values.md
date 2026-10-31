# 记录 CellValue 契约

## 适用范围与通用规则

适用：`lark-cli base +record-upsert`、`lark-cli base +record-batch-create`、`lark-cli base +record-batch-update`。

定义字段标识、可写边界和 `CellValue` 格式；命令外层 JSON 见[写入协议](record-write.md#命令选择与公共参数)。

- 同一 payload 的同一字段只用字段名或字段 ID，不得重复。
- 按实际 `type/style/multiple` 选格式，不得按字段名推断。
- 仅在字段允许时，清空优先传 `null`。

## 只读字段与附件边界

写记录不得写 `auto_number`、`lookup`、`formula`、`created_at`、`updated_at`、`created_by`、`updated_by`。写入不更新它们；返回可能含 `ignored_fields`，reason 为 `READONLY`。该提示只说明对应字段被忽略，不表示其他存储字段未写入。

附件不得作为普通 CellValue 写入；调用方式和签字样式限制见[附件专用协议](record-attachments.md)。

## 文本：text

按 `style.type` 检查并传值：

|`style.type`|值|
|---|---|
|`plain`|Markdown 格式字符串|
|`url`|带 title 的 Markdown 链接，或单独一个链接|
|`phone`|合法电话号码|
|`email`|合法邮箱字符串|

## 数值：number

传 JSON number，不得传带单位或千分位的字符串。货币、百分比、进度、评分等数字字段也传数字；展示格式由字段配置决定。

## 单选与多选：select

单选、多选优先传选项名数组：`multiple=false` 时至多一个选项，`multiple=true` 时可传多个。只传已有选项；不得自动新增或近似替换未知选项。报错所列选项可能不完整，不得视为完整值域。

## 日期时间：datetime

优先传 `YYYY-MM-DD HH:mm:ss` 字符串；不得传“明天上午”等相对时间。

## 复选框：checkbox

只传 JSON boolean `true` 或 `false`；不得传 `"true"`、`"是"`、`1`。

## 人员与群组：user / group_chat

单值、多值均传对象数组，元素至少含 `id`。人员传用户 ID（如 `ou_xxx`），群组传群 ID（如 `oc_xxx`）。

- 不得猜人员 ID；未知 `open_id` 时执行 `lark-cli contact +search-user --query "<姓名/邮箱/手机号>" --as user`。
- 不得猜群组 ID；未知 `chat_id` 时执行 `lark-cli im +chat-search --query "<群名关键词>" --as user`，取结果中的 `oc_xxx`。

### 当前用户身份与人员值

Scene 已确定使用当前用户时，执行 `lark-cli contact +get-user --as user`，不得传 `--user-id`；取 `.data.user.open_id`，构造 `[{"id":"<返回的 open_id>"}]`。单人、多人字段都用对象数组。

是否采用本人、是否允许复用身份由对应 Scene 决定；Mock 适用条件见[人员字段填值](../scenes/mock-data.md#人员字段填值)。

## 关联记录：link

传含 `id` 的对象数组；`id` 为目标记录的 `record_id`。不得传记录标题；先用 `+record-list` / `+record-search` 查目标记录 ID。

## 地理位置：location

- 写入：传 `{lng, lat}`；两者均为数字，`lng` 是经度，`lat` 是纬度。不得手动传 `full_address`；平台按坐标解析地址。
- 读取、筛选、转文本：使用 `full_address` 字符串；只有公式能访问坐标。
- 仅有地址文本：先获取或确认坐标再写入；不得把地址文本直接作为 location CellValue。

## 完整示例

```json
{"标题":"Hello, [lark-cli](https://github.com/larksuite/cli)","金额":3000,"完成度":0.65,"单选":["Todo"],"多选":["高优","外部依赖"],
 "日期":"2026-03-24 10:00:00","完成":false,"负责人":[{"id":"ou_123"}],"协作群":[{"id":"oc_123"}],"关联任务":[{"id":"rec_456"}],
 "坐标":{"lng":116.397428,"lat":39.90923}}
```
