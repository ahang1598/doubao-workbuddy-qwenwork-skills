---
keyword: table_geometry
---

**功能**：修改表格尺寸与排列，包括均分行列、拖动边界、移动行列和调整整表宽高

# 本地 Word：修改表格尺寸与排列

修改前读取 `table_geometry`，选择要操作的表格出现位置，原样使用该项的 `update_context_base`；不要默认取第一项。读取方法见 [Canvas 读取说明](../canvas-doc-fetch.md)。

## 修改参数

把底稿中的 `block_id` 填入 `--block-id`，将 `table_option` 原样放入 `--table-option`，保留其中的 `instance` 和两个指纹，只补本次 `action` 和对应字段。`--revision-id` 使用同次读取返回的文档版本；这里不传 `--content`。

| action（操作） | 用途 | 补充字段 |
|---|---|---|
| `distribute_columns` | 均分列宽 | 整表用 `scope="table"`；指定范围用 `range`，例如 `"A1:C3"` |
| `distribute_rows` | 均分行高 | 整表用 `scope="table"`；指定行用 `row_start_index`、`row_end_index`，包含起止行 |
| `resize_column_boundary` | 拖动列边界 | `boundary_index`、`anchor_row_index`、带正负号的 `delta_twips` |
| `resize_row_boundary` | 拖动行边界 | `boundary_index`、带正负号的 `delta_twips` |
| `resize` | 调整整表宽高 | 最终宽度 `width_twips`、最终高度 `height_twips` |
| `reorder_rows` / `reorder_columns` | 移动行或列 | 从 1 开始编号的起止范围及插入边界；插入位置按移动前的排列计算 |

行号和边界编号从 1 开始。`B3` 表示第 2 列第 3 行，`A1:C3` 表示两端之间的矩形范围。`anchor_row_index` 是调整列边界时用于定位的行。

均分整张表的列宽：

```bash
lark-cli docs +local-update --doc "<token>" \
  --revision-id "<latest_revision_id>" \
  --command table_geometry --block-id "<block_id_from_update_context_base>" \
  --table-option '{"instance":{"block_id":"<table_block_id>","instance_id":<instance_id>,"story":"<story>"},"expected_topology_fingerprint":"<topology_fingerprint>","expected_geometry_fingerprint":"<geometry_fingerprint>","action":"distribute_columns","scope":"table"}'
```

示例中的 `instance` 字段仅示意，实际使用所选 `update_context_base.table_option.instance` 的完整对象，保留返回的全部字段。`<instance_id>` 替换为返回的数字，不加引号；所有占位符替换后再执行。两个指纹也从同一份底稿原样复制。

调整整表宽高：读取尺寸用像素 `px`，写入尺寸或位移用 `twips`。响应给出 `twips_per_px=15`，所以宽 600 px、高 200 px 对应 9000 和 3000 twips：

```bash
lark-cli docs +local-update --doc "<token>" \
  --revision-id "<latest_revision_id>" \
  --command table_geometry --block-id "<block_id_from_update_context_base>" \
  --table-option '{"instance":{"block_id":"<table_block_id>","instance_id":<instance_id>,"story":"<story>"},"expected_topology_fingerprint":"<topology_fingerprint>","expected_geometry_fingerprint":"<geometry_fingerprint>","action":"resize","width_twips":9000,"height_twips":3000}'
```

不要混用 px 和 twips，也不要沿用改动前的定位与状态参数。行列移动的具体字段、边界编号含义或位移方向不明确时，用 `lark-cli docs +local-help --tool local-update --command table_geometry` 查询；CLI 返回未知命令或参数时看对应 `--help`，不把内部 `command_params` 当成 CLI 参数。

列宽声明、行高及其规则、表格对齐和首选宽度通过完整 XML 设置，见 `table` 和 `xml:table`。修订模式下的可用操作范围见 `revisions`。
