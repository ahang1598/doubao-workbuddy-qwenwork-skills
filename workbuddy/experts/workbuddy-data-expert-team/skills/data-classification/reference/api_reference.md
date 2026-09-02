# API Reference — 敏感数据分类与脱敏标签打标

本文档详细描述本 skill 涉及的所有 API 的请求/响应参数。

## 目录

- [1. ListCatalogNames — 查询 Catalog 名称列表](#1-listcatalognames--查询-catalog-名称列表)
- [2. SearchAsset — 资产搜索](#2-searchasset--资产搜索)
- [3. ListLabels — 查询标签列表](#3-listlabels--查询标签列表)
- [4. BatchVoteAssetTag — 批量资产打标](#4-batchvoteasset tag--批量资产打标)
- [5. ListMaskPoliciesByLabel — 根据标签查询绑定的脱敏策略](#5-listmaskpoliciesbylabel--根据标签查询绑定的脱敏策略)
- [5.1 UpdatePolicyLabelBindings — 策略侧声明式批量关联标签（推荐）](#51-updatepolicylabelbindings--策略侧声明式批量关联标签推荐)
- [6. BindLabelMaskPolicy — 绑定脱敏标签与脱敏策略](#6-bindlabelmaskpolicy--绑定脱敏标签与脱敏策略)
- [7. UnbindLabelMaskPolicy — 解绑脱敏标签与脱敏策略](#7-unbindlabelmaskpolicy--解绑脱敏标签与脱敏策略)
- [8. ListTagsByAsset — 查询资产标签](#8-listtagsbyasset--查询资产标签)
- [9. ListDataMaskStrategies — 查询脱敏策略列表](#9-listdatamaskstrategies--查询脱敏策略列表)
- [10. UpdateAssetTagExclusions — 更新 AI 打标排除记录](#10-updateassettagexclusions--更新-ai-打标排除记录)
- [11. ListAssetTagExclusions — 查询 AI 打标排除记录](#11-listassettagexclusions--查询-ai-打标排除记录)
- [12. ListDataMaskStrategyTypes — 查询脱敏方法枚举列表](#12-listdatamaskstrategytypes--查询脱敏方法枚举列表)
- [13. CreateDataMaskStrategy — 创建脱敏策略](#13-createdatamaskstrategy--创建脱敏策略)
- [14. DeleteDataMaskStrategy — 删除脱敏策略](#14-deletedatamaskstrategy--删除脱敏策略)
- [15. UpdateDataMaskStrategy — 更新脱敏策略](#15-updatedatamaskstrategy--更新脱敏策略)
- [16. ListConsoleGroups — 查询用户组列表](#16-listconsolegroups--查询用户组列表)
- [17. ListMaskPolicyDispatchLogs — 查询脱敏策略下发流水](#17-listmaskpolicydispatchlogs--查询脱敏策略下发流水)
- [枚举值参考](#枚举值参考)

---

## 1. ListCatalogNames — 查询 Catalog 名称列表

**服务**：`CatalogService`
**用途**：查询当前工作空间下的 Catalog 名称列表，用于用户不确定有哪些 Catalog 时辅助选择扫描范围

### 请求参数（ListCatalogNamesReq）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| MaxResults | int64 | 否 | 最大结果条数，默认 10 |
| PageToken | string | 否 | 分页 Token（base64 编码） |
| WorkspaceId | string | 是 | 工作空间 ID |
| Types | string[] | 否 | Catalog 类型过滤，如 `["TABLE"]`、`["MODEL"]`、`["VOLUME"]`，不填默认查询所有类型 |

### 响应参数（ListCatalogNamesRsp）

| 字段 | 类型 | 说明 |
|------|------|------|
| Items | NameIdentifier[] | Catalog 名称列表 |
| NextPageToken | string | 下一页 Token，为空表示没有更多数据 |

### NameIdentifier 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| Name | string | Catalog 名称 |

### 调用示例

```bash
# 查询表类型的 Catalog 列表
wedatacli ListCatalogNames '{"WorkspaceId":"123456","Types":["TABLE"],"MaxResults":50}'

# 分页获取下一页
wedatacli ListCatalogNames '{"WorkspaceId":"123456","Types":["TABLE"],"MaxResults":50,"PageToken":"<next_page_token>"}'
```

---

## 2. SearchAsset — 资产搜索

**服务**：`AssetSearchService`
**用途**：搜索 Catalog 下的表，获取字段信息和已有标签

### 请求参数（SearchAssetReq）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| Keyword | string | 否 | 搜索关键字 |
| AssetTypes | string[] | 否 | 资产类型过滤，如 `["TABLE"]` |
| MaxResults | int64 | 否 | 最大结果条数，取值 1～50，默认 30 |
| PageToken | string | 否 | 分页 Token（base64 编码） |
| WorkspaceId | string | 是 | 工作空间 ID |
| Owner | string[] | 否 | 责任人过滤 |
| TagIds | int64[] | 否 | 资产标签 ID 过滤 |
| TagValueIds | int64[] | 否 | 资产标签值 ID 过滤 |
| ModifiedTime | string | 否 | 更新时间，毫秒字符串 |
| CatalogNames | string[] | 否 | Catalog 名称列表过滤 |
| WorkspacePaths | string[] | 否 | 工作空间路径过滤 |
| Order | WeDataOrderFields[] | 否 | 排序字段列表 |
| FieldTagIds | int64[] | 否 | 字段标签 ID 列表，根据字段上打的标签检索资产（表），最多支持 20 个标签 ID |
| EnableHybridSearch | bool | 否 | 是否开启混合搜索 |

### 响应参数（SearchAssetRsp）

| 字段 | 类型 | 说明 |
|------|------|------|
| Items | SearchResult[] | 搜索结果列表 |
| NextPageToken | string | 下一页 Token，为空表示没有更多数据 |

### SearchResult 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| FullName | string | 资产全名，catalog.schema.assetName |
| AssetGuid | string | 资产全局 ID（UUID） |
| AssetId | string | 各资产类别下的唯一 ID |
| AssetName | string | 资产名称 |
| AssetType | string | 资产类型 |
| Tags | TagInfo[] | 资产标签列表 |
| Owner | Owner | 资产责任人 |
| ModifiedTime | string | 最近更新时间，13 位时间戳 |
| Comment | string | 描述 |
| WorkspaceId | string | 工作空间 ID |
| FieldInfo | FieldInfo[] | 字段信息列表 |
| FieldTags | FieldTagInfo[] | 字段标签信息列表 |
| Properties | KVPair[] | 各类资产的元数据属性 |

### FieldInfo 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| Name | string | 字段名称 |
| Comment | string | 字段描述 |
| Type | string | 字段类型 |
| Lang | string | 语言类型 |
| Content | string | 字段内容或代码片段 |
| SampleValues | string[] | 字段采样值列表，字段实际数据的采样值。**可能为空**（采样未开启 / 数据为空 / 无访问权限等场景）。在敏感字段识别中作为可选辅助输入，用于交叉验证元数据匹配结论；展示给用户时必须先脱敏处理，严禁明文展示完整真实值 |

### 调用示例

```bash
# 搜索指定 Catalog 下的所有表
wedatacli SearchAsset '{"Keyword":"","AssetTypes":["TABLE"],"CatalogNames":["my_catalog"],"MaxResults":50,"WorkspaceId":"123456"}'

# 搜索指定 Catalog 下包含关键字的表
wedatacli SearchAsset '{"Keyword":"user","AssetTypes":["TABLE"],"CatalogNames":["my_catalog"],"MaxResults":50,"WorkspaceId":"123456"}'

# 分页获取下一页
wedatacli SearchAsset '{"Keyword":"","AssetTypes":["TABLE"],"CatalogNames":["my_catalog"],"MaxResults":50,"PageToken":"<next_page_token>","WorkspaceId":"123456"}'
```

---

## 3. ListLabels — 查询标签列表

**服务**：`TagService`
**用途**：查询脱敏标签列表（LabelType=4）

### 请求参数（ListLabelsReq）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| WorkspaceId | string | 是 | 工作空间 ID，**用于 gateway 工作空间维度 RBAC 鉴权**，必须传当前用户所在工作空间的真实 ID。⚠️ **不再支持传 `all` 跳过鉴权**。 |
| Shared | bool | 是（业务侧） | **调用标签接口时统一传 `true`**（页面上展示的业务标签和脱敏标签底层是同一组资源，全部通过 `Shared=true` 访问；不带 `Shared=true` 会被工作空间过滤掉大部分可见标签，本 skill 必传）。 |
| LabelIds | int64[] | 否 | 标签 ID 列表 |
| LabelNames | string[] | 否 | 标签名称列表（精确查询） |
| Control | int64 | 否 | 管控状态过滤（参考 LabelControlStatus 枚举） |
| Page | Page | 否 | 分页结构体，**不传时服务端默认只返回 20 条**；建议首次即显式传入 `PageSize=100` 尽量一次拉全 |
| Types | int64[] | 否 | 标签类型列表，`[4]` 表示脱敏标签，不传则默认查询类型 1 和 2 |
| KeyWord | string | 否 | 关键词模糊查询标签名称 |
| OrderBy | WeDataOrderFields[] | 否 | 排序字段列表 |
| SourceTypes | int32[] | 否 | 来源类型筛选。不传/空数组=不过滤；`[1]`=仅查系统标签；`[2]`=仅查自定义标签 |
| SecurityTypes | string[] | 否 | 安全规范筛选（**仅对 Type=4 有效**）。不传/空数组=不过滤；任一命中即返回（OR 语义）；取值范围 `PII / GDPR / HIPAA / PCI-DSS / CCPA / PDPA` |
| PolicyBindStatus | int32 | 否 | 策略关联状态筛选（**仅对 Type=4 有效**）。`0`=不过滤（默认）；`1`=仅查已关联策略的标签；`2`=仅查未关联策略的标签 |

### Page 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| PageNumber | int64 | 当前页码，从 1 开始 |
| PageSize | int64 | 每页大小，推荐 100 |

> ⚠️ **首次请求即用 `PageSize=100`**：调用 `ListLabels` 时首次请求就传入 `Page={PageNumber:1, PageSize:100}`，通常一个请求即可拉全标签；只有在响应 `TotalCount > 100` 时才需要继续翻页。不传 `Page` 默认只返回 20 条，虽然不会漏数据，但会造成多轮无谓翻页请求、降低执行效率。

### 响应参数（ListLabelsRsp）

| 字段 | 类型 | 说明 |
|------|------|------|
| Message | string | 响应消息 |
| Labels | BizLabel[] | 标签列表 |
| TotalCount | int64 | 总记录数 |

### BizLabel 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| Id | string | 标签 ID |
| Name | string | 标签名称 |
| Description | string | 标签描述 |
| WorkspaceId | string | 工作空间 |
| Control | int64 | 管控状态 |
| Creator | string | 创建者 |
| Modifier | string | 修改者 |
| CreateTime | string | 创建时间 |
| ModifiedTime | string | 更新时间 |
| Values | BizLabelValue[] | 标签值列表；LabelType=4（脱敏标签）时可为空 |
| Type | int64 | 标签类型：1-治理标签，2-自定义标签，3-属性标签，4-脱敏标签 |
| SourceType | int64 | 标签来源类型：1-系统，2-自定义 |
| SecurityTypes | string[] | 安全类型，仅 LabelType=4（脱敏标签）时有效，支持多选，枚举值：PII、GDPR、HIPAA、PCI-DSS、CCPA、PDPA |
| MaskPolicy | LabelMaskPolicyBrief | **当前关联的脱敏策略简要信息**（仅 LabelType=4 时回填；**未关联策略时该字段不返回**）。一个敏感标签同时只能关联 1 个脱敏策略，所以是单值；关联跨工作空间共享。⭐ **优先读本字段，无需 N+1 调 `ListMaskPoliciesByLabel`** |

### LabelMaskPolicyBrief 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| PolicyId | string | 脱敏策略 ID（前端可用于跳转策略详情：`/governance/masking-policy/{PolicyId}`） |
| PolicyName | string | 脱敏策略名称 |
| BindTime | int64 | 关联建立时间（13 位时间戳） |

### BizLabelValue 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| Id | string | 标签值 ID |
| LabelId | string | 标签 ID |
| Value | string | 标签值 |
| Weight | int64 | 标签值权重 |
| Creator | string | 创建人 |
| Modifier | string | 修改者 |
| CreateTime | string | 创建时间 |
| ModifiedTime | string | 更新时间 |

### 调用示例

> ⚠️ **本 skill 所有 `ListLabels` 调用必须同时携带 `WorkspaceId`（用于 gateway 鉴权）+ `Shared=true`（页面展示的业务标签/脱敏标签的统一调用约定）**。漏传 `Shared=true` 会因工作空间过滤拿不到大部分页面可见标签，导致整个分级工作流空跑。

```bash
# 首次请求（按 TotalCount 判断是否需要继续翻页）；响应 BizLabel.MaskPolicy 已直接给出关联策略
wedatacli ListLabels '{"WorkspaceId":"<ws_id>","Shared":true,"Types":[4],"Page":{"PageNumber":1,"PageSize":100}}'

# 第二页
wedatacli ListLabels '{"WorkspaceId":"<ws_id>","Shared":true,"Types":[4],"Page":{"PageNumber":2,"PageSize":100}}'

# 按关键词搜索脱敏标签
wedatacli ListLabels '{"WorkspaceId":"<ws_id>","Shared":true,"Types":[4],"KeyWord":"class","Page":{"PageNumber":1,"PageSize":100}}'

# 按 SecurityTypes + 关联状态过滤（仅 Type=4 有效）
wedatacli ListLabels '{"WorkspaceId":"<ws_id>","Shared":true,"Types":[4],"SecurityTypes":["PII","GDPR"],"PolicyBindStatus":1,"Page":{"PageNumber":1,"PageSize":100}}'

# 仅查未关联任何策略的脱敏标签（用于"待关联"清单）
wedatacli ListLabels '{"WorkspaceId":"<ws_id>","Shared":true,"Types":[4],"PolicyBindStatus":2,"Page":{"PageNumber":1,"PageSize":100}}'
```

---

## 4. BatchVoteAssetTag — 批量资产打标

**服务**：`AssetTagService`
**用途**：批量为字段打上脱敏标签

> ⚠️ **重要：增量合并模式（按资产 + 按字段）**。服务端通过 `FieldTags` 是否为空推断用户意图：
> - **FieldTags 为空**：仅更新 Tags（Tags 无论空不空都覆盖）；FieldTags 保持原值
> - **Tags 为空**：仅更新 FieldTags，按 FieldName 维度增量覆盖；Tags 保持原值
> - **两者均非空**：Tags 整体覆盖，FieldTags 按 FieldName 增量覆盖
>
> **FieldTags 按 FieldName 增量覆盖语义**：传入的 FieldName 对应所有标签会**完全替换** ES 中该字段已有标签；未传入的 FieldName 对应的已有标签保持不变。因此只需传本次要打标的字段，但同一字段仍需合并已有标签 + 新增标签，否则该字段已有标签会丢失。
>
> **清除标记**：FieldTags 中某项若 `LabelId="-1"`，视为「清除标记」：服务端会清除该 FieldName 下所有字段标签（不追加新标签）；清除标记项本身不保存。可与正常打标项混用。
>
> **前置条件**：
> - 单个资产 Tags 数量上限 50
> - 同一字段最多只能关联一个 LabelType=4 的脱敏标签，且已有脱敏标签的字段不能再关联其他标签
>
> **错误处理**：单个资产打标失败不影响其他资产，各资产结果通过 Results 返回。

### 请求参数（BatchVoteAssetTagReq）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| WorkspaceId | string | 是（自动注入） | 工作空间 ID；wedatacli 从 `~/.wedata/config.json` 自动注入，命令行示例无需显式传入 |
| Votes | VoteAssetTagReq[] | 是 | 批量打标请求列表 |

### VoteAssetTagReq 结构

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| PropertyType | string | 是 | 资产类型，字段打标时固定传 `"TABLE"` |
| PropertyId | string | 是 | 表的资产全局 ID（`SearchResult.AssetGuid`，UUID 格式） |
| Tags | TagInfo[] | 否 | 资产级标签列表；空表示不更新资产级标签 |
| Creator | string | 是 | 创建人 |
| OwnerAccount | string | 否 | 所有者账号 |
| FieldTags | FieldTagInfo[] | 否 | 字段标签列表，按 FieldName 增量覆盖；LabelId="-1" 为清除标记；单次最多 100 条 |

### TagInfo 结构

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| LabelId | string | 是 | 标签 ID |
| LabelName | string | 是 | 标签名称 |
| LabelValueId | string | 否 | 标签值 ID（脱敏标签的标签值非必填，设为 "0"） |
| LabelValue | string | 否 | 标签值；LabelType=4（脱敏标签）时非必填 |
| IsDeleted | bool | 否 | 标签是否已删除 |
| Type | int64 | 是 | 标签类型，脱敏标签固定为 4 |
| CreateCustomLabel | bool | 否 | 是否创建自定义标签，脱敏标签场景为 false |

### FieldTagInfo 结构

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| LabelId | string | 是 | 标签 ID；特殊值 `"-1"` 表示「清除标记」，服务端会清除该 FieldName 下所有标签 |
| LabelName | string | 否 | 标签名称；清除标记场景可省 |
| LabelType | int64 | 否 | 标签类型：1-治理 2-自定义 3-属性 4-脱敏；清除标记场景可省 |
| FieldName | string | 是 | 字段名称；增量合并的维度 key |
| FieldType | string | 否 | 字段类型，如 string、int、bigint 等 |
| LabelValueId | string | 否 | 标签值 ID；脱敏标签（LabelType=4）非必填 |
| LabelValue | string | 否 | 标签值；脱敏标签（LabelType=4）非必填 |

### 响应参数（BatchVoteAssetTagRsp）

| 字段 | 类型 | 说明 |
|------|------|------|
| SuccessCount | int64 | 成功数量 |
| FailureCount | int64 | 失败数量 |
| Results | VoteAssetTagRsp[] | 详细结果 |

### VoteAssetTagRsp 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| VoteId | string | 投票记录 ID |
| Success | bool | 是否成功 |
| Message | string | 错误信息 |

### 调用示例

```bash
# 示例 1：纯字段打标（脱敏场景最常用）
# 只关心 FieldTags，不传 Tags ⇒ 资产级标签保持不变
# 同一字段需传 「已有标签 + 新增标签」 的全量合并结果（按 FieldName 覆盖）
wedatacli BatchVoteAssetTag '{"Votes":[{"PropertyType":"TABLE","PropertyId":"550e8400-e29b-41d4-a716-446655440000","Creator":"zhangsan","FieldTags":[{"LabelId":"100","LabelName":"已有治理标签","LabelType":1,"FieldName":"phone","FieldType":"string"},{"LabelId":"1001","LabelName":"手机号","LabelType":4,"FieldName":"phone","FieldType":"string"}]}]}'

# 示例 2：清除指定字段的全部标签（LabelId=-1 清除标记）
wedatacli BatchVoteAssetTag '{"Votes":[{"PropertyType":"TABLE","PropertyId":"550e8400-e29b-41d4-a716-446655440000","Creator":"zhangsan","FieldTags":[{"LabelId":"-1","FieldName":"phone","FieldType":"string"}]}]}'

# 示例 3：清除某字段标签 + 为另一字段新打标（混合场景）
wedatacli BatchVoteAssetTag '{"Votes":[{"PropertyType":"TABLE","PropertyId":"550e8400-e29b-41d4-a716-446655440000","Creator":"zhangsan","FieldTags":[{"LabelId":"-1","FieldName":"phone","FieldType":"string"},{"LabelId":"1002","LabelName":"邮箱","LabelType":4,"FieldName":"email","FieldType":"string"}]}]}'
```

---

## 5. ListMaskPoliciesByLabel — 根据标签查询绑定的脱敏策略

**服务**：`AssetTagService`
**用途**：查询脱敏标签绑定的脱敏策略信息，用于标签管理页展示策略关联关系

### 请求参数（ListMaskPoliciesByLabelReq）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| LabelId | string | 是 | 标签 ID |

### 响应参数（ListMaskPoliciesByLabelRsp）

| 字段 | 类型 | 说明 |
|------|------|------|
| PolicyRelList | LabelMaskPolicyRelInfo[] | 策略关联列表 |
| TotalCount | int64 | 总数 |

### LabelMaskPolicyRelInfo 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| RelId | string | 关联记录 ID |
| LabelId | string | 标签 ID |
| LabelName | string | 标签名称 |
| PolicyId | string | 脱敏策略 ID |
| PolicyName | string | 脱敏策略名称 |
| Creator | string | 创建人 |
| CreateTime | string | 创建时间，13 位时间戳 |

### 调用示例

```bash
# 查询指定脱敏标签绑定的策略
wedatacli ListMaskPoliciesByLabel '{"LabelId":"1001"}'
```

---

> ℹ️ **策略视角反查接口未暴露给 dataclaw skill**：`ListLabelsByPolicyId`（单策略反查关联标签）和 `BatchListLabelsByPolicyIds`（批量反查避免 N+1）目前仅供 platform/security 内部 trpc 互调使用，**未注册到云 API**，因此本文档不收录。dataclaw 场景下如需"按 PolicyId 反查 labels"，请用 `ListLabels(Types=[4])` 后客户端按 `BizLabel.MaskPolicy.PolicyId` 过滤；脱敏标签数量 < 200，无性能问题。

---

## 5.1 UpdatePolicyLabelBindings — 策略侧声明式批量关联标签（推荐）

**服务**：`AssetTagService`
**用途**：策略视角声明式批量管理关联（PUT 语义），**一个接口同时覆盖"新增/修改/删除"三个语义**。
**典型场景**：脱敏策略详情页/创建弹窗的"关联标签"保存按钮。

### 调用语义（声明式）

- `LabelIds` 是该策略**最终应当关联**的标签 ID 全集（**不是增量**）
- 服务端自动 diff：
  - 当前关联 - 目标 = 待解绑
  - 目标 - 当前关联 = 待绑定
  - 交集保持不变
- `LabelIds=[]` → 解绑该策略的所有标签

### 失败语义（all-or-nothing 全成全败）

- 任一标签业务校验失败（`policyAlreadyBound` / `labelNotFound` / `labelTypeNotDesensitization`）→ **整批回滚**（DB 关联表无任何变更）→ RPC error
- 入参非法 / 策略不存在 / DB 不可用 → RPC error
- 异步下发任务（`AttachDataMaskPolicy`）失败**不阻断**同步路径，仅记录日志

### 请求参数（UpdatePolicyLabelBindingsReq）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| PolicyId | string | 是 | 脱敏策略 ID（最大长度 128） |
| LabelIds | int64[] | 是 | 该策略最终应当关联的标签 ID 全集；可为空数组（=解绑全部）；长度 ≤ 200 |
| WorkspaceId | string | 是 | 工作空间 ID，**禁止 `"all"`**；用于：① 透传给 `Security.AttachDataMaskPolicy`；② 写入关联表 `workspace_id` 列作审计来源 |
| Operator | string | 否 | 操作人，未传时从 RequestContext 中获取 |

### 响应参数（UpdatePolicyLabelBindingsRsp）

| 字段 | 类型 | 说明 |
|------|------|------|
| Success | bool | true 表示整批已提交（DB 写入完成）；失败走 RPC error 而非 Success=false |
| Message | string | 错误信息（成功时为空） |
| AddedLabelIds | int64[] | 新增 bind 成功的标签 ID 列表 |
| RemovedLabelIds | int64[] | 解除 bind 成功的标签 ID 列表 |
| UnchangedLabelIds | int64[] | 保持不变的标签 ID 列表（已在关联中且仍在目标中） |
| AsyncTaskIds | string[] | 异步任务 ID 列表（每个 Bind/Unbind 各产生 1 个，可追踪字段级下发进度） |

### 错误码

| 错误码 | 含义 |
|--------|------|
| INVALID_PARAMETER | 参数非法（PolicyId/WorkspaceId 为空、WorkspaceId="all"、LabelIds 长度超 200 等） |
| LABEL_NOT_FOUND | 待 bind 标签不存在 |
| LABEL_TYPE_NOT_DESENSITIZATION | 待 bind 标签 LabelType ≠ 4（不是脱敏标签） |
| POLICY_ALREADY_BOUND | 待 bind 标签已绑到其他策略（一标签一策略约束） |

### 调用示例

```bash
# 该策略最终关联标签 [1, 2, 3]：服务端自动 diff 应用（增/删/保留）
wedatacli UpdatePolicyLabelBindings '{"PolicyId":"3001","LabelIds":[1,2,3],"WorkspaceId":"123456","Operator":"zhangsan"}'

# 解绑该策略的所有标签
wedatacli UpdatePolicyLabelBindings '{"PolicyId":"3001","LabelIds":[],"WorkspaceId":"123456","Operator":"zhangsan"}'
```

> 💡 **何时用本接口 vs `BindLabelMaskPolicy`/`UnbindLabelMaskPolicy`**：
> - 策略详情页"保存关联"、批量关联场景 → **优先用 `UpdatePolicyLabelBindings`**（一次请求、自动 diff、全成全败）
> - 单标签 ↔ 单策略的简单 1 对 1 操作 → 旧的 Bind/Unbind 仍可用，但新代码推荐统一走声明式接口

---

## 6. BindLabelMaskPolicy — 绑定脱敏标签与脱敏策略

**服务**：`AssetTagService`
**用途**：将脱敏标签与脱敏策略绑定，绑定关系写入为同步操作，策略下发到关联字段为异步执行

### 前置条件

- 标签必须为脱敏标签（LabelType=4）
- 脱敏策略必须已存在

### 错误码

| 错误码 | 说明 |
|--------|------|
| TAG_NOT_FOUND | 标签不存在 |
| POLICY_NOT_FOUND | 策略不存在 |
| LABEL_TYPE_NOT_DESENSITIZATION | 标签类型非脱敏标签 |
| POLICY_ALREADY_BOUND | 已绑定策略 |
| 1120201 | 安全服务参数校验失败 |
| 1120202 | 调用 DLC 接口失败 |
| 1120203 | 脱敏策略不存在 |
| 1120205 | 字段已绑定其他策略 |

### 请求参数（BindLabelMaskPolicyReq）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| LabelId | string | 是 | 标签 ID，要求 LabelType=4（脱敏标签） |
| PolicyId | string | 是 | 脱敏策略 ID，最大长度 128 |
| Operator | string | 是 | 操作人 |
| WorkspaceId | string | 是 | 工作空间 ID，用于调用 Security.AttachDataMaskPolicy 时传入 |

### 响应参数（BindLabelMaskPolicyRsp）

| 字段 | 类型 | 说明 |
|------|------|------|
| Success | bool | 是否成功（仅代表绑定关系写入成功，策略下发为异步） |
| Message | string | 错误信息 |
| AsyncTaskId | string | 异步任务 ID，可用于追踪策略下发进度 |

### 调用示例

```bash
# 绑定脱敏策略
wedatacli BindLabelMaskPolicy '{"LabelId":"1001","PolicyId":"3001","Operator":"zhangsan","WorkspaceId":"123456"}'
```

---

## 7. UnbindLabelMaskPolicy — 解绑脱敏标签与脱敏策略

**服务**：`AssetTagService`
**用途**：解除脱敏标签与脱敏策略的绑定，解绑关系删除为同步操作，策略从关联字段移除为异步执行

### 前置条件

- 标签与策略的绑定关系必须存在

### 错误码

| 错误码 | 说明 |
|--------|------|
| TAG_NOT_FOUND | 标签不存在 |
| POLICY_BINDING_NOT_FOUND | 绑定关系不存在 |
| 1120201 | 安全服务参数校验失败 |
| 1120202 | 调用 DLC 接口失败 |

### 请求参数（UnbindLabelMaskPolicyReq）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| LabelId | string | 是 | 标签 ID |
| PolicyId | string | 是 | 脱敏策略 ID，最大长度 128 |
| Operator | string | 是 | 操作人 |
| WorkspaceId | string | 是 | 工作空间 ID，用于调用 Security.AttachDataMaskPolicy 时传入 |

### 响应参数（UnbindLabelMaskPolicyRsp）

| 字段 | 类型 | 说明 |
|------|------|------|
| Success | bool | 是否成功（仅代表解绑关系删除成功，策略从字段移除为异步） |
| Message | string | 错误信息 |
| AsyncTaskId | string | 异步任务 ID，可用于追踪策略解绑进度 |

### 调用示例

```bash
# 解绑脱敏策略
wedatacli UnbindLabelMaskPolicy '{"LabelId":"1001","PolicyId":"3001","Operator":"zhangsan","WorkspaceId":"123456"}'
```

---

## 8. ListTagsByAsset — 查询资产标签

**服务**：`AssetTagService`
**用途**：查询指定资产已有的标签

### 请求参数（ListTagsByAssetReq）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| WorkspaceId | string | 是（自动注入） | 工作空间 ID；wedatacli 从 `~/.wedata/config.json` 自动注入，命令行示例无需显式传入 |
| QueryItems | AssetQueryItem[] | 是 | 批量查询项列表 |

### AssetQueryItem 结构

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| PropertyType | string | 是 | 资产类型 |
| PropertyId | string | 是 | 资产 ID |

### 响应参数（ListTagsByAssetRsp）

| 字段 | 类型 | 说明 |
|------|------|------|
| Results | AssetTagResult[] | 批量查询结果列表 |
| TotalCount | int64 | 总数 |

### AssetTagResult 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| PropertyType | string | 资产类型 |
| PropertyId | string | 资产 ID |
| Tags | TagInfo[] | 标签列表 |
| Creator | string | 创建人 |
| Modifier | string | 修改者 |
| CreateTime | string | 创建时间 |
| ModifiedTime | string | 修改时间 |
| OwnerAccount | string | 所有者账号 |

### 调用示例

```bash
# 查询表的标签（PropertyType 传 TABLE，PropertyId 传表的 AssetGuid）
wedatacli ListTagsByAsset '{"QueryItems":[{"PropertyType":"TABLE","PropertyId":"550e8400-e29b-41d4-a716-446655440000"}]}'

# 批量查询多个表的标签
wedatacli ListTagsByAsset '{"QueryItems":[{"PropertyType":"TABLE","PropertyId":"550e8400-e29b-41d4-a716-446655440000"},{"PropertyType":"TABLE","PropertyId":"660f9500-f39c-52e5-b827-557766551111"}]}'
```

---

## 9. ListDataMaskStrategies — 查询脱敏策略列表

**服务**：`SecurityService`
**用途**：查询当前工作空间下的脱敏策略列表，用于为未绑定脱敏策略的安全标签推荐合适的策略

### 前置条件

- 调用方需具备该项目的数据安全查看权限

### 错误码

| 错误码 | 说明 |
|--------|------|
| 1120201 | Limit 超出范围（>100）、Offset 为负数 |
| 1120202 | DLC 接口调用失败 |
| 1120204 | 无项目数据安全查看权限 |

### 请求参数（ListDataMaskStrategiesRequest）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| WorkspaceId | string | 是 | 工作空间 ID |
| Offset | int64 | 否 | 分页偏移量，从 0 开始，默认 0 |
| Limit | int64 | 否 | 每页条数，默认 20，最大 100 |
| Filters | DataMaskFilter[] | 否 | 过滤条件列表，支持按策略名称模糊搜索 |

### DataMaskFilter 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| Name | string | 过滤字段名称，支持：`strategy-name`（按策略名称模糊搜索） |
| Values | string[] | 过滤字段值列表，多个值之间为 OR 关系 |

### 响应参数（DescribeDataMaskStrategiesRsp）

| 字段 | 类型 | 说明 |
|------|------|------|
| Strategies | DataMaskStrategyItem[] | 策略列表 |
| TotalCount | string | 满足条件的策略总数（字符串类型，用于分页） |

### DataMaskStrategyItem 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| StrategyId | string | 策略 ID（DLC 侧 UUID） |
| StrategyName | string | 策略名称 |
| StrategyDesc | string | 策略描述 |
| Groups | DataMaskGroup[] | 用户组脱敏规则列表 |
| State | int64 | 策略状态：1=正常，0=已禁用 |
| CreateTime | string | 创建时间，Unix 毫秒时间戳 |
| UpdateTime | string | 最后更新时间，Unix 毫秒时间戳 |
| Uin | string | 创建者主账号 UIN |
| SubAccountUin | string | 创建者子账号 UIN |
| CreatorName | string | 创建人名称 |

### DataMaskGroup 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| GroupId | string | 工作组 ID |
| StrategyType | string | 脱敏方法：MASK_SHOW_FIRST_4（保留前四）、MASK_SHOW_LAST_4（保留后四）、MASK_HASH（哈希）、MASK_DATE_SHOW_YEAR（日期保留年份）、MASK_NULL（置 NULL）、MASK_DEFAULT（默认值） |
| GroupName | string | 用户组名称 |

### 调用示例

```bash
# 查询所有脱敏策略
wedatacli ListDataMaskStrategies '{"WorkspaceId":"123456","Offset":0,"Limit":100}'

# 按策略名称模糊搜索
wedatacli ListDataMaskStrategies '{"WorkspaceId":"123456","Offset":0,"Limit":100,"Filters":[{"Name":"strategy-name","Values":["手机号"]}]}'
```

---

## 10. UpdateAssetTagExclusions — 更新 AI 打标排除记录

**服务**：`AssetTagService`
**用途**：排除或恢复字段的 AI 敏感打标。排除后，后续 AI 扫描时自动跳过该字段；恢复后，AI 重新分析该字段

### 前置条件

- 排除操作时，字段必须已存在 AI 打标记录
- 通过 MySQL 事务保证批量操作的原子性，要么全部成功，要么全部失败

### 错误码

| 错误码 | 说明 |
|--------|------|
| INVALID_PARAMETER | 参数校验失败 |
| EXCLUSION_ALREADY_EXISTS | 排除记录已存在（幂等返回成功） |
| EXCLUSION_NOT_FOUND | 恢复时排除记录不存在 |

### 请求参数（UpdateAssetTagExclusionsRequest）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| WorkspaceId | string | 是（自动注入） | 工作空间 ID；wedatacli 从 `~/.wedata/config.json` 自动注入，命令行示例无需显式传入 |
| ExclusionAction | int64 | 是 | 操作类型：1=排除（创建排除记录），2=恢复（删除排除记录） |
| Items | AssetTagExclusionItem[] | 是 | 排除项列表，单次最多 1000 条 |

### AssetTagExclusionItem 结构

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| PropertyType | string | 是 | 资产类型，如 TABLE、VIEW 等，最大长度 64 |
| PropertyId | string | 是 | 资产 ID（表的 AssetGuid），最大长度 256 |
| ColumnName | string | 是 | 被排除的字段名，最大长度 64 |
| LabelId | string | 是 | 被排除的安全标签 ID |
| LabelName | string | 否 | 标签名称，冗余存储便于展示，最大长度 128 |
| Reason | string | 否 | 排除原因，最大长度 512 |
| CatalogName | string | 否 | 数据目录名称，用于按 Catalog 维度查询，最大长度 64 |
| SchemaName | string | 否 | Schema 名称，最大长度 64 |
| TableName | string | 否 | 表名称，冗余存储便于展示和查询，最大长度 64 |

### 响应参数（UpdateAssetTagExclusionsRsp）

| 字段 | 类型 | 说明 |
|------|------|------|
| Success | bool | 是否成功 |
| AffectedCount | int64 | 影响的记录数量（排除：创建的记录数；恢复：删除的记录数） |
| Message | string | 错误信息（失败时返回） |

### 调用示例

```bash
# 排除字段（ExclusionAction=1）
wedatacli UpdateAssetTagExclusions '{"ExclusionAction":1,"Items":[{"PropertyType":"TABLE","PropertyId":"550e8400-e29b-41d4-a716-446655440000","ColumnName":"phone","LabelId":"445","LabelName":"class.phone_number","Reason":"该字段为内部测试号码","CatalogName":"my_catalog","SchemaName":"default","TableName":"customer"}]}'

# 恢复字段（ExclusionAction=2）
wedatacli UpdateAssetTagExclusions '{"ExclusionAction":2,"Items":[{"PropertyType":"TABLE","PropertyId":"550e8400-e29b-41d4-a716-446655440000","ColumnName":"phone","LabelId":"445","LabelName":"class.phone_number","CatalogName":"my_catalog","SchemaName":"default","TableName":"customer"}]}'

# 批量排除多个字段
wedatacli UpdateAssetTagExclusions '{"ExclusionAction":1,"Items":[{"PropertyType":"TABLE","PropertyId":"550e8400-e29b-41d4-a716-446655440000","ColumnName":"phone","LabelId":"445","LabelName":"class.phone_number","Reason":"测试数据","CatalogName":"my_catalog","SchemaName":"default","TableName":"customer"},{"PropertyType":"TABLE","PropertyId":"550e8400-e29b-41d4-a716-446655440000","ColumnName":"address","LabelId":"447","LabelName":"class.location","Reason":"非真实地址","CatalogName":"my_catalog","SchemaName":"default","TableName":"customer"}]}'
```

---

## 11. ListAssetTagExclusions — 查询 AI 打标排除记录

**服务**：`AssetTagService`
**用途**：查询已排除的字段记录，支持按 Catalog、Schema、表名、标签等维度过滤。AI 扫描前调用此接口获取排除列表，跳过已排除的字段

### 请求参数（ListAssetTagExclusionsRequest）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| WorkspaceId | string | 是（自动注入） | 工作空间 ID；wedatacli 从 `~/.wedata/config.json` 自动注入，命令行示例无需显式传入 |
| PropertyId | string | 否 | 资产 ID 过滤，精确匹配，最大长度 256 |
| CatalogName | string | 否 | 数据目录名称过滤，最大长度 64 |
| SchemaName | string | 否 | Schema 名称过滤，最大长度 64 |
| TableName | string | 否 | 表名称过滤，最大长度 64 |
| LabelId | string | 否 | 标签 ID 过滤 |
| PageNumber | int64 | 是 | 页码，从 1 开始 |
| PageSize | int64 | 是 | 每页数量，范围 1-200 |

### 响应参数（ListAssetTagExclusionsRsp）

| 字段 | 类型                        | 说明 |
|------|---------------------------|------|
| Records | AssetTagExclusionRecord[] | 排除记录列表 |
| TotalCount | string                    | 总记录数 |

### AssetTagExclusionRecord 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| Id | string | 排除记录主键 ID |
| PropertyType | string | 资产类型 |
| PropertyId | string | 资产 ID |
| ColumnName | string | 字段名称 |
| LabelId | string | 标签 ID |
| LabelName | string | 标签名称 |
| Reason | string | 排除原因 |
| CatalogName | string | 数据目录名称 |
| SchemaName | string | Schema 名称 |
| TableName | string | 表名称 |
| Operator | string | 操作人 |
| CreateTime | string | 创建时间（毫秒时间戳） |
| UpdateTime | string | 更新时间（毫秒时间戳） |

### 调用示例

```bash
# 查询指定 Catalog 下的排除记录
wedatacli ListAssetTagExclusions '{"CatalogName":"my_catalog","PageNumber":1,"PageSize":50}'

# 查询指定表的排除记录
wedatacli ListAssetTagExclusions '{"PropertyId":"550e8400-e29b-41d4-a716-446655440000","PageNumber":1,"PageSize":50}'

# 查询指定标签的排除记录
wedatacli ListAssetTagExclusions '{"LabelId":"445","PageNumber":1,"PageSize":50}'

# 组合过滤
wedatacli ListAssetTagExclusions '{"CatalogName":"my_catalog","SchemaName":"default","TableName":"customer","PageNumber":1,"PageSize":50}'
```

---

## 12. ListDataMaskStrategyTypes — 查询脱敏方法枚举列表

**服务**：`SecurityService`
**用途**：查询所有可用的脱敏方法列表（含名称、枚举值、脱敏前后示例），用于创建/编辑脱敏策略时选择脱敏方法

### 前置条件

- 无需鉴权，任何已登录用户均可调用
- 无需传入任何参数

### 请求参数

无参数。

### 响应参数（DescribeDataMaskStrategyTypesRsp）

| 字段 | 类型 | 说明 |
|------|------|------|
| StrategyTypes | DataMaskStrategyTypeItem[] | 脱敏方法枚举列表，固定返回 6 条 |

### DataMaskStrategyTypeItem 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| StrategyType | string | 策略类型枚举标识，如 `MASK_SHOW_FIRST_4` |
| DisplayName | string | 展示名称（中文），如 "保留前四个字符" |
| ExampleBefore | string | 脱敏前示例，如 "18888888888" |
| ExampleAfter | string | 脱敏后示例，如 "1888xxxxxxx" |

### 调用示例

```bash
# 查询所有脱敏方法
wedatacli ListDataMaskStrategyTypes '{}'
```

---

## 13. CreateDataMaskStrategy — 创建脱敏策略

**服务**：`SecurityService`
**用途**：创建数据脱敏策略，为一个或多个用户组配置脱敏方法

### 前置条件

- 调用方需具备该项目的数据安全管理权限
- StrategyName 在同一项目下唯一

### 错误码

| 错误码 | 说明 |
|--------|------|
| 1120201 | 参数校验失败（StrategyName 为空/超长 >128 字符、Groups 为空、StrategyType 枚举值非法） |
| 1120202 | DLC 接口调用失败 |
| 1120204 | 无项目数据安全管理权限 |

### 请求参数（CreateDataMaskStrategyRequest）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| WorkspaceId | string | 是 | 工作空间 ID |
| Strategy | DataMaskStrategyInfo | 是 | 策略信息 |

### DataMaskStrategyInfo 结构

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| StrategyName | string | 是 | 策略名称，长度 1~128 字符，同一项目下唯一 |
| StrategyType | string | 是 | 策略类型（脱敏方法），合法值见 StrategyType 枚举 |
| StrategyDesc | string | 否 | 策略描述，最大 512 字符 |
| Groups | DataMaskGroup[] | 是 | 用户组脱敏规则列表，至少包含一条规则 |

### DataMaskGroup 结构

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| GroupId | string | 是 | 工作组 ID，对应 WeData 用户组 ID |
| StrategyType | string | 是 | 脱敏方法，合法值见 StrategyType 枚举 |
| GroupName | string | 否 | 工作组名称 |

### 响应参数（CreateDataMaskStrategyRsp）

| 字段 | 类型 | 说明 |
|------|------|------|
| StrategyId | string | 新创建的策略 ID（DLC 侧 UUID） |

### 调用示例

```bash
# 创建脱敏策略
wedatacli CreateDataMaskStrategy '{"WorkspaceId":"123456","Strategy":{"StrategyName":"手机号脱敏","StrategyType":"MASK_SHOW_LAST_4","StrategyDesc":"保留后四位","Groups":[{"GroupId":"17738042827013749","StrategyType":"MASK_SHOW_LAST_4","GroupName":"数据分析组"}]}}'
```

---

## 14. DeleteDataMaskStrategy — 删除脱敏策略

**服务**：`SecurityService`
**用途**：删除数据脱敏策略，支持批量删除

### 前置条件

- 调用方需具备该项目的数据安全管理权限
- 删除前建议先解绑所有已绑定该策略的字段

### 错误码

| 错误码 | 说明 |
|--------|------|
| 1120201 | StrategyIds 为空 |
| 1120202 | DLC 接口调用失败 |
| 1120203 | 策略 ID 不存在 |
| 1120204 | 无项目数据安全管理权限 |

### 请求参数（DeleteDataMaskStrategyRequest）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| WorkspaceId | string | 是 | 工作空间 ID |
| StrategyIds | string[] | 是 | 待删除的策略 ID 列表，至少 1 个，最多 20 个 |

### 响应参数（DeleteDataMaskStrategyRsp）

| 字段 | 类型 | 说明 |
|------|------|------|
| Success | bool | 是否删除成功 |

### 调用示例

```bash
# 删除单个策略
wedatacli DeleteDataMaskStrategy '{"WorkspaceId":"123456","StrategyIds":["71a88499-266f-4b24-9944-2d80078ec0a6"]}'

# 批量删除多个策略
wedatacli DeleteDataMaskStrategy '{"WorkspaceId":"123456","StrategyIds":["71a88499-266f-4b24-9944-2d80078ec0a6","82b99500-377g-53f5-a055-3e91189fd1b7"]}'
```

---

## 15. UpdateDataMaskStrategy — 更新脱敏策略

**服务**：`SecurityService`
**用途**：更新数据脱敏策略的名称、描述或用户组脱敏规则

### 前置条件

- 调用方需具备该项目的数据安全管理权限
- StrategyId 必须是已存在的策略

### 错误码

| 错误码 | 说明 |
|--------|------|
| 1120201 | 参数校验失败（StrategyId 为空、StrategyName 超长 >128 字符、StrategyType 枚举值非法） |
| 1120202 | DLC 接口调用失败 |
| 1120203 | 策略 ID 不存在 |
| 1120204 | 无项目数据安全管理权限 |

### 请求参数（UpdateDataMaskStrategyRequest）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| WorkspaceId | string | 是 | 工作空间 ID |
| Strategy | DataMaskStrategyUpdateInfo | 是 | 策略更新信息 |

### DataMaskStrategyUpdateInfo 结构

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| StrategyId | string | 是 | 策略 ID，由 CreateDataMaskStrategy 返回 |
| StrategyName | string | 否 | 策略名称，不填则不更新，长度 1~128 字符 |
| StrategyDesc | string | 否 | 策略描述，不填则不更新，最大 512 字符 |
| StrategyType | string | 否 | 策略类型，不填则不更新，合法值见 StrategyType 枚举 |
| Groups | DataMaskGroup[] | 否 | 用户组脱敏规则列表，不填则不更新。填写时会全量替换原有规则列表 |

### 响应参数（UpdateDataMaskStrategyRsp）

| 字段 | 类型 | 说明 |
|------|------|------|
| Success | bool | 是否更新成功 |

### 调用示例

```bash
# 更新策略名称和描述
wedatacli UpdateDataMaskStrategy '{"WorkspaceId":"123456","Strategy":{"StrategyId":"71a88499-266f-4b24-9944-2d80078ec0a6","StrategyName":"手机号脱敏-v2","StrategyDesc":"更新后的描述"}}'

# 更新用户组脱敏规则（全量替换）
wedatacli UpdateDataMaskStrategy '{"WorkspaceId":"123456","Strategy":{"StrategyId":"71a88499-266f-4b24-9944-2d80078ec0a6","Groups":[{"GroupId":"17738042827013749","StrategyType":"MASK_HASH","GroupName":"数据分析组"}]}}'
```

---

## 16. ListConsoleGroups — 查询用户组列表

**服务**：`WorkspaceService`
**用途**：查询控制台用户组列表，用于创建脱敏策略时选择需要配置脱敏规则的用户组

### 前置条件

- 已登录用户均可调用
- 此接口为控制台级别接口（console_region），不需要 WorkspaceId

### 请求参数（ListConsoleGroupsRequest）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| PageRequest | PageReq | 否 | 分页参数，含 PageNumber（从1开始）和 PageSize |
| GroupIds | string[] | 否 | 按用户组 ID 精确过滤 |
| Keywords | string | 否 | 用户组名称模糊匹配 |
| SortInfo | SortInfo | 否 | 排序字段 |

### 响应参数（ListConsoleGroupsRsp）

| 字段 | 类型 | 说明 |
|------|------|------|
| Items | UserGroupInfo[] | 用户组信息列表 |
| PageResponse | PageRsp | 分页信息 |

### UserGroupInfo 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| GroupId | string | 用户组 ID |
| GroupName | string | 用户组名称 |
| GroupNickname | string | 用户组昵称 |
| Description | string | 用户组描述 |
| CreateTime | string | 创建时间戳 |
| UpdateTime | string | 更新时间戳 |
| UserCount | uint64 | 用户组内用户总量 |

### 调用示例

```bash
# 查询所有用户组（分页）
wedatacli ListConsoleGroups '{"PageRequest":{"PageNumber":1,"PageSize":50}}'

# 按名称模糊搜索
wedatacli ListConsoleGroups '{"PageRequest":{"PageNumber":1,"PageSize":50},"Keywords":"数据分析"}'

# 按用户组 ID 精确查询
wedatacli ListConsoleGroups '{"GroupIds":["17738042827013749"]}'
```

---

## 17. ListMaskPolicyDispatchLogs — 查询脱敏策略下发流水

**服务**：`AssetTagService`
**用途**：查询脱敏策略下发到字段的异步执行结果（成功/失败 + 失败原因 + 时间）。标签关联字段后，自动下发脱敏策略到字段是【异步执行】（详见 `BindLabelMaskPolicy` 注释）；本接口用于回查每个字段的下发结果，供「标签详情页」展示下发状态、运维排查「用户给字段打标后策略未生效」问题。

### 使用场景

- **打标后回查**：`BatchVoteAssetTag` 完成后，对绑定了脱敏策略的脱敏标签，按 `LabelId + 字段四元组` 查询最近一次下发记录
- **单字段排障**：用户反馈「某字段打了标但脱敏未生效」，按 `LabelId + 完整四元组（CatalogName/SchemaName/TableName/FieldName）` 查询最近一次记录
- **全标签视图**：仅传 `LabelId`，返回该标签关联字段的全部下发流水，用于运维监控

### 前置条件

- `LabelId` 必填且 > 0（走 `idx_label_id` 索引）
- 通常用于已绑定脱敏策略的脱敏标签（`LabelType=4`）

### 错误码

| 错误码 | 说明 |
|--------|------|
| INVALID_PARAMETER | LabelId 为空，或 Limit 超限（>500） |

### 请求参数（ListMaskPolicyDispatchLogsReq）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| LabelId | string | 是 | 标签 ID（>0） |
| WorkspaceId | string | 是（自动注入） | 工作空间 ID；wedatacli 从 `~/.wedata/config.json` 自动注入，命令行示例无需显式传入。空字符串视为不过滤 |
| CatalogName | string | 否 | Catalog 名称，空字符串视为不过滤 |
| SchemaName | string | 否 | Schema（Database）名称，空字符串视为不过滤 |
| TableName | string | 否 | 表名称，空字符串视为不过滤 |
| FieldName | string | 否 | 字段名称，空字符串视为不过滤 |
| Limit | int64 | 否 | 单次返回条数，默认 100，最大 500（防止全表扫描） |

### 响应参数（ListMaskPolicyDispatchLogsRsp）

| 字段 | 类型 | 说明 |
|------|------|------|
| Logs | MaskPolicyDispatchLogItem[] | 下发流水明细列表（已按 `CreateTime DESC` 排序） |
| TotalCount | int64 | 本次返回总条数 |
| SuccessCount | int64 | 本次返回中下发成功的条数 |
| FailedCount | int64 | 本次返回中下发失败的条数 |

### MaskPolicyDispatchLogItem 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| Id | string | 流水主键 ID |
| AsyncTaskId | string | 异步任务 ID（UUID 不含连字符），用于关联同一次绑定/解绑触发的所有批次 |
| BatchIndex | int64 | 批次序号，同一 AsyncTaskId 内从 1 开始 |
| LabelId | string | 标签 ID |
| PolicyId | string | 脱敏策略 ID（解绑时为 `"-1"`） |
| WorkspaceId | string | 工作空间 ID |
| CatalogName | string | Catalog 名称 |
| SchemaName | string | Schema 名称 |
| TableName | string | 表名称 |
| FieldName | string | 字段名称 |
| FieldType | string | 字段类型（如 string / int / bigint） |
| DispatchType | int64 | 操作类型：1=绑定策略（打标触发），2=解绑策略（清除/排除触发） |
| DispatchStatus | int64 | 下发结果：1=成功，2=失败 |
| FailReason | string | 失败原因（成功时为空），如 DLC 鉴权失败、字段不存在等 |
| CreateTime | string | 创建时间，13 位时间戳 |
| ModifiedTime | string | 修改时间，13 位时间戳 |

### 调用示例

```bash
# 示例 1：单字段精确查询（推荐：传完整四元组以缩小结果集）
wedatacli ListMaskPolicyDispatchLogs '{"LabelId":"1001","CatalogName":"my_catalog","SchemaName":"my_schema","TableName":"user_info","FieldName":"phone_number","Limit":10}'

# 示例 2：全标签视图（返回该标签下全部字段的下发流水）
wedatacli ListMaskPolicyDispatchLogs '{"LabelId":"1001","Limit":500}'

# 示例 3：按表维度查询（某张表上某标签的所有字段下发情况）
wedatacli ListMaskPolicyDispatchLogs '{"LabelId":"1001","CatalogName":"my_catalog","SchemaName":"my_schema","TableName":"user_info"}'
```

### 使用建议

- **异步等待**：策略下发通常需要数秒到数十秒；若打标后立即调用查询不到记录，建议提示用户稍后重试，不要立刻断言下发失败
- **结果排序**：返回按 `CreateTime DESC` 排序，列表中第一条即为最近一次下发记录
- **结果压缩**：建议传完整字段四元组以缩小结果集；不传四元组+大 `Limit` 在大标签场景下数据量较大

---

## 枚举值参考

### LabelType（标签类型）

| 值 | 名称 | 说明 |
|----|------|------|
| 0 | LABEL_TYPE_UNKNOWN | 未知类型 |
| 1 | GOVERNANCE_LABEL | 治理标签（标签管理页手动创建） |
| 2 | CUSTOM_LABEL | 自定义标签（打标时自动创建） |
| 3 | PROPERTY_LABEL | 属性标签（Key-Value 键值对，允许 labelValueId 为 null） |
| 4 | DESENSITIZATION_LABEL | 脱敏标签（与脱敏策略绑定，支持字段级脱敏策略自动下发；标签值非必填） |

### LabelControlStatus（标签管控状态）

| 值 | 名称 | 说明 |
|----|------|------|
| 0 | UNKNOWN | 未知 |
| 1 | UNCONTROLLED | 默认未管控 |
| 2 | SYSTEM_CONTROLLED | 系统定义已管控 |
| 3 | CUSTOMER_CONTROLLED | 用户自定义已管控 |

### PropertyType（资产类型）

| 值 | 说明 |
|----|------|
| TABLE | 数据表 |
| VIEW | 视图 |
| FIELD | 字段 |

### ExclusionAction（排除操作类型）

| 值 | 名称 | 说明 |
|----|------|------|
| 1 | EXCLUDE | 排除，创建排除记录，AI 下次分析时跳过这些字段 |
| 2 | RESTORE | 恢复，删除排除记录，AI 下次分析时重新分析这些字段 |

### StrategyType（脱敏方法）

| 值 | 说明 |
|----|------|
| MASK_SHOW_FIRST_4 | 保留前四个字符 |
| MASK_SHOW_LAST_4 | 保留后四个字符 |
| MASK_HASH | 哈希脱敏 |
| MASK_DATE_SHOW_YEAR | 日期脱敏保留年份 |
| MASK_NULL | 置为 NULL |
| MASK_DEFAULT | 默认值脱敏 |