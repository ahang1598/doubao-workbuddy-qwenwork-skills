---
name: data-classification
description: WeData 敏感数据分类与脱敏标签打标能力，覆盖敏感字段扫描、AI智能打标、脱敏标签管理、脱敏策略全生命周期管理。当用户涉及敏感数据识别、分类分级、脱敏相关操作时触发。
layer: L3
lintCheckVersion: "1.0"
tags: [data-development]
user-invocable: false
requires:
  - scenarios/common/skills/artifact-uploader
  - scenarios/data-development/skills/asset-discovery
hidden-description: |
  WeData 敏感数据分类与脱敏标签打标能力。当用户提及"敏感字段 / 敏感数据分类 / 数据分类 /
  脱敏标签 / 安全标签 / 脱敏策略 / 敏感数据识别 / 字段打标 / 安全分类 /
  数据脱敏 / 脱敏绑定 / 安全扫描 / 敏感扫描 / 字段安全 / 隐私字段 / PII /
  个人信息 / 手机号脱敏 / 身份证脱敏 / 安全合规 / 数据分级分类"等关键词时触发。覆盖：
  (1) 敏感字段扫描：对指定 Catalog 下的表字段进行 AI 敏感数据识别；
  (2) 脱敏标签打标：根据识别结果为字段打上脱敏标签（系统自动关联脱敏策略）；
  (3) 脱敏标签与脱敏策略管理：查询、绑定、解绑脱敏标签的脱敏策略关联关系；
  (4) 脱敏策略全生命周期管理：查询脱敏方法、创建/更新/删除脱敏策略；
  (5) AI 打标排除管理：对不希望被 AI 打上敏感标签的字段进行排除/恢复管理。
  即使用户没有明确说"脱敏标签"，只要涉及表字段的敏感数据识别、分类分级、脱敏相关操作，
  或涉及脱敏策略的创建、修改、删除、查询，都应使用此 skill。
  产生敏感字段扫描清单、脱敏打标变更记录、脱敏策略变更摘要等产物时，
  通过 Skill("artifact-uploader") 上传到 Studio 的 databuddy/governance/ 目录。
---

# WeData 敏感数据分类与脱敏标签打标

## Skill 概述

本 skill 提供敏感数据分类、字段自动识别与脱敏标签打标能力。WeData 中数据表采用三级结构 `Catalog / Schema / Table`，用户可以对一个或多个 Catalog 下的表字段进行敏感数据扫描，AI 根据字段名称、类型、描述以及（如有）字段采样值自动识别敏感字段并推荐脱敏标签，经用户确认后完成打标。

> ℹ️ **关于字段采样数据：** `SearchAsset` 返回的 `FieldInfo.SampleValues` 为字段实际数据采样值列表，**可能存在也可能不存在**。当 `SampleValues` 非空时，必须将其纳入识别判断作为元数据的有力佐证；当为空时，仅基于元数据（表名、表描述、字段名、字段类型、字段描述）和脱敏标签信息进行识别。**不要把「是否使用采样数据」作为选项询问用户**——有就用，没有就只用元数据，识别策略由 skill 自动决定。

WeData 的脱敏标签（LabelType=4）可以绑定脱敏策略，当字段被打上脱敏标签后，系统内部会自动对该字段下发已绑定的脱敏策略。用户也可以单独管理脱敏标签与脱敏策略的绑定关系。

### 核心能力

| 能力 | 说明 |
|------|------|
| 敏感字段扫描 | 对指定 Catalog 下的表进行字段级敏感数据识别 |
| AI 智能打标 | 根据字段元数据（名称、类型、描述）+ 字段采样值（如有）+ 脱敏标签列表，自动推荐匹配的脱敏标签 |
| 脱敏标签打标 | 调用接口为字段打上脱敏标签，系统自动关联脱敏策略 |
| 脱敏策略管理 | 查询、绑定、解绑脱敏标签与脱敏策略的关联关系；创建、更新、删除脱敏策略 |
| AI 打标排除管理 | 对不希望被 AI 打上敏感标签的字段进行排除，后续 AI 扫描时自动跳过；也可恢复已排除的字段 |

## 不适用场景

- 用户询问**治理标签 / 自定义标签 / 属性标签**（LabelType=1 或 2 或 3）的管理 → 这些不是脱敏标签
- 用户询问**表 / 字段 / 血缘**等通用资产检索（不涉及脱敏标签） → 使用 `knowledge` / `semantic-meta-search`
- 用户询问**数据质量规则**的创建和执行 → 使用 `data-quality`
- 用户询问**数据开发任务**的管理 → 使用 `data-engineer`

## 必需输入

- **Catalog 范围**：敏感扫描时需要用户指定要扫描的 Catalog 名称（一个或多个）
- **写操作确认**：打标和脱敏策略绑定属于写操作，必须经用户明确确认后执行

---

## 实体模型

```
Catalog（数据目录）
  └── Schema（数据库）
        └── Table（数据表）
              └── Field（字段）
                    ├── Name: 字段名称
                    ├── Type: 字段类型（string, int, ...）
                    ├── Comment: 字段描述
                    ├── SampleValues: 字段采样值列表（可选，可能为空）
                    └── Tags: 已有标签列表

脱敏标签（BizLabel, LabelType=4）
  ├── Name: 标签名称（如"手机号"、"身份证号"、"银行卡号"）
  ├── Description: 标签描述（含用途说明、合规要求等）
  ├── SecurityTypes: 安全类型列表（如 PII、GDPR、HIPAA 等）
  ├── ⚠️ 脱敏标签的标签值非必填（Values 可为空），与治理标签/自定义标签不同
  └── 脱敏策略绑定（LabelMaskPolicyRelInfo）
        ├── PolicyId: 脱敏策略 ID
        └── PolicyName: 脱敏策略名称
```

---

## 意图路由（第一步 MUST）

收到用户问题后，第一步必须判定意图属于下列哪类，然后进入对应工作流。

| 意图类别 | 触发词 | 工作流 |
|----------|--------|--------|
| **A. 敏感字段扫描与打标** | "扫描 / 识别 / 敏感字段 / 安全扫描 / 字段打标 / PII / 分类分级" | 工作流 A：扫描与打标 |
| **B. 脱敏标签查询** | "脱敏标签 / 安全标签 / 标签列表 / 有哪些脱敏标签 / 查看标签" | 工作流 B：标签查询 |
| **C. 脱敏策略管理** | "脱敏策略 / 绑定策略 / 解绑 / 策略关联 / 脱敏绑定 / 创建策略 / 新建策略 / 删除策略 / 修改策略 / 更新策略 / 脱敏方法 / 用户组" | 工作流 C：脱敏策略管理 |
| **D. 已有标签查询** | "字段标签 / 表的标签 / 哪些字段打了标" | 工作流 D：资产标签查询 |
| **E. AI 打标排除管理** | "排除 / 不要打标 / 忽略字段 / 恢复排除 / 排除列表 / 跳过字段" | 工作流 E：AI 打标排除管理 |

> ⚠️ 若同一句话含多个类别触发词（如"扫描敏感字段并绑定脱敏策略"），按顺序拆分执行，先完成 A 再处理 C。

---

## 工作流 A：敏感字段扫描与打标（核心流程）

这是本 skill 的核心场景，完整流程分为 5 个阶段：

### 阶段 1：确定扫描范围

> ⚠️ **强制要求：必须先与用户确认扫描的 Catalog 范围后才能开始扫描，绝不能在用户未明确指定的情况下自动扫描所有 Catalog。** 即使用户说"帮我扫描敏感字段"但未指定 Catalog，也必须先询问用户要扫描哪些 Catalog。

1. 用户指定要扫描的 Catalog 名称（一个或多个）→ 直接进入阶段 2
2. 如果用户未指定或不确定自己有哪些 Catalog，通过 `Skill("asset-discovery")` 查询可用 Catalog 列表，**展示给用户选择后再开始扫描**

> 将查询到的 Catalog 列表展示给用户，**等待用户选择要扫描的范围后再继续**，不要自动选择全部。

### 阶段 2：获取表和字段信息

本阶段分两步：先通过 `Skill("asset-discovery")` 检索目标范围内的表列表，再通过 `SearchAsset` 获取字段详情（采样值、已有标签等）。

#### 步骤 2.1：检索表列表（通过 asset-discovery）

> ⚠️ **所有平台资产的检索/浏览操作统一走 `Skill("asset-discovery")`**。包括但不限于：查 Catalog 列表、查 Schema 列表、获取表列表、搜索表名等。不要直接用 `SearchAsset` 做全量翻页扫描。
>
> 🔴 **直连分析型 Catalog 标记**：在获取表列表时，同时记录每个 Catalog 是否为直连分析型（`connection_id` 非空）。此信息将在阶段 4 输出格式和阶段 5 中用于能力降级判断。直连分析型 Catalog 的表**支持敏感识别和打标**，但**不支持脱敏策略下发**。

#### 步骤 2.2：获取字段及标签信息（SearchAsset）

拿到表名列表后，调用 `SearchAsset` 获取每个表的**字段信息**（名称、类型、描述、采样值）和**已有标签信息**（FieldTags）。这是 `SearchAsset` 在本 skill 中的唯一用途——提供字段级元数据，而非用于检索/浏览资产。

> ⚠️ **必须循环分页**：每次最多返回 50 条，必须检查 `NextPageToken` 直到为空。
> 详细参数见 [api_reference.md](reference/api_reference.md#searchasset)。

**关键字段提取**：`FullName`（表路径）、`AssetGuid`（**打标时的 PropertyId**）、`AssetName`、`Comment`、`FieldInfo`（字段名/类型/描述/**采样值 SampleValues**）、`FieldTags`（已有标签）。

> ℹ️ `FieldInfo.SampleValues` 为该字段的实际数据采样列表（如有），将作为阶段 4 敏感识别的辅助输入。该字段可能为空（采样未开启、数据为空、无访问权限等场景），为空时跳过采样维度判断即可。
> ℹ️ 从 `SearchAsset` 结果中按 `FullName`（catalog.schema.table）过滤出步骤 2.1 获取的目标表，忽略不在范围内的结果。

### 阶段 3：获取脱敏标签列表

调用 `ListLabels`（Types=[4]，**必传 `WorkspaceId` + `Shared=true`**，PageSize=100）。响应 `BizLabel.MaskPolicy` 已直接回填关联策略，无需 N+1 调 `ListMaskPoliciesByLabel`。

> 💡 可选过滤（仅 Type=4 有效）：`SecurityTypes`、`PolicyBindStatus`（1=已关联/2=未关联）、`SourceTypes`（[2]=仅自定义）

```bash
# 首页（根据 TotalCount 决定是否需要继续翻页）；响应 BizLabel.MaskPolicy 已直接给出关联策略
wedatacli ListLabels '{"WorkspaceId":"<ws_id>","Shared":true,"Types":[4],"Page":{"PageNumber":1,"PageSize":100}}'

# 例：只想要"已绑定策略 + 命中 PII/GDPR"的脱敏标签
wedatacli ListLabels '{"WorkspaceId":"<ws_id>","Shared":true,"Types":[4],"SecurityTypes":["PII","GDPR"],"PolicyBindStatus":1,"Page":{"PageNumber":1,"PageSize":100}}'
```

> ⛔ **不要再走旧 N+1 写法**：`ListLabels` 拿到 N 个脱敏标签后逐个调 `ListMaskPoliciesByLabel` 的写法已**过时**，请直接读 `BizLabel.MaskPolicy`。仅当需要查看完整历史关联记录（含已 unbind 的）时才走 `ListMaskPoliciesByLabel`。

### 阶段 4：AI 敏感数据识别

基于以下信息进行智能识别：

**输入（以下数据源）**：
- 表元数据：表全名（FullName，即 catalog.schema.table）、表名称（AssetName）、表描述（Comment）
- 字段元数据：名称（Name）、类型（Type）、描述（Comment）
- **字段采样值（如有）**：`FieldInfo.SampleValues`，字段的实际数据采样列表，可能为空
- 脱敏标签列表：名称、描述、安全类型（SecurityTypes）、已绑定的脱敏策略（如有）

> ⚠️ 脱敏标签的标签值非必填，识别时只需匹配到脱敏标签本身即可，不需要匹配标签值。
> ℹ️ **采样数据是可选辅助输入，不是必需输入。** 当 `SampleValues` 非空时把它作为有力佐证（用真实值格式特征佐证或推翻元数据匹配结论）；为空时仅基于元数据识别即可。**不要把「是否使用采样数据」作为可选项让用户选择**——有就用，没有就基于元数据识别，由 skill 自动决定。

**核心原则：不漏报，减少误报。** 漏报意味着敏感数据未被保护，是安全风险；误报可通过排除机制（工作流 E）修正。当存在歧义时，倾向于纳入识别结果并交给用户确认，而非直接跳过。

**识别采用两阶段框架：先降噪排除 → 再按标签匹配。**

#### 第一阶段：降噪排除（仅排除明确不可能是敏感数据的字段，宁可放过不可错杀）

排除纯标识符（`_id`/`_uid`/`_uuid`）、枚举/状态（`_type`/`_status`）、度量/统计（`count`/`amount`）、时间（`_at`/`_ts`）、布尔（`is_`/`has_`）、技术配置（`version`/`config`）等明确非敏感字段。含 `name`/`phone`/`email`/`address`/`card` 等敏感关键词的字段不排除。

> 详细排除规则表见 [recognition_rules.md](reference/recognition_rules.md#第一阶段降噪排除规则)。

#### 第二阶段：按标签匹配（基于 ListLabels 实际返回的标签，动态匹配）

对每个通过第一阶段的字段，遍历 ListLabels 返回的所有脱敏标签，利用标签 `Name`（提取 `.` 后的语义关键词）和 `Description` 进行语义匹配。需注意区分系统对象名（`file_name`/`table_name`）与自然人姓名、技术地址（`mac_address`）与地理位置等易误报场景。

> 详细误报场景处理规则见 [recognition_rules.md](reference/recognition_rules.md#第二阶段误报场景处理)。

#### 采样值交叉验证（当 `SampleValues` 非空时启用）

- 元数据匹配 + 采样值符合 → **强匹配**，识别依据标注「字段名+采样值」
- 元数据匹配 + 采样值明显不符 → **推翻匹配**，作为误报排除
- 元数据匹配 + 采样值缺失 → **维持元数据匹配结论**
- 元数据未匹配 + 采样值强烈指向某敏感类型 → 纳入候选，标注置信度较低

> 详细采样值校验规则见 [recognition_rules.md](reference/recognition_rules.md#采样值校验规则)。

> ⚠️ **匹配优先级**：字段 Comment > 字段名关键词 > **采样值特征** > 表名上下文。描述中明确提及敏感含义时，即使字段名不含关键词也应纳入；采样值用于交叉验证以减少误报。已有相同标签的字段跳过。
> ⚠️ **排除字段跳过**：识别前先调用 `ListAssetTagExclusions` 查询已排除字段，已排除字段自动跳过。

**输出格式**（展示给用户确认）：

结果按 `Catalog / Schema / Table` 分组展示。每个字段列出：字段名、类型、描述、推荐脱敏标签、安全类型、识别依据、采样佐证（脱敏后，如 `138****1234`）、已绑定脱敏策略状态（✅/❌）。末尾汇总扫描表数、识别字段数、未绑定策略的标签数。

> ⚠️ 严禁明文展示采样真实值，必须先脱敏处理。标记 ❌ 的脱敏标签需提醒用户打标后不会自动脱敏。
>
> 🔴 **直连分析型 Catalog 展示调整**：若目标表属于外部数据目录（直连分析型），"已绑定脱敏策略状态"列展示 `N/A（外部表不支持下发）`，而非 ✅/❌；汇总信息中不统计"未绑定策略的标签数"（因为绑定了也不生效）。

### 阶段 5：执行打标与脱敏策略处理

**用户确认后**，执行以下操作：

#### 5.1 批量打标

> ⚠️ FieldTags 按 `FieldName` 增量覆盖：传入的 FieldName 会**完全替换**该字段的已有标签，未传入的 FieldName 保持不变。详见 [api_reference.md](reference/api_reference.md#4-batchvoteassettag--批量资产打标)。

**打标决策**：
1. 只动 FieldTags，**不传 Tags**（避免误改资产级标签）
2. 仅包含本次要打标的字段；未涉及字段不传
3. 每个字段需合并已有标签 + 新增脱敏标签后一并传入

```bash
wedatacli BatchVoteAssetTag '{"Votes":[{"PropertyType":"TABLE","PropertyId":"<table_asset_guid>","Creator":"<user>","FieldTags":[{"LabelId":"<label_id>","LabelName":"<name>","LabelType":4,"FieldName":"<field>","FieldType":"<type>"}]}]}'
```

#### 5.2 处理未绑定脱敏策略的脱敏标签

> 🔴 **直连分析型 Catalog 能力降级**：若目标表属于外部数据目录（直连分析型 Linked Catalog，`connection_id` 非空），**跳过本阶段**，改为输出提示：
> > "已完成敏感字段打标。当前表属于外部数据目录（直连分析型），暂不支持动态脱敏策略下发，标签仅作为分类标记使用。"
>
> 仅对内部 Catalog 的表执行以下策略绑定建议流程。

打标完成后，对标记"❌ 未绑定"的脱敏标签：调用 `ListDataMaskStrategies` 匹配推荐策略，展示给用户选择绑定（→ 工作流 C.2）、创建策略（→ 工作流 C.5）或跳过。

#### 5.3 查询并汇报脱敏策略下发结果

> 🔴 **直连分析型 Catalog 能力降级**：若目标表属于外部数据目录（直连分析型），**整体跳过本阶段**（外部表不支持脱敏策略下发，无下发结果可查）。

仅当打标涉及已绑定策略的脱敏标签时执行。调用 `ListMaskPolicyDispatchLogs`（`LabelId` 必填 + 四元组缩小结果集）。

**状态判定**：`DispatchStatus=1`→✅ 成功；`=2`→❌ 失败（读 `FailReason`）；查不到→⏳ 处理中（提示 30 秒后重试）。

---

## 工作流 B：脱敏标签查询（只读）

调用 `ListLabels`（Types=[4]，**必传 `WorkspaceId` + `Shared=true`**，PageSize=100）查询脱敏标签。响应 `BizLabel.MaskPolicy` 已直接回填关联策略，⛔ 不要走旧 N+1 写法。

```bash
wedatacli ListLabels '{"WorkspaceId":"<ws_id>","Shared":true,"Types":[4],"Page":{"PageNumber":1,"PageSize":100}}'
```

整合输出：标签名称、描述、安全类型、已绑定脱敏策略。

---

## 工作流 C：脱敏策略管理（含确认闭环）

工作流 C 覆盖脱敏策略的完整生命周期：查询绑定关系、绑定/解绑、查询策略列表、创建/更新/删除策略。

### C.1 查询脱敏策略绑定（只读）

**优先**：直接读 `ListLabels` 响应的 `BizLabel.MaskPolicy` 字段。仅当需要完整历史关联记录时才走 `ListMaskPoliciesByLabel`。

> ℹ️ 策略视角反查（PolicyId → labels）无云 API 暴露，可在 `ListLabels(Types=[4])` 结果中按 `MaskPolicy.PolicyId` 客户端过滤。

### C.2 关联/更换/解绑脱敏策略（写操作，需确认）

**推荐：`UpdatePolicyLabelBindings`**（声明式 PUT 语义，一次调用覆盖新增/修改/删除）：

```bash
wedatacli UpdatePolicyLabelBindings '{"PolicyId":"<policy_id>","LabelIds":[1,2,3],"WorkspaceId":"<ws_id>","Operator":"<user>"}'
```

- LabelIds 为最终全集，服务端自动 diff；`LabelIds:[]` = 解绑全部
- 全成全败；LabelIds ≤ 200

**标签侧替代方案**：通过 `UpdateLabels.PolicyBindingUpdate`（三态）调整关联：
- 不传 `PolicyBindingUpdate` = 保持不动
- `PolicyId="<id>"` = 关联或更换
- `PolicyId=""` = 解除关联

```bash
wedatacli UpdateLabels '{"WorkspaceId":"<ws_id>","Shared":true,"Labels":[{"LabelId":1,"Modifier":"<user>","PolicyBindingUpdate":{"PolicyId":"<policy_id>","WorkspaceId":"<ws_id>"}}]}'
```

### C.4 查询脱敏策略列表（只读）

调用 `ListDataMaskStrategies` 展示策略列表。一个脱敏策略下可以包含多个脱敏方法，每个脱敏方法针对一个用户组生效。

```bash
wedatacli ListDataMaskStrategies '{"WorkspaceId":"<workspace_id>","Offset":0,"Limit":100}'
```

> ⚠️ 展示策略详情时必须同时给出 `GroupId` 与 `GroupName`。名称优先取接口返回的 `Groups[].GroupName`；为空时收集缺失的 `GroupId` **一次性**调用 `ListConsoleGroups` 补查，严禁编造。

### C.5~C.7 创建 / 删除 / 更新脱敏策略（写操作，需确认）

| 操作 | 关键接口 | 要点 |
|------|---------|------|
| **创建** | `CreateDataMaskStrategy` | 不同用户组配不同脱敏方法；确认计划需展示 `GroupId` + `GroupName`；创建后询问是否绑定标签 |
| **删除** | `DeleteDataMaskStrategy` | 不可恢复；需列出影响范围（脱敏方法+用户组）；建议先检查标签绑定 |
| **更新** | `UpdateDataMaskStrategy` | `Groups` 为**全量替换**，必须传入完整规则列表 |

详细交互流程与示例见 [strategy_lifecycle.md](reference/strategy_lifecycle.md)。

---

## 工作流 D：资产标签查询（只读）

通过 `SearchAsset`（FieldTags）或 `ListTagsByAsset` 查询指定表/字段已有的脱敏标签。

如用户进一步追问「这个字段的脱敏策略下发是否成功？为什么没生效？」之类的问题，调用 `ListMaskPolicyDispatchLogs` 按 `LabelId` + 四元组（CatalogName/SchemaName/TableName/FieldName）精确查询，参考工作流 A 阶段 5.3 的结果解读和展示模板。

---

## 工作流 E：AI 打标排除管理

用户对 AI 识别的敏感标签不认可时，可将字段排除（后续扫描自动跳过）；也可恢复已排除字段。

### E.1 排除字段（写操作，需确认）

> ⚠️ **排除 = 保存排除记录 + 移除字段标签**，是原子操作，确认排除即同时移除标签，严禁拆开询问。

展示排除计划（表名、字段名、当前脱敏标签、排除原因）等待确认后，**连续执行**：

1. 保存排除记录：`UpdateAssetTagExclusions`（ExclusionAction=1）
2. 移除字段标签：`BatchVoteAssetTag`（`LabelId="-1"` 清除，或传保留标签列表走增量覆盖）

```bash
wedatacli UpdateAssetTagExclusions '{"ExclusionAction":1,"Items":[{"PropertyType":"TABLE","PropertyId":"<guid>","ColumnName":"<field>","LabelId":"<id>","LabelName":"<name>","Reason":"<原因>","CatalogName":"<c>","SchemaName":"<s>","TableName":"<t>"}]}'
```

### E.2 恢复排除字段（写操作，需确认）

先查询排除记录（`ListAssetTagExclusions`），展示恢复计划等待确认后，调用 `UpdateAssetTagExclusions`（ExclusionAction=2）。

### E.3 查询排除记录（只读）

调用 `ListAssetTagExclusions`，支持按 Catalog、表、标签等维度过滤。

---

## API 速查表

所有接口通过 `wedatacli <Action> '<JSON_Params>'` 调用。详细参数见 [api_reference.md](reference/api_reference.md)。

| 场景 | Action | 关键约束 |
|------|--------|----------|
| 平台资产检索（Catalog/Schema/表列表/搜索） | `Skill("asset-discovery")` | 所有检索/浏览操作统一走 asset-discovery（`get catalogs` / `get schemas` / `get tables` / `search table`） |
| 获取字段及标签信息 | `SearchAsset` | 获取表的字段元数据（名称/类型/描述/采样值）和已有标签；必须循环分页（检查 NextPageToken） |
| 查询脱敏标签列表 | `ListLabels` | **必传 `WorkspaceId` + `Shared=true`**；Types=[4]；PageSize=100；响应 `BizLabel.MaskPolicy` 已回填关联策略 |
| 批量字段打标 | `BatchVoteAssetTag` | FieldTags 按 FieldName 增量覆盖；LabelId="-1" 清除全部标签 |
| 策略侧批量关联标签 | `UpdatePolicyLabelBindings` | 声明式 PUT 语义，LabelIds 为最终全集；全成全败 |
| 修改脱敏标签关联策略 | `UpdateLabels` | 用 `PolicyBindingUpdate` wrapper（三态） |
| 查询脱敏策略列表 | `ListDataMaskStrategies` | — |
| 创建/更新/删除脱敏策略 | `CreateDataMaskStrategy` / `UpdateDataMaskStrategy` / `DeleteDataMaskStrategy` | Groups 为全量替换；详见 [strategy_lifecycle.md](reference/strategy_lifecycle.md) |
| 查询脱敏策略下发流水 | `ListMaskPolicyDispatchLogs` | LabelId 必填；DispatchStatus: 1=成功 2=失败 |
| 排除/恢复字段打标 | `UpdateAssetTagExclusions` | ExclusionAction: 1=排除 2=恢复 |
| 查询排除记录 | `ListAssetTagExclusions` | 支持按 Catalog、表、标签过滤 |

> ℹ️ `WorkspaceId` 由 wedatacli 从 `~/.wedata/config.json` 自动注入，命令示例无需显式传入。

---

## 全局安全约束

1. **写操作需显式确认**：打标、策略绑定/解绑/创建/更新/删除、排除/恢复必须经用户确认
2. **打标确认闭环**：AI 识别结果必须展示给用户确认后才执行
3. **不编造 ID**：所有 ID 必须从 API 查询结果获取。PropertyId = `AssetGuid`，PropertyType = `"TABLE"`
4. **打标增量合并**：FieldTags 按 FieldName 增量覆盖，需合并已有标签 + 新增标签；清除用 `LabelId="-1"`
5. **跳过已打标字段**：字段已有相同脱敏标签时默认跳过
6. **分页处理**：SearchAsset 必须循环检查 `NextPageToken` 直到为空
7. **扫描范围确认**：必须先与用户确认 Catalog 范围，绝不能自动扫描所有 Catalog
8. **检索能力收拢**：所有平台资产的检索/浏览操作（查 Catalog、查 Schema、获取表列表、搜索表）统一走 `Skill("asset-discovery")`；本 skill 不直接调用 `ListCatalogNames` 等检索类 API；`SearchAsset` 仅用于获取表的字段信息和标签信息
9. **脱敏标签标签值非必填**：打标时 `LabelValueId="0"`，`LabelValue=""`
10. **采样数据自动决策**：非空时必须作为交叉验证依据；为空时仅基于元数据识别。不要询问用户。严禁明文展示采样真实值
11. **排除字段跳过**：AI 扫描前先查询排除记录，已排除字段自动跳过
12. **排除即移除标签**：排除 = 保存排除记录 + 移除字段标签，是原子操作，严禁拆开询问
13. **脱敏策略 Groups 全量替换**：更新时必须传入完整的用户组规则列表
14. **脱敏策略删除不可恢复**：删除前必须提醒用户，建议先检查标签绑定
15. **脱敏策略用户组展示必须含名称**：必须同时给出 `GroupId` + `GroupName`；名称优先取接口返回值，为空时一次性调 `ListConsoleGroups` 补查，严禁编造
16. 🔴 **直连分析型 Catalog 能力降级**：目标表属于外部数据目录（直连分析型 Linked Catalog，`connection_id` 非空）时，**敏感识别和打标本身支持**，但**动态脱敏策略下发不支持**。具体处理：
    - 工作流 A 阶段 5.1（打标）：✅ 正常执行
    - 工作流 A 阶段 5.2（处理未绑定策略的标签）：🔴 **跳过策略绑定建议**，改为输出提示：
      > "已完成敏感字段打标。当前表属于外部数据目录（直连分析型），暂不支持动态脱敏策略下发，标签仅作为分类标记使用。"
    - 工作流 A 阶段 5.3（查询下发结果）：🔴 外部表场景下**整体跳过**
    - 工作流 C.2（绑定/解绑脱敏策略）：依赖后端 `BindLabelMaskPolicy` / `UpdatePolicyLabelBindings` 返回错误码 `UnsupportedOperationForLinkedCatalog`，捕获后提示：
      > "外部数据目录（直连分析型）的表暂不支持动态脱敏策略下发。"
    - 识别结果展示调整：外部表的扫描结果中，"已绑定脱敏策略状态"列展示 `N/A（外部表不支持下发）`，而非 ✅/❌；汇总信息中不统计"未绑定策略的标签数"

---

## Reference 文件索引

- [`reference/api_reference.md`](reference/api_reference.md) — 各 API 的请求/响应参数详细说明
- [`reference/strategy_lifecycle.md`](reference/strategy_lifecycle.md) — 脱敏策略创建/删除/更新的详细流程与示例
- [`reference/recognition_rules.md`](reference/recognition_rules.md) — AI 敏感数据识别的降噪排除规则、误报场景处理、采样值校验规则

---

## 最终产物处理

敏感字段扫描清单、脱敏打标变更记录、脱敏策略变更摘要等结构化产物，通过 `Skill("artifact-uploader")` 上传到 `databuddy/governance/`。

关键约束：`domain="governance"` → 仅 Markdown 且单文件 ≤ 5MB → 多文件用 `op="upload_batch"` 合并 → 回显 `studio_link`，失败时展示 `errors[]`。采样真实值必须脱敏后再写入产物，严禁明文。
