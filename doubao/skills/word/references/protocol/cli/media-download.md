---
keyword: media-download
---

**功能**：下载 Canvas 图片资源

## 图片资源读取

本页使用 Canvas `<img>` 的资源 token，不处理在线文档附件、`<source>`、画板或封面；不要传 `--type whiteboard`，也不要套用这些对象的下载规则。

### 获取图片 token

本地 Word 图片使用 `<img src="...">` 表达资源引用：

```xml
<img id="blk_image" src="file_xxx" width="800" height="600"/>
```

- `src` 是图片资源 token，不是本地路径或网络 URL。
- 按已读取的 [canvas-doc-fetch.md](../canvas-doc-fetch.md) 获取包含目标图片的最小范围；图片定位或后续还要编辑时使用 `--detail full`。
- 替换图片前使用 `--detail full`，同时保存图片 block ID 和所有未要求修改的属性。
- token 必须来自 `<img src>`，不能用文档 ID、图片 block ID、`document_id`、`obj_token` 或本地文件路径代替。

---

### 下载原图

用户明确要求“下载、保存、导出原图”时使用 `lark-cli docs +media-download`；只是查看内容时优先预览，用 `media-preview`。下载前明确输出目录或文件名，避免覆盖已有文件。提取 `src` 后执行：

```bash
lark-cli docs +media-download \
  --token "file_xxx" \
  --output "./downloaded-image"
```

成功后返回实际保存路径。

### 输出路径与失败处理

- `lark-cli docs +media-preview` 和 `lark-cli docs +media-download` 的 `--output` 不带扩展名时，均会根据响应类型自动补全。
- token 为空：重新 fetch 目标图片，不能猜测 token。
- 预览返回 `HTTP 403` 或资源不可见：检查当前上下文对该素材的访问权限；不要改用文档 ID 下载。
- 下载返回 `HTTP 403`：仅需查看内容时可改用预览；明确要求下载时，报告权限错误，不得把预览结果冒充下载结果。
- 输出路径已存在：遵循当前命令的覆盖规则，不得未经用户允许覆盖已有文件。
