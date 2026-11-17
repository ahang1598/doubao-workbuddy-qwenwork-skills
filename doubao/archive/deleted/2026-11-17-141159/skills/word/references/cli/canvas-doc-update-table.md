# 本地 Word：表格结构与属性更新

> 使用前须完整读取本页；未见末行「全文完」时，调整 offset 继续读取至该标记。

前置读取 [`canvas-doc-fetch.md`](canvas-doc-fetch.md)、[`canvas-doc-update.md`](canvas-doc-update.md) 和 [`canvas-doc-table.md`](../xml/canvas-doc-table.md)。

## 统一命令

表格结构与属性编辑统一使用 `table`，具体操作放在 `table_option.action`。顶层 `--block-id` 必须是最新 Fetch 返回的共享 table record ID。

| action | 必填/可选字段 | 语义 |
|---|---|---|
| `insert_rows` | `row_index`；可选 `count`，顶层可选 `--content` | 在 1-based 行位置插入 1..100 行 |
| `insert_columns` | `column_index`；可选 `count`，顶层可选 `--content` | 在 A1 字母列位置插入 1..100 列 |
| `delete_rows` | `row_start_index`；可选 `row_end_index` | 删除 1-based 闭区间；end 缺省为 start |
| `delete_columns` | `column_start_index`；可选 `column_end_index` | 删除 A1 字母闭区间；end 缺省为 start |
| `merge_cells` | `range` | 合并 A1 矩形范围 |
| `split_cells` | `cell` / `cells` / `range` 三选一；可选 `split_columns`、`split_rows` | 取消合并或拆分单元格 |
| `update_property` | `cell` / `row_index` / `column_index` 三选一；至少一个属性 | 更新单元格、整行或整列覆盖的 source cell 属性 |

所有 action 都可携带最新结构化读取返回的 `instance`。正文中只有一个可写 occurrence 时可省略；Header/Footer、多实例正文或 TextBox 中必须先 Fetch `table_geometry`，从目标 occurrence 原样复制 `update_context_base.table_option.instance`，禁止取首项或自行拼装。

```bash
lark-cli docs +local-update --doc "<token>" \
  --command table --block-id "<table_block_id>" \
  --table-option '{"action":"insert_rows","row_index":2,"count":2}'
```

`--table-option` 必须解析为单层 JSON object，可内联、从相对文件或 stdin 读取；不得把整个对象再次序列化成字符串。只提交当前 action 消费的字段。

## 坐标、顺序与验证

- 行号从 1 开始；列使用大小写不敏感的 A1 字母。insert 的位置上限是现有行列数 + 1。
- `count` 缺省为 1。插入行列有 1..100 的单次上限；大操作拆分后必须逐步回读。
- 删除范围是闭区间，start 不得大于 end。合并范围必须是矩形。
- 多个依赖坐标的动作必须串行；每次写后重新 Fetch 完整表格，并使用新的 ID、坐标和 occurrence。
- 增删列还要比较写前后的 `<colgroup>` 总宽度；非预期变化视为验证失败。是否补充视觉验收按编辑 workflow 的视觉门禁判断。
- 能用 `table` 或 `table_geometry` 表达时不得整表替换。边界拖动、均分、行列重排和整表物理缩放使用 `table_geometry`；普通模式下列宽声明、行高及其规则、表格对齐和 preferred width 可基于最新完整 `<table>` 执行 `block_replace`。修订模式的整表替换仅支持行高/对齐等可逆子集；列宽和重排须走受支持的 `table_geometry` 动作，见[修订专项](canvas-doc-revisions.md)。
- 修订模式下单元格内边距、不换行和首选宽度可使用最新完整单元格 XML 执行受支持的 `block_replace`；其他属性仍按实际结果判断，不扩大为整表任意属性更新。

## 插入行列与内容

```bash
# 插入两行
lark-cli docs +local-update --doc "<token>" \
  --command table --block-id "<table_block_id>" \
  --table-option '{"action":"insert_rows","row_index":2,"count":2}'

# 在 D 列前插入一列
lark-cli docs +local-update --doc "<token>" \
  --command table --block-id "<table_block_id>" \
  --table-option '{"action":"insert_columns","column_index":"D"}'
```

只有 `insert_rows` 和 `insert_columns` 可带顶层 `--content`。内容是顶层 `<td>` 序列，不包裹 `<tr>` / `<tbody>`：

```bash
lark-cli docs +local-update --doc "<token>" \
  --command table --block-id "<table_block_id>" \
  --table-option '{"action":"insert_rows","row_index":2}' \
  --content '<td><p>研发部</p></td><td><p>进行中</p></td>'
```

- `<td>` 不带属性，内部必须是块级元素；要设置属性，插入后使用 `update_property`。
- `<td>` 数量必须等于本次新增的可填内容单元格数。合并表格中无法可靠计算时省略 `--content`，写后逐格 `block_replace`。
- `count>1` 时内容必须覆盖本次全部新增可填单元格；不得假定同一行内容会被自动复制。

## 删除与合并

```bash
# 删除第 2 至 4 行
lark-cli docs +local-update --doc "<token>" \
  --command table --block-id "<table_block_id>" \
  --table-option '{"action":"delete_rows","row_start_index":2,"row_end_index":4}'

# 删除 B 至 D 列
lark-cli docs +local-update --doc "<token>" \
  --command table --block-id "<table_block_id>" \
  --table-option '{"action":"delete_columns","column_start_index":"B","column_end_index":"D"}'

# 合并 A1:C3
lark-cli docs +local-update --doc "<token>" \
  --command table --block-id "<table_block_id>" \
  --table-option '{"action":"merge_cells","range":"A1:C3"}'
```

## 取消合并与拆分

`split_cells` 不带 `split_columns` / `split_rows` 时取消目标所在合并区域；带任一大于 1 的份数时拆分目标。定位优先级为 `cells > cell > range`，但新调用只能提供一种。`cells` 最多 1000 个，`range` 最多覆盖 1000 格；`split_columns` 最大 63，`split_rows` 最大 32767。

```bash
# 取消合并
lark-cli docs +local-update --doc "<token>" \
  --command table --block-id "<table_block_id>" \
  --table-option '{"action":"split_cells","cell":"B3"}'

# 将 A1 拆为 2 列 3 行
lark-cli docs +local-update --doc "<token>" \
  --command table --block-id "<table_block_id>" \
  --table-option '{"action":"split_cells","cell":"A1","split_columns":2,"split_rows":3}'
```

取消合并时，单个未合并格会报错；批量目标会跳过未合并格，全部未合并则报错。多格同时增加物理行不受支持，应按单个 `cell` 串行拆分并逐次回读。

## 更新单元格、行或列属性

```bash
lark-cli docs +local-update --doc "<token>" \
  --command table --block-id "<table_block_id>" \
  --table-option '{"action":"update_property","row_index":2,"background_color":"#DDEBF7"}'
```

目标必须且只能是 `cell`、`row_index` 或 `column_index` 之一。当前属性闭集：

- `background_color`：使用[统一颜色文法](../xml/canvas-doc-xml.md#颜色与单位)，接受 `auto` 和 `none`，实际颜色须不透明；
- `vertical_align`：`top` / `middle` / `bottom`。

至少提供一个属性。整行或整列只修改其覆盖到的 source cell；跨行列合并时以回读结果为准。改单元格内容使用 `<td>` / `<th>` ID + `block_replace`；这些 ID 不支持 `block_delete` 或 `block_insert_after`。

===== 全文完 =====
