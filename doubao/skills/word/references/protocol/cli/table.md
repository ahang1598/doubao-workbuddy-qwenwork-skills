---
keyword: table
---

**功能**：表格行列增删、合并拆分及单元格/行/列属性操作

# 本地 Word：表格结构与属性更新

通用写入参数见 `local-update`，单元格 XML 写法见 `xml:table`。

## 统一命令

表格结构与属性编辑统一使用 `table`，在 `table_option.action` 中指定要执行的操作。顶层 `--block-id` 使用最新读取返回的表格记录 ID。

| action（操作） | 必填/可选字段 | 含义 |
|---|---|---|
| `insert_rows` | `row_index`；可选 `count`，顶层可选 `--content` | 在指定行前插入 1 至 100 行；行号从 1 开始 |
| `insert_columns` | `column_index`；可选 `count`，顶层可选 `--content` | 在指定列前插入 1 至 100 列；列用 A、B、C 等字母表示 |
| `delete_rows` | `row_start_index`；可选 `row_end_index` | 删除指定行范围，包含起止行；end 缺省为 start |
| `delete_columns` | `column_start_index`；可选 `column_end_index` | 删除指定列范围，包含起止列；end 缺省为 start |
| `merge_cells` | `range` | 合并矩形范围内的单元格，例如 `A1:C3` |
| `split_cells` | `cell` / `cells` / `range` 三选一；可选 `split_columns`、`split_rows` | 取消合并或拆分单元格 |
| `update_property` | `cell` / `row_index` / `column_index` 三选一；至少一个属性 | 更新单元格，或整行、整列所覆盖的实际单元格（source cell）属性 |

`instance` 指定同一表格记录出现的哪一处，所有操作都可携带最新结构化读取返回的 `instance`。正文中只有一个可写出现位置时可省略；页眉、页脚、文本框或正文多实例表格先读取 `table_geometry`，从目标项原样复制 `update_context_base.table_option.instance`，不要默认取第一项或自行拼装。

```bash
lark-cli docs +local-update --doc "<token>" \
  --command table --block-id "<table_block_id>" \
  --table-option '{"action":"insert_rows","row_index":2,"count":2}'
```

`--table-option` 接收 JSON 对象，可内联、从相对文件或标准输入（stdin）读取；不要把整个对象再次编码成字符串。只提交当前操作使用的字段。

## 坐标和顺序

- 行号从 1 开始；列用 A、B、C 等字母表示，Z 后接 AA、AB 等，大小写均可。`B3` 表示第 2 列第 3 行，`A1:C3` 表示两端之间的矩形范围。插入位置最多是现有行列数 + 1。
- `count` 默认是 1，单次最多插入 100 行或列。
- 删除范围包含起点和终点，起点不能在终点之后。合并范围必须是矩形。
- 后续动作依赖这次改动后的表格结构时，等这次写入有结果再继续。按改动后的结构取 ID、坐标和 `instance`，缺少下一步所需的信息时只读这张表。
- 能用 `table` 或 `table_geometry` 表达时默认不整表替换。边界拖动、均分、行列重排和整表物理缩放使用 `table_geometry`；普通模式下列宽声明、行高及其规则、表格对齐和 preferred width 可基于最新完整 `<table>` 执行 `block_replace`。修订模式的整表替换只支持行高、对齐等可逆子集；列宽和重排须走受支持的 `table_geometry` 动作，具体边界查询 `revisions`。
- 修订模式下，单元格内边距、不换行和首选宽度可使用最新完整单元格 XML 执行受支持的 `block_replace`；不要扩大为整表任意属性更新。

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
- `<td>` 数量必须等于本次新增的可填内容单元格数。合并表格中无法可靠计算时省略 `--content`，再按需用 `block_replace` 填写新单元格。
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

取消合并时，单个未合并格会报错。批量目标会跳过未合并格，全部未合并则报错。多格需要拆出新行时，按单个 `cell` 依次拆分，每次用当前表格的坐标。

## 更新单元格、行或列属性

目标必须且只能是 `cell`、`row_index` 或 `column_index` 之一，不支持 `cells` / `range`。支持以下 16 项属性，值均为字符串：

| 属性 | 含义与取值 |
|---|---|
| `background_color` | 底色使用 `xml:common` 的统一颜色文法，接受 `auto` 和 `none`，实际颜色须不透明；`none` 清除 direct shading 的填充色 |
| `vertical_align` | 单元格垂直对齐：`top` / `middle` / `bottom` |
| `border` | 边框简写，设置四边及内部横纵线，不包含两条对角线 |
| `border_top`、`border_right`、`border_bottom`、`border_left` | 上、右、下、左边框 |
| `border_inside_h`、`border_inside_v` | 内部横线、纵线 |
| `border_tl2br`、`border_tr2bl` | 左上至右下、右上至左下的对角线 |
| `cell_padding` | 内边距简写，设置四向 |
| `cell_padding_top`、`cell_padding_right`、`cell_padding_bottom`、`cell_padding_left` | 上、右、下、左内边距 |

- 边框值使用“样式 宽度 颜色”，例如 `"single 0.5pt #000000"`；样式如 `single`、`double`，宽度为非负 `pt` 值，颜色使用统一颜色文法。三部分可缺省或调整顺序，但不能全空；`"none"` 表示显式无边框，不删除 direct 属性。
- 内边距接受单个非负 `pt` 值或 `"auto"`，例如 `"4pt"`、`"0pt"`；不支持 `"4pt 8pt"` 等 CSS 多值简写。`auto` 是显式设置，不清除 direct 属性。
- 同时提供简写和具体方向时，具体方向覆盖简写，与 JSON 键顺序无关。未提供且未被简写覆盖的属性保持原值，不替换整份单元格属性。
- 上述 16 项属性至少提供一项，可同时更新多项；仅修改边框或仅修改内边距都是合法请求，无需附带底色或垂直对齐。任一属性值非法，整条指令失败，不会跳过非法属性继续执行。
- JSON 属性名使用下划线，对应 `xml:table` 中 `<td>` / `<th>` 的同名连字符属性，例如 `border_top` → `border-top`、`cell_padding_top` → `cell-padding-top`；`border` 名称相同。

```bash
# 仅改整行底色
lark-cli docs +local-update --doc "<token>" \
  --command table --block-id "<table_block_id>" \
  --table-option '{"action":"update_property","row_index":2,"background_color":"#DDEBF7"}'

# 仅改单元格下边框
lark-cli docs +local-update --doc "<token>" \
  --command table --block-id "<table_block_id>" \
  --table-option '{"action":"update_property","cell":"B3","border_bottom":"single 1pt #000000"}'

# 仅改整列内边距
lark-cli docs +local-update --doc "<token>" \
  --command table --block-id "<table_block_id>" \
  --table-option '{"action":"update_property","column_index":"B","cell_padding":"4pt"}'

# 简写加单边覆盖
lark-cli docs +local-update --doc "<token>" \
  --command table --block-id "<table_block_id>" \
  --table-option '{"action":"update_property","cell":"B3","border":"single 0.5pt #808080","border_bottom":"double 1pt #000000","cell_padding":"4pt","cell_padding_left":"8pt"}'
```

整行或整列只修改其覆盖到的实际单元格（source cell）。

## 替换单元格内容

使用最新 `<td>` / `<th>` ID + `block_replace`；这些 ID 不支持 `block_delete` 或 `block_insert_after`。

从最新的 `full` 响应取出单元格的完整 XML，在原 XML 上修改，保存为 `cell.xml`。保留根标签、原 ID，以及本次没改的属性和子节点。替换文字时，把要保留的行内格式一并写进 `cell.xml`。

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_replace --block-id "<cell_block_id>" \
  --content - < "cell.xml"
```

`cell.xml` 必须以对应 `<td>` / `<th>` 为根，不包裹 `<table>` / `<tr>`。
