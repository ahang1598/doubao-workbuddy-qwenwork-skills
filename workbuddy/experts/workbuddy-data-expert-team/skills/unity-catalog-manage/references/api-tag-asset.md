# Tag / AssetTag API Reference

> Load on demand. [SKILL.md](../SKILL.md) is the single authority for call rules, safety constraints, anti-hallucination baselines, and label API contracts. Examples omit the outer auto-injected `WorkspaceId`; explicitly override it for cross-workspace calls. Exception: `UpdateLabels.PolicyBindingUpdate.WorkspaceId` is the target workspace for the policy binding and may differ from the current workspace; it must be explicit.

## 0. Label semantics -> Type -> skill routing

Use this to classify user "tag / mark / label" requests and avoid routing executable business tagging to masking or semantic skills.

| User wording | Route | Skill | Notes |
|---|---|---|---|
| BI, report, business purpose, department, project, core asset, analyst, data extraction, warehouse layer, subject domain | business-tag family (`Type` != 4) | **unity-catalog-manage** | Use `CreateLabels` + `BatchVoteAssetTag`. Never hard-map user wording to a specific `Type` value — resolve `Type` at runtime by reading `ListLabels` distribution (or `scripts/label_ops.py --group-by-type`) or by asking the user. |
| PII, GDPR, phone number, ID card, bank card, sensitive field, masking, data classification, security scan | `Type=4` masking | **data-classification** | Yield to data-classification AI tagging plus masking-policy workflow. |
| metric, dimension, semantic model, definition, measure | Not a Label; semantic object | **semantic-manage** | Use YAML CRUD; not this skill. |

Priority: if one sentence contains both business-tag and masking terms, such as "tag BI tables as sensitive", masking terms win and routing goes to `data-classification`. Only pure business-tag terms start this skill's read-only exploration branch in [SKILL.md](../SKILL.md).

`Type` has two authoritative layers — do not conflate them:
- **Schema layer** (`CreateLabels.Type` enum, from the runtime schema): `1 / 2 / 3 / 4` — the raw enum values the server accepts on write. `Type=4` is the fixed masking bucket; `1 / 2 / 3` are non-masking buckets whose business meaning is workspace-configurable and NOT fixed by the schema. Cross-referenced in `data-classification/reference/api_reference.md`.
- **Business-dictionary layer** (per-workspace label taxonomy exposed by `ListLabels`): the mapping of each non-masking `Type` integer to a business name (e.g. business / category / BI / department / project / governance) is a **workspace dictionary**, not a schema constant. Read it live from `ListLabels`, or use the built-in mapping in `scripts/label_ops.py` (`_TYPE_LABEL`).

Routing (this table) only depends on the schema layer (masking = 4 vs non-masking = else). Selecting a specific `Type` value for `CreateLabels` / `BatchVoteAssetTag` MUST always go through the business-dictionary layer — never inline a fixed keyword-to-int mapping in prompts or code.

---

## 1. TagService

Manage labels and label values.

| Operation | API | Example |
|---|---|---|
| Batch create labels | `CreateLabels` | `wedatacli CreateLabels '{"Shared":true,"Labels":[{"Name":"Data Quality","Type":1,"Values":[{"Value":"Excellent"},{"Value":"Good"},{"Value":"Poor"}]}]}'` |
| Create masking label with optional policy binding | `CreateLabels` | `wedatacli CreateLabels '{"Shared":true,"Labels":[{"Name":"PII-Phone","Type":4,"SecurityTypes":["PII"],"PolicyId":"policy_xxx","PolicyBindingWorkspaceId":"<target workspace>"}]}'` |
| List labels | `ListLabels` | `wedatacli ListLabels '{"Shared":true,"Page":{"PageNumber":1,"PageSize":100}}'` |
| List masking labels with filters | `ListLabels` | `wedatacli ListLabels '{"Shared":true,"Types":[4],"SecurityTypes":["PII","GDPR"],"PolicyBindStatus":1,"Page":{"PageNumber":1,"PageSize":100}}'` |
| Batch list label names and values | `ListLabelInfos` | `wedatacli ListLabelInfos '{"QueryItems":[{"LabelId":1,"ValueIds":[10,11]}]}'` |
| Update label name/comment | `UpdateLabels` | `wedatacli UpdateLabels '{"Shared":true,"Labels":[{"LabelId":1,"Name":"Data Quality Level","Modifier":"user_001"}]}'` |
| Update masking label security types | `UpdateLabels` | `wedatacli UpdateLabels '{"Shared":true,"Labels":[{"LabelId":1,"Modifier":"user_001","SecurityTypesUpdate":{"SecurityTypes":["PII","GDPR"]}}]}'` |
| Bind or replace masking-label policy | `UpdateLabels` | `wedatacli UpdateLabels '{"Shared":true,"Labels":[{"LabelId":1,"Modifier":"user_001","PolicyBindingUpdate":{"PolicyId":"policy_new","WorkspaceId":"<policy target workspace>"}}]}'` |
| Unbind masking-label policy | `UpdateLabels` | `wedatacli UpdateLabels '{"Shared":true,"Labels":[{"LabelId":1,"Modifier":"user_001","PolicyBindingUpdate":{"PolicyId":""}}]}'` |
| Batch delete labels | `DeleteLabels` | `wedatacli DeleteLabels '{"Shared":true,"LabelIds":[1,2]}'` |
| Create label values | `CreateLabelValues` | `wedatacli CreateLabelValues '{"LabelId":1,"Values":[{"Value":"Outstanding"}]}'` |
| Delete label values | `DeleteLabelValues` | `wedatacli DeleteLabelValues '{"LabelId":1,"Values":["Poor"]}'` |

`CreateLabels` has both `Type` and `SourceType`; verify with the runtime schema for `CreateLabels` before calls. Current contract uses `Type=4` for masking labels and can include `SecurityTypes`, `PolicyId`, and `PolicyBindingWorkspaceId`; `SourceType` is backend-injected and should not be passed by clients. `CreateLabels.Values` uses `CreateLabelValueInfo`. `DeleteLabelValues` deletes by label value string, not ID. `ListLabels` uses `Page` struct pagination.

**`CreateLabels.Labels[].Values` structural quirk**: must be an object array `[{"Value":"pass"},{"Value":"fail"}]`, never a plain string array. Passing `["pass","fail"]` returns `json: cannot unmarshal string into Go struct field CreateLabelInfo.Labels.Values of type v20251010.CreateLabelValueInfo`. `CreateLabelValues.Values` uses the same `CreateLabelValueInfo` object shape; `DeleteLabelValues.Values` conversely takes a plain string array of value literals. Do not swap the two shapes.

Critical label-call contracts, including `Shared=true`, `UpdateLabels` wrapper three-state semantics, and one-step `CreateLabels` policy binding, are authoritative in [SKILL.md 2.11](../SKILL.md#211-label-api-contracts). In particular, `UpdateLabels.PolicyBindingUpdate.WorkspaceId` is the policy target workspace and is semantically different from the outer `WorkspaceId`; it must be explicit.

`ListLabels` response enhancement: `Type=4` masking labels return `MaskPolicy` (`{PolicyId, PolicyName, BindTime}`) when a policy is bound; no policy means this field is absent. The frontend does not need N+1 calls to `ListMaskPoliciesByLabel`.

---

## 2. AssetTagService

Apply, update, delete, and query asset tags.

| Operation | API | Example |
|---|---|---|
| Batch tag assets | `BatchVoteAssetTag` | `wedatacli BatchVoteAssetTag '{"Votes":[{"PropertyType":"TABLE","PropertyId":"asset_guid_001","Tags":[{"LabelId":"1","LabelName":"Data Quality","LabelValueId":"10","LabelValue":"Excellent","Type":1}]}]}'` |
| List tags by assets | `ListTagsByAsset` | `wedatacli ListTagsByAsset '{"QueryItems":[{"PropertyType":"TABLE","PropertyId":"asset_guid_001"},{"PropertyType":"TABLE","PropertyId":"asset_guid_002"}]}'` |
| Delete asset tag | `DeleteAssetTagVote` | `wedatacli DeleteAssetTagVote '{"PropertyType":"TABLE","PropertyId":"asset_guid_001","LabelId":1}'` |
| Update asset tag | `UpdateAssetTag` | `wedatacli UpdateAssetTag '{"PropertyType":"TABLE","PropertyId":"asset_guid_001","Tags":[{"LabelId":"1","LabelName":"Data Quality","LabelValueId":"11","LabelValue":"Good","Type":1}],"Modifier":"user_001"}'` |

The CLI uses `BatchVoteAssetTag` for asset tagging even for a single asset; put items in `Votes`. Asset identity is `PropertyType` + `PropertyId` (asset GUID). Tag data uses `Tags` list (`TagInfo`: `LabelId` + `LabelName` + `LabelValueId` + `LabelValue`; `LabelId` and `LabelValueId` are strings). Field-level tags use `FieldTags`. `CreateCustomLabel=true` can auto-create custom labels. The current CLI does not expose single-asset tagging or reverse lookup by label.

`BatchVoteAssetTag.Votes[].Tags[].Type` is server-required even though the runtime schema does not mark it required. Omitting it returns `InvalidParameterValue.InvalidParameter / Unsupported label type: LABEL_TYPE_UNKNOWN`. Always pass `Type` explicitly, sourced from the target label's `Type` field returned by `ListLabels` (never inline a fixed keyword-to-int mapping — see §0 on the schema-vs-business-dictionary split). `UpdateAssetTag.Tags[].Type` has the same origin; pass it explicitly too.

`DeleteAssetTagVote.LabelId` is `int64`, unlike string `BatchVoteAssetTag.Tags[].LabelId`; pass a numeric literal such as `"LabelId":1`. A string value fails JSON deserialization.

All APIs require `WorkspaceId`, auto-injected by `wedatacli` from `~/.wedata/config.json`; examples omit it. Explicitly override only for another workspace.
