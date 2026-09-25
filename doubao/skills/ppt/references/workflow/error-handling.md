# 排障

本文件覆盖 lark-slides 的 **XML 语法 / 接口调用 / 错误码** 排障与失败处理（`invalid param`、创建失败、空白页、3350001 等报错）。其它类别的问题请转对应文档：

- **XML 里的排版/布局/元素问题**（文本溢出、重叠、越界、空白/破损页等）→ [validation-xml.md](validation-xml.md)。
- **视觉问题**（对比度、图片裁切、间距、风格一致性等）→ [validation-visual.md](validation-visual.md)。

## 先读当次写入结果

创建/加页/更新/替换返回 JSON，外层 `ok` 表示调用是否成功。`ok: true` 时业务字段位于 `data`；未附问题发现时，记录其中的 ID/版本并继续。`ok: true` 带 `data.issues`，或创建返回 `data.slide_issues` 时，逐条读完：对象/数组直接读，JSON 字符串解码，普通文本原样读。`ok: false` 的 `4000153` 则读 `error.message`，将完整字符串解码为报告。

报告先看 `summary` 的状态与数量，再读 `document.errors/warnings/infos` 和 `slides[].errors/warnings/infos` 的问题正文；页面 `issues` 可能镜像分级列表，不重复计数。逐条读 `code`、`message`、实际存在的 `hint`、定位和测量字段。不能用 `data` 分支的默认空值掩盖 `error`，也不能用字符串长度、消息前缀或 shell/解析脚本退出码判断通过。

本地解析器在成功响应后报错，不等于写入失败。先检查已返回的原文，避免再次创建/更新来“看看返回结构”。报告过大或工具截断时，取回该次已有完整输出或响应文件，用 `lint_inspect.py` 分页；无法取得且写入状态不明时只读回读确认状态，不能把当前回读当成之前的拒绝报告。完整返回结构见 [validation-xml.md](validation-xml.md)。

## 失败处理顺序

**先区分首次提交保护与参数错误**：当前页首次写入直接携带 `--no-lint`，仍可能被服务端 lint 阻断，具体机制与处理要求见 [validation-xml.md](validation-xml.md)「修复与单页例外」。按实际响应分流：

- 返回服务端 lint 阻断报告（如 `4000153` 或检测报告中的 `status: blocked`）：完整读取报告，按问题修复并恢复默认开启 lint 的提交方式。不能仅因携带 `--no-lint` 仍被拦，就改判为参数不支持；也不能自动原样重试 `--no-lint`。
- CLI 明确提示 `unknown flag` / `unrecognized arguments` 等不识别 `--no-lint`：按 CLI 参数或版本问题排查。仅有 `invalid param` 等泛化错误不足以认定参数不支持，应继续读取完整错误原因。

遇到响应解析失败、必要 ID 缺失、`invalid param`、某一页创建失败、页面空白或布局错乱时，先保留并完整读取原始响应，不得假定成功或直接重试。若为 `4000153`，先按 [validation-xml.md](validation-xml.md) 二次解析 `error.message` 并读完全部发现，再修复和开启 lint 重提；报告截断、解析失败或结果过期不能当作无问题，更不能据此跳过。其他错误按以下顺序排查，其中第 2–4 项也是创建或替换前应先自检的点：

1. **保住现场**：记录已返回的 ID。单页明确被 lint 拒绝时直接按报告修复；多页创建可能部分成功、必要 ID 缺失或结果不明确时，不要假设失败就代表什么都没创建，先用 `slides +xml-get --output <CWD 内相对路径>` 回读到本地文件（必须使用 `--output`），确认已有哪些页写入、问题出在哪一页。
2. **未转义字符**（`invalid param` / 3350001 最常见原因）：正文和标题里的 `&`、`<`、`>` 不能裸写（`Q&A -> Q&amp;A`，`<` / `>` 写成 `&lt;` / `&gt;`）；属性值里的裸 `&` 也要写成 `&amp;`（如 URL `a=1&b=2 -> a=1&amp;b=2`）。
3. **结构与引号**：标签闭合、属性引号安全（XML 属性、shell 引号、JSON 包装之间不互相打断）；`<slide>` 下只放 `<style>`、`<data>`、`<note>`，文本都在 `<content>` 内。
4. **图片路径**：`<img src="@...">` 占位符由 `+create` 和 `+add-slide` 处理，会自动上传并替换成 `file_token`。
5. **疑似 shell 截断**：用 `--slides '[...]'` 且内容缺失或异常时，切换两步创建——先 `slides +create`，再用 `slides +add-slide --slide @<文件>` 逐页添加。
6. **修复并复验**：局部问题用 `+replace-slide` 块级修正；整页结构要重做时优先用 `+update-slide` 原地覆盖，保留 ID 和页序。确需重新创建时，先明确目标位置：插到某页之前须传 `--before-slide-id <目标页ID>`，只有目标位置为末尾才省略。新页写入并回读验证成功后，再删除旧页。修复后重新回读确认内容和页序，必要时截图。

**非 lint 失败不能靠跳过 lint 解决**：超时、限流、路径或参数错误、`RewriteSlideBySXSD`、SVG 命名空间和渲染错误等，应按实际原因处理；重试默认开启 lint，禁止自动附加或沿用 `--no-lint`。若例外写入仍失败，重新检查原先的“误报”判断，不能把该参数保留为后续默认值。结果不明确时先回读确认，避免重复写入。

## 回读 lint 的结果与异常

`+xml-get --output` 的 XML 文件与响应 JSON 分开保存；先检查本次退出状态、stdout 和 stderr 中的完整响应，再使用 XML。失败后路径上可能仍留有旧 XML，不能据此认定本次成功。

| 情况 | 处理 |
|---|---|
| `ok: true`，`data.issues` 是有效报告，含 error 或 `summary.status: blocked` | XML 读取成功，报告指出已存内容的问题；不是写入拒绝，不要仅因此重复上一次写入。按 [validation-xml.md](validation-xml.md) 读完文档级及页面级发现，与原稿基线比较并修复本次新增/加重的真实问题 |
| `ok: true`，但 `data.issues` 缺失、类型错误、截断或报告不完整 | 不能记为 lint 通过；重新读取完整响应，并用 `lint_inspect.py` 查看诊断。仅拿到 XML 可用于查看实际状态，不能替代基线/验收报告 |
| 读取失败，或明确报告 lint 超时/执行失败/部分失败 | 按原始错误处理并补读对应范围，未检查的页或规则不能按零问题处理；不同版本或范围的结果不能拼成同一次完整校验 |

对已保存的完整回读响应，用 `scripts/lint_inspect.py --input <完整响应文件>` 先查看 lint 检测报告摘要，再分页读详情；脚本自动区分回读对象与写入拒绝的 JSON 字符串。`no_report` / `partial` / `api_error` 均不能当作通过；普通错误和无法识别的文本保留在详情中，处理方法见 [validation-xml.md](validation-xml.md)。回读问题或异常均不能作为自动添加 `--no-lint` 的理由；已保存的原稿基线不被重试结果覆盖。

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
| 4000153 `xml lint blocked` | 服务端版式校验拒绝了本次写入，被拒的页面未写入（`+create` 逐页提交，之前的页面保留） | `error.message` 是 JSON 字符串，按 [validation-xml.md](validation-xml.md) 二次解析并读完完整报告，修复后开启 lint 重验。成功响应可能含 `data.issues`，也须逐条处理；`--no-lint` 仅按该文档的单页例外规则使用 |
| validation: unsafe file path | `--file` 给了绝对路径或上层路径 | `--file` 必须是 CWD 内相对路径；先 `cd` 到素材目录再执行 |

## 命令专属参考

- 图片上传、`@path` 占位符、`file_token`：见 [lark-slides-media-upload.md](../cli/lark-slides-media-upload.md) 和 [lark-slides-create.md](../cli/lark-slides-create.md)。
- 块级替换、`block_id`、3350001 replace 细节：见 [lark-slides-replace-slide.md](../cli/lark-slides-replace-slide.md)。
- 追加/插入单页、`--before-slide-id` 和 `--slide @file`：见 [lark-slides-add-slide.md](../cli/lark-slides-add-slide.md)。
- 删除单页：见 [lark-slides-delete-slide.md](../cli/lark-slides-delete-slide.md)。
