# slides +xml-get / xml_presentations get

## 用途

读取飞书幻灯片演示文稿或指定单页的 XML；用于理解原稿、定位编辑对象和核对实际内容；响应可能附带服务端 lint 报告，本流程不主动处理。

## Shortcut

文件保存在当前工作目录 `<CWD>` 下，命令中的 `./readback.xml` 即 `<CWD>/readback.xml`；`<CWD>` 不是要创建的目录名或直接传入 CLI 的参数。示例文件名按任务/页面区分，避免覆盖已有文件。

使用 `slides +xml-get` shortcut，把纯 XML 保存到本地文件，并另存完整 stdout 响应和 stderr，保留页面标识和版本。get 默认可能附带 lint 报告，无须另外读取。

```bash
lark-cli slides +xml-get \
  --presentation "slides_example_presentation_id" \
  --output ./readback.xml \
  --json > ./readback-response.json \
  2> ./readback-error.json
```

确认本次命令成功和响应的 `ok` 后读取 XML，记录页面标识与版本。原稿内容使用独立文件名保存，后续回读另存；不建立 lint 基线或调用 `lint_inspect.py`。

> [!IMPORTANT]
> 拿到 XML 后必须先用 XML 解析器解析。**命名空间（`xmlns`）要从根元素实际读取，不要硬编码或猜测，否则匹配不到元素。**

### 参数说明

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `--presentation` | string | 是 | 演示文稿的唯一标识符 |
| `--revision-id` | integer | 否 | 版本号，`-1` 表示最新版本 |
| `--output` | string | 否 | 纯 XML 保存路径，必须使用相对路径；保存元数据和 lint 报告仍在 stdout JSON 中。省略时 XML 在 JSON envelope 内返回 |
| `--raw` | flag | 否 | 直接把 XML 输出到 stdout，不包 JSON envelope；不能与 `--output`、`--jq` 或非 JSON `--format` 同时使用 |
| `--slide-id` | string | 否 | 只读取指定 `slide_id` 的单页 XML；不能与 `--slide-number` 或 `--remove-attr-id` 同时使用 |
| `--slide-number` | integer | 否 | 只读取指定的 1-based 页码；不能与 `--slide-id` 或 `--remove-attr-id` 同时使用 |
| `--remove-attr-id` | flag | 否 | 仅全文读取可用；移除 XML id 属性后读取，不适合后续精确块编辑 |
| `--json` | flag | 否 | `--format json` 的简写，json 为默认输出格式 |

`--slide-id` 和 `--slide-number` 都是单值参数；重复 `--slide-id` 不能读取多页，可能只取最后一个值。多页需逐页调用并保存各自响应，或一次读取全文后用 `xml_inspect.py --input ./readback.xml --mode raw --slide-id "<sid-1>" "<sid-2>"` 本地提取。后者返回 JSON，单页 XML 在 `.slides[].raw_xml`。

> [!IMPORTANT]
> `--output` 必须是**当前工作目录（CWD）内的相对路径**（如 `./readback.xml`）。传绝对路径或上级路径（如 `/tmp/x.xml`、`/dev/null`、`../up.xml`）会被拒绝，报 `--output must be a relative path within the current directory`。本流程沿用当前工作目录，以文件名区分任务和读取批次。

### 读取单页并保存

按页面 ID 和按页码二选一：

```bash
lark-cli slides +xml-get \
  --presentation "slides_example_presentation_id" \
  --slide-id "slide_example_id" \
  --output ./slide.xml \
  --json > ./slide-response.json \
  2> ./slide-error.json
```

单页 XML 根是 `<slide>`，可能不带 `xmlns` 和画布尺寸；用 XML 解析器按实际结构读取。当前 `xml_inspect.py` 要求 SML 命名空间，需要使用该脚本时优先读全文再提取目标页。

### Shortcut 返回结构

以下路径均相对于完整响应；`ok`、`identity` 在外层，业务字段在 `data`：

| 读取方式 | XML 所在位置 | `data` 中的定位/保存字段 |
|---|---|---|
| 全文，不带 `--output` | `data.xml_presentation.content` | `xml_presentation_id`、`revision_id`、`scope: "presentation"`；`xml_presentation` 内也含 `revision_id` |
| 单页，不带 `--output` | `data.slide.content` | `xml_presentation_id`、`revision_id`、`scope: "slide"`、`slide_id`；`slide` 内含 `slide_id`、`revision_id` |
| 全文，带 `--output` | 指定文件中的纯 XML | `content_saved: true`、`path`、`size`、`xml_presentation_id`、`revision_id`、`scope: "presentation"` |
| 单页，带 `--output` | 指定文件中的纯 XML | 同上，`scope: "slide"`，另有 `slide_id` |

按 `--slide-number` 读取时还会返回 `data.slide_number`；按 ID 读取时不要依赖该字段。`size` 是保存内容的字节数，返回的 `path` 可以是绝对路径，但传入 `--output` 仍须用相对路径。`revision_id` 从响应读取，不从 XML 推断。

JSON 响应可能在 `data.issues` 中附带服务端 lint 报告；本流程不展开、不分页、不比较该报告。`ok: true` 表示读取成功，页面内容与标识按上述路径获取。

### 直接输出 XML 到管道

此模式直接输出 XML，不返回报告；仅凭这一输出形式不能认定服务端关闭了 lint 计算：

```bash
lark-cli slides +xml-get \
  --presentation "slides_example_presentation_id" \
  --slide-number 1 \
  --raw
```

### 指定版本读取

```bash
lark-cli slides +xml-get \
  --presentation "slides_example_presentation_id" \
  --revision-id 10 \
  --output ./readback-r10.xml \
  --json
```

### 移除 XML id 属性后读取

```bash
lark-cli slides +xml-get \
  --presentation "slides_example_presentation_id" \
  --remove-attr-id \
  --output ./readback-no-id.xml \
  --json
```

## 底层原生命令形态

```bash
lark-cli slides xml_presentations get --params '<json_params>'
```

### 参数说明

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `--params` | JSON string | 是 | 路径参数与查询参数，结构以 schema 为准 |

### params JSON 结构

```json
{
  "xml_presentation_id": "slides_example_presentation_id",
  "revision_id": -1
}
```

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `xml_presentation_id` | string | 是 | 演示文稿的唯一标识符 |
| `revision_id` | integer | 否 | 版本号，`-1` 表示最新版本 |

### 返回值

成功时返回演示文稿的完整信息：

```json
{
  "ok": true,
  "identity": "user",
  "data": {
    "xml_presentation": {
      "presentation_id": "slides_example_presentation_id",
      "revision_id": 1,
      "content": "<presentation xmlns=\"...\" height=\"540\" width=\"960\">...</presentation>"
    }
  }
}
```

### 返回字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.xml_presentation.presentation_id` | string | 演示文稿唯一标识 |
| `data.xml_presentation.revision_id` | integer | 版本号 |
| `data.xml_presentation.content` | string | XML 格式的完整内容 |

### 常见错误

| 错误码 | 含义 | 解决方案 |
|--------|------|----------|
| 404 | 演示文稿不存在 | 检查 `xml_presentation_id` 是否正确 |
| 403 | 权限不足 | 检查是否拥有 `slides:presentation:read` scope，或是否有访问权限 |
| 400 | 参数格式错误 | 确保 `--params` 是合法的 JSON 字符串 |

### 注意事项

1. lark-slides 工作流默认使用 `slides +xml-get`；只有必须直接调底层 API 时，才使用
2. 直接调用底层 API 前，使用 `lark-cli schema slides.xml_presentations.get` 查看最新的参数结构
3. 返回的 XML 在 `data.xml_presentation.content` 字段中
4. 需要过滤信息时保留页面 ID、版本与 XML；不为获取 lint 报告追加请求。
5. 不要在普通工作流中把完整 XML 打到终端；用 `slides +xml-get --output` 保存文件
6. 必须先用 XML 解析器解析回读结果；命名空间（`xmlns`）从根元素实际读取，不要硬编码否则匹配不到元素

## 相关命令

- [slides +create](lark-slides-create.md) - 创建空白幻灯片
- [slides +add-slide](lark-slides-add-slide.md) - 添加幻灯片页面
- [slides +delete-slide](lark-slides-delete-slide.md) - 删除幻灯片页面
