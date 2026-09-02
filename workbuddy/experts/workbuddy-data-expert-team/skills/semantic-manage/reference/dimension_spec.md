# Dimension spec

This is the authority for dimension YAML. Shared contracts are in `common_spec.md`.

## Types

| Type | Use case | `type_param` |
|---|---|---|
| TIME | day/month/year/hour slicing | `time_precision` |
| CATEGORICAL | product, region, channel, category | none |
| DICT | finite code/value mapping needing display labels | `dict_items` |

## YAML fields

### TIME

```yaml
- name: order_date
  label:
    - Order date
  description: "Order creation date"
  source: catalog.db.orders
  col_name: created_at
  type: TIME
  type_param:
    time_precision: DAY
```

`time_precision` enum (case-sensitive, on the YAML write side): `YEAR`, `QUARTER`, `MONTH`, `WEEK`, `DAY`, `HOUR`, `MINUTE`, `SECOND`, `MILLISECOND`.

`time_precision` describes the physical storage precision of the column, not the reporting period. If the column stores timestamps to seconds, use `SECOND`; monthly metrics should use CUMULATIVE metric windows such as `DAY_30` or `MTD`, not `time_precision: MONTH` unless the column itself stores month-level values.

### CATEGORICAL

```yaml
- name: product_category
  label:
    - Product category
  description: "Product category"
  source: catalog.db.products
  col_name: category
  type: CATEGORICAL
```

For LogicalView source:

```yaml
- name: store_name
  label:
    - Store name
  description: "Store name"
  source: store_ops_wide
  col_name: store_name
  type: CATEGORICAL
```

Validate one-segment LogicalView sources through `GetLogicalView.Data.View.Columns`.

### DICT

`type_param.dict_items` embeds full `<key,value>` pairs.

```yaml
- name: order_status
  label:
    - Order status
  description: "Current order status"
  source: catalog.db.orders
  col_name: status
  type: DICT
  type_param:
    dict_items:
      - key: 0
        value: Pending payment
      - key: 1
        value: Paid
```

Rules:

- `key` is a business mapping label. Write it as the user provided it; it is semantically decoupled from the physical type of `col_name`.
- `value` is the readable display label.
- Keys must be unique. Values must be unique and non-empty.
- The mapping should enumerate all legal business values.
- If the user explicitly provides mappings such as `APP: App` or `MINI_PROGRAM: Mini Program`, preserve them exactly. Do not rewrite string keys to physical integers and do not block creation because key type differs from the table column type; only give a mild note in the confirmation page.
- Dimension `label` must be globally unique in the Workspace.

### DICT UPDATE — full-cover rule for `dict_items` (add / rename / remove a code)

`UpdateSemanticFromYaml` on a DICT dimension is **full-cover** on `type_param.dict_items`: whatever list you submit becomes the new complete `CodeValueList`; items present in the current server state but missing from the submitted list are dropped. There is no incremental "append one code" API. This is symmetric to Entity full-cover UPDATE.

User expressions that trigger this path (Chinese / English):

| User wording | Intent |
|---|---|
| "给 <dim> 加一个枚举值 / 加一项 / 补一个 code / 新增取值" | add one code (preserve all existing) |
| "add a value to <dim>", "add code X", "append a mapping" | add one code (preserve all existing) |
| "改 <dim> 里 X 的显示名", "把 X 改成 Y" | rename one Value (keep Key) |
| "删掉 <dim> 里的 X", "remove code X" | drop one code (destructive; ask user to confirm) |

Mandatory sequence (any of the above):

1. **Read the full existing list first** via `ListDimensions '{"KeyWord":"<exact-name>","PageNumber":1,"PageSize":5}'`, locally exact-match `Data[].Name == <name>`, and copy every `CodeValueList[].{Key,Value}` verbatim. Never rebuild `dict_items` from user memory / label text / column samples.
2. **Compute the new list** = existing verbatim ± the user's single-item change. Keep original order, append new items at the tail unless the user requested an explicit position.
3. **Show the confirmation page as a delta table** with columns `Key | Value | Change` where `Change ∈ {kept, added, renamed(<old>→<new>), removed}`. A UPDATE that removes any code MUST show `removed` rows explicitly and require the user's confirmation on the same turn — never silently drop.
4. **Submit** the full new list under `type_param.dict_items`.

Canonical UPDATE YAML template (adding `douyin` to an existing 4-code DICT — verified 2026-08-14 on ap-chongqing `channel_for_create` Id=542, `CodeValueList` had 4 items `{APP, MINI_PROGRAM, H5, PC_WEB}`):

```yaml
dimension:
  name: channel_for_create
  label:
    - Channel
  description: "Sales channel"
  source: test_for_dg.semantic_create.order_detail
  col_name: channel_id
  type: DICT
  type_param:
    dict_items:
      - {key: APP,          value: APP}
      - {key: MINI_PROGRAM, value: 小程序}
      - {key: H5,           value: H5}
      - {key: PC_WEB,       value: PC官网}
      - {key: douyin,       value: 抖音小程序}   # ← new tail item
```

Anti-patterns (do NOT do any of these):

- Submitting only the new item (`dict_items: [{key: douyin, value: 抖音小程序}]`) — server treats this as full-cover and drops the other 4 codes.
- Reading `TypeParam.dict_items` from `ListDimensions` — that path does not exist. Read top-level `CodeValueList[]` instead (see §Read-side field mapping details).
- Rewriting existing `Key`s in the copied list to "normalize" them (e.g. lower-casing `APP` → `app`); Keys are user-visible business labels, preserve byte-for-byte.

## Read-side rendering

When rendering dimension YAML for a **read-side** purpose (aggregate export, bundle dump of a domain, "show me the semantic definition" request, entity+referenced-dimensions merged YAML, etc.), `type` and `type_param` MUST be sourced from `ListDimensions '{"KeyWord":"<exact-name>","PageNumber":1,"PageSize":5}'` and locally exact-matched on `Data[].Name`. The returned `Type` is an **int64** with the following mapping (verified 2026-08-14 on ap-chongqing over 80 live dimensions; distribution `{1: 51, 2: 18, 3: 11}`, no `0` observed):

| `Type` (int64) | YAML `type` | Signature |
|---|---|---|
| `1` | `CATEGORICAL` | `TypeParam` is null or `{WindowUnit:-999, TimePrecision:0, DictCodeId:""}` |
| `2` | `TIME` | `TypeParam.TimePrecision` > 0 and `TypeParam.WindowUnit` >= 0 |
| `3` | `DICT` | Top-level `CodeValueList` non-empty (list of `{Key,Value}` pairs) |

⚠️ **CLI `--describe ListDimensions` documents `TypeList: 0-普通维度 1-时间维度 2-字典维度` — that describe metadata is WRONG.** The real server enum starts at `1` (not `0`) and the numeric-to-semantic mapping is different from what the describe comment says. When calling `ListDimensions` with `TypeList` filter, pass `[1]` / `[2]` / `[3]` per the table above; `[0]` returns zero rows. When rendering YAML, map the numeric `Type` back to the string form (`CATEGORICAL` / `TIME` / `DICT`) — never emit the numeric value into YAML.

Chinese ↔ English `Type` labels the user may express (all point to the same authoritative enum above):

| int64 `Type` | English (YAML) | 中文名 |
|---|---|---|
| `1` | `CATEGORICAL` | 普通维度 |
| `2` | `TIME` | 时间维度 |
| `3` | `DICT` | 字典维度 |

### `MetadataStatus` authoritative enum

Current dimension lifecycle has **only two operations**: create and delete. There is **no draft state and no disable/offline state** for dimensions (unlike metric/model). Server-authoritative dimension state is therefore a two-value enum:

| `MetadataStatus` | Meaning |
|---|---|
| `1` | 已创建 / ONLINE (active, readable & writable) |
| `2` | 已删除 / DELETED (soft-deleted; still visible on read-back but treated as gone) |

A legacy value `3` may appear in `ListDimensions` responses — this is retired-enum residue from an earlier draft-state design that the product has since removed. **Treat `MetadataStatus=3` as equivalent to `1` (active/live)** for all downstream logic: search, uniqueness gates, UPDATE / DELETE preconditions, metric/model reference resolution, and rendering. Do NOT ask the user to "re-publish" or "re-disable" such rows — the product no longer supports Enable/Disable on dimensions and there is no way for the user to "fix" the value.

Helper predicates:

- `is_dimension_active(row) := row.MetadataStatus in (1, 3)`
- `is_dimension_deleted(row) := row.MetadataStatus == 2`

Dimensions also do NOT participate in `EnableSemanticFromYaml` / `DisableSemanticFromYaml`; only CREATE / UPDATE / DELETE apply. Skill §6 UPDATE/ENABLE/DISABLE preconditions elsewhere in this skill that refer to `MetadataStatus=1` / `=2` are authored for metric/model — for dimension the only preconditions are: exists (any active value) for UPDATE / DELETE, and does-not-exist for CREATE.

### Read-side field mapping details

**DICT read-back path**: The dictionary items are stored at the **top-level** `CodeValueList` array on the dimension VO, NOT inside `TypeParam`. Each entry is `{Key: <string>, Value: <string>}`. When rendering DICT YAML, map:

```
ListDimensions.Data[i].CodeValueList[j].Key   → YAML type_param.dict_items[j].key
ListDimensions.Data[i].CodeValueList[j].Value → YAML type_param.dict_items[j].value
```

Do NOT look for `TypeParam.dict_items`, `TypeParam.CodeValueList`, or `TypeParam.DictItems` — those paths do not exist. `TypeParam.DictCodeId` is a service-internal reference to the code-book resource and is not surfaced into the YAML `dict_items` list. Verified 2026-08-14 on 11 DICT samples (`wr_decision_tree_flag`, `decision_status`, `knowledge_type`, ...).

**TIME `TypeParam.TimePrecision` / `TypeParam.WindowUnit` are int64 code numbers, not enum strings** (verified 2026-08-14 on 18 TIME dimensions; observed `TimePrecision ∈ {3, 5, 7, 8}` and `WindowUnit ∈ {4, 5, 7, 9}`). The CLI `--describe ListDimensions` output declares both as raw `int64` with no enum legend. On the YAML write side, users express these as string tokens (`DAY`, `SECOND`, `HOUR`, `MONTH`, ...). The exact int↔string map is **not** fully recoverable from the current CLI describe / real-environment sampling; when rendering a read-side YAML block for a TIME dimension:

- Do NOT hard-code an int→string map from guesswork.
- Do NOT emit the raw integer into YAML `type_param.time_precision` (`5` / `8` are not valid YAML enum tokens on the write side and will be rejected).
- Preferred sources of truth (in order):
  1. If a sibling `GetMetric` / `GetSemanticModel` response embeds the same dimension via `TimeDimension` and returns a string form of `time_precision`, use that verbatim.
  2. If the flow only has `ListDimensions.TypeParam` numeric form, render the YAML placeholder `type_param.time_precision: <int:N, pending write-side enum>` and surface a "N TIME dimensions need write-side precision resolution" note. Ask the user or defer to an explicit write-time input rather than fabricate a mapping.
  3. On UPDATE flows that only need to preserve the existing precision, the safe path is to re-attach by dimension `Id` and let the server keep `TypeParam` unchanged; do NOT round-trip int→string→int through the skill.

**`LogicalViewId` string-"0" placeholder**: Non-LogicalView-backed dimensions return `LogicalViewId="0"` (literal string zero, verified in `GetMetric.TimeDimension.LogicalViewId` and dimension VO), NOT `""`. When gating on "is this LV-backed?", the correct predicate is `LogicalViewId not in ("", "0")` — a plain `!= ""` check will misclassify all data-table-backed dimensions as LV-backed. Same rule applies mirror-wise to metric top-level `LogicalViewId`. Verified 2026-08-14 on `GetMetric('total_orders').SimpleMetricParam.TimeDimension.LogicalViewId == "0"` while its `SourceCategory == 0`.

For domain-scoped bundle dumps, `ListOntologyDomainDimensions '{"DomainId":"<id>","PageNumber":1,"PageSize":100}'` may replace the per-name loop but the same exact-name match still applies. Explicitly forbidden:

- Guessing `type: TIME` because the dimension `name` / `label` / `col_name` contains `time` / `date` / `create_time` / `_at` / `_dt`.
- Copying `type: TIME` from a neighbouring dimension that shares the same `source` table (no "proximity inheritance"; e.g. `warning_name` / `vin` / `project_code` on `warning_event` are NOT TIME just because `create_time` on the same table is TIME).
- Inferring `type: DICT` from label wording like `状态` / `类型` without a real `type_param.dict_items` payload from the API.
- Filling `type` from `search dimension` items whose `Type` field is empty.

If the authoritative read cannot be obtained (API failure, name not found, ambiguity across multiple hits), the rendered dimension MUST carry an explicit placeholder such as `type: <unknown, pending ListDimensions>` and the surrounding artifact must surface a "N dimensions unresolved" note; never guess.

Dimension source-form gate (mirrors metric per GetMetric OpenAPI schema `wedata_2025-10-10_GetMetric.json`): `ListDimensions.Data[]` items are `SimpleDimensionVO`, whose `SourceCategory` / `LogicalViewId` / `LogicalViewName` live at the **dimension top level** (not inside the nested `Source` object) and are structurally identical to `MetricVO`. When a rendered artifact or downstream flow needs to decide whether the dimension is DLC-backed or LogicalView-backed, branch on top-level `SourceCategory` (`0`=data table, `1`=LogicalView) and read top-level `LogicalViewId` for the LV branch or `Source.{CatalogName,DatabaseName,TableName,ColName}` for the data-table branch. Never write `Source.LogicalViewId` / `Source.SourceCategory` — those paths do not exist on `SimpleDimensionVO` (`SourceVO` is 5 fields: `{Id, CatalogName, DatabaseName, TableName, DatasourceId}`, with `DatasourceId` declared `x-tcapi-visibility=2` and therefore not reliable in CLI stdout for direct-connection id reads). See `common_spec.md` §`source` / `source_table` rule for the parallel `MetricVO` contract.



Before writing dimension CREATE YAML, run `ListDimensions '{"KeyWord":"","PageNumber":1,"PageSize":100}'` (paginate on `TotalCount`) and locally filter for an entry whose `Source.CatalogName + DatabaseName + TableName + ColName` equals the target `source + col_name`. If any active (`MetadataStatus in (1, 3)` per §`MetadataStatus` authoritative enum) dimension already covers this `(source, col_name)`:

- Stop and report the existing dimension `Name`, `Id`, `MetadataStatus` to the user.
- Recommend reusing the existing name in downstream FILTER `Dimension(...)` / CONVERSION `conversion_dimension` references instead of creating a synonym.
- Never retry with a renamed dimension against the same `(source, col_name)`; the server rejects with `维度[<new>]已存在（与维度[<existing>]含义相同）`, `InnerCode=1403002`.

## Dimension table selection

A dimension’s `source` should point to a dimension-role table. Skip this section when the user explicitly uses a LogicalView; then validate `col_name` against LogicalView columns.

Priority:

1. Independent `dim` schema: `ListSchemaNames` → `ListTableNames`.
2. Governance label for dimension table: resolve real `LabelId` / label value IDs through `ListLabels`, then use `SearchAsset` native filters (`TagIds`, `TagValueIds`, or `FieldTagIds`) with `Keyword:"<stem>"`, `AssetTypes:["TABLE"]`, and verify returned `Items[].Tags` / `FieldTags`. There is no `ListAssetsByTag` CLI (not registered as of 2026-08-14); do not attempt it or invent label IDs.
3. `dim_*` naming prefix: `SearchAsset`.
4. DWD-layer `dim_*` fallback in mixed organizations.

If none hits, ask the user for a table; never invent one. TIME dimensions commonly live directly on fact tables, so if the user explicitly provides a fact-table time field, use it directly.

## Prohibitions

- Do not invent dimension tables when no signal hits.
- Do not reference a non-existent `col_name`; validate physical fields with `GetTable` and LogicalView fields with `GetLogicalView.Data.View.Columns`.
- Do not duplicate existing dimension labels.
- Do not run model-planning flow when creating a dimension.
- Do not call `GetTable` for a one-segment LogicalView source.
- Do not block DICT YAML because `dict_items.key` differs from the physical column type.
