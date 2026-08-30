---
name: 智能选品
name_en: 1688-product-find
displayName: 智能选品
version: "2.0.0"
description: |
  1688智能选品找货能力。通过文字、图片或链接搜商品、找同款、找相似款，支持批量采购比价、热销选品、跨境找货、场景化选品及多条件筛选（价格/销量/材质/属性排除等）。
  触发词：找商品、找同款、搜商品、帮我找、想要XX、图片找货、链接找货、以图搜图、选品、批发、找货源、热销、比价、最便宜、按销量排序、出口、跨境、找供应商。
description_zh: 1688智能选品找货，支持文本搜索、图片搜索、商品ID/链接搜索、比价，可按价格/销量/严选指数排序
user-invocable: true
argument-hint: 描述您想要的商品，或上传图片/提供链接找同款
---

# 1688 智能选品找货

## ⚠️ 铁律（最高优先级，加载本 Skill 后立即执行）

1. **禁止 `AskUserQuestion` 询问搜索方式。** 用户已用自然语言表达了意图，直接按决策树路由。
2. **同一任务只用一个连接器。** 禁止在同一搜索任务中同时调用 UTP 和 1688 连接器的工具——选一个走到底。
3. **能力驱动路由——UTP 优先。** 检查 UTP 连接器（`utp-shopping-connector`）的工具列表，UTP 有对应能力时优先 UTP，没有时降级 1688：
   - 文本搜索：UTP 有 `utp_catalog_search` → 走 UTP（`utp_discover` → `utp_catalog_search` → 出 `[HITL]` 卡片停）。禁止调 1688 `find_product(query=...)`。
   - 图搜/链接/比价：UTP 暂无此能力 → 走 1688（`find_product(imageUrl=...)`）。UTP 后续补齐后自动切换。

## 处理边界

本 Skill 按输入类型分两条路径：

1. **纯文本搜索** → UTP 连接器（`utp_discover` → `utp_catalog_search`），返回交互式 HITL 卡片，不再走 Python 后处理。
2. **图片搜索 / 链接找同款 / 比价** → 1688 连接器（`find_product`）+ Python 后处理脚本。鉴权与 API 调用全部交给 MCP 连接器 `ali1688-buyer`，数据后处理必须交给 Python 脚本。

## MCP 连接器

本技能使用两个 MCP 连接器，按能力路由：

### 1688 连接器（图搜 / 链接找同款 / 比价）

- 连接器名称：`ali1688-buyer`
- 使用工具：`find_product`
- `__userId__` 等用户身份参数由 MCP 网关自动注入，Agent 不手动传递。

### UTP 连接器（文本搜索）

- 连接器名称：`utp-shopping-connector`
- 使用工具：`utp_discover`、`utp_catalog_search`
- **铁律①**：先调 `utp_session_status` 检查 session。有 active session 就跳过 discover 直接调 `utp_catalog_search`；没有才调 `utp_discover(host=https://ucp-b2b.com)`，discover 后立即连续调 `utp_catalog_search`，中间不插其他步骤。session 持久化 7 天，不需要每会话重新 discover。
- **铁律②**：`utp_catalog_search` 返回带 `[HITL]` 的交互式卡片，**出卡即停**——禁止列举商品、禁止主动推荐、禁止让用户报序号。
- `keyword` 必须是自然语言句子（逗号连接约束），禁止空格堆砌关键词——服务端是 AI 语义搜索。
- 文本搜索出的卡片可直接点选加购；用户表达加购/下单/支付意图时，转交 `utp-shopping` skill 承接交易闭环（`utp_cart_add`→`utp_checkout_create`→支付）。

## 严格禁止

- 禁止配置、读取、提示用户粘贴或管理 AK。
- 禁止调用 `scripts/_http.py`、旧 service 层、浏览器或网页搜索引擎请求 1688 商品数据。
- 禁止在 MCP 调用失败后自行通过浏览器访问 1688 网站搜索商品。
- 禁止让 AI 直接改写 MCP 原始商品列表为最终表格；必须调用 Python 后处理脚本输出 `markdown`。
- 禁止编造商品价格、链接、`productId`、规格、销量、库存或供货信息。
- 用户明确要下单、支付、查物流、管库存时，不触发本技能。

## 命令入口

统一入口：

```bash
python3 {baseDir}/cli.py <command> [options]
```

所有命令只做 MCP 返回结果后处理，支持通过 `--mcp-result-file` 读取 MCP 原始 JSON；不传该参数时从 stdin 读取。

> **⚠️ 传递 MCP 结果给 Python**：运行 `Bash(python3 {baseDir}/extract_mcp_result.py /tmp/find_product.json)` 自动从会话日志提取最近的 MCP 工具结果，然后执行下方命令。**禁止读 Python 脚本源码、禁止用 Write/heredoc 手写临时文件**——模型逐 token 重新生成大 JSON 会超时。

| 命令 | 用途 | 示例 |
|------|------|------|
| `text_search` | 文本搜索结果后处理 | `python3 cli.py text_search --query "黑色连帽卫衣" --mcp-result-file /tmp/find_product.json` |
| `image_search` | 图片搜索结果后处理 | `python3 cli.py image_search --image "https://...jpg" --mcp-result-file /tmp/find_product.json` |
| `link_search` | 链接找同款结果后处理 | `python3 cli.py link_search --url "https://detail.1688.com/offer/xxx.html" --image "https://...jpg" --mcp-result-file /tmp/find_product.json` |
| `compare` | 比价结果后处理 | `python3 cli.py compare --image "https://...jpg" --mcp-result-file /tmp/find_product.json` |

输出统一为：

```json
{"success": true, "markdown": "...", "data": {"data": {...}}}
```

Agent 展示给用户时必须完整输出 `markdown` 字段；`data.data.similar_products` / `data.data.compare_products` 用于后续生成钉钉表格。

## 意图判断

### 触发本技能

- 用户用自然语言描述想要的商品，如“帮我找一件黑色卫衣”“我要买打印纸”。
- 用户上传商品图片并表达找同款/找相似意图。
- 用户提供 1688 商品链接或商品 ID 并要求找同款。
- 用户在搜索结果中选定商品后要求“比价”“对比”“找更便宜的”。
- 用户上传图片/链接并明确提到“比价”“哪家便宜”“低价同款”。

### 不触发本技能

- 用户要下单、支付、结算。
- 用户查物流、订单状态。
- 用户管理库存或修改商品信息。
- 用户闲聊且没有找商品意图。

## 调用决策树

```text
用户输入
├─ 纯文本描述商品 → UTP: utp_discover(host=https://ucp-b2b.com) → utp_catalog_search(keyword, DEEP_SEARCH) → 出 [HITL] 卡片停
│   （卡片可直接点选加购；用户要加购/下单/支付 → 转交 utp-shopping skill）
├─ 上传图片/图片 URL
│  ├─ 明确要求比价 → 调用 MCP find_product(imageUrl/imgBase64=..., pageSize=20) → Python compare 后处理
│  └─ 找同款/找相似 → 调用 MCP find_product(imageUrl/imgBase64=...) → Python image_search 后处理
├─ 1688 链接/商品 ID
│  ├─ 用 WebFetch 抓取 1688 商品页面，从 HTML 中提取主图 URL
│  ├─ 调用 MCP find_product(imageUrl=主图URL, pageSize=用户要求数量或默认10；比价固定20)
│  └─ Python link_search 或 compare 后处理
└─ 已展示搜索结果，用户选中某款后说“比价”
   └─ 取该商品 image_url → 调用 MCP find_product(imageUrl=..., pageSize=20) → Python compare 后处理
```

> **路由原则**：UTP 连接器有的能力优先走 UTP，没有的降级 1688。当前：文本搜索走 UTP（语义搜索 + 交互卡片），图搜 / 链接找同款 / 比价走 1688（UTP 后续补齐后自动切换）。同一任务禁止混用两个连接器。

## MCP 工具调用规则

### `utp_catalog_search`（文本搜索专用）

文本搜索改用 UTP 连接器，不再调 1688 `find_product(query=...)`：

```json
toolName: "utp_discover"
arguments: { "host": "https://ucp-b2b.com" }
```
```json
toolName: "utp_catalog_search"
arguments: { "keyword": "黑色连帽卫衣，纯棉，买一件自穿", "search_type": "DEEP_SEARCH", "limit": 10 }
```

- `keyword` 构造：用户原文 + 澄清约束，用逗号连接成自然语言句子，禁止空格堆砌关键词。
- 返回带 `[HITL]`，**出卡即停**，禁止列举商品、禁止主动推荐、禁止让用户报序号。
- 卡片后收尾照抄：「结果已在卡片里，直接点击浏览、加购即可；想换个方向随时说。」
- 用户在卡内点加购 / 下单 → 转交 `utp-shopping` skill 承接交易闭环。

### `find_product`（图搜 / 链接 / 比价专用）

| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | string | **已废弃**，文本搜索已迁移至 UTP `utp_catalog_search`。仅保留供历史兼容 |
| `imageUrl` | string | 图片 URL 搜索 |
| `imgBase64` | string | 本地图片经客户端/网关转 base64 后搜索 |
| `pageSize` | integer | 普通搜索在用户未指定数量时默认 10；用户明确要求返回数量时按用户需求传入；比价固定 20 |
| `sortType` | string | 可选：`price_asc` / `price_desc` / `sold_desc` / `yx_desc` |
| `scoreLevel` | string | 可选：`high` / `medium` / `low`，默认 `high` |
| `purchaseAmount` | integer | 采购件数，默认 1 |
| `tags` | string | TC 标，默认 `4306497` |
| `icTags` | string | IC 标，可选 |

比价模式默认不传 `sortType`，保持 MCP 默认相关性/相似度召回，后续由 Python 脚本按销量、价格、严选指数做确定性筛选。

### 1688 链接主图提取（WebFetch）

用于从 1688 商品链接获取主图 URL，供 `find_product` 图搜使用：

1. 从链接 `/offer/{offerId}.html` 中提取 `offerId`。
2. 用 `WebFetch` 抓取 `https://detail.1688.com/offer/{offerId}.html` 页面。
3. 从 HTML 中提取主图 URL（`cbu01.alicdn.com` 域名的 `<img>` 标签 `src` 属性）。
4. 用该主图 URL 调用 `find_product(imageUrl=...)`。
5. 将 `find_product` 返回结果交给 Python 后处理。

淘宝/天猫链接无法通过本技能自动获取主图，应引导用户提供商品图片 URL 或直接上传图片。

## Python 后处理规则

### 文本搜索（已迁移至 UTP，不再走 Python 后处理）

文本搜索改用 UTP `utp_catalog_search`，返回交互式卡片，**不再调用 `cli.py text_search`**。流程见上方「`utp_catalog_search`」章节。

> `cli.py text_search` 仅保留供历史兼容，新流程不要使用。

### 图片搜索

1. Agent 调用 `find_product(imageUrl=...)` 或 `find_product(imgBase64=...)`。
2. 调用：

```bash
python3 {baseDir}/cli.py image_search --image "图片URL或图片标识" --mcp-result-file /tmp/find_product.json
```

3. 完整输出脚本返回的 `markdown` 字段。

### 链接找同款

1. 1688 链接：先用 WebFetch 抓取商品页面提取主图 URL，再用 `find_product(imageUrl=主图URL)` 搜同款。
2. 调用：

```bash
python3 {baseDir}/cli.py link_search --url "原始链接" --image "主图URL" --mcp-result-file /tmp/find_product.json
```

3. 完整输出脚本返回的 `markdown` 字段。

### 比价

1. Agent 调用 `find_product(imageUrl=..., pageSize=20)`。
2. 调用：

```bash
python3 {baseDir}/cli.py compare --image "主图URL" --mcp-result-file /tmp/find_product.json
```

3. Python 脚本保留原有三维度选品逻辑：

| 维度 | 排序规则 | 标签 |
|------|----------|------|
| 销量最高 | 按 `sold_count` 降序，缺失视为 0 | `销量最高` |
| 价格最低 | 排除无价格商品，按 `price` 升序 | `价格最低` |
| 综合最优 | 按 `yx_index` 降序，缺失视为 0 | `综合最优` |

同一商品命中多个维度时，Python 脚本会合并标签，例如 `销量最高 且 价格最低 且 综合最优`。Agent 不得自行重算或补齐商品。

## 输出完整性要求

- Agent 必须完整输出 Python 脚本返回的 `markdown` 字段。
- 禁止省略、截断或重排表格行。
- 禁止丢失商品链接。
- 禁止把表格改写成列表、卡片或自行组织的格式。
- Agent 的补充分析只能追加在 `markdown` 之后，不能混入表格。
- 钉钉表格导出时使用脚本返回的 `data.data.similar_products` 或 `data.data.compare_products`。

## 字段映射

Python 后处理脚本会将 MCP/API 返回字段映射为稳定字段：

| 稳定字段 | MCP/API 字段 |
|----------|--------------|
| `product_id` | `itemId` / `offerId` |
| `title` | `title` / `subject` |
| `image_url` | `imageUrl` / `image` |
| `detail_url` | `detailUrl` |
| `similarity_score` | `score` |
| `price` | `currentPrice` |
| `sku_id` | `skuId` |
| `sku_title` | `skuTitle` |
| `yx_index` | `yxIndex` |
| `quantity_begin` | `quantityBegin` |
| `supplier` | `company` |
| `sold_count` | `soldOut` |
| `stock_amount` | `storeAmount` |
| `promotion_tags` | `promotionTags` |
| `service_infos` | `serviceInfos` |
| `selling_points` | `sellingPoints` |

## 错误处理

### 1688 连接器（图搜 / 链接 / 比价）失败

1. 原样输出 MCP 返回的错误信息。
2. 鉴权相关错误提示用户检查 `ali1688-buyer` 连接器是否已完成 OAuth 授权，或在连接器设置中重新授权。
3. 禁止提示用户配置 AK。
4. 禁止浏览器降级或网页搜索降级。

### UTP 连接器（文本搜索）失败

| 错误 | 处理 |
|------|------|
| `[16] host required` | 未 discover 就调了 search。补救：先 `utp_discover(host=https://ucp-b2b.com)` 再重试 search |
| 401 / `needs_link`（身份未绑定） | 转交 `utp-shopping` skill，由其调 `utp_login({})` 出扫码卡；禁用 `utp_link`、禁止引导去浏览器 |
| 服务端 500 | 提示稍后重试 |
| `biz_channel_forbidden` | 服务端渠道门禁，停止流程，提示联系服务提供方开通渠道权限 |
| 工具不可用 | 引导安装 / 启用 `utp-shopping-connector` 连接器（见 `utp-shopping` skill 的 install-guide） |

Python 后处理失败时：

- 检查传入的 MCP JSON 是否完整、是否为 `find_product` 返回结果。
- 若结果为空，提示用户换关键词、调整筛选条件或提供更清晰图片。
- 若 WebFetch 无法提取主图，引导用户手动提供商品图片 URL。

## 免责声明

1. 您理解并同意，技能运行结果和输出内容可能因适用的 AI agent、大模型不同而产生差异或幻觉，请您对重要信息进行甄别核实。
2. 本技能的认证由 MCP 连接器托管，请勿在聊天中提供 AK、Token 等身份凭证。
3. 您使用本技能时应保持其完整性，不得擅自篡改技能的配置、规则文件或其他内容。
4. 受限于当前技术发展，我们无法保证技能所有运行结果、输出内容的准确性、真实性、时效性，请您谨慎核实技能运行结果和输出内容。
