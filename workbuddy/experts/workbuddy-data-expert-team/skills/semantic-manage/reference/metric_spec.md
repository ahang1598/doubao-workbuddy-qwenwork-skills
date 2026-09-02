# Metric spec

This is the authority for metric YAML, six metric types, model reuse, and fact-source selection. Shared rules are in `common_spec.md`; model planning is in `model_spec.md`.

## Complex-metric decision tree

Every metric CREATE intent must walk this tree before writing YAML. It maps user natural language to the smallest legal set of metric objects and forbids the two common wrong paths: putting SQL keywords into `expr`, and escaping into a new LogicalView or new model.

```
Q1. Is the target an atomic column aggregation or a derived calculation?
├─ Atomic (SUM/COUNT/AVG/MAX/MIN over fact columns)
│  ├─ No condition → SIMPLE(expr=<agg>(<col>))
│  ├─ Row-level condition ("credit-card orders", "GD region", "last 7 days") →
│  │      SIMPLE(base) + FILTER(base, filter=Dimension(<semantic_dimension_name>)...)
│  │      `Dimension(...)` takes a semantic Dimension name, not a physical column.
│  │      Reuse an existing online Dimension on the same source/column first;
│  │      create a Dimension only when no reusable one exists.
│  │      NEVER put WHERE/CASE WHEN inside SIMPLE.expr.
│  └─ Conditional aggregation SUM(CASE WHEN cond THEN col ELSE 0 END) →
│         Prefer SIMPLE(base) + FILTER(base, filter=Dimension(cond_dim_name)='X').
│         Server accepts SUM(CASE WHEN ...) in SIMPLE.expr as a compat fallback,
│         but semql query layer forbids CASE WHEN in query expressions,
│         so the FILTER decomposition is the only path that stays queryable.
├─ Derived
│  ├─ Ratio / share / A over B → DERIVED(metrics=[A,B], expr="A/B")
│  ├─ Year-on-year / month-on-month / period-over-period → RATIO
│  │      HARD: RATIO.metrics[] MUST reference a CUMULATIVE metric.
│  │      A SIMPLE base is rejected by the server with 1403002
│  │      "must be a cumulative metric (CUMULATIVE type); current type is Atomic metric".
│  │      Build order: SIMPLE(base) → CUMULATIVE(window=MTD/DAY_30/...) → RATIO.
│  │      Chinese-keyword → derived_type mapping:
│  │        "同比" / "年同比" / "同期对比" / YoY  → derived_type: YEAR_ON_YEAR
│  │        "环比" / "月环比" / "MoM" / "上期对比" / "相对变化率"
│  │                                             → derived_type: RELATIVE_RATIO
│  ├─ Rolling window / to-date / "monthly active" / "last N days" → CUMULATIVE
│  │      NEVER change a TIME dimension `time_precision` to fake a monthly window;
│  │      NEVER build a LogicalView just to pre-aggregate the window.
│  │      Chinese-keyword → window enum mapping (verified against
│  │      the CUMULATIVE window enum below; use the closest match and
│  │      surface any ambiguity to the user on the confirmation page):
│  │        "日活" / "DAU" / "日活跃" / "当日活跃"        → window: DAY_1
│  │        "周活" / "WAU" / "周活跃" / "近7天活跃"       → window: DAY_7
│  │        "月活" / "月度活跃" / "月度去重" / "MAU" / "月人活"
│  │        + “自然月 / 本月 / 月初到今天”语义  → window: MTD
│  │        + “ۭa动30天 / 近30天 / ۭa动月”语义 → window: DAY_30
│  │        (if the user only says "月活" without "自然月" or "近30天",
│  │         ask which one; the two calibers differ)
│  │        "小时活跃" / "小时去重用户数"                → window: HOUR_1
│  │        "本周至今 / 周至今 / WTD"                    → window: WTD
│  │        "本季度至今 / 季至今 / QTD"                  → window: QTD
│  │        "本年至今 / 年至今 / YTD"                    → window: YTD
│  │        "本半年至今 / HTD"                            → window: HTD
│  │        "近N天 / ۭa动N天 / 最近N天"                  → window: DAY_<N>
│  │           where DAY_<N> ∈ {DAY_1, DAY_7, DAY_30, DAY_90, DAY_180};
│  │           N without an exact enum slot (e.g. 近60天) → stop
│  │           and ask the user which of the closest slots to use.
│  │      The above list covers CUMULATIVE only; “同比 / 环比 / 同期对比”
│  │      is RATIO (see below), not CUMULATIVE.
│  └─ Event-to-event conversion / retention → CONVERSION
│         NEVER use DERIVED to express retention.
│         HARD: `conversion_dimension` MUST be an existing Dimension name
│         (create the Dimension first, or place it earlier in the same YAML).
│         A raw physical column name is rejected by the server with 1403002
│         "conversion_dimension=[x] 不存在".
Q2. Which model does the metric attach to?
├─ SIMPLE only → run the "Model reuse for SIMPLE CREATE" flow below.
├─ FILTER / DERIVED / RATIO / CUMULATIVE / CONVERSION → NO model_ref;
│    model context is inherited from the referenced metric(s).
└─ If reuse says a model already exists on the same physical source →
     reuse it. Never build a second model, never wrap the same table in a
     LogicalView to bypass the server-side same-meaning check.
```

Batch submission contract for the tree:

- Atomic metrics (SIMPLE) and their required dimensions must be submitted before any derived metric that depends on them; a single-batch payload with SIMPLE + FILTER together returns `Dependent metrics not found` because the server does not topologically sort within one YAML.
- DERIVED / RATIO / CUMULATIVE / CONVERSION are submitted in a later batch after their dependencies are read-back verified.
- On partial failure, resubmit only the failed items in a new batch; do not repeat successful items.

Source-form gate (must run BEFORE writing batch 1): the source-form of every planned SIMPLE metric determines whether derived metrics are even submittable. Run this two-stage gate; skipping it is the root cause of the 2026-08-14 direct-connection derived-metric failure mode.

- **Design-time gate (preferred, prevents rework)**: after the shared Direct-connection resolver returns its result and BEFORE building any YAML, if resolver returned DIRECT AND the plan contains any of FILTER / DERIVED / RATIO / CUMULATIVE / CONVERSION on the same direct-connection source, stop and present the user two paths on the confirmation page:
  a. **Atomic-only**: submit only the SIMPLE metrics (two-segment `db.table` + top-level `DatasourceId`); explicitly drop or defer the derived metrics; document the derived caliber for the user's follow-up.
  b. **LogicalView carrier**: first create (or reuse — see `logical_view_spec.md` §Direct-connection derived-metric carrier) a plain-projection DIRECT LogicalView over the same table, then build the semantic model + SIMPLE + derived metrics with one-segment `source` / `source_table = <logical_view_name>`. This is the only path that keeps all derived types available on a direct-connection source.
  Disclose in the confirmation: "Direct-connection two-segment sources currently cannot host derived metrics; the derived-metric validator rejects them with `1403314 Source table path is incomplete` (verified 2026-08-14)."

- **Batch-1 read-back gate (fallback, catches design-time miss)**: after batch 1 succeeds and BEFORE submitting any batch that contains FILTER / DERIVED / RATIO / CUMULATIVE / CONVERSION, call `GetMetric '{"Name":"<name>"}'` on each SIMPLE dependency. Field-path convention comes from the GetMetric OpenAPI schema `wedata_2025-10-10_GetMetric.json`: `Response.Data.Data` is a `MetricVO` whose `SourceCategory` / `LogicalViewId` / `LogicalViewName` are top-level fields ("与 Source 二选一"), and `Source` is a 5-field `SourceVO` `{Id, CatalogName, DatabaseName, TableName, DatasourceId}` with NO `LogicalViewId` / `SourceCategory` inside. Apply this **branch gate** (mechanized, GetMetric-schema aligned):

  - If `Response.Data.Data.SourceCategory == 1` (LogicalView carrier): assert top-level `Response.Data.Data.LogicalViewId != ""`. Pass → dependency is submittable. Fail → STOP; the record is malformed (LV branch without id), do NOT submit derived batch.
  - If `Response.Data.Data.SourceCategory == 0` (data-table carrier, default): assert `Response.Data.Data.Source.CatalogName != ""` AND `Response.Data.Data.Source.DatabaseName != ""` AND `Response.Data.Data.Source.TableName != ""` (three-segment DLC path is complete). Pass → dependency is submittable. Fail → STOP; the SIMPLE was persisted as a two-segment direct-connection stub whose derived metrics will be rejected with `1403314 Source table path is incomplete for metric: <name>`. Report the incomplete source to the user with the two paths above.

  Do NOT resubmit blindly, and do NOT attempt `UpdateSemanticFromYaml` to patch `Source` — UPDATE does not rewrite the persisted `Source` fields nor the top-level `SourceCategory` / `LogicalViewId` (see `common_spec.md` §Status and sensitivity, UPDATE-vs-Source invariant).

  Note on false-positive avoidance: the branch gate on `SourceCategory` naturally separates LogicalView carriers (top-level `SourceCategory=1` + `LogicalViewId`) from data-table paths (top-level `SourceCategory=0` + `Source.{Catalog,Database,Table}`), so a valid LogicalView-hosted SIMPLE will always pass under the LV branch and a broken direct-connection two-segment stub will always fail under the data-table branch. Never write `Source.LogicalViewId` / `Source.SourceCategory` in a gate expression — those paths do not exist in the GetMetric response schema.

## Metric types

| Type | Direct model dependency | Meaning |
|---|---|---|
| SIMPLE | yes, `model_ref` or inline `model` required | aggregate on fact fields |
| FILTER | no | add business filter to an atomic metric |
| DERIVED | no | arithmetic among metrics |
| RATIO | no | year-on-year / period-over-period |
| CUMULATIVE | no | window accumulation |
| CONVERSION | no | conversion/retention between two events |

Only SIMPLE uses `model_ref`. Derived types reference metrics and inherit model context; never add `model_ref` to them.

### YAML type ↔ `GetMetric` read-back mapping (authoritative signal)

`GetMetric` response has 6 mutually-exclusive `*MetricParam` sub-objects. The reliable way to classify a persisted metric is by which sub-object is populated, **not** by the numeric `Type` field. Verified 2026-08-14 on ap-chongqing.

| YAML `type` | Populated `*MetricParam` sub-object | Additional signature |
|---|---|---|
| `SIMPLE` | `SimpleMetricParam` (non-null) | `SimpleMetricParam.Filter` is null / empty string |
| `FILTER` | `SimpleMetricParam` (non-null, shared with SIMPLE) | `SimpleMetricParam.Filter` is non-empty; the `Filter` string contains `Dimension(...)` / `TimeDimension(...)` clauses |
| `DERIVED` | `DerivedMetricParam` | contains `RelatedMetricList[]` and `Expression` |
| `RATIO` | `RatioMetricParam` | contains `DerivedType` (`YEAR_ON_YEAR` / `RELATIVE_RATIO`) and a CUMULATIVE base ref |
| `CUMULATIVE` | `CumulativeMetricParam` | contains `Window` (`MTD`/`DAY_30`/...) |
| `CONVERSION` | `ConversionMetricParam` | contains `BaseMetric` / `ConversionMetric` / `ConversionDimension` / `Calculation` / `WindowType` |

⚠️ **Do NOT rely on the top-level `Type` int64 for YAML-type classification.** `wedatacli --describe GetMetric` documents `Type: 0-简单指标 1-派生指标 2-转化指标 3-比例指标 4-累积指标`, but (a) this legend has only 5 slots for 6 YAML types (FILTER has no dedicated code — it collapses into the SIMPLE bucket + `Filter` field), and (b) live records contradict the legend: `total_orders` (a plain COUNT-aggregation SIMPLE metric with `SimpleMetricParam` populated and `Filter` empty) reads back as `Type=1`, which the legend labels "派生指标". Treat `Type` as display-only; branch write / render logic on `*MetricParam` presence per the table above.

Same rule applies to `DisPlayType` / `DisPlayDerivedType` — those are UI hints, not authoritative type codes.

## YAML fields

Metric-wide field specs (apply to every `type`):

- `name`: 1-50 chars, charset `[a-zA-Z0-9_]`, unique across the Workspace (also globally unique across model / metric / dimension per `common_spec.md` §Naming uniqueness).
- `label`: display name list; **each alias MUST NOT contain a comma** (server stores labels comma-joined; a comma inside an alias breaks the split).
- `description`: optional, max 500 chars.
- `type`: one of `SIMPLE` / `FILTER` / `DERIVED` / `RATIO` / `CUMULATIVE` / `CONVERSION`; the `type_params` sub-object shape is determined by `type` as documented below.

### SIMPLE

```yaml
- name: total_amount
  label:
    - Total order amount
  description: "Total order amount"
  type: SIMPLE
  type_params:
    model_ref: order_model
    source_table: catalog.db.orders
    expr: "SUM(amount)"
    time_dimension: order_date
    non_additive_dimension:
      dimension: order_date
      window_groupings:
        - dimension1
      window_choice: MIN
```

For LogicalView source, `source_table` is one segment:

```yaml
- name: store_total_gmv
  label:
    - Store GMV
  description: "Store sales amount"
  type: SIMPLE
  type_params:
    model_ref: store_ops_model
    source_table: store_ops_wide
    expr: "SUM(gmv)"
    time_dimension: biz_date
```

`model_ref` must come from the reuse chain below. Validate LogicalView fields through `GetLogicalView.Data.View.Columns`.

### FILTER

`Dimension(...)` and `TimeDimension(...)` reference semantic Dimension names, not raw physical column names. Before writing a FILTER, locate an existing online Dimension for the source column (for example through `ListDimensions` by label/column/source) and reuse its `name`; only create a new Dimension if no same-meaning Dimension exists. The server rejects raw/unknown names with `Dimension not found`.

```yaml
- name: recent_amount
  label:
    - Recent amount
  description: "Recent order amount with filters"
  type: FILTER
  type_params:
    metrics:
      - name: total_amount
    filter: "TimeDimension(order_date,DAY)>='2025-01-01' and Dimension(product_name_dim) LIKE 'milk'"
```

### DERIVED

Use for arithmetic such as profit rate or AOV. Do not use DERIVED for retention; retention is CONVERSION.

```yaml
- name: profit_rate
  label:
    - Profit rate
  description: "Total profit / total revenue"
  type: DERIVED
  type_params:
    metrics:
      - name: total_profit
      - name: total_revenue
    expr: "total_profit / total_revenue"
```

### RATIO

RATIO expresses year-on-year or period-over-period change. Its `metrics[]` entry MUST reference a CUMULATIVE metric; a SIMPLE base is rejected by the server. Build order: SIMPLE base → CUMULATIVE window → RATIO.

```yaml
- name: amount_mom
  label:
    - Amount MoM
  description: "Order amount relative change from previous period"
  type: RATIO
  type_params:
    derived_type: RELATIVE_RATIO
    metrics:
      - name: total_amount_mtd
```

Here `total_amount_mtd` is a pre-built CUMULATIVE metric (`window: MTD` on top of atomic `total_amount`). `derived_type`: `YEAR_ON_YEAR` or `RELATIVE_RATIO`.

### CUMULATIVE

Use for rolling windows and to-date windows. Do not express "monthly active" by changing a dimension's `time_precision`; use CUMULATIVE windows.

```yaml
- name: monthly_active_users
  label:
    - Monthly active users rolling 30d
  description: "Distinct active users in rolling 30 days"
  type: CUMULATIVE
  type_params:
    window: DAY_30
    metrics:
      - name: daily_active_users
```

Optional `filter` (row-level SQL WHERE clause) is supported on CUMULATIVE and must be non-empty when present — omit the key entirely instead of submitting an empty string. Use it only when the same base metric needs BOTH a windowed and a filtered window in the same domain; otherwise prefer stacking a FILTER over the SIMPLE base and CUMULATIVE-ing the FILTER for cleaner reuse.

```yaml
- name: weekly_paid_order_amount
  label:
    - Weekly paid order amount (rolling 7d)
  description: "Rolling 7-day sum of paid/shipped order amount"
  type: CUMULATIVE
  type_params:
    window: DAY_7
    filter: "status IN ('PAID', 'SHIPPED')"
    metrics:
      - name: total_order_amount
```

Window enum: `MINUTE_5`, `MINUTE_30`, `HOUR_1`, `DAY_1`, `DAY_7`, `DAY_30`, `DAY_90`, `DAY_180`, `WTD`, `MTD`, `QTD`, `YTD`, `HTD`. `DAY_30` is a fixed rolling 30-day window; `MTD` is month-to-date.

### CONVERSION

Use for same-entity conversion or retention in a time window. `conversion_dimension` MUST be an existing Dimension `name`, not a raw physical column: create the Dimension first (or place its YAML entry earlier in the same document) so the server can resolve it. A raw column name is rejected with `1403002 conversion_dimension=[x] 不存在`.

```yaml
- name: order_conversion_rate
  label:
    - Order conversion rate
  description: "User conversion from page view to order"
  type: CONVERSION
  type_params:
    base_metric:
      name: page_view_count
    conversion_metric:
      name: order_count
    conversion_entity_type: FROM_DIMENSION
    conversion_dimension: user_id_dim
    calculation: CONVERSIONRATE
    window_type: WINDOW
    window: 7 day
```

`conversion_entity_type`: same table → `FROM_DIMENSION` using a non-time semantic Dimension; cross-table → `FROM_ENTITY` using the model JOIN field. **`conversion_dimension` is REQUIRED under `FROM_DIMENSION` and MUST NOT be set under `FROM_ENTITY`** — in FROM_ENTITY mode the model JOIN itself carries the entity linkage (see `model_spec.md` §4.1 CONVERSION requires a cross-table model), so any `conversion_dimension` value is meaningless and should be omitted. `calculation`: `CONVERSIONS` or `CONVERSIONRATE`. `window_type`: `WINDOW` or `OFFSET`. `window` is a `"<int> <unit>"` string where `<unit> ∈ {hour, day, week, month}` (case-insensitive on write; e.g. `"7 day"`, `"24 hour"`, `"1 month"`).

## Model reuse for SIMPLE CREATE

Trigger only when creating a SIMPLE metric. Goal: avoid semantic fragmentation.

Flow:

1. Lock table `T` from user definition or selected source. Physical table is exact `catalog.schema.table`; LogicalView is one-segment name and must pass `GetLogicalView` field checks.
2. Search candidate models, then compare exact main source:
   - `wedatacli search semantic_model "<tableName>" --top 20 -v`.
   - For each candidate, `GetSemanticModel '{"Name":"<model_name>"}'` and extract the model's main physical source. `SemanticModelVO` has NO top-level `source` field. Use one of the following authoritative paths (whichever is present, they agree on the main source triple):
   - `Response.Data.Data.MainNode.{Id,CatalogName,DatabaseName,TableName}` — preferred, present with a full triple for saved models backed by physical tables (both DLC three-segment and direct-connection two-segment, verified 2026-08-14 on ap-chongqing direct-connection model `cockpit_decision_model`: `MainNode={Id:547,CatalogName:DataLakeCatalog,DatabaseName:gac_poc,TableName:t_decision_run_record_md5}`). **⚠️ LogicalView-carrier models may leave `MainNode` empty or all-null** (`{Id:"",CatalogName:"",DatabaseName:"",TableName:""}` or the whole key elided by omitempty) — those models keep the source on the LogicalView side, and the only reliable read path is `NodeTree.NodeList[].NodeData` on the `MainNode==true` row (which still carries `LogicalViewId` / `LogicalViewName` on the node) plus `TableList` for cross-check. Before dereferencing `MainNode.TableName` byte-for-byte, always guard `if not MainNode or not MainNode.get("TableName"): fall through to NodeTree`. NOTE: DLC-mode models typically leave `MainNode.DatasourceId` empty (schema defines the field on `SourceVO` but the DLC branch does not populate it, and the omitempty JSON contract elides the key from CLI stdout). For a direct-connection model, `MainNode.DatasourceId` may be present but is not the most reliable read; treat `NodeTree.NodeList[].NodeData.DatasourceId` on the `MainNode==true` row as the authoritative direct-connection id (see also the `NodeTree` bullet below and `common_spec.md` §NodeTree direct-connection catalog is a virtual namespace).
   - `Response.Data.Data.TableList[]` — array form of all sources; the main source is the entry whose `{CatalogName,DatabaseName,TableName}` matches `MainNode`.
   - `Response.Data.Data.NodeTree.NodeList[].NodeData` — graph representation; the node whose `NodeData.MainNode==true` carries the same triple plus `DatasourceId` / `DatasourceName`, and this is the authoritative place to read the model's direct-connection id from a saved model. Prefer this path over `MainNode.DatasourceId` and over the metric-level `Source.DatasourceId` (metric-level `Source.DatasourceId` is `x-tcapi-visibility=2` and may be filtered by CLI stdout).
   - Build the comparison triple `T_model = <CatalogName>.<DatabaseName>.<TableName>` from that source and compare `T_model == T` byte-for-byte. Never read `model.source` / `model.joins[].source` — those paths do not exist on `SemanticModelVO`; the server response has no top-level `Joins` / `JoinList`.
   - If one/multiple main-source hits, auto-pick Top1 and show reuse reason + alternates in preview.
3. If no main-source hit, check whether `T` appears as a non-main JOIN source via `Response.Data.Data.NodeTree.NodeList[].NodeData` (rows with `MainNode==false`) and the JOIN edges in `Response.Data.Data.NodeTree.EdgeList[].{SourceNodeId,TargetNodeId,EdgeRelationList[].{SourceNodeColName,TargetNodeColName}}`. If yes, pause and ask whether to attach to that cross-table model or create a new model. Do not auto-reuse JOIN-table hits. Do NOT reconstruct JOINs from any imagined top-level `joins[].source` path — that path does not exist.
4. If no reusable model, pause and offer: create single-source model, create multi-table model through `model_spec.md`, specify existing model, or cancel.

Ranking among main-source hits: time-dimension compatibility, recent update time, then attached metric count.

## Same-meaning rejection at dimension level

Beyond the well-known model-level same-meaning check (`Model [X] already exists (same meaning as model [Y])`, `1403002`), the server also rejects dimension CREATE when another online dimension already covers the same `(source, col_name)` pair:

- Error: `维度[<new_name>]已存在（与维度[<existing_name>]含义相同）`, `InnerCode=1403002`.
- Trigger: writing a new dimension whose `source` + `col_name` equal an existing online dimension's, regardless of `name`/`label`/`type`.
- Handling: stop, show the existing dimension name and its `Id`/`MetadataStatus` from `ListDimensions`, and ask the user to reuse the existing dimension (in `Dimension(...)` / `TimeDimension(...)` / `conversion_dimension`) instead of creating a synonym. Never retry with a renamed dimension on the same `(source, col_name)`.
- Prevention: before dimension CREATE run `ListDimensions '{"KeyWord":"","PageNumber":1,"PageSize":100}'` and locally filter by exact `Source.CatalogName+DatabaseName+TableName+ColName`; also check LogicalView-source dimensions when the source is one-segment.

## Fact-source selection

SIMPLE `source_table` points to a fact-role source and follows `model_spec.md` fact-table selection. If source is a LogicalView, skip physical selection and validate fields through `GetLogicalView.Data.View.Columns`. Derived metrics inherit source from referenced metrics.

## Prohibitions

- Do not skip model reuse and create a new single-table model directly for SIMPLE metrics.
- Do not use fuzzy/contains match for main-source equality.
- Do not auto-reuse a model where `T` is only a JOIN table.
- Do not set `model_ref` on derived metric types.
- Do not implement retention with DERIVED; use CONVERSION.
- Do not put raw physical column names inside `Dimension(...)` / `TimeDimension(...)` FILTER clauses; use semantic Dimension names and reuse existing same-source/same-column Dimensions first.
- Do not put SQL keywords such as `CASE WHEN`, `WITH`, `UNION`, or `IN (SELECT)` inside `expr`; the server may accept them into `CustomAggregationExpression` on write, but the semql query layer refuses to translate them, so the metric will fail at query time. Decompose with FILTER metrics.
- Do not attach RATIO to a SIMPLE base; RATIO.metrics[] must reference a CUMULATIVE metric (server rejects with 1403002 `must be a cumulative metric`).
- Do not put a raw physical column name into CONVERSION `conversion_dimension`; it must be an existing semantic Dimension name (server rejects with 1403002 `conversion_dimension=[x] 不存在`).
- Do not build a LogicalView solely to host CASE WHEN / aggregated pre-calculation for a single physical table; use SIMPLE+FILTER decomposition on the existing model instead. See `logical_view_spec.md` negative list. **Exception (direct-connection derived-metric carrier)**: when the source is a direct connection AND the plan contains FILTER / DERIVED / RATIO / CUMULATIVE / CONVERSION, a plain-projection LogicalView (e.g. `SELECT * FROM db.table`, no CASE WHEN, no pre-aggregation, no filter-condition duplication of what a Dimension/FILTER metric would express) IS the correct carrier and is explicitly whitelisted — it is the only currently working path for derived metrics on direct-connection sources (see `common_spec.md` §`source` / `source_table` rule persistence matrix, and `logical_view_spec.md` §Direct-connection derived-metric carrier). Reuse an existing plain-projection LogicalView on the same connection + table before creating a new one.
- Do not call `GetTable` for a one-segment LogicalView source.

## Vague-concept expansion catalogue (optional, industry-fallback only)

Referenced by `SKILL.md` §Vague-concept query intent step 1 as a **fallback** when workspace-aware decomposition (`ListOntologyDomains` → `ListOntologyDomainMetrics`) yields no sub-family hint. This catalogue is industry commonsense, NOT workspace-verified — when using entries here, the answer MUST disclaim the source (e.g. "以下子族基于行业通用口径，非本工作空间登记内容").

Common domain examples (extend on the fly for concepts not listed; the pattern matters more than the exact rows):

| Vague concept | Candidate sub-family keywords (parallel-search) |
|---|---|
| 用户粘性 / stickiness | DAU / MAU / WAU / 日活 / 月活 / 回访率 / 人均时长 / 次日留存 / 7日留存 / 30日留存 / 人均会话数 |
| 用户价值 / user value | ARPU / ARPPU / LTV / 客单价 / AOV / 付费率 / 人均购买次数 |
| 转化漏斗 / conversion | 浏览UV / 加购率 / 下单率 / 支付率 / CVR |
| 营销效果 / marketing | ROI / ROAS / CAC / CPA / CPC / 新增数 / 拉新成本 / 核销率 |
| 风控 / risk | 拒单率 / 取消率 / 退款率 / 投诉率 / 异常登录 / 黑名单命中率 |
| 客户健康度 / health | 活跃天数 / 会话数 / 流失风险 / NPS / 满意度 / 处理时长 |

Rules of use:

- Do NOT auto-load this catalogue in every turn. Consult it only after `ListOntologyDomainMetrics` returns no relevant sub-family for the concept.
- Never assert an entry exists as a metric before running `search metric` + `GetMetric` anti-ghost verification.
- If the user's domain is clearly NOT in this catalogue (e.g. 金融风控 / 政务 / SaaS 内部效率), skip the table and ask the user to name 2–3 sub-families they care about; do NOT force-fit rows above onto an unrelated domain.