# 记录读取、搜索与导出命令

## 目录

- 适用范围与读取权限
- 调用参数与限制
- 构造筛选、排序与关键词查询
- 使用视图配置
- 关联记录的数据形态
- 解析返回与完整分页

## 适用范围与读取权限

本页规定 `+record-get`、`+record-list`、`+record-search` 的调用、筛选、排序、分页和输出协议；读取需要 `base:record:read`。

## 调用参数与限制

| 命令 | 定位方式与限制 |
| --- | --- |
| `+record-get` | 按已知 `record_id` 直接读取 |
| `+record-list` | 按筛选、排序、投影和数量读取原始记录 |
| `+record-search` | 关键词命中；必须显式传 `--keyword`、`--search-field`；可加 `--filter-json`，用 `--field-id` 投影 |

默认 NDJSON 的 stdout 是文件描述，不是记录正文；记录在 `record_file`，分页读完整 manifest，见 [NDJSON](#ndjson默认格式文件记录与-manifest)。

## 构造筛选、排序与关键词查询

### 字段、筛选、排序与 TopN

- 筛选只用 `--filter-json '<json>'` 或 `--filter-json @file`，排序用 `--sort-json`；字段名完整加引号。
- 用 `--field-id` 做最小投影，`--limit` 控制数量；仪表盘视图组件遵循[使用视图配置](#使用视图配置)的字段规则。
- `filter-json` 与视图筛选同构。字段类型、operator、value 形状不确定，或筛人员、群组、关联、空值、地理位置、Formula / Lookup 时，先读[完整筛选条件协议](shared-filter-tuple.md)。

| 条件 | tuple；语义 |
| --- | --- |
| 文本等于 | `["标题","==","计划"]` |
| 文本不等 | `["状态","!=","已完成"]` |
| 文本包含 / like | `["标题","intersects","紧急"]`；包含目标片段 |
| 数字等于 | `["金额","==",95]` |
| 数字下限 | `["金额",">=",80]` |
| 日期等于 | `["日期","==","ExactDate(2026-06-02)"]`；datetime / created_at / updated_at 用 `ExactDate(...)` |
| 普通日期边界 | tuple operator 优先用 `>` / `<` 加 `ExactDate(...)`，不用 SQL 语法 |
| 选项等于 | `["状态","==",["待处理"]]`；使用选项名数组，单选也写数组 |
| 选项相交 | `["状态","intersects",["待处理","已完成"]]`；多选或命中任一选项 |

`--sort-json` 接受排序数组；数组顺序即优先级，`desc:true` 降序、`desc:false` 升序，最多 10 个条件。TopN 前把限定的类别、状态等写入 filter 或核实视图筛选；结果保留条件列，越界则修正筛选后重取 N 条。

### 关键词搜索与结构化条件

`+record-search` 只做关键词命中；金额、状态、日期、空值、关联字段写入 `--filter-json`。

```bash
lark-cli base +record-search --base-token "<base_token>" --table-id "<table_id>" \
  --keyword 名称 --search-field 名称 \
  --filter-json @filter.json \
  --sort-json '[{"field":"日期","desc":true}]' --field-id 名称 --field-id 状态 --limit 20
```

## 使用视图配置

1. `--filter-json` 覆盖 `--view-id` 保存的 filter JSON。
2. `--sort-json` 覆盖 `--view-id` 保存的 sort config。
3. 未手动传 filter/sort 时，`--view-id` 使用视图保存的 filter/sort。

读取仪表盘视图组件时，默认省略 `--filter-json`、`--sort-json`、`--field-id` 以继承视图；仅按用户要求覆盖相应部分。
显式投影覆盖视图可见字段及展示所需字段的默认选择，见[视图组件数据读取](dashboard-view.md#读取视图组件数据)。

## 关联记录的数据形态

- link 单元格通常是关联表 `record_id` 数组，即连接键。
- 已知关联记录 ID 时，在关联表用 `+record-get` 读内容；不用 `+record-search` 搜 link `record_id`。

## 解析返回与完整分页

按已确定范围读取。程序化处理优先用 NDJSON；先按[通用调用与恢复](shared-cli-invocation.md)确认成功，再解析实际格式。
全量必须完整分页；`+record-list` 串行调用，分页参数以精确命令帮助为准。`has_more=true` 或返回行数等于 page size 均表示可能尚有数据。

### NDJSON：默认格式，文件记录与 manifest

- 默认及最大 limit 均为 10000。文件每行是含 `record_id` 的“字段名 → 值”对象。
- stdout 是顶层 manifest 或精简摘要，不套 `data`、不要求 `ok`。摘要含 `record_file/manifest_file/records_count/has_more`，不保证含 `format/next_offset`；读取 `manifest_file` 取得完整 manifest，检查 `format=ndjson`、分页和字段元数据。
- `has_more=true` 时用 `--offset <next_offset>`，保持查询范围不变并写不同文件。
- NDJSON 不与 `--jq` 混用。

```bash
lark-cli base +record-list --base-token "$BASE_TOKEN" --table-id "$TABLE_ID" \
  --filter-json '{"logic":"and","conditions":[["金额","empty"]]}' \
  --field-id "金额" --limit 1000 --format ndjson --output ./records.ndjson --as user > ./records-manifest.json &&
python3 - "$BASE_TOKEN" "$TABLE_ID" <<'PY'
import json, sys
m = json.load(open("records-manifest.json"))
if "format" not in m: m = json.load(open(m["manifest_file"]))
assert m["format"] == "ndjson", m
assert (m["base_token"], m["table_id"]) == tuple(sys.argv[1:3]), "wrong source"
required = {"金额"}  # 来自已确认的真实字段清单，不从返回列反推
cols = m["columns"]
assert required <= cols.keys(), "required columns missing"
ids = {cols[n]["field_id"] for n in required}
assert not any(f.get("name") in required or f.get("id") in ids for f in m.get("ignored_fields", [])), "required fields ignored"
assert not m.get("record_not_found"), "requested records missing"
rows = [json.loads(x) for x in open(m["record_file"]) if x.strip()]
assert len(rows) == m["records_count"], "record file count mismatch"
assert all(required <= r.keys() and "record_id" in r for r in rows), "row columns missing"
print(len(rows), m["has_more"], m.get("next_offset"))
PY
```

相关 `ignored_fields`、`record_not_found` 表示证据缺失，不得当成真实空值、空表或业务未发生；无关字段被忽略不影响完整返回的目标列。是否允许 null 按任务决定。全量任务继续处理 `has_more/next_offset` 并核验业务条件。业务核验复用实际 `rows`，不得从 manifest 的示例值推断全量。

`&&` 只在 CLI 成功后解析，stderr 保持独立。直接解析保存的 JSON 原文，不用 Python 字典打印结果、stdout 的 `wc -l` 或 grep 字段数代替。文件读取或解析失败时，不重放已成功的写入。

### JSON：行矩阵与字段映射

- 单页 limit 最大 200。未用 `--jq` 时，成功信封的 `data.data` 是行数组。
- `+record-list --format json` 无 page_token / next_page_token，只用 `--offset` 翻页。`--jq` 只配 JSON，并按表达式结果解析。
- 先以 `data.field_id_list` 建“字段 ID → 列下标”映射；缺 ID 时才以 `data.fields` 映射，并确认字段名唯一。
- 从 `data.data` 取值；不得凭位置或内容认列，不得按 `row["字段名"]` 读行数组。`--field-id` 只减少投影，不是正确映射的前提。

例：`data.fields=["负责人","客户"]`、`data.field_id_list=["f1","f2"]`、`data.data=[["甲","乙"]]`；“客户”ID 为 `f2`，取第 2 列“乙”，不得凭“甲”也像名称而取第 1 列。

仅当任务路径允许全量 Record 导出且选择 JSON 矩阵时，串行调用 `+record-list --format json --limit 200 --offset <n>`；按字段 ID／唯一字段名映射行数组，令 `offset += len(data.data)`，直到 `data.has_more=false`。

### 常用读取写法

```bash
# 数量／抽样：--jq 只配 --format json；每行是数组，列顺序 = data.fields（字段名）= data.field_id_list
lark-cli base +record-list --base-token "<base_token>" --table-id "<table_id>" --as user --format json --limit 200 --jq '.data.data | length'
lark-cli base +record-list --base-token "<base_token>" --table-id "<table_id>" --as user --format json --limit 200 2>/dev/null \
  | python3 -c "import sys,json;d=json.load(sys.stdin)['data'];r=[dict(zip(d['fields'],x)) for x in d['data']];print(len(r),r[:3])"
lark-cli base +record-list --base-token "<base_token>" --table-id "<table_id>" --as user --format json \
# 全量：默认 NDJSON，stdout 是多行 manifest，记录在 record_file 里逐行
lark-cli base +record-list --base-token "<base_token>" --table-id "<table_id>" --as user --output ./records.ndjson > ./manifest.json 2>/dev/null \
  && python3 -c "import json; m=json.load(open('manifest.json')); rows=[json.loads(l) for l in open(m['record_file']) if l.strip()]; print(m['records_count'], m['has_more'], rows[:2])"
# 筛选／排序／投影
lark-cli base +record-list --base-token "<base_token>" --table-id "<table_id>" --as user --format json \
  --filter-json '{"logic":"and","conditions":[["状态","intersects",["处理中"]]]}' --sort-json '[{"field":"金额","desc":true}]' --field-id 标题 --field-id 金额 --limit 10
# 写入：单选／多选为选项名数组；人员、关联为 [{"id":...}]；日期带时分；字段名以 +field-list 为准
lark-cli base +record-batch-create --base-token "<base_token>" --table-id "<table_id>" --as user \
  --json '{"create_records":[{"标题":"A","状态":["待处理"],"负责人":[{"id":"ou_xxx"}],"关联客户":[{"id":"recxxx"}],"截止日期":"2026-10-21 08:00:00","数量":3}]}' --jq '.data.record_id_list'
lark-cli base +record-batch-update --base-token "<base_token>" --table-id "<table_id>" --as user \
  --json '{"update_records":{"recxxx":{"状态":["已完成"]}}}'
```

JSON 模式的记录 ID 在 `data.record_id_list`，与 `data.data` 行同序，行内无 `record_id`；不存在 `data.records`、`row.fields`、`total`、`.fields` 对象。默认 manifest 无 `data` 层，不逐行 `json.loads`。jq 对象的中文键必须加引号。

### 完整性与解析检查

- Record 不支持 markdown。不假设总数字段；完整分页后，NDJSON 累计 `records_count`，JSON 累计 `len(data.data)`。
- 必要字段按已确认的 ID／名称与 NDJSON `columns` 或 JSON 字段清单对照。
- `physical_type` 只描述导出形态；Formula / Lookup 计算类型按[计算类型与导出展示](field-formula-expression.md#计算类型与导出展示)确认，不从展示字符串反推。
- 数值运算前核对实际 JSON 类型。命令失败、解析失败或文件已存在时，不得把旧文件或后处理失败当成空数据。
