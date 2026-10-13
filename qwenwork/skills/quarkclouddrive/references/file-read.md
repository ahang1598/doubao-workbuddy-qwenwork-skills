# 读取文件

读取网盘文件内容，支持多文件批量读取、断点续传、任务管理。

> **用语规范**：read-file 命令在面向用户的所有场景中统一使用「读取」而非「下载」。用户能感知到的是「模型读取了文件内容」，而非文件被下载到了个人设备。因此 agent 在**所有面向用户的表述**中——包括规划说明、中间过程描述、操作结果——**必须**使用「读取」，**禁止**使用「下载」或「到本地」。
>
> - ✅ "读取照片内容后为您制作贺卡"、"正在读取文件"、"读取成功"
> - ❌ "下载到本地然后制作贺卡"、"正在下载文件"、"下载成功"、"读取文件到本地"
>
> 代码中出现的 `DownloadManager`、`downloadedSize` 等为 SDK 内部命名，不影响面向用户的表述。

## 命令

### 读取文件（read-file）

读取网盘文件内容，支持多文件批量读取。通过 FID 指定文件，串行依次读取。支持 Ctrl+C 自动保存断点。

#### 入参

```bash
# 单文件
node scripts/quark-drive.cjs read-file --fid <FID> [--overwrite]

# 多文件（位置参数）
node scripts/quark-drive.cjs read-file <FID1> <FID2> <FID3> [--overwrite]

# 混合（位置参数 + --fid，所有 FID 合并去重）
node scripts/quark-drive.cjs read-file <FID1> <FID2> --fid <FID3>
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `[fids...]` | string[] | 与 `--fid` 二选一 | — | 文件 FID 列表（位置参数，支持多个） |
| `--fid <fid>` | string | 与位置参数二选一 | — | 文件 FID（单文件时可用，多文件时推荐使用位置参数） |
| `--overwrite` | boolean | 选填 | `false` | 同名文件时覆盖已有文件（默认：自动重命名） |

文件最终保存到 `$OPENCLAW_RUNTIME_DIR/.quarkclouddrive` 目录（运行时目录由平台注入）。读取过程中文件先写入 `/tmp/.quarkclouddrive/` 临时目录，完成后自动移动到最终目录，以兼容不支持随机偏移写入的文件系统（如 FUSE 挂载）。临时文件在读取失败或中断时会自动清理。

#### 成功出参

多文件时，每个文件读取完成后输出一行 `type: "list"`，最终输出一行 `type: "result"` 汇总。读取过程中输出 `type: "progress"` 进度行。

**list 行 data 字段**（每个文件一行）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fid` | string | 文件 FID |
| `fileName` | string | 文件名 |
| `filePath` | string | 文件保存的本地绝对路径 |
| `fileSize` | number | 文件大小（字节） |

**result.data 字段**（汇总）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalCount` | number | 总文件数 |
| `successCount` | number | 成功读取数 |
| `failCount` | number | 失败数 |
| `files` | array | 每个文件的详细结果 |

**成功示例（多文件）**：

```jsonl
{"code":0,"msg":"读取成功","data":{"fid":"abc123","fileName":"doc.pdf","filePath":"<runtimeDir>/.quarkclouddrive/doc.pdf","fileSize":1024000},"action":"read-file","type":"list"}
{"code":0,"msg":"读取成功","data":{"fid":"def456","fileName":"img.png","filePath":"<runtimeDir>/.quarkclouddrive/img.png","fileSize":2048000},"action":"read-file","type":"list"}
{"code":0,"msg":"成功","data":{"totalCount":2,"successCount":2,"failCount":0,"files":[{"fid":"abc123","fileName":"doc.pdf","filePath":"<runtimeDir>/.quarkclouddrive/doc.pdf","fileSize":1024000,"success":true},{"fid":"def456","fileName":"img.png","filePath":"<runtimeDir>/.quarkclouddrive/img.png","fileSize":2048000,"success":true}]},"action":"read-file","type":"result"}
```

**成功示例（单文件）**：

```jsonl
{"msg":"","action":"read-file","type":"progress","data":{"current":2048000,"total":10240000,"percent":20}}
{"code":0,"msg":"读取成功","data":{"fid":"abc123","fileName":"document.pdf","filePath":"<runtimeDir>/.quarkclouddrive/document.pdf","fileSize":10240000},"action":"read-file","type":"list"}
{"code":0,"msg":"成功","data":{"totalCount":1,"successCount":1,"failCount":0,"files":[{"fid":"abc123","fileName":"document.pdf","filePath":"<runtimeDir>/.quarkclouddrive/document.pdf","fileSize":10240000,"success":true}]},"action":"read-file","type":"result"}
```

#### 失败出参

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -1701 | 缺少必要参数: --fid | 未传任何 FID 参数 |
| -1702 | 获取读取链接失败 | SDK `getDownloadUrlById` 返回 `status !== 0`，`msg` 优先使用 SDK 返回的 `error_info` |
| -1703 | 创建读取任务失败 | SDK `createTask` 返回 `status !== 0`，`msg` 优先使用 SDK 返回的 `error_info` |
| -1704 | 读取文件失败 | 读取执行过程中出错 |

**说明**：多文件模式下，单个文件失败不会中断整体流程，失败信息通过 `type: "list"` 行输出，最终 `result` 中 `failCount > 0` 表示存在失败的文件。

**失败示例**：

```jsonl
{"code":-1701,"msg":"缺少必要参数: --fid","data":{},"action":"read-file","type":"result"}
```

```jsonl
{"code":-1,"msg":"file not found","data":{"fid":"invalid_fid","fileName":"","filePath":"","fileSize":0},"action":"read-file","type":"list"}
```

---

### 读取文件任务列表（read-file list）

列出所有持久化的读取文件任务，支持按状态过滤。

#### 入参

```bash
node scripts/quark-drive.cjs read-file list [--state <state>]
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--state <state>` | string | 选填 | — | 按状态过滤 (pending/paused/failed/completed) |

#### 成功出参

逐条输出任务信息（`type: "list"`），最终输出一行 `type: "result"` 汇总。

**list 行 data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `recordId` | string | 任务 ID |
| `fileName` | string | 文件名 |
| `fileSize` | number | 文件大小（字节） |
| `state` | string | 任务状态 |
| `downloadedSize` | number | 已读取大小（字节） |

**result.data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalCount` | number | 任务总数 |

**成功示例**：

```jsonl
{"code":0,"msg":"","data":{"recordId":"rec_001","fileName":"doc.pdf","fileSize":1024000,"state":"paused","downloadedSize":0},"action":"read-file-list","type":"list"}
{"code":0,"msg":"成功","data":{"totalCount":1},"action":"read-file-list","type":"result"}
```

#### 失败出参

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -1705 | 没有持久化的读取任务 | 加载持久化任务失败 |

---

### 恢复读取文件任务（read-file resume）

恢复指定的读取文件任务，支持断点续传。

#### 入参

```bash
node scripts/quark-drive.cjs read-file resume --record-id <id>
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--record-id <id>` | string | 必填 | — | 任务 ID（通过 `read-file list` 获取） |

#### 成功出参

读取过程中输出 `type: "progress"` 进度行，完成后输出 `type: "result"`。

**result.data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `recordId` | string | 任务 ID |
| `fileName` | string | 文件名 |
| `filePath` | string | 文件保存的本地绝对路径 |

**成功示例**：

```jsonl
{"msg":"","action":"read-file-resume","type":"progress","data":{"current":5120000,"total":10240000,"percent":50}}
{"code":0,"msg":"成功","data":{"recordId":"rec_001","fileName":"doc.pdf","filePath":"<runtimeDir>/.quarkclouddrive/doc.pdf"},"action":"read-file-resume","type":"result"}
```

#### 失败出参

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -1706 | 缺少必要参数: --record-id | 未传 record-id |
| -1707 | 指定的读取任务不存在 | 持久化层找不到对应任务 |
| -1708 | 任务恢复失败 | restoreTask 或 resumeTask 返回失败 |
| -1704 | 读取文件失败 | 读取执行过程中出错 |

---

### 删除读取文件任务记录（read-file delete）

删除持久化的读取文件任务记录。

#### 入参

```bash
node scripts/quark-drive.cjs read-file delete --record-id <id>
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--record-id <id>` | string | 必填 | — | 任务 ID（通过 `read-file list` 获取） |

#### 成功出参

**result.data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `recordId` | string | 已删除的任务 ID |

**成功示例**：

```jsonl
{"code":0,"msg":"成功","data":{"recordId":"rec_001"},"action":"read-file-delete","type":"result"}
```

#### 失败出参

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -1706 | 缺少必要参数: --record-id | 未传 record-id |
| -1707 | 指定的读取任务不存在 | 持久化层找不到对应任务 |
