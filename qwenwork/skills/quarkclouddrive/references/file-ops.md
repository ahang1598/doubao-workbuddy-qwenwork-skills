# 文件操作

所有命令的 stdout 输出遵循 NDJSON 协议，每行一个 JSON 对象（统一为 `IApiType` 格式）。提示信息输出到 stderr（仅 `--verbose` 模式可见）。

## NDJSON 统一输出格式（IApiType）

所有 stdout 输出行均遵循以下结构：

```typescript
{
  code?: number;       // 状态码，0 为成功，负数为 CLI 错误码（progress 类型不含 code）
  msg: string;         // 状态描述
  action: string;      // 命令名称（如 "upload"、"download"）
  type: string; // 输出类型："result" | "progress" | "list"
  data: object;        // 业务数据
}
```

- **`type: "result"`** — 命令最终结果，每个命令的最后一行
- **`type: "progress"`** — 长任务（上传）的中间进度
- **`type: "list"`** — 列表条目（如 browse 的文件列表、upload 的失败任务）

**失败处理**：命令失败时通过 `CliExitError` 抛出（进程退出码 1），顶层 `quark-drive.ts` 的 catch 捕获后输出一行 `IApiType` 格式的错误结果到 stdout：

```jsonl
{"code":<错误码>,"msg":"<错误信息>","data":{},"action":"<命令名>","type":"result"}
```

- **`code`**：来自 `CliExitError.errorCode`，即 `error_constants.ts` 中定义的负数错误码
- **`msg`**：来自 `CliExitError.message`，为 `CLI_ERROR_MAP` 中的默认消息或命令中通过 `customMsg` 覆盖的动态消息
- **`data`**：固定为 `{}`
- **`action`**：来自 `CliExitError.action`，即命令名称
- **`type`**：固定为 `"result"`

---

## 目录 FID 说明

网盘中每个目录都有一个唯一的目录 FID（字符串类型）。特殊值 `"0"` 代表**根目录**（网盘最顶层目录）。

> **重要约束（面向 AI agent）**：`upload` 和 `saveas` 命令的目标目录参数（`--parent-fid`、`--to-pdir-fid`、`--to-pdir-path`）均为**选填参数**。当用户没有明确指定保存到哪个目录时，**严禁自行补充 `"0"` 或任何目录参数**，必须省略该参数，让 CLI 使用内部默认行为。只有当用户明确说"保存到根目录"或提供了具体的目录 FID/路径时，才传入对应参数。

---

## 命令

### 创建文件夹（create-folder）

在网盘指定目录下创建文件夹。同名文件夹重复创建时具有幂等性，返回已有文件夹的 FID。

#### 入参

```bash
node scripts/quark-drive.cjs create-folder --dir-path <DIR_PATH> [--parent-fid <PDIR_FID>]
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--dir-path <path>` | string | 必填 | — | 文件夹名称或路径 |
| `--parent-fid <fid>` | string | 选填 | 服务端默认目录 | 父目录 FID（`"0"` 代表根目录） |

> **重要（面向 AI agent）**：`--parent-fid` 不传时，服务端会将文件夹创建在平台默认目录中，**而非根目录**。当用户明确要求在根目录下创建文件夹时，**必须**传入 `--parent-fid "0"`；当用户指定了具体目录 FID 时，传入对应 FID。仅当用户未指定目录且无明确偏好时，才可省略该参数。

#### 成功出参

仅一行 `type: "result"`，无进度输出。

**result.data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fid` | string | 创建的文件夹 FID |
| `full_path` | string | 文件夹完整路径（从「夸克网盘」根目录拼接，如 `"夸克网盘/我的备份/my-folder"`）。路径解析失败时不返回该字段 |

**成功示例**：

```jsonl
{"code":0,"msg":"成功","data":{"fid":"4cdd65bd1a2b3c4d","full_path":"夸克网盘/我的备份/my-folder"},"action":"create-folder","type":"result"}
```

#### 失败出参

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -601 | 缺少必要参数: --dir-path | 未传 `--dir-path` 参数 |
| -602 | 文件浏览器实例不存在 | SDK 文件浏览器初始化失败，`msg` 使用默认消息 |
| -603 | 创建操作失败 | SDK `createFolder` 返回 `status !== 0`，`msg` 优先使用 SDK 返回的 `error_info`，无则使用默认消息 |

**失败示例**：

```jsonl
{"code":-601,"msg":"缺少必要参数: --dir-path","data":{},"action":"create-folder","type":"result"}
```

```jsonl
{"code":-602,"msg":"文件浏览器实例不存在","data":{},"action":"create-folder","type":"result"}
```

```jsonl
{"code":-603,"msg":"parent folder not found","data":{},"action":"create-folder","type":"result"}
```

---

### 移动（move）

移动文件或文件夹到目标目录。支持同时移动多个文件（最多 100 个），使用同步移动模式（type=1）。

#### 入参

```bash
node scripts/quark-drive.cjs move <FID1> [FID2...] --target-fid <TARGET_FID>
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `[fids...]` | string[] | 必填 | — | 要移动的文件 FID 列表（位置参数，至少一个） |
| `--target-fid <fid>` | string | 必填 | — | 目标目录 FID |

#### 成功出参

仅一行 `type: "result"`，无进度输出。

**result.data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fids` | string[] | 移动的文件 FID 列表 |
| `targetFid` | string | 实际移动到的目标目录 FID。通常等于入参 `--target-fid`；若服务端异步任务返回最终目录，则以服务端返回值为准 |
| `move_path` | string | 实际移动到的目标目录完整路径（含目标目录自身名称，如 `"夸克网盘/文档/目标文件夹"`）。路径解析失败时不返回该字段 |

**成功示例**：

```jsonl
{"code":0,"msg":"成功","data":{"fids":["e33ed06b1a2b3c4d","f44fe17c2b3c4d5e"],"targetFid":"4cdd65bd1a2b3c4d","move_path":"夸克网盘/文档/目标文件夹"},"action":"move","type":"result"}
```

#### 失败出参

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -501 | 缺少必要参数: 文件 FID 列表 | 未传入任何 FID 参数 |
| -502 | 缺少必要参数: --target-fid | 未传 `--target-fid` 参数 |
| -503 | 文件浏览器实例不存在 | SDK 文件浏览器初始化失败，`msg` 使用默认消息 |
| -504 | 移动操作失败 | SDK `moveFiles` 返回 `status !== 0`，`msg` 优先使用 SDK 返回的 `error_info`，无则使用默认消息 |

**失败示例**：

```jsonl
{"code":-501,"msg":"缺少必要参数: 文件 FID 列表","data":{},"action":"move","type":"result"}
```

```jsonl
{"code":-502,"msg":"缺少必要参数: --target-fid","data":{},"action":"move","type":"result"}
```

```jsonl
{"code":-503,"msg":"文件浏览器实例不存在","data":{},"action":"move","type":"result"}
```

```jsonl
{"code":-504,"msg":"target folder not found","data":{},"action":"move","type":"result"}
```


