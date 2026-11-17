---
keyword: media-upload
---

**功能**：上传本地或网络图片并取得可写资源 token

# 本地 Word 图片上传

本文只负责为图片更新取得资源 token；插入、替换与属性更新查询 `media-update`。

`--parent-node` 使用当前本地 Word 的 Canvas token；不要用文档路径、图片 block ID 或其他文档 token 顶替。

## 图片来源

插入或替换图片时，用用户指定的来源。只改图片属性时沿用原 `src`。

| 图片来源 | 本地 Word 处理方式 | 禁止做法 |
|---|---|---|
| 当前本地 Word fetch 返回的图片 token，或本次上传已经返回的 `file_token` | 直接写入 `<img src="...">`，跳过上传 | 不要重复上传同一图片 |
| 用户给出明确的本地图片路径 | 使用 `lark-cli docs +media-upload --file <path>`，取得 `file_token` 后更新文档 | 不要把文件路径直接写入 `src` |
| 用户给出 HTTP/HTTPS 图片 URL | 先下载为可访问的本地图片文件，再执行上传和更新 | 不要把 URL 写入 `src`，也不要改用在线文档的 `<img href>` |
| 用户只说明“剪切板里的图”“刚复制的截图” | 告知当前 `lark-cli docs +media-upload` 不支持剪切板，请用户提供可访问的本地图片文件 | 不要调用 `lark-cli docs +media-insert --from-clipboard`，也不要猜测图片路径 |
| 上下文没有唯一、明确的图片来源 | 只问一个澄清问题，确认使用已有 token、本地文件还是网络 URL | 不要扫描目录、猜测最近图片或任意选择文档内图片 |

补充规则：

- 只有 token 明确来自当前本地 Word fetch 或一次已成功完成的上传时，才能省略上传；不要根据 token 外形猜测资源有效性。
- 从 URL 下载失败、文件不存在或剪切板没有可用本地文件时，停止写入并说明缺失条件；不要静默换来源。

## 上传

```bash
lark-cli docs +media-upload \
  --file "./image.png" \
  --parent-type docx_image \
  --parent-node "<token>"
```

调用方仍传公开参数值 `docx_image`；CLI 识别本地 Word token 后自动把下游 `parent_type` 映射为 `office_docx_file`。使用当前 Canvas 的 token，映射由 CLI 处理。

成功结果中的关键字段位于 `data`：

```json
{
  "data": {
    "file_token": "file_xxx",
    "file_name": "image.png",
    "size": 12345
  }
}
```

- `data.file_token` 是后续 `<img src="...">` 使用的资源 token。
- 文件大于 20MB 时命令会自动改用分片上传。

## 失败处理

- 上传失败：不要执行 `lark-cli docs +local-update`。
- 上传成功后保留 `file_token`；写入文档用 `media-update`。
- 客户端不可达或本地 Word 已关闭：停止当前 CLI 流程，不要把活动文档 `<token>` 当本地路径。

## 明确禁止

- 不使用 `lark-cli docs +media-insert`；
- 不把普通文件路径或网络 URL 写入 `src`；
- 图片资源必须通过 `src` 引用；不使用在线文档的附件类型、`align` 或 `file-view`；
- 不把图片上传和文档更新并行执行；
- 不根据 token 外形自行判断对象类型或构造 `office_docx_file` 私有请求。
