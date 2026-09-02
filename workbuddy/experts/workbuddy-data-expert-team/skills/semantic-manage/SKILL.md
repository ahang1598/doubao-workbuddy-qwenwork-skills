---
name: semantic-manage
description: Manage DataBuddy semantic models, metrics, dimensions, LogicalViews, ontology Entities, OntologyDomains, and Entity-domain attach/detach with precise CLI/API guardrails.
layer: L3
lintCheckVersion: "1.0"
tags: [data-development, data-direct-connection]
user-invocable: false
requires:
  - scenarios/common/skills/artifact-uploader
hidden-description: |
  Governance semantic-management skill. Trigger for semantic-layer model/metric/dimension CREATE/UPDATE/ENABLE/DISABLE/DELETE, authoritative read-only semantic details, metric governance reports, LogicalView management, ontology Entity management, OntologyDomain management, and Entity↔BusinessDomain batch attach/detach. LogicalView means the DataBuddy semantic virtual data source managed by ListLogicalViews/GetLogicalView/CreateLogicalView/UpdateLogicalView/DeleteLogicalView, not a warehouse physical VIEW/table; never use search table for LogicalView lookup. Authoritative metric/model/dimension details must use GetMetric/GetSemanticModel/ListDimensions, because asset-discovery forbids PascalCase Describe*/List* APIs and its search whitelist does not cover metric/semantic_model/dimension. Entity uses independent *EntityFromYaml APIs and top-level YAML key entity; OntologyDomain has no YAML form and uses JSON APIs; both are decoupled from CreateSemanticFromYaml. Upload final/draft YAML artifacts through Skill("artifact-uploader") to Studio databuddy/governance/.
---

# Semantic Management

Manage DataBuddy semantic-layer objects with anti-hallucination guardrails:

- **Semantic YAML objects**: model / metric / dimension write operations through `CreateSemanticFromYaml`, `UpdateSemanticFromYaml`, `EnableSemanticFromYaml`, `DisableSemanticFromYaml`, `DeleteSemanticFromYaml`.
- **Authoritative semantic reads**: metric caliber/formula/status, model details/related metrics, dimension type params through `GetMetric`, `GetSemanticModel`, `ListDimensions`.
- **LogicalView**: semantic virtual data source CRUD, SQL parsing, field governance, and one-segment YAML references through independent LogicalView APIs.
- **Ontology layer**: Entity YAML APIs, OntologyDomain JSON APIs, and Entity↔BusinessDomain attach/detach.
- **Artifacts**: final/draft YAML and structured summaries are uploaded through `artifact-uploader` to `databuddy/governance/`.

## Routing contract

- **Semantic authoritative details stay here**. If the user asks what a metric/model/dimension means, its formula, caliber, aggregation, source table, related model/metric, time dimension, type params, or publish status, call PascalCase APIs in this skill. Do not route to `asset-discovery`; `wedatacli cat metric/<name>` only returns `Name`/`Label`/`Description` and is not authoritative.
- **Shallow list browsing stays here**:
  - Dimensions: `wedatacli ListDimensions '{"KeyWord":"","PageNumber":1,"PageSize":20}'`. Response returns `Response.Data.{TotalCount,PageNumber,PageSize,Data:[...]}`; when `TotalCount > PageSize`, loop `PageNumber` from 1 upward until `PageNumber * PageSize >= TotalCount`, do not report a truncated first-page slice as the full set.
  - LogicalViews: `wedatacli ListLogicalViews '{"Keyword":"","PageNum":1,"PageSize":20}'`.
  - Metrics/models: no `ListMetrics` / `ListSemanticModels`; `wedatacli search metric|semantic_model` requires query text. Ask for a topic keyword or exact `--name`; never promise a full metric/model list without a query.
- **Metric/model/dimension search is only a locator**. Use `search -v` to find candidates, then call `GetMetric` / `GetSemanticModel` / `ListDimensions` for authoritative fields and status. Never infer formulas from empty `search.items[].fields.calculate_expr`.
- **Aggregate export / bundle-dump intent stays here and is authoritative-read-only**. When the user asks to "export/dump/collect the entities + referenced dimensions + referenced semantic models of a domain into one YAML" (or any similar cross-object rendering), every rendered field MUST come from an authoritative read-back, not from name/label/description/column/table-context inference: dimension `type` and `type_param` from `ListDimensions '{"KeyWord":"<exact-name>","PageNumber":1,"PageSize":5}'` (or `GetOntologyDomainDimensions` for domain-scoped pulls), then locally exact-match `Data[].Name`; semantic model JOIN / main table from `GetSemanticModel '{"Name":"<name>"}'`; metric `expr`/`agg`/`type_params` from `GetMetric '{"Name":"<name>"}'`; entity YAML from `ExportEntityAsYaml '{"Name":"<entity-name>"}'`. It is explicitly forbidden to guess a dimension's `type` as `TIME` from suffixes like `_time`/`_date`/`create_time` or from a neighbouring TIME dimension in the same source table; unread values must be marked `type: <unknown, pending ListDimensions>` rather than filled in. See `reference/dimension_spec.md` §Read-side rendering and `reference/entity_spec.md` §Export.
- **LogicalView intent always enters this skill**: list/query/detail/SQL/fields/create/update/delete. LogicalView is not a physical warehouse `VIEW`; use `ListLogicalViews` / `GetLogicalView`, not `search table` or `asset-discovery`. `search table` is allowed inside LogicalView SQL drafting (§4.3 business-requirement path) for physical-table candidate discovery only; it is NOT allowed for source-mode inference or `DatasourceId` narrowing (see `reference/logical_view_spec.md` §3.4 and `reference/common_spec.md` §Direct-connection resolution).
- **Physical warehouse view/table/catalog/lineage discovery does not enter this skill** unless it is part of model or LogicalView construction.

## Metric governance report intent

When the user asks for a metric governance report, duplicate semantics, same-name-different-meaning, different-name-same-meaning, or inconsistent caliber:

1. Actively pull data; do not ask for a keyword first. Use default business keywords such as `order`, `payment`, `GMV`, `refund`, `AOV`, `conversion`, `amount`, plus user topics, with `wedatacli search metric "<kw>" -v --top 50`. For model-scoped pulls use `search metric "<topic>" --model <model> -v --top 50`; use `"*" --model <model>` only for list-like pulls.
2. Anti-ghost check: every concrete metric in the report must pass `GetMetric '{"Name":"<name>","WorkspaceId":"<ws>"}'`. If `GetMetric` returns `Code=InvalidParameter.MetricNotFound` with `InnerCode=1403021`, treat the search hit as an index ghost and exclude it (do NOT retry, do NOT rename); when every candidate for a topic keyword is a ghost, stop and report "no verified metric under this topic" rather than fabricating a governance conclusion from ghosts alone.
3. **Zero-search-hit guard**: `search metric` / `search dimension` are indexed queries and MAY return `total=0` even when the objects exist — the index can be stale, un-synced, or partially covered for a workspace whose catalog has not been fully re-indexed. Verified 2026-08-14 on ap-chongqing: multiple concrete keywords (business nouns and even literal metric name stems) returned `total=0` from `search metric` / `search dimension` while `ListOntologyDomainMetrics` / `ListDimensions` under the same workspace returned matching rows. Before concluding "topic empty", fall back to authoritative listers: `ListOntologyDomains` → `ListOntologyDomainMetrics` / `ListOntologyDomainDimensions` per domain (each domain item is wrapped as `Response.Data.Data[i].Data` with sibling `AssetCount` — do NOT dereference `.Data[i].Name` directly), or `ListDimensions '{"KeyWord":"<kw>"}'` (server `KeyWord` is fuzzy — locally exact-filter `Data[].Name`). If both search AND the authoritative lister return zero for the topic, only THEN report "no verified metric under this topic". Never treat zero search hits alone as a governance conclusion.
4. Classify verified metrics only: same name with different expressions, different names with equivalent expressions, and same business meaning with inconsistent expressions across models. Include `name`, model, expression, and discrepancy.

## Vague-concept query intent

Trigger: user asks for metrics/dimensions by a **fuzzy business noun** unlikely to appear verbatim in any metric name (e.g. `用户粘性` / `用户价值` / `客户健康度` / `转化漏斗` / `风控` / `运营质量` / `健康度`). Do NOT search the noun verbatim and conclude `total=0`.

Mandatory expansion procedure (concept-agnostic, workspace-aware):

1. **Decompose into ≥3 concrete measurement sub-families**. Prefer workspace-aware decomposition first: scan `ListOntologyDomains` and call `ListOntologyDomainMetrics` on domains whose `Name`/`Description` plausibly covers the concept — this reveals which sub-families actually exist in this workspace. Only if that yields nothing, fall back to industry-standard sub-families and clearly disclaim the fallback source. See `reference/metric_spec.md` §Vague-concept expansion catalogue for optional common-domain hints (lazy-load, not required in every turn).
2. **Parallel-search each sub-family keyword**, union + dedupe by `Name`, then run the anti-ghost `GetMetric` filter (§Metric governance report intent step 2). Apply the **Zero-search-hit guard** (§Metric governance report intent step 3) on the union; only after both search AND authoritative listers return empty may you report "topic empty".
3. **Group hits by sub-family** in the answer with explicit labels; do NOT collapse into a flat "N metrics found" list. When some sub-families are empty, state so ("‘留存’子族为空") rather than hiding the gap.

Prohibitions: do NOT invent business→metric mappings not backed by `ListOntologyDomainMetrics` or actual search hits; do NOT hard-code an industry-specific keyword dictionary into the answer without disclaiming it is not workspace-verified.

## Caliber / definition question intent ("GMV 和营业收入有什么区别" / "What does <metric> mean?")

When the user asks for a metric **definition, caliber, formula, difference-between-two-metrics, or “什么叫 X”** kind of question, this skill is authoritative — do NOT answer from general business commonsense.

Mandatory pre-answer steps (in order):

1. Extract every concrete metric noun from the question (both sides of “X 和 Y 的区别”, or the single “<X> 是什么”).
2. For each noun, run `wedatacli search metric "<noun>" -v --top 20` in parallel.
3. For every hit whose `Name` or `Label` contains the noun, call `GetMetric '{"Name":"<name>"}'`. Skip ghost results per the anti-ghost rule.
4. When at least one authoritative hit exists per noun, answer strictly from the returned `Response.Data.Data.{Description, SimpleMetricParam.Expr, SimpleMetricParam.Filter, TimeDimension, Source, LogicalViewId, DerivedMetricParam, ...}` fields, quoting `Name` in backticks. State whether each hit is `MetadataStatus=1` (ONLINE) or `2` (DISABLED) so the user knows which caliber is live.
5. When NO authoritative hit exists after search + anti-ghost + `ListOntologyDomainMetrics` fallback (Zero-search-hit guard), say so explicitly and offer either (a) a generic industry note clearly marked "平台未登记与此同名的指标，以下仅为行业通用口径，需您确认" or (b) a proposal to create the metric.

Anti-patterns:

- Answering "GMV 和营业收入的区别…” directly from LLM prior knowledge without any `search metric` / `GetMetric` call.
- Skipping `GetMetric` when `search` already returned a hit — `search` fields are shallow and formulas / calibers are not authoritative there.
- Assuming both nouns exist as platform metrics before checking; if only one exists, explicitly say the other is unregistered and only compare against the registered one’s authoritative caliber.

## Same-name-metric-already-exists handling (CREATE path)

During a CREATE flow, if the search+`GetMetric` combo (§Workflow step 4) finds an existing ONLINE metric whose `Name` OR `Label` collides with the requested metric, do NOT silently rename with a suffix and submit. The user's intent is one of three, and only the user can pick:

1. **Reuse**: use the existing metric — no write, echo its authoritative caliber, ask if that meets the need.
2. **New (different caliber)**: create a suffixed synonym, but only after the user reads the existing caliber and confirms the difference is intentional.
3. **Change caliber**: UPDATE the existing metric (via `UpdateSemanticFromYaml`) — disclose that this affects every downstream reference and any FILTER/DERIVED/RATIO/CUMULATIVE/CONVERSION built on it.

Mandatory confirmation shape (Chinese-first, always show the authoritative caliber pulled from `GetMetric`, never fabricate any missing field):

> `<name>` (ID=<Id>, MetadataStatus=<1|2>, model=<model_name>) 已存在且上线：
> expr = "<SimpleMetricParam.Expr | DerivedMetricParam.Expression>"
> filter = "<SimpleMetricParam.Filter or 无>"
> time_dimension = "<...>"
> 您想要的是以下哪种？
> A. 直接复用这个指标（不写）
> B. 新建一个口径不同的同名后缀指标（需告诉我与现有口径的具体区别）
> C. 修改现有指标的口径（会影响已有下游引用，需您确认）

Explicit prohibitions:

- Do NOT auto-suffix (`_v2`, `_new`, `_2026`) and submit without asking.
- Do NOT report to the user "指标已存在, 我会使用它" without showing the existing caliber — the user may have meant a completely different definition and the existing one just happens to share a keyword.
- Do NOT read "model=<model_name>" from `search.items[].fields.model_name` (search hits may lag or drift); always read it from `GetSemanticModel` / `GetMetric.SourceCategory` context.
- When BOTH `Name` and `Label` differ but the user’s described formula strongly matches an existing metric (same source table + same aggregation + compatible filter after normalization), still show the possible synonym and ask; do NOT auto-reuse without confirmation.

## Single source of truth

- LogicalView details: `reference/logical_view_spec.md`.
- Semantic YAML shared rules: `reference/common_spec.md` plus model/metric/dimension-specific specs.
- Entity: `reference/entity_spec.md`.
- OntologyDomain: `reference/business_domain_spec.md`.
- If this file conflicts with a reference, the reference wins. Runtime CLI parameters must still be checked with `wedatacli --describe <Action>`; specs constrain behavior but do not replace describe output.

## Operation map

### Semantic YAML objects

| Intent | Operation | API | Sensitivity | YAML shape |
|---|---|---|---|---|
| create / add / define | CREATE | `CreateSemanticFromYaml` | L2 create | full definition |
| update / modify / change definition | UPDATE | `UpdateSemanticFromYaml` | L3 write | full definition |
| enable / publish / restore | ENABLE | `EnableSemanticFromYaml` | L3 write | name list |
| disable / unpublish / stop | DISABLE | `DisableSemanticFromYaml` | L3 write | name list |
| physically/permanently delete | DELETE | `DeleteSemanticFromYaml` | L4 delete | name list |

Ambiguous remove-like wording defaults to DISABLE; ambiguous open/restore wording defaults to ENABLE; confirm with the user. DELETE is only for explicit physical/permanent deletion. `YamlContent` limit is 100K chars. ENABLE internal order is fixed: model → dimension → metric. Report status only after read-back; write responses do not carry authoritative `MetadataStatus`.

CREATE / UPDATE accept an optional top-level `DatasourceId` (max 64 chars). Set it only when the shared Direct-connection resolver (`common_spec.md` §Direct-connection resolution) returned DIRECT for the current user turn; the value MUST equal the resolved `ConnectionId` or user-supplied UUID. With `DatasourceId` set, two-segment `db.table` `source` / `source_table` is legal and the server auto-fills `catalogName`; three-segment refs are cross-checked against the reverse-lookup catalog. When resolver returned NONE, do NOT pass `DatasourceId` and keep `source` / `source_table` in the traditional three-segment or LogicalView one-segment form.

### LogicalView

| Intent | Operation | API | Confirmation |
|---|---|---|---|
| list/query LogicalViews | LIST | `ListLogicalViews` | no |
| SQL/fields/detail | GET | `GetLogicalView` after exact `Id` location | no |
| parse SQL / validate fields | PARSE | `ParseLogicalViewSql` + `GetLogicalViewParseResult` | no |
| create SQL as LogicalView | CREATE | `CreateLogicalView` | yes |
| edit/add fields | UPDATE | `UpdateLogicalView` by `Id` | yes |
| delete | DELETE | `DeleteLogicalView` by `Id` | explicit delete confirmation |
| publish | EXPLAIN | no publish API; save is effective | no write |

Hard lines: request `SqlContent` is exactly-once Base64; response `SqlContent` is plaintext; parsing `Status=2` stops the flow; `ResourceId` is parse-only and never submitted to create/update; `DatasourceId` is DIRECT-only and must match parse-time value; `Columns` is normal JSON, never Base64. `source_mode` is decided by the shared Direct-connection resolver in `common_spec.md` §Direct-connection resolution (triggers: `数据源:` / `直连数据源:` / `直连:` / `datasource=` / `connection=` / `direct=` / explicit `DatasourceId` UUID). Resolver DIRECT → submit `DatasourceId`; resolver NONE → DLC (non-three-segment SQL under DLC will fail server-side and the error passes through); resolver AMBIGUOUS → stop and disambiguate. Do NOT scan `get catalog` / `get catalogs` / `wedata-connection-id` to auto-infer DIRECT.

### Entity

| Intent | Operation | API | Confirmation |
|---|---|---|---|
| create entity | CREATE | `CreateEntityFromYaml` | yes |
| update entity | UPDATE | `UpdateEntityFromYaml` | yes |
| disable entity | DISABLE | `DisableEntityFromYaml` | yes |
| enable entity | ENABLE | `EnableEntityFromYaml` | yes |
| delete entity | DELETE | `DeleteEntityFromYaml` | explicit delete confirmation |
| export YAML | EXPORT | `ExportEntityAsYaml` | no |
| list/get/graph | LIST/GET/GRAPH | `ListEntities` / `GetEntity` / `ListEntityGraph` | no |
| attach to domain | ATTACH | `BatchAttachEntityBusinessDomain` | yes |
| detach from domain | DETACH | `BatchDetachEntityBusinessDomain` | yes |

Entity YAML top-level key is `entity`, not `models`/`metrics`/`dimensions`. Full CREATE/UPDATE YAML requires `version: 1.0`; compact ENABLE/DISABLE/DELETE YAML must not include `version`. `business_domain` is a Name, optional by service behavior, and may be string or list; default behavior is to ask for a domain unless the user explicitly wants no domain. UPDATE is full-cover rebuild; confirmation must show added/kept/deleted sources, attributes, and relations. Entity UPDATE accepts `Status=2`; Entity DELETE accepts `Status=1` or `2`, unlike semantic YAML DELETE.

### OntologyDomain

| Intent | Operation | API | Confirmation |
|---|---|---|---|
| list/get domains | LIST/GET | `ListOntologyDomains` / `GetOntologyDomain` | no |
| list domain assets | LIST | `ListOntologyDomainEntities/SemanticModels/Metrics/Dimensions` | no |
| list domain models/orphans/all | LIST | `ListDomainsModels` | no |
| create domain | CREATE | `CreateOntologyDomain` | yes |
| update name/description/owners/labels | UPDATE | `UpdateOntologyDomain` | yes |
| delete domain | DELETE | `DeleteOntologyDomain` | explicit delete confirmation |

OntologyDomain has no YAML form. `Labels` is required on CREATE; label IDs must be real IDs from `ListLabels`. `UpdateLabels=true` makes `Labels` overwrite the full old set; warn about removed labels. Domain deletion does not block on assets; service detaches/cleans as needed, but show visible asset counts before confirmation.

## Workflow

1. **Classify intent and object type** using the maps above.
2. **Run the shared Direct-connection resolver** on the user's current turn (see `common_spec.md` §Direct-connection resolution). Its output (`DIRECT` with `DatasourceId` / `NONE` / `AMBIGUOUS`) feeds every downstream write path that can accept `DatasourceId` (semantic YAML CREATE/UPDATE, LogicalView PARSE/CREATE/UPDATE). AMBIGUOUS stops here for disambiguation.
3. **Load only necessary references**:
   - model create/update: `common_spec.md` + `model_spec.md`.
   - metric create/update: `common_spec.md` + `metric_spec.md`.
   - dimension create/update: `common_spec.md` + `dimension_spec.md`.
   - semantic enable/disable/delete: `common_spec.md`.
   - LogicalView any operation: `logical_view_spec.md`.
   - Entity any operation: `entity_spec.md`; attach/detach also `business_domain_spec.md`.
   - OntologyDomain any operation: `business_domain_spec.md`.
4. **For CREATE, search before asking for missing details**. Use provided name/label/business terms to check same-name/same-label/synonym candidates first. If conflict exists, stop, show candidates, recommend a suffixed new name, and ask whether to reuse/update/rename/create.
5. **Build YAML or JSON** from reference specs. Do not invent sources, fields, joins, owners, label IDs, or formulas.
6. **Run mandatory validation** before user confirmation:
   - CREATE semantic YAML: existence/uniqueness, `model_ref`, source consistency, field existence.
   - UPDATE semantic YAML: object exists and (for metric/model) `MetadataStatus=1`; **dimension is active whenever `MetadataStatus in (1, 3)`** (per `reference/dimension_spec.md` §`MetadataStatus` authoritative enum). Entity UPDATE is exempt.
   - ENABLE semantic YAML: applies to model / metric / entity only — object exists and `MetadataStatus=2`; when enabling a model, read related metrics and warn that metrics disabled by model cascade will not auto-recover. **Dimensions do NOT participate in ENABLE/DISABLE**; refuse and route to CREATE / DELETE.
   - DELETE semantic YAML: object-level precondition — `dimension` may be deleted directly from active state (`MetadataStatus in (1, 3)`); `model` and `metric` MUST be `MetadataStatus=2` (disabled) first. LogicalView/entity exceptions follow their specs.
   - LogicalView write/delete: exact `Id` location, SQL parse/field validation, dependency visibility check, and confirmation.
7. **Show confirmation** before any write:
   - Semantic YAML: show the YAML and “confirm to submit <operation>”.
   - LogicalView: show name, description, data source, SQL summary/diff, field table, catalog evidence, dependency risk.
   - Entity UPDATE: show full-cover diff with add/keep/delete.
   - DELETE: warn irreversible impact and require explicit confirmation.
8. **Submit API** only after confirmation. Use `wedatacli <Action> '<JSON>'`; omit `WorkspaceId` unless cross-workspace and the user supplies a numeric long ID.
9. **Parse response and read back** status/IDs when reporting status. If stdout is truncated, read the file path from the wrapper’s truncation JSON; never parse `preview_head_1k` as complete.
10. **If the user changes anything after confirmation preview**, restart validation from intent/reference/search/build/validate/preview; do not patch YAML and submit directly.

### CLI wrapper invariants

Apply on every `wedatacli` write and every `Get*` / `List*` read-back that feeds validation gates. These rules exist because we have observed stderr-decode crashes on non-UTF-8 bytes, empty CreateSemanticFromYaml stdout on transport issues, and API paging parameter drift (`ListDimensions` uses `PageNumber`; `ListLogicalViews` uses `PageNum`; a wrong paging key or a wrong-casing filter is hard-rejected by the CLI param validator as `未知入参 [<key>]`).

- **stderr tolerant decoding**: decode CLI stderr with `errors='replace'`; do NOT let a non-UTF-8 stderr byte crash the wrapper and abort a write mid-flight. stdout stays strict UTF-8.
- **Truncation / spill**: when stdout exceeds the wrapper envelope, the CLI writes a spill JSON `{truncated: true, file: "/tmp/wedatacli-*.json", preview_head_1k: "..."}`. Read `file` and parse the full JSON body from there; never parse `preview_head_1k` as complete (already in Workflow step 9, restated here as a hard rule).
- **Read-before-resubmit iron rule**: if a write CLI call returns an exception, an empty stdout, a decode failure, or an ambiguous non-JSON body, do NOT resubmit the same payload. First run the single-object authoritative read (`GetMetric` / `GetSemanticModel` / `ListDimensions` with exact-name filter, `GetLogicalView` for LV, `GetEntity` for entity) to determine whether the object already exists / partially exists. Only after read-back proves the object is missing may you resubmit; if read-back shows the object is present, treat the write as effectively-succeeded and proceed to the next batch. This is the only defense against duplicate-create on empty-return failure modes.
- **Paging parameter check**: any API called with paging MUST first be confirmed via `wedatacli --describe <Action>`. Verified 2026-08-14 paging-key inconsistencies across the semantic-manage surface: `ListDimensions` uses flat `PageNumber` + `PageSize`; `ListLogicalViews` uses flat `PageNum` + `PageSize`; `ListConnections` uses nested `PageRequest:{PageNumber,PageSize}`. Passing the wrong paging key or wrong-casing filter (e.g. `Keyword` where `KeyWord` is required, or vice versa) is HARD-REJECTED by the CLI wrapper as `未知入参 [<key>]（<Action> 没有这些字段，已拒绝调用...）` — the request never reaches the server, so hard-rejection cannot be mis-read as “object absent”; still, do NOT infer object absence from any error that is a param-validation failure (parse the wrapper stderr and treat as CLI usage error, not as an empty page).
- **Authoritative read-back combo**: when reporting object state, use the single-object authoritative APIs, never search hits:
  - metric: `GetMetric '{"Name":"<name>"}'` → `Response.Data.Data.MetadataStatus` (`1`=ONLINE, `2`=DISABLED) + top-level `Response.Data.Data.SourceCategory` (`0`=data table, `1`=LogicalView) + top-level `Response.Data.Data.LogicalViewId` (when `SourceCategory=1`) + nested `Response.Data.Data.Source.{CatalogName,DatabaseName,TableName}` (when `SourceCategory=0`) for source-form gate; MetricVO layout per `wedata_2025-10-10_GetMetric.json` (`SourceCategory` / `LogicalViewId` at top level "与 Source 二选一", `Source` is a 5-field SourceVO with NO `LogicalViewId` / `SourceCategory` inside). Metric-not-found: `Code=InvalidParameter.MetricNotFound, InnerCode=1403021` (throws, does NOT return empty Data).
  - semantic model: `GetSemanticModel '{"Name":"<name>"}'` → `Response.Data.Data.MetadataStatus` + `MainNode` / `TableList` / `NodeTree` per `common_spec.md` and `metric_spec.md`. **Model-not-found returns HTTP 200 with `Response.Data = {}` (no nested `Data.Data` key) — does NOT throw an error**, so always check `if not response.get('Response',{}).get('Data',{}).get('Data'): treat as missing/ghost` before dereferencing fields. Verified 2026-08-14; this is asymmetric to `GetMetric`.
  - dimension: `ListDimensions '{"KeyWord":"<name>","PageNumber":1,"PageSize":5}'` → locally exact-match `Response.Data.Data[].Name` (server `KeyWord` is fuzzy — never trust the first hit). `Type` returns as int64 `{1:CATEGORICAL, 2:TIME, 3:DICT}` — do NOT map by CLI describe's `0/1/2` legend (that legend is wrong). See `reference/dimension_spec.md` §Read-side rendering.
  - LogicalView: exact-`Id` locate per `logical_view_spec.md` §6.0, then `GetLogicalView`
  - ONLINE judgment: `MetadataStatus=1` on metric / model; **dimension is active when `MetadataStatus in (1, 3)`** (`3` is legacy draft-enum residue treated as active per `reference/dimension_spec.md` §`MetadataStatus` authoritative enum). Ontology domain uses `Status` (not `MetadataStatus`) AND the domain `Status` semantic is INVERTED vs. `MetadataStatus`: `Status=0`=Live/Published, `Status=1`=Offline — see `reference/business_domain_spec.md` §State matrix

### CLI `--describe` known-inaccuracy table

The following describe-metadata claims have been verified as **stale or wrong** against live behavior (ap-chongqing, 2026-08-14). When they conflict with this skill's contracts, **trust the skill, not the describe output**. Do not "correct" the skill to match describe.

| API | describe says | Reality (verified) | Skill authority |
|---|---|---|---|
| `ListDimensions` | `TypeList: 0-普通维度 1-时间维度 2-字典维度` | int64 enum is `{1:CATEGORICAL/普通, 2:TIME/时间, 3:DICT/字典}`; `TypeList:[0]` returns 0 rows; no dimension in the workspace has `Type=0` | `reference/dimension_spec.md` §Read-side rendering |
| `ListDimensions` / `GetMetric` / `GetSemanticModel` `MetadataStatus` | no explicit enum legend on describe | Metric / model state has **exactly two** values: `1=ONLINE`, `2=DISABLED`. **Dimension state is `1=已创建/active`, `2=已删除/deleted` (no draft, no disable)**, and a legacy value `3` observed on many live dimensions is retired-enum residue that MUST be treated as active-equivalent to `1`. Any other integer on metric/model is unexpected; surface it to the user. | `reference/dimension_spec.md` §`MetadataStatus` authoritative enum for dimension; `reference/common_spec.md` for metric/model. Never ask the user to "re-publish" or "re-disable" a dimension with `MetadataStatus=3` — those actions do not apply to dimensions. |
| `DeleteSemanticFromYaml` | "幂等操作。... 配置项不存在时跳过（幂等）" | NOT idempotent — server returns per-item `Success=false, ErrorMessage="<对象>不存在"`, `FailedCount>0` when a name in the list is missing | `reference/common_spec.md` §Disable / Delete YAML shape (Idempotence row) |
| `GetMetric` | `Type: 0-简单指标 1-派生指标 2-转化指标 3-比例指标 4-累积指标` (5 values) | Numeric legend is unreliable: YAML type family has **6** members and `Type=1` records with only `SimpleMetricParam` are SIMPLE (not 派生). Details in `reference/metric_spec.md` §YAML type ↔ GetMetric read-back mapping. | Judge YAML type by **which `*MetricParam` sub-object is populated** (`SimpleMetricParam` / `DerivedMetricParam` / `RatioMetricParam` / `CumulativeMetricParam` / `ConversionMetricParam`); for FILTER, additionally `SimpleMetricParam.Filter` non-empty. Treat numeric `Type` as display-only. |
| `ListDimensions` | `TypeParam.TimePrecision` / `TypeParam.WindowUnit` typed as raw `int64` with no enum legend | Both fields ARE int64 code numbers (observed `TimePrecision ∈ {3,5,7,8}` and `WindowUnit ∈ {4,5,7,9}` across 18 live TIME dimensions) but the YAML write side uses string tokens like `DAY` / `SECOND` / `HOUR`. The exact int↔string map is not currently recoverable from CLI describe alone. | `reference/dimension_spec.md` §Read-side field mapping details — do NOT hard-code an int→string map; render `type_param.time_precision: <int:N, pending write-side enum>` when only the numeric form is available |
| `ListComputeResourceOptions` | describe shows `Page` as an optional-looking nested object | `Page` is **required**; omitting it returns `MissingParameter: 请求缺少必传参数 Page`. Payload must be `{"WorkspaceId":..., "ResourceTypes":[1|3], "Page":{"PageNumber":1,"PageSize":10}}`. Response items are at `Response.Data.Resources[]`, NOT `Data.Data` or `Data.Items`. | `reference/logical_view_spec.md` §3.4.4 sub-block `ListComputeResourceOptions request-body contract` |
| `CreateLogicalView` / `UpdateLogicalView` / `GetLogicalView` | describe lists `ClusterType` (string) with no enum legend and no usage rule | Field is optional; server infers cluster class from `DatasourceId` (DIRECT) or parse `ResourceId` (DLC) when omitted. All 8 sampled LVs on ap-chongqing have `ClusterType=null`. Do NOT hard-code a value from `source_mode` alone. | `reference/logical_view_spec.md` §3.4.5 `ClusterType` |
| non-LV metric/dimension `LogicalViewId` | field is a string; describe suggests empty string when unused | Empty case is the LITERAL STRING `"0"`, not `""`. Predicate must be `LogicalViewId not in ("", "0", None)` before treating a metric/dimension as LV-backed. | `reference/common_spec.md` derived-metric availability rule (LogicalViewId "0" note) |

If a new describe/skill mismatch is discovered, add a row here rather than editing the describe or silently changing skill behavior.

## Search and status helpers

- `search` needs a positional query except identifier filters. Use `-v` for rich fields and `--top N` to control size.
- Identifier filters usable without positional query: `--name`, `--col`, `--source`.
- Association filters require query text: `--model`, `--dim`, `--metric`, `--type`. Use topic + flag for relevance, or `"*" + flag` only for pull-list scenarios.
- `search dimension --type` uses strings `CATEGORICAL|TIME|DICT`; numeric `0/1/2` returns no rows. The underlying `ListDimensions.Type` int enum is separate; see `reference/dimension_spec.md` §Read-side rendering for the int↔string map.
- Authoritative paths:
  - `GetMetric` → `Response.Data.Data.*`.
  - `GetSemanticModel` → `Response.Data.Data.*`.
  - `ListDimensions` → `Response.Data.Data[]` with list metadata under `Response.Data`.
  - `ListOntologyDomains` items → each element is a wrapper `{Data: OntologyDomainVO, AssetCount:{EntityCount,SemanticModelCount,MetricCount,DimensionCount}}`; the domain fields (`Id`, `Name`, `Description`, `Status`, `RelatedTags`, owners, times) live under `Response.Data.Data[].Data.*`, and asset totals per tab live under `Response.Data.Data[].AssetCount.*`. Domain uses `Status` (not `MetadataStatus`) and `RelatedTags` (not `Labels`) on read-back; `Labels` is a write-side CREATE/UPDATE key only.
  - `GetOntologyDomain` → `Response.Data.Data.*` with the same domain field set (`Id,Name,Description,Status,RelatedTags,...`).

## Response handling

For semantic YAML write responses, use `Success`, `Message`, `Summary`, `Model`, `Dimensions`, `Metrics`; item-level failures are in `ErrorMessage`. For Entity write responses, use `EntityId`, `EntityName`, `OperationType`; write responses do not include `Status`.

Standard handling:

| Failure | Handling |
|---|---|
| not disabled when deleting semantic YAML | Object-level: `dimension` skip — direct DELETE from ONLINE is allowed (server accepts, skill accepts). `metric` — server hard-rejects with `1403043 上线指标不能删除`; ask user to disable first, then retry. `model` — server would accept but skill guardrail refuses submit (model DELETE cascades to its metrics, high-risk irreversible fan-out); ask user to disable first, only bypass on explicit user request with cascade + irreversibility confirmation on the same turn |
| dimension dependency conflict | list dependent metrics if known; ask user to handle them |
| permission/auth error | pass through original cloud error; do not invent admin requirement |
| duplicate/same name | stop, show conflict, recommend suffixed name |
| model create rejected with `same meaning as model [X]` (InnerCode 1403002) | do NOT retry with a renamed model. Parse `X` out of the message, run `GetSemanticModel '{"Name":"X"}'` to confirm it is online, then rebuild the pending metric YAML with `model_ref: X` and resubmit; show the switch to the user before submit |
| RATIO dependency rejected with `must be a cumulative metric` (1403002) | stop, prompt user to first create the required CUMULATIVE metric (window on top of the SIMPLE base); do not silently drop the RATIO |
| FILTER rejected with `Dimension not found` (1403002) | do not rewrite to a physical column. Search/reuse an online semantic Dimension on the same source/column, or create that Dimension first, then resubmit the FILTER |
| CONVERSION rejected with `conversion_dimension=[x] 不存在` (1403002) | stop, prompt user to first create the CATEGORICAL/DICT Dimension with that name; do not rewrite the physical column into the field |
| dependent metric not found on batch CREATE | server does not topo-sort within one YAML; resubmit atomic metrics first, then derived metrics referring to them |
| missing object on DELETE | server returns per-item `Success=false, ErrorMessage="<对象>不存在"` (NOT idempotent); report as failure in the output table and ask user how to proceed |
| LogicalView Base64/WAF error | encode plaintext SQL once with standard Base64; if already compliant, pass through |
| LogicalView field/dependency/parameter error | stop, show exact error, retry only exact-`Id` location once when `Id` is missing/invalid |

## Output format

- Success: table `Type | Name | Status | ID`, plus `Total N, success N, failed 0`.
- Partial failure: table `Type | Name | Status | Detail`, plus summary and ask whether to fix failed items.
- Read-only: concise tables and exact authoritative fields; state when only visible dependencies were checked.

## Safety constraints

- Never submit write APIs before user confirmation.
- Never invent source tables, fields, joins, SQL, label IDs, object IDs, formulas, statuses, owners, or dependencies. Never modify user-provided identifiers (table/view/field/metric/dimension/entity names, including hash-like suffixes) via edit-distance guessing; use them byte-for-byte and quote them in backticks when echoing.
- Do not call legacy `DeleteYamlConfig`; use `DeleteSemanticFromYaml`.
- Do not fake LogicalView publish/enable/status; save is effective.
- Do not auto-expand ENABLE/DELETE/UPDATE scope. Ask before adding dependent metrics/models.
- One physical source (three-segment `catalog.schema.table`) supports at most one semantic model; the server rejects duplicates as `same meaning as model [X]`. When a metric CREATE targets a physical source already covered by an existing model, reuse that model; never wrap the source in a LogicalView to bypass this check. See `reference/metric_spec.md` Complex-metric decision tree and `reference/logical_view_spec.md` negative list.
- Do not put CASE WHEN / WITH / UNION / IN (SELECT) into metric `expr`. The server may accept it on write but the semql query layer will refuse the metric at query time; decompose with FILTER metrics.
- Batch CREATE payloads must be split by dependency layer: atomic metrics (SIMPLE) and required Dimensions submit first; FILTER/DERIVED/RATIO/CUMULATIVE/CONVERSION submit only after their dependencies are read-back verified. The server does not topologically sort inside one YAML.
- Direct-connection derived-metric routing: when the shared Direct-connection resolver returns DIRECT AND the plan contains any of FILTER/DERIVED/RATIO/CUMULATIVE/CONVERSION on the same direct-connection source, do NOT submit two-segment `db.table` `source` / `source_table` for the base SIMPLE metrics. The server persists a two-segment SIMPLE with top-level `SourceCategory=0` + empty `Source.CatalogName`; the metric-level `Source.DatasourceId` field is `x-tcapi-visibility=2` (per GetMetric OpenAPI schema `wedata_2025-10-10_GetMetric.json`) so CLI stdout may hide or downgrade it and it is not an authoritative direct-connection id source. The derived-metric validator then hard-rejects the dependents with `1403314 Source table path is incomplete for metric: <name>`. Route through a plain-projection DIRECT LogicalView carrier (`logical_view_spec.md` §Direct-connection derived-metric carrier), reuse an existing carrier on the same connection first, and reference it by one-segment name — the resulting SIMPLE metrics will read back as top-level `SourceCategory=1` + `LogicalViewId=<id>`, which is the state the derived-metric validator requires. Verified 2026-08-14. See `metric_spec.md` §Batch submission contract, source-form gate, and `common_spec.md` §`source` / `source_table` rule.
- DICT dimension keys are business mapping labels and are semantically decoupled from physical column types; preserve user-provided mappings and only give a mild confirmation note.
- Do not operate Entity through semantic YAML APIs or semantic objects through Entity APIs.
- `BatchDetachEntityBusinessDomain.BusinessDomainId` is required and must be > 0; DetachAll does not exist. Detach from multiple domains by looping each concrete domain.
- **FILTER metric must not self-reference**. In a FILTER YAML, every entry under `type_params.metrics[]` MUST be a different SIMPLE/derived metric name, never the FILTER metric's own `name`; the same rule applies to DERIVED / RATIO / CUMULATIVE `type_params.metrics[]` and to CONVERSION `type_params.base_metric.name` / `type_params.conversion_metric.name` (both are objects with a `name` field per `reference/metric_spec.md` §CONVERSION). Even when the server accepts a self-referential write, the semql query layer cannot resolve the metric at runtime. Standard shape when the user says "改现有 metric 口径 → 加 filter": (a) rename the existing SIMPLE to `<name>_raw`, then CREATE a FILTER under the original `<name>` with `type_params.metrics: [{name: <name>_raw}]`; or (b) CREATE a new FILTER with a suffixed name (e.g. `<name>_excl_refund`) whose `type_params.metrics[0].name` points to the original SIMPLE and disable the SIMPLE — pick with the user before submit.
- **Never re-List / re-Search the just-written object for "self-verification" after CREATE/UPDATE succeeds**. After a `CreateSemanticFromYaml` / `CreateLogicalView` / `Create*` write returns `Success:true` with an `Id`, the ONLY authoritative read-back is `Get<Object>` by that `Id`; running `List<Object>s` / `search <object>` with the same name will find the object you just created and mis-classify it as a pre-existing name-collision. This is a hard anti-pattern distinct from the `Read-before-resubmit iron rule` (§CLI wrapper invariants), which only applies when the write returned exception / empty stdout / decode failure. Verified 2026-08-14 on LogicalView CREATE round-trip: `ListLogicalViews` executed after a successful `CreateLogicalView` returned the fresh `Id` with matching SQL and description, and the naive re-check flow aborted the case as "same-name conflict" though nothing was actually stale.
- **`search table` results must be cross-checked against `get catalogs` accessibility before use** (LogicalView SQL drafting §4.3 business-requirement path). The search index is workspace-scoped but may include catalogs the current user has no access to; picking such a hit and continuing with `wedatacli get schemas <inaccessible-catalog>` triggers `WorkspaceForbidden` and the case dead-ends. Correct flow: run `get catalogs` once → keep the set of accessible catalog names → drop every `search table` hit whose `catalog` is not in that set → if the accessible set is empty after filtering, fall back to `get schemas` / `get tables` on the accessible catalogs and match by keyword locally. Do NOT retry the forbidden catalog; do NOT ask the user to grant permission before confirming an accessible fallback is empty.
- **User-specified identifiers (table / view / field / metric / dimension / entity names) MUST be used byte-for-byte and MUST NOT be replaced by "same-meaning" alternatives via edit-distance / synonym / column-family guessing**. When `ListTables` / `search table` does not return a user-specified name in the first page, do NOT switch to a similar-looking table (e.g. `order_detail` → `dwd_fact_payment_order`, `order_amount` → `payment_amount`). Instead: (a) `GetTable '{"CatalogName":"<c>","SchemaName":"<s>","TableName":"<user-specified>"}'` to confirm existence; (b) cross-check `ListDimensions` whose `Source.TableName` equals the user's table name (existing dimensions prove the physical table exists even when index is stale); (c) only if both authoritative reads confirm the table truly is missing, ask the user whether to switch tables — never switch silently. This applies equally to column names: `order_amount` and `payment_amount` are NOT interchangeable and must not be swapped without explicit user consent.

## Trigger examples

Should trigger: define/create/update/delete/enable/disable semantic models, metrics, dimensions; ask metric formula/caliber/status/source/related model; list dimensions/LogicalViews; create/update/delete LogicalView; view LogicalView SQL/fields; create/update/export/list/get/graph Entity; create/update/delete/list/get OntologyDomain; attach/detach entities to/from business domains; metric governance reports.

Should not trigger: run data queries or get metric values (`semantic-analysis`), write ad-hoc SQL (`intelligent-query`), create warehouse tables, discover physical tables/catalogs/schemas/physical VIEW lineage unless needed as a sub-step here.

## Artifact handling

Upload final/draft YAML and structured batch summaries via `Skill("artifact-uploader")` with `domain="governance"`. Only Markdown artifacts, single file ≤ 5 MB, batch through `op="upload_batch"`, echo `studio_link`, and show `errors[]` on failure. Never include unverified IDs or statuses in artifacts.
