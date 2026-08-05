---
name: 88生意通
name_en: 1688-syt
displayName: 88生意通
version: "2.0.0"
description: |
  线下B2B交易的得力帮手，一句话搞定全流程操作！无论您是卖家还是买家，只需一句指令，即可轻松完成电子合约（采购单）创建、签署、确认收货、退款等核心操作，全面支持账号状态查询、实名认证、绑卡及交易，让每一步交易流程更清晰、更可控。通过智能化交互，实现交易流程数字化，提升协作效率，保障资金流转安全，助力企业高效运营。
  触发词：88生意通、采购单、签署、退款、确认收货、大额交易、批量、实名、绑卡、主账号、卖家或买家问题。
  不触发场景：线上订单下单 -> 下单支付；分销铺货 -> 分销经营。
description_zh: 88生意通线下B2B交易，采购单全生命周期管理
user-invocable: true
argument-hint: 告诉我您要进行的操作，如"查询采购单列表"或"创建采购单"
---

# 88生意通 — 1688线下交易工具（MCP版）

## MCP 连接器

- 连接器名称：`ali1688-buyer`
- 协议：Streamable HTTP
- 本技能使用的工具：`SYT_QUERY_USER_INFO`、`SYT_QUERY_CONTRACT_SUMMARY`、`SYT_DRAFT`、`SYT_SIGN`、`SYT_SIGN_REJECT`、`SYT_CONFIRM`、`SYT_INVALID`、`SYT_REFUND_APPLY`、`SYT_QUERY_CONTRACT`、`SYT_PAGE_QUERY_CONTRACT`
- 鉴权方式：由 MCP 连接器 `ali1688-buyer` 的 OAuth 自动管理，Agent 无需处理 AK 配置或授权流程。

---

## 产品定位

**88 生意通**是 1688 面向线下买卖合作的交易服务工具，通过电子合约（采购单/合同）与银行资金专户等能力，帮助买卖双方安全、便捷地完成收付款。

### 核心概念

- **账号**：需使用 1688 账号登录。
- **主账号 / 子账号**：企业在 1688 注册认证的主账号拥有最高权限；子账号由主账号创建。**本技能仅支持主账号**操作，子账号引导网页端。
- **买家 / 卖家**：平台两种角色；**卖家即商家**。
- **用户服务协议**：操作前买卖双方需签署 88 生意通用户服务协议。
- **实名认证**：发起交易前，发起方需完成实名认证。
- **收款账户**：卖家在采购单确认或签署前需绑定银行卡收款账户。
- **交易方式**：采购单、合同两类。**本技能仅支持采购单**；合同类请去网页端。
- **支付方式**：引导网页端。

### 采购单主流程

1. 买家或卖家发起采购单（发起前需实名认证）；
2. 收集并确认采购单信息；
3. 邀请对方确认；
4. 确认完成后，买家通过**银行卡转账**支付；
5. 卖家发货；
6. 买家确认交易完成或申请退款（分支：完成则卖家收款；退款则按规则处理）。

### 能力亮点

- 银行资金专户：买家付款后资金进入专户管理，确认完成后再结算给卖家。
- 电子采购单：支持在线生成与确认（电子合同签署由 e 签宝等能力支撑，合同签署以网页为准）。

---

## 可用工具

本技能通过连接器 **ali1688-buyer** 调用以下 MCP 工具：

| 工具名 | 用途 | 关键业务参数 |
|--------|------|-------------|
| `SYT_QUERY_USER_INFO` | 查询账号状态（签约/实名/绑卡） | 无额外业务参数 |
| `SYT_PAGE_QUERY_CONTRACT` | 分页查询采购单列表 | contractRole, pageIndex, pageSize, subStatusIn, statusIn |
| `SYT_QUERY_CONTRACT` | 查询单笔采购单详情 | draftNo |
| `SYT_QUERY_CONTRACT_SUMMARY` | 查询采购单汇总统计 | contractRole |
| `SYT_DRAFT` | 创建/起草采购单（自动完成己方签署） | draftRole, counterpartyName, counterpartyOrigin, contractType, purchaseItemList |
| `SYT_SIGN` | 签署/确认采购单 | draftNo |
| `SYT_SIGN_REJECT` | 拒绝签署采购单 | draftNo |
| `SYT_CONFIRM` | 买家确认收货 | draftNo |
| `SYT_INVALID` | 采购单失效/作废 | draftNo |
| `SYT_REFUND_APPLY` | 申请退款（仅买家） | draftNo |

---

## 公共参数

以下公共字段**全部使用固定值注入**，**适用于所有工具**，**Agent 绝不修改**：

| 参数 | 固定值 | 说明 |
|------|-----------|------|
| `skillName` | `"88生意通"` | 技能名称 |
| `site` | `"1688"` | 站点标识 |
| `skillVersion` | `"2.0.0"` | 技能版本 |

---

## API 响应格式

### 网关已剥包

MCP 网关已经吸收签名、重试、错误映射与拆包逻辑：

| 处理项 | 改造后归属 |
|--------|-----------|
| HMAC 签名 + 重试 | **网关吸收**（OAuth + 网关层重试） |
| HTTP 错误映射（401/429/400/500） | **网关吸收**（统一抛工具调用错误） |
| 第一层拆包 | **网关吸收**，工具直接返回 `data` 字段对应的 dict |

**Agent 拿到的就是网关解包后的业务数据（即 `data` 字段内容）**，无需再做二次提取。

### 错误判断"三连"（顺序依次判断）

实测网关响应同时包含网关层与业务层两套错误结构，加上工具调用本身的异常，共有三层需要逐一判断：

| 层级 | 字段 | 触发条件 | Agent 处理 |
|------|------|----------|-----------|
| **① 工具调用层** | 工具调用直接抛错（如 401/429/超时） | 网关侧 OAuth 失败 / 限流 / 网络异常 | 按下文「错误处理」表关键词应对，不再读响应 |
| **② 网关层** | `__success__: false`、`__msgCode__`、`__msgInfo__` | 工具调用未抛错但响应顶层 `__success__=false` | 输出 `__msgInfo__` 中文转述，按 `__msgCode__` 路由（`401`/`429`/`400`/`500` 等） |
| **③ 业务层** | `success: false`、`responseCode`、`responseMessage` | 网关层 OK 但业务侧失败（如 `NOT_1688_MAIN_ACCOUNT`、未签约、单据状态不匹配等） | 输出 `responseMessage` 中文转述，按 `responseCode` 路由 |

### 网关返回的"业务数据"结构

网关返回的对象即解包后的业务 dict。**网关不再下发 markdown 字段**，Agent 必须按下文「展示模板」章节自行拼装 Markdown 给用户。

---

## 使用流程

Agent 根据用户意图**直接执行对应工具调用**，无需每次先执行 `SYT_QUERY_USER_INFO`。
各工具在账号状态异常等情况下会自行返回明确错误，Agent 按下方「错误处理」应对即可。

**采购单典型路径**：

```
SYT_QUERY_USER_INFO（检查准入）→ SYT_DRAFT（创建采购单，自动签署）→ SYT_SIGN（对手方签署）→ SYT_QUERY_CONTRACT（确认状态）
```

---

## 通用规则（硬性要求）

### 对用户呈现（对客）

- **仅使用中文**：状态码、字段说明、错误原因等均译为中文表述；不展示原始英文枚举或技术字段名（除非用户明确要求看技术细节）。
- **最小可用信息**：只返回用户决策所需的核心结论，避免冗长中间过程。
- **不暴露请求细节**：不向用户展示完整请求参数、工具调用细节、响应原文；需要收集参数时，直接说明**需要用户提供哪些信息**及**将得到什么结果**。
- **引导**：无法回答或超出本技能范围时，**友善引导**用户前往 88 生意通页面（使用带 `tracelog=88sytskill` 的链接）。
- **免责声明**：每次回答末尾增加简短、友善的免责声明（见文末模板）。
- **二次确认**：下列行为在执行前须请用户**明确确认**后再调用工具：确认收货、采购单失效、拒绝签署、申请退款、取消退款（取消退款当前暂无独立工具支持，请引导用户在网页端操作）。

### 外链规范

- 所有提供给用户点击的 `syt.1688.com`、`peixun.1688.com` 等链接，须追加参数 **`tracelog=88sytskill`**（已有查询参数用 `&`，否则用 `?`）。
- 标准入口链接（按需选用）：
  - 买家首页：`https://syt.1688.com/page/SYT/buyer?__existtitle__=1&__removesafearea__=1&__immersive__=1&tracelog=88sytskill`
  - 卖家首页：`https://syt.1688.com/page/SYT/seller?__existtitle__=1&__removesafearea__=1&__immersive__=1&tracelog=88sytskill`
  - 买家采购单详情页：`https://syt.1688.com/page/SYT/buyer-contract-simple?draftNo=${draftNo}&__existtitle__=1&__removesafearea__=1&__immersive__=1&tracelog=88sytskill`（需动态替换 `${draftNo}`）
  - 卖家采购单详情页：`https://syt.1688.com/page/SYT/seller-contract-simple?draftNo=${draftNo}&__existtitle__=1&__removesafearea__=1&__immersive__=1&tracelog=88sytskill`（需动态替换 `${draftNo}`）
  - 用户服务协议：`https://syt.1688.com/n/openService/sign/preview?code=SYT_OPEN_SERVICE_AGREEMENT&tracelog=88sytskill`
  - 帮助文档：`https://peixun.1688.com/space/WVJqzq3VdLKmYEKZ2AmonAjAbY4pDXdb?tracelog=88sytskill#4ever-bi-201`

### 角色确认

- 当工具需要 `contractRole` 或 `draftRole` 参数时（如查询采购单列表、查询汇总、创建采购单），若用户**未明确说明自己是买家还是卖家**，Agent 须**先询问用户身份**再执行工具调用。
- 询问话术示例：「请问您是以买家身份还是卖家身份操作？」

### 调用策略

- 已具备必要参数时，**直接发起工具调用**，不要在对话中复述完整调用细节。
- 返回数据仅抽取中文业务结论写入回复。

---

## 安全声明

| 风险级别 | 操作 | Agent 行为 |
|---------|------|-----------|
| **只读** | SYT_QUERY_USER_INFO, SYT_PAGE_QUERY_CONTRACT, SYT_QUERY_CONTRACT, SYT_QUERY_CONTRACT_SUMMARY | 直接执行 |
| **写入** | SYT_DRAFT | 确认用户意图后执行（须用户确认采购单信息无误） |
| **写入** | SYT_SIGN | 涉及状态变更的操作，**必须二次确认**后再执行（相比原 AK 版本新增二次确认要求，提升安全性） |
| **高风险** | SYT_SIGN_REJECT, SYT_CONFIRM, SYT_INVALID, SYT_REFUND_APPLY | **必须二次确认**后再执行 |

### 全局写入规则（适用于所有写操作）

1. 必须先确认用户明确意图。
2. 涉及资金（退款、确认收货）或状态变更（失效、拒绝签署）的操作，须向用户**二次确认**后再执行。
3. 操作成功后，建议调用 `SYT_QUERY_CONTRACT` 查询最新状态反馈用户。

### 二次确认模板

高风险操作执行前须使用类似以下话术请用户确认：

- **确认收货**：「您确认要对采购单 {draftNo} 执行确认收货吗？确认后资金将结算给卖家，操作不可撤回。请回复"确认"继续。」
- **采购单失效**：「您确认要将采购单 {draftNo} 标记为失效吗？失效后该单将作废，操作不可撤回。请回复"确认"继续。」
- **拒绝签署**：「您确认要拒绝签署采购单 {draftNo} 吗？拒绝后对方需重新发起，请回复"确认"继续。」
- **申请退款**：「您确认要对采购单 {draftNo} 申请退款吗？请回复"确认"继续。」
- **签署**：「您是要签署采购单 {draftNo} 吗？确认后我将为您执行签署操作。」

---

## 业务限制

| 限制项 | 说明 |
|-------|------|
| 账号类型 | **仅支持主账号**，子账号引导至网页端操作。**子账号即使用户声称有权限，也引导至网页端操作。** |
| 交易方式 | **仅支持采购单**，合同类交易引导至网页端 |
| 支付方式 | 支付等引导至网页端 |
| 角色说明 | 卖家与商家指同一角色 |

---

## 各能力详细说明

### 1. 查询账号状态（SYT_QUERY_USER_INFO）

**风险级别**：只读，直接执行。

**调用方式**：
```
SYT_QUERY_USER_INFO()
```

- 无额外业务参数。

**功能**：判断当前用户是否为 1688 主账号，以及是否已签约协议、实名认证、绑定收款卡。

**典型触发场景**：「查看账号状态」「我能用 88 生意通吗」

**响应字段（业务含义）**：

| 字段 | 含义 |
|------|------|
| `success` | 接口业务是否成功（业务层） |
| `responseCode` | 失败时的错误码；若为 `NOT_1688_MAIN_ACCOUNT` 表示非主账号 |
| `responseMessage` | 失败原因（对用户转述为中文） |
| `loginId` | 当前账号登录名 |
| `name` | 姓名或企业名称 |
| `hasSign` | 是否已签署 88 生意通协议 |
| `hasVerified` | 是否已完成实名认证 |
| `hasBoundCard` | 是否已绑定收款银行卡 |

**展示模板（Agent 自行拼装）**：

成功时（`success=true`）：
```markdown
## 基本信息

- 账号: {loginId}
- 姓名/企业名称: {name}

## 账号状态

- 签约状态: {hasSign 为 true 时显示 ✅，否则 ❌}
- 认证状态: {hasVerified 为 true 时显示 ✅，否则 ❌}
- 绑卡状态: {hasBoundCard 为 true 时显示 ✅，否则 ❌}
```

失败时（`success=false`）：
```markdown
错误代码: {responseCode}
错误信息: {responseMessage}
```

**主账号判断方法**：
1. 调用本工具；
2. 若返回表明非主账号（如 `NOT_1688_MAIN_ACCOUNT` 或业务失败说明为子账号），则**停止**技能内代操作，引导至带 `tracelog=88sytskill` 的 88 生意通页面。

**签约/认证/绑卡未满足时**：
- 不向用户展示接口细节，友善说明当前缺哪一步，并给出对应网页入口链接（须含 `tracelog=88sytskill`），引导在浏览器完成。

---

### 2. 查询采购单列表（SYT_PAGE_QUERY_CONTRACT）

**风险级别**：只读，直接执行。

**调用方式**：
```
SYT_PAGE_QUERY_CONTRACT(
  contractRole="BUYER" 或 "SELLER",
  contractType="PURCHASE_ORDER",
  pageIndex=1,
  pageSize=10,
  subStatusIn=<可选，子状态过滤>,
  statusIn=<可选，主状态过滤>
)
```

**业务参数**：
- `contractRole`：必填，角色 — `BUYER`（买家）或 `SELLER`（卖家）
- `pageIndex`：可选，页码，默认 1
- `pageSize`：可选，每页条数，默认 10
- `subStatusIn`：可选，按子状态过滤
- `statusIn`：可选，按主状态过滤

**固定参数（每次调用原样填入，勿修改）**：
- `contractType`：固定 `"PURCHASE_ORDER"`（仅查采购单）

**功能**：查询当前用户采购单列表（分页）。

**响应字段（业务含义）**：

| 字段 | 含义 |
|------|------|
| `success` | 业务层是否成功 |
| `responseCode` | 失败时的错误码；`NOT_1688_MAIN_ACCOUNT` 表示非主账号 |
| `responseMessage` | 失败原因 |
| `totalCount` | 总条数 |
| `dataList` | 采购单列表（数组） |

**列表每项字段**：
- `draftNo`：采购单号
- `status`：主状态枚举（英文，需翻译）
- `drafterRole`：起草方角色（`BUYER`/`SELLER`）
- `sellerName`：卖家名称
- `buyerName`：买家名称
- `amount`：金额（元，可能缺失）
- `gmtCreate`：创建时间

**状态枚举翻译**：

| 英文枚举 | 中文 |
|---------|------|
| `DRAFT` | 起草中 |
| `DATA_SUPPLYING` | 起草中 |
| `SIGNING` | 确认中 |
| `SIGN_REJECT` | 已拒绝 |
| `PAYING` | 待支付 |
| `PAID` | 已支付 |
| `SHIPPED` | 已发货 |
| `COMPLETED` | 已完成 |
| `CANCELLED` | 已取消 |
| `INVALID` | 已失效 |

**角色翻译**：`BUYER` → 买家，`SELLER` → 卖家。未命中则原样返回。

**展示模板（Agent 自行拼装）**：

成功且 `dataList` 非空：
```markdown
## 采购单列表（共 {totalCount} 条）

### 单号: {draftNo}

- 状态: {翻译后的中文状态}
- 起草方: {翻译后的中文角色}
- 卖家: {sellerName}
- 买家: {buyerName}
- 金额: {amount} 元   ← amount 为 null 时省略此行

（重复每个 item）
```

成功但 `dataList` 为空：
```markdown
## 采购单列表（共 0 条）

暂无采购单数据。
```

失败：
```markdown
错误代码: {responseCode}
错误信息: {responseMessage}
```

**输出规范**：
- 用表格呈现每条：单号（`draftNo`）、状态（中文）、起草方角色（中文）、卖家名称、买家名称、金额（元）。
- `totalCount` 可简述总条数。
- 若无 `amount` 字段则省略，不编造。
- 失败码 `NOT_1688_MAIN_ACCOUNT` 等按通用错误处理规则应对。

**前置条件**：须为主账号，已签约、已实名认证。

---

### 3. 查询采购单详情（SYT_QUERY_CONTRACT）

**风险级别**：只读，直接执行。

**调用方式**：
```
SYT_QUERY_CONTRACT(
  draftNo="88SYT开头的采购单号"
)
```

**参数说明**：
- `draftNo`：必填，采购单号（88SYT 开头）

**功能**：根据采购单号查询当前详情。

**响应字段（业务含义）**：

| 字段 | 含义 |
|------|------|
| `success` | 业务层是否成功 |
| `responseCode` | 失败时的错误码 |
| `responseMessage` | 失败原因 |
| `contract.draftNo` | 采购单号 |
| `contract.gmtCreate` | 创建时间 |
| `contract.status` | 主状态英文枚举（按上表翻译） |
| `contract.drafterRole` | 起草方角色（`BUYER`/`SELLER`） |
| `contract.drafterType` | 起草方类型（`PERSONAL`/`COMPANY`） |
| `contract.buyerType` | 买家类型（`PERSONAL`/`COMPANY`） |
| `contract.sellerType` | 卖家类型（`PERSONAL`/`COMPANY`） |
| `contract.buyerName` | 买家展示名 |
| `contract.sellerName` | 卖家展示名 |
| `contract.amount` | 金额（元） |

**类型翻译**：`PERSONAL` → 个人，`COMPANY` → 企业。

**展示模板（Agent 自行拼装）**：

成功且 `contract` 存在：
```markdown
## 采购单详情

- 单号: {draftNo}
- 状态: {翻译后中文}
- 起草方: {drafterRole 翻译} ({drafterType 翻译})
- 买家: {buyerName} ({buyerType 翻译})
- 卖家: {sellerName} ({sellerType 翻译})
- 金额: {amount} 元   ← amount 为 null 时省略此行
```

成功但 `contract` 为空：
```markdown
未找到采购单详情。
```

失败：
```markdown
错误代码: {responseCode | "-"}
错误信息: {responseMessage | "未知错误"}
```

**前置条件**：须为主账号，已签约、已实名认证。

---

### 4. 查询采购单汇总（SYT_QUERY_CONTRACT_SUMMARY）

**风险级别**：只读，直接执行。

**调用方式**：
```
SYT_QUERY_CONTRACT_SUMMARY(
  contractRole="BUYER" 或 "SELLER"
)
```

**参数说明**：
- `contractRole`：必填，角色 — `BUYER`（买家）或 `SELLER`（卖家）

**功能**：查询用户在 88 生意通侧的采购单汇总数据（如待确认笔数、已收款金额、待收款金额等）。

**调用前要求**：**必须**先确认用户当前咨询身份是买家还是卖家，再传入对应的 `contractRole`。

**响应字段（业务含义）**：

| 字段 | 含义 |
|------|------|
| `success` | 业务层是否成功 |
| `responseCode` | 失败错误码 |
| `responseMessage` | 失败原因 |
| `data.dataList` | 多项指标列表（注意此处嵌套了一层 `data`） |

**dataList 每项字段**：
- `name`：英文指标名（按下表翻译）
- `value`：指标值（数值或金额字符串）
- `link`：可选，指标对应的网页链接（须追加 `tracelog=88sytskill`）

**指标名翻译**：

| 英文 name | 中文 |
|----------|------|
| `pendingConfirm` | 待确认 |
| `receivedAmount` | 已收款金额 |
| `pendingReceiveAmount` | 待收款金额 |
| `pendingPayAmount` | 待支付金额 |
| `paidAmount` | 已支付金额 |

**链接追加 tracelog 规则**：URL 已含 `?` 时用 `&tracelog=88sytskill`，否则用 `?tracelog=88sytskill`。

**展示模板（Agent 自行拼装）**：

成功且 `data.dataList` 非空：
```markdown
## 采购单汇总信息

- {name 翻译后}: {value} [查看详情]({link 追加 tracelog 后})   ← 有 link 时
- {name 翻译后}: {value}                                         ← 无 link 时

（重复每项）
```

成功但 `dataList` 为空：
```markdown
暂无汇总数据。
```

失败：
```markdown
错误代码: {responseCode | "-"}
错误信息: {responseMessage | "未知错误"}
```

**输出规范**：将 `name`/`value` 译为中文句子输出；若接口返回链接，替换或追加 `tracelog=88sytskill` 后再给用户。

**前置条件**：主账号，已签约、已实名认证。

---

### 5. 创建采购单（SYT_DRAFT）

**风险级别**：写入操作，须确认用户意图后执行。

**调用方式**：
```
SYT_DRAFT(
  draftRole="BUYER" 或 "SELLER",
  counterpartyName="对方1688登录名或企业名称",
  counterpartyOrigin="LOGIN_ID_1688_MATCH",
  contractType="PURCHASE_ORDER",
  purchaseItemList=[
    {
      "productName": "A4打印纸",
      "quantity": 10,
      "unitPrice": "1.00",
      "subtotal": "10.000",
      "productSpec": "箱"
    }
  ]
)
```

**业务参数（需根据用户输入填写）**：
- `draftRole`：必填，己方角色 — `BUYER`（买家）或 `SELLER`（卖家）
- `counterpartyName`：必填，对方 1688 会员登录名或企业名称
- `purchaseItemList`：必填，采购清单数组

**固定参数（每次调用原样填入，勿修改）**：
- `counterpartyOrigin`：固定为 `"LOGIN_ID_1688_MATCH"`
- `contractType`：固定为 `"PURCHASE_ORDER"`

**采购清单项字段**：

| 字段 | 必填 | 说明 |
|------|------|------|
| `productName` | 是 | 商品名称（须 `strip()` 去前后空格） |
| `quantity` | 是 | 商品数量（整数，最小 1） |
| `unitPrice` | 是 | 商品单价（数字字符串，最小 0.001 元） |
| `subtotal` | 是 | 各商品小计（= 数量 × 单价，**保留三位小数**） |
| `productSpec` | 是 | 商品规格（必填，提供时须 strip） |

**校验规则（Agent 须在调用前自行校验）**：
1. `draftRole` 必须为 `BUYER` 或 `SELLER`，否则报参数错误。
2. `counterpartyName` 不能为空；调用前**移除所有空格**（`replace(" ", "")`）。
3. `purchaseItemList` 不能为空。
4. 每项 `productName` 不能为空（去空格后）。
5. 每项 `quantity` 须为大于等于 1 的整数。
6. 每项 `unitPrice` 须为大于等于 0.001 的数字。
7. 每项 `subtotal = quantity × unitPrice`，保留三位小数。
8. 总金额（各 subtotal 之和）不能低于 0.01 元，否则提示用户调整数量或单价。

**功能**：创建采购单（发起交易），**并自动完成己方签署**。创建成功后无需再单独调用 SYT_SIGN。

**响应字段（业务含义）**：

| 字段 | 含义 |
|------|------|
| `success` | 是否创建成功（业务层） |
| `responseCode` | 失败错误码 |
| `responseMessage` | 失败原因 |
| `draftNo` | 采购单号（必须告知用户，可称「交易单号」） |
| `contractCurrentStatus` | 创建后的合同状态 |

**展示模板（Agent 自行拼装）**：

成功：
```markdown
## 创建采购单结果

- 创建状态: 成功
- 采购单号: {draftNo}
- 当前状态: {contractCurrentStatus}   ← 缺失时省略此行
```

失败：
```markdown
错误代码: {responseCode | "-"}
错误信息: {responseMessage | "未知错误"}
```

**成功后处理**：务必再调 `SYT_QUERY_CONTRACT` 同步最新状态告知用户。

**前置条件**：
- 须为主账号，已签约、已实名认证。
- 创建前须请用户**确认信息无误**。

---

### 6. 签署采购单（SYT_SIGN）

**风险级别**：写入操作，涉及状态变更，**必须二次确认**后再执行。

**调用方式**：
```
SYT_SIGN(
  draftNo="采购单号"
)
```

**参数说明**：
- `draftNo`：必填，采购单号

**功能**：对采购单进行签署确认。

**口语映射**：用户说「签署采购单」「确认采购单」「签约」「同意」等均指本操作。

**响应字段（业务含义）**：

| 字段 | 含义 |
|------|------|
| `success` | 是否签署成功（业务层） |
| `responseCode` | 失败错误码 |
| `responseMessage` | 失败原因 |
| `draftNo` | 采购单号 |
| `contractCurrentStatus` | 签署后的合同状态英文枚举（按上文「状态枚举翻译」表译为中文展示） |

**展示模板（Agent 自行拼装）**：

成功：
```markdown
## 采购单签署结果

✅ 采购单签署成功

- 采购单号: {draftNo}
- 当前状态: {翻译后中文状态}   ← 缺失时省略此行
```

失败：
```markdown
错误代码: {responseCode | "-"}
错误信息: {responseMessage | "未知错误"}
```

**成功后处理**：再次调用 `SYT_QUERY_CONTRACT` 查询最新状态并反馈用户。

**前置条件**：
- 须为主账号，已签约、已实名认证。

---

### 7. 拒绝签署（SYT_SIGN_REJECT）

**风险级别**：高风险，必须二次确认。

**调用方式**：
```
SYT_SIGN_REJECT(
  draftNo="采购单号"
)
```

**参数说明**：
- `draftNo`：必填，采购单合同号

**功能**：拒绝签署采购单。

**响应字段（业务含义）**：

| 字段 | 含义 |
|------|------|
| `success` | 是否拒绝成功（业务层） |
| `responseCode` | 响应码，`SUCCESS` 表示成功 |
| `responseMessage` | 失败原因 |
| `draftNo` | 采购单号 |
| `contractCurrentStatus` | 合同当前状态（英文枚举，按下表翻译） |

**签署状态枚举翻译**：

| 英文枚举 | 中文 |
|---------|------|
| `SIGN_INIT` | 签署初始化 |
| `AUTHING` | 核身中 |
| `SIGNING` | 签署中 |
| `SIGN_SUCCESS` | 签署成功 |
| `SIGN_FAIL` | 签署失败 |
| `SIGN_EXPIRED` | 签署过期 |

> 注：拒绝签署返回的是签署流程状态（前者），与采购单列表的合同主状态（后者）是两套不同的枚举。Agent 拼装时按响应字段语义选用对应枚举表。

**展示模板（Agent 自行拼装）**：

成功：
```markdown
## 拒绝签约结果

✅ 拒绝签约成功

- 采购单号: {draftNo}
- 合同当前状态: {翻译后中文}   ← 缺失时省略此行
```

失败：
```markdown
错误代码: {responseCode | "-"}
错误信息: {responseMessage | "未知错误"}
```

**成功后处理**：再次调用 `SYT_QUERY_CONTRACT` 查询最新状态并反馈用户。

**前置条件**：
- 须为主账号，已签约、已实名认证。
- **卖家需校验绑卡**，未绑卡则不能继续；**买家无需绑卡**。
- 执行前须请用户**明确确认**（二次确认）。

---

### 8. 确认收货（SYT_CONFIRM）

**风险级别**：高风险，必须二次确认。

**调用方式**：
```
SYT_CONFIRM(
  draftNo="采购单号"
)
```

**参数说明**：
- `draftNo`：必填，采购单号

**功能**：买家确认收货。

**响应字段（业务含义）**：

| 字段 | 含义 |
|------|------|
| `success` | 是否确认成功（业务层） |
| `responseCode` | 失败错误码 |
| `responseMessage` | 失败原因 |
| `draftNo` | 采购单号 |

**展示模板（Agent 自行拼装）**：

成功：
```markdown
## 确认收货结果

✅ 确认收货成功

- 采购单号: {draftNo}   ← 缺失时省略此行
```

失败：
```markdown
错误代码: {responseCode | "-"}
错误信息: {responseMessage | "未知错误"}
```

**成功后处理**：再次调用 `SYT_QUERY_CONTRACT` 查询最新状态并反馈用户。

**前置条件**：
- 须为主账号，已签约、已实名认证。
- 当前用户须为该单的**买家**角色。
- 执行前须请用户**明确确认**（二次确认）。

---

### 9. 采购单失效（SYT_INVALID）

**风险级别**：高风险，必须二次确认。

**调用方式**：
```
SYT_INVALID(
  draftNo="采购单号"
)
```

**参数说明**：
- `draftNo`：必填，采购单合同号

**功能**：将采购单标记为失效（作废/删除）。

**响应字段（业务含义）**：

| 字段 | 含义 |
|------|------|
| `success` | 是否失效成功（业务层） |
| `responseCode` | 响应码，`SUCCESS` 表示成功 |
| `responseMessage` | 失败时的错误描述 |

**展示模板（Agent 自行拼装）**：

成功：
```markdown
## 采购单失效结果

✅ 采购单已成功标记为失效
```

失败：
```markdown
## 采购单失效结果

❌ 采购单失效失败

- 错误信息: {responseMessage}   ← responseMessage 为空时省略此行
```

> 注：采购单失效在失败分支**不输出 responseCode**，仅在有 `responseMessage` 时输出错误信息行。其他能力的失败展示为 "错误代码 + 错误信息" 双行结构，本能力是唯一例外。

**成功后处理**：再次调用 `SYT_QUERY_CONTRACT` 查询最新状态并反馈用户。

**前置条件**：
- 须为主账号，已签约、已实名认证。
- **卖家需校验绑卡**，未绑卡则不能继续；**买家无需绑卡**。
- 执行前须请用户**明确确认**（二次确认）。

---

### 10. 申请退款（SYT_REFUND_APPLY）

**风险级别**：高风险，必须二次确认。

**调用方式**：
```
SYT_REFUND_APPLY(
  draftNo="采购单号"
)
```

**参数说明**：
- `draftNo`：必填，采购单合同号

**功能**：**仅限买家**发起退款申请。

**响应字段（业务含义）**：

| 字段 | 含义 |
|------|------|
| `success` | 是否申请成功（业务层） |
| `responseCode` | 响应码，`SUCCESS` 表示成功 |
| `responseMessage` | 失败原因 |
| `draftNo` | 采购单号 |
| `refundNo` | 退款申请单号（申请成功后返回，须告知用户） |

> 注：退款申请在响应顶层直接读取 `draftNo`/`refundNo`（**不在 `data.result` 嵌套层下**）。Agent 拼装时直接读 `responseBody.draftNo` / `responseBody.refundNo`。

**展示模板（Agent 自行拼装）**：

成功：
```markdown
## 退款申请结果

✅ 退款申请提交成功

- 采购单号: {draftNo}      ← draftNo 缺失时省略此行
- 退款申请单号: {refundNo}  ← refundNo 缺失时省略此行
```

失败：
```markdown
错误代码: {responseCode | "-"}
错误信息: {responseMessage | "未知错误"}
```

**前置条件**：
- 须为主账号，已签约、已实名认证。
- 申请退款仅限**买家操作**，无需校验绑卡状态。
- 执行前须请用户**明确确认**（二次确认）。

---

## 错误处理

### 错误三层定位（先判层级再判错误码）

工具调用返回后，按下述顺序逐层定位错误：

1. **工具调用层**：MCP 工具直接抛出异常（401/429/超时等），Agent 看到工具异常，直接按下表关键词应对。
2. **网关层**：响应顶层 `__success__: false` → 读取 `__msgCode__`（含 `400/401/429/500` 字样按对应错误处理）+ `__msgInfo__`（中文转述给用户）。
3. **业务层**：网关层通过后再看响应 `success: false` → 读取 `responseCode`（如 `NOT_1688_MAIN_ACCOUNT`）+ `responseMessage`（中文转述）。

> **三层都通过（工具调用未抛错 + `__success__=true` + `success=true`）才算调用成功**，再读各 capability 的业务字段拼装展示模板。

### 错误码与 Agent 应对

| 错误码/关键词 | 含义 | Agent 应对 |
|--------------|------|-----------|
| 400 | 参数不合法 | 检查用户输入是否正确，提示具体哪个参数有问题 |
| 401 / "鉴权无效" / "授权过期" | 鉴权失败 | 提示用户登录态可能过期，引导重新登录或联系客服 |
| 429 / "限流" | 请求被限流 | 建议用户稍后重试（等待 1-2 分钟） |
| 500 | 服务端异常 | 建议用户稍后重试，如持续出现建议联系客服 |
| "非主账号" / `NOT_1688_MAIN_ACCOUNT` | 当前为子账号 | 引导用户使用主账号操作，或前往网页端 |
| "未签约" / "未实名" / "未绑卡" | 准入条件未满足 | 引导用户前往 [88生意通页面](https://syt.1688.com/page/SYT/buyer?__existtitle__=1&__removesafearea__=1&__immersive__=1&tracelog=88sytskill) 完成相关操作 |
| 网络异常 | 网络连接失败 | 告知用户"网络异常，请检查网络连接后重试" |
| 其他未知错误 | — | 仅输出工具返回的错误信息即可 |

### 处理原则

当工具调用返回失败时：
1. **将错误信息转述为中文**，友善告知用户；
2. **根据错误关键词追加引导**（按上表对应处理）；
3. **不暴露**原始错误码、调用参数等技术细节。

---

## 常见问答（对客口径）

| 问题 | 回答 |
|------|------|
| 是否官方产品？ | 是 1688 官方线下交易服务工具。 |
| 支付是否安全？ | 资金专户管理，买家确认完成后卖家收款，过程可追溯。 |
| 卖家有什么好处？ | 增强买家信任、促成交易；平台对交易额有相应权益说明以官方为准。 |
| 转账是否麻烦？ | 发起/确认采购单 -> 买家付款 -> 卖家发货 -> 买家确认完成，资金按规则结算。 |
| 支持账期支付吗？ | 本技能不支持，请前往 88 生意通网页办理。 |
| 有法律效力吗？ | 经双方确认的采购单及电子合同具有与纸质合同同等法律效力；电子合同签章服务以平台公示为准。 |

---

## 意图判断

### 触发本技能

用户提到以下关键词时触发：88生意通、采购单、签署合同、确认收货、退款申请、线下交易、大额转账、批量、实名认证、绑卡、主账号、卖家或买家问题

### 不触发本技能

- 线上订单下单/支付 -> 下单支付技能
- 分销铺货 -> 分销经营技能
- 售后退款（线上订单） -> 履约服务技能

---

## 典型交互示例

### 示例 1：创建采购单

```
用户: 我要创建一个采购单

Agent: 请问您是以买家身份还是卖家身份发起采购单？

用户: 买家

Agent: 好的，请提供以下信息：
1. 对方（卖家）的 1688 登录名或企业名称
2. 采购商品清单（商品名称、规格、数量、单价）

用户: 对方登录名是 shop123，买 100 箱 A4 纸，单价 25 元

Agent: 请确认以下采购单信息：
- 您的角色：买家
- 对方登录名：shop123
- 商品：A4 纸，规格：箱，数量 100，单价 25.00 元，小计 2500.000 元
- 总金额：2500.000 元
信息无误请回复"确认"，我将为您创建采购单。

用户: 确认

→ Agent 调用 SYT_DRAFT，成功后调用 SYT_QUERY_CONTRACT 查询最新状态，拼装展示模板回复用户。
```

### 示例 2：查询并签署采购单

```
用户: 帮我查一下我的采购单

Agent: 请问您是以买家身份还是卖家身份查询？

用户: 卖家

→ Agent 调用 SYT_PAGE_QUERY_CONTRACT(contractRole="SELLER", contractType="PURCHASE_ORDER")，拼装列表展示。

用户: 帮我签署 88SYT20260324419012

Agent: 您是要签署采购单 88SYT20260324419012 吗？确认后我将为您执行签署操作。

用户: 确认

→ Agent 调用 SYT_SIGN(draftNo="88SYT20260324419012")，成功后调用 SYT_QUERY_CONTRACT 查询最新状态。
```

---

## 输出规范

- 操作成功后，建议调用 `SYT_QUERY_CONTRACT` 查询最新状态反馈用户
- 金额展示使用"元"为单位
- 所有输出使用中文
- 采购单号（draftNo）必须完整展示给用户
- 接口返回的链接如包含 `syt.1688.com` 域名，须确保包含 `tracelog=88sytskill` 参数

---

## 免责声明

每次回答末尾增加：

> 以上信息根据当前查询结果整理，具体以 88 生意通页面及银行/平台实际处理为准。若与您页面不一致，请以页面展示为准。
