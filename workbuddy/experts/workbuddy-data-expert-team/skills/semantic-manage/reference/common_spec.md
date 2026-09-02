# Common semantic YAML spec

This is the shared contract for `semantic-manage` semantic YAML objects: model, metric, and dimension. Entity and LogicalView have separate specs.

## Overall YAML shape

CREATE / UPDATE use one full YAML document. Sections are independent and optional as needed:

```yaml
version: 1.0
model: ...
metrics:
  - ...
dimensions:
  - ...
```

`YamlContent` maximum size is 100K characters.

`version` MUST be a YAML number (`1.0`), never a quoted string (`"1.0"`). Quoted-string form is rejected by server-side schema validation with a type error at first submit (verified 2026-08-14: an initial 11-object batch was rejected because `version` was quoted; after unquoting to `1.0` the same YAML succeeded 11/11).

## Naming uniqueness

| Rule | Contract |
|---|---|
| `name` global uniqueness | In one Workspace, model / metric / dimension names must be unique across all three types. |
| dimension `label` uniqueness | Dimension labels are also globally unique in the Workspace. |
| no semantic duplicates | Do not create synonyms with different names, such as `total_sales` and `sales_total`. |
| mandatory precheck | Before CREATE, use `wedatacli search <metric|semantic_model|dimension> --name <name>` and semantic/label search `wedatacli search <resource> "<label-or-meaning>"`. Stop on conflicts and let the user decide reuse/update/rename. |

## `model_ref` rule

Only SIMPLE metrics directly depend on a model. FILTER / DERIVED / RATIO / CUMULATIVE / CONVERSION metrics reference other metrics and inherit the model indirectly; they must not set `model_ref`.

For SIMPLE metrics, if the YAML does not include an inline `model` block, `type_params.model_ref` is required and must be produced by the reuse decision chain in `metric_spec.md`. Never silently create a single-table model or invent a model reference.

## Direct-connection resolution (shared prerequisite)

This is the single authoritative resolver for "does the user want a direct-connection data source, and which one". All write paths that accept a `DatasourceId` parameter (semantic YAML `CreateSemanticFromYaml` / `UpdateSemanticFromYaml`, and LogicalView `ParseLogicalViewSql` / `CreateLogicalView` / `UpdateLogicalView`) MUST run this resolver on the user's current turn and consume its output. Do not re-implement the trigger list, do not add local variants, do not scan catalog metadata to guess `DatasourceId`.

### Triggers

Only the following strong triggers activate direct-connection resolution. If none matches the current user turn, the resolver returns `NONE` (no `DatasourceId`).

- Chinese: `数据源[:：]\s*<value>`, `直连数据源[:：]\s*<value>`, `直连[:：]\s*<value>`, `直连id[:：=]\s*<value>`.
- English (case-insensitive): `datasource\s*[:=]\s*<value>`, `connection\s*[:=]\s*<value>`, `direct(?:\s+connection)?\s*[:=]\s*<value>`, `connection\s+id\s*[:=]\s*<value>`, `DatasourceId\s*[:=]\s*<value>`.
- UUID form: any trigger above whose `<value>` matches `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`.

Extraction is byte-for-byte from the user turn. Do not lowercase / trim / edit-distance guess `<value>`.

### Resolution algorithm

1. If no trigger matched → return `{status: NONE, DatasourceId: absent}`. Do NOT call `ListConnections`. Do NOT scan catalogs.
2. If UUID form → return `{status: DIRECT, DatasourceId: <value>, evidence: "user-supplied uuid"}`. Skip `ListConnections`. Show the id in confirmation before any submit.
3. Otherwise (name form) → call `wedatacli ListConnections '{"KeyWords":"<value>","PageRequest":{"PageNumber":1,"PageSize":50}}'`; server does fuzzy recall. `ListConnections` paging is a NESTED object `PageRequest:{PageNumber,PageSize}` (verified via `--describe ListConnections` 2026-08-14), NOT flat top-level `PageNumber` / `PageSize`; a flat form is rejected by CLI param validation. Locally filter `Response.Data.Items[].ConnectionName == <value>` (case-sensitive, exact).

   | Local exact matches | Return |
   |---|---|
   | exactly 1 | `{status: DIRECT, DatasourceId: item.ConnectionId, ConnectionName, ConnectionType, evidence}` |
   | ≥ 2 | `{status: AMBIGUOUS, candidates: [...]}` → stop; show table `ConnectionName \| ConnectionId \| ConnectionType \| Owner`; ask user to pick; on pick, re-enter the resolver with the chosen id as UUID form |
   | 0 | `{status: NONE, DatasourceId: absent, note: "named connection not found"}` → continue without `DatasourceId`; the caller falls back to its default path (semantic YAML → three-segment only; LogicalView → DLC per `logical_view_spec.md` §3.4) |

4. `ListConnections` CLI or permission failure → stop and pass through the error verbatim. Never fall back to `NONE` on transport errors; `NONE` is only for the "no trigger" and "0 exact match" business outcomes.
5. `ListConnections` full parameter set (paging, filters, etc.) is authoritative from `wedatacli --describe ListConnections`; this spec fixes only the required `KeyWords=<value>` plus nested `PageRequest:{PageNumber,PageSize}` for resolver purposes. If server-side fuzzy recall returns > 100 items and the exact-name match is still not on the first page, page through by incrementing `PageRequest.PageNumber` until exhaustion or stop with an explicit "server recall too broad, please refine the connection name" message — never silently truncate to the first page, and never fall back to flat `PageNumber` / `PageSize`.

### Contract with callers

- Semantic YAML (`CreateSemanticFromYaml` / `UpdateSemanticFromYaml`): if resolver returns DIRECT, add top-level `DatasourceId=<ConnectionId>` to the request; two-segment `source` / `source_table` becomes legal (see §`source` / `source_table` rule below). If resolver returns NONE, do NOT add `DatasourceId`; `source` / `source_table` must stay three-segment or LogicalView one-segment.
- LogicalView (`ParseLogicalViewSql` / `CreateLogicalView` / `UpdateLogicalView`): consume the resolver output as the `source_mode` decision per `logical_view_spec.md` §3.4; DIRECT → submit `DatasourceId`, NONE → DLC path. On UPDATE with NONE, carry forward the old `DatasourceId` from `GetLogicalView`; do not spontaneously downgrade DIRECT→DLC.
- Confirmation summary must always tell the user which of `{DIRECT <ConnectionName / id>, DIRECT <uuid>, DLC / three-segment default}` was chosen and why (evidence string from resolver).

### NodeTree direct-connection catalog is a virtual namespace

`GetSemanticModel.Data.Data.NodeTree.NodeList[].NodeData` may expose a `CatalogName` field for direct-connection nodes (e.g. `xzp_mysql_1`, `auto_test_mysql`). This value is a display-side node identifier scoped to the connection graph — NOT a catalog that the metadata layer can address. Verified 2026-08-14: `wedatacli GetTable '{"CatalogName":"xzp_mysql_1",...}'` returns `ResourceNotFound.CatalogNotFound` (InnerCode 1401110).

Prohibitions:

- Do NOT concatenate NodeTree's direct-connection `CatalogName` with `DatabaseName.TableName` into a three-segment `source` / `source_table` value; the resulting string is not a valid physical path and `GetTable` will reject it.
- Do NOT call `GetTable` with a direct-connection NodeTree `CatalogName`; use `ListConnections` + connection-scoped table probing under the resolved `DatasourceId` if physical existence check is needed, or trust parse-time server validation.
- Do NOT use NodeTree `CatalogName` as `DatasourceId`; the two identifiers are unrelated. The authoritative `DatasourceId` for a saved model comes only from `NodeTree.NodeList[].NodeData.DatasourceId` on the `MainNode==true` row, as documented in `metric_spec.md` §Model reuse for SIMPLE CREATE.

## `source` / `source_table` rule

Three valid submission forms, each with a distinct persisted-source shape and derived-metric availability. The following matrix is empirical behavior verified 2026-08-14 on ap-chongqing; re-verify if the platform patches direct-connection persistence.

Field-path convention for this section (authoritative per GetMetric OpenAPI schema `wedata_2025-10-10_GetMetric.json`): on the `GetMetric` response `Response.Data.Data` (a `MetricVO`), the fields `SourceCategory` / `LogicalViewId` / `LogicalViewName` live at the **MetricVO top level** and are declared "与 Source 二选一" (mutually exclusive with `Source`). The nested `Source` object (a `SourceVO`) contains ONLY `{Id, CatalogName, DatabaseName, TableName, DatasourceId}` — 5 fields, no `LogicalViewId` / no `SourceCategory`. Never write `Source.LogicalViewId` / `Source.SourceCategory` in gate expressions; those paths do not exist. Additional caveat: `SourceVO.DatasourceId` is `x-tcapi-visibility=2` (all other SourceVO fields are visibility=1), which means CLI output may hide or downgrade this field even when the server-side record holds a value; do NOT rely on `Source.DatasourceId` as an authoritative direct-connection id source — read `GetSemanticModel.NodeTree.NodeList[].NodeData.DatasourceId` on the `MainNode==true` row instead. `SimpleDimensionVO` (used in `MetricVO.TimeDimension`, `SimpleMetricParam.TimeDimension`, `ListDimensions` items) mirrors the same layout: `SourceCategory` / `LogicalViewId` / `LogicalViewName` at the dimension top level, `Source` a 5-field SourceVO alongside.

| Form | Example | Server persistence (read-back via `GetSemanticModel` / `GetMetric`) | Derived-metric availability (FILTER/DERIVED/RATIO/CUMULATIVE/CONVERSION) | Requires top-level `DatasourceId` |
|---|---|---|---|---|
| three-segment path (DLC) | `catalog.schema.table` | model `MainNode.{CatalogName,DatabaseName,TableName}` complete; metric top-level `SourceCategory=0` + `Source.{CatalogName,DatabaseName,TableName}` complete (e.g. `CatalogName="DataLakeCatalog"`) | ✅ all derived types available | no; optional `DatasourceId` triggers server-side catalog cross-check |
| two-segment path (direct-connection physical) | `db.table` + top-level `DatasourceId` | model `MainNode.DatasourceId=<connId>` but `MainNode.CatalogName=""`; metric top-level `SourceCategory=0` + `Source.CatalogName=""`; `Source.DatasourceId` is not authoritative here (visibility=2, often filtered from CLI stdout) — the connection id is NOT reliably readable from the metric's `Source` record | ❌ derived metrics against this source hard-fail server-side with `1403314 Source table path is incomplete for metric: <name>` because the derived-metric validator requires either a complete three-segment catalog path OR a LogicalView reference; two-segment direct-connection SIMPLE metrics satisfy neither | yes, top-level `DatasourceId` REQUIRED (from Direct-connection resolver DIRECT status) |
| one-segment name (LogicalView) | `store_ops_wide` | metric top-level `SourceCategory=1` + top-level `LogicalViewId=<id>` + `LogicalViewName=<name>`; nested `Source` object is empty (LogicalView carrier is expressed at the MetricVO top level, per GetMetric schema "与 Source 二选一") | ✅ all derived types available; verified 2026-08-14 on `lv_total_amount` → `avg_transaction_amount` (DERIVED, ONLINE) | no |

Derived-metric availability rule (mechanized, GetMetric-schema aligned): a derived metric requires its base metric's source to be resolvable by the server — that means EITHER a complete three-segment catalog path (`SourceCategory=0` AND `Source.CatalogName` non-empty AND `Source.DatabaseName` non-empty AND `Source.TableName` non-empty) OR a LogicalView reference (`SourceCategory=1` AND top-level `LogicalViewId` non-empty AND `LogicalViewId not in ("", "0")`). Two-segment direct-connection physical sources satisfy neither, so derived metrics on them are rejected at submit with `1403314`.

⚠️ **`LogicalViewId` string-"0" placeholder** (verified 2026-08-14): for non-LogicalView-backed metrics/dimensions, `LogicalViewId` is returned as the literal string `"0"`, NOT the empty string `""` — observed on `GetMetric('total_orders').LogicalViewId == "0"` while `SourceCategory == 0`, and mirrored on `GetMetric.SimpleMetricParam.TimeDimension.LogicalViewId == "0"`. A gate written as `LogicalViewId != ""` will misclassify every data-table-backed metric/dimension as LogicalView-backed. The correct predicate everywhere in this skill is:

```
is_lv_backed = (SourceCategory == 1) and (LogicalViewId not in ("", "0", None))
```

Apply the same predicate to any `LogicalViewId` field on `MetricVO`, `SimpleDimensionVO`, `SimpleMetricParam.TimeDimension`, `RatioMetricParam.*`, and `CumulativeMetricParam.*`. When rendering YAML, treat `LogicalViewId in ("", "0", None)` as "no LV reference" and omit the LV-specific fields; do not emit `logical_view_id: "0"` into YAML.

Invalid forms: two segments without a resolved `DatasourceId`, four segments, empty string, or mixing physical path and LogicalView name for the same source. Stop and ask the user to fix.

Two-segment `source` / `source_table` is allowed ONLY when Direct-connection resolver returned DIRECT and the caller submits top-level `DatasourceId` on the same `CreateSemanticFromYaml` / `UpdateSemanticFromYaml` request. In that mode the model records the connection id on its `MainNode`, but does NOT persist `catalogName` and does NOT propagate `DatasourceId` down to the metric's `Source`; there is no `UpdateSemanticFromYaml` shape that patches these fields after the fact (see §Status and sensitivity, UPDATE-vs-Source invariant). Disclose this in the confirmation whenever the caller plans to build derived metrics on the same source. If the user pasted a two-segment `source` without any direct-connection trigger, stop and ask to either add a catalog prefix or name the direct connection (e.g. `数据源: mysql333`).

Direct-connection derived-metric routing: when the resolver returned DIRECT AND the caller's plan contains any of FILTER / DERIVED / RATIO / CUMULATIVE / CONVERSION on that source, do NOT submit the two-segment physical form. Route the caller through `logical_view_spec.md` §4.1 to first create (or reuse — see `logical_view_spec.md` §Direct-connection derived-metric carrier) a plain-projection DIRECT LogicalView over the same table, then build the semantic model + SIMPLE + derived metrics with `source` / `source_table = <logical_view_name>`. See `metric_spec.md` §Batch submission contract, source-form gate.

Consistency:

- A metric `type_params.source_table` must match the source set of its `model_ref`.
- A dimension `source` must match the source set of its related model.
- Physical sources match by exact three-segment string; LogicalViews match by exact one-segment name.
- `expr`, `col_name`, and `time_dimension` must reference existing fields.
- When a LogicalView is used, fields must come from parse result / `GetLogicalView`; do not invent fields from SQL text or business description.
- User-provided identifiers (`catalog.schema.table`, LogicalView name, field/metric/dimension/entity names, including hash-like suffixes) must be used byte-for-byte from the user's original message. Never trim, extend, deduplicate, or "fix apparent typos" via edit-distance or LLM guessing. When echoing back to the user, wrap the identifier in backticks so it is not continued as free text. On `GetTable` / `GetLogicalView` NotFound with a fully-specified user identifier, stop and ask the user to reconfirm the literal string; do not retry with a near-name variant or fall back to fuzzy search "auto-correction".

## Disable / Delete YAML shape

Semantic DISABLE and DELETE use the same compact name-list shape and do not require `version`:

```yaml
models:
  - model_name
metrics:
  - metric_name
dimensions:
  - dim_name
```

Compact YAML key contract (verified 2026-08-14):

- Plural keys `models:` / `metrics:` / `dimensions:` MUST carry a string array (name-only). Object arrays like `- name: xxx` are rejected server-side with `1403002 已找到 object，必须是 string`.
- Singular keys `model:` / `metric:` / `dimension:` are NOT part of the DISABLE / DELETE schema. Mixing them with plural keys, or using them alone, is rejected as `1403002 架构中未定义属性 "model|metric|dimension"`. Compact DISABLE / DELETE must stay pure plural + string-array.
- CREATE / UPDATE / ENABLE YAML uses a DIFFERENT shape: `model:` / `dimension:` accept a singular object; `metrics:` accepts a plural object array; `model_spec.md` / `metric_spec.md` / `dimension_spec.md` are authoritative for those payload keys.

| Dimension | DISABLE | DELETE |
|---|---|---|
| Meaning | **N/A — dimensions have no disable/offline state** (only CREATE / DELETE apply) | physical deletion, irreversible |
| Sensitivity | — | L4 delete |
| Precondition | — (skill MUST refuse `DisableSemanticFromYaml` / `EnableSemanticFromYaml` on dimensions and route to CREATE/DELETE) | object-level: `dimension` may be deleted directly from active state (`MetadataStatus in (1, 3)` per `dimension_spec.md` §`MetadataStatus` authoritative enum); `model` and `metric` MUST be `MetadataStatus=2` (disabled) first |
| Impact | — | deleting model cascades DELETE to its metrics (high-risk irreversible fan-out); deleting dimension may fail on metric dependency |
| Idempotence | — | NOT idempotent — server returns per-item `Success=false, ErrorMessage="<对象>不存在"` (`FailedCount>0`) when a name in the list is missing; treat as a real failure and surface it, do not silently swallow. **⚠️ `wedatacli --describe DeleteSemanticFromYaml` claims "幂等操作 ... 配置项不存在时跳过（幂等）" — this describe metadata is WRONG; the live server behaves non-idempotently as documented in this row. Verified 2026-08-14.** |
| Default | — | only for explicit physical/permanent cleanup |

Empirical cascade asymmetry: DISABLE model cascades its metrics offline, but ENABLE model does not restore those metrics. When enabling a model, read related metrics and ask whether to explicitly enable disabled metrics; never auto-expand YAML scope.

## Status and sensitivity

Semantic object `MetadataStatus` — metric / model: `1` = ONLINE / published, `2` = DISABLED / offline. Objects created by `CreateSemanticFromYaml` reach ONLINE steady state, but the skill must report status only from read-back APIs. **Dimension uses a different two-value enum**: `1` = 已创建 / active, `2` = 已删除 / deleted; a legacy `3` is retired-enum residue and MUST be treated as active-equivalent to `1` — see `dimension_spec.md` §`MetadataStatus` authoritative enum. Dimensions do NOT participate in ENABLE / DISABLE.

| Operation | API | Sensitivity | Allowed state | Rejected state |
|---|---|---|---|---|
| CREATE | `CreateSemanticFromYaml` | L2 create | missing object | same name / same label exists |
| UPDATE | `UpdateSemanticFromYaml` | L3 write | `MetadataStatus=1` | missing / `2` |
| ENABLE | `EnableSemanticFromYaml` | L3 write | `MetadataStatus=2` | missing / `1` |
| DISABLE | `DisableSemanticFromYaml` | L3 write | `MetadataStatus=1` | already `2` is meaningless |
| DELETE | `DeleteSemanticFromYaml` | L4 delete | Object-level precondition (verified 2026-08-14, enforced as skill contract): `dimension` may be deleted directly from active state (`MetadataStatus in (1, 3)` per `dimension_spec.md` §`MetadataStatus` authoritative enum) — server returns `Success=true, Id=<dimId>` and this is the only object where skill also allows direct delete from active state. `model` and `metric` MUST be `MetadataStatus=2` (disabled) before DELETE. Enforcement asymmetry: for `metric` the server hard-rejects ONLINE direct-delete with `1403043 上线指标不能删除`; for `model` the server would accept ONLINE direct-delete (`Success=true, Id=<modelId>`) BUT the skill adds a guardrail and refuses to submit ONLINE model DELETE, because model DELETE cascades to its metrics (high-risk irreversible fan-out) and treating model like metric keeps the write path predictable. Only bypass the model guardrail when the user explicitly requests ONLINE direct-delete AND confirms cascade + irreversibility on the same turn. | missing name returns per-item `Success=false, ErrorMessage="<对象>不存在"` — surface as failure, do NOT treat as idempotent success. ONLINE metric: `1403043 上线指标不能删除` — instruct the user to `DisableSemanticFromYaml` first, then retry DELETE. ONLINE model without explicit bypass: skill stops before submit and asks the user to disable first. |

`CreateSemanticFromYaml` / `UpdateSemanticFromYaml` accept an optional top-level `DatasourceId` (max 64 chars). Set it ONLY when Direct-connection resolver returned DIRECT for the current user turn; the value MUST equal the resolved `ConnectionId` / user-supplied UUID. When set, two-segment `source` / `source_table` becomes legal on CREATE; the server records `DatasourceId` on the model's `MainNode` but does NOT populate `CatalogName` on `MainNode` and does NOT propagate `DatasourceId` down to per-metric `Source` records (see §`source` / `source_table` rule for the persistence matrix). Three-segment refs submitted alongside two-segment refs on the same YAML are cross-checked at parse time against the connection's reverse-lookup catalog, but that cross-check is a validator, not a persistence hook. When resolver is NONE, MUST NOT pass `DatasourceId`; downstream `source` / `source_table` must stay three-segment or LogicalView one-segment.

UPDATE-vs-Source invariant (verified 2026-08-14): `UpdateSemanticFromYaml` is a semantic-overwrite path — it rewrites the model / metric / dimension definitional fields but does NOT rewrite the persisted `Source.{CatalogName,DatasourceId}` on an existing metric, and does NOT retroactively fill in `CatalogName` on a two-segment direct-connection model. If batch 1 read-back shows a SIMPLE metric with top-level `SourceCategory=0` AND `Source.CatalogName=""` (i.e. neither a three-segment DLC path nor a LogicalView carrier — LogicalView carriers would surface as top-level `SourceCategory=1` + non-empty `LogicalViewId`), no `UpdateSemanticFromYaml` payload (two-segment or three-segment, with or without `DatasourceId`) will patch that record. The only forward path is to DISABLE / DELETE the affected objects and rebuild them under a LogicalView carrier (see `logical_view_spec.md` §Direct-connection derived-metric carrier and the migration Runbook there).

Recommended status reads:

- Batch/fuzzy: `wedatacli search metric|semantic_model|dimension "<query>" -v --top N`; search does not carry authoritative `MetadataStatus` for all needs.
- Single authoritative: `GetMetric`, `GetSemanticModel`, `ListDimensions` with exact-name filtering.

### Missing-object read-back contract (asymmetric across APIs)

The three authoritative read APIs handle "object not found" DIFFERENTLY. Verified 2026-08-14 on ap-chongqing. Callers MUST branch on both shapes; treating all three uniformly (e.g. always expecting `Data.Data` or always expecting an error) is a common source of false ghost/present classification.

| API | Object missing → response shape | Detection logic |
|---|---|---|
| `GetMetric` | **Throws**: `Code=InvalidParameter.MetricNotFound`, `InnerCode=1403021`, human message `指标不存在` | Catch the error code; do NOT treat 1403021 as a transport failure and do NOT retry |
| `GetSemanticModel` | **HTTP 200 with empty payload**: `Response.Data = {}` — the nested `Data.Data` field is ABSENT (not `null`, not `{}` — the key does not exist) | `if not response.get('Response',{}).get('Data',{}).get('Data'): treat as missing`. Do NOT dereference `Response.Data.Data.Name` before this null-check. |
| `ListDimensions` | **HTTP 200 with empty list**: `Response.Data.Data = []` (list, not object); `TotalCount` may be `0` or non-zero if fuzzy `KeyWord` matched other names | After the API call, locally exact-filter `Data[]` where `Name == <target>`; zero hits = missing. Never trust a fuzzy first hit. |
| `GetLogicalView` | **Throws**: `Code=ResourceNotFound.LogicalViewNotFound`, `InnerCode=1403073`, human message `逻辑视图不存在` (verified 2026-08-14 with `Id:"999999999"`). Behavior symmetric to `GetMetric`, asymmetric to `GetSemanticModel`. | Catch the error code; do NOT treat 1403073 as a transport failure and do NOT retry. Exact-`Id` locate via `ListLogicalViews` is still required first (see `logical_view_spec.md` §6.0). |

Practical guardrail: when the same flow reads back multiple object kinds (e.g. model + its metrics + its dimensions), wrap each read in the type-appropriate detection above; do NOT collapse them into a single try/except that assumes error-on-missing.

## Write-response Id contract

`Response.Data.Data.Model/Dimensions/Metrics[].Id` schema is declared by `--describe CreateSemanticFromYaml` / `UpdateSemanticFromYaml` / `DeleteSemanticFromYaml`. Empirical behavior verified 2026-08-14:

- CREATE: `Id` is filled with the newly created object id (string).
- DELETE: `Id` is filled with the deleted object's id.
- UPDATE: `Id` is EMPTY STRING (`""`) even on success; do not read UPDATE `Id` as authority. To confirm the updated object's identifier, do a read-back through `GetMetric` / `GetSemanticModel` / `ListDimensions` using the object's `Name`.

## WorkspaceId parameter

- Default: omit `WorkspaceId`; CLI injects `defaultWorkspace` from `~/.wedata/config.json` when absent.
- Only pass explicit `WorkspaceId` when cross-workspace is requested and the user provides a pure numeric long ID.
- Never pass readable aliases or placeholders.
- Injection is if-absent, not override; a wrong explicit `WorkspaceId` is not corrected by CLI.

Recommended example: `wedatacli GetMetric '{"Name":"total_amount"}'`.
