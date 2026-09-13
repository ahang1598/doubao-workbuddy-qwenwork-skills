# drive +fetch

把 Drive 文件（上传的 PDF/Word/Excel/zip/图片/音视频等文件）读取为 Markdown。Drive 文件的 URL 有两种形态：云盘中的 `/file/` URL，和知识库节点映射的 wiki URL；两种都可直接传入 `--url`，wiki 自动解包，无需先执行 `drive +inspect`。

本版本只开放 File 读取：传入 docx / sheet / base / slides / minutes 等在线文档类型会直接返回校验错误并提示改用对应实体 skill（lark-doc / sheet / lark-base / ppt / lark-meeting）；wiki 解包后不是 Drive 文件时同样报错，错误里附解析出的 `resource: {…}`（真实 type / token / 标题），可据此直接切换 skill，不用重新解包。

## 什么时候用它，什么时候用别的

| 目标 | 用什么 |
|---|---|
| 把 Drive 文件读取为 Markdown 速览 | `drive +fetch` |
| 获取原始文件字节并保存到本地 | `drive +download` |
| 需要 PDF / HTML / 图片等预览版式产物 | `drive +preview` |
| 读取 Drive 上的原生 `.md` 文件 | [`lark-markdown`](../../lark-markdown/SKILL.md) 的 `markdown +fetch` |
| 读取在线文档（docx / sheet / base / slides / minutes） | 对应实体 skill（lark-doc / sheet / lark-base / ppt / lark-meeting） |

## 命令

```bash
# 传 URL（推荐）：/file/ 路径自动识别
lark-cli drive +fetch --url "https://xxx.feishu.cn/file/boxcnxxx"

# wiki 链接背后是 Drive 文件：直接传 wiki URL，自动解包
lark-cli drive +fetch --url "https://xxx.feishu.cn/wiki/wikcnxxx"

# 裸 token 必须显式 --type
lark-cli drive +fetch --token boxcnxxx --type file
```

## 参数

| 参数 | 必填 | 说明 |
|---|---|---|
| `--url` | 二选一 | 文件 URL 或 wiki URL（推荐） |
| `--token` + `--type` | 二选一 | 裸 token 需 `--type file`（wiki 节点 token 用 `--type wiki`） |
| `--embed-max-rows` | 否 | 正文中的表格每表最多 N 行（默认 50，0 = 不限），超了截断并提示 |
| `--paginate` | 否 | 请求服务端分页；完整读取失败或超时（超大文件）时用它分页重试 |
| `--page-token` | 否 | 传入上次返回的 `next_page_token` 续读，同时进入分页模式 |
| `--page-size` | 否 | 每页大小提示（0 = 服务端默认），同时进入分页模式 |

## 输出

默认输出遵循 CLI JSON envelope：`{ok, identity, data: {...}, ...}`。正文按交付方式出现在 `content` 或 `content_file`；以下字段均位于 `data`：

- `data.content`：内联 Markdown 内容；超大正文自动落盘时不返回
- `data.content_file` / `data.content_preview`：完整读取的超大正文自动落盘时，完整内容位于 `data.content_file.path`，`content_preview` 仅用于确认内容
- `data.content_delivery_hint` / `data.content_inline`：自动落盘不支持或写入失败时正文保持内联，`content_delivery_hint` 给出后续恢复方式
- `data.resource`：`{type, title, url, token, selector, update_time, source}`；`source` 仅 wiki 输入出现，记录解包前的 wiki 节点（`node_token` / `space_id`）
- `data.has_more` / `data.next_page_token`：服务端分页时标记是否还有内容并给出续读游标
- `data.warnings`：提示信息，英文原文（如分页游标缺失提示）

正文之外，统一内容读取链路会默认请求当前已进入内容索引的评论，并追加在 `## 评论` 下；评论索引异步更新，刚创建的评论可能暂未出现，需要实时评论状态时使用 `drive +list-comments`。

失败时信封为 `{ok:false, identity, error:{type, subtype, message, hint, log_id, …}}`；`error.hint` 给出恢复命令，末尾单独一行 `resource: {type,title,url,token,selector,source}`，与成功时的 `data.resource` 同形，可用 `jq -r .error.hint | sed -n 's/^resource: //p' | jq` 取出。

## 内容读取的边界（拿不全时怎么办）

- **完整内容交付**：默认读取返回 `data.content_file` 时，直接对 `path` 本地 read / search；`content_preview` 不能替代完整正文，也不要再次 fetch 同一资源。出现 `data.content_delivery_hint` 时按 hint 恢复，不要把可能截断的内联内容当作完整正文。
- **超大文件**：完整读取失败或超时时用 `--paginate` / `--page-size` 分页重试；后续将 `data.next_page_token` 传给 `--page-token`。若 `data.has_more=true` 但 `data.next_page_token` 为空，说明结果不完整并停止，不要静默宣称已覆盖全文。
- **表格被截断**：正文中的 GFM 表超过 `--embed-max-rows`（默认 50 行）会截断，尾部写「还有 X 行」；要不截断的全量表格，设 `--embed-max-rows 0`。
- **`drive +fetch` 的正文足够回答时直接使用**；正文不足且需要原始文件字节时用 `drive +download`，需要核对 PDF / HTML / 图片等预览版式时用 `drive +preview`。
