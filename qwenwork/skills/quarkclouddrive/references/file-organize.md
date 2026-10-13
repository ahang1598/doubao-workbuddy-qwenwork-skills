# 相册整理

所有命令的 stdout 输出遵循 NDJSON 协议，每行一个 JSON 对象（统一为 `IApiType` 格式）。提示信息输出到 stderr（仅 `--verbose` 模式可见）。

---

## 使用前提

- **整理行为默认为复制**：文件整理的默认行为是将匹配文件的副本拷贝到新建的目标文件夹中，原文件保持不动、不会被删除或移动。当整理涉及的文件数量超过 **500** 时，服务端会中断整理流程并要求二次确认，此时用户可选择**复制**（copy，默认）或**移动**（move）方式完成整理。
- **适用范围**：file-organize 仅处理个人照片、图片、视频、录像、截图、自拍、相簿等媒体整理；不处理文档、PDF、压缩包、音频、应用、种子、资料等非媒体文件，也不处理考研、考公、四六级等文档资料整理。
- **移动需求排除**：用户明确有"移动"需求时，不应触发相册整理，应走文件操作/移动流程。
- 用户的整理指令必须**清晰明确**，包含以下三要素：
  1. **整理范围**：要整理哪些照片（如"去年十月在北京长城的照片"、"网盘里的美食照片"）
  2. **整理方式**：如何分类（如"按地点分类"、"按月份归类"），可省略（用户首次未指明整理方式时需澄清，后续可省略由系统会自动推断）
  3. **限制条件**：排除/筛选条件（如"不要自拍照"），可省略
- 如果用户的指令**不明确**，应先向用户澄清再调用。部分需澄清的例子
  1. "帮我整理下旅游照片"。旅游照片范围宽泛，没有明确整理范围，整理范围需澄清明确
  2. "帮我整理下个人证件"。没有明确整理方式，整理方式需澄清明确

> **⚠️ 调用约束：请将用户澄清后的完整指令作为 `<user_request>` 参数一次性传入，不要拆分成多次调用。**
>
> **⚠️ 自包含约束：file-organize 是自包含的原子操作，内部已集成意图识别、文件搜索、方案生成全流程。**
> - 禁止在调用前先调用 search 搜索图片（file-organize 内部会自动搜索）
> - 禁止下载图片后本地理解图片内容（file-organize 通过 API 获取文件信息）
> - 禁止拆分用户指令为多次调用

### 意图示例

以下需求属于相册整理：

- 按照不同的人脸把照片分类
- 把我和妈妈的合照放到一个文件夹
- 把今年春节的照片和视频归到一个相簿
- 帮我把在日本拍的照片放到一个文件夹
- 按城市整理旅游照片
- 把美食照片归到「美食打卡」相簿
- 帮我把截图和拍摄的照片分开
- 把我夸克网盘中今年旅游的照片按照地点、景点进行整理
- 整理下夸克网盘中近几年跟家人朋友们一起聚餐的图片

以下需求**不属于**相册整理，不应触发：

- "帮我整理网盘里的考研资料" → 文档整理需求
- "把PDF和Word文件归类" → 文档整理需求
- "帮我整理下载文件夹" → 通用文件管理需求
- "把音乐文件按歌手分类" → 音频整理需求
- "整理一下网盘里的压缩包" → 通用文件管理需求
- "帮我把网盘里的考研资料，都移动到考研复习文件夹下" → 移动文件需求

## 命令

### 整理文件（organize）

根据用户的自然语言指令，AI 自动搜索匹配文件并完成整理（创建文件夹 + 按服务端契约拷贝文件副本至目标文件夹，原文件保持不动）。命令采用异步轮询模式：先触发整理任务获取 task_id，再轮询结果直到完成、中断或超时。

#### 入参

```bash
node scripts/quark-drive.cjs organize --query <QUERY>
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--query <string>` | string | 必填 | -- | 整理指令（自然语言描述，如"把照片按年份归类"） |

#### 执行流程

1. 初始化 SDK + 助手管理器
2. 调用 `/open/v1/assistant/file_organize` 触发整理任务，获取 `task_id`
3. 每 2 秒轮询 `/open/v1/assistant/file_organize/pull_result`，最长等待 3 分钟
4. `finish=1` 时轮询结束，根据 `finish_reason` 输出不同结果：
   - `finish_reason=STOP`：整理正常完成，输出整理结果
   - `finish_reason` 非 `STOP`：需要用户介入（如文件数量过多需确认整理方式），输出 `-1609` 错误码，`msg` 携带服务端提示信息

#### 成功出参（finish_reason=STOP）

整理正常完成时，输出 NDJSON result。

##### NDJSON 输出序列

轮询期间输出 progress 行，完成后输出 result 行：

```jsonl
{"msg":"处理中","data":{"message":"相册整理中","retry":1},"action":"organize","type":"progress"}
{"msg":"处理中","data":{"message":"相册整理中","retry":2},"action":"organize","type":"progress"}
{"code":0,"msg":"成功","data":{"task_id":"abc123","finish":1,"target_dir_list":[...],"total_file_count":15,"organize_path":"夸克网盘/整理/旅游照片","checkAllLink":"https://pan.quark.cn/open/v1/oauth/agent#/skill-sub-file-list?fid=f1"},"action":"organize","type":"result"}
```

**result data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 整理任务 ID |
| `finish` | number | 完成状态，固定为 `1` |
| `target_dir_list` | array | 整理后的目标目录列表；保留该字段用于兼容旧版 agent 调用方 |
| `total_file_count` | number | 整理涉及的文件总数 |
| `organize_path` | string | 第一个整理目标目录的完整路径（以 `"夸克网盘/"` 为前缀，如 `"夸克网盘/整理/旅游照片"`）。路径解析失败时不返回该字段 |
| `checkAllLink` | string | **wild 模式特有字段**。整理结果的夸克网盘查看地址（取第一个整理目标）：目标为文件夹时路由到子文件列表页，为文件时路由到落地页。agent 须将其呈现给用户用于点击查看全部整理结果 |

> **agent 须知**：整理完成后，agent 必须以**表格**形式展示整理结果，表格列包括：**目标文件夹名称**、**文件数量**、**整理路径**。可从 `result.data` 中提取 `target_dir_list`、`total_file_count` 和 `organize_path` 等信息组织表格，同时用 1-2 句话概括整理情况（如"已将 15 张照片按地点整理到 3 个文件夹"）。**成功完成时整理操作已全部执行（文件副本已拷贝至目标文件夹，原文件保持不动），agent 禁止提示用户"确认"或暗示需要用户确认后才执行。**
>
> **呈现查看链接**：当 `data.checkAllLink` 存在且非空时，agent 必须透出该链接供用户点击查看整理结果，**以可点击链接形式展示**（如 Markdown `[点击查看整理结果](checkAllLink)`）。当环境不支持可点击渲染时，**直接展示完整地址原文**（明文 URL）以便用户复制访问；**禁止**用代码块/行内代码包裹或截断该地址。`checkAllLink` 为空时省略该提示。
>                                                                                        
> **agent 须知（零结果场景）**：当整理正常完成但 `total_file_count` 为 `0` 时，表示整理流程正常完成但未找到符合条件的文件。agent 回复用户时**必须使用自然语言描述**（如"网盘中没有找到符合条件的文件"），**严禁**在回复中暴露任何内部字段名（如 `total_file_count`、`finish`、`task_id` 等）。错误示例：~~"结果显示 total_file_count：0，意思是没有找到文件"~~；正确示例："整理完成，但网盘中没有找到符合你描述的文件，可以尝试调整整理范围后重试"。

#### 需确认出参（finish_reason 非 STOP）

当服务端检测到整理涉及的文件数量过多（通常超过 **500**），返回 `finish=1` 但 `finish_reason` 不为 `STOP`，要求用户确认整理方式。此时 CLI 输出错误码 `-1609`，`msg` 携带服务端返回的提示信息，`data.task_id` 携带任务 ID。

##### NDJSON 输出序列

```jsonl
{"msg":"处理中","data":{"message":"相册整理中","retry":1},"action":"organize","type":"progress"}
{"code":-1609,"msg":"为你找到654项内容，共0.9GB。你想让我「复制整理」还是「移动整理」？由于结果文件较多，复制整理会多占一倍空间，建议选择移动整理哦。","data":{"task_id":"abc123"},"action":"organize","type":"result"}
```

**result 字段说明（错误码 -1609）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `msg` | string | 服务端返回的用户友好提示信息，agent 应如实展示给用户 |
| `data.task_id` | string | 整理任务 ID，后续调用 `organize-confirm` 时需传入 |

> **agent 须知**：收到 `-1609` 时，agent 应将 `msg` 中的提示信息**如实展示给用户**（禁止暴露错误码、字段名等技术细节），等待用户选择整理方式（复制或移动），然后使用 `data.task_id` 调用对应命令提交确认：选择复制则调用 `organize-copy --task-id <TASK_ID>`，选择移动则调用 `organize-move --task-id <TASK_ID>`。
>
> **agent 回复示例**：
> - ✅ 直接展示服务端提示："为你找到654项内容，共0.9GB。你想让我「复制整理」还是「移动整理」？由于结果文件较多，复制整理会多占一倍空间，建议选择移动整理哦。\n\n请问你选择哪种方式？"（用户选择后调用 `organize-copy` 或 `organize-move`）
> - ❌ "收到 -1609 错误码，finish_reason=CONFIRM，task_id=abc123"
> - ❌ "finish=3，需要确认，请选择 copy 或 move"

#### 失败出参

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -1601 | 缺少必要参数: --query | 未传入 `--query` 参数 |
| -1602 | 发起相册整理请求失败 | 触发整理 API 返回 `status !== 0`，`msg` 附带服务端 `error_info` |
| -1603 | 查询相册整理结果失败 | 轮询 API 返回 `status !== 0`，`msg` 附带服务端 `error_info`，`data.task_id` 携带任务 ID |
| -1604 | 相册整理任务轮询超时 | 轮询超过 3 分钟未完成，`data.task_id` 携带任务 ID |
| -1605 | 相册整理任务被中断 | 预留错误码 |
| -1609 | 文件整理需要二次确认 | 轮询返回 `finish_reason` 非 `STOP` 时触发，`msg` 携带服务端返回的用户友好提示信息，`data.task_id` 携带任务 ID。agent 应将 `msg` 如实展示给用户，引导用户确认后调用 `organize-confirm` 命令 |

**失败示例**：

```jsonl
{"code":-1601,"msg":"缺少必要参数: --query","data":{},"action":"organize","type":"result"}
```

```jsonl
{"code":-1602,"msg":"发起相册整理请求失败: invalid token","data":{},"action":"organize","type":"result"}
```

```jsonl
{"code":-1603,"msg":"查询相册整理结果失败: server error","data":{"task_id":"abc123"},"action":"organize","type":"result"}
```

```jsonl
{"code":-1604,"msg":"相册整理超时（180s），task_id=abc123","data":{"task_id":"abc123"},"action":"organize","type":"result"}
```

```jsonl
{"code":-1609,"msg":"为你找到654项内容，共0.9GB。你想让我「复制整理」还是「移动整理」？由于结果文件较多，复制整理会多占一倍空间，建议选择移动整理哦。","data":{"task_id":"abc123"},"action":"organize","type":"result"}
```

> **agent 须知**：失败 result 的 `data` 中包含 `task_id`（如果已获取到）。当收到 `-1609` 错误码时，`msg` 中包含服务端返回的用户友好提示信息，agent 应将该提示**如实展示给用户**（禁止暴露错误码等技术细节），等待用户选择整理方式（复制/移动），然后使用 `data.task_id` 调用对应命令提交确认：选择复制则调用 `organize-copy --task-id <TASK_ID>`，选择移动则调用 `organize-move --task-id <TASK_ID>`。

### 以复制方式确认整理（organize-copy）

当 organize 命令返回错误码 `-1609`（即轮询返回 `finish_reason` 非 `STOP`）时，表示整理涉及文件数量过多，服务端要求用户确认整理方式。若用户选择**复制**，调用此命令。

#### 入参

```bash
node scripts/quark-drive.cjs organize-copy --task-id <TASK_ID>
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--task-id <string>` | string | 必填 | -- | 整理任务 ID（由 organize 命令返回的 `data.task_id`） |

#### 执行流程

1. 初始化 SDK + 助手管理器
2. 调用 `/open/v1/assistant/file_organize/confirm`（way=copy）提交确认
3. 输出 NDJSON result

#### 成功出参

```jsonl
{"code":0,"msg":"成功","data":{"task_id":"abc123"},"action":"organize-copy","type":"result"}
```

**result data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 整理任务 ID |

#### 失败出参

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -1606 | 缺少必要参数: --task-id | 未传入 `--task-id` 参数 |
| -1608 | 文件整理确认请求失败 | 确认 API 返回 `status !== 0`，`msg` 附带服务端 `error_info` |

**失败示例**：

```jsonl
{"code":-1606,"msg":"缺少必要参数: --task-id","data":{},"action":"organize-copy","type":"result"}
```

```jsonl
{"code":-1608,"msg":"文件整理确认请求失败: task not found","data":{"task_id":"abc123"},"action":"organize-copy","type":"result"}
```

---

### 以移动方式确认整理（organize-move）

当 organize 命令返回错误码 `-1609` 时，若用户选择**移动**，调用此命令。

#### 入参

```bash
node scripts/quark-drive.cjs organize-move --task-id <TASK_ID>
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--task-id <string>` | string | 必填 | -- | 整理任务 ID（由 organize 命令返回的 `data.task_id`） |

#### 执行流程

1. 初始化 SDK + 助手管理器
2. 调用 `/open/v1/assistant/file_organize/confirm`（way=move）提交确认
3. 输出 NDJSON result

#### 成功出参

```jsonl
{"code":0,"msg":"成功","data":{"task_id":"abc123"},"action":"organize-move","type":"result"}
```

**result data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 整理任务 ID |

#### 失败出参

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -1606 | 缺少必要参数: --task-id | 未传入 `--task-id` 参数 |
| -1608 | 文件整理确认请求失败 | 确认 API 返回 `status !== 0`，`msg` 附带服务端 `error_info` |

**失败示例**：

```jsonl
{"code":-1606,"msg":"缺少必要参数: --task-id","data":{},"action":"organize-move","type":"result"}
```

```jsonl
{"code":-1608,"msg":"文件整理确认请求失败: task not found","data":{"task_id":"abc123"},"action":"organize-move","type":"result"}
```

---

## Troubleshooting

### 整理超时（-1604）

**现象**：命令输出 `code: -1604`，提示相册整理超时。

**排查**：
1. 确认网络连接正常
2. 检查整理指令是否过于复杂（涉及大量文件）

**解决**：
- 简化整理指令，缩小整理范围（如指定具体文件夹）
- 重试命令

### 触发失败（-1602）

**现象**：命令输出 `code: -1602`，提示发起相册整理请求失败。

**排查**：
1. 检查 `msg` 中的具体错误信息
2. 确认用户是否已授权

**解决**：
- 若提示 token 相关错误，重新登录后重试
- 若提示服务端错误，稍后重试
