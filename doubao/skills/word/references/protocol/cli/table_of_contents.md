---
keyword: table_of_contents
---

**功能**：自动目录插入、刷新、配置和删除

# 本地 Word：自动目录领域命令

## 按需读取

水印另查 `watermark`。

写入公共参数见 `local-update`。

自动目录使用 `lark-cli docs +local-update` 的领域命令及对应 option，不写 DocxXML 标签。仅通过 `lark-cli` 调用，不构造包含 `document_id`、`format`、`revision_id`、`command_params` 等字段的内部请求，也不直调私有接口。

命令须提供顶层 `--revision-id`，接受 `-1` 或非负安全整数；优先传入同一次读取返回的文档版本，不得放进业务 option。后续操作需要新 ID 或文档版本时再读；完整规则见 revision 规则。

---

## 自动目录 `table_of_contents`

`--table-of-contents-option` 接受以下业务参数：

| action | 必填 | 语义 |
|---|---|---|
| `insert` | `parent_id,position`；`config` 可选 | 在 parent children 的 0 基位置插入，position 为非负安全整数；无标题时允许空目录 |
| `update` | `target` | 通常重建指定的目录。没有可用的目录来源时，只刷新现有 `PAGEREF` 页码 |
| `configure` | `target,config` | 把配置应用到指定的目录，再重建目录 |
| `remove` | `target` | 删除指定的目录 |

`configure` 会重新扫描来源并重建条目、书签和页码。`update` 默认执行同样的完整重建；仅当完整生成唯一因
`no-source-items` 阻塞时，运行时才自动改用现有 PAGEREF 页码更新链路，保留目录条目与字段结构。当前 CLI
没有独立的“仅更新页码” action，不猜测对应 action/flag。完整重建保留各级目录的段落样式 ID。
原条目的手工内容、直接格式和列表不会原样迁移。用户要求保留这些内容时，如果只能完整重建，就保留原目录并说明限制。

`update`、`configure` 和 `remove` 都通过 `target` 指定目录。`target` 支持下面两种写法。顶层不接受 `target_id` 或 `locator`。

- content-control 自动目录使用读取结果中的 `target_id`，写作 `target={"kind":"content_control","target_id":"<Fetch 返回的 target_id>"}`。
- field-only 自动目录使用目标目录中任意一个 `PAGEREF` 域的 ID，写作 `target={"kind":"field_marker","field_id":"<任一目录内 PAGEREF field id>"}`。

field-only 目录没有 content-control `target_id`，服务端会用 `field_id` 唯一反查所属 outer TOC field。`field_id` 在多个 story 中歧义、没有 TOC 祖先或目录结构不可安全 splice 时整次拒绝。field-only `configure` 读取现有 metadata、应用 patch 后重建；field-only `remove` 按 S/P/E 边界删除并保留范围外正文。

`insert` 可省略 `config`；默认包含页码、右对齐、点引导符、1～3 级标题和超链接，并使用 Heading/outline 来源。显式传入 `config` 时必须包含 `include_page_numbers,right_align_page_numbers,tab_leader,upper_heading_level,lower_heading_level`。`configure` 的 `config` 是非空 patch，缺席字段保留现值；若 patch 同时给出上下 heading level，则必须满足 upper ≤ lower。level 为 1..9 的整数，`tab_leader=none|dot|hyphen|middleDot|underscore`，可选 `tab_leader_edited,use_hyperlinks`。两种形态若传 `source`，都必须完整提供 `use_heading_styles,use_outline_levels,style_mappings`；每个 mapping 的 `style_name` 非空白，按去除首尾空白、连续空白折为一个空格、转小写后判重，去除首尾空白后的名称禁止双引号、逗号、换行，`level` 为 1..9 的整数。开关字段均为 boolean。

目录来源包含正文顶层 `RD` 域时，`update/configure` 会按文档顺序读取被引用的本地 DOCX，并可能逐文件请求
用户授权。外部标题使用各自文档的分页和字符样式生成普通目录结果，不在当前文档伪造 bookmark/PAGEREF。
远程 URL、缺失文件、拒绝授权、循环引用、超限或读取期间主文档变化都会 fail closed；不要绕过授权、改写
引用路径或把外部页码替换为当前文档页码。

```bash
lark-cli docs +local-update --doc "<token>" \
  --revision-id "<revision_id_from_same_fetch>" \
  --command table_of_contents \
  --table-of-contents-option '{"action":"insert","parent_id":"<parent_id>","position":0,"config":{"include_page_numbers":true,"right_align_page_numbers":true,"tab_leader":"dot","upper_heading_level":1,"lower_heading_level":3}}'
```

更新已有 content-control 目录：

```bash
lark-cli docs +local-update --doc "<token>" \
  --revision-id "<revision_id_from_same_fetch>" \
  --command table_of_contents \
  --table-of-contents-option '{"action":"update","target":{"kind":"content_control","target_id":"<target_id>"}}'
```

更新 field-only 目录：

```bash
lark-cli docs +local-update --doc "<token>" \
  --revision-id "<revision_id_from_same_fetch>" \
  --command table_of_contents \
  --table-of-contents-option '{"action":"update","target":{"kind":"field_marker","field_id":"<PAGEREF field id>"}}'
```

配置 field-only 目录：

```bash
lark-cli docs +local-update --doc "<token>" \
  --revision-id "<revision_id_from_same_fetch>" \
  --command table_of_contents \
  --table-of-contents-option '{"action":"configure","target":{"kind":"field_marker","field_id":"<PAGEREF field id>"},"config":{"include_page_numbers":false}}'
```

删除 field-only 目录：

```bash
lark-cli docs +local-update --doc "<token>" \
  --revision-id "<revision_id_from_same_fetch>" \
  --command table_of_contents \
  --table-of-contents-option '{"action":"remove","target":{"kind":"field_marker","field_id":"<PAGEREF field id>"}}'
```

content-control 目标必须是 `gallery=Table of Contents` 的目录控件；field-only 目标必须是可唯一反查 outer TOC 的 PAGEREF field。`update/configure` 要求可解析的自动目录 metadata 及所需来源；`remove` 不要求来源可刷新，但两种目标都必须能证明删除边界安全。`parent_id`、`target.target_id` 必须来自当前 CLI Fetch 的明确身份，`target.field_id` 必须来自同次主 DocxXML，不凭可见文字猜测；不要在 option 中加入 `TOC/PAGEREF/bookmark` 内部结构、`content`、`reference_map` 或其他宿主内部字段。操作顺序见 [Canvas 自动目录](../canvas-doc-toc.md)。

## 写前定位与边界

- **先核实读取契约**：使用带 ID 的 Fetch（`--detail with-ids|full`）读取目标范围；兼容的已有 content-control 自动目录会在 `data.command_result.table_of_contents` 返回 `target_id,parent_id`。该数组只覆盖本次可见范围；field-only 目录从同次 Fetch 的主 DocxXML 读取 PAGEREF `<field id>`，不得从可见目录文字猜 identity。
- content-control TOC 的 `target.target_id` 只能取自当前 Fetch 的 `data.command_result.table_of_contents`；更新、配置或删除时同时保留同项 `parent_id` 用于核对父子关系。插入需要目标 parent 的完整 children 顺序来计算 0 基 `position`；若当前响应未明确提供可用 parent 及其完整 children，则不试填 ID。
- 先完成会影响标题或分页的正文/布局修改，再重新读取身份并更新自动目录。

## 回执

目录命令的领域结果在 `data.command_result`。公共回执见 `local-update`。
