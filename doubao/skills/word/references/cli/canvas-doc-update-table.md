# 本地 Word：表格更新命令

> 使用前须完整读取本页；未见末行「全文完」时，调整 offset 继续读取至该标记。

前置读取 [`canvas-doc-fetch.md`](canvas-doc-fetch.md)、[`canvas-doc-update.md`](canvas-doc-update.md) 及 [`canvas-doc-table.md`](../xml/canvas-doc-table.md)，其中的公共 XML 前置同样适用。

## 指令速查

| 指令 | 说明 | 必需参数 | `--table-option` |
|---|---|---|---|
| `table_insert_rows` | 在指定位置插入一行 | `--block-id` `--table-option`；`--content` 可选 | `{"row_index":2}` |
| `table_insert_cols` | 在指定位置插入一列 | `--block-id` `--table-option`；`--content` 可选 | `{"column_index":"D"}` |
| `table_delete_rows` | 删除行闭区间 | `--block-id` `--table-option` | `{"row_start_index":2,"row_end_index":4}`；单行也必须传 end=start |
| `table_delete_cols` | 删除列闭区间 | `--block-id` `--table-option` | `{"column_start_index":"B","column_end_index":"D"}`；单列也必须传 end=start |
| `table_merge_cells` | 合并矩形单元格区域 | `--block-id` `--table-option` | `{"range":"A1:C3"}` |
| `table_split_cells` | 取消合并，或把单元格拆成多行多列 | `--block-id` `--table-option` | `{"cell":"B3"}`、`{"cells":["A1","C1"]}`、`{"range":"A1:B2"}`，可加 `split_columns` / `split_rows` |
| `table_update_property` | 更新指定单元格、整行或整列的已定义属性 | `--block-id` `--table-option` | `{"cell":"B3","background_color":"#DDEBF7"}`、`{"row_index":2,"background_color":"#DDEBF7"}`、`{"column_index":"B","vertical_align":"middle"}` |

## 定位与验证

- 编辑前，结合用户目标与标题、表头、周围正文等上下文确认目标表格及行列含义，再用最新 Fetch 返回的 ID 和坐标定位；写后核对变化落在预期表格与行列。
- 能用单元格 ID 或 `table_*` 表达时不得整表替换；只有整表 width/align、行高或列宽等必须使用完整 `<table>` 的属性，才基于最新完整 XML 做 `block_replace`。
- 表格结构或属性更新后重新 fetch 完整表格，使用新的 Block ID 和 A1 坐标。多个依赖坐标的表格动作必须串行，不能并行提交；每一步都要重新确认坐标仍指向目标格。
- 增删列时比较写前后的 `<colgroup>` 总宽度，非预期变化视为验证失败。

## 单元格内容替换

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_replace \
  --block-id "<从 Fetch 结果中取得的 td id>" \
  --content @cell.xml
```

`cell.xml` 以最新完整 `<td>` / `<th>` 为底稿，只修改目标内容或属性并保留内部段落格式。单元格的 ID **只能用于 `block_replace`**。对 `<td>` / `<th>` 的 ID 使用 `block_delete` 或 `block_insert_after` 不是“删掉一格”或“加一格”的意思，增删单元格只能通过 `table_insert_*` / `table_delete_*` 改变行列。

协议允许省略 `<td>` 外层，但编辑已有单元格时仍应回放完整 `<td>` 及内部格式；只有明确接受默认单元格格式的新内容才使用简写。要同时改单元格自身属性时必须写全 `<td …>`。

## table-option 编码规则

`--table-option` 必须解析为单层 JSON object，可内联传入，也可使用相对文件路径或 stdin：

```bash
--table-option '{"row_index":2}'
--table-option @table-option.json
--table-option -
```

`table_option` 是顶层 JSON 对象，不是序列化后的字符串。以下写法会二次编码，不能使用：

```text
'"{\"row_index\":2}"'
```

坐标基数：

- **行号从 1 开始**，第 1 行是表格首行。传 `0` 会报参数错误。
- **列标大小写不敏感**，`A`/`a` 都表示首列。
- `table_insert_rows` / `table_insert_cols` 中的 `row_index` / `column_index` 是**插入位置**，上限是「现有行数 / 列数 + 1」，即可以插在末行 / 末列之后；`table_update_property` 中则表示已有的目标行或目标列。
- 删除区间是闭区间；当前 CLI 要求显式提供 start 和 end，单行/单列传 end=start；start 不大于 end。合并 range 必须是矩形区域。
- 这些坐标按客户端协议原样传递，不在 Agent 侧做零基/一基转换。

## table_insert_rows：插入行

```bash
lark-cli docs +local-update --doc "<token>" \
  --command table_insert_rows \
  --block-id "<table_block_id>" \
  --table-option '{"row_index":2}'
```

## table_insert_cols：插入列

```bash
lark-cli docs +local-update --doc "<token>" \
  --command table_insert_cols \
  --block-id "<table_block_id>" \
  --table-option '{"column_index":"D"}'
```

### 插入行列时的 `--content` 文法

仅 `table_insert_rows` 和 `table_insert_cols` 的 `--content` 使用这一特殊文法：顶层 `<td>` 序列，不包裹 `<tr>` 或 `<tbody>`。

```bash
lark-cli docs +local-update --doc "<token>" \
  --command table_insert_rows \
  --block-id "<table_block_id>" \
  --table-option '{"row_index":2}' \
  --content '<td><p>研发部</p></td><td><p>进行中</p></td>'
```

- `<td>` **不能带任何属性**。要设置底色或对齐，插入后再用 `table_update_property`。
- `<td>` 里只能放块级元素，裸文本不合法——写 `<td><p>文本</p></td>`，不是 `<td>文本</td>`。
- `<td>` 的**个数必须等于本次真正新增的可填内容单元格数**，否则整条指令失败。无合并的规整表格里，插一行就等于列数、插一列就等于行数；**表格有合并单元格时这个数会更小**——被合并区覆盖到的位置不算可填单元格。算不准就省略 `--content`，写完再用 `block_replace` 逐格填。
- 省略 `--content` 或传空字符串，新增的行列全部是默认空段落。这是最省事也最不容易算错的写法。

## table_delete_rows：删除行

```bash
lark-cli docs +local-update --doc "<token>" \
  --command table_delete_rows \
  --block-id "<table_block_id>" \
  --table-option '{"row_start_index":2,"row_end_index":4}'
```

## table_delete_cols：删除列

```bash
lark-cli docs +local-update --doc "<token>" \
  --command table_delete_cols \
  --block-id "<table_block_id>" \
  --table-option '{"column_start_index":"B","column_end_index":"D"}'
```

## table_merge_cells：合并单元格

```bash
lark-cli docs +local-update --doc "<token>" \
  --command table_merge_cells \
  --block-id "<table_block_id>" \
  --table-option '{"range":"A1:C3"}'
```

## table_split_cells：取消合并 / 拆分单元格

一个命令两种语义，由是否带 `split_columns` / `split_rows` 决定：

- **不带**这两个参数是**取消合并**，把目标所在的合并区域还原成 1×1；
- **带**其中任一个且大于 1，是**拆分单元格**，把目标拆成指定的行列数。

至少提供一种定位方式，建议只传一种。协议按 `cells > cell > range` 选择；同时提供时只校验和消费优先级最高者，最高者非法也不会回退：

| 字段 | 含义 | 上限 |
|---|---|---|
| `cell` | 单个单元格，A1 记法 | — |
| `cells` | 非空单元格数组 | 1000 个 |
| `range` | 矩形区域，如 `A1:B2` | 覆盖 1000 格 |

拆分份数必须为正整数；两个字段可选，缺省都按 1 处理（即纯取消合并）：

| 字段 | 含义 | 上限 |
|---|---|---|
| `split_columns` | 拆成几列 | 63（Word 单行最多 63 格） |
| `split_rows` | 拆成几行 | 32767（Word 单表最大行数） |

```bash
# 取消合并：还原 B3 所在的合并区域
lark-cli docs +local-update --doc "<token>" \
  --command table_split_cells \
  --block-id "<table_block_id>" \
  --table-option '{"cell":"B3"}'

# 批量取消合并：一次还原多个区域
lark-cli docs +local-update --doc "<token>" \
  --command table_split_cells \
  --block-id "<table_block_id>" \
  --table-option '{"cells":["A1","C1"]}'

# 拆分单元格：把 A1 拆成 2 列 3 行
lark-cli docs +local-update --doc "<token>" \
  --command table_split_cells \
  --block-id "<table_block_id>" \
  --table-option '{"cell":"A1","split_columns":2,"split_rows":3}'
```

这些份数上限不保证当前表格可以拆分；执行时还会检查合并关系、结构及拆分后的行列限制。

`table_option` 只生成当前命令需要的字段。前端只校验并消费该命令实际使用的字段；其他键（包括其他命令的字段、较低优先级的 split 定位字段）被忽略，不能依赖它们报错或实现额外操作。

两条会直接报错、不会静默降级的边界：

- **取消合并语义下点到未合并的格**：`cell` 形态直接报错；`cells` / `range` 形态会跳过其中未合并的格，全部都未合并时报错。`updated_blocks_count` 是 command 级成功计数，成功固定为 `1`，不能据此推断跳过了多少格；必须回读表格确认。
- **多格同时增加行数**：`cells` / `range` 配 `split_rows`，且需要新插入物理行时报错。插入物理行只支持单个目标，用 `cell` 逐个拆。

## table_update_property：更新单元格、行或列属性

```bash
# 更新单个单元格
lark-cli docs +local-update --doc "<token>" \
  --command table_update_property \
  --block-id "<table_block_id>" \
  --table-option '{"cell":"B3","background_color":"#DDEBF7","vertical_align":"middle"}'

# 更新整行
lark-cli docs +local-update --doc "<token>" \
  --command table_update_property \
  --block-id "<table_block_id>" \
  --table-option '{"row_index":2,"background_color":"#DDEBF7"}'

# 更新整列
lark-cli docs +local-update --doc "<token>" \
  --command table_update_property \
  --block-id "<table_block_id>" \
  --table-option '{"column_index":"B","vertical_align":"middle"}'
```

目标三选一，必须且只能提供一个：

| 字段 | 含义 |
|---|---|
| `cell` | 单个单元格，A1 记法 |
| `row_index` | 整行目标，1-based 行号 |
| `column_index` | 整列目标；列标大小写不敏感，如 `A`、`a` 或 `AA` |

当前文档化的更新属性只有：

- `background_color`：使用 [统一颜色文法](../xml/canvas-doc-xml.md#颜色与单位)，接受 `auto` 和 `none`（清除），实际颜色须不透明；
- `vertical_align`：`top` / `middle` / `bottom`。

`background_color` 或 `vertical_align` 至少提供一个。作用到整行或整列时，只修改该行或列覆盖到的 source cell；跨行列合并下不要假设视觉上每个格都有独立属性，写后必须重新 fetch 表格确认实际结果。

`background_color` 或 `vertical_align` 取值非法时，整条指令以参数错误失败；这与 XML 中同名属性被丢弃后继续处理的行为不同。

`table_update_property` 只更新已定义的表格单元格属性。改单元格内容用 `<td>` / `<th>` block ID + `block_replace`；增删行列、合并拆分用对应的 `table_*` 命令。

整表宽度、整表对齐和行高不属于 `table_update_property`。基于最新完整 `<table>` 执行 `block_replace`，保留全部 ID、内容、合并关系及非目标属性；语法见 [`canvas-doc-table.md`](../xml/canvas-doc-table.md)。

===== 全文完 =====
