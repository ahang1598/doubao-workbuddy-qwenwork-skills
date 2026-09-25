# slides +add-slide（向已有演示文稿追加/插入单页）

向已有演示文稿添加**一页**。这是两步创建流程的第二步：先 `+create` 建空壳，再逐页 `+add-slide`；也用于给已有 PPT 追加新页。

`--presentation` 接受 token / `/slides/` URL / `/wiki/` URL（wiki 自动解析），`--slide` 直接收 XML（支持 `@file` 和 stdin，复杂 XML 走文件可绕开 shell 转义），`<img src="@./local.png">` 占位符自动上传并替换成 `file_token`。

## 命令

```bash
# 追加到末尾（XML 直接作为参数）
lark-cli slides +add-slide \
  --presentation "$PID" \
  --slide '<slide xmlns="https://www.larkoffice.com/sml/2.0"><data></data></slide>'

# XML 从文件读（推荐：避免 shell 转义和长参数截断）
lark-cli slides +add-slide \
  --presentation "$PID" \
  --slide @page3.xml

# XML 从 stdin 读
cat page3.xml | lark-cli slides +add-slide --presentation "$PID" --slide -

# 插到某页之前
lark-cli slides +add-slide \
  --presentation "$PID" \
  --slide @cover.xml \
  --before-slide-id "$SID"

# wiki 链接（CLI 自动 wiki.spaces.get_node 解析，并校验 obj_type=slides）
lark-cli slides +add-slide \
  --presentation "https://xxx.feishu.cn/wiki/wikcnXXXXXX" \
  --slide @page3.xml

# 预览请求，不实际写入
lark-cli slides +add-slide --presentation "$PID" --slide @page3.xml --dry-run
```

## 参数

| 参数 | 必需 | 说明 |
|------|------|------|
| `--presentation` | 是 | `xml_presentation_id`、`/slides/` URL 或 `/wiki/` URL |
| `--slide` | 是 | 一个完整的 `<slide>...</slide>` 文档；支持字面量、`@file`、stdin `-` |
| `--before-slide-id` | 否 | 插到该 `slide_id` 之前；**不传就是追加到末尾** |
| `--revision-id` | 否 | 演示文稿版本号，默认 `-1`（最新）；传具体版本号做乐观锁 |
| `--dry-run` | 否 | 打印将要发起的请求（含图片上传步骤），不写入 |
| `--no-lint` | 否 | 跳过服务端版式校验（默认开启）；只能在当前页已被拦、完整报告已读完且符合[单页例外规则](../workflow/validation-xml.md)时单独使用，禁止多页共用或自动重试附加 |

`@file` 路径**必须在 CWD 内**（如 `@./plan/page3.xml`）；绝对路径和 `../` 会被拒绝并报 `unsafe file path`。

## 本地图片：`@路径` 占位符

XML 里写 `<img src="@./chart.png" .../>`，CLI 会：先把每个不重复的本地文件上传到这份演示文稿（`parent_type=slide_file`），再把 `src` 替换成返回的 `file_token`，最后才提交页面。

占位符路径按**执行命令时的 CWD** 解析，跟 `--slide @file` 所在目录无关；`@./assets/x.png` 找的是 `$PWD/assets/x.png`。

```bash
lark-cli slides +add-slide \
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
| `issues` | 仅在**页面已写入成功**且服务端有发现时返回，干净提交时不返回，不影响本次调用的成功状态。两种来源：提交的 XML 里有服务端不支持的标签/属性被丢弃（**页面内容与提交的不一致**），或未达阻断级的版式校验发现。按实际类型读取：对象/数组直接读，JSON 字符串解码后读，普通文本原样读；完整读取全部发现，立即回读并截图核验，真实问题须修复，不能按普通告警忽略 |

### 返回字段与处理

返回 JSON 的外层 `ok` 表示调用是否成功，`identity` 表示调用身份；成功时业务字段位于 `data`，失败时错误信息位于 `error`。按以下字段判断结果并处理 lint 发现。

| 当次响应 | 读取与处理 |
|---|---|
| `ok: true`，未附问题发现 | 从 `data` 记录 ID、版本等业务字段，继续流程 |
| `ok: true`，有 `data.issues` | 页面已写入；对象/数组直接读，JSON 字符串先解码，普通文本完整读。逐条处理发现，按验证流程回读与截图；不能因成功而忽略 |
| `ok: false`，`error.code: 4000153` | 被拒页面未写入；对 `error.message` 的完整 JSON 字符串解码，读完报告后修复并开启 lint 重提 |
| 其他失败或返回不完整 | 读完整 `error` 或诊断，按实际原因处理；不能只读 `data` 并把缺失字段默认成零问题 |

返回的是 lint 报告对象时，先看 `summary` 中的 `error_count`、`warning_count`、`info_count` 和 `status`，再读 `document.errors/warnings/infos` 和 `slides[].errors/warnings/infos` 的全部问题；`slides[].issues` 可能是分级列表的镜像，不能重复计数；合并列表中的额外发现也须读取，根 `issues` 不能当作全页列表。逐条读 `code`、`message`、实际存在的 `hint` 及定位/测量字段；`element_ids` 可能为空，需继续看 `elements`、`target.xml_path` 或 schema 的 `path`。单页报告内部 `slide_number: 1` 不一定是整稿第 1 页，关联本次请求/响应的 `slide_id`。

字符串长度不是问题数，`summary` 或前几百字符也不是完整问题正文。报告过大或工具输出截断时，先检查是否已有该次完整响应文件；有文件时可用 `lint_inspect.py` 分页读取，只有截断文本时无法恢复遗漏内容，不能据此认定问题已全部处理。使用 `--no-lint` 后的成功不代表校验通过；异常、长报告和单页例外规则见 [validation-xml.md](../workflow/validation-xml.md)。

## 常见错误

| 现象 | 原因 | 解决 |
|------|------|------|
| `--slide is not a single complete <slide> document` | 传了 `<presentation>` 整份 XML，或多个 `<slide>` 拼在一起 | 一次只传一页，根元素必须是 `<slide>` |
| `--slide cannot be empty` | `@file` 指向空文件，或 stdin 没内容 | 检查文件内容 |
| 3350001 | XML 结构/转义有问题；**或 `--before-slide-id` 不是有效 `slide_id`** | 优先改用 `--slide @file` 绕开 shell 转义；插页失败先 `+xml-get` 回读确认 `slide_id`；再按 [workflow/error-handling.md](../workflow/error-handling.md) 排查 |
| 4000153 `xml lint blocked` | 服务端版式校验拒绝了这一页，页面未写入 | 按 [validation-xml.md](../workflow/validation-xml.md) 解析并读完 `error.message` 的完整报告，修复后开启 lint 重提 |
| 1061004 / 403 | 当前身份对这份 PPT 没有编辑权限 | 检查是否拥有 `slides:presentation:update` 或 `slides:presentation:write_only` scope；wiki 链接另需 `wiki:node:read`，`@` 占位符另需 `docs:document.media:upload` |
