# 文件分享

分享相关命令：创建分享链接、获取分享详情、分享内搜索。

---

## 命令

### 分享（share）

创建分享链接，支持多个 FID 同时分享，支持公开/私密链接和过期时间设置。

#### 入参

```bash
node scripts/quark-drive.cjs share <FID1> [FID2...] [--title <TITLE>] [--url-type <NUMBER>] [--expired-type <NUMBER>]
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `[fids...]` | string[] | 必填 | — | 要分享的文件 FID 列表（位置参数） |
| `--title <string>` | string | 选填 | — | 分享标题 |
| `--url-type <number>` | number | 选填 | `1` | 链接类型：`1`=公开链接，`2`=私密链接（提取码由服务端自动生成） |
| `--expired-type <number>` | number | 选填 | `1` | 过期类型：`1`=永久有效，`2`=1天，`3`=7天，`4`=30天，`5`=60天，`6`=100天，`7`=180天 |

#### 成功出参

仅一行 `type: "result"`，无进度输出。`data` 透传 SDK 返回的分享信息。

**result.data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `share_url` | string | 分享链接 URL |
| `passcode` | string | 提取码（仅 `url-type=2` 私密链接时返回，由服务端自动生成） |

> 注意：私密链接的提取码不由调用方指定，而是由服务端自动生成后通过 `data.passcode` 字段返回。Agent 需要从返回结果中读取 `passcode` 才能拼出完整的分享信息给用户。

**成功示例（公开链接）**：

```jsonl
{"code":0,"msg":"成功","data":{"share_url":"https://pan.quark.cn/s/abc123def456"},"action":"share","type":"result"}
```

**成功示例（私密链接）**：

```jsonl
{"code":0,"msg":"成功","data":{"share_url":"https://pan.quark.cn/s/abc123def456","passcode":"xK9m"},"action":"share","type":"result"}
```

> **❗ 分享地址展示规则（wild 模式必做）**：
> - **优先**：把 `data.share_url` 渲染成**可点击跳转**的链接展示给用户（Markdown `[分享链接](share_url)`，确保终端/客户端可识别并点击跳转）。
> - **兜底**：当环境不支持可点击链接渲染时，**直接展示完整分享地址原文**（明文 URL），保证用户能复制访问。
> - 无论哪种方式都**禁止**用代码块 / 行内代码包裹或截断分享地址，导致无法点击或复制。
> - 私密链接（`url-type=2`）还需从 `data.passcode` 读取提取码并一并告知用户，拼成完整分享信息（如「链接：<可点击 URL 或明文 URL>　提取码：xK9m」）。

#### 失败出参

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -401 | 未提供文件 FID 列表 | 未传入任何 FID 参数 |
| -402 | 分享管理器实例不存在 | SDK 分享管理器初始化失败，`msg` 使用默认消息 |
| -403 | 分享操作失败 | SDK `share` 返回 `status !== 0`，`msg` 优先使用 SDK 返回的 `error_info`，无则为 `"未知错误"` |
| -404 | 无效的链接类型 | `--url-type` 值不是 `1` 或 `2`，`msg` 附带具体的无效值 |
| -405 | 无效的过期类型 | `--expired-type` 值不在 `1-7` 范围内，`msg` 附带具体的无效值 |

**失败示例**：

```jsonl
{"code":-401,"msg":"未提供文件 FID 列表","data":{},"action":"share","type":"result"}
```

```jsonl
{"code":-402,"msg":"分享管理器实例不存在","data":{},"action":"share","type":"result"}
```

```jsonl
{"code":-403,"msg":"invalid fid","data":{},"action":"share","type":"result"}
```

```jsonl
{"code":-404,"msg":"无效的链接类型: 3，仅支持 1(公开) 或 2(私密)","data":{},"action":"share","type":"result"}
```

```jsonl
{"code":-405,"msg":"无效的过期类型: 9，仅支持 1-7","data":{},"action":"share","type":"result"}
```

---

### 获取分享详情（share-detail）

获取分享链接的详细信息，包括文件列表。支持翻页和子目录浏览（融合了原 share-page 命令的能力）。通过网盘服协议请求，支持客态模式（无需登录）。用户只需传入完整的分享链接 URL，CLI 内部自动解析 pwd_id 和提取码。

智能路由逻辑：
- 首页场景（`page=1` 且 `pdir-fid=0`）：直接调用 `getShareDetail`（1 次请求，高效）
- 翻页/子目录场景（`page>1` 或 `pdir-fid≠0`）：先调 `getShareDetail` 获取 stoken，再调 `getSharePageDetail`（2 次请求）

#### 入参

```bash
node scripts/quark-drive.cjs share-detail --url <URL> [--page <NUMBER>] [--size <NUMBER>] [--pdir-fid <FID>]
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--url <string>` | string | 必填 | — | 分享链接 URL（如 `https://pan.quark.cn/s/xxx` 或带提取码 `https://pan.quark.cn/s/xxx?pwd=abcd`） |
| `--page <number>` | number | 选填 | `1` | 页码 |
| `--size <number>` | number | 选填 | `50` | 每页条目数 |
| `--pdir-fid <string>` | string | 选填 | `0` | 目录 ID（根目录为 `"0"`，进入子目录时传对应 FID） |

#### 成功出参

仅一行 `type: "result"`，无进度输出。

**result.data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `token_info` | object | 分享令牌信息，包含 `title`（分享标题）等 |
| `share_info` | object | 分享元信息（文件总数 `file_num` 等） |
| `file_count` | number | 当前页返回的文件数量 |
| `files` | array | 文件列表 |

**files 数组元素字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fid` | string | 文件 ID |
| `filename` | string | 文件名 |
| `size` | number | 文件大小（字节） |
| `file_type` | string | 文件类型（`'0'`:文件夹 `'1'`:文件） |
| `category` | number | 文件分类 |
| `created_at` | number | 创建时间 |
| `updated_at` | number | 更新时间 |
| `share_fid_token` | string | 分享文件令牌（转存时需要） |

**成功示例（首页场景）**：

```jsonl
{"code":0,"msg":"成功","data":{"token_info":{"title":"我的分享"},"share_info":{"file_num":3},"file_count":3,"files":[{"fid":"file1","filename":"doc.pdf","size":1048576,"file_type":"1","category":4,"created_at":1700000000,"updated_at":1700000000,"share_fid_token":"token1"}]},"action":"share-detail","type":"result"}
```

**成功示例（翻页场景）**：

```jsonl
{"code":0,"msg":"成功","data":{"token_info":{"title":"我的分享"},"share_info":{"file_num":10},"file_count":5,"files":[{"fid":"file1","filename":"video.mp4","size":52428800,"file_type":"1","category":1,"created_at":1700000000,"updated_at":1700000000,"share_fid_token":"token1"}]},"action":"share-detail","type":"result"}
```

#### 失败出参

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -801 | --page 必须为正整数 | `--page` 参数不是正整数 |
| -802 | --size 必须为正整数 | `--size` 参数不是正整数 |
| -803 | 获取分享详情失败 | SDK `getShareDetail` 或 `getSharePageDetail` 返回 `status !== 0`，`msg` 附带 SDK 返回的 `errno` 和 `error_info` |
| -804 | 无效的分享链接 URL | `--url` 参数不是合法的夸克网盘分享链接 |
| -805 | 获取分享令牌失败 | 翻页/子目录场景下，内部调用 `getShareDetail` 获取 stoken 失败 |

**失败示例**：

```jsonl
{"code":-801,"msg":"--page 必须为正整数","data":{},"action":"share-detail","type":"result"}
```

```jsonl
{"code":-803,"msg":"获取分享详情失败: errno=41007, message=share not exist","data":{},"action":"share-detail","type":"result"}
```

```jsonl
{"code":-804,"msg":"无效的分享链接 URL: invalid-url","data":{},"action":"share-detail","type":"result"}
```

```jsonl
{"code":-805,"msg":"获取分享令牌失败: errno=41007, message=share not exist","data":{},"action":"share-detail","type":"result"}
```

---

### 分享内搜索（share-search）

在分享链接内搜索文件。支持客态模式（无需登录）。用户只需传入完整的分享链接 URL，CLI 内部自动获取 stoken。

#### 入参

```bash
node scripts/quark-drive.cjs share-search --url <URL> --keyword <KEYWORD> [--page <NUMBER>] [--size <NUMBER>]
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--url <string>` | string | 必填 | — | 分享链接 URL（如 `https://pan.quark.cn/s/xxx`） |
| `--keyword <string>` | string | 必填 | — | 搜索关键词 |
| `--page <number>` | number | 选填 | `1` | 页码 |
| `--size <number>` | number | 选填 | `50` | 每页条目数 |

#### 成功出参

仅一行 `type: "result"`，无进度输出。

**result.data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `file_count` | number | 搜索结果数量 |
| `files` | array | 文件列表（字段同 `share-detail`） |

**成功示例**：

```jsonl
{"code":0,"msg":"成功","data":{"file_count":2,"files":[{"fid":"file1","filename":"report.pdf","size":2097152,"file_type":"1","category":4,"created_at":1700000000,"updated_at":1700000000,"share_fid_token":"token1"}]},"action":"share-search","type":"result"}
```

#### 失败出参

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -1001 | --page 必须为正整数 | `--page` 参数不是正整数 |
| -1002 | --size 必须为正整数 | `--size` 参数不是正整数 |
| -1003 | 搜索分享文件失败 | SDK `searchShareFiles` 返回 `status !== 0`，`msg` 附带 SDK 返回的 `errno` 和 `error_info` |
| -1004 | 无效的分享链接 URL | `--url` 参数不是合法的夸克网盘分享链接 |
| -1005 | 获取分享令牌失败 | 内部调用 `getShareDetail` 获取 stoken 失败 |

**失败示例**：

```jsonl
{"code":-1001,"msg":"--page 必须为正整数","data":{},"action":"share-search","type":"result"}
```

```jsonl
{"code":-1003,"msg":"搜索分享文件失败: errno=41008, message=stoken invalid","data":{},"action":"share-search","type":"result"}
```

```jsonl
{"code":-1004,"msg":"无效的分享链接 URL: invalid-url","data":{},"action":"share-search","type":"result"}
```
