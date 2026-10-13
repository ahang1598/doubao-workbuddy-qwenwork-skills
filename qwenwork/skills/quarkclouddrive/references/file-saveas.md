# 转存分享链接（saveas）

将分享链接中的文件转存到自己的网盘。默认转存整个分享链接，也可通过 `--fid-list` 指定部分文件。用户只需传入完整的分享链接 URL，CLI 内部自动解析 pwd_id、获取 stoken，并在使用 `--fid-list` 时自动匹配 `share_fid_token`。SDK 内部自动以 1 秒间隔轮询任务状态，不限轮询次数，仅受 15 分钟超时控制。单次查询失败时记录日志并继续重试，不中断轮询。任务完成（status=2）时输出成功结果，任务失败（status=3）时输出错误信息。
## 入参

```bash
node scripts/quark-drive.cjs saveas --url <URL> [--fid-list <FIDS>] [--to-pdir-path <PATH>] [--passcode <CODE>]
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--url <string>` | string | 必填 | — | 分享链接 URL（如 `https://pan.quark.cn/s/xxx` 或带提取码 `https://pan.quark.cn/s/xxx?pwd=abcd`） |
| `--save-all` | boolean | 选填 | `true` | 转存整个分享链接（默认行为，与 `--fid-list` 互斥） |
| `--fid-list <string>` | string | 选填 | — | 指定文件 FID 列表，逗号分隔（与 `--save-all` 互斥，CLI 内部自动匹配 `share_fid_token`） |
| `--to-pdir-path <string>` | string | 选填 | — | 保存目录路径。不传时由 CLI 内部决定默认行为 |
| `--to-pdir-fid <string>` | string | 选填 | — | 保存目录 FID（高级选项，推荐使用 `--to-pdir-path`）。不传时由 CLI 内部决定默认行为 |
| `--passcode <string>` | string | 选填 | — | 提取码。私密分享链接需要提供。如果 URL 中已带 `?pwd=abcd`，可不传此参数（CLI 会自动解析 URL 中的提取码）；如果同时提供了 `--passcode` 和 URL 中的 `pwd` 参数，以 `--passcode` 为准 |

> **重要（面向 AI agent）**：`--to-pdir-path` 和 `--to-pdir-fid` 均为选填参数。当用户没有明确指定转存到哪个目录时，**严禁自行补充 `"0"`、`"根目录"` 或任何值**，必须省略这些参数。只有当用户明确说"保存到根目录"或提供了具体的目录 FID/路径时，才传入对应参数。`"0"` 代表根目录。
>
> **指定目录的处理流程**：当用户指定了转存目标目录（如"保存到 XX 文件夹"）时，agent **必须**按以下步骤执行：
> 1. 先阅读搜索命令文档（[references/file-search.md](references/file-search.md)），调用 `search` 命令搜索该目录
> 2. 从搜索结果中找到目标目录的 `fid`
> 3. 将该 `fid` 作为 `--to-pdir-fid` 参数传入 `saveas` 命令
> 4. 如果搜索不到该目录，则**不传** `--to-pdir-fid` 和 `--to-pdir-path`，走 CLI 内部默认逻辑，并告知用户未找到指定目录、文件已转存到默认位置

**示例**

```bash
# 最简用法：转存整个分享链接（默认行为，无需指定目录参数）
node scripts/quark-drive.cjs saveas --url "https://pan.quark.cn/s/abc123"

# 转存到指定路径
node scripts/quark-drive.cjs saveas --url "https://pan.quark.cn/s/abc123" --to-pdir-path "/我的文件/下载"

# 转存指定文件（不指定目录）
node scripts/quark-drive.cjs saveas --url "https://pan.quark.cn/s/abc123" --fid-list fid1,fid2

# 带提取码的私密分享链接（提取码在 URL 中）
node scripts/quark-drive.cjs saveas --url "https://pan.quark.cn/s/abc123?pwd=abcd"

# 带提取码的私密分享链接（通过 --passcode 参数传入）
node scripts/quark-drive.cjs saveas --url "https://pan.quark.cn/s/abc123" --passcode "abcd"

# 显式使用 --save-all（效果等同于不传）
node scripts/quark-drive.cjs saveas --url "https://pan.quark.cn/s/abc123" --save-all
```

## 成功出参

输出 NDJSON，仅一行 `type: "result"`，无进度输出。`code` 为 `0` 表示转存成功：

```jsonl
{"code":0,"msg":"成功","data":{"task_id":"xxx","task_type":17,"status":2,"save_as":{"to_pdir_fid":"0","to_pdir_name":"根目录"},"save_path":"网盘根目录"},"action":"saveas","type":"result"}
```

> **agent 须知**：
> - `code` 为 `0` 时表示转存成功，此时 `data` 中包含任务详情和保存目录信息
> - `code` 不为 `0` 时表示转存未成功，agent **必须**将 `msg` 字段的内容告知用户，并终止后续任务，禁止忽略错误继续执行

**result 行 data 字段**（成功时）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 异步任务 ID |
| `task_type` | number | 任务类型（17=转存） |
| `status` | number | 任务状态（成功时为 2） |
| `save_as.to_pdir_fid` | string | 保存目标目录 FID |
| `save_as.to_pdir_name` | string | 保存目标目录名称 |
| `save_path` | string | 保存目标目录的完整路径（含目录自身名称，以 `"夸克网盘/"` 为前缀，如 `"夸克网盘/我的文件/下载"`；根目录时为 `"网盘根目录"`）。路径解析失败时不返回该字段 |

**任务状态码**：

| 状态码 | 含义 |
|--------|------|
| 0 | 待处理 |
| 1 | 处理中 |
| 2 | 完成 |
| 3 | 失败 |
| 4 | 暂停 |

**转存成功时的人类可读输出**：

转存成功时，CLI 会通过 stderr 输出人类可读的提示信息（仅 `--verbose` 模式可见），告知用户转存结果和目标目录：

```
✔ 转存完成！
保存目录 FID: <to_pdir_fid>
保存目录名称: <to_pdir_name>
```

在转存成功后，应使用 result 行中的 `save_as.to_pdir_name` 字段，告知用户转存结果，例如：

> 转存成功！文件已保存到「根目录」。

## 失败出参

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -1101 | --fid-list 和 --save-all 互斥 | 同时提供了 `--fid-list` 和 `--save-all` |
| -1104 | 分享管理器实例不存在 | SDK 分享管理器初始化失败 |
| -1105 | 转存操作失败 | SDK `saveAsWithTrace` 返回 `status !== 0` 且 errno 不匹配 -1107 的兜底错误（如 saveAs 接口失败、任务轮询超时、指定的 fid 无效等） |
| -1106 | 无效的分享链接 URL | `--url` 参数不是合法的夸克网盘分享链接 |
| -1107 | 获取分享令牌失败 | SDK 内部调用 `getShareDetail` 获取 stoken 失败（SDK errno=-1107） |
| -1108 | （已废弃）指定的 fid 在分享详情中找不到对应的 share_fid_token | SDK 现在采用尽力匹配模式，找不到 fid_token 的 fid 会被跳过并直接请求服务端，不再在客户端报错 |
| 32003 | 网盘空间已满 | 用户网盘存储空间不足，无法转存。服务端透传错误码，需提示用户清理空间或升级容量 |
| 32004 | 网盘空间已满 | 同 32003，用户网盘存储空间不足。服务端透传错误码，需提示用户清理空间或升级容量 |

> **agent 须知**：当 `code` 为 `32003` 或 `32004` 时，表示用户网盘空间已满，agent 应明确告知用户"网盘空间不足，请清理空间或升级容量后重试"，**不要重试转存操作**。
