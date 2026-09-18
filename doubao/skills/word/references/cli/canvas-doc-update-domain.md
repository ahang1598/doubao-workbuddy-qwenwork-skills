# 本地 Word：水印与自动目录领域命令

## 按需读取

先读本节前置条件、[写前定位与边界](#写前定位与边界)和[结果与验证](#结果与验证)，再按目标完整读取[自动目录](#自动目录-table_of_contents_update)或[水印](#水印-watermark_update)；两者都涉及则都读。每节读至下一同级或更高级标题，不能因示例相似而跳过配置、身份和保留约束。

前置按各自导航读取 [`canvas-doc-fetch.md`](canvas-doc-fetch.md#按需读取)、[`canvas-doc-update.md`](canvas-doc-update.md#按需读取)的公共契约与命中章节，并完整读取 [`canvas-doc-editing.md`](../workflows/canvas-doc-editing.md)。同轮已完整读取且仍可见的内容复用。

先确认当前子命令帮助公开所需 command 与 option；父级帮助不能证明支持。水印和自动目录使用 `docs +local-update` 的领域命令及对应 option，不写 DocxXML 标签。仅通过 `lark-cli` 调用，不构造包含 `document_id`、`format`、`revision_id`、`command_params` 等字段的内部请求，也不直调私有接口。

两类命令均须提供顶层 `--revision-id`，接受 `-1` 或非负安全整数；优先传入同一 Fetch checkpoint 的具体 revision，不得放进业务 option。写入、协同变化或版本冲突后重新 Fetch，使用当前身份与 revision；完整规则见 [revision 规则](canvas-doc-update.md#revision-规则)。

## 水印 `watermark_update`

`--watermark-option` 接受单层 JSON object，必填 `action=set_text|set_image|clear`：

- `set_text`：当前 CLI 在新建和更新时均要求完整提供 `text,font_family,font_size,bold,italic,underline,color,transparency,direction`。新建无其他要求时可显式使用思源黑体、`font_size="auto"`、三个强调开关 `false`、`color="#808080"`、`transparency=85`、`direction="horizontal"`。更新传最新 `target_id`，从写前读取保留全部非目标属性，只改用户要求的值；不得只提交 patch 或用新建默认值覆盖现值。`font_size` 为 `auto` 或 `1..1000` 数值，`transparency` 为 `0..100` 数值，强调开关为 boolean，`direction=horizontal|diagonal`。`text`、`font_family` 不得为空白；`color` 为不透明 Hex/RGB（允许 alpha=1 的等价写法），不接受 `auto`、命名色或真实透明色。
- `set_image`：当前 CLI 在新建和更新时均要求显式提供 `washout` 和 `scale`；新建还须提供 `box_token,name,mime_type`。新建无其他要求时可显式使用 `washout=true,scale="auto"`。更新传最新 `target_id`，仅改 washout 或 scale 时仍从基线补齐另一值，可省略资源三元组以保留原资源；替换资源时提供完整三元组。`washout` 为 boolean，`scale` 为 `auto` 或 `1..1000` 数值。
- 前端的缺省值和局部 patch 语义不等于当前 CLI 已放开参数省略。更新所需的完整非目标值无法从最新读取确定时，不猜默认值补齐，停止该操作并说明缺失证据。
- `clear` 必填 `clear_kind=all|text|image`；无匹配项是成功 no-op。
- 可选作用域为 `target_id,header_ids,text_target_ids,image_target_ids`。ID 必须来自当前 Fetch 结果并去重；不得从 DocxXML、文件路径或 block ID 推导水印 ID。省略作用域表示覆盖 root 与各节 header 引用，不等于只改当前页。

```bash
lark-cli docs +local-update --doc "<token>" \
  --revision-id "<revision_id_from_same_fetch>" \
  --command watermark_update \
  --watermark-option '{"action":"set_text","text":"机密","font_family":"Arial","font_size":48,"bold":false,"italic":false,"underline":false,"color":"#BFBFBF","transparency":60,"direction":"diagonal"}'
```

## 自动目录 `table_of_contents_update`

`--table-of-contents-option` 接受以下业务参数：

| action | 必填 | 语义 |
|---|---|---|
| `insert` | `parent_id,position`；`config` 可选 | 在 parent children 的 0 基位置插入，position 为非负安全整数；无标题时允许空目录 |
| `update` | `target` | 通常按判别目标重建；无标题源时仅刷新现有 PAGEREF 页码 |
| `configure` | `target,config` | 按判别目标应用配置后重建 |
| `remove` | `target` | 按判别目标删除目录 |

`configure` 会重新扫描来源并重建条目、书签和页码。`update` 默认执行同样的完整重建；仅当完整生成唯一因
`no-source-items` 阻塞时，运行时才自动改用现有 PAGEREF 页码更新链路，保留目录条目与字段结构。当前 CLI
没有独立的“仅更新页码” action，不猜测对应 action/flag。完整重建会保留当前目录各级实际引用的段落
style ID，但原条目的手工结果、direct formatting 和列表不会原样迁移。调用前核对该语义是否满足原稿及
用户的保留要求，调用后验收实际结果。

`update/configure/remove` 统一使用 `target` 判别联合，不再接受顶层 `target_id` 或 `locator`：

- content-control 自动目录仅支持使用 Fetch 返回的 `target_id` 更新：`target={"kind":"content_control","target_id":"<Fetch 返回的 target_id>"}`；
- field-only 自动目录：`target={"kind":"field_marker","field_id":"<任一目录内 PAGEREF field id>"}`。

field-only 目录没有 content-control `target_id`，服务端会用 `field_id` 唯一反查所属 outer TOC field。`field_id` 在多个 story 中歧义、没有 TOC 祖先或目录结构不可安全 splice 时整次拒绝。field-only `configure` 读取现有 metadata、应用 patch 后重建；field-only `remove` 按 S/P/E 边界删除并保留范围外正文。

`insert` 可省略 `config`；默认包含页码、右对齐、点引导符、1～3 级标题和超链接，并使用 Heading/outline 来源。显式传入 `config` 时必须包含 `include_page_numbers,right_align_page_numbers,tab_leader,upper_heading_level,lower_heading_level`。`configure` 的 `config` 是非空 patch，缺席字段保留现值；若 patch 同时给出上下 heading level，则必须满足 upper ≤ lower。level 为 1..9 的整数，`tab_leader=none|dot|hyphen|middleDot|underscore`，可选 `tab_leader_edited,use_hyperlinks`。两种形态若传 `source`，都必须完整提供 `use_heading_styles,use_outline_levels,style_mappings`；每个 mapping 的 `style_name` 非空白，按去除首尾空白、连续空白折为一个空格、转小写后判重，去除首尾空白后的名称禁止双引号、逗号、换行，`level` 为 1..9 的整数。开关字段均为 boolean。

目录来源包含正文顶层 `RD` 域时，`update/configure` 会按文档顺序读取被引用的本地 DOCX，并可能逐文件请求
用户授权。外部标题使用各自文档的分页和字符样式生成普通目录结果，不在当前文档伪造 bookmark/PAGEREF。
远程 URL、缺失文件、拒绝授权、循环引用、超限或读取期间主文档变化都会 fail closed；不要绕过授权、改写
引用路径或把外部页码替换为当前文档页码。

```bash
lark-cli docs +local-update --doc "<token>" \
  --revision-id "<revision_id_from_same_fetch>" \
  --command table_of_contents_update \
  --table-of-contents-option '{"action":"insert","parent_id":"<parent_id>","position":0,"config":{"include_page_numbers":true,"right_align_page_numbers":true,"tab_leader":"dot","upper_heading_level":1,"lower_heading_level":3}}'
```

更新已有 content-control 目录：

```bash
lark-cli docs +local-update --doc "<token>" \
  --revision-id "<revision_id_from_same_fetch>" \
  --command table_of_contents_update \
  --table-of-contents-option '{"action":"update","target":{"kind":"content_control","target_id":"<target_id>"}}'
```

更新 field-only 目录：

```bash
lark-cli docs +local-update --doc "<token>" \
  --revision-id "<revision_id_from_same_fetch>" \
  --command table_of_contents_update \
  --table-of-contents-option '{"action":"update","target":{"kind":"field_marker","field_id":"<PAGEREF field id>"}}'
```

配置 field-only 目录：

```bash
lark-cli docs +local-update --doc "<token>" \
  --revision-id "<revision_id_from_same_fetch>" \
  --command table_of_contents_update \
  --table-of-contents-option '{"action":"configure","target":{"kind":"field_marker","field_id":"<PAGEREF field id>"},"config":{"include_page_numbers":false}}'
```

删除 field-only 目录：

```bash
lark-cli docs +local-update --doc "<token>" \
  --revision-id "<revision_id_from_same_fetch>" \
  --command table_of_contents_update \
  --table-of-contents-option '{"action":"remove","target":{"kind":"field_marker","field_id":"<PAGEREF field id>"}}'
```

content-control 目标必须是 `gallery=Table of Contents` 的目录控件；field-only 目标必须是可唯一反查 outer TOC 的 PAGEREF field。`update/configure` 要求可解析的自动目录 metadata 及所需来源；`remove` 不要求来源可刷新，但两种目标都必须能证明删除边界安全。`parent_id`、`target.target_id` 必须来自当前 CLI Fetch 的明确身份，`target.field_id` 必须来自同次主 DocxXML，不凭可见文字猜测；不要在 option 中加入 `TOC/PAGEREF/bookmark` 内部结构、`content`、`reference_map` 或其他宿主内部字段。目录执行顺序与验收见 [`canvas-doc-toc.md`](../xml/canvas-doc-toc.md)；目标 action 不支持时停止并报告，不进入 OOXML 兜底。

## 写前定位与边界

- **先核实读取契约**：使用带 ID 的 Fetch（`--detail with-ids|full`）读取目标范围；兼容的已有 content-control 自动目录会在 `data.command_result.table_of_contents` 返回 `target_id,parent_id`。该数组只覆盖本次可见范围；field-only 目录从同次 Fetch 的主 DocxXML 读取 PAGEREF `<field id>`，不得从可见目录文字猜 identity。水印身份仍须由当前构建已公开的配套契约明确提供；没有时记录“领域读取接口未暴露”，并按主流程判断 OOXML。
- content-control TOC 的 `target.target_id` 只能取自当前 Fetch 的 `data.command_result.table_of_contents`；更新、配置或删除时同时保留同项 `parent_id` 用于核对父子关系。插入需要目标 parent 的完整 children 顺序来计算 0 基 `position`；若当前响应未明确提供可用 parent 及其完整 children，则不试填 ID。水印及 header 作用域 ID 同样只能取自当前 CLI 返回的明确领域身份。
- 图片水印新资源的 `box_token/name/mime_type` 必须来自当前已公开的资源流程；不把普通图片 `file_token` 自行转换或拼接为 `box_token`。这一资源要求不适用于保留原资源的属性更新。
- 先完成会影响标题、分页或共享 header 的正文/布局修改，再重新读取身份并更新 TOC/水印；后续改动使结果失效时重新纳入计划验收。

## 结果与验证

- 先检查进程退出码、`ok`、`result` 和 `warnings`，再从 `data.command_result` 读取领域命令结果。
- 水印写后回读受影响的 layout/page，核对目标及非目标 placements；需要验证视觉范围、位置或样式时使用宿主 PDF/可见页面证据，只有 XML/文本不得声称视觉通过。
- 自动目录写后回读目录所在范围及受影响页面，确认标题集合、条目顺序、层级、编号和页码；页码按文档显示编号核对，不能以物理页序号代替。条目或页码无法从回读确定时 Fetch `pdf` 补查；含页码的目录及引用若缺少当前分页证据，不标为已刷新。命令失败后的 PDF 只用于诊断或读取实际页码，不替代目录写入。
- 版本冲突、未知终态和回读失败统一遵循工作流的共享预算与停止条件；冲突重新 Fetch 并规划，不复用旧 ID 或 option，不另起无限重试。

===== 全文完 =====
