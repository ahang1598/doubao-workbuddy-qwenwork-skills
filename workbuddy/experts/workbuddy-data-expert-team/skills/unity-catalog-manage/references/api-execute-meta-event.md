# Execute / MetaCommon API Reference

> Load on demand. [SKILL.md](../SKILL.md) is the single authority for call rules, safety constraints, and anti-hallucination baselines. Examples omit the outer auto-injected `WorkspaceId`; explicitly override it for cross-workspace calls. Exception: `SubmitJob.Job.WorkspaceId` is a nested business field, not marked `[auto injected]` by runtime schema, and must be supplied.

## 1. ExecuteService

Query compute resources and submit asynchronous jobs.

| Operation | API | Example |
|---|---|---|
| List compute resources | `ListComputeResourceOptions` | `wedatacli ListComputeResourceOptions '{"Page":{"PageNumber":1,"PageSize":20}}'` |
| Submit job | `SubmitJob` | `wedatacli SubmitJob '{"Job":{"JobType":"Sql","JobSource":"IDE","WorkspaceId":"<current workspace>","Name":"query job","ExecuteParam":{"TemplateInfo":{"ExecuteTemplate":{"TemplateType":"Sql","Sql":{"Content":"SELECT * FROM my_table LIMIT 10","Source":"2","Catalog":"my_catalog","Schema":"my_schema"}}}}}}'` |
| Query job status | `QueryJobStatus` | `wedatacli QueryJobStatus '{"JobId":"job_001"}'` |

`SubmitJob` takes a nested `Job` (`ExecuteJobInfo`) object. `JobSource` is required; current enum values are `MANUAL_SCHEDULE`, `CYCLE_SCHEDULE`, `IDE`, and `RERUN`. `Job.WorkspaceId` is a nested business field and must be explicit, while the outer WorkspaceId is CLI-injected. Template fields are deeply nested; run the runtime schema for `SubmitJob` before real submission to verify structure and enums. `ListComputeResourceOptions.Page` (`PageNumber` + `PageSize`) is required; `ResourceTypes` and `ResourceIds` are optional.

---

## 2. MetaCommonService

Shared metadata capabilities: owner lookup/transfer, business metadata, and AI description generation.

| Operation | API | Example |
|---|---|---|
| Batch list metadata owners | `ListMetaOwners` | `wedatacli ListMetaOwners '{"MetaType":"TABLE","FullNames":["my_catalog.my_schema.my_table","my_catalog.my_schema.other_table"]}'` |
| Transfer metadata owner | `UpdateMetaOwner` | `wedatacli UpdateMetaOwner '{"MetaType":"TABLE","FullName":"my_catalog.my_schema.my_table","OwnerType":"User","Owner":"user_002_uin"}'` |
| Get metadata business info | `GetMetaBiz` | `wedatacli GetMetaBiz '{"MetaType":"TABLE","MetaIdentifier":"tccatalog_identifier_value"}'` |
| Generate AI description, table | `GetCommentCompletion` | `wedatacli GetCommentCompletion '{"EntityType":"TABLE","CatalogName":"my_catalog","SchemaName":"my_schema","EntityName":"my_table","Operation":"generate"}'` |
| Generate AI descriptions, columns | `GetCommentCompletion` | `wedatacli GetCommentCompletion '{"EntityType":"TABLE_COLUMN","CatalogName":"my_catalog","SchemaName":"my_schema","EntityName":"my_table","Operation":"generate","Columns":[{"Name":"id","Type":"integer"},{"Name":"name","Type":"string"}]}'` |

`ListMetaOwners`, `UpdateMetaOwner`, and `GetMetaBiz` `MetaType` enum values are `CATALOG`, `SCHEMA`, `TABLE`, `VIEW`, `MODEL`, and `VOLUME`; verify with runtime schema. `ListMetaOwners` returns batched owner data by `MetaType` + `FullNames`; `Data.Items[]` contains `FullName`, `OwnerType`, `Owner`, and `OwnerName`. `UpdateMetaOwner` locates one asset by `MetaType` + `FullName`; current `OwnerType` only supports `User`. `GetMetaBiz.MetaIdentifier` comes from the `tccatalog.identifier` value in detail API `Properties`; for tables, read it from `GetTable` response path `Response.Data.Table.Properties`.

`GetCommentCompletion` call notes; decision rules for generation versus persistence live in [SKILL.md 2.12](../SKILL.md#212-getcommentcompletion-contracts):

- **Linked-Catalog pre-gate** (mandatory, see SKILL.md §2.10 / §2.12): AI metadata completion does not support external tables. The verdict is driven by the target table's owning catalog resolved through `wedatacli get catalogs` + per-item `source` field (verified 2026-08-19), NOT by scanning the user's text for datasource keywords and NOT by routing through any other skill.
  1. **Resolve `<catalog>` from any of four input forms** — recipes call `common.resolve_and_pregate(<user_input>)` which handles: ① 3-part FQN (zero probes), ② 2-part `schema.table` (`search table T --schema S --verbose` → `fields.catalog`), ③ single table name (`search table T --verbose`), ④ semantic phrase. Returns `{verdict, candidates, refusal}` where `verdict ∈ {proceed, refuse, ambiguous, not_found}`. Ambiguous → surface up to 3 full-FQN candidates for user pick; not_found → ask for the missing segment; never call `GetCommentCompletion` / `UpdateTable*Comment` on a guessed FQN.
  2. **Catalog probe**: recipes call `common.is_linked_catalog(<catalog>)` — reads `wedatacli get catalogs` and asserts `source=="CONNECTION"` (Linked) vs `source=="METALAKE"` (internal). **Banned probes** (all fail in real env): `GetCatalog` PascalCase Action, `wedatacli get catalog --name`, `search table` field `connection_id`.
  3. **Short-circuit hard verdict** (`verdict=="refuse"` or `linked=true`): STOP and reply `⚠ 外部表暂不支持智能元数据补齐能力（Linked Catalog: <CatalogName>）。` Do NOT call `GetCommentCompletion`. Do NOT call any `UpdateTable*Comment` persistence API.

  **Backend backstop (scope-qualified)**: even if the pre-gate was skipped or the FQN was guessed, `GetCommentCompletion` / `UpdateTable*Comment` against a Linked Catalog **that is registered in `get catalogs` metadata** surface `UnsupportedOperationForLinkedCatalog` — treat this as the same terminal refusal, do NOT retry, do NOT self-probe alternative APIs. **Direct-connection catalogs that are NOT registered in `get catalogs`** may not surface this error at all (the server returns success on generate + silently drops the persist call, or write is silently ignored), which is exactly why the client-side pre-gate MUST NOT be skipped. Scope: this gate applies ONLY to §2.12 AI metadata completion and §2.14 table lineage; other unity-catalog paths are unaffected.
- Set `EntityName` by `EntityType`: `TABLE` -> table name; `TABLE_COLUMN` -> table name and column names in `Columns[].Name`; `MODEL_VERSION` -> `model.version`.
- For `TABLE_COLUMN`, `Columns` is required, non-empty, max 100 per call, and response `Data.ColumnComments` returns per-field descriptions.
- `Operation` only supports `generate`.
- The server enforces target Catalog write-permission on `GetCommentCompletion` despite the `Get` prefix; when the workspace lacks write-permission the call returns `UnauthorizedOperation.WorkspaceForbidden` (InnerCode 1401301). Follow the SKILL.md `Permission gate reminders` contract: relay the server `KeyMessage` + `Suggestion` verbatim to the user, do not soften it, and offer writable catalog candidates from `ListCatalogs` based on the user's intent.

---

## 3. Unexposed capability boundary

The current CLI does not expose metadata event reporting. If the user asks to report non-TCCatalog asset events, state that current `wedatacli` capability is unavailable; do not guess API names or event fields.