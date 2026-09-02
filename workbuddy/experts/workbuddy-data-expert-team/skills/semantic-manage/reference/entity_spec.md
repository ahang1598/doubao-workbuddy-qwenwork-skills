# Entity spec

This is the authority for ontology Entity operations. Entity is an ontology-layer business concept container, such as user/order/product. It combines sources, attributes that reference existing dimensions/metrics, and relations that reference semantic-model JOIN definitions. Entity is not a semantic YAML object type and must use independent Entity APIs.

## API surface

| API | Kind | Purpose | Sensitivity |
|---|---|---|---|
| `CreateEntityFromYaml` | write | create full entity with sources/attributes/relations | L2 create |
| `UpdateEntityFromYaml` | write | full-cover update by soft-delete + rebuild | L3 write |
| `DeleteEntityFromYaml` | write | delete by `entity.name` | L3 write |
| `EnableEntityFromYaml` | write | offline → online | L3 write |
| `DisableEntityFromYaml` | write | online → offline | L3 write |
| `ExportEntityAsYaml` | read | export current YAML for edit/backup | L1 read |
| `GetEntity` | read | detail aggregation | L1 read |
| `ListEntities` | read | filtered paged list + counts | L1 read |
| `ListEntityGraph` | read | graph view with relations only inside result set | L1 read |
| `BatchAttachEntityBusinessDomain` | write | batch attach entities to one domain | L3 write |
| `BatchDetachEntityBusinessDomain` | write | detach from one concrete domain; no DetachAll | L3 write |

All five `*FromYaml` write APIs accept `{"YamlContent":"..."}`. Do not use `CreateSemanticFromYaml` / `EnableSemanticFromYaml` etc. for entities.

Parameter casing traps (verified by `wedatacli --describe`, 2026-08-14 ap-chongqing):

- `KeyWord` (K and W both uppercase) is used by: `ListOntologyDomains`, `ListDimensions`, `ListOntologyDomainEntities`, `ListOntologyDomainSemanticModels`, `ListOntologyDomainMetrics`, `ListOntologyDomainDimensions`, `ListDomainsModels`.
- `Keyword` (lowercase `w`) is used by: `ListEntities`, `ListEntityGraph`, `ListLogicalViews`.
- Wrong casing is HARD-REJECTED by the CLI with `未知入参 [X]（<Action> 没有这些字段，已拒绝调用以避免被静默丢弃后返回语义错误的结果）`; the call never reaches the server. When in doubt, always re-check with `wedatacli --describe <Action>` before writing the JSON payload.
- `ListEntities`: `BusinessDomainId` is int64, `BusinessDomainIds` is []int64 (multi-select, preferred when both are set).
- `ListEntityGraph`: `BusinessDomainId` is string single-value; there is no `BusinessDomainIds`. Also supports `Keyword` (matches name/aliases/description).
- Ontology 4-tab APIs: `DomainId` is string.
- `ListDomainsModels`: `DomainIds` is []int64.

## Operation map

| Intent | Operation | API | Confirmation | YAML shape |
|---|---|---|---|---|
| create entity | CREATE | `CreateEntityFromYaml` | yes | full entity YAML |
| update/edit entity | UPDATE | `UpdateEntityFromYaml` | yes | full-cover YAML |
| disable entity | DISABLE | `DisableEntityFromYaml` | yes | compact `entity.name` |
| enable/restore entity | ENABLE | `EnableEntityFromYaml` | yes | compact `entity.name` |
| physically/permanently delete entity | DELETE | `DeleteEntityFromYaml` | explicit delete confirmation | compact `entity.name` |
| export entity YAML | EXPORT | `ExportEntityAsYaml` | no | none |
| list/get/graph | LIST/GET/GRAPH | `ListEntities` / `GetEntity` / `ListEntityGraph` | no | none |
| attach to domain | ATTACH | `BatchAttachEntityBusinessDomain` | yes | JSON |
| detach from domain | DETACH | `BatchDetachEntityBusinessDomain` | yes | JSON |

Ambiguous “remove/no longer need” defaults to DISABLE; only explicit physical/permanent delete uses DELETE.

## Full YAML skeleton

CREATE / UPDATE:

```yaml
version: 1.0
entity:
  name: <string>
  aliases: "alias1;alias2"
  description: <string>
  business_domain: <string or [string]>
  entity_identifier:
    name: <string>
    sources:
      - table: "catalog.database.table"
        filter: ''
        mapping_column: <string>
  relations:
    - name: <string>
      target_entity: <string>
      description: <string>
      join_ref:
        semantic_model: <string>
        name: <string>
  attributes:
    - name: <string>
      description: <string>
      dimension_ref: <string>
      # metric_ref: <string>  # not open in phase 1
```

Hard constraints:

- CREATE/UPDATE require top-level `version: 1.0`.
- `entity` is the only business top-level key; `sources`, `attributes`, `relations`, and `entity_identifier` are nested under it.
- `aliases` is a semicolon-separated string, not an array.
- `business_domain` is optional by service behavior, but recommended. It is a domain Name, not ID. Service accepts string or YAML list; export normalizes to list. Missing/empty creates an unassociated entity (`BusinessDomains=null`), discoverable with `ListEntities '{"BusinessDomainId":0}'`. Ask before omitting.
- `entity_identifier.name` must appear as one `attributes[].name`.
- `entity_identifier.sources[].table` is one dotted string `catalog.database.table`; do not split keys.
- `mapping_column` is per source and may differ across sources; do not default all to the entity identifier name.
- Referenced `business_domain`, `dimension_ref`, `target_entity`, `join_ref.semantic_model`, and `join_ref.name` must exist before submit.
- `metric_ref` is not open in phase 1; if present or requested, stop and explain.
- `dimension_ref` and `metric_ref` are mutually exclusive.
- UPDATE is full-cover rebuild; omitted sources/attributes/relations are deleted, so preview must show add/keep/delete.

Compact ENABLE / DISABLE / DELETE YAML:

```yaml
entity:
  name: <entity_name>
```

Compact Entity YAML must not include `version`; empirically service schema rejects `version` for Enable/Disable/Delete with `YAMLformatvalidatefailed`.

## Status matrix

Entity `Status`: `1` ONLINE, `2` OFFLINE. This is not `MetadataStatus` although values match.

| Operation | Allowed | Rejected |
|---|---|---|
| CREATE | missing entity | same `Name` or alias exists |
| UPDATE | entity exists, any `Status` 1 or 2 | missing |
| ENABLE | `Status=2` | missing / already `1` |
| DISABLE | `Status=1` | missing / already `2` |
| DELETE | exists, `Status=1` or `2`, no inbound relation blocking | missing / referenced by other entity relation |

Entity differences from semantic YAML: DELETE does not require prior DISABLE; UPDATE accepts offline entities. You may recommend safe practices, but do not refuse valid API states based on semantic YAML rules.

Before DELETE, inspect visible inbound references through `ListEntityGraph` broadly; warn on `relations[].TargetEntityName == <name>`. Do not auto-edit referencing entities.

## CREATE flow

1. Self-check required top-level fields, name length/charset, optional `business_domain`, identifier/attribute consistency, table segment count.
2. Uniqueness precheck: `ListEntities '{"Keyword":"<name>","PageNumber":1,"PageSize":20}'`, exact-filter `Data[].Name`; split aliases by `;` and check each against `Data[].Aliases`.
3. Reference precheck:
   - non-empty `business_domain` → `ListOntologyDomains '{"KeyWord":"<name>","PageNumber":1,"PageSize":20}'`, exact `Data[].Data.Name`.
   - `dimension_ref` → `ListDimensions '{"KeyWord":"<name>","PageNumber":1,"PageSize":5}'`, exact name.
   - `target_entity` → `ListEntities` exact name.
   - `join_ref.semantic_model` → `GetSemanticModel`.
   - `join_ref.name` → verify inside `NodeTree` / JOIN definitions, supporting dotted paths.
   - `metric_ref` → stop.
4. Source validation: split each table into catalog/database/table, call `GetTable`, and validate `mapping_column` exists. Non-empty filters are syntax-risk-noted but not executed.
5. Confirmation page: YAML, dependency list, alias split result, identifier/source mappings.
6. Submit `CreateEntityFromYaml`.
7. Read back `GetEntity '{"Name":"<name>"}'` and report `Response.Data.Entity.{Id,Status,AttributeCount,RelationCount}`.

## UPDATE flow

1. `GetEntity` existence. Offline `Status=2` is still updatable.
2. Prefer `ExportEntityAsYaml` as baseline, generate full diff, and show add/keep/delete for `entity_identifier.sources`, `attributes`, and `relations`.
3. If `business_domain` changes, explicitly show old → new; it is equivalent to domain reassignment.
4. Run CREATE-like self-checks and reference checks.
5. Submit `UpdateEntityFromYaml`, then `GetEntity` read-back.

## Attach / detach BusinessDomain

These JSON APIs are independent from YAML and do not change Entity `Status`.

### Attach

```bash
wedatacli BatchAttachEntityBusinessDomain '{"EntityIds":[123,456],"BusinessDomainId":789}'
```

- `EntityIds` is int64 IDs, not names; `BusinessDomainId` is int64 domain ID.
- Per-item failures do not abort the batch. Response path: `Response.Data.{SuccessIdList:[string],FailedItemList?:[...]}`. `SuccessIdList` elements are strings; `FailedItemList` may be absent.
- Precheck non-empty IDs and `BusinessDomainId>0`. Confirmation page shows entity names and target domain name.

### Detach

```bash
wedatacli BatchDetachEntityBusinessDomain '{"EntityIds":[123],"BusinessDomainId":789}'
```

Empirical correction: `BusinessDomainId` is required and must be > 0. Missing or `0` is rejected; service does not support DetachAll. To detach multiple domains, `GetEntity` current `BusinessDomains[].Id`, then call detach once per domain and read back after each.

## Read-only queries

| Intent | Command |
|---|---|
| list entities | `ListEntities '{"PageNumber":1,"PageSize":20}'` |
| filter by domain | `ListEntities '{"BusinessDomainId":123,"PageNumber":1,"PageSize":20}'` |
| keyword/status | `ListEntities '{"Keyword":"...","Status":1,"PageNumber":1,"PageSize":20}'` |
| detail | `GetEntity '{"Name":"<name>"}'` |
| graph | `ListEntityGraph '{}'` with optional filters |

Response notes:

- `ListEntities` → `Response.Data.{TotalCount,DraftTotalCount,PublishTotalCount,DisableTotalCount,PageNumber,PageSize,Data:[EntityVO]}`.
- `GetEntity` → `Response.Data.{Entity,Sources,Attributes,ExtendAttributeGroups?,Relations?}`. `Relations` and `ExtendAttributeGroups` may be absent, not empty arrays. Large responses may trigger CLI stdout truncation.
- Entity write APIs → `Response.Data.{Success,Message,EntityId,EntityName,OperationType}`; no status in write response.
- Missing `GetEntity` empirically returns `InvalidParameter.CommonInvalidArgument` with `entity not found`, `InnerCode=1403002`; handle alongside ResourceNotFound.
- `ListEntityGraph` only returns relations whose both ends are in the result set; absence is not proof of no relation.

## Export

`ExportEntityAsYaml '{"Name":"<entity_name>"}'` returns `Response.Data.{YamlContent,EntityId}`. Use it as the preferred baseline for UPDATE, backup before DELETE, and “show definition” requests. Do not rewrite unknown exported schema fields; if export seems odd, treat it as backend schema evolution.

`ExportEntityAsYaml` covers ONLY the entity's own YAML (sources / attributes / relations / entity_identifier / business_domain). It does NOT inline the referenced dimensions or semantic models. When the user asks for a **bundle export** ("把某业务域的实体、实体引用的语义信息均生成到一个 YAML"), the extra parts must be filled from authoritative reads, not from entity attribute names or table context:

- Each `attributes[].dimension_ref` → `ListDimensions '{"KeyWord":"<exact-name>","PageNumber":1,"PageSize":5}'`, exact-match `Data[].Name`, then copy `Type` / `TypeParam` / `Source` / `ColName` verbatim into the rendered dimension block. Never infer `type` from the attribute name (e.g. `warning_name` / `vin` / `project_code` are NOT `TIME`; `xxx_time` / `xxx_date` still must be confirmed via API before being rendered as `TIME`). See `reference/dimension_spec.md` §Read-side rendering.
- Each `relations[].join_ref.semantic_model` → `GetSemanticModel '{"Name":"<name>"}'`, render `MainNode` / `NodeTree` / `TableList` verbatim; do not reconstruct JOINs from `join_ref.name` alone.
- For domain-scoped bundle dumps, `ListOntologyDomainEntities` + `ListOntologyDomainDimensions` + `ListOntologyDomainSemanticModels` under the same `DomainId` may batch the entity/dimension/model enumeration, but each item still requires its own authoritative detail read before serialization.
- Any item whose authoritative detail cannot be retrieved MUST be rendered with an explicit placeholder (e.g. `type: <unknown, pending ListDimensions>`) and the artifact must list an "unresolved refs" summary; never silently guess.

## Prohibitions

- Do not operate entity with semantic YAML APIs.
- Do not mix `models` / `metrics` / `dimensions` into Entity YAML.
- Do not put entity children at top level.
- Do not omit `version` in full CREATE/UPDATE; do not include it in compact Enable/Disable/Delete.
- Do not make `aliases` an array.
- Do not put integer `BusinessDomainId` into YAML `business_domain`.
- Do not split `entity_identifier.sources[].table` into separate keys.
- Do not omit the identifier attribute.
- Do not create `metric_ref` or pair it with `dimension_ref`.
- Do not reference missing objects.
- Do not flatten `join_ref`.
- Do not treat UPDATE as a patch.
- Do not silently change domain assignment.
- Do not delete without inbound relation risk check.
- Do not use `BusinessDomainId=0` or missing field for detach.
- Do not pass entity names where IDs are required.
- Do not infer status from write responses.
