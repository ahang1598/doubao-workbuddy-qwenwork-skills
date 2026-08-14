# 排障

本文件覆盖 lark-slides 的 **XML 语法 / 接口调用 / 错误码** 排障与失败处理（`invalid param`、创建失败、空白页、3350001 等报错）。其它类别的问题请转对应文档：

- **XML 里的排版/布局/元素问题**（文本溢出、重叠、越界、空白/破损页等）→ [validation-xml.md](validation-xml.md)。
- **视觉问题**（对比度、图片裁切、间距、风格一致性等）→ [validation-visual.md](validation-visual.md)。

## 失败处理顺序

遇到 `invalid param`、某一页创建失败、页面空白或布局错乱时，按顺序排查；其中第 2–4 项也是创建或替换前应先自检的点：

1. **保住现场**：记录 `xml_presentation_id`，不要假设失败就代表什么都没创建；先用 `slides +xml-get --output <CWD 内相对路径>` 回读到本地文件（`--output` 必填），确认已有哪些页写入、问题出在哪一页。
2. **未转义字符**（`invalid param` / 3350001 最常见原因）：正文和标题里的 `&`、`<`、`>` 不能裸写（`Q&A -> Q&amp;A`，`<` / `>` 写成 `&lt;` / `&gt;`）；属性值里的裸 `&` 也要写成 `&amp;`（如 URL `a=1&b=2 -> a=1&amp;b=2`）。
3. **结构与引号**：标签闭合、属性引号安全（XML 属性、shell 引号、JSON 包装之间不互相打断）；`<slide>` 下只放 `<style>`、`<data>`、`<note>`，文本都在 `<content>` 内。
4. **图片路径**：`<img src="@...">` 只在 `+create --slides` 的支持链路里自动上传并替换；直接调 `xml_presentation.slide.create` 必须先用 `+media-upload` 拿到 `file_token`。
5. **疑似 shell 截断**：用 `--slides '[...]'` 且内容缺失或异常时，切换两步创建——先 `slides +create`，再用 `xml_presentation.slide.create` 逐页添加。
6. **修复并复验**：局部问题用 `+replace-slide` 块级修正；整页结构要重做时用 `slide.delete` 旧页 + `slide.create` 新页。修复后重新回读或截图确认。

## 常见错误码

| 错误码 / 信号 | 含义 | 解决方案 |
|--------------|------|----------|
| 400 XML 格式错误 | XML 语法错误 | 检查标签闭合、属性引号、特殊字符转义 |
| 400 请求包装错误 | `--data` 未按 schema 包装 | 检查是否传入 `xml_presentation.content` 或 `slide.content` |
| 创建成功但页面空白 / 内容缺失 / 布局错乱 | 常见于 `--slides '[...]'` 的 shell 转义或长参数传递问题 | 改用两步创建，并在创建后立即读取 XML 验证 |
| 403 权限不足 | scope 或文档权限不匹配 | 确认 scope 和文档权限；无权限时根据错误响应引导用户解决 |
| 404 演示文稿不存在 | `xml_presentation_id` 不正确或无权限 | 检查 token；wiki URL 需先解析真实 `obj_token` |
| 404 幻灯片不存在 | `slide_id` 不正确 | 重新读取 presentation 或 slide，确认最新 ID |
| 400 无法删除唯一幻灯片 | 演示文稿至少保留一页 | 先创建新页，再删除旧页 |
| 1061002 媒体上传 params error | slides 媒体上传参数不符合约定 | 用 `slides +media-upload`，不要手拼原生 `medias/upload_all`；slides 唯一可用 `parent_type` 是 `slide_file` |
| 1061004 forbidden | 当前用户对演示文稿无编辑权限 | 确认当前用户对目标幻灯片有编辑权限 |
| 3350001 | XML 非 well-formed、XML 结构不符合服务端要求，或 replace 片段问题 | 优先检查未转义字符；replace 场景再看 `block_id` 和 `<content/>`；改写回读来的页时检查有没有 `<undefined>`，它只能导出不能写入 |
| 3350002 | `revision_id` 大于当前版本 | 用 `-1` 取当前版本；要取真实版本号从 CLI 响应里读（`+xml-get --json` 的返回，或单页读的 `data.revision_id`），回读落盘的 XML 文件里没有这个值 |
| validation: unsafe file path | `--file` 给了绝对路径或上层路径 | `--file` 必须是 CWD 内相对路径；先 `cd` 到素材目录再执行 |

## 命令专属参考

- 图片上传、`@path` 占位符、`file_token`：见 [lark-slides-media-upload.md](../cli/lark-slides-media-upload.md) 和 [lark-slides-create.md](../cli/lark-slides-create.md)。
- 块级替换、`block_id`、3350001 replace 细节：见 [lark-slides-replace-slide.md](../cli/lark-slides-replace-slide.md)。
- 原生 `slide.create` 包装、`before_slide_id` 和 jq 模板：见 [lark-slides-xml-presentation-slide-create.md](../cli/lark-slides-xml-presentation-slide-create.md)。
