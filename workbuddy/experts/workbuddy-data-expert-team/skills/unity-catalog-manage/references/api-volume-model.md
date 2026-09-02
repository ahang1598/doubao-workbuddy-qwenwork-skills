# Volume / Model API Reference

> Load on demand. [SKILL.md](../SKILL.md) is the single authority for call rules, safety constraints, and anti-hallucination baselines. Examples omit auto-injected `WorkspaceId`; explicitly override it only for cross-workspace calls.

## 1. VolumeService

Manage the full Volume lifecycle for `MANAGED` and `EXTERNAL` types.

| Operation | API | Example |
|---|---|---|
| Create Volume | `CreateVolume` | `wedatacli CreateVolume '{"CatalogName":"my_catalog","SchemaName":"my_schema","VolumeName":"my_volume","Type":"MANAGED","StorageLocation":"/path/to/storage"}'` |
| List Volumes | `ListVolumes` | `wedatacli ListVolumes '{"CatalogName":"my_catalog","SchemaName":"my_schema","MaxResults":20}'` |
| List Volume names | `ListVolumeNames` | `wedatacli ListVolumeNames '{"CatalogName":"my_catalog","SchemaName":"my_schema","MaxResults":50}'` |
| Get Volume | `GetVolume` | `wedatacli GetVolume '{"CatalogName":"my_catalog","SchemaName":"my_schema","VolumeName":"my_volume"}'` |
| Rename Volume | `UpdateVolumeName` | `wedatacli UpdateVolumeName '{"CatalogName":"my_catalog","SchemaName":"my_schema","VolumeName":"old_name","NewName":"new_name"}'` |
| Update Volume comment | `UpdateVolumeComment` | `wedatacli UpdateVolumeComment '{"CatalogName":"my_catalog","SchemaName":"my_schema","VolumeName":"my_volume","NewComment":"updated description"}'` |
| Delete Volume | `DeleteVolume` | `wedatacli DeleteVolume '{"CatalogName":"my_catalog","SchemaName":"my_schema","VolumeName":"my_volume"}'` |

`CreateVolume` uses `StorageLocation` for the storage path and supports `Properties` (`KVPair` list) as creation-time extension parameters. Runtime list/get calls require a Catalog whose `Type` is `VOLUME`; VOLUME catalogs typically coexist with TABLE catalogs, so use `ListCatalogs` to pick a `Type=VOLUME` name before calling `ListVolumes` / `GetVolume`. The current CLI does not expose APIs for updating Volume properties, listing connection-source files, listing all Volume names, or batch-getting Volumes.

**Schema-probe prerequisite (Volume)**: do not hardcode `SchemaName:"default"`. VOLUME catalogs are commonly created without a `default` schema (typical shape is a single dedicated `*_volume_schema`); calling `ListVolumes`/`GetVolume` with `SchemaName:"default"` against such a catalog returns `ResourceNotFound.VolumeNotFound` (`InnerCode=1401108`). Standard flow: `ListCatalogs` -> pick `Type=VOLUME` -> `ListSchemaNames` for that catalog -> pick a real schema -> then `ListVolumes`/`GetVolume`/`UpdateVolumeComment`/`DeleteVolume`. The same schema-probe rule applies to `ListModels`/`GetModel` under `Type=MODEL` catalogs. `UpdateVolumeComment.NewComment` also cannot be an empty string; see the comment-clearing rule in [SKILL.md 2.0](../SKILL.md#20-api-index) cross-API quirks.

---

## 2. ModelService

Manage Models and Model Versions, including MLflow-style flows.

| Operation | API | Example |
|---|---|---|
| Create Model | `CreateModel` | `wedatacli CreateModel '{"CatalogName":"my_catalog","SchemaName":"my_schema","ModelName":"my_model","Comment":"ML model"}'` |
| Register Model | `RegisterModel` | `wedatacli RegisterModel '{"Name":"my_catalog.my_schema.my_model","ModelId":"logged_model_id","Type":"MACHINE_LEARNING","Description":"ML model","Tags":{"Key":"env","Value":"prod"}}'` |
| List Models | `ListModels` | `wedatacli ListModels '{"CatalogName":"my_catalog","SchemaName":"my_schema","MaxResults":20}'` |
| List Model names | `ListModelNames` | `wedatacli ListModelNames '{"CatalogName":"my_catalog","SchemaName":"my_schema","MaxResults":50}'` |
| Search Models | `SearchModels` | `wedatacli SearchModels '{"CatalogName":"my_catalog","Filter":"name LIKE %keyword%","MaxResults":20}'` |
| Get Model | `GetModel` | `wedatacli GetModel '{"CatalogName":"my_catalog","SchemaName":"my_schema","ModelName":"my_model"}'` |
| Rename Model | `UpdateModelName` | `wedatacli UpdateModelName '{"CatalogName":"my_catalog","SchemaName":"my_schema","ModelName":"old_name","NewName":"new_name"}'` |
| Update Model comment | `UpdateModelComment` | `wedatacli UpdateModelComment '{"CatalogName":"my_catalog","SchemaName":"my_schema","ModelName":"my_model","NewComment":"updated description"}'` |
| Delete Model | `DeleteModel` | `wedatacli DeleteModel '{"CatalogName":"my_catalog","SchemaName":"my_schema","ModelName":"my_model"}'` |
| Create Model Version | `CreateModelVersion` | `wedatacli CreateModelVersion '{"CatalogName":"my_catalog","SchemaName":"my_schema","ModelName":"my_model","Uri":"/path/to/artifacts","Comment":"v1 version"}'` |
| List Model Versions | `ListModelVersions` | `wedatacli ListModelVersions '{"CatalogName":"my_catalog","SchemaName":"my_schema","ModelName":"my_model","MaxResults":"20"}'` (MaxResults is STRING here, unique in this file) |
| Get Model Version | `GetModelVersion` | `wedatacli GetModelVersion '{"CatalogName":"my_catalog","SchemaName":"my_schema","ModelName":"my_model","ModelVersion":1}'` |
| Update Model Version comment | `UpdateModelVersionComment` | `wedatacli UpdateModelVersionComment '{"CatalogName":"my_catalog","SchemaName":"my_schema","ModelName":"my_model","ModelVersion":1,"NewComment":"version description"}'` |
| Update Model Version aliases | `UpdateModelVersionAliases` | `wedatacli UpdateModelVersionAliases '{"CatalogName":"my_catalog","SchemaName":"my_schema","ModelName":"my_model","ModelVersion":1,"AddedAliases":["production"]}'` |
| Delete Model Version | `DeleteModelVersion` | `wedatacli DeleteModelVersion '{"CatalogName":"my_catalog","SchemaName":"my_schema","ModelName":"my_model","ModelVersion":1}'` |
| List Model Version audit log | `ListModelVersionAuditLog` | `wedatacli ListModelVersionAuditLog '{"CatalogName":"my_catalog","SchemaName":"my_schema","ModelName":"my_model","PageNumber":1,"PageSize":20}'` |

Version field is consistently `ModelVersion` (`int64`). Alias management uses `AddedAliases` and `RemovedAliases`. `ListModelVersionAuditLog` uses traditional `PageNumber` + `PageSize` pagination. Runtime list/get calls require a Catalog whose `Type` is `MODEL`; not every workspace has one, so probe available types with `wedatacli ListCatalogs` first and only call `ListModels`/`GetModel` when a `MODEL` catalog exists. The current CLI does not expose model-version-number list, batch get, model-version search, or model-version property update APIs.

**`ListModelVersions.MaxResults` type quirk**: this field is declared `string` in the Go request struct (unlike `ListModels.MaxResults` which is `int64`). Passing a JSON number fails immediately with `json: cannot unmarshal number into Go struct field ListModelVersionsRequest.MaxResults of type string`; always quote it as `"MaxResults":"20"`. This is the only known API in this reference that inverts the numeric convention; do not string-quote `MaxResults` for `ListModels`/`ListModelNames`/`ListVolumes`/`ListVolumeNames`. Same expectation applies to `UpdateModelComment.NewComment` / `UpdateModelVersionComment.NewComment`: empty string is rejected, see [SKILL.md 2.0](../SKILL.md#20-api-index) cross-API quirks.