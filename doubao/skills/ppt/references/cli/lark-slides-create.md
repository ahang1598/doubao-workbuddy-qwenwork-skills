# slides +create（创建飞书幻灯片）

创建一个新的飞书幻灯片演示文稿。

- **标准做法：统一两步创建**——先用 `+create`（不带 `--slide` / `--slides`）建**空白幻灯片**，再用 [`+add-slide`](lark-slides-add-slide.md) 逐页添加，每次只提交一个 `<slide>`。
- 禁止：从完整 `<presentation>` XML 解析、拆分、重序列化后再生成提交 payload；提交源直接就是单页 `<slide>` XML。
- `--slides` 一步加页仍受支持（下文有说明），但**不再作为默认路径**：复杂 XML 直接塞命令行时，中文、引号、特殊字符容易发生 shell 转义或截断，统一走两步更稳。

## 命令

```bash
# 创建空白幻灯片
lark-cli slides +create --title "项目汇报"

# 创建幻灯片 + 添加 slide 页面
lark-cli slides +create --title "项目汇报" --slides '[
  "<slide xmlns=\"https://www.larkoffice.com/sml/2.0\"><data><shape type=\"text\" topLeftX=\"80\" topLeftY=\"80\" width=\"800\" height=\"120\"><content textType=\"title\"><p>封面</p></content></shape></data></slide>",
  "<slide xmlns=\"https://www.larkoffice.com/sml/2.0\"><data><shape type=\"text\" topLeftX=\"80\" topLeftY=\"80\" width=\"800\" height=\"120\"><content textType=\"title\"><p>第二页</p></content></shape></data></slide>"
]'

# 预览（不执行）
lark-cli slides +create --title "项目汇报" --slides '[...]' --dry-run
```

复杂内容建议按页保存 XML，再用 `jq --rawfile` 组装 `--slides` 参数：

```bash
lark-cli slides +create --title "项目汇报" \
  --slides "$(jq -n \
    --rawfile s1 .lark-slides/project/slide-01.xml \
    --rawfile s2 .lark-slides/project/slide-02.xml \
    '[$s1, $s2]')"
```

`--rawfile` 会把文件内容作为字符串读入 JSON，自动处理 XML 中的引号和换行；不要手动拼接带大量转义符的 JSON 字符串。

## 返回值

工具成功执行后，返回一个 JSON 对象，包含以下字段：

- **`xml_presentation_id`**（string）：演示文稿的唯一标识符，后续添加页面时需要此 ID
- **`title`**（string）：演示文稿标题
- **`url`**（string，重要）：演示文稿的在线链接。present_files 工具只接受 `url`，缺这个字段就无法交付
- **`revision_id`**（integer）：演示文稿版本号
- **`slide_ids`**（string[]，可选）：仅传 `--slides` 时返回，成功添加的页面 ID 列表
- **`slides_added`**（integer，可选）：仅传 `--slides` 时返回，成功添加的页面数量
- **`images_uploaded`**（integer，可选）：仅 `--slides` 中含 `@<本地路径>` 占位符时返回，已上传的去重后图片数量

> [!IMPORTANT]
> 不传 `--slide` / `--slides` 时，`slides +create` 只创建一个**不含任何页面（0 页）**的空演示文稿——不会自带任何默认页或空白页（回读时 `<presentation>` 里没有 `<slide>`）。创建后需要使用 `slides +add-slide` 逐页添加 slide 内容。
>
> 传了 `--slide` / `--slides` 时，CLI 先创建空白演示文稿，再逐页添加页面。如果某一页添加失败，CLI 会停止并报错，已创建的演示文稿和已添加的页面会保留。
>
> **不要擅自执行 owner 转移。** 如果用户需要把 owner 转给自己，必须单独确认。

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--title` | 否 | 演示文稿标题（不传则默认 "Untitled"） |
| `--slide` | 否 | 一页 `<slide>` XML，或 `@路径`；可重复，最多 10 次，出现顺序即页序 |
| `--slides` | 否 | 页面 XML 的 JSON 字符串数组，最多 10 个；支持 `@文件` 和 `-`（stdin） |

两者二选一，同时传会报错。超过 10 页：先用 `+create` 建空白幻灯片，再用 [`+add-slide`](lark-slides-add-slide.md) 逐页添加。

## `--slides` 参数格式

```json
[
  "<slide xmlns=\"https://www.larkoffice.com/sml/2.0\">...第1页XML...</slide>",
  "<slide xmlns=\"https://www.larkoffice.com/sml/2.0\">...第2页XML...</slide>"
]
```

JSON string 数组，每个元素是一页 slide 的完整 XML。CLI 内部负责包装成 API 所需的 `{"slide": {"content": "..."}}` 格式并逐页调用。

### 本地图片：`@<path>` 占位符

`<img>` 元素的 `src` 属性如果以 `@` 开头，CLI 会把它当作本地文件路径，自动上传到当前演示文稿，并把占位符替换为返回的 `file_token`。

```bash
lark-cli slides +create --title "图测试" --slides '[
  "<slide xmlns=\"https://www.larkoffice.com/sml/2.0\"><data><img src=\"@./assets/chart.png\" topLeftX=\"100\" topLeftY=\"100\" width=\"320\" height=\"180\"/></data></slide>"
]'
```

行为：

- 路径相对于**当前工作目录**（CWD）解析；**必须是 CWD 内的相对路径**（如 `./pic.png`、`./assets/x.png`）
- 同一份图被多次引用时**只上传一次**（按路径去重）
- `src` 不以 `@` 开头的会原样保留，但**只允许写 `slides +media-upload` 拿到的 `file_token`**；**禁止写 http(s) 外链 URL**：飞书 slides 渲染端不会代理外链图片，外链 src 通常显示破图。要用网图必须先用 `wget` 下载到 CWD 内、再走上传流程
- 单张图片最大 20 MB（slides upload API 不支持分片上传）
- 校验阶段就会检查所有占位符文件存在及大小；缺文件或超限直接报错，不会创建空白幻灯片占位
- 创空白幻灯片 → 上传所有图 → 替换 token → 逐页创建 slide，按这个顺序执行

> [!IMPORTANT]
> **路径必须在 CWD 内**：`@/abs/path/x.png` 或 `@../up/x.png` 这种会被 CLI 拒绝（报 `unsafe file path`）。如果素材在别的目录，先 `cd` 过去再执行。

### 给已有幻灯片加带图新页

`+create --slides` 只在新建幻灯片时使用 `@` 占位符。给已有幻灯片加带图新页要分两步（CLI 没封装这个组合）：

```bash
# 1) 上传图片
TOKEN=$(lark-cli slides +media-upload \
  --file ./pic.png --presentation $PRES_ID --jq '.data.file_token')

# 2) 把 file_token 写进这一页 XML，存成文件后用 --slide @file 提交
cat > page-01.xml <<XML
<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>
  <img src="$TOKEN" topLeftX="100" topLeftY="100" width="200" height="200"/>
</data></slide>
XML
lark-cli slides +add-slide --presentation "$PRES_ID" --slide @page-01.xml
```

## 创建后续步骤

不带页面参数创建时，`slides +create` 返回的 `xml_presentation_id` 用于后续操作：

```bash
# 第 1 步：创建空白幻灯片
PRES_ID=$(lark-cli slides +create --title "项目汇报" --jq '.data.xml_presentation_id')

# 第 2 步：添加页面（使用返回的 xml_presentation_id）
lark-cli slides +add-slide --presentation "$PRES_ID" --slide @page-01.xml
```

## 常见错误

| 错误码 | 含义 | 解决方案 |
|--------|------|----------|
| 400 | 参数错误 | 检查参数格式是否正确 |
| 403 | 权限不足 | 检查是否拥有 `slides:presentation:create` 和 `slides:presentation:write_only` scope |

## 相关命令

- [slides +add-slide](lark-slides-add-slide.md) — 逐页添加幻灯片页面
- [slides +xml-get](lark-slides-xml-presentations-get.md) — 读取幻灯片内容并保存到本地文件
