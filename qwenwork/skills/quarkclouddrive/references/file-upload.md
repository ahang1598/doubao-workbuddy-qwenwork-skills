# 上传（upload）

上传文件或文件夹到网盘指定目录。支持同时传入多个路径，每个路径可以是文件或文件夹，SDK 自动递归上传文件夹内容。

## 入参

```bash
node scripts/quark-drive.cjs upload <PATH1> [PATH2] [PATH3...] [--parent-fid <PDIR_FID>]
node scripts/quark-drive.cjs upload --file-path <LOCAL_PATH> [--parent-fid <PDIR_FID>]
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `[paths...]` | string[] | 与 `--file-path` 二选一 | — | 本地文件或文件夹路径列表（variadic argument，支持多个） |
| `--file-path <path>` | string | 与 `paths` 二选一 | — | 本地文件或文件夹路径（向后兼容，推荐直接传参） |
| `--parent-fid <fid>` | string | 选填 | — | 目标目录 FID。不传时由 CLI 内部决定默认行为 |

> **重要（面向 AI agent）**：`--parent-fid` 是选填参数。当用户没有明确指定上传到哪个目录时，**严禁自行补充 `"0"` 或任何值**，必须省略该参数。只有当用户明确说"上传到根目录"或提供了具体的目录 FID 时，才传入该参数。`"0"` 代表根目录。

> **多文件上传（面向 AI agent）**：本 CLI 上传命令支持多路径上传，有两种方式：
> 1. **直接传入多个路径**（推荐）：`upload path1 path2 path3`，CLI 会逐个路径调用 SDK 上传，每个路径如果是文件夹则递归上传目录结构。
> 2. **传入文件夹路径**：将文件放入同一目录，传入目录路径即可一次性上传。
>
> 两种方式均支持混合使用（`upload ./file1.txt ./dir1 --file-path ./file2.txt`）。`paths` 参数和 `--file-path` 选项会合并去重。

## 成功出参

上传过程中持续输出 `type: "progress"` 进度行（`data.current`/`data.total` 为所有子任务的汇总字节数）。每个子任务到达终态时输出 `type: "list"` 行（成功或失败各一行）。最后一行为 `type: "result"`。

**progress 行 data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `current` | number | 已上传字节数（所有子任务汇总） |
| `total` | number | 总字节数（所有子任务汇总） |
| `percent` | number | 上传百分比（0-100 整数） |

**成功任务 list 行**（`code: 0`，单个子任务上传成功时输出）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.recordId` | string | 任务记录 ID |
| `data.fileId` | string | 上传成功的文件 FID |
| `data.fileName` | string | 文件名 |
| `data.fileSize` | number | 文件大小（字节） |
| `data.instantUpload` | boolean | 是否秒传（服务端已存在相同文件，跳过实际上传） |

**失败任务 list 行**（`code: SDK 错误码`，单个子任务上传失败时输出）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.recordId` | string | 失败任务的记录 ID |

**result 行**：所有子任务完成后输出。如果全部成功，`code: 0`；如果存在失败任务，`code: -204`（由顶层 catch 捕获 `CliExitError` 输出）。

**全部成功时 result 行 data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.fileNames` | string[] | 上传的文件/目录名列表 |
| `data.fileCount` | number | 传入的路径数量 |
| `data.totalSize` | number | 所有文件总大小（字节，文件夹不计入） |
| `data.fids` | string[] | 上传成功的文件 FID 列表 |
| `data.successCount` | number | 上传成功的任务数量 |
| `data.instantUpload` | boolean | 是否存在秒传文件（任一文件秒传即为 true） |
| `data.instantUploadCount` | number | 秒传成功的文件数量 |
| `data.fullPath` | string | 上传文件在网盘中的完整路径（以 `"夸克网盘/"` 为前缀，由第一个成功文件的 file/info 接口获取，尽力而为，失败时为空字符串）。路径不含文件自身名称，表示文件所在目录的完整路径 |

> **fullPath 解析规则（面向 AI agent）**：
> - `fullPath` 含 `/` 且非仅为前缀 → 向用户说"已上传到「{fullPath}」目录"
> - `fullPath` 为空字符串 `""` 或不含 `/` → 仅说"已上传到夸克网盘"，**绝对禁止说"根目录"**
> - 仅当用户明确请求"上传到根目录"且 Agent 显式传入了 `--parent-fid=0` 时，才能在回复中说"根目录"
> - ❌ 反例：`fullPath` 为 `"夸克网盘"`（不含 `/`）时说"已保存到根目录" — 这是错误的

**成功示例**（全部子任务成功）：

```jsonl
{"msg":"进行中","data":{"current":1048576,"total":10485760,"percent":10},"action":"upload","type":"progress"}
{"msg":"进行中","data":{"current":5242880,"total":10485760,"percent":50},"action":"upload","type":"progress"}
{"code":0,"msg":"上传成功","data":{"recordId":"rec_1","fileId":"844db92f066f4537b59ff668d1d75144","fileName":"test.txt","fileSize":256,"instantUpload":false},"action":"upload","type":"list"}
{"msg":"进行中","data":{"current":10485760,"total":10485760,"percent":100},"action":"upload","type":"progress"}
{"code":0,"msg":"成功","data":{"fileNames":["test.txt"],"fileCount":1,"totalSize":256,"fids":["844db92f066f4537b59ff668d1d75144"],"successCount":1,"instantUpload":false,"instantUploadCount":0,"fullPath":"夸克网盘/我的文档"},"action":"upload","type":"result"}
```

**部分失败示例**（存在失败子任务时，`checkAllTasksDone` 通过 `state.reject(CliExitError)` 抛出异常，`ctx.finish()` 不会执行，最终由顶层 catch 输出 `-204` 错误 result 行）：

```jsonl
{"code":0,"msg":"上传成功","data":{"recordId":"rec_1","fileId":"file_1","fileName":"a.txt","fileSize":1024,"instantUpload":true},"action":"upload","type":"list"}
{"code":31003,"msg":"file hash conflict","data":{"recordId":"rec_abc123"},"action":"upload","type":"list"}
{"code":-204,"msg":"上传操作失败, 失败任务数量: 1","data":{},"action":"upload","type":"result"}
```

## 失败出参

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -201 | 缺少必要参数: --file-path | 未传文件路径（`paths` 和 `--file-path` 均为空） |
| -202 | 文件不存在 | 指定的本地文件路径不存在，错误信息会附带具体路径 |
| -203 | 上传管理器实例不存在 | SDK 上传管理器初始化失败，`msg` 使用默认消息 |
| -204 | 上传操作失败 | 所有上传任务完成后存在失败任务，`msg` 附带失败任务数量（如 `"上传操作失败, 失败任务数量: 2"`） |

**失败示例**：

```jsonl
{"code":-201,"msg":"缺少必要参数: --file-path","data":{},"action":"upload","type":"result"}
```

```jsonl
{"code":-202,"msg":"文件不存在: /path/to/nonexistent.txt","data":{},"action":"upload","type":"result"}
```

```jsonl
{"code":-203,"msg":"上传管理器实例不存在","data":{},"action":"upload","type":"result"}
```

```jsonl
{"code":-204,"msg":"上传操作失败, 失败任务数量: 2","data":{},"action":"upload","type":"result"}
```

## 断点续传子命令

上传支持断点续传。上传过程中按 Ctrl+C 会自动保存断点，后续可通过子命令管理和恢复任务。

### 列出上传任务（upload list）

列出所有持久化的上传任务记录。

```bash
node scripts/quark-drive.cjs upload list [--state <STATE>]
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--state <state>` | string | 选填 | — | 按状态过滤：`pending`/`hashing`/`uploading`/`paused`/`success`/`failed`/`cancelled`/`post_hashing` |

**成功出参**

逐条输出 `type: "list"` 行，最后一行为 `type: "result"`。

**list 行 data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `recordId` | string | 任务 ID |
| `fileName` | string | 文件名 |
| `fileSize` | number | 文件大小（字节） |
| `state` | string | 任务状态（`pending`/`hashing`/`uploading`/`paused`/`success`/`failed`/`cancelled`/`post_hashing`） |
| `createdAt` | number | 创建时间（毫秒时间戳） |

**成功示例**：

```jsonl
{"code":0,"msg":"","data":{"recordId":"abc123","fileName":"video.mp4","fileSize":104857600,"state":"paused","createdAt":1700000000000},"action":"upload-list","type":"list"}
{"code":0,"msg":"成功","data":{"totalCount":1},"action":"upload-list","type":"result"}
```

**失败出参**

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -209 | 加载持久化任务失败 | SDK `loadPersistedTasks` 返回 `status !== 0`，`msg` 附带 SDK 返回的 `error_info` |

### 恢复上传任务（upload resume）

从持久化存储恢复指定的上传任务并继续上传。恢复过程中按 Ctrl+C 同样会自动保存断点。

```bash
node scripts/quark-drive.cjs upload resume --record-id <ID>
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--record-id <id>` | string | 必填 | — | 任务 ID（从 `upload list` 获取） |

**成功出参**

上传过程中输出 `type: "progress"` 进度行，每个任务完成时输出 `type: "list"` 行，最后一行为 `type: "result"`。

**list 行 data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `recordId` | string | 任务 ID |
| `fileId` | string | 上传成功后的文件 FID |
| `fileName` | string | 文件名 |
| `fileSize` | number | 文件大小（字节） |
| `instantUpload` | boolean | 是否秒传 |

**成功示例**：

```jsonl
{"msg":"进行中","data":{"current":52428800,"total":104857600,"percent":50},"action":"upload-resume","type":"progress"}
{"code":0,"msg":"上传成功","data":{"recordId":"abc123","fileId":"fid456","fileName":"video.mp4","fileSize":104857600,"instantUpload":false},"action":"upload-resume","type":"list"}
{"code":0,"msg":"成功","data":{"recordId":"abc123","fileName":"video.mp4"},"action":"upload-resume","type":"result"}
```

**失败出参**

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -204 | 上传操作失败 | 上传任务 `onFailure` 回调触发，`code` 优先使用 SDK 返回的 `errorCode`，`msg` 优先使用 SDK 返回的 `errorMessage` |
| -205 | 任务不存在 | 指定的 `--record-id` 在持久化任务列表中不存在 |
| -208 | 恢复任务失败 | SDK `restoreTask` 返回失败，`msg` 附带具体错误信息 |
| -210 | 缺少必要参数: --record-id | 未传 `--record-id` 参数 |

**失败示例**：

```jsonl
{"code":-210,"msg":"缺少必要参数: --record-id","data":{},"action":"upload-resume","type":"result"}
```

```jsonl
{"code":-205,"msg":"未找到任务: abc123","data":{},"action":"upload-resume","type":"result"}
```

```jsonl
{"code":-208,"msg":"恢复失败: task expired","data":{},"action":"upload-resume","type":"result"}
```

### 删除上传任务记录（upload delete）

删除持久化的上传任务记录。

```bash
node scripts/quark-drive.cjs upload delete --record-id <ID>
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--record-id <id>` | string | 必填 | — | 任务 ID（从 `upload list` 获取） |

**成功出参**

仅一行 `type: "result"`，无进度输出。

**result.data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `recordId` | string | 已删除的任务 ID |

**成功示例**：

```jsonl
{"code":0,"msg":"成功","data":{"recordId":"abc123"},"action":"upload-delete","type":"result"}
```

**失败出参**

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -205 | 任务不存在 | 指定的 `--record-id` 在持久化任务列表中不存在 |
| -210 | 缺少必要参数: --record-id | 未传 `--record-id` 参数 |

**失败示例**：

```jsonl
{"code":-210,"msg":"缺少必要参数: --record-id","data":{},"action":"upload-delete","type":"result"}
```

```jsonl
{"code":-205,"msg":"未找到任务: abc123","data":{},"action":"upload-delete","type":"result"}
```
