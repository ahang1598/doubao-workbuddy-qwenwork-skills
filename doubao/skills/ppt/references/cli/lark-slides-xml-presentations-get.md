# slides +xml-get / xml_presentations get

## 用途

读取飞书幻灯片演示文稿或指定单页的 XML；默认同时取得服务端 lint 报告，用于原稿基线与写入后复核。

## Shortcut

文件保存在当前工作目录 `<CWD>` 下，命令中的 `./readback.xml` 即 `<CWD>/readback.xml`；`<CWD>` 不是要创建的目录名或直接传入 CLI 的参数。示例文件名按任务/页面区分，避免覆盖已有文件。

使用 `slides +xml-get` shortcut，把纯 XML 保存到本地文件，并另存完整 stdout 响应和 stderr，避免长报告被终端截断。get 默认返回 lint 检测报告。

```bash
lark-cli slides +xml-get \
  --presentation "slides_example_presentation_id" \
  --output ./readback.xml \
  --json > ./readback-response.json \
  2> ./readback-error.json
```

先检查本次命令是否成功及完整响应的 `ok`，再用当前 Skill 下的 `scripts/lint_inspect.py --input ./readback-response.json` 读取 lint 检测报告摘要，按 `--details` 分页读完相关问题，避免大报告被截断。完整参数和状态说明见 [validation-xml.md](../workflow/validation-xml.md)。原稿基线使用独立文件名保存，不被之后的 `readback` 覆盖；具体见 [validation-xml.md](../workflow/validation-xml.md)。

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

`--slide-id` 和 `--slide-number` 都是单值参数；重复 `--slide-id` 不能读取多页，可能只取最后一个值。多页需逐页调用并保存各自响应，或一次读取全文后用 `xml_inspect.py --input ./readback.xml --mode raw --slide-id "<sid-1>" "<sid-2>"` 本地提取。后者返回的 raw XML 不包含服务端 lint，报告仍从整份读取响应中按页面对应。

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

上述四种 JSON 返回模式默认附带报告，报告均位于 **`data.issues`**，不写入 XML 文件，也不嵌在 `xml_presentation` 或 `slide` 对象里。报告结构为：

```text
data.issues                         对象，直接读取，不用 fromjson
├── schema_version / tool
├── summary                         slide_count、各级数量、status 等
├── document                        errors / warnings / infos
├── issues                          可能仅镜像文档级问题，不能当作全稿列表
└── slides[]                        slide_number、status、element_count
    ├── errors / warnings / infos   分级问题列表
    └── issues                      同一批问题的合并列表，勿重复计数
```

问题的 `element_ids` / `elements`、`target`、`related_objects`、`measurement` 等按实际存在的字段读取；不能要求每条问题都有全部定位和测量字段。报告可含 `file`、`slide_size` 等辅助字段，但它们不能替代外层的 presentation ID、版本和读取范围。

`ok: true` 仅表示读取成功；即使报告 `summary.status` 为 `blocked`，XML 仍可正常保存。报告缺失不等于零问题，不能只读 summary；完整读取和前后比较规则见 [validation-xml.md](../workflow/validation-xml.md)。单页报告通过请求/响应的 slide ID 关联页面，不假定报告内部页码就是整稿页码；整份报告与同次 XML 页序对应。

### 直接输出 XML 到管道

此模式不返回 lint 报告，不用于建立 lint 基线或完成验收：

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
4. 优先使用默认返回 lint 的 `+xml-get`；必须走原生 API 时，先以最新 schema 确认是否支持及如何传递 lint 参数，不猜测字段名。需要过滤信息时，先保留完整响应，再用 `jq` 提取，避免丢失报告
5. 不要在普通工作流中把完整 XML 打到终端；用 `slides +xml-get --output` 保存文件
6. 必须先用 XML 解析器解析回读结果；命名空间（`xmlns`）从根元素实际读取，不要硬编码否则匹配不到元素

## 相关命令

- [slides +create](lark-slides-create.md) - 创建空白幻灯片
- [slides +add-slide](lark-slides-add-slide.md) - 添加幻灯片页面
- [slides +delete-slide](lark-slides-delete-slide.md) - 删除幻灯片页面
