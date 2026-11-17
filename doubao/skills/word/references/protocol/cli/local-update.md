---
keyword: local-update
---

**功能**：Canvas 写入的通用参数、文档版本和回执

# 用 +local-update 改 Canvas

## 权限和目标

`--doc` 用当前 Canvas 的 `token`。客户端分别授权正文编辑和批注。只有批注权限（comments-only）时，只能用批注命令。客户端拒绝写入时，停止操作并向用户说明原因。

替换整块时，直接在当前完整 XML 上改，保留没动的属性、子节点和对象。摘要、裁剪后的 XML，以及带有 `BLOCK_REF_INCOMPLETE` 或 `BLOCK_ID_FABRICATED` 的结果都不能拿来做整块替换。新增块、表格坐标和对象 ID 按对应命令的说明填写。覆盖或删除前要明确用户指的是哪里。

## 内容格式与输入

`str_replace` 的 `--pattern` 和 `--content` 仅支持纯文本，不能创建、修改或删除公式；其中形似 `<equation>` 的标签会作为普通文字写入。block 写入与插入行列的 `--content` 固定使用 XML，并按 XML 公共规则及能力规范生成；不要传内容格式参数，也不要切换为其他格式。`block_delete` 和不插入内容的表格指令不接受 `--content`。

请求整体和每个字段的上限都是 256 KiB。整条请求按 JSON 转义后的 UTF-8 字节数算，单个字段按原始值算。XML 属性里的引号转义后占用更多字节，整条请求可能比原始 XML 大。超过任何一个上限，请求都会被拒绝。`--chart-option` 的 `data` 另有 192 KiB 上限，见图表说明。

`--content` 支持直接字符串、`@relative-file` 或 `-` 从 stdin 读取。`@` 后只接受当前工作目录内的相对路径，不接受绝对路径或 `../`；不要假定上一条 shell 的 `cd` 会延续。文件内容较长时，Mac/Linux 优先使用 stdin 重定向，避免 XML 引号和工作目录解析问题：

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_replace --block-id "<最新目标 ID>" \
  --content - < "/absolute/path/to/content.xml"
```

重定向路径由 shell 打开，`--content` 实际接收的是 `-`。使用 `@content.xml` 时，须在同一条调用中先进入文件所在目录。同一次调用只有一个参数可以从 stdin 读取；Windows 下使用等价的标准输入或文件参数写法。

## 参数

| 参数 | 必填 | 适用指令 | 说明 |
|---|---|---|---|
| `--doc` | 是 | 全部 | Canvas 上下文提供的 `<token>`；不接受普通 `.docx` 路径 |
| `--command` | 是 | 全部 | 指令名，见下方速查表及专项文档 |
| `--revision-id` | 视指令 | 图表数据指令禁止；其余见下表 | 顶层 CLI flag；指定写入所依据的文档版本，不能写进业务 option JSON |
| `--content` | 视指令 | 文本/块写入、插入行列 | 新内容；`str_replace` 传空字符串表示删除匹配文本；表格插入行列可省略 |
| `--pattern` | 视指令 | `str_replace` | 要匹配的旧文本 |
| `--block-id` | 视指令 | `str_replace`、block 与表格指令 | `str_replace` 可用它限定搜索范围，表格指令用表格 ID，批量删除见 `block_delete` |
| `--table-option` | 视指令 | `table`、`table_geometry` | 单层 JSON object；`action` 必填；支持内联、`@relative-file` 或 stdin |
| `--chart-option` | 视指令 | `chart_data` | 单层 JSON object；`action=create|replace` 必填 |
| `--watermark-option` | 视指令 | `watermark` | 单层 JSON object；完整字段见水印与目录专项文件 |
| `--table-of-contents-option` | 视指令 | `table_of_contents` | 单层 JSON object；`config`、`source` 可包含嵌套业务字段 |
| `--comment-option` | `comment` 必填 | `comment` | 单层 JSON object；字段查询 `comment` |
| `--field-option` | `field_update` 必填 | `field_update` | 单层 JSON object；字段查询 `field_update` |
| `--object-option` | `object` 必填 | `object` | 单层 JSON object；字段查询 `object` |
| `--revision-option` | `revision` 必填 | `revision` | 单层 JSON object；字段查询 `revisions` |
| `--style-option` | 视指令 | `style_*` | 单层 JSON object；JSON 中只放业务字段 |

### 文档版本（`--revision-id`）

| 指令 | 顶层 `--revision-id` |
|---|---|
| `style_update`、`style_apply`、`watermark`、`table_of_contents`、`comment`、`field_update`、`object`、`table_geometry` | 必填，接受 `-1` 或非负安全整数；优先使用本次读取返回的文档版本 |
| `chart_data` | 禁止传入；`action=replace` 使用 `expected_data_version` |
| `revision` | 禁止传入；接受/拒绝使用 `revisions` 返回的 `state_fingerprint`，模式/追踪控制不需要它 |
| 其余文本、block、表格指令 | 可选；省略或 `-1` 使用最近一次读取的版本，未读取时用当前状态；非负值指定版本 |

安全整数上限为 `9007199254740991`。要求传 `--revision-id` 的命令即使使用 `-1` 也要传这个参数，并按命令提供所需指纹和 `plan_token`。文档版本用于发现写入冲突。发生冲突，或前一笔写入改变了下一步依赖的 ID、坐标或 XML 时，重新读取受影响的范围。

修订模式下连续写入及待审保护查询 `revisions`；普通文档 revision 不能代替待审决议的 `state_fingerprint`。

`+local-update` 不接受在线文档专属参数。不要改用 `lark-cli docs +update` 补齐本地协议，也不要手工构造下游请求字段。

只使用本协议及命中专项明确列出的 flag、command 和 option；不要自行拼装请求。`--revision-id` 是顶层参数，不写进业务 option JSON。CLI 返回未知 command/flag 或有其他版本漂移证据时，查看受影响命令的当前 `--help` 并按恢复流程处理。

## 通用指令速查

| 指令 | 说明 | 必需参数 |
|---|---|---|
| `str_replace` | 替换搜索范围内全部非重叠纯文本命中；可用 `--block-id` 限定范围；`--content ''` 删除命中 | `--pattern` `--content` |
| `block_delete` | 原子删除一个或多个 block/inline object | `--block-id` |
| `block_insert_after` | 在指定 block 后插入一个或多个 XML block | `--block-id` `--content` |
| `block_replace` | 用 XML 整体替换目标 block | `--block-id` `--content` |
| `append` | 在尾随连续分节符前追加正文 XML | `--content` |

通用命令见上表；领域命令包括 `table`、`table_geometry`、`chart_data`、`style_update`、`style_apply`、`watermark`、`table_of_contents`、`comment`、`field_update`、`revision`、`object`。细分动作放在对应 option 的 `action`；仅使用当前 CLI 帮助暴露的入口。样式必须先 dry-run 再携带 plan token 提交。

**指令选择速查**：纯文本替换使用 `str_replace`，新文本仅继承命中范围的共有样式；只改一个 block 时传其最新 ID 限定范围。需要保留区间内不同样式时，使用 `block_replace`。完整 XML 无法表达必须保留的结构时，不得整块重写。

## 可寻址标签与可用命令

带 `id` 不等于支持全部命令。下表的 ID 来自 `+local-fetch` 的最新结果；XML 节点身份与合法结构查询 `xml:common`。

| 标签 | `block_replace` | `block_delete` | `block_insert_after` |
|---|---|---|---|
| `<p>`、`<h1>`～`<h9>`、`<li>`、`<img>`、`<chart>`、`<drawing>`、`<table>` | 支持 | 支持 | 支持 |
| 已有普通 `<content-control>` | 支持 | 不支持 | 不支持 |
| `<td>` / `<th>` | 支持 | 不支持 | 不支持 |
| TextBox、Note、Header/Footer story 内已由 Fetch 返回且专项允许编辑的 block | 支持 | 支持 | 支持 |
| `<layout-break/>` | 支持 | 支持 | 支持 |
| `<layout>` | 支持 | 不支持 | 不支持 |

- 单元格是表格结构的一部分，只能整格替换内容；增删行列、合并拆分和属性更新使用 `table + action`。
- `<layout>` 是文档级单例，只能用作 `block_replace` 目标；删除它或在它之后插入内容都没有语义。
- 普通块级 `<content-control>` 只能整体 `block_replace` 更新 children，且必须保留原 `id`；不支持创建、删除或属性编辑。目录与页码 gallery 控件不走通用 block 命令。
- `<tr>` 和 `<col>` 没有独立 Record，不可直接操作。
- `<bookmark-start>` / `<bookmark-end>`、`<tabs>` / `<tab>` 是宿主段落的一部分，不是独立 command target。删除含书签的 carrier 前，必须核对 `xml:p` 的跨 carrier 只读边界。
- `<page-break/>` 是行内对象，即使读取结果带 `id` 也不能作为 `--block-id` 直接删除、替换或后插入；要改它必须替换所属的 `<p>`、标题或 `<li>`。
- `<equation>` 没有 `id` 属性且不是 block；新增、修改、删除或复制公式时，使用宿主 carrier 的 block ID 和完整 XML。
- `<field>` 和 `<note-ref/>` 是宿主文本流的一部分，不是独立 command target；修改或删除时替换完整 carrier，并按 Field/Note 专项携带所需的 detached graph。新建题注也必须一次写入完整 `<p role="caption">`，不能先建普通段落再补角色。
- `<notes>` 是 detached collection，`<note>` / `<textbox>` 是 story owner，不是 command target；只操作其内部 Fetch 返回的 block ID。跨 body、note、textbox、header-footer story 使用 ID 会失败。
- `<drawing>` 虽位于宿主文本流，但拥有专用 inline-object target：更新、删除或在其后插入 Drawing 时，`--block-id` 使用最新 Fetch 返回的 drawing ID；替换 content 必须是同 ID 的单根 `<drawing>`，后插 content 必须是省略 ID 的单根 `<drawing>`。shape/textbox ID 不能作为 Drawing 命令目标；TextBox story 内部 block 的精确更新是另一条 story target 路径。
- standalone 图片按普通 block 处理；inline 图片的专用目标和 content 形状查询 `media-update`。
- `<layout-break/>` 支持 `block_delete`、`block_insert_after` 和 `block_replace`；`block_replace` 的 content 必须是同 ID 的单根 `<layout-break>`，其 root page 直接子节点约束见 XML 规范。
- `<li>` 可作命令目标，但 content 不能是裸 `<li>`，否则整次失败（`BLOCK_INVALID_PARENT`）。替换和插入须携带列表容器；替换原项还须保留原 `id`，省略会新建。合法形状查询 `xml:ol`。
- 列表容器定义本次写入后的同级集合。只替换一个列表项时，其他项可能分到独立容器，原编号也可能变化。仅修改一项的纯文本时，优先用该项 ID 限定 `str_replace`。如果单项替换会改变用户要求保留的编号或分组，改用能保留这些关系的方式。兄弟项 ID 不能放进单项替换载荷。

## Block ID 生命周期

**普通 block 的 `block_replace` 写回原 `id` 时保留身份；省略时可能新建 record，使原 ID 失效。** 不把此规则套到 inline 图片（原 record 原地更新）或 layout/layout-break（必须同 ID）等专项目标。以 fetch 返回的完整 XML 为底稿改写时 `id` 天然带着。inline 图片及 layout 等特殊目标还须满足专项约束。

下一步需要新 ID、坐标或版本时，可从对应回执取得，或读取相应范围。表格坐标与分页关系见专项说明。

宿主 `block_replace.block_ids` 仅用于同一 story、同一父容器、连续文本块的跨 carrier 书签边界更新，不是通用批量替换；只有当前 CLI 帮助暴露对应参数时才按 `xml:p` 的书签规则使用。

## 更新回执

成功回执如下。

```json
{
  "ok": true,
  "data": {
    "document": {
      "document_id": "doccn_xxx",
      "new_blocks": []
    },
    "result": "success",
    "updated_blocks_count": 1,
    "warnings": []
  }
}
```

| 字段 | 说明 |
|---|---|
| `ok` | CLI 调用是否成功；必须同时确认进程退出码为 0 且 `ok == true`，不要按顶层 `code == 0` 判断 |
| `document.document_id` | 被修改的本地 Word 标识 |
| `document.new_blocks` | 当前实现返回空数组。后续需要新增对象 ID 时，通过稳定锚点定位 |
| `result` | 成功回执中的值为 `success` 或 `partial_success`。**有 warning 不等于 `partial_success`**：降级的只有 `ATTR_*`、`COMPAT_*` 以及 `REPAIR_NODE_DEMOTED`、`REPAIR_ATTR_IGNORED`；其余 `REPAIR_*` 给出 warning 但仍是 `success`。调用失败是 `ok == false` 加错误码 |
| `updated_blocks_count` | `str_replace` 统计受影响的文本记录，同一记录里的多次匹配只算一次。普通块或表格操作成功时通常返回 `1`，这个值不能当成改动对象数。预创建、dry-run、处理修订或没有变化时可能返回 `0`，实际结果看对应命令的回执 |
| `command_result` | 结构化领域结果；包含 Chart Data 版本、样式 dry-run/commit、目录/水印、批注、Field、修订、表格几何和对象操作回执；当返回安全整数 `new_revision_id` 时，应优先作为下一次写入的文档版本。普通文本和块命令可能不返回该字段 |
| `warnings` | 归一化、兼容性或能力限制诊断，格式见下 |

修订模式下，受支持的修改会记录为待审修订，回执通过 `revision_changes.created_revision_ids` / `updated_revision_ids` 返回本次新增 / 更新的待审阅修订 ID，用于定向查询修订前后内容；它们不同于文档版本 `new_revision_id`，示例与查询规则见 `revisions`。

以 CLI 本身的退出码和完整 JSON 读取回执。退出码为 0、`ok=true` 且返回该命令所需的字段时，按 `result` 和命令回执判断结果。失败时保留实际错误信息。响应缺失或不完整时，按[Canvas 遇到问题怎么办](../../workflows/canvas-doc-recovery.md)处理原请求。

### warnings 的格式

每条 warning 形如 `CODE: <标签 属性>`，标签名和属性名就是本协议的标签与属性。诊断定位不到具体标签时（例如整块内容被丢弃），退化成 `CODE: 一句英文说明`：

```text
ATTR_ENUM_INVALID_DROPPED: <img border-style>
REPAIR_CHILD_WRAPPED: <td>
```

同一个 `(code, 标签, 属性)` 组合只报一次。同一个 code 超过 10 条时，返回摘要 `CODE: ... (N total, M more omitted)`。

| 前缀或代码 | 含义 |
|---|---|
| `REPAIR_CHILD_WRAPPED`、`REPAIR_CHILD_UNWRAPPED`、`REPAIR_PARENT_WRAPPED`、`REPAIR_ATTR_SUPPLIED`、`REPAIR_TEXT_NORMALIZED`、`BLOCK_PARENT_REPAIRED` | 宿主自动补容器、解包、补属性或处理裸换行，`result` 仍是 `success` |
| `REPAIR_NODE_DEMOTED`、`REPAIR_ATTR_IGNORED` | 节点或属性按兼容规则降级，`result=partial_success` |
| `ATTR_*`、`COMPAT_DUPLICATE_ATTR_LAST_WINS` | 属性不支持、被忽略，或只采用最后一个重复属性 |
| `COMPAT_BLOCK_DROPPED`、`COMPAT_REF_INCOMPLETE`、`COMPAT_RESOURCE_DROPPED` | 内容、引用或资源没有完整保留。涉及要保留的内容时，用写前底稿和当前受影响范围处理，避免继续在已丢失内容的块上写入 |
| `COMPAT_STYLE_LOST` | 宿主不能完整表达或继承样式，也可能提示形似标签的字面文本 |

`str_replace` 只继承命中文本共有且可继承的字符样式。`<b>`、`<TODO>` 等 ASCII 文本会按字面写入，同时可能产生 `COMPAT_STYLE_LOST` 和 `partial_success`。需要写入实际格式时，用 `block_replace` 在 XML 中显式保留行内格式。

## 安全与能力边界

- 局部修改可用精确的块 ID 或文本范围。
- CLI 返回 `confirmation_required` 时按 `lark-shared` 展示 action、risk 和关键参数；用户确认后才能追加 `--yes`（仅当该命令实际支持）。
- 未知 command、非法 `--table-option` 已知字段、派发失败或客户端不可达时，不直调 `LocalDocxUpdate` 私有 API。参照[异常处理](../../workflows/canvas-doc-recovery.md)。
- 不支持在线文档的 `overwrite`、`block_copy_insert_after`、`block_move_after`。XML 全局能力限制查询 `xml:common`；对象级限制按命中的 XML/CLI 专项关键词判断。