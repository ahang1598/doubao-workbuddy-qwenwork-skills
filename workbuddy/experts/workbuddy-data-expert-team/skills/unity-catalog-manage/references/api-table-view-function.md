# Table / View / Function API Reference

> Load on demand. [SKILL.md](../SKILL.md) is the single authority for call rules, safety constraints, and anti-hallucination baselines. Examples omit auto-injected `WorkspaceId`; explicitly override it only for cross-workspace calls.

## 1. TableService

Query, update, delete, and update field descriptions for Tables.

| Operation | API | Example |
|---|---|---|
| List Tables | `ListTables` | `wedatacli ListTables '{"CatalogName":"my_catalog","SchemaName":"my_schema","MaxResults":20}'` |
| List Table names | `ListTableNames` | `wedatacli ListTableNames '{"CatalogName":"my_catalog","SchemaName":"my_schema","MaxResults":50}'` |
| Get Table | `GetTable` | `wedatacli GetTable '{"CatalogName":"my_catalog","SchemaName":"my_schema","TableName":"my_table"}'` |
| Batch get Tables | `GetTables` | `wedatacli GetTables '{"FullNames":["catalog.schema.table1","catalog.schema.table2"]}'` |
| Rename Table | `UpdateTableName` | `wedatacli UpdateTableName '{"CatalogName":"my_catalog","SchemaName":"my_schema","TableName":"old_name","NewName":"new_name"}'` |
| Update Table comment | `UpdateTableComment` | `wedatacli UpdateTableComment '{"CatalogName":"my_catalog","SchemaName":"my_schema","TableName":"my_table","NewComment":"updated description"}'` |
| Update one column comment | `UpdateTableColumnComment` | `wedatacli UpdateTableColumnComment '{"CatalogName":"my_catalog","SchemaName":"my_schema","TableName":"my_table","FieldName":"col1","NewComment":"column description"}'` |
| Batch update column comments | `UpdateTableColumnsComment` | `wedatacli UpdateTableColumnsComment '{"CatalogName":"my_catalog","SchemaName":"my_schema","TableName":"my_table","Columns":[{"Name":"col1","Type":"string","Comment":"description 1"},{"Name":"col2","Type":"int","Comment":"description 2"}]}'` |
| Delete Table | `DeleteTable` | `wedatacli DeleteTable '{"CatalogName":"my_catalog","SchemaName":"my_schema","TableName":"my_table"}'` |
| Check Table exists | `CheckTable` | `wedatacli CheckTable '{"CatalogName":"my_catalog","SchemaName":"my_schema","TableName":"my_table"}'` |

`ListTables.MaxResults` has a server-enforced max of 50 per call; exceeding it returns `InvalidParameterValue.InvalidParameter` / `InnerCode=1401110` with message `MaxResults supports a maximum of 50`. This hard check is currently verified only for `ListTables`; for consistency, also keep `ListTableNames`, `ListViews`, `ListViewNames`, and `ListFunctions` <=50. `GetTables` supports at most 20 `FullName` values. `GetTable` returns the table object under `Response.Data.Table`; read `Columns`, `Properties`, `AssetGuid`, and comments from that nested object. `UpdateTableColumnsComment.Columns` uses `ColumnBrief` (`Name` + `Type` + `Comment`) and supports at most 500 per call. Single-column updates use `FieldName` + `NewComment`.

**Empty-string not allowed on comment writes**: `UpdateTableComment.NewComment` cannot be an empty string. Passing `NewComment:""` returns `FailedOperation.TcCatalogError / NewComment is empty` (`InnerCode=1401001`). The same expectation applies to `UpdateTableColumnComment.NewComment`, `UpdateTableColumnsComment.Columns[].Comment` (per-row), `UpdateViewComment.NewComment`, and `UpdateFunctionComment.NewComment`. If the user wants to clear a comment back to blank, tell them the platform disallows empty; offer a placeholder such as `"-"` or route to manual UI action. Before every comment write, first call `GetTable`/`GetView`/`GetFunction` and cache the original `Comment` in session context; include the original in the confirmation summary so a manual rollback via the same API with the cached original is possible.

**Linked-Catalog pre-gate on comment writes** (mandatory, see SKILL.md §2.10 / §2.12): the write APIs `UpdateTableComment` / `UpdateTableColumnComment` / `UpdateTableColumnsComment` are the persistence half of the AI-metadata-completion flow, so they honor the same pre-gate. The verdict is driven by the target table's owning catalog resolved through `wedatacli get catalogs` + per-item `source` field (verified 2026-08-19), NOT by scanning the user's text for datasource keywords and NOT by routing through any other skill.
1. **Resolve `<catalog>` from any of four input forms** — recipes call `common.resolve_and_pregate(<user_input>)` which handles: ① 3-part FQN (zero probes), ② 2-part `schema.table` (`search table T --schema S --verbose` → `fields.catalog`), ③ single table name (`search table T --verbose`), ④ semantic phrase. Returns `{verdict, candidates, refusal}` where `verdict ∈ {proceed, refuse, ambiguous, not_found}`. Ambiguous → surface up to 3 full-FQN candidates for user pick; not_found → ask for the missing segment; never call any `UpdateTable*Comment` API on a guessed FQN.
2. **Catalog probe**: recipes call `common.is_linked_catalog(<catalog>)` — reads `wedatacli get catalogs` and asserts `source=="CONNECTION"` (Linked) vs `source=="METALAKE"` (internal). **Banned probes** (all fail in real env): `GetCatalog` PascalCase Action, `wedatacli get catalog --name`, `search table` field `connection_id`.
3. **Short-circuit hard verdict** (`verdict=="refuse"` or `linked=true`): STOP before calling any of the three write APIs and reply `⚠ 外部表暂不支持智能元数据补齐能力（Linked Catalog: <CatalogName>）。` This applies whether the description came from `GetCommentCompletion`, an external LLM, or the user's own text — Linked-Catalog tables must not receive AI-generated or persisted descriptions through this skill.

**Backend backstop (scope-qualified)**: even if the pre-gate was skipped or the FQN was guessed, the write APIs surface `UnsupportedOperationForLinkedCatalog` when the target catalog is a Linked Catalog **registered in `get catalogs` metadata**. Treat this as the same terminal refusal — do NOT retry, do NOT self-probe alternative APIs. **Direct-connection catalogs that are NOT registered in `get catalogs`** may not raise this error (writes are silently dropped or return no-op success), which is why the client-side pre-gate above MUST NOT be skipped.

Pagination: request one page first and inspect `Response.Data.NextPageToken`. Empty string means stop. Only pass `PageToken` when the first response returns a non-empty token such as `eyJvZmZzZXQiOjF9`. Do not predict pagination before seeing the first page.

Large output: `ListTables` responses can be large; a page with ~10 tables plus full field structures is typically tens of KB. The CLI spills above its default 16 KB threshold. Then stdout is an instruction JSON like `{truncated:true, file:"<spill-json-path>", size_bytes, preview_head_1k, next_actions:[...]}`, not the data itself. Do not pipe stdout with `|` expecting table data. Correct approach: parse `.file` from stdout, then use one `python3` script to open that file and do read + analysis in one pass, avoiding multi-stage scripts such as "extract names then compute similarity".

Never disable spill proactively. Do not set `WEDATA_MAX_STDOUT_BYTES=0` in any form (`export`, inline env var, or wrapper script). That would stream full 43 KB / 10K tokens into context and can trigger token-repetition degradation within three turns. The switch is only for human one-off terminal debugging; agents must use the spilled `.file` path. Ignore suggestions in `next_actions` that mention this variable.

---

## 2. ViewService

Query, update, and delete Views. Views are created through the SQL engine, not by a `CreateView` API.

| Operation | API | Example |
|---|---|---|
| List Views | `ListViews` | `wedatacli ListViews '{"CatalogName":"my_catalog","SchemaName":"my_schema","MaxResults":20}'` |
| List View names | `ListViewNames` | `wedatacli ListViewNames '{"CatalogName":"my_catalog","SchemaName":"my_schema","MaxResults":50}'` |
| Get View | `GetView` | `wedatacli GetView '{"CatalogName":"my_catalog","SchemaName":"my_schema","ViewName":"my_view"}'` |
| Rename View | `UpdateViewName` | `wedatacli UpdateViewName '{"CatalogName":"my_catalog","SchemaName":"my_schema","ViewName":"old_name","NewName":"new_name"}'` |
| Update View comment | `UpdateViewComment` | `wedatacli UpdateViewComment '{"CatalogName":"my_catalog","SchemaName":"my_schema","ViewName":"my_view","NewComment":"updated description"}'` |
| Delete View | `DeleteView` | `wedatacli DeleteView '{"CatalogName":"my_catalog","SchemaName":"my_schema","ViewName":"my_view"}'` |

---

## 3. FunctionService

Query UDFs and update function comments. Functions are managed by the SQL engine or CLI; no create/delete API is exposed here.

| Operation | API | Example |
|---|---|---|
| List functions | `ListFunctions` | `wedatacli ListFunctions '{"CatalogName":"my_catalog","SchemaName":"my_schema","MaxResults":20}'` |
| Get function | `GetFunction` | `wedatacli GetFunction '{"CatalogName":"my_catalog","SchemaName":"my_schema","FunctionName":"my_func"}'` |
| Update function comment | `UpdateFunctionComment` | `wedatacli UpdateFunctionComment '{"CatalogName":"my_catalog","SchemaName":"my_schema","FunctionName":"my_func","NewComment":"updated description"}'` |