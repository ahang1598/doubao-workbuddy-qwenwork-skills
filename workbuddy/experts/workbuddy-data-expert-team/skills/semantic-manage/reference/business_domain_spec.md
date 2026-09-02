# OntologyDomain spec

This is the authority for Ontology BusinessDomain APIs in `semantic-manage`. OntologyDomain is independent from semantic YAML: it groups Entity / semantic model / metric / dimension assets into four detail-page tabs. It has no YAML form.

## Concepts

- OntologyDomain is an ontology-layer business grouping, such as trading, marketing, or risk-control. One asset can belong to multiple domains.
- Namespace: `Name` is unique in Workspace + tenant, but independent from entity/model/metric/dimension/logical_view names.
- Labels: domain-bound governance tags, each `{LabelId, LabelValueId}`. CREATE requires at least one label; empirically missing `Labels` returns `MissingParameter: Labels`. UPDATE changes labels only with `UpdateLabels=true` and uses overwrite semantics.
- Owners: `BusinessOwnerId` and `DevelopOwnerId`, both optional numeric-string uins.

## Operation map

| Intent | Operation | API | Sensitivity | Confirmation |
|---|---|---|---|---|
| list domains | LIST | `ListOntologyDomains` | read | no |
| domain detail | GET | `GetOntologyDomain` | read | no |
| list entities/models/metrics/dimensions under a domain | LIST | `ListOntologyDomainEntities/SemanticModels/Metrics/Dimensions` | read | no |
| batch list domain models / orphan models | LIST | `ListDomainsModels` | read | no |
| create domain | CREATE | `CreateOntologyDomain` | L2 create | yes |
| update name/description/owners/labels | UPDATE | `UpdateOntologyDomain` | L3 write | yes |
| delete domain | DELETE | `DeleteOntologyDomain` | L3 write | explicit delete confirmation |

CREATE / UPDATE / DELETE submit JSON to `wedatacli <Action> '<JSON>'`; parameters come from `wedatacli --describe <Action>`. Passing `Labels` without `UpdateLabels=true` on UPDATE is ignored by service.

## Fields

| Field | Required | Contract |
|---|---|---|
| `Name` | CREATE | unique in Workspace; independent namespace |
| `Description` | optional | text |
| `BusinessOwnerId` | optional | business owner uin numeric string |
| `DevelopOwnerId` | optional | developer owner uin numeric string |
| `Labels` | CREATE | `[]OntologyDomainTagKey`, each `{LabelId, LabelValueId}`, count 1-20; UPDATE controlled by `UpdateLabels` |
| `UpdateLabels` | UPDATE | `true` overwrites full label set; false/missing ignores `Labels` |
| `Id` / `Name` | locate | UPDATE requires `Id`; GET/DELETE support `Id` or `Name` + WorkspaceId |

`Labels[].LabelId` and `LabelValueId` are real label-center IDs, not display names. If the user gives label names only, run `ListLabels` to resolve IDs. If unresolved, stop and ask the user to create/confirm labels; never invent IDs.

## State matrix

`OntologyDomainVO.Status` semantics (verified 2026-08-14 on ap-chongqing ws=17793323750369703; also confirmed on ws=17785903443560603): `Status=0` = **Live / Published** (returned by `ListOntologyDomains '{"StatusList":[0]}'`); `Status=1` = **Offline** (`StatusList:[1]` returned zero rows). `wedatacli --describe ListOntologyDomains` shows `StatusList: 0-已发布 1-已下线`, which agrees with the live behavior. Do NOT treat `1` as normal-online semantics or filter for `1` by default. Other values are service soft-delete states and usually not listed.

⚠️ **Semantic INVERSION vs. semantic-YAML objects**: metric / model use `MetadataStatus` where `1=ONLINE, 2=DISABLED`; dimension uses `MetadataStatus` where `1=已创建/active, 2=已删除/deleted` (no draft, no disable state; legacy value `3` is retired-enum residue and MUST be treated as active-equivalent to `1` — see `dimension_spec.md` §`MetadataStatus` authoritative enum). Domain `Status=0` and metric/model `MetadataStatus=1` and dimension `MetadataStatus in (1,3)` **all** mean "live / active", but the numeric codes differ across objects. Do NOT use semantic `MetadataStatus` on domains; do NOT reuse a domain filter/rendering pipeline for semantic objects without re-mapping the numeric codes.

| Operation | Allowed | Rejected |
|---|---|---|
| CREATE | object missing | same-name domain exists |
| UPDATE | object exists | object missing |
| DELETE | object exists | object missing; report already gone and do not retry |

Domains have no Enable/Disable and never participate in semantic YAML name lists.

## CREATE flow

1. Uniqueness precheck: `ListOntologyDomains '{"KeyWord":"<name>","PageNumber":1,"PageSize":20}'`, then exact-filter `Data[].Data.Name`. On hit, stop, show conflict, recommend a suffixed name, and ask whether to rename or update.
2. Label resolution: at least one label is mandatory. If only display names are provided, call `ListLabels '{"Shared":true,"KeyWord":"<display>","Page":{"PageNumber":1,"PageSize":10}}'` and resolve real IDs. If none, stop; do not send an empty label list.
3. Owner handling: if the user gives a human name, ask for uin; if they explicitly say no owner, omit it.
4. Confirmation page: show `Name`, `Description`, `BusinessOwnerId`, `DevelopOwnerId`, and resolved labels with display names when known.
5. Submit `CreateOntologyDomain` JSON.
6. Read back with `GetOntologyDomain '{"Name":"<name>"}'` and report `Response.Data.Data.Id`.

## UPDATE flow

1. Locate `Id`. If only Name is available, use `ListOntologyDomains` exact filtering. Zero hits → ask whether to CREATE; multiple hits → ask user to clarify.
2. `GetOntologyDomain`, diff old vs requested fields and label set.
3. If labels change, set `UpdateLabels=true` and pass the complete target `Labels`; warn that unlisted old labels will be removed. If labels do not change, omit labels or use `UpdateLabels=false`.
4. Submit `UpdateOntologyDomain` and read back to verify.

## DELETE flow

1. Locate `Id` as above.
2. Visible dependency/asset detection: call the four tab list APIs with `PageSize:1` to detect counts for entities, semantic models, metrics, and dimensions. Hits do not block deletion, but must be shown.
3. Require explicit delete confirmation.
4. Submit `DeleteOntologyDomain '{"Id":"<id>"}'`; success is `Response.Data.Success=true`.
5. Pass through any business error; do not auto-retry or switch APIs.

## Read-only queries

| Intent | Command |
|---|---|
| list domains | `wedatacli ListOntologyDomains '{"PageNumber":1,"PageSize":20}'` |
| filter live domains | `wedatacli ListOntologyDomains '{"KeyWord":"...","OwnerList":["uin"],"StatusList":[0],"PageNumber":1,"PageSize":20}'` |
| detail | `wedatacli GetOntologyDomain '{"Id":"<id>"}'` or `{"Name":"<name>"}` |
| domain entities | `ListOntologyDomainEntities '{"DomainId":"<id>","PageNumber":1,"PageSize":20}'` |
| domain semantic models | `ListOntologyDomainSemanticModels '{"DomainId":"<id>","PageNumber":1,"PageSize":20}'` |
| domain metrics | `ListOntologyDomainMetrics '{"DomainId":"<id>","PageNumber":1,"PageSize":20}'` |
| domain dimensions | `ListOntologyDomainDimensions '{"DomainId":"<id>","PageNumber":1,"PageSize":20}'` |
| domain models / all / orphan | `ListDomainsModels '{"DomainIds":[...],"OrphanOnly":false,"PageNumber":1,"PageSize":20}'` |

Response paths:

- `ListOntologyDomains` → `Response.Data.{TotalCount,Data:[{Data:OntologyDomainVO,AssetCount:{...}}]}`.
- `GetOntologyDomain` → `Response.Data.Data.{Id,Name,Description,Status,RelatedTags,...}`.

Parameter traps:

- Four tab APIs use `DomainId` as a string long integer, e.g. `"42"`.
- `ListEntities` / `ListEntityGraph` use `BusinessDomainId` / `BusinessDomainIds` as int64/[]int64.
- `ListDomainsModels` uses `DomainIds` as `[]int64`; `OrphanOnly=true` requires empty `DomainIds`; `OrphanOnly=false` with empty `DomainIds` returns all Workspace models and may trigger stdout truncation.

## Prohibitions

- Do not mix domain names into semantic YAML operation lists.
- Do not use `MetadataStatus` for domains.
- Do not invent label IDs.
- Do not forget `UpdateLabels=true` when changing labels.
- Do not silently overwrite label sets.
- Do not delete without visible asset detection and explicit confirmation.
- Do not handle entity attach/detach through domain APIs; use `BatchAttachEntityBusinessDomain` / `BatchDetachEntityBusinessDomain`.
