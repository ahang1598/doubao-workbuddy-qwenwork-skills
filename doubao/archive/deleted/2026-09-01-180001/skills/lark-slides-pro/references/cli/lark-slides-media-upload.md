# slides +media-upload（上传本地图片到飞书幻灯片）

把本地图片上传到指定演示文稿的 drive 媒体库，返回 `file_token`。**返回的 token 作为 `<img src="...">` 的值塞进 slide XML 即可显示图片。**

## 命令

```bash
# 直接传 xml_presentation_id
lark-cli slides +media-upload \
  --file ./pic.png \
  --presentation slidesXXXXXXXXXXXXXXXXXXXXXX

# 传 slides URL 也行
lark-cli slides +media-upload \
  --file ./chart.png \
  --presentation "https://xxx.feishu.cn/slides/slidesXXXXXXXXXXXXXXXXXXXXXX"

# 传 wiki URL（CLI 自动 wiki.spaces.get_node 解析为真实 token，校验 obj_type=slides）
lark-cli slides +media-upload \
  --file ./pic.png \
  --presentation "https://xxx.feishu.cn/wiki/wikcnXXXXXX"

# 预览（不实际上传）
lark-cli slides +media-upload --file ./pic.png --presentation $PRES_ID --dry-run
```

## 返回值

```json
{
  "file_token": "boxcnXXXXXXXXXXXXXXXXXXXXXX",
  "file_name": "pic.png",
  "size": 12345,
  "presentation_id": "slidesXXXXXXXXXXXXXXXXXXXXXX"
}
```

- **`file_token`**：把它写进 `<img src="...">`
- **`file_name` / `size`**：上传文件元信息
- **`presentation_id`**：解析后的真实 `xml_presentation_id`（wiki URL 解析后会变化）

> 上面展示的是 `.data` 的内容；实际输出是 `{"ok":true,"data":{...}}` 信封，所以取值路径是 **`.data.file_token`**（不是顶层 `.file_token`）。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--file` | 是 | 本地图片路径，**必须是 CWD 内的相对路径**（如 `./pic.png`）。**最大 20 MB**（slides upload API 不支持分片上传）。**仅支持 png / jpeg / gif / bmp / tiff / webp** |
| `--presentation` | 是 | `xml_presentation_id`、`/slides/<token>` URL，或 `/wiki/<token>` URL |

> [!IMPORTANT]
> **路径必须在 CWD 内**：`--file /abs/path/x.png` 或 `--file ../up/x.png` 会被 CLI 拒绝（报 `unsafe file path`）。如果素材在别的目录，先 `cd` 过去再执行。

## 使用流程

### 给已有幻灯片加带图新页

```bash
# 1) 上传图片（内置 --jq 取 token，$() 只截 stdout；不要加 2>&1，否则 stderr 进度行会污染 token）
TOKEN=$(lark-cli slides +media-upload \
  --file ./pic.png \
  --presentation $PRES_ID \
  --jq '.data.file_token')

# 2) 把 file_token 写进这一页 XML，存成文件后用 --slide @file 提交
cat > page-01.xml <<XML
<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>
  <img src="$TOKEN" topLeftX="100" topLeftY="100" width="320" height="180"/>
</data></slide>
XML
lark-cli slides +add-slide --presentation "$PRES_ID" --slide @page-01.xml
```

### 新建带图幻灯片

统一走两步：先 `+create` 建空白幻灯片，再对每张图 `+media-upload` 拿 `file_token`，最后 `+add-slide` 把 token 写进 `<img src>`——与上面「给已有幻灯片加带图新页」同一套流程，只是幻灯片是新建的空白 deck。

> `+create --slides` 的 `@<本地路径>` 占位符可一步上传+替换，但**不作为默认路径**（一步法已不推荐）；如需了解见 [+create 文档](lark-slides-create.md#本地图片path-占位符)。

### 给已有幻灯片的已有页加图

拿到 `file_token` 后走 [`+replace-slide`](lark-slides-replace-slide.md) 的 `block_insert`，不用搬原 XML、不改 `slide_id`、不打乱页序：

```bash
PRES_ID=xxx
SID=yyy       # 要加图的那一页

# 1) 上传图片拿 file_token
TOKEN=$(lark-cli slides +media-upload \
  --file ./pic.png --presentation $PRES_ID --jq '.data.file_token')

# 2) block_insert 到页末（或用 insert_before_block_id 指定插入位置）
lark-cli slides +replace-slide \
  --presentation "$PRES_ID" --slide-id "$SID" \
  --parts "$(jq -n --arg token "$TOKEN" \
    '[{action:"block_insert",insertion:("<img src=\""+$token+"\" topLeftX=\"500\" topLeftY=\"100\" width=\"200\" height=\"150\"/>")}]')"
```

注意事项：

1. **`<img>` 坐标避开现有元素** —— 先读现有元素 bbox 挑空白区；空间不够就先用 `block_replace` 挪动/缩小现有元素后再放图
2. **`<img>` 的 `width:height` 对齐原图比例** —— 比例不一致会被裁剪，参见 [xml-schema-quick-ref.md](../xml/xml-schema-quick-ref.md) `<img>` 说明

## 工作原理

`+media-upload` 内部调用 `POST /open-apis/drive/v1/medias/upload_all`（单次上传，最大 20 MB），固定使用：

- `parent_type=slide_file`（slides 后端唯一接受的取值，已实测验证）
- `parent_node=<xml_presentation_id>`

**不要尝试用 `slides_image`、`slide_image` 等 parent_type**——后端会返回 1061001 / 1061002 错误。这是 slides 的特殊约定。

## 常见错误

| 错误码 | 含义 | 解决方案 |
|--------|------|----------|
| 1061002 | params error / 不支持的 parent_type | 不要用原生 API 自己拼 parent_type；用 `+media-upload` 即可 |
| 1061004 | forbidden：当前用户对该演示文稿无编辑权限 | 确认当前用户对目标幻灯片有编辑权限；无权限时根据错误响应引导用户解决 |
| 1061044 | parent node not exist | `--presentation` 给的 token 不对，或不是 slides 类型 |
| 403 | 权限不足 | 检查 `docs:document.media:upload` scope；wiki URL 还需要 `wiki:node:read` |

## 相关命令

- [+create](lark-slides-create.md) — 新建幻灯片（两步创建第一步：建空白 deck）
- [+replace-slide](lark-slides-replace-slide.md) — 给已有页加图 / 换图（`block_insert` / `block_replace`）
- [slides +add-slide](lark-slides-add-slide.md) — 逐页添加幻灯片页面（拿到 file_token 后塞进 XML）
