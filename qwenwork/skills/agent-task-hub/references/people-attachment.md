# 人员字段与附件上传参考（people-attachment）

> 两个最易踩坑的字段类型：`user`（创建人 / 任务交接对象）和 `attachment`（产出物 / 工作文件）。本文件只讲这两块。

## 一、人员字段（创建人 / 任务交接对象）怎么获得、怎么写入

### 写入格式（cells 里的 value）

```jsonc
{"<人员fieldId>": [{"userId": "<userId>", "corpId": "<corpId>"}]}
```

**硬规则**：即使字段是单选（`multiple:false`），也必须传**对象数组**（数组长度 1）。传字符串 `"姓名"` 或 `{"userId":"<userId>"}`（不带 corpId）都会错。

### 三步拿到 userId + corpId

```bash
# ① 拿当前企业的 corpId（组织级固定值，同一企业所有成员相同）
dws contact user get-self --format json
# → result[0].orgEmployeeModel.corpId  = "<corpId>"

# ② 按姓名/工号/职责查人，拿 userId
dws aisearch person --keyword "<姓名或工号或职责>" --format json
# → result[0].userId = "<userId>"（也可用 result[0].meta.staffId，二者一致）
# 按工号查：--keyword "<工号>" --dimension jobNumber
# 按职责查：--keyword "<职责>" --dimension duty

# ③ 组装写入
# {"<人员fieldId>": [{"userId": "<userId>", "corpId": "<corpId>"}]}
```

### 字段名不一致的坑（已实测确认）

- `aisearch person` 返回的是 `userId`（顶层）和 `meta.staffId`（同值），**没有 corpId**
- `contact user search` 只返回 `userId`，**没有 corpId**
- `contact user get` 返回 `orgEmployeeModel.orgUserId`，**没有 corpId**（orgId 为 null）
- 只有 `contact user get-self` 返回 `orgEmployeeModel.corpId`

所以 corpId 统一用 `get-self` 拿（企业级常量），userId 用 `aisearch person` 或 `contact user search` 拿。不要试图从 `contact user get` 里找 corpId，它没有。

> 若目标用户不在当前请求组织内，AI 表格会要求回退为 `[{"userRef": "ur_xxx"}]`，这是另一套引用格式，遇到时以 `aisearch person` 返回的 `userId` 为准，不要编 userRef。

## 二、附件字段（产出物 / 工作文件）上传

### 硬规则

**禁用钉盘 drive**：钉盘返回的 fileId 写不进 attachment 字段。必须走下面的 OSS 三步流程。

### 手动三步流程（不依赖脚本，最稳）

```bash
# ① 获取上传凭证（返回 uploadUrl + fileToken）
# --mime-type 必传：不传时服务端不识别 .md 等扩展名会直接报错（已实测）
dws aitable attachment upload --base-id <BASE_ID> --file-name report.pdf --size 204800 --mime-type application/pdf --format json
# 返回示例：{"uploadUrl":"https://oss...","fileToken":"ft_xxx","expiresAt":"..."}

# ② curl PUT 上传文件（Content-Type 必须与 ① 的 --mime-type 一致，不能留空，否则 OSS 403）
curl -X PUT "<uploadUrl>" -H "Content-Type: application/pdf" --data-binary @/path/to/report.pdf

# ③ 把 fileToken 写入 attachment 字段（record create 或 update）
dws aitable record update --base-id <BASE_ID> --table-id <TABLE_ID> \
  --records '[{"recordId":"<RECORD_ID>","cells":{"<产出物fieldId>":[{"fileToken":"ft_xxx"}]}}]' --format json
```

### MIME 对照（① `--mime-type` 与 ② Content-Type 同值，都必填）

| 扩展名 | MIME |
|---|---|
| .md / .txt | text/plain |
| .ts / .tsx | text/typescript |
| .js / .mjs | text/javascript |
| .py | text/x-python |
| .yml / .yaml | text/yaml |
| .csv | text/csv |
| .html | text/html |
| .png | image/png |
| .jpg | image/jpeg |
| .pdf | application/pdf |
| .json | application/json |
| .xlsx | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet |
| .docx | application/vnd.openxmlformats-officedocument.wordprocessingml.document |

表外扩展名按标准 MIME 推断；推不出就用 `application/octet-stream`（① ② 同值）。

### 已有脚本（可选，但默认不推荐）

`dws` 技能自带 `scripts/upload_attachment.py`，可 `python3 scripts/upload_attachment.py <BASE_ID> /path/to/file` 一键返回 fileToken。**但它内部会 subprocess 调 dws**，与本技能「dws 必须前台执行」的约束冲突，且在本运行环境可能只出 pending 标记。**优先用手动三步**，脚本仅作为兜底尝试。

### 多文件 / 覆盖语义

- attachment 字段一次写入是**整体覆盖**，不是追加。要多附件就在同一数组里放多个 `{"fileToken":"ft_1"},{"fileToken":"ft_2"}`。
- 文件大小 `--size` 是字节数，必须 >0；`--file-name` 必须含扩展名。
- `uploadUrl` 有时效性（`expiresAt`），拿到后要立即 curl PUT。

### 多文件批量策略（为什么批量，不是一个文件做完再做下一个）

固定顺序：**批量申请凭证 → 批量 curl PUT → 一次合并写入 → 一次回读**。不要改成逐文件串行（凭证→PUT→写→回读 循环），原因：

- 表格写入是慢操作（单次约 1.5s），回读也是一次往返。逐文件做 N 个文件要 N 次写 + N 次回读；批量只要 1+1。凭证申请和 PUT 不写表格、不是慢操作，N 次开销小。
- attachment 是整体覆盖语义：逐文件写第 2 个时必须把第 1 个的 fileToken 一起带上，否则前一个被覆盖丢失——批量一次写天然规避这个错。
- 凭证/PUT 失败是单文件粒度的：哪个文件 ① 或 ② 失败就只重试那个文件，不影响批量策略。
