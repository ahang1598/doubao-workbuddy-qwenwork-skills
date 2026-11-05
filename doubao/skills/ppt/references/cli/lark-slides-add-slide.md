# slides +add-slide（向已有演示文稿追加/插入单页）

向已有演示文稿添加**一页**。这是两步创建流程的第二步：先 `+create` 建空壳，再逐页 `+add-slide`；也用于给已有 PPT 追加新页。

`--presentation` 接受 token / `/slides/` URL / `/wiki/` URL（wiki 自动解析），`--slide` 直接收 XML（支持 `@file` 和 stdin，复杂 XML 走文件可绕开 shell 转义），`<img src="@./local.png">` 占位符自动上传并替换成 `file_token`。

## 命令

```bash
# 追加到末尾（XML 直接作为参数）
lark-cli slides +add-slide --no-lint \
  --presentation "$PID" \
  --slide '<slide xmlns="https://www.larkoffice.com/sml/2.0"><data></data></slide>'

# XML 从文件读（推荐：避免 shell 转义和长参数截断）
lark-cli slides +add-slide --no-lint \
  --presentation "$PID" \
  --slide @page3.xml

# XML 从 stdin 读
cat page3.xml | lark-cli slides +add-slide --no-lint --presentation "$PID" --slide -

# 插到某页之前
lark-cli slides +add-slide --no-lint \
  --presentation "$PID" \
  --slide @cover.xml \
  --before-slide-id "$SID"

# wiki 链接（CLI 自动 wiki.spaces.get_node 解析，并校验 obj_type=slides）
lark-cli slides +add-slide --no-lint \
  --presentation "https://xxx.feishu.cn/wiki/wikcnXXXXXX" \
  --slide @page3.xml

# 预览请求，不实际写入
lark-cli slides +add-slide --no-lint --presentation "$PID" --slide @page3.xml --dry-run
```

## 参数

| 参数 | 必需 | 说明 |
|------|------|------|
| `--presentation` | 是 | `xml_presentation_id`、`/slides/` URL 或 `/wiki/` URL |
| `--slide` | 是 | 一个完整的 `<slide>...</slide>` 文档；支持字面量、`@file`、stdin `-` |
| `--before-slide-id` | 否 | 插到该 `slide_id` 之前；**不传就是追加到末尾** |
| `--revision-id` | 否 | 演示文稿版本号，默认 -1 表示最新版本。指定版本号不应被视为已确认的并发保护；写入前仍须回读目标页，发现变化时重新合并修改。 |
| `--dry-run` | 否 | 打印将要发起的请求（含图片上传步骤），不写入 |
| `--no-lint` | 否 | 请求跳过服务端版式校验；本 Skill 写入页面时默认传入。服务端仍可能拒绝，实际结果以 `ok` 为准 |

`@file` 路径**必须在 CWD 内**（如 `@./plan/page3.xml`）；绝对路径和 `../` 会被拒绝并报 `unsafe file path`。

## 本地图片：`@路径` 占位符

XML 里写 `<img src="@./chart.png" .../>`，CLI 会：先把每个不重复的本地文件上传到这份演示文稿（`parent_type=slide_file`），再把 `src` 替换成返回的 `file_token`，最后才提交页面。

占位符路径按**执行命令时的 CWD** 解析，跟 `--slide @file` 所在目录无关；`@./assets/x.png` 找的是 `$PWD/assets/x.png`。

```bash
lark-cli slides +add-slide --no-lint \
  --presentation "$PID" \
  --slide '<slide xmlns="https://www.larkoffice.com/sml/2.0"><data><img src="@./chart.png" topLeftX="100" topLeftY="100" width="320" height="180"/></data></slide>'
```

- 文件不存在、不是普通文件、超过 20 MB，都在**调用任何接口之前**报错，不会留下半成品。
- 去重只在**单次调用内**生效：多页共用同一张图时，逐页循环会把它每页重传一次。这种图先用 [`+media-upload`](lark-slides-media-upload.md) 传一次，把 `file_token` 写进各页的 `src`。

## 成功输出

默认 JSON 响应如下，业务字段位于 `data` 内，例如新页面 ID 取自 `.data.slide_id`：

```json
{
  "ok": true,
  "identity": "user",
  "data": {
    "xml_presentation_id": "slides_example_presentation_id",
    "slide_id": "slide_example_id",
    "revision_id": 42,
    "before_slide_id": "slide_example_target_id",
    "images_uploaded": 1
  }
}
```

| 字段 | 说明 |
|------|------|
| `slide_id` | 新创建页面的唯一标识 |
| `issues` | 页面已写入成功时可能附带的发现；不改变成功状态，本流程不主动展开 lint 报告 |

### 返回字段与处理

本 Skill 写入默认传 `--no-lint`。`ok: true` 时记录 `data` 中的页面 ID、版本并继续；成功附带的 `issues` / `slide_issues` 不触发报告阅读、修复或复检。空壳创建成功仅说明文稿已创建。

`ok: false` 时保留失败状态并按 [error-handling.md](../workflow/error-handling.md) 处理。`4000153` 表示服务端仍拒绝提交，即使传了 `--no-lint` 也不能标记已写入；不自动重试或进入 lint 清零循环。返回不完整或状态不明时先只读确认，避免重复创建。

## 常见错误

| 现象 | 原因 | 解决 |
|------|------|------|
| `--slide is not a single complete <slide> document` | 传了 `<presentation>` 整份 XML，或多个 `<slide>` 拼在一起 | 一次只传一页，根元素必须是 `<slide>` |
| `--slide cannot be empty` | `@file` 指向空文件，或 stdin 没内容 | 检查文件内容 |
| 3350001 | XML 结构/转义有问题；**或 `--before-slide-id` 不是有效 `slide_id`** | 优先改用 `--slide @file` 绕开 shell 转义；插页失败先 `+xml-get` 回读确认 `slide_id`；再按 [workflow/error-handling.md](../workflow/error-handling.md) 排查 |
| 4000153 `xml lint blocked` | 服务端版式校验拒绝了这一页，页面未写入 | 保留未写入状态，按 [error-handling.md](../workflow/error-handling.md) 处理；不自动进入 lint 修复循环 |
| 1061004 / 403 | 当前身份对这份 PPT 没有编辑权限 | 检查是否拥有 `slides:presentation:update` 或 `slides:presentation:write_only` scope；wiki 链接另需 `wiki:node:read`，`@` 占位符另需 `docs:document.media:upload` |
