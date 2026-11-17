---
keyword: media-preview
---

**功能**：预览 Canvas 图片资源

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

### 预览图片

用户要求“看一下、预览、确认图片内容”时使用 `lark-cli docs +media-preview`。提取 `src` 后执行：

```bash
lark-cli docs +media-preview \
  --token "file_xxx" \
  --output "./preview-image"
```

预览完成后向用户展示或说明实际输出路径。明确要求“下载、保存、导出原图”时见 `media-download`。

### 输出路径与失败处理

- `lark-cli docs +media-preview` 和 `lark-cli docs +media-download` 的 `--output` 不带扩展名时，均会根据响应类型自动补全。
- token 为空：重新 fetch 目标图片，不能猜测 token。
- 预览返回 `HTTP 403` 或资源不可见：检查当前上下文对该素材的访问权限；不要改用文档 ID 下载。
- `lark-cli docs +media-download` 可能返回 `HTTP 403` 的权限错误，此时可回退尝试 `lark-cli docs +media-preview`：使用同一 `<img src>` 资源 token。预览成功不代表原图下载成功；用户明确要求下载原图时，仍须说明下载因权限失败，不得把预览结果冒充下载结果。
- 输出路径已存在：遵循当前命令的覆盖规则，不得未经用户允许覆盖已有文件。
