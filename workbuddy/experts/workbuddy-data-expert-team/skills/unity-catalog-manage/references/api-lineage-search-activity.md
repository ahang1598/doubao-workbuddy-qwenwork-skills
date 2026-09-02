# Lineage / AssetActivity / AssetSearch API Reference

> Load on demand. [SKILL.md](../SKILL.md) is the single authority for call rules, safety constraints, and anti-hallucination baselines. Examples omit auto-injected `WorkspaceId`; explicitly override it for cross-workspace calls. Exception: `ListLineages` — `WorkspaceId` is auto-injected by the CLI; do NOT pass it explicitly in the payload.

## 1. LineageService

Query lineage between data assets.

| Operation | API | Example |
|---|---|---|
| Query upstream lineage | `ListLineages` | `wedatacli ListLineages '{"ResourceName":"my_catalog.my_schema.my_table","ResourceType":"TABLE","Direction":"INPUT","Page":{"PageNumber":1,"PageSize":20}}'` |
| Query downstream lineage | `ListLineages` | `wedatacli ListLineages '{"ResourceName":"my_catalog.my_schema.my_table","ResourceType":"TABLE","Direction":"OUTPUT","Page":{"PageNumber":1,"PageSize":20}}'` |

`Direction` accepts only uppercase `INPUT` (upstream) and `OUTPUT` (downstream); other values are rejected as parameter errors (the server may respond as either HTTP 503 with empty body or `InvalidParameterValue.DirectionInvalid` — treat both as parameter errors, do NOT retry as service outage). The contract has no explicit `WorkspaceId` field in the payload — the CLI auto-injects it; do not pass it explicitly. `TotalCount=0` may indicate either (a) the resource is not indexed by the lineage service yet, or (b) that direction is genuinely empty. Lineage indexing is direction-asymmetric — always try the opposite `Direction` before concluding "no lineage" (SKILL.md §2.14). Lineage items are nested: read the displayed resource from `Items[].CurrentResource.{ResourceName,ResourceType}` and process names from `Items[].Processes[].ProcessName`; `NextResource` may be absent. The CLI does not expose lineage-registration APIs.

**Linked-Catalog pre-gate** (mandatory, see SKILL.md §2.10 / §2.14): table lineage does not support external tables. The verdict is driven by the target table's owning catalog resolved through `wedatacli get catalogs` + per-item `source` field (verified 2026-08-19), NOT by scanning the user's text for datasource keywords and NOT by routing through any other skill.
1. **Resolve `<catalog>` from any of four input forms** — recipes call `common.resolve_and_pregate(<user_input>)` which handles: ① 3-part FQN (zero probes), ② 2-part `schema.table` (`search table T --schema S --verbose` → `fields.catalog`), ③ single table name (`search table T --verbose`), ④ semantic phrase. Returns `{verdict, candidates, refusal}` where `verdict ∈ {proceed, refuse, ambiguous, not_found}`. Ambiguous → surface up to 3 full-FQN candidates and let the user pick; not_found → ask for the missing segment; never enumerate catalogs/schemas one-by-one; never call `ListLineages` on a guessed FQN.
2. **Catalog probe**: recipes call `common.is_linked_catalog(<catalog>)` — reads `wedatacli get catalogs` and asserts `source=="CONNECTION"` (Linked) vs `source=="METALAKE"` (internal). Manual CLI: `wedatacli get catalogs`, look up target `name`, check `source`. **Banned probes** (all fail in real env): `GetCatalog` PascalCase Action, `wedatacli get catalog --name`, `search table` field `connection_id`.
3. **Short-circuit verdict** (`verdict=="refuse"` or `linked=true`): STOP and reply `⚠ 外部表暂不支持表血缘分析能力（Linked Catalog: <CatalogName>）。` Do NOT call `ListLineages`.

**Recipe self-protection**: `scripts/lineage.py` embeds the gate in `main()` on the 3-part `--resource`; pass `--skip-pregate` only when `resolve_and_pregate` already ran upstream.

**Backend backstop (scope-qualified)**: even if the pre-gate was skipped or the FQN was guessed, `ListLineages` against a Linked Catalog **that is registered in `get catalogs` metadata** returns `UnsupportedOperationForLinkedCatalog` — treat this as the same terminal refusal, do NOT retry, do NOT self-probe alternative APIs, do NOT synthesize a chain from table names. **Direct-connection catalogs that are NOT registered in `get catalogs`** (e.g. ad-hoc external tables surfaced only through `search table --verbose`) do not trigger this error code — the server silently returns empty lineage, which looks indistinguishable from an unindexed internal table. This is exactly why the client-side pre-gate (steps 1–3 above) MUST NOT be skipped: it is the ONLY reliable Linked-Catalog defense for the unregistered subset. Scope: this gate applies ONLY to table lineage here and to AI metadata completion in §2.12; SearchAsset / favorites / activity APIs below are unaffected.

---

## 2. AssetActivityService

Manage user favorites and asset view history.

| Operation | API | Example |
|---|---|---|
| Favorite asset | `CreateAssetFavorite` | `wedatacli CreateAssetFavorite '{"AssetType":"TABLE","AssetGuid":"tccatalog.v1.uid<digits>@<app_id>_<region>_TABLE"}'` |
| Remove favorite | `DeleteAssetFavorite` | `wedatacli DeleteAssetFavorite '{"AssetType":"TABLE","AssetGuid":"tccatalog.v1.uid<digits>@<app_id>_<region>_TABLE"}'` |
| List favorites, recommended | `ListAssetFavoritesV2` | `wedatacli ListAssetFavoritesV2 '{"MaxResults":20}'` |
| List favorites | `ListAssetFavorites` | `wedatacli ListAssetFavorites '{"PageNumber":1,"PageSize":20}'` |
| Record asset view | `CreateAssetView` | `wedatacli CreateAssetView '{"AssetType":"TABLE","AssetGuid":"tccatalog.v1.uid<digits>@<app_id>_<region>_TABLE"}'` |
| List views, recommended | `ListAssetViewsV2` | `wedatacli ListAssetViewsV2 '{"MaxResults":20}'` |
| List views | `ListAssetViews` | `wedatacli ListAssetViews '{"PageNumber":1,"PageSize":20}'` |

V2 APIs use `MaxResults` + `PageToken` pagination and are preferred. V1 APIs `ListAssetFavorites` and `ListAssetViews` use `PageNumber` + `PageSize`; do NOT pass `MaxResults` to V1 (the field is not part of the contract and is silently ignored, resulting in default page size and apparent "no pagination"). Confirm the V1 contract with the runtime schema for `ListAssetViews`, which exposes only `PageNumber`, `PageSize`, `Keyword`, `AssetTypes`, `WorkspaceId`. `CreateAssetFavorite`, `DeleteAssetFavorite`, and `CreateAssetView` require the full `AssetGuid`; `FullName` alone or `AssetId` alone is rejected with `InvalidParameterValue.InvalidParameter / AssetGuid is empty` (`InnerCode=1401110`), even though runtime schema lists `FullName` and `AssetId` as fields. Only `AssetGuid` passes server-side validation. Get `AssetGuid` from `SearchAsset` / `SearchAssetQuickly` responses (`Items[].AssetGuid`) or from `GetTable` (`Response.Data.Table.AssetGuid`); its format is `tccatalog.v1.uid<digits>@<app_id>_<region>_<AssetType>`, where `<app_id>` is the tenant AppId embedded by the server, not the current `WorkspaceId`. Always copy the whole `AssetGuid` from a runtime response; do not assemble it manually from `WorkspaceId`, region, or asset type, or the server will reject the call. The current CLI does not expose a standalone "my favorites" API; use `ListAssetFavoritesV2` or `ListAssetFavorites`.

---

## 3. AssetSearchService

Full-text search, quick search, catalog-tree search, and location.

| Operation | API | Example |
|---|---|---|
| Full-text asset search | `SearchAsset` | `wedatacli SearchAsset '{"Keyword":"sales orders","AssetTypes":["TABLE","VIEW"],"CatalogNames":["my_catalog"],"MaxResults":20}'` |
| Quick asset search | `SearchAssetQuickly` | `wedatacli SearchAssetQuickly '{"Keyword":"user_info","AssetTypes":["TABLE"],"MaxResults":10}'` |
| Catalog-tree search | `SearchCatalogTree` | `wedatacli SearchCatalogTree '{"Keyword":"my_table","AssetTypes":["TABLE"],"MaxResults":20}'` |
| Locate catalog-tree node | `LocateCatalogTree` | `wedatacli LocateCatalogTree '{"FullName":"my_catalog.my_schema.my_table","AssetType":"TABLE"}'` |
| List feature tables | `ListFeatureTables` | `wedatacli ListFeatureTables '{"Keyword":"feature","MaxResults":20}'` |

Full-text search supports highlights, tag filters (`TagIds`/`TagValueIds`), owner filter (`Owner`), and multi-dimensional sorting (`Order`). `SearchCatalogTree` supports `PermissionFilters` per `AssetType`. Search APIs use `MaxResults` + `PageToken` pagination. `SearchAsset` and `SearchAssetQuickly` both cap `MaxResults` at 100; values above 100 return `InvalidParameterValue.InvalidParameter / maxResults must be less than or equal to 100` (the runtime schema for `SearchAsset` mentions "default 30, optional 30-50", which is descriptive guidance rather than a hard limit; the hard limit is 100). Prefer 20 for interactive tasks. `SearchAsset` often exceeds the wrapper 16 KB stdout threshold; when stdout is `{truncated:true,file:"..."}`, open that file and parse `Response.Data.Items`.

**`SearchAsset` vs `SearchAssetQuickly` vs `SearchCatalogTree`**: choose by shape of the result the user needs. `SearchAsset` is full-text with rich filters/highlights/sort, returns a flat `Items[]` ranked by score, best for "find any asset containing keyword X" and asset recommendation flows. `SearchAssetQuickly` is a lighter typeahead-style variant with the same flat item shape; use it for short-keyword quick lookups (single table name, single column name) where speed and small payload matter. `SearchCatalogTree` returns a hierarchical `Catalog -> Schema -> Asset` tree scoped to the user's permission and is intended for the left-side catalog explorer UI; use it when the user needs to preserve the tree location of matches (e.g. "which schemas contain tables named X?"). Response shape is nested `Catalogs[].Schemas[].Assets[]` with `FullName`/`Comment`/`IsFavorite`/`CurrentWorkspacePermissionLevel`. If tree responses look empty, first verify the keyword also hits `SearchAsset`; empty tree with non-empty `SearchAsset` typically means the assets exist in catalogs the user has no read permission on, not an API bug.

### Asset recommendation / find-table workflow

When the user asks "which table should I use for analysis X" or "which table has field X", treat it as a read-only metadata task. Actively search and recommend; do not reject as out of scope and do not route to data-engineering just to write SQL.

1. Recall candidates: call `SearchAsset` with semantic terms or `SearchAssetQuickly` with table/keyword terms, then collect candidate `FullName` values in `catalog.schema.table` form.
2. Verify fields: for the most relevant candidates, call `GetTable` with separate `CatalogName`, `SchemaName`, and `TableName` parsed from `FullName`; there is no single `FullName` field for `GetTable`. The table object is `Response.Data.Table`. Check target fields, for example `order_purchase_timestamp` and `order_approved_at` for order lifecycle latency. If same-name tables exist across catalogs, trust runtime `SearchAsset` `FullName` values; never hardcode schemas from examples.
3. Recommend: output table name, matched fields, and rationale. If several tables are semantically close, sort by relevance and compare them.

Illustrative flow for "which table should I use to analyze time from order placement to approval": run `wedatacli SearchAsset '{"Keyword":"orders_dataset","AssetTypes":["TABLE"],"MaxResults":20}'` (or search broader business terms and compare candidates); pick a runtime candidate `FullName` such as `<catalog>.<schema>.orders_dataset`; call `wedatacli GetTable '{"CatalogName":"<catalog>","SchemaName":"<schema>","TableName":"orders_dataset"}'`; read `Response.Data.Table.Columns`; verify fields such as `order_purchase_timestamp` and `order_approved_at`; return the recommended table, matched fields, and rationale. Always trust runtime-returned schemas; never hardcode the names above.