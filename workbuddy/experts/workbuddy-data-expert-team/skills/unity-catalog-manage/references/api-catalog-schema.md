# Catalog & Schema API Reference

> Load on demand. [SKILL.md](../SKILL.md) is the single authority for call rules, safety constraints, and anti-hallucination baselines. Examples omit auto-injected `WorkspaceId`; explicitly override it only for cross-workspace calls.

## 1. CatalogService

Create, read, update, and delete Catalogs.

| Operation | API | Example |
|---|---|---|
| Create Catalog | `CreateCatalog` | `wedatacli CreateCatalog '{"Name":"my_catalog","Type":"TABLE","Comment":"business data catalog"}'` |
| List Catalogs | `ListCatalogs` | `wedatacli ListCatalogs '{"MaxResults":20}'` |
| List Catalog names | `ListCatalogNames` | `wedatacli ListCatalogNames '{"MaxResults":50}'` |
| Get Catalog | `GetCatalog` | `wedatacli GetCatalog '{"CatalogName":"my_catalog"}'` |
| Rename Catalog | `UpdateCatalogName` | `wedatacli UpdateCatalogName '{"CatalogName":"old_name","NewName":"new_name"}'` |
| Update Catalog comment | `UpdateCatalogComment` | `wedatacli UpdateCatalogComment '{"CatalogName":"my_catalog","NewComment":"updated description"}'` |
| Delete Catalog | `DeleteCatalog` | `wedatacli DeleteCatalog '{"CatalogName":"my_catalog"}'` |
| List connected Catalog names | `ListConnectionCatalogNames` | `wedatacli ListConnectionCatalogNames '{"ConnectionId":"conn_001","MaxResults":20}'` |
| List unauthorized workspaces | `ListCatalogWorkspacesUnAuth` | `wedatacli ListCatalogWorkspacesUnAuth '{"CatalogName":"my_catalog","CatalogId":"cat_id_001","MaxResults":20}'` |

`CreateCatalog.Type` must follow the runtime schema for `CreateCatalog`; verified values are `TABLE`, `MODEL`, and `VOLUME`. Use `ListConnectionCatalogNames` for connection-source Catalog names. Do not pass external data-source types as `CreateCatalog.Type`. Pagination uses `MaxResults` + `PageToken`.

> ⚠ `GetCatalog` limitation on Linked Catalogs: `GetCatalog` (and `wedatacli get catalog --name`) returns `CatalogNotFound` for direct-connection (Linked) catalogs and cannot be used as a Linked-Catalog detection signal. For the §2.10 pre-gate use `wedatacli get catalogs` (plural) and read the per-item `source` field instead (`CONNECTION` = Linked, `METALAKE` = internal). `GetCatalog` remains valid for internally managed catalogs where full Catalog metadata is needed.

---

## 2. SchemaService

Create, read, update, and delete Schemas.

| Operation | API | Example |
|---|---|---|
| Create Schema | `CreateSchema` | `wedatacli CreateSchema '{"CatalogName":"my_catalog","Name":"my_schema","Comment":"business schema"}'` |
| List Schemas | `ListSchemas` | `wedatacli ListSchemas '{"CatalogName":"my_catalog","MaxResults":20}'` |
| List Schema names | `ListSchemaNames` | `wedatacli ListSchemaNames '{"CatalogName":"my_catalog","MaxResults":50}'` |
| Get Schema | `GetSchema` | `wedatacli GetSchema '{"CatalogName":"my_catalog","SchemaName":"my_schema"}'` |
| Update Schema comment | `UpdateSchemaComment` | `wedatacli UpdateSchemaComment '{"CatalogName":"my_catalog","SchemaName":"my_schema","NewComment":"updated description"}'` |
| Delete Schema | `DeleteSchema` | `wedatacli DeleteSchema '{"CatalogName":"my_catalog","SchemaName":"my_schema"}'` |
| List connection-source Schemas | `ListConnectionSchemaNames` | `wedatacli ListConnectionSchemaNames '{"ConnectionId":"conn_001","CatalogName":"my_catalog","MaxResults":20}'` |

Pagination uses `MaxResults` + `PageToken`. The create-time Schema name field is `Name`. Use `ListConnectionSchemaNames` for connection-source Schema lookup; use its `DatabaseName` field when database filtering is needed. The current CLI does not expose a standalone Database-name list API.
