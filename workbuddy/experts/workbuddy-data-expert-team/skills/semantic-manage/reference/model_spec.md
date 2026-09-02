# Model spec

This is the authority for semantic model YAML: fields, fact-table selection, modeling plan, and JOIN rules. Shared contracts are in `common_spec.md`.

## YAML fields

A model defines a main source and optional JOINs. It supports star and snowflake patterns.

```yaml
model:
  name: order_model
  label:
    - Order Model
  description: "Order lifecycle with customer and region attributes"
  type: DEF
  source: catalog.db.orders
  filter: "status != 'DELETED'"
  tags:
    - name: 内部域
      value: 财务
    - name: 数仓分层
      value: DWD
  joins:
    - name: customer
      source: catalog.db.customers
      on:
        - customer_id = customer_id
      joins:
        - name: region
          source: catalog.db.regions
          on:
            - region_id = region_id
```

Field specs:

- `name`: model English name, 1-50 chars, charset `[A-Za-z0-9_()]`, unique across the Workspace (also globally unique across model / metric / dimension per `common_spec.md` §Naming uniqueness).
- `label`: display name list; every alias is comma-free.
- `description`: max 500 chars.
- `source`: three-segment `<catalogName>.<databaseName>.<tableName>` OR one-segment LogicalView name; charset `[a-zA-Z0-9_.-]`. Direct-connection two-segment `db.table` form is allowed only under Direct-connection resolver DIRECT with top-level `DatasourceId` (see `common_spec.md` §`source` / `source_table` rule).
- `filter` (main-table): optional SQL WHERE clause on the main table only. Not a metric-level filter. When the user says "改口径" on a metric, do NOT write it here — see §"Model has no top-level `filter` — intent translation" below (that section is about metric-level filter mis-mapping; the main-table `filter` here is a different scope and is a legitimate model field).
- `tags`: optional list of `{name, value}` label pairs; max 50 items; `name` max 128 chars, `value` max 256 chars. These are governance labels attached to the model (not metric/dimension labels). Resolve real label ID/value ID via `ListLabels` before writing.
- `joins[]`: nested list, supports unlimited depth. Per-item specs:
  - `name`: 1-50 chars, charset `[A-Za-z0-9_]`; **UNIQUE across all nesting levels of the same model** (a nested JOIN cannot reuse a name from any outer level).
  - `source`: same 3-form rule as `model.source`; **UNIQUE across all nesting levels of the same model** (a table cannot be JOIN'd twice under the same model, at any depth).
  - `description`: optional, max 500 chars.
  - `filter`: optional per-JOIN SQL WHERE on that JOIN table.
  - `on[]`: JOIN conditions, each item is `"leftCol = rightCol"`; **charset `[A-Za-z0-9_ =]` only, no consecutive spaces**. Left side references the parent (outer JOIN or main source) column; right side references the current `joins[].source` column.
  - `joins[]`: nested JOINs of arbitrary depth.

LogicalView source uses one segment:

```yaml
model:
  name: store_ops_model
  label:
    - Store operations model
  description: "Model built on the store operations LogicalView"
  type: DEF
  source: store_ops_wide
```

Mixed LogicalView/physical JOIN is allowed only when the user explicitly requests and confirms each JOIN. `on` always means left-side field from current left source/JOIN result equals right-side field from current `joins[].source`.

### Model has no top-level `filter` — intent translation for "model 过滤条件 / model 口径 / model WHERE"

`SemanticModelVO` has NO `filter` / `where` / `condition` field at the model or `joins[]` level (verified 2026-08-14 on ap-chongqing `GetSemanticModel` responses: only `MainNode` / `TableList` / `NodeTree.NodeList[]` / `NodeTree.EdgeList[]` on the model body). A user request to "give the model a filter" / "给模型加个过滤条件" / "改一下模型的口径" / "让这个模型只看…数据" must NOT be answered by editing model YAML — there is nowhere in model YAML to write the filter.

Intent translation table (apply BEFORE building any YAML):

| User wording | Correct object | Path |
|---|---|---|
| "给模型加个过滤 / 模型只看<X>的数据" (i.e. metric-agnostic scoping the whole model) | new **FILTER metric** on top of each affected SIMPLE base | `metric_spec.md` FILTER + reuse Dimension for the scoping column |
| "改<metric>的口径 / 修改<metric>的统计口径 / 仅统计<X>的<metric>" | **UPDATE the metric** (its `filter` on FILTER, or its `expr` on SIMPLE if truly a numerator change) | `UpdateSemanticFromYaml` on the metric, not the model |
| "在模型里直接排除<X>行" (permanent row-level exclusion for every metric on this model) | new **plain-projection LogicalView** with `WHERE ...` + rebuild the model on that LogicalView | `logical_view_spec.md` (row-level filtering that is genuinely shared across many metrics is a legitimate LV reason — see LV negative list) |

Stop-and-clarify wording when the request is ambiguous (do NOT silently pick a path):

> "model 本身没有 filter 字段。你想要的是以下哪种：
> A. 改已有的某个指标口径 → 我会 UPDATE 那个指标；
> B. 新建一个带条件的统计口径 → 我会建一个 FILTER 指标；
> C. 让这个模型以后看到的全部数据都被过滤 → 需要重建到一个带 WHERE 的 LogicalView 上，影响面很大，需要你确认。"

Never try `UpdateSemanticFromYaml` on the model with a fabricated `filter:` / `where:` key hoping the server will accept it; the server silently ignores unknown keys and the caller ends up believing the request succeeded while nothing changed.

Validation:

- one-segment source → `GetLogicalView` existence and field checks.
- three-segment source → `GetTable` existence and field checks.
- JOIN fields on both sides must exist. Same-name fields still need clear source ownership in the confirmation page.
- JOIN conditions must come from user input or the mandatory modeling confirmation page; never silently write them from name similarity.
- Same-level duplicate JOIN of the same table is not supported.

## Fact-table selection

For model CREATE or SIMPLE metric source selection, the main source should be a fact table. Skip this section when the user explicitly builds on a LogicalView.

| Intent | Priority |
|---|---|
| detail-level analysis / transaction rows | DWD > DWS > ODS |
| subject aggregation / daily or monthly summary | DWS > DWD |
| reuse existing app/report facts | ADS if foreign keys remain > DWS |
| temporary exploration / raw data | ODS fallback with explicit warning |

ADS can be a fact table when it keeps `*_id` / `*_key` keys. Highly aggregated ADS/DWS without keys becomes a single-table model.

Discovery:

- Business keyword or layer prefix only: `wedatacli search table "<keyword>" --top 20`, then strictly local-filter by requested catalog/schema/layer prefix.
- Explicit `catalog.schema`: `wedatacli get tables --catalog <catalog> --schema <schema> --keyword <keyword>` or `ListTableNames`.

Empty-list fallback for explicit `catalog.schema`:

1. `ListTableNames` for that exact catalog/schema.
2. If empty, `SearchAsset '{"Keyword":"<keyword>","AssetTypes":["TABLE"],"MaxResults":20}'`, then strictly filter returned catalog/schema to the user-provided values.
3. If the user already hinted a table name, call `GetTable` with the exact user catalog/schema/table.
4. Still no hit: stop and ask for table name or schema correction. Never switch to an unmentioned schema or invent a table.

Any accepted table must still pass `GetTable` before field/JOIN planning.

## Modeling plan for CREATE model

Trigger only for CREATE model, not metric/dimension create and not update/enable/disable/delete. LogicalView-based single-source model skips physical-table planning unless the user asks for extra JOINs.

Purpose: avoid one single-table model per metric; build reusable star/snowflake models centered on fact tables.

Flow: role recognition → candidate dimension-table discovery → JOIN inference → modeling mode decision → mandatory user confirmation page.

### 1. Role recognition

After `GetTable`, classify:

| Signal | Role |
|---|---|
| `fact_*` / `dwd_*`, measure columns, at least two `*_id`/`*_key` columns | fact |
| `dim_*`, independent `dim` schema, dimension-table governance label | dimension table |
| `ads_*` / `dws_*` with at least one key | light-aggregate fact |
| `ads_*` / `dws_*` highly aggregated with no keys | single-table model |
| wide table with measures and denormalized dimension descriptions | single-table model |
| keys exist but measures are ambiguous | ask user |

Single-table decision skips candidate discovery and writes no `joins`, but the YAML preview must state why.

### 2. Candidate dimension discovery

For each fact foreign key (`*_id` / `*_key`), run parallel signals where useful:

| Signal | Method | Hit rule | Weight |
|---|---|---|---|
| name prefix | `SearchAsset` keyword `dim_<fk_stem>` | `user_id` → `dim_user` | high |
| independent DIM schema | `ListSchemaNames` then `ListTableNames` | table begins with stem | high |
| governance label | Resolve real label IDs through `ListLabels`, then call `SearchAsset` with native `TagIds` / `TagValueIds` / `FieldTagIds` plus `Keyword` stem and `AssetTypes:["TABLE"]`; verify returned `Items[].Tags` / `FieldTags`. There is no `ListAssetsByTag` CLI (not registered as of 2026-08-14); do not call it or invent IDs. | filter by real label ID/value ID and stem | medium |
| upstream lineage fallback | `ListLineages` Direction `INPUT` | upstream `dim_*` or matching above | medium |
| field match | `GetTable` candidates | same FK or id+description | supplement |

Use lineage only when the first three signals fail. If no dimension table is found, do not invent one; offer single-table mode or ask for manual dimension tables.

Confidence: prefix/schema + field match = high; prefix/schema alone or label = medium; lineage only = low.

### 3. JOIN inference

| Rule | Example | Confidence |
|---|---|---|
| exact same field and right side looks like PK | `orders.user_id = dim_user.user_id` | high |
| semantic match with spelling difference | `orders.user_id = dim_user.id` | medium |
| explicit field lineage mapping | lineage mapping | high |
| only type compatible | `orders.uid = dim_user.user_id` | low |

All JOINs, even high-confidence ones, must appear on the confirmation page. Medium/low confidence must be marked for review.

### 4. Modeling modes

- A star model: fact directly joins dimension tables; default recommendation.
- B snowflake model: dimension tables further join nested dimensions.
- C single-table model: wide/high-aggregate/user-requested no JOIN.

### 4.1 CONVERSION metrics require a cross-table (multi-source) model

When the intent classification returns a CONVERSION metric (event-to-event conversion / retention, e.g. "从登录到下单的转化率", "页面浏览 → 下单 → 支付"), the base event and conversion event usually live in different physical tables. In that case:

1. The semantic model backing the CONVERSION metric MUST include BOTH the base-event source and the conversion-event source as JOIN sources on a shared entity key (typically `user_id` / `open_id` / `device_id`). A single-source model over only one of the two tables will make it impossible to attach the CONVERSION metric — the metric YAML has no place to declare the second source (metric-level `type_params` only carries `base_metric` / `conversion_metric` names, source is inherited from the model context).
2. Two independent single-source models over the two tables are also insufficient for the same reason. Do NOT create two single-source models and then try to link them via metric names alone.
3. Correct pattern:

```yaml
model:
  name: user_trade_conversion_model
  label:
    - User login → order conversion model
  description: "Cross-table model for login → order CONVERSION metrics"
  type: DEF
  source: catalog.db.user_login_log     # base-event table
  joins:
    - name: order_detail
      source: catalog.db.order_detail    # conversion-event table
      on:
        - user_id = user_id
```

4. On the model confirmation page (§5), explicitly disclose that this JOIN exists because a CONVERSION metric downstream needs both event sources, so the user understands why a single-source model is not offered.
5. The `conversion_dimension` on the CONVERSION metric must still be an existing semantic Dimension (see `metric_spec.md` CONVERSION section); the fact that the model now spans two tables does not remove that requirement.

Same rule applies mirror-wise to any metric plan that inherently needs two source tables (e.g. "登录用户购买转化率" as DERIVED across two SIMPLE bases on different tables): the DERIVED itself does not carry source info, so both SIMPLE bases must attach to a shared cross-table model.

### 5. Mandatory confirmation page

Before YAML generation, show fact table, table-selection reason, candidate dimension tables, JOIN condition, confidence, hit signals, selected modeling mode, and ask the user to confirm/adjust selected tables, JOINs, and mode. If the user changes fact table, rerun the full plan.

## Prohibitions

- Do not silently accept inferred JOINs.
- Do not invent dimension tables or fields.
- Do not skip the modeling confirmation page.
- Do not run this model-planning flow for metric/dimension creation.

## Catalog CLI boundary

Inside model/LogicalView planning, call `wedatacli` directly for metadata/lineage/tag reads: `GetTable`, `SearchAsset`, `ListSchemaNames`, `ListTableNames`, `ListLabels`, `ListLineages`. Do not chain to external catalog-governance skills. `ListAssetsByTag` is NOT a registered wedatacli action (verified 2026-08-14); do not invoke it. Always prefer runtime `wedatacli --describe <Action>` for parameters.
