# LogicalView spec

This is the authority for DataBuddy LogicalView operations: CRUD, SQL parsing, field governance, one-segment YAML references, permission boundaries, and save-is-effective behavior. Shared semantic YAML rules are in `common_spec.md`.

## Entry index

| User intent | Execute |
|---|---|
| list LogicalViews | §6.1 |
| view SQL / fields / detail | §6.0 exact `Id` location + §6.2 |
| parse SQL / validate fields | §3.3 + §3.4 + §3.6 |
| create from SQL | §4.1 |
| create from business requirement | §4.3 then §4.1 |
| update | §5.1 + §5.2 + §5.3 |
| delete | §7 |
| model/metric/dimension referencing LogicalView | §8 |
| publish LogicalView | §10.3: explain save is effective; no write |

## Capability boundary

LogicalView is a semantic-layer virtual data source that encapsulates SQL joins, filters, and field processing for use by models, metrics, dimensions, and ontology objects.

It is not a `CreateSemanticFromYaml` object, not a warehouse physical VIEW/table, not cross-Workspace in phase 1, and not governed by OntologyDomain. Semantic YAML references it by one-segment name.

The platform/internal-table vs direct-connection path must be decided by verifiable SQL table-reference segment structure and catalog metadata, then confirmed by successful `ParseLogicalViewSql`. Do not guess from names, dialects, or errors.

### When NOT to build a LogicalView (negative list)

LogicalView must not be used as an escape hatch for the metric spec. Reject the following intents and route them back to `metric_spec.md`:

| Anti-pattern | Correct path |
|---|---|
| Single physical table, no JOIN, LV exists only to host `SUM(CASE WHEN ...)` or other conditional aggregation | SIMPLE(base) + FILTER on the existing model over that table |
| Single physical table, LV exists only to pre-compute a rolling/to-date window (e.g. wrap `WHERE dt >= today-30`) | CUMULATIVE metric with `window` enum on the existing SIMPLE base |
| Single physical table, LV exists only to produce a ratio column (`amt_a / amt_b`) | DERIVED metric over two SIMPLE bases; no LV needed |
| Duplicate a table into a "v2" LV to bypass server-side same-meaning model check | Reuse the existing model on the original physical source; capture `Model [X] already exists (same meaning as model [Y])` and switch `model_ref` to `Y` |
| Wrap a physical table in an LV solely so a metric can write a non-English `expr` or column alias | Fix the metric expr / add a proper Dimension; do not smuggle logic into LV SQL |

Legitimate LV reasons remain: multi-table JOIN reuse, cross-catalog federation, physical column pruning / rename to English-only aliases, row-level filtering that is genuinely shared across many metrics, and column-type normalization (array/map/json to scalar). When a request is ambiguous, ask whether the same result can be produced by SIMPLE+FILTER / DERIVED / CUMULATIVE on an existing model before proposing a new LV.

### Direct-connection derived-metric carrier (explicit exception to the single-physical-table rule)

Verified 2026-08-14: direct-connection two-segment SIMPLE metrics leave top-level `SourceCategory=0` AND `Source.CatalogName=""` after CREATE, and `Source.DatasourceId` is not authoritatively readable (declared `x-tcapi-visibility=2` on the SourceVO schema, so CLI stdout may hide or downgrade it) — see `common_spec.md` §`source` / `source_table` rule persistence matrix. The derived-metric validator then rejects any FILTER / DERIVED / RATIO / CUMULATIVE / CONVERSION built on such a base with `1403314 Source table path is incomplete for metric: <name>`, and `UpdateSemanticFromYaml` cannot patch the persisted `Source` (or the top-level `SourceCategory` / `LogicalViewId`) afterwards.

For this limitation window, a DIRECT LogicalView with a plain-projection SQL (`SELECT * FROM db.table` or an explicit English-aliased projection over the same table, no CASE WHEN, no pre-aggregation, no window computation, no filter-condition duplication of what a Dimension/FILTER metric would express) IS an allowed carrier and is explicitly whitelisted against the single-physical-table clause of the negative list above. It is currently the only working path for derived metrics on direct-connection sources; keep the SQL a semantic-neutral projection so the anti-patterns the negative list actually targets (CASE WHEN pre-aggregation, window pre-computation, ratio pre-computation, same-meaning duplication) remain forbidden.

Reuse-first (required before creating a new carrier): call `ListLogicalViews` scoped to the resolved `DatasourceId` and locally exact-match `Items[].DatasourceId == <connId>` AND `Items[].SqlContent` referencing the target `db.table`. If a matching plain-projection view already exists (verified 2026-08-14 on `auto_test_mysql` where `nqmysql` is already `select * from wedata_test.auto_test_table_1`), reuse it as the semantic model's `source` — do NOT create a synonym view. Only when no reusable carrier exists is a new plain-projection view justified under this exception.

### Direct-connection derived-metric migration Runbook

When a workspace already has a broken direct-connection direct-build (SIMPLE metrics ONLINE but with top-level `SourceCategory=0` AND `Source.CatalogName=""` — i.e. neither a three-segment DLC path nor a LogicalView carrier; LogicalView carriers would surface as top-level `SourceCategory=1` + non-empty `LogicalViewId`), and derived metrics failing `1403314`, migrate through the following sequence. This is the only forward-safe path; there is no in-place patch (see `common_spec.md` §Status and sensitivity, UPDATE-vs-Source invariant).

1. Read-back audit: enumerate the affected model + metrics + dimensions with `GetSemanticModel` / `GetMetric` / `ListDimensions`; snapshot names, labels, and dependencies. Do not proceed on incomplete audit.
2. DISABLE the model. `DisableSemanticFromYaml` on the model name cascades its metrics to `MetadataStatus=2` (per `common_spec.md` §Empirical cascade asymmetry). Confirm with per-object read-back that model + all metrics are now `MetadataStatus=2`.
3. DELETE in dependency order: derived metrics first (referring metrics before referred), then SIMPLE metrics, then dimensions, then the model. Use `DeleteSemanticFromYaml` compact plural + string-array shape. Dimension DELETE from ONLINE is allowed by contract, but during migration the dimensions are already disabled through cascade — surface any per-item `Success=false` as failure (DELETE is not idempotent).
4. Carrier: reuse or create a DIRECT LogicalView per §Direct-connection derived-metric carrier above. Verify with `GetLogicalView` that `Data.View.DatasourceId` matches the resolved connection id and `Data.View.Columns` contains the fields needed by the plan.
5. Rebuild top-down, using one-segment LogicalView-name references: `model` (single source = `<logical_view_name>`) → dimensions (`source: <logical_view_name>`) → SIMPLE metrics (`source_table: <logical_view_name>`). Submit through `CreateSemanticFromYaml` in one batch or split by `YamlContent` size.
6. Read back each SIMPLE metric via `GetMetric` and assert top-level `Response.Data.Data.SourceCategory == 1` AND `Response.Data.Data.LogicalViewId != ""` (LogicalView carrier confirmed at the MetricVO top level per GetMetric schema "与 Source 二选一"); only then submit the derived-metric batch (FILTER / DERIVED / RATIO / CUMULATIVE / CONVERSION) in a second `CreateSemanticFromYaml` call.
7. Final read-back: every rebuilt object is `MetadataStatus=1` (ONLINE) through single-object authoritative reads. ENABLE model does NOT auto-restore its metrics (asymmetric cascade); explicitly ENABLE any metric that must be online but is still `MetadataStatus=2` — never auto-expand the ENABLE YAML scope beyond what the user confirmed.

| Capability | API | Notes |
|---|---|---|
| list | `ListLogicalViews` | `WorkspaceId`, `Keyword`, `PageNum`, `PageSize`; response `Response.Data.{Items[],Total}` |
| detail | `GetLogicalView` | by `Id`; response SQL is plaintext at `Data.View.SqlContent` |
| parse submit | `ParseLogicalViewSql` | request `SqlContent` Base64, parse `ResourceId` required, `DatasourceId` only for DIRECT |
| parse poll | `GetLogicalViewParseResult` | only when submit returns `Status=0`; use describe-confirmed polling keys |
| create | `CreateLogicalView` | name/description/Base64 SQL/columns; DIRECT submits same parse-time `DatasourceId`; never submits `ResourceId`; accepts optional top-level `ClusterType` string (see §3.4.5) |
| update | `UpdateLogicalView` | by `Id`; SQL-change updates require reparse and Base64 SQL; metadata-only updates may omit SQL if describe supports it; carries `ClusterType` when the caller wants to change it (see §3.4.5) |
| delete | `DeleteLogicalView` | by `Id`; service blocks dependency conflicts |

Always check `wedatacli --describe <Action>` for runtime parameters. `ParseLogicalViewSql` and `GetLogicalViewParseResult` are currently registered; only if describe proves unavailable may fields come from user-confirmed or trusted external parse results. LogicalView has no status/publish/enable API.

## 3. Fields and parameters

### 3.1 Name

Required, unique in Workspace, max 100 chars, letters/digits/underscore only. Recommended regex: `^[A-Za-z_][A-Za-z0-9_]{0,99}$`. Run `ListLogicalViews` uniqueness precheck before create. LogicalView namespace is independent from model/metric/dimension, but if the same flow creates same-named semantic objects, warn about confusion and confirm.

### 3.2 Description

Required, max 500 chars. If absent, the skill may draft one from SQL/business requirement but must show it for confirmation.

### 3.3 SQL content

Rules:

- Required; after stripping leading whitespace and normal comments, must start with `SELECT` or `WITH`.
- Prohibit DDL/DML, `EXPLAIN`, `ANALYZE`, `SHOW`, `DESCRIBE`, grants/admin/session commands, optimizer/session hints, multiple top-level statements, and references to other LogicalViews in phase 1.
- Can reference catalog data tables.
- Must confirm data source and fields before create/update.

#### 3.3.1 `SqlContent` encoding

Mental model: in skill/user view, SQL is UTF-8 plaintext. In request bodies, every `SqlContent` field is standard Base64 encoded exactly once. In responses, `SqlContent` is plaintext and must not be decoded.

Python-equivalent request encoding:

```python
sql_encoded = base64.b64encode(sql_plain.encode("utf-8")).decode("ascii")
payload = {"SqlContent": sql_encoded}
```

Contracts:

- `ParseLogicalViewSql` and `CreateLogicalView` always carry Base64 `SqlContent`; `UpdateLogicalView` carries it only when SQL changes.
- Use standard JSON serialization; never hand-escape SQL into JSON.
- Do not double-encode, URL-encode, gzip, normalize, beautify, trim, or otherwise mutate plaintext SQL between parse and create/update.
- Retain `sql_plain_parsed`; before create or SQL-changing update assert `sql_plain_to_submit == sql_plain_parsed` byte-for-byte, then Base64 encode once. If not equal, stop and reparse.
- If the user changes SQL after parse, run `ParseLogicalViewSql` again.
- If payload JSON exceeds roughly 4KB or contains many special chars, use a temporary JSON file / supported input-file path to avoid shell truncation; do not split SQL.

Error handling:

| Error fragment | Root cause | Handling |
|---|---|---|
| WAF / blocked / SQL injection gateway | SQL was not encoded into request or compliant request still hit gateway | encode once and retry only if not encoded; if already compliant, pass through |
| `sqlContent base64 decode failed` | missing/truncated/broken encoding | re-encode once using standard Base64; do not alter padding manually |
| SQL syntax/table/field error | decode succeeded; semantic validation failed | pass through; do not re-encode |

### 3.4 Data source and parse resource

Goal: `source_mode` is decided by the shared Direct-connection resolver in `common_spec.md` §Direct-connection resolution (shared prerequisite). This spec only tells LogicalView what to do with the resolver's output. Do not re-implement the trigger list here; do not scan catalog metadata to guess `source_mode` or `DatasourceId`.

Principles:

1. `source_mode` = `DIRECT` if the resolver returned DIRECT; otherwise `source_mode` = `DLC`. Segment count does NOT decide mode.
2. `DatasourceId` = resolver's `DatasourceId` when DIRECT; must be omitted when DLC.
3. Both DIRECT and DLC still require a real parse `ResourceId` from `ListComputeResourceOptions`: DIRECT uses `ResourceTypes=[1]`, DLC uses `ResourceTypes=[3]`. `ResourceId` is parse-only and never saved.
4. Ambiguous resolver output (`AMBIGUOUS`) stops the flow before parse; resume only after user picks one candidate.

Allowed signals for mode: resolver output only (per common_spec §Direct-connection resolution); on UPDATE, old `DatasourceId` from `GetLogicalView` as a carry-forward default when resolver returned NONE this turn. Prohibited: `get catalog --name` / `get catalogs` scanning to infer DIRECT; treating `wedata-connection-id` in catalog properties as a mode signal; `search table` / `get tables` for `DatasourceId` narrowing; catalog name/type guessing; error-based mode switching; using `Catalog.Id` / `Identifier` as `DatasourceId`; using `DatasourceId` as `ResourceId`.

#### 3.4.1 LogicalView-specific rules on top of the shared resolver

- When resolver returned NONE (no trigger matched, or name-form returned 0 exact matches), LogicalView defaults to DLC. DLC parse requires three-segment `catalog.schema.table` in the SQL; if the SQL is non-three-segment, DLC parse will fail server-side and the error is passed through to the user (do not silently switch to DIRECT).
- When resolver returned DIRECT, LogicalView submits `DatasourceId` to `ParseLogicalViewSql`, `CreateLogicalView`, and `UpdateLogicalView`; the SQL may be non-three-segment (server resolves under the connection).
- UPDATE fallback: if resolver returned NONE this turn but `GetLogicalView` shows the old view is DIRECT with `DatasourceId=X`, keep `source_mode=DIRECT` with `DatasourceId=X` (carry-forward). Do NOT downgrade DIRECT→DLC unless the user explicitly requested it in this turn. If the user pastes a new trigger with a different resolved `DatasourceId`, treat it as a migration and require explicit confirmation.\n- No-table-ref SQL (`SELECT 1`, `SELECT NOW()`): only allowed when resolver returned DIRECT with an explicit `DatasourceId`; otherwise stop.

#### 3.4.2 Table-reference extraction

Use fail-closed pipeline S1-S6. This is a parse-time validity check, not a mode-decision step; mode is already fixed by the resolver.

1. Strip comments and string literals; avoid fake refs in comments/literals; exclude CTE names, aliases, functions, LogicalView names.
2. Remove identifier quotes by segment. Three-segment regex must match `^[A-Za-z_][\w$]*\.[A-Za-z_][\w$]*\.[A-Za-z_][\w$]*$`. Two/one segments must match legal identifier parts. Invalid identifiers stop; never auto-fill catalog.
3. Exclude table-valued functions and pseudo tables such as `UNNEST`, `VALUES`, `TABLE`, `generate_series`, `explode`, `dual`; treat as no physical table ref.
4. Reject table refs with template variables/placeholders `${...}`, `{{...}}`, `?`, `:name`; ask user to expand.
5. Four or more segments: if a known dialect project prefix is clear and tail three segments pass regex, use tail three and disclose in confirmation; otherwise stop.
6. Mixed three- and non-three-segment refs: allowed only under `source_mode=DIRECT`; server resolves non-three-segment refs under the direct connection. Under DLC, mixed segments will cause parse failure; surface the server error.

Aggregation result (validity, not mode):

| Extracted refs | Under DIRECT | Under DLC |
|---|---|---|
| all three-segment | ok; server may cross-check catalog vs reverse-lookup | ok |
| all one/two-segment | ok; server resolves under connection | parse will fail; server error passes through |
| none | ok only if `DatasourceId` is set (already true under DIRECT) | stop before parse |
| mixed | ok | parse will fail; server error passes through |
| S1-S5 validation failure | stop with exact reason | stop with exact reason |

#### 3.4.3 Catalog metadata (validation aid only)

Catalog metadata (`get catalog --name`, `get catalogs`) MUST NOT be used to infer `source_mode` or to derive `DatasourceId`. Whatever `wedata-connection-id` a catalog exposes is irrelevant to mode selection; only the shared resolver fixes mode.

The only remaining catalog interaction: optional catalog-name spelling canonicalization via `get catalogs --type TABLE` before showing SQL evidence to the user (exact match first, case-insensitive with disclosure). It is a display aid and never influences `source_mode` or `DatasourceId`; skip it if it introduces ambiguity and rely on parse-time server validation instead. No `get catalog --name` property inspection. No `search table` / `get tables` probing.

#### 3.4.4 Decision table

| source_mode | Enter condition | `ResourceId` | `DatasourceId` | `ListComputeResourceOptions` |
|---|---|---|---|---|
| DLC (default) | resolver returned NONE (no trigger, or 0 exact match) | required, real DLC parse resource | absent | `ResourceTypes=[3]` |
| DIRECT (name) | resolver returned DIRECT via unique `ListConnections` exact match, or user pick after AMBIGUOUS | required, real DIRECT parse resource, ≠ `DatasourceId` | required (= resolved `ConnectionId`) | `ResourceTypes=[1]` |
| DIRECT (uuid) | resolver returned DIRECT via user-supplied UUID | required, real DIRECT parse resource, ≠ `DatasourceId` | required (as given) | `ResourceTypes=[1]` |
| DIRECT (carry-forward) | UPDATE turn: resolver returned NONE, but `GetLogicalView` shows old DIRECT `DatasourceId` | required | required (= old `DatasourceId`) | `ResourceTypes=[1]` |

Resource selection: choose resources with `AvailableStatus=1` and `BasicInfo.ExecAvailableStatus=1`; when `BasicInfo.ResourceType` is present, match requested type. If no usable resource, show candidates/ask; never invent IDs.

Keep `datasource_parsed`; if create/update `DatasourceId` differs, stop and reparse. If user changes `DatasourceId` after parse, reparse. Switching an existing DIRECT LogicalView to DLC requires the user's explicit request in the current turn AND confirmed API support for clearing old `DatasourceId`; otherwise suggest creating a new DLC view or stop.

##### `ListComputeResourceOptions` request-body contract

Verified 2026-08-14 on ap-chongqing. `Page` is a **required** top-level object; omitting it returns `MissingParameter: 请求缺少必传参数 Page`. The minimal correct payload is:

```json
{
  "WorkspaceId": "<injected>",
  "ResourceTypes": [3],
  "Page": {"PageNumber": 1, "PageSize": 10}
}
```

Field notes:

- `ResourceTypes`: `[1]` for DIRECT parse resources, `[3]` for DLC parse resources. Passing `[1,3]` is allowed for enumeration but skill flows always call with a single element to match `source_mode`.
- `Page.PageNumber` / `Page.PageSize`: both integers, both required inside `Page`. Recommended `PageSize=10` (workspaces typically expose 1–5 compute resources per type).
- Response: `Response.Data.Resources[]` (NOT `Data.Data`), plus `Response.Data.Page.TotalCount`. Each `Resources[i]` carries `BasicInfo.{ResourceId,ResourceName,ResourceType,ResourceStatus,ExecAvailableStatus,EngineId}`, `EngineInfo`, `AvailableCU`, `TotalCU`, `AvailableStatus`, `ComputeType`. Pick by `AvailableStatus==1` AND `BasicInfo.ExecAvailableStatus==1`.

Do NOT read the response through `Data.Items` or `Data.Data` — those paths do not exist for this API.

#### 3.4.5 `ClusterType` (Create/Update/List)

`CreateLogicalView`, `UpdateLogicalView`, and `GetLogicalView` all carry an optional top-level `ClusterType` (string). Verified 2026-08-14 via `--describe` output. Semantics (from CLI describe + live data):

| `ClusterType` value | Meaning |
|---|---|
| `""` / absent / `null` | Not set; the server derives cluster class from `DatasourceId` (DIRECT) or the parse `ResourceId` (DLC). All 8 LogicalViews sampled from ap-chongqing ws=17793323750369703 have `ClusterType == null`. |
| `"spark"` | DIRECT LogicalView backed by a Spark-class analysis-version compute resource. Reported informally by the platform team as the expected value when a DIRECT LV is explicitly bound to a Spark analysis cluster; not yet reproduced in this environment. |
| `"tcd"` / `"emr"` / `"dlc"` | Class hints for other DIRECT / DLC cluster types documented by the platform. Values are lowercase strings. |

Skill rules:

- **CREATE**: OMIT `ClusterType` by default and let the server infer. Only set it when the user explicitly gave a cluster class token in the current turn. NEVER hard-code `"spark"` / `"dlc"` from `source_mode` alone — the resolver output does not carry cluster class.
- **UPDATE**: DO NOT touch `ClusterType` unless the user explicitly asked to migrate cluster class. Carry-forward the value read from `GetLogicalView` when re-submitting a metadata-only update; do not clear it.
- **READ / render**: When `ListLogicalViews` / `GetLogicalView` returns `ClusterType=null` (the common case), do NOT synthesize a value — render as absent. When it is a non-empty string, pass it through verbatim.
- **Relation to `DatasourceId`**: `ClusterType` is orthogonal to `DatasourceId`; they describe cluster class vs. connection identity, and a DIRECT LV can have both fields set. A DLC LV must NOT set `DatasourceId` (per §3.4.4) but may still carry `ClusterType` if the user provided one.

If the flow needs to differentiate cluster classes but the field is null, fall back to the parse-time `ResourceId` type (`ResourceTypes=[1]` DIRECT vs `[3]` DLC) — that is authoritative today; `ClusterType` is best-effort metadata.

### 3.5 Columns

`Columns` is ordinary JSON and never Base64. Only `SqlContent` is Base64.

Core fields:

| Field | Rule |
|---|---|
| `ColName` | required; max 128; must start with English letter and then letters/digits/underscore, recommended `^[A-Za-z][A-Za-z0-9_]{0,127}$`; duplicates stop |
| `ColType` | one of `STRING`, `NUMBER`, `TIME`, `BOOLEAN` |
| `ColDesc` | max 500; prefer source comments; generated suggestions require user confirmation |
| `TimeFormat` | optional, only when returned or user-confirmed for TIME |
| `IsVisible` | optional, never silently default/overwrite |

`LogicalViewColumnVO` structure is shared by parse/create/update/get. `GetLogicalView` detail path is `Data.View.Columns`. When updating, preserve the full old field object from detail; parse results are change signals, not final field objects.

#### SQL alias ↔ `ColName` hard rule

Engine result column names are SQL aliases. To avoid NL2SQL mismatch and full-scan fallback:

1. Every projection must have explicit English `AS <alias>`.
2. Alias must match `ColName` regex; no non-English aliases. Display names belong in `ColDesc`.
3. SQL alias and `ColName` must be byte-for-byte equal.

Two-layer validation:

- Before parse, best-effort normalize SQL: parse SELECT list, replace non-English/missing aliases with English identifiers, demote display text to `ColDesc`, and show/generated identifiers for user confirmation when inferred from expressions.
- After parse, trust returned `Columns`: if any `ColName` violates English regex or differs from expected alias, stop and ask for corrected SQL. If alias normalization happens after parse, SQL changed, so reparse.

Do not skip either layer; do not create `ColName` English while SQL alias is non-English.

Type mapping:

| Source type | `ColType` |
|---|---|
| char/varchar/string/text | `STRING` |
| integer/float/double/decimal/numeric | `NUMBER` |
| date/time/timestamp/datetime | `TIME` |
| boolean/bool | `BOOLEAN` |
| array/map/struct/row/json/binary/variant | require SQL cast/extract/explode to scalar, or explicit user-confirmed STRING |

### 3.6 Parse state flow

Call `--describe` before use. Submit Base64 SQL to `ParseLogicalViewSql`.

| Stage | Handling |
|---|---|
| parse returns `Status=1` | use returned `Columns` |
| parse returns `Status=0` | save `QueryId` / `QueryTaskExecId`; poll `GetLogicalViewParseResult` |
| parse returns `Status=2` | stop and pass through `ErrMsg` |
| poll returns `Status=1` | use `Columns` |
| poll returns `Status=0` | keep waiting with backoff |
| poll returns `Status=2` | stop and pass through `ErrMsg` |

Backoff: `2s,2s,3s,3s,5s,5s,8s,8s` max 8 polls. If still running, stop current create/update and tell user parse is still in progress; user may retry later or provide confirmed fields only when parse action is unavailable/timed out.

Polling input keys must follow `--describe GetLogicalViewParseResult`; current model uses `QueryId` / `QueryTaskExecId`. Do not pass unsupported `JobId` merely because it appears somewhere.

### 3.6.1 Parse failure fallback (compute-side transient errors)

`ParseLogicalViewSql` may fail for reasons that are **not** SQL syntax / table-existence problems, e.g. `Status=2` with `Code=FailedOperation.QueryExecuteInvalid, InnerCode=1403170`, or repeated poll timeouts with the parse resource in an unhealthy state. In those cases the SQL itself may still be valid; the parse-side compute cluster is the bottleneck.

Default behavior is unchanged: `Status=2` stops the flow and the exact `ErrMsg` is passed through. The fallback below is **opt-in** and only unlocks when ALL of the guards below hold; when any guard fails, fall back to the default stop-and-report behavior.

Guards (all mandatory, in order):

1. Failure classification: `Code` starts with `FailedOperation.` (typically `QueryExecuteInvalid`/`InternalError`) OR the poll timed out 8 times without any `Status=1` / `Status=2` result. `InvalidParameter.*` and `sqlContent base64 decode failed` are NOT eligible — those are caller errors and must be fixed at the SQL/encoding side.
2. Retry once with a **different** parse `ResourceId` from `ListComputeResourceOptions` that is `AvailableStatus=1` AND `BasicInfo.ExecAvailableStatus=1`. If the retry succeeds normally (`Status=1`), continue the standard flow — no fallback needed. If no alternative resource exists, or the retry also fails with the same class, proceed to step 3.
3. Trusted-columns path (only if the user explicitly provides `Columns` in the current turn, OR the target is a same-connection same-SQL reusable LogicalView already present per §Direct-connection derived-metric carrier reuse-first rule):
   - User-provided `Columns` MUST be a full list (`ColName` / `ColType` / `ColDesc`), one row per SELECT projection alias, English aliases only. Do NOT synthesize `Columns` from the SQL projection list yourself — that is fabrication and is explicitly forbidden.
   - When reusing an existing LV: run `GetLogicalView` on the existing view; if `Data.View.SqlContent` byte-for-byte equals the new plaintext SQL AND `Data.View.DatasourceId` equals the resolved connection id, hand the model / metric / dimension YAML the existing view's one-segment name; do NOT create a new LV under this fallback.

4. Confirmation page must disclose the fallback explicitly:
   > ‘ParseLogicalViewSql 返回 <Code>/<InnerCode>，该错属于解析集群侧问题。我会使用您提供的字段 / 复用已有 LogicalView `<name>`，不再重新 parse。如该 SQL 后续在引擎侧也无法执行，依赖它的模型 / 指标也会失败，需您确认继续。’

Hard prohibitions under this fallback:

- Do NOT skip the trusted-columns / reusable-LV requirement to submit `CreateLogicalView` with an empty `Columns` list or with LLM-synthesized columns.
- Do NOT downgrade `source_mode=DIRECT` to `DLC` (or vice versa) as a way to route around the parse error — mode is fixed by the shared resolver in `common_spec.md` §Direct-connection resolution and remains fixed under fallback.
- Do NOT retry the same failing `ResourceId` more than once; try one alternative, then stop or fall through to trusted-columns.
- Do NOT use this fallback for UPDATE flows that change SQL — UPDATE with SQL change requires a successful reparse (§5.1 step 5); if reparse consistently fails, stop and pass through the server error.

## 4. Create flow

### 4.1 Create directly from SQL

Fixed sequence:

1. Collect name, description, SQL. Run the shared Direct-connection resolver (see `common_spec.md` §Direct-connection resolution) on the user turn: it returns DIRECT (with `DatasourceId`), NONE, or AMBIGUOUS (stop and disambiguate before continuing). Set `source_mode` per §3.4.
2. Local validate name/description/SQL safety.
3. Normalize SELECT aliases per §3.5 before parse.
4. Extract table refs per §3.4.2 for parse-time validity check (mode already fixed by step 1).
5. Run LogicalView name uniqueness precheck through `ListLogicalViews` exact name filtering.
6. Show SQL summary and data-source evidence: for DIRECT, show `ConnectionName` + `ConnectionId` (or UUID) from the resolver; for DLC, state "DLC (no direct-connection trigger)".
7. Parse SQL per §3.6. If parse API fails with `Status=2`, stop. Only when action unavailable/timeout may use user-confirmed/trusted fields.
8. Show field confirmation page.
9. After user confirms, assert plaintext SQL equals parse-time plaintext and `DatasourceId` equals parse-time value when DIRECT.
10. Submit `CreateLogicalView` with once-Base64 `SqlContent`, full `Columns`, and DIRECT `DatasourceId` if needed; never include `ResourceId`.
11. `GetLogicalView` verify and read plaintext SQL and the full field object list. `ListLogicalViews` also returns `Items[].SqlContent` (plaintext) and full `Items[].Columns[]` (verified via `--describe ListLogicalViews` 2026-08-14), so a name-scoped list call can serve as a quick sanity check on SQL + columns for shallow inspection; still use `GetLogicalView` as the single authoritative read before any UPDATE/DELETE because list responses may be truncated on large workspaces.
12. Ask whether to continue creating model/metric/dimension on the view.

### 4.2 Field confirmation page

Show at least `ColName | ColType | ColDesc`; include `TimeFormat` and `IsVisible` when present. If more than 20 fields, page in batches of 20 and then show a final full summary before submit. Accept user fields as Markdown, CSV, or JSON array. Validate names, types, duplicates, and descriptions. Missing descriptions may get suggestions but require confirmation.

Never call `CreateLogicalView` with empty fields, duplicate fields, invalid types, or unconfirmed fields.

### 4.3 Generate SQL from business requirement

If the user gives only a business goal, do not invent final SQL. Flow: identify entities/filters/measures → search candidate tables/fields → show candidates/JOIN draft/confidence → user confirms tables/fields/JOINs → generate SQL draft with explicit English aliases → user confirms/tunes → run §4.1.

JOIN sources must be user-provided or backed by exact metadata/lineage/tag evidence shown to the user. Do not write joins from field-name similarity without confirmation.

## 5. Update flow

### 5.1 Standard flow

1. Locate `Id` using §6.0 exact rule.
2. `GetLogicalView` old plaintext SQL, fields, and old `DatasourceId`.
3. Build SQL diff or metadata update plan in plaintext.
4. Run the shared Direct-connection resolver on the user's update turn. If it returned NONE, carry forward old `DatasourceId` verbatim (no auto-downgrade DIRECT→DLC, no catalog re-scan). If it returned DIRECT with a value different from the old one, treat as an explicit migration and require user confirmation. If it returned AMBIGUOUS, stop and disambiguate.
5. If SQL changes, normalize aliases, parse new SQL with the resolved `source_mode` / `DatasourceId`, merge fields, detect dependencies, and confirm.
6. If only description/field metadata changes and describe confirms `SqlContent` can be omitted, do not pass `SqlContent`, do not reparse, and do not modify old SQL.
7. For SQL changes, assert plaintext SQL and `DatasourceId` equal parse-time values, then submit `UpdateLogicalView` with once-Base64 SQL. For metadata-only updates, submit full/changed fields as supported without SQL.

Migration risk: DIRECT↔DLC or `DatasourceId` changes must be shown; DIRECT→DLC only proceeds when the user explicitly requested it this turn AND API support for clearing old `DatasourceId` is confirmed.

### 5.2 Field merge

`UpdateLogicalView.Columns` is full-cover. Final columns must be merged from `GetLogicalView.Data.View.Columns`, not rebuilt from parse’s three fields.

Merge order:

1. Index old complete field objects by `ColName`.
2. Use parse results only to detect added/still-present/disappeared/type/order changes.
3. Existing fields default to old full objects. Only explicit user confirmation may overwrite `ColType`, `ColDesc`, `TimeFormat`, `IsVisible`.
4. New fields use parse result; missing description needs confirmed suggestion.
5. Disappeared fields are high-risk and are removed only after user confirms.
6. Show final complete field table before submit.

### 5.3 Impact prompt

For SQL/field updates, detect visible dependencies and warn. Search semantic objects by view name, then verify:

- models whose `source` or nested `joins[].source` equals the view name;
- metrics whose `source_table` equals the view or whose `model_ref` depends on it;
- dimensions whose `source` equals the view;
- ontology usage when visible.

Show only exact matches. If retrieval is incomplete, say visible scope is incomplete; never invent “N metrics depend on it”.

## 6. Query and detail

### 6.0 Exact `Id` location

`ListLogicalViews.Keyword` is fuzzy. For GET/UPDATE/DELETE:

1. Call `ListLogicalViews` with the target name or page through all views.
2. Exact-filter `Items[].Name` case-sensitively.
3. Exactly one hit → use `Id`.
4. Zero hits → stop; do not use best fuzzy match.
5. Multiple hits → stop and show candidates.
6. If `Total > PageSize`, keep paging until same-name absence/presence is established.

### 6.1 List

Return concise table `Name | Description | DatasourceId | CreateUserName | UpdateTime`. `ListLogicalViews.Items[]` real field keys (verified via `--describe ListLogicalViews` 2026-08-14) are `{Id, Name, Description, SqlContent, Columns, DatasourceId, WorkspaceId, CreateUserId, CreateUserName, UpdateUserId, UpdateUserName, CreateTime, UpdateTime}`; there is no `Owner` / `CreatedAt` / `UpdatedAt` field, so never render those keys as column headers. Empty list → say no LogicalViews in current Workspace.

### 6.2 Detail

After exact `Id` location, call `GetLogicalView` and return name, description, owner, data source, update time, SQL, and field list. Long SQL may be summarized with an option to expand.

## 7. Delete flow

High-risk and needs explicit confirmation:

1. Locate `Id` exactly.
2. `GetLogicalView` to confirm object.
3. Run visible dependency detection as §5.3.
4. Show delete risk and dependencies/limitations.
5. Require reply equivalent to “confirm delete”.
6. Call `DeleteLogicalView '{"Id":"<id>"}'` and pass through result.

Dependency prompt must distinguish found dependencies, no visible dependencies, and incomplete detection. Service-side dependency check is final and may still block deletion. Do not auto-delete referencing objects, auto-retry after dependency conflict, or invent permission conclusions.

## 8. YAML references

LogicalView is referenced by one-segment name; physical table remains `catalog.schema.table`.

### Model

```yaml
model:
  name: store_ops_model
  label:
    - Store operations model
  description: "Built on store_ops_wide LogicalView"
  type: DEF
  source: store_ops_wide
```

Rules: verify view exists; fields come from `Columns`; physical fact-table selection is skipped; default is single source; extra JOINs require explicit confirmation.

### Metric

```yaml
metrics:
  - name: store_total_gmv
    label:
      - Store GMV
    description: "Store GMV"
    type: SIMPLE
    type_params:
      model_ref: store_ops_model
      source_table: store_ops_wide
      expr: SUM(gmv)
      time_dimension: biz_date
```

Rules: `source_table` one-segment validates as LogicalView, must match model source set, `expr` fields must exist, time dimension source must be consistent.

### Dimension

```yaml
dimensions:
  - name: store_name
    label:
      - Store name
    description: "Store name"
    source: store_ops_wide
    col_name: store_name
    type: CATEGORICAL
```

Rules: `col_name` must exist in LogicalView columns; TIME `time_precision` follows physical stored precision, not reporting period.

## 9. SQL safety

Hard-stop prohibited content:

- DDL: `CREATE`, `DROP`, `ALTER`, `TRUNCATE`.
- DML: `INSERT`, `UPDATE`, `DELETE`, `MERGE`.
- plan/metadata commands: `EXPLAIN`, `ANALYZE`, `SHOW`, `DESCRIBE`.
- permission/admin/session: `GRANT`, `REVOKE`, `SET ROLE`, `SET`, `USE`.
- optimizer/session hints: `/*+ ... */`, `--+ ...`.
- multiple top-level statements.
- references to other LogicalViews in phase 1.

When blocked, list each violation independently, state that the LogicalView was not created/updated, and stop. Do not output a “fixed SQL” that removes violations; the user must provide corrected SQL.

SQL draft generation is allowed only from user-provided or metadata-confirmed tables/fields/JOINs/filters and must be confirmed before parse.

## 10. Permissions and save behavior

- Admins and creators can use/manage per product policy; other permission errors are returned by backend and must be passed through.
- Do not judge whether the user is admin.
- Authorization/grant APIs are not confirmed; if requested, explain that no available authorization API is confirmed and do not fake results.
- LogicalView has no `status`; create/update save is effective. For publish requests, explain no independent publish action exists and do not call extra write APIs.
