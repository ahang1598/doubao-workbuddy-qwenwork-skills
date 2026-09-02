---
name: unity-catalog-manage
description: Verified Unity Catalog governance for metadata CRUD, lineage, asset search/recommendation, tags, AI descriptions, and audit-log inventory.
layer: L3
tags: [data-development]
user-invocable: false
requires:
  - scenarios/common/skills/artifact-uploader
lintCheckVersion: "1.0"
hidden-description: |
  Verified Unity Catalog governance: metadata CRUD, lineage, asset search/recommendation, tag governance, AI descriptions, and audit-log inventory. Upload governance artifacts through Skill("artifact-uploader") to Studio under databuddy/governance/.
  Trigger for: Catalog/Schema/Table/View/Volume/Model/Function/MLflow (model version, model alias) lifecycle; tagging on tables/columns/assets covering business/category/BI/report/department/project/purpose/core-asset/governance/custom/property/masking-visible/batch tags and asset-tag lookup; lineage and upstream/downstream; asset search, table recommendation, favorite (收藏), view history (访问历史); AI table/column comment generation (自动生成表描述 / 生成字段注释 / AI 描述 / 补全字段注释); business metadata and owner transfer (业务元数据 / owner 转移); compute-job submission via SubmitJob (submit job / 提交作业 — NOT standalone compute-resource enumeration); audit logs, cold-table or unused-asset inventory.
  Do not trigger for: PII/GDPR/phone/ID-card/sensitive-field scans/masking-policy/data classification (use data-classification); metrics/dimensions/semantic models/measure definitions AND LogicalView / 逻辑视图 list/detail/create/update/delete (use semantic-manage; physical warehouse VIEW tables remain in scope of this skill); grants/roles/permission policies (use the permission module); multi-step table planning loops that call SavePlan/GetPlan/ListPlans/LocateSourceTable/CreateTable with DDL generation (route to data-engineering plan skill; this skill only reads/writes catalog metadata on already-existing tables); standalone compute-resource enumeration such as "查看/查询/列出可用计算资源 / 资源列表 / 资源组 / ListComputeResourceOptions on its own" — this is a **basic read-only** workspace-level resource-lookup intent that does NOT touch Catalog/Schema/Table governance and MUST NOT enter this skill (owned by `asset-discovery` via `wedatacli get compute-resources`; `ListComputeResourceOptions` here is kept only as a helper input for SubmitJob).
---

# Unity Catalog Governance Skill

## Mission

Use verified Wedata3 Unity Catalog APIs to govern Catalog-Schema-Data assets: Table/View, Volume, Function, Model, lineage, search, tags, AI descriptions, and audit logs.

## When to use

- Create, read, update, or delete Catalog / Schema / Table / View / Volume / Model / Function metadata.
- Query upstream or downstream lineage.
- Search assets, manage favorites, or inspect view history.
- Recommend or locate tables for business analysis, for example "which table should I use to analyze order-to-approval latency" or "which table has order time and approval time fields". This is an asset-search plus metadata-read task: call `SearchAsset` / `SearchAssetQuickly`, then use `GetTable` to verify fields such as `order_purchase_timestamp` and `order_approved_at`, and return table name, matched fields, and recommendation rationale. Do not reject this as out of scope and do not route it to data-engineering just to write SQL.
- Apply governance/custom/property/masking tags to assets.
- Transfer metadata ownership, fetch business metadata, or generate AI descriptions.
- Submit compute jobs via `SubmitJob` (query-only compute-resource enumeration is OUT OF SCOPE here; `ListComputeResourceOptions` in this skill is only a helper input for `SubmitJob`, never a standalone routing target — see "When not to use").
- Query Wedata audit logs for operations, logins, asset access, API calls, permission changes, or usage-based asset inventory.

## When not to use

- Execute SQL queries or preview data; use a SQL engine or Notebook.
- Manage permissions, policies, or roles; use the permission module.
- Manage semantic objects such as metrics, dimensions, semantic models, or measure definitions; use ontology-service YAML APIs via semantic-manage.
- Manage workflow scheduling or data integration; use the corresponding scheduling/integration module.
- Standalone compute-resource enumeration ("查看/查询/列出可用计算资源" / "资源组列表" / "我的执行资源" / user asks `ListComputeResources` or `ListComputeResourceOptions` on its own without any SubmitJob follow-up) is a read-only workspace-level resource lookup, NOT Catalog governance. Route to `Skill("asset-discovery")` (`wedatacli get compute-resources [--keyword <kw>] [--resource-type <csv>] [--status <csv>]`); do not emit the "这属于 Unity Catalog 治理范畴" opener.

## Required inputs

- **WorkspaceId**: most APIs are auto-injected by `wedatacli` from `~/.wedata/config.json` and marked `[auto injected]` in `--describe`; examples omit it by default. Explicitly override only for cross-workspace calls. Exceptions: `ListLineages` — `WorkspaceId` is auto-injected by the CLI; do NOT pass it explicitly in the payload; `SubmitJob.Job.WorkspaceId` is a nested business field and must be supplied; `UpdateLabels.PolicyBindingUpdate.WorkspaceId` is the target workspace for a policy binding and must be supplied.
- **CatalogName**: usually required for Catalog-level operations.
- **SchemaName**: usually required for Schema-level and lower operations.
- **Object identity**: name or `FullName` for Table/View/Volume/Model/Function operations.
- **Intent**: the governance action, such as create, read, update, delete, tag, or lineage query.

## Workflow

### 1. Identify target and scope

Determine the hierarchy level (Catalog -> Schema -> Table/View/Volume/Model/Function) and action type (CRUD / search / tag / lineage / audit).

### 2. Select API and build the request

#### API-call policy

**Priority 1: use this whitelist and load only needed references**

- Pick an API domain from `2.0 API index`, then load the matching reference for examples, business notes, and edge cases. Section `2.16` audit-log tasks are SQL tasks: the main agent builds SQL and runs `wedatacli query-sql` directly.
- References are fast templates, not the final contract. If a reference conflicts with `wedatacli --describe <Action>`, `--describe` wins.

**Priority 2: verify risky calls with `--describe`**

- Before writes, complex nested payloads, critical enums, historically drifting fields, or after parameter errors such as `InvalidParameter`, `InvalidParameterValue`, missing field, or type mismatch, run `wedatacli --describe <Action>` and rebuild the request from the authoritative definition.
- Examples: `wedatacli --describe CreateCatalog`, `wedatacli --describe BatchVoteAssetTag`, `wedatacli --describe ListLineages`.

**Runtime anti-hallucination baseline**

- If an API is not in `2.0 API index`, first prove it exists with `wedatacli --describe <Action>` before calling it.
- If `--describe` returns `unknown tool`, stop. Do not guess a similar name, symmetric API, or business synonym; report that the current CLI does not expose the capability.
- Never invent enum values, field names, or request structures unless they are documented or verified by `--describe`. High-risk fields include `Type`, `SourceType`, `AssetType`, `MetaType`, `Direction`, `Operation`, and `OwnerType`.
- `ListLineages.Direction` accepts only uppercase `INPUT` (upstream) or `OUTPUT` (downstream); other values are rejected as parameter errors (server may respond as either HTTP 503 with empty body or as `InvalidParameterValue.DirectionInvalid` — treat both as parameter errors, do NOT retry as service outage). See [references/api-lineage-search-activity.md](references/api-lineage-search-activity.md).
- `ListLineages` reality gates (do not assume the graph is complete):
  - `Response.Data` may be `null` when the resource is not indexed by the lineage service yet, OR when the queried direction happens to be empty even though the opposite direction is populated (server-side lineage indexing is direction-asymmetric). Do NOT retry the same `Direction` with the same resource, and do NOT invent an upstream/downstream chain. However, before concluding "no lineage", run the cross-check ladder in `2.14` (opposite `Direction` on the same resource + reverse `Direction=INPUT` on peers whose names suggest they consume/produce this resource + `audit_log` writer probe for INSERT/OVERWRITE events). Only when all these come back empty may you state "no lineage in the current environment" and stop.
  - `Items[]` can contain multiple entries with the same `CurrentResource.ResourceName` — each entry groups a subset of the total `Processes`; `TotalCount` is the sum of processes across items, not the number of distinct resources. If the user needs every sync/ETL job, iterate `Items[].Processes[]` (the `lineage.py` recipe already flattens this into `ProcessCount` + `Processes[]` per item).
  - `ProcessType` / `ProcessSubType` are heterogeneous. Verified values include `INTEGRATEDOFFLINE/""` (data-integration offline sync), `CODE_STUDIO/SQL`, `WORK_FLOW_TASK/SQL`. Never claim "downstream is entirely one type" without checking `ProcessStats`.
- Cross-API type/quirk hotspots: server-rejection quirks per API family live in the corresponding domain reference — string-typed `ListModelVersions.MaxResults`, object-array `CreateLabels.Labels[].Values`, empty-string `Update*Comment` rejection, and Volume/Model no-default-schema rule are all covered in [api-volume-model.md](references/api-volume-model.md) / [api-tag-asset.md](references/api-tag-asset.md) / [api-table-view-function.md](references/api-table-view-function.md). Universal read-before-write rule for comment/owner writes: first call the matching `Get*`/`ListMetaOwners` and cache the original in session context; include the original in the confirmation summary (empty-string reset is rejected so this cached original is the only rollback path).
- Permission gate reminders (surface these before the first call, do not wait for a 403):
  - `UpdateMetaOwner` requires Metalake Administrator on the target catalog. Absent that role the call returns a permission error; ask the user to confirm role or switch operator before submitting.
  - `system_catalog.wedata.audit_log` queries and any cold-table/usage-inventory SQL require Security Administrator (or an equivalent audit-read role). If the user is unsure, run a 1-row LIMIT probe first; on `PERMISSION_DENIED` report and stop.
  - Catalog permission = server's job. Never proactively speculate or announce a workspace's read/write permission on a catalog before an actual call, and never invert such state from the user's natural language (e.g. "我对那些 catalog 有写权限"). Just follow the normal read -> confirm -> write flow. On write, if the server returns `UnauthorizedOperation.WorkspaceForbidden` (InnerCode 1401301, message such as `当前工作空间只有读权限，不能修改数据目录` or `当前工作空间对数据目录无读写权限，无法修改资产标签`), stop the current write and reply with the server `KeyMessage` + `Suggestion` verbatim (no rewording, no `可能受限`, no `您已确认有写权限`). Then, based on the user's original intent, recommend viable alternatives from `ListCatalogs.Items[]` where `CurrentWorkspacePermissionLevel==2` (writable catalogs the user actually has; legend `0=无权限, 1=只读, 2=读写`) — for "create table like X" prefer writable catalogs matching X's data type/asset type; keep to ≤5 candidates plus the reason, and let the user pick in the next turn without a blocking modal. If the user later names a new target catalog, repeat the same read -> confirm -> write cycle; do not carry over the previous 1401301 as a blanket rule.

#### 2.0 API index

Load only the reference needed for the user's intent. This table is routing only; complete API lists, parameters, examples, and boundaries live in the references. Main-file rules and safety constraints remain authoritative.

| Domain | Intent keywords | Load file | Recipe (preferred) |
|---|---|---|---|
| **Catalog / Schema** | catalog, database, schema | [references/api-catalog-schema.md](references/api-catalog-schema.md) | — |
| **Table / View / Function** | table, view, function, column description, similarity / compare tables / 相似表 / 异名同义 | [references/api-table-view-function.md](references/api-table-view-function.md) | Structural similarity per section `2.19` (two `GetTable` calls; no dedicated script) |
| **Volume / Model** | volume, model, model version, MLflow, model alias | [references/api-volume-model.md](references/api-volume-model.md) | — |
| **Execute / MetaCommon** | job submit (`SubmitJob`), owner, AI description, business metadata (`ListComputeResourceOptions` here is only a helper input for `SubmitJob`; standalone "list compute resources" → `asset-discovery`) | [references/api-execute-meta-event.md](references/api-execute-meta-event.md) | — |
| **Tag / AssetTag** | tag, label, classify by business purpose, governance/custom/property/masking tag | [references/api-tag-asset.md](references/api-tag-asset.md) | `scripts/label_ops.py` (read-only exploration / type histogram; write path still gated by confirm) |
| **Lineage / Activity / Search** | lineage, upstream, downstream, favorite, view history, search, find table, asset recommendation | [references/api-lineage-search-activity.md](references/api-lineage-search-activity.md) | `scripts/lineage.py` (Direction=INPUT/OUTPUT + recursive expansion) · `scripts/asset_search.py` (SearchAsset+GetTable+require-fields). Pure exploration / layered pipeline map / mermaid diagram (no ETL `ProcessName`, no governance table needed) → `asset-discovery` (`explore-lineage --format pipeline\|mermaid`). |
| **Audit logs and usage inventory** | audit, operation log, login, API call, cold table, unused asset, popularity, usage inventory | [references/audit-log.md](references/audit-log.md) plus section `2.16` | `scripts/cold_tables.py` (cold-table inventory + optional downstream-exclusion) |

Loading guidance: most tasks need only one or two references; load multiple only for cross-domain tasks such as batch tagging plus lineage lookup. When a Recipe covers the intent, prefer it over hand-crafting `wedatacli` calls -- see [references/recipe_scripts.md](references/recipe_scripts.md) for the full contract firewall checklist. Section numbering below preserves historical anchors: gaps (§2.1–2.9, §2.15) are intentional after content consolidation and are referenced from other files; do not renumber. §2.10 is the shared Linked-Catalog (external-table) pre-gate consumed by §2.12 and §2.14.

#### 2.11 Label API contracts

These counter-intuitive rules apply even if [references/api-tag-asset.md](references/api-tag-asset.md) is not loaded.

- APIs: `CreateLabels`, `ListLabels`, `UpdateLabels`, `DeleteLabels`.
- `WorkspaceId`: auto-injected by `wedatacli` for gateway workspace RBAC. Examples omit it; explicit override is allowed for cross-workspace calls.
- Always pass `Shared=true`. Business tags and masking tags shown in the UI are the same resource family underneath. Without `Shared=true`, workspace filtering hides most visible tags and may create misplaced tags. Use `Shared=true` for governance, custom, property, and masking labels.
- `UpdateLabels.SecurityTypes`: update masking label security types only with `SecurityTypesUpdate: { SecurityTypes: [...] }`; top-level `SecurityTypes` is ignored.
- `UpdateLabels.PolicyBindingUpdate`: bind, replace, or unbind policy through `PolicyBindingUpdate: { PolicyId: "<id or empty>", WorkspaceId: "<target workspace>" }`.
- Three-state wrapper semantics: omit wrapper = keep old value; wrapper with empty array/string = explicitly clear or unbind; wrapper with non-empty value = overwrite or bind.
- `Type` is display-only for `UpdateLabels`; do not modify it there.
- System labels (`SourceType=1`) cannot modify `Name` or `Values`.
- When creating a `Type=4` masking label and the target policy is known, `CreateLabels` can create and bind in one call with `PolicyId` + `PolicyBindingWorkspaceId`; do not call a guessed `BindLabelMaskPolicy`.

#### 2.10 Linked-Catalog (external-table) pre-gate (shared, referenced by §2.12 and §2.14)

**Scope — ONLY two user-facing entrypoints trigger this gate**: (a) AI metadata completion (§2.12, `GetCommentCompletion` + `UpdateTableComment` / `UpdateTableColumnComment` / `UpdateTableColumnsComment`), and (b) table lineage (§2.14, `ListLineages` / `scripts/lineage.py`). All other paths — SearchAsset / favorites / view history / ListLabels / BatchVoteAssetTag / owner transfer / audit-log SQL / cold-table inventory / ListTables / GetTable / GetTables — do NOT short-circuit.

The gate is driven by the target table's owning catalog. Resolution source is **`wedatacli get catalogs` (lowercase list) → per-item `source` field** (verified 2026-08-19, four-form real-env test) — nothing else. Do NOT scan the user's text for datasource keywords; do NOT pre-parse "直连/direct" hints; do NOT route the verdict through any other skill.

1. **Resolve to `<catalog>` via one of four input forms** — the gate is catalog-driven, so the owning `<catalog>` MUST be identified before probing. Recipe layer (preferred) calls `common.resolve_and_pregate(user_input, mode=<M>)` which handles all four forms in one call. `mode` ∈ {hybrid|exact|semantic}; when omitted, the helper auto-picks per form (identifier-shape single token → hybrid, whitespace/CJK/punctuation → semantic).

   | # | Form | Example | Resolution | Mode | Cost |
   |---|---|---|---|---|---|
   | ① | 3-part FQN | `red_test_catalog.ai_gateway.aig_api_key` | Take segment 1 directly | n/a | zero probes |
   | ② | 2-part `schema.table` | `ai_gateway.aig_api_key` | `search table T --schema S --mode hybrid --verbose` → `fields.catalog` | hybrid | 1 call |
   | ③ | single identifier | `aig_api_key` | `search table T --mode hybrid --verbose` → `fields.catalog` | hybrid | 1 call |
   | ④ | semantic phrase | `API密钥表` | `search table "<phrase>" --mode semantic --verbose` → `fields.catalog` | semantic | 1 call |

   Ambiguity handling (returned by `resolve_and_pregate` as `verdict`):
   - `proceed` → single METALAKE candidate → call the entrypoint API.
   - `refuse` → all hits under CONNECTION catalog(s) → emit refusal one-liner (step 3), do NOT ask for disambiguation.
   - `ambiguous` → multiple METALAKE candidates (or mixed CONNECTION/METALAKE, only METALAKE surfaced) → list up to 3 full-FQN candidates and let the user pick; do NOT guess.
   - `not_found` → zero hits or catalog not in workspace → ask the user for the missing segment BEFORE probing; do NOT call the entrypoint API on a guessed FQN.

   Never enumerate catalogs/schemas one-by-one. Once `<catalog>` is known, proceed to step 2. If the entrypoint call was already issued on an unresolved / guessed FQN, the backend backstop below still applies.

2. **Catalog probe — `get catalogs` + `source`**:
   - Recipe layer (preferred): `common.is_linked_catalog(<catalog>)` returns `{linked, source, CatalogName}`. `linked=true` iff `source=="CONNECTION"`; if the catalog is not present in the workspace list, the helper raises (do NOT silently downgrade to `linked=false`).
   - Manual CLI (equivalent): `wedatacli get catalogs` and look up the target `name` — `source=="CONNECTION"` → Linked Catalog; `source=="METALAKE"` → internal.

   **Banned resolution paths (all fail in real env — do NOT probe)**:
   - `GetCatalog` Action (PascalCase) / `wedatacli get catalog --name <catalog>` → returns `CatalogNotFound` for Linked Catalogs.
   - `wedatacli get catalog <name>` (positional singular) → `unknown or unexpected argument`.
   - `search table --verbose` field `connection_id` → also populated for METALAKE tables (points at the ingestion connection, not the catalog kind); unreliable.

3. **Short-circuit verdict (only on `linked=true` / `verdict=="refuse"`)** — STOP and reply with the one-line refusal appropriate to the entrypoint. Do NOT call the underlying APIs.
   - §2.12 metadata completion: `⚠ 外部表暂不支持智能元数据补齐能力（Linked Catalog: <CatalogName>）。`
   - §2.14 table lineage: `⚠ 外部表暂不支持表血缘分析能力（Linked Catalog: <CatalogName>）。`

**Recipe self-protection**: `scripts/lineage.py` embeds a LIGHT gate in `main()` on the 3-part `--resource` — even with `--skip-pregate` it still runs one `get catalogs` lookup so a Linked Catalog can never bypass the refusal. `--skip-pregate` only skips the expensive four-form search resolver (assumed to have run upstream via `common.resolve_and_pregate`). On refusal, `lineage.py` exits 0 with the refusal one-liner on stdout and `[LINKED_CATALOG]` on stderr — shell wrappers must NOT treat this as a failure.

**Backend backstop (scope-qualified)**: even if the pre-gate was skipped or the FQN was guessed, the backend surfaces `UnsupportedOperationForLinkedCatalog` on write / lineage attempts against a Linked Catalog **that is registered in `get catalogs` metadata**. Treat this error code as the same terminal refusal — emit the same one-liner above and stop; do NOT retry, do NOT self-probe alternative APIs, do NOT synthesize a lineage chain. **Direct-connection catalogs that are NOT registered in `get catalogs`** (e.g. ad-hoc external tables surfaced only through `search table --verbose`) do NOT trigger this error code — the server silently returns empty lineage / drops writes. That silent-empty case is why the client-side pre-gate (steps 1–3 above) MUST NOT be skipped for arbitrary hand-crafted callers.

Authoritative implementation lives in [scripts/common.py](scripts/common.py) (`list_catalogs`, `is_linked_catalog`, `search_table_candidates`, `resolve_and_pregate`); this section, §2.12, §2.14, [references/api-execute-meta-event.md](references/api-execute-meta-event.md), and [references/api-table-view-function.md](references/api-table-view-function.md) all mirror the same rule and MUST stay in lockstep.

#### 2.12 `GetCommentCompletion` contracts

- **Linked-Catalog pre-gate**: run the §2.10 decision before any `GetCommentCompletion` / `UpdateTable*Comment` call. Recipe layer: `common.resolve_and_pregate(<user_input>, mode=<M>)` covers all four input forms (3-part / 2-part / single-name / semantic — `mode` auto-picks; explicit override allowed) and returns `{verdict, candidates, refusal}`; on `verdict=="refuse"`, emit `⚠ 外部表暂不支持智能元数据补齐能力（Linked Catalog: <CatalogName>）。` and stop. Do NOT parse the user's text for datasource keywords; do NOT route through any other skill. If the pre-gate was skipped, backend `UnsupportedOperationForLinkedCatalog` (only for registered Linked Catalogs — unregistered direct-connection catalogs may silently no-op) is the terminal refusal.

- Purpose: generate only, do not persist. The API returns suggestions from metadata and writes nothing. For editing, translating, or shortening existing descriptions, use an external LLM result and then persist through `UpdateTableComment`, `UpdateTableColumnComment`, or `UpdateTableColumnsComment` after write confirmation.
- `Operation` only supports `generate`.
- `TABLE_COLUMN`: `EntityName` is the table name only, not `table.column`; pass fields through non-empty `Columns` (`ColumnBrief` array with `Name`, `Type`, `Comment`), max 100 per call. The response returns `Data.ColumnComments` per field; do not loop per column or fill locally.
- `TABLE`: `Data.Comment` contains the table description and `Data.ColumnComments` is empty; use `TABLE_COLUMN` for field descriptions.
- Permission: the server still checks target Catalog permission even though no write occurs; read-only workspaces may return `UnauthorizedOperation.WorkspaceForbidden`.
- Batch-size alignment: `GetCommentCompletion.Columns` max is 100 per call; `UpdateTableColumnsComment.Columns` max is 500 per call. Generate in batches of 100, merge results per table, then persist in one `UpdateTableColumnsComment` call of <=500 fields. Do not split writes into five 100-field writes merely because generation was batched.
- Multi-table write minimization: for N tables, perform at most one table-description write plus one merged field-description write per table, total <=2N writes. Use this wording in confirmation summaries.

#### 2.13 Same-table write serialization and compact batch output

- Serialize writes to the same table. Multiple writes to one table, including description updates, tagging, and owner changes, must run sequentially. Cross-table writes may run in parallel. Concurrent same-table writes have been observed to trigger server conflicts, CLI retries, and token-expensive repeated failure details.
- User-facing batch output thresholds: <=20 rows show the full Markdown table in the response and do not upload an artifact; >20 rows show 10 sample rows plus total count, and upload the full content through `Skill("artifact-uploader")` to `databuddy/governance/*.md`, returning `studio_link`. This threshold must stay aligned with section `2.14`.
- Rationale: <=20 rows stays readable; above that use artifacts. Artifact hard limit is [artifact-uploader/scripts/upload.py](../../../common/skills/artifact-uploader/scripts/upload.py) `SIZE_HARD_LIMIT = 5MB`.
- Confirmation summaries must use business wording only, such as "update 1 table description and batch update 20 field descriptions". Do not expose API names or call-count expressions such as `UpdateTableComment` or `x N`.
- Do not add redundant self-justifying text such as "used exactly as provided", "based on standard X", or "correct me if wrong".
- AI inference confidence: until the user states the business domain/source, display generated field descriptions as `Warning: Low-confidence inference`; remove it only after an explicit domain source such as "this is a SAP HR import table" or "this is an e-commerce orders table". Never cite external systems such as "SAP standard" or `PA0000` without user-provided source evidence. Preview columns stay `Field name / Inferred description / Confidence`; no `Evidence` column.
- Preserve server-returned English descriptions as-is. Do not proactively translate them into another language unless the user asks; proactive translation can drift ambiguous field meanings and inflate tokens.
- Keep each response compact. Detailed rows follow the `2.14` thresholds; the body should keep a summary and artifact pointer rather than rewriting details repeatedly.
- If any of these rules is violated while building an intermediate artifact, stop expanding that batch and switch to artifact plus summary.

#### 2.14 User-facing output contract

**Four universal constraints**

1. For the scenarios below, the only deliverable is a short heading plus one Markdown table; do not replace it with a sentence or dump full schemas.
2. Table cells must not contain `<br/>`, newlines, `|`, or multiline code blocks. Truncate long text with `...` and move full content to an artifact.
3. Per table: <=20 rows -> show all rows; >20 rows -> show first 10 rows plus "remaining N rows in [artifact/studio_link]". This equals the `2.13` threshold.
4. Use the exact English column names below; do not mix languages, add columns, or remove columns in the same turn.

| Scenario | Trigger | Heading | Columns, strict order |
|---|---|---|---|
| AI field-description preview | `GetCommentCompletion` returns >=5 fields | **Field description preview** | Field name / Inferred description / Confidence |
| Table recommendation | `SearchAsset` / `SearchAssetQuickly` returns >=2 candidates | **Candidate tables** | Table FullName / Comment / Popularity |
| Lineage expansion | `ListLineages` returns non-empty `Items` | **Upstream** or **Downstream** | # / ResourceName / ResourceType / ProcessName |
| Tag exploration | `ListLabels` returns >=2 candidates | **Candidate labels** | Name / Type / Sample values / Id |

Audit and asset-inventory SQL results do not use fixed templates. Present them as one summary line with row count, time range, and `CsvPath`, plus a `head -N` CSV preview, while obeying the universal constraints above.

Formatting rules:

- `Inferred description` and `Comment` are <=30 characters; truncate with `...`. Preserve English returned by the server.
- `Confidence` is `High` or `Low`; low confidence must be prefixed with `Warning:`. Before user-provided domain attribution, all AI field descriptions are low confidence.
- `Table FullName` and `ResourceName` use full three-part names: `catalog.schema.name`.
- For lineage rows, read `ResourceName` and `ResourceType` from `Items[].CurrentResource`; `ProcessName` is the first non-empty `Items[].Processes[].ProcessName`, or empty when absent. When a lineage row groups multiple sync/ETL jobs, show the primary `ProcessName` in the table and add a follow-up line `Full processes: <ProcessName1>, <ProcessName2>, ...` beneath the table only if the user explicitly asked for every job. Do not stuff all names into the cell.
- If `ListLineages` returns an empty result (server-side `Data:null` or zero items) for the requested direction, replace the table with a single explicit line such as `No lineage returned by the server for <resource> (Direction=<X>).` and do NOT synthesize a plausible chain from table names. Before concluding the task, attempt these deterministic cross-checks (each is one `wedatacli` call, cheap and bounded).
  1. **Opposite direction** on the same resource — `lineage.py --resource <same> --direction <flipped>` (INPUT↔OUTPUT). Lineage indexing is direction-asymmetric; the opposite side is frequently populated.
  2. **Peer reverse lookup** — for "trace origin / impact analysis" questions, run `lineage.py --direction INPUT` on sibling tables whose names suggest they consume or produce this resource (e.g. tables sharing a domain prefix, or named `*_upstream_*` / `*_downstream_*`). Reverse lookup often surfaces the missing edge. Cap at 3 sibling candidates per task; do NOT enumerate every same-named table across catalogs.
  3. **Audit-log writer probe** — for "who produced this table" style questions, one `query-sql` on `system_catalog.wedata.audit_log` filtered by `get_json_object(request_params,'$.FullName')` = the target and `event_action` in (`INSERT_INTO`,`INSERT_OVERWRITE`) identifies writer workflows.
  Only when all three return empty may you conclude "no lineage in the current environment" and stop. Report which checks were performed so the user sees the investigation trail.
- Lineage idempotency: see **§2.14.1** below — one call per `(resource, direction)` per task; cross-checks apply only when the direction the user actually needs is empty.
- `Sample values` shows at most four values, separated by `, `.
- `Popularity` is passed through as server value 1-4.

Gate: if a scenario triggers, output its table before confirmation, writing, or follow-up questions. Missing the table means the turn is incomplete; do not jump from "query done" directly to a write.

**Linked-Catalog pre-gate for table lineage**: run the §2.10 decision before calling `ListLineages` / `scripts/lineage.py`. Recipe layer: `common.resolve_and_pregate(<user_input>, mode=<M>)` covers all four input forms and returns `{verdict, candidates, refusal}`; on `verdict=="refuse"`, emit `⚠ 外部表暂不支持表血缘分析能力（Linked Catalog: <CatalogName>）。` and stop. `lineage.py` also embeds a LIGHT gate in `main()` on the 3-part `--resource` (self-protection: one `get catalogs` lookup, unavoidable even with `--skip-pregate`); on refusal it exits 0 with the refusal on stdout. Do NOT parse the user's text for datasource keywords; do NOT route through any other skill. If the pre-gate was skipped, backend `UnsupportedOperationForLinkedCatalog` (only for registered Linked Catalogs — unregistered direct-connection catalogs silently return empty) is the terminal refusal; do NOT retry, do NOT synthesize.

**§2.14.1 Lineage idempotency gate (mandatory)** — within a single task, each `(resource, direction)` pair is called AT MOST ONCE. Cache the JSON result in your working memory and reuse it for follow-up reasoning; re-issuing `lineage.py --resource X --direction Y` yields the same bytes and is pure waste. If the opposite direction already returned non-empty for the current resource AND the user's question is fully answered by that direction (e.g. "downstream impact" answered by OUTPUT alone, "upstream origin" answered by INPUT alone), DO NOT run the three cross-checks above — they apply only when the direction the user actually needs is empty. This gate is the single biggest token drain observed in evaluation runs; treat it as a hard rule, not guidance.

#### 2.16 Audit-log hard constraints

Applies to user behavior audit logs in Wedata (operation stream, login, asset access, API call, permission change) and usage-based asset inventory (cold-table detection, popularity ranking, usage by user/team). Build SQL in the main agent and run it through `wedatacli query-sql`.

- Partition filter: `system_catalog.wedata.audit_log` is partitioned by `event_date`. Every business query `WHERE` must include `event_date` filtering with `=`, `>=`, `<=`, `BETWEEN`, or `IN`; otherwise full scans will be rejected.
- Sole path for usage inventory: for "no operations in past N days", "cold tables", "unused tables", or "least-used tables", use `audit_log` reverse lookup, typically metadata table list left/diffed against audit events. Never use these paths: looping `ListTables` plus `SELECT * FROM <tbl>.snapshots` / `<tbl>.files`; pulling all assets with `wedatacli inventory` then probing `last_modified`; repeated `SubmitJob` + `DownloadJobResult` across thousands of tables. These paths caused >300 turns, 20M+ tokens, and no valid result in observed runs.
- Default time range: if the user gives no range, use the last 7 days: `event_date BETWEEN date_sub(current_date(), 7) AND current_date()`. Do not ask. If a range is explicit, use it. General audit queries should be <=31 days per run; usage-inventory/cold-table queries may use up to 90 days, never more.
- Field-name anti-hallucination: do not hardcode columns. At session start, probe `system_catalog.wedata.audit_log` through `wedatacli query-sql`: first `DESCRIBE`; if it returns only headers or no real column rows, run `SELECT * ... WHERE event_date BETWEEN ... LIMIT 0` and use returned `Schema`. Replace [references/audit-log.md](references/audit-log.md) placeholders only with confirmed columns.
- If `AnalysisException: cannot resolve column` occurs, return to DESCRIBE and rebuild. Do not keep guessing column names.
- CLI compute-resource contract: every `wedatacli query-sql` for `system_catalog.wedata.audit_log` MUST pass both `--sql-type 1` (lakehouse SparkSQL) and `--compute-resource <analysis-resource-id>`. Resolve the analysis resource once per session via `wedatacli ListComputeResourceOptions - <<< '{"WorkspaceId":"'"$TENCENTCLOUD_WORKSPACE_ID"'","Page":{"PageNumber":1,"PageSize":100},"ResourceTypes":[3]}'` and pick the first item with `AvailableStatus==1` and `BasicInfo.ExecAvailableStatus==1`. Omitting either flag lets the server pick a default compute resource whose Spark session may not have `system_catalog` registered; the resulting `only support namespace with 1 level` / `TABLE_OR_VIEW_NOT_FOUND` / `Doesn't support multi level namespaces` errors are engine-side false negatives, not real schema issues, and MUST NOT be interpreted as "three-part naming unsupported". See [references/audit-log.md](references/audit-log.md) `Invocation` for the full command template.
- Failure handling: SQL missing `event_date` filter -> reject/regenerate; `PERMISSION_DENIED` or `TABLE_NOT_FOUND` -> report directly; repeated same API/error or same SQL skeleton/column error three times -> stop and report.

#### 2.17 Environment-metadata assumption

Do NOT probe the runtime environment with generic shell commands (`which`, `command -v`, `apt`, `ls`, `cat ~/.wedata/config.json`, etc.); it wastes turns and never influences API contracts. Assumptions holding on every supported runner: `wedatacli.sh` is on `PATH`; `jq` and `python3` are installed; `~/.wedata/config.json` is populated so `WorkspaceId` auto-injects. When workspace / region / regionId / consoleDomain values are actually needed for a request or a user answer, fetch them once via `wedatacli GetEnv <key>` (official short read; `<key>` in `workspaceId` / `region` / `regionId` / `consoleDomain`) and cache the result for the session.

#### 2.18 Recipe scripts (preferred path for hallucination-prone links)

[scripts/](scripts/) freezes SKILL chains that are high-frequency, high-hallucination, and token-expensive. All recipes are contract-verified against the runtime CLI. When a user intent matches the table below, **invoke the recipe first**; do NOT hand-roll wedatacli.

| Intent | Recipe | Underlying chain | Stable assertion |
|---|---|---|---|
| Upstream / downstream lineage (single-layer or recursive) | `python3 scripts/lineage.py --resource <3-part> --direction INPUT\|OUTPUT [--max-depth N] [--pretty]` | `ListLineages` (paged, slim projection) | Returns `Items[]` + full `Processes[]` + `ProcessStats`; recursive expansion uses breadth-first with visited-set protection |
| Cold-table inventory / last N days unused (optionally exclude tables with downstream consumers) | `python3 scripts/cold_tables.py --catalog C --schema S [--days 1..90] [--exclude-with-downstream] [--pretty]` | `get tables` + `audit_log` SQL + local LEFT ANTI JOIN + optional `ListLineages Direction=OUTPUT` | One `get tables` + one partition-filtered `audit_log` SQL + local diff; pre-flights `system_catalog.wedata.audit_log` availability and returns a structured error when it is unregistered / permission-denied |
| Table recommendation / find table / field probe ("which table can analyse X" / "which table contains both column A and B") | `python3 scripts/asset_search.py --keyword <kw> [--limit N] [--asset-types TABLE,VIEW] [--with-fields] [--require-fields col1,col2] [--pretty]` | `SearchAsset` (WorkspaceId auto-injected as string; MaxResults server-cap 100, recipe auto-clamps values >100 and prints a stderr note) + optional per-table `GetTable` 4-tuple + strict local field filter | Slim candidate items avoid full `SearchAsset` spill (baseline single page >16KB); `--require-fields` emits compact `MatchedRequired`/`MissingRequired` without dumping full `Columns` unless `--with-fields` is set |
| Label read-only exploration / "which business / BI / category labels exist in the workspace" / distribution | `python3 scripts/label_ops.py [--keyword K] [--types 1,3] [--group-by-type] [--pretty]` | `ListLabels {Shared:true, Page:{PageNumber,PageSize}}` paginated + type slim; write ops (CreateLabels / UpdateLabels / BatchVoteAssetTag) are NOT in this recipe -- still go through section 3 confirm gate | Uses nested `Page:{...}` pagination; slims values and excludes `Type=4` masking by default to keep boundary with data-classification clean |

Contract firewall (recipe layer already enforces; callers need not re-check): `Direction` accepts only uppercase `INPUT` / `OUTPUT`; `ListLineages.WorkspaceId` is auto-injected by the CLI (do NOT pass it explicitly); `ListLineages` items use `CurrentResource.ResourceName / ResourceType` and `Processes[].ProcessType / ProcessSubType` (NOT `Name / Type`); `wedatacli get tables` returns lowercase-key JSON `items[].name`; `query-sql` must use the `--sql` / `--sql-file` flag; `audit_log` MUST filter by the `event_date` partition, and resource identity is extracted via `get_json_object(request_params, '$.FullName')`. Linked-Catalog gate: before invoking `lineage.py` / `GetCommentCompletion` / `UpdateTable*Comment`, resolve via `common.resolve_and_pregate(<user_input>, mode=<M>)` (uses `wedatacli get catalogs` + per-item `source`); on `verdict=="refuse"` stop with the §2.10 refusal line. Banned probes: `GetCatalog` PascalCase Action, `get catalog --name`, `search table` field `connection_id`. `lineage.py` embeds a LIGHT gate in `main()` (one `get catalogs` lookup even with `--skip-pregate`); refusal exits 0 with stdout one-liner. Backend `UnsupportedOperationForLinkedCatalog` is a terminal backstop ONLY for Linked Catalogs registered in `get catalogs` — unregistered direct-connection catalogs silently return empty, so the client-side pre-gate MUST NOT be skipped. Full list: [references/recipe_scripts.md](references/recipe_scripts.md).

Fallback rule: hand-roll `wedatacli` when either (a) the recipe does not cover the parameter combination the user needs, or (b) the recipe returned empty / too-sparse results **and** the user question implies broader investigation is expected (impact analysis, root-cause tracing, cross-schema recommendation, zombie-table judgment, role-based recommendation). In case (b) state which recipe was tried first and why you are widening the search; stay within the section 2.x rules above. Contract-drift risk is absorbed by the scripts/ directory -- SKILL content stays stable as CLI fields evolve.

#### 2.19 Table similarity detection (default = structural)

When the user asks to compare two given tables ("检测 A 和 B 的相似度" / "compare A vs B"), scan a schema for near-duplicates ("扫一下 X 库下相似表" / "find similar tables"), or detect cross-prefix synonyms ("dwd 层里有没有异名同义表" / "same data with different naming"), **default to structural similarity and start real reads immediately**. Do NOT block on "which kind of similarity do you mean" — that question turns a well-scoped comparison task into an over-clarification loop.

Reality gates (contract-verified):
- `GetTable` returns full column list per table; two `GetTable` 4-tuple calls are enough to score structural similarity for the "given A vs B" case (columns from `Response.Data.Table.Columns`).
- Scanning a whole schema needs `wedatacli get tables --catalog C --schema S` first (returns lowercase `items[].name`), then per-table `GetTable`. Batch `GetTable` calls on many tables produce >16KB spill each and must therefore be issued sequentially with slim structured summaries, not raw dumps.
- Data-level similarity (row-count / value-distribution / sampling) is NOT covered by unity-catalog APIs — it belongs to data-quality skill or a manual SQL sample. State this explicitly rather than silently promising to compute it.

Structural similarity output contract (follows §2.14 output rules; use these headings verbatim):
- **Scan scope**: which catalog/schema/table pair was inspected and via which API (`GetTable` 4-tuple / `get tables` + per-table `GetTable`).
- **Field-level comparison**: one Markdown table with columns `Field A / Type A / Field B / Type B / Match`. `Match=exact` when name+type identical, `aligned` when name maps by shared suffix (e.g. `customer_id` ↔ `seller_id`) with same type, `A-only` / `B-only` for asymmetric fields. Truncate to top 20 rows with an artifact link if >20.
- **Similarity summary**: one line per dimension — `Structure: HIGH/MED/LOW (K/N fields aligned)`; explicitly print `Semantic/Data: not covered by this skill` for the two dimensions unity-catalog does not measure.
- **Governance suggestion**: one of `merge candidate` / `annotate as variant` / `keep separate`, with the one-sentence reason grounded in the field table above; never invent unseen fields.

Ask the user only if the user references a table that is NOT identifiable (no catalog/schema/table triplet, no `AssetGuid`, and `SearchAsset` returns zero candidates). Providing two identifiable table names alone is sufficient to start — do not ask "结构 vs 数据 vs 分布" before the first `GetTable`.

### 3. Ask for confirmation before every write

All writes (create, update, delete, register, submit, vote, batch changes) require a user-visible summary and explicit confirmation before execution. Read-only calls (`Get*`, `List*`, `Search*`, `Check*`, `Locate*`, and read-only audit SQL) may run without confirmation when the object and parameters are clear.

Confirmation summary must include:

- operation type: create / update / delete / tag / submit job;
- object: asset name, `FullName`, or ID;
- key parameters: new name, new description, tag values, etc.;
- impact scope: count and range for batch operations;
- irreversible-risk warning for deletes.

Example confirmation, using business wording only:

```text
About to perform this operation. Please confirm:
- Operation: create Catalog
- Name: sales_data
- Type: TABLE
- Workspace: 123456

Continue? Reply Y to execute, N to cancel, or tell me what to adjust.
```

Compliant AI-description batch confirmation. Details must appear through the section `2.14` field-description table; this is only the confirmation summary:

```text
About to update my_catalog.my_schema.sdi_hljt_hrshare_individual_df:
- Update 1 table description: "Employee personal information wide table (HR master data)"
- Batch update 20 field descriptions; 6 are marked as Warning: Low-confidence inference in the details

Full details: [databuddy/governance/xxx.md] (studio_link).
Please confirm execution, or tell me which field descriptions to adjust before persistence.
```

Wrong example: `Confirm UpdateTableComment x 2 + UpdateTableColumnsComment x 2?` This violates the business-wording rule.

Write-operation detector: API names starting with `Create`, `Update`, `Delete`, `Register`, `Submit`, `Vote`, or `Batch` are writes and require confirmation.

### 4. Execute and verify

After confirmation, call the API, inspect status/error fields, and verify success with a read API when applicable, such as `Get*` after create/update.

### 5. Summarize result

Summarize operations, success/failure, and concise next steps.

## Decision rules

- **Execute directly without confirmation**: read-only `Get*`, `List*`, `Search*`, `Check*`, `Locate*`, and read-only audit SQL when the user gave enough object/parameter information.
- **Require confirmation before writes**:
  - create: show object name, type, hierarchy, or three-part name;
  - update: show before/after when available;
  - delete: show object plus irreversible warning;
  - tag: `BatchVoteAssetTag`, `UpdateAssetTag`, `DeleteAssetTagVote` need asset and tag summary;
  - job submit: show job type, `JobSource`, code/content, and compute resource;
  - batch: show count and scope.
- **Start read-only exploration first; avoid over-clarifying**: if the user provides both a Catalog/Schema/range and an operation keyword such as tag, create label, mark, batch annotate, or apply tag, start read-only exploration even without exact table names or tag values:
  1. `ListSchemaNames` / `ListTables` or `SearchAsset` to get candidate assets and `AssetGuid`.
  2. `ListLabels {Shared:true}` to find matching existing labels.
  3. Return summary plus confirmation: assets, matched labels, and any proposed new `Name/Values`; only then write.
  4. Existing-resource overlap does NOT trigger a second clarification round: when `ListLabels` (or any read-only exploration) surfaces resources overlapping the user's proposed category, still emit the full proposal (Name / Description / Type / target scope) as one Markdown table plus one closing question "reuse existing or create new". Do NOT pause the proposal to ask "reuse vs create" first.

  Routing default: BI/report/business purpose/department/project/core asset/analyst extraction/warehouse-layering terms are business-tag semantics under `Type=1/2/3`; choose the exact type from existing `ListLabels` distribution or user choice, not keyword hard mapping. If sensitive/PII/GDPR/masking/data-classification terms appear, route to data-classification and use `Type=4` masking flow there.
- **Ask the user** only when intent is too vague to identify level/object, required identifiers are missing (except auto-injected `WorkspaceId`), or there are multiple materially different implementation choices.
- **Stop and report** when `--describe` says `unknown tool`, permissions are insufficient, the object does not exist and cannot be auto-created, the same failure pattern repeats three times, or the user replies N.

## Output format

- **Execution summary**: what governance operation ran and which assets were involved.
- **Execution actions**: API calls, key parameters, and returned status when useful.
- **Verification**: read-back API or query result used to verify success.
- **Risk and next steps**: irreversible risks and concise follow-ups.

## Safety constraints

- API names starting with `Create`, `Update`, `Delete`, `Register`, `Submit`, `Vote`, or `Batch` are writes and require confirmation. Exception: `GetCommentCompletion` only generates suggestions and is read-only; actual persistence still uses `UpdateTable*` APIs and needs confirmation.
- Current CLI does not expose lineage registration or metadata event reporting. For such requests, report capability unavailable; do not guess API names or event fields.
- Do not update more than 500 field descriptions in one `UpdateTableColumnsComment` call.
- Do not run unverified batch writes in production; do not bypass permission controls.
- All writes must leave operation logs for audit. If the user rejects confirmation (N), stop immediately; do not ask again or bypass confirmation.
- Audit-log SQL against `system_catalog.wedata.audit_log` must contain an `event_date` filter. If missing, refuse execution and regenerate.

## Examples

### Should trigger

| # | Intent | First action | Key rule |
|---|---|---|---|
| 1 | Create/query/rename/delete Catalog, Schema, Table, View, Volume, or Model | Load the matching reference and build request from examples | Confirm before writes |
| 2 | "Which table should I use to analyze X" or "which table has field X" | `SearchAsset` / `SearchAssetQuickly` recall -> `GetTable` field check -> recommend table, fields, and rationale | Read-only metadata task; do not route to data-engineering SQL |
| 3 | "Batch tag tables in schema X for BI reports" | `ListTables` + `ListLabels{Shared:true}` exploration -> summary + confirmation -> `CreateLabels` if needed + `BatchVoteAssetTag` | Do not repeatedly ask for exact tag values before exploration |
| 4 | Apply governance/custom/property/business-purpose/core-asset tags | `ListLabels{Shared:true}` -> `BatchVoteAssetTag` with explicit `Tags[].Type` | Follow section `2.11`; `Type` avoids `LABEL_TYPE_UNKNOWN` |
| 5 | Query upstream/downstream lineage | `ListLineages` with `Direction=INPUT/OUTPUT` | `Direction` only accepts uppercase `INPUT/OUTPUT` |
| 6 | AI-generate table/field descriptions | `GetCommentCompletion Operation=generate` -> confirmation -> `UpdateTable*Comment` | Follow section `2.12`: 100 per generation batch, <=2N writes |
| 7 | User/asset operation stream, login, or API-call audit | Build SQL + `wedatacli query-sql` | Mandatory `event_date`, default last 7 days |
| 8 | Cold table / 90-day unused assets / popularity ranking | Use `audit_log` reverse lookup only | No `.snapshots`, `.files`, or per-table `SubmitJob` loop |
| 9 | Compare two given tables / find similar tables in a schema / detect cross-prefix synonyms ("检测 A 和 B 的相似度" / "扫一下 X 库下相似表") | Two `GetTable` 4-tuple calls (or `get tables` + per-table `GetTable`) -> field-level comparison table -> similarity summary | Section `2.19`; default to structural similarity, do NOT block on "which kind of similarity" clarification |

### Should not trigger

| Intent | Use instead | Boundary |
|---|---|---|
| "Write SQL to query sales data" | SQL engine / data-engineering | Distinguish from "find/recommend a table", which is this skill |
| Grant permissions or manage roles | Permission module | - |
| Data integration task | Data integration module | - |
| Metrics, dimensions, semantic models, measure definitions | semantic-manage YAML CRUD | - |
| Sensitive data, PII, GDPR, masking policy, data classification | data-classification | Sensitive keywords take priority over business-tag terms |
| Deployment or pipeline | deploy-pipeline | - |

## Artifact handling

Upload structured governance artifacts such as lineage inventories, asset inventories, AI description batches, batch-tagging summaries, property-change summaries, and audit exports through `Skill("artifact-uploader")` to `databuddy/governance/`.

Constraints: ask the user first; use `domain="governance"`; Markdown only; one file <=5MB; for multiple files use `op="upload_batch"`; echo `studio_link`; on failure show `errors[]`. Never fabricate asset GUIDs, `FullName`, owners, or audit-log field values.
