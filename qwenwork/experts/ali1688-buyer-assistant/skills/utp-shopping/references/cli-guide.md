# CLI 执行方式指导

通过 `utp` 命令行工具执行购物操作。所有命令输出 JSON，AI 解析后以表格展示给用户。**不要向用户暴露 CLI 命令细节**，除非用户主动询问或出错需要排查。

> 若执行 `utp` 时报 `command not found`，说明 CLI 未安装，参见 `references/install-guide.md`。

---

## 响应格式

CLI 输出为嵌套 JSON（双层解析）：

```
第一层（CLI 输出）: {"status_code": 200, "headers": {...}, "body": "<JSON字符串>"}
第二层（业务数据）: JSON.parse(body) → 实际数据
```

### 错误判断

- `status_code` 非 200，或
- 业务数据含 `messages[]` 且 `type=error`

出错时展示：

> | 错误码 | 说明 | 严重程度 |
> |--------|------|----------|
> | ... | ... | ... |
>
> TraceId: `<headers.X-Trace-Id>`（可用于排查）

常见错误（401/403/500、session 失效、规格变更等）的排查方式见 `references/error-guide.md`。

---

## 动作 → 命令映射

### ACTION_SEARCH

```bash
utp catalog search --keyword "<用户本轮原始搜索词>" --search-type DEEP_SEARCH [--limit N]
```

- `keyword` 必须是用户本轮搜索词的逐字原文，由服务端 AI 语义搜索完整理解。**禁止任何改写**：不翻译、不纠错别字、不调语序、不同义替换、不扩写、不精简。无论简短还是长描述都一字不改直接传。
- `--search-type` 固定传 `DEEP_SEARCH`，使用 AI 语义搜索。

解析路径: `body.products[]` → id, title, price_range.min.amount, price_range.max.amount

### ACTION_PRODUCT

```bash
utp catalog product --id <product_id>
```

解析路径: `body.product` → title, id; `body.product.variants[]` → id(= spec_id), title, price.amount, options[].label

### ACTION_CART_ADD

```bash
utp cart add --product-id <product_id> --spec-id <spec_id> [--quantity <N>]
```

参数来源: product_id 从当前商品取，spec_id 从用户选择的规格序号对应的 variant.id 取。

### ACTION_CART_LIST

```bash
utp cart list
```

解析路径:
- `body.line_items[]` → id(cart_item_id), item.id(spec_id), item.title, item.product_id, item.options[].label, item.price, quantity, totals[0].amount
- `body.totals[0].amount` → 合计

### ACTION_CART_UPDATE

```bash
utp cart update --cart-item-id <id> --product-id <product_id> --quantity <N>
```

从存储的 line_items 按序号取 cart_item_id 和 product_id。

### ACTION_CART_REMOVE

```bash
utp cart remove --cart-item-id <id> --product-id <product_id>
```

从存储的 line_items 按序号取。

### ACTION_CHECKOUT（创建）

> **CLI 下结账通过逐项指定商品完成（`--item`）**，有规格的商品**必须**带 spec_id，否则服务端报错。spec_id 来源：**商品来自购物车时，直接取 `utp cart list` 返回对应 `line_item` 的 spec 字段**（购物车已透出规格，不必重查）；只有购物车里没有的新商品，才先对该商品走 ACTION_PRODUCT 取得 spec_id，再下单。
>
> 无论 CLI 还是 MCP，结账都通过 `items`/`--item` 逐项指定商品；“下单全部购物车”即把购物车所有商品行逐项列入。

多商品合单：
```bash
utp checkout create --item <product_id>:<spec_id>:<quantity> [--item ...]
```

单商品简写：
```bash
utp checkout create --product-id <product_id> --spec-id <spec_id> --quantity <N>
```

`--item` 格式：`product-id:quantity` 或 `product-id:spec-id:quantity`。

解析路径: `body.id`(checkout_id), `body.status`, `body.totals[0].amount`, `body.fulfillment.methods[].destinations[]`, `body.messages[]`

### ACTION_CHECKOUT（完成）

```bash
utp checkout complete --checkout-id <checkout_id>
```

解析路径: `body.status`, `body.orders[].id`, `body.totals[0].amount`, `body.fulfillment.methods[].destinations[].street_address`, `body.fulfillment.methods[].destinations[].first_name`

### ACTION_CHECKOUT_GET

```bash
utp checkout get --checkout-id <checkout_id>
```

### ACTION_CHECKOUT_CANCEL

```bash
utp checkout cancel --checkout-id <checkout_id>
```

### ACTION_LOOKUP

```bash
utp catalog lookup --ids <id1>,<id2>,...
```

---

## 前置条件命令

### Session 模型

每个 agent 会话使用独立 session，**不需要**检查或复用已有的活跃 session。每次进入购物流程直接 discover 目标 host 建立 session 即可。

### Discover

```bash
utp discover <host-url>
```

### Link（身份绑定）

```bash
utp link
```

默认浏览器模式，自动打开授权页面。最多重试 2 次（共 3 次尝试）。

**仅在真正下单（`checkout complete`）时才需要 link。** discover、catalog 搜索/查询、cart 加购、checkout create 全程都不需要买家身份，不要在这些环节催促用户绑定。只有用户确认下单、或某次操作返回 401/未登录时，才引导用户执行 link。

> **MCP 模式下已支持卡内登录**：下单/加购遇 401 时卡片会自动弹出扫码登录浮层（二维码 + 浏览器登录），用户主动要登录时可调 `utp_login` 打开独立登录卡，均无需终端。`utp link` 命令行仅作卡片环境不可用时的兜底。

---

## 全局标志

| 标志 | 说明 | 默认值 |
|------|------|--------|
| `--session-id` | 指定 session | 最近 session |
| `-o, --output` | 输出格式 | json |
| `--dry-run` | 仅打印带签名的 curl 命令 | false |
| `-v, --verbose` | 详细日志 | false |

---

## 命令参数速查

### catalog

| 命令 | 必填参数 | 可选参数 |
|------|----------|----------|
| `catalog search` | `--keyword`, `--search-type` | `--limit` |
| `catalog product` | `--id` | |
| `catalog lookup` | `--ids`（逗号分隔） | |

### cart

| 命令 | 必填参数 | 可选参数 |
|------|----------|----------|
| `cart list` | | `--cart-id`(默认1) |
| `cart add` | `--product-id` | `--spec-id`, `--quantity`(默认1) |
| `cart update` | `--cart-item-id`, `--product-id`, `--quantity` | `--spec-id` |
| `cart remove` | `--cart-item-id`, `--product-id` | |

### checkout

| 命令 | 必填参数 | 可选参数 |
|------|----------|----------|
| `checkout create` | `--product-id` 或 `--item`(可重复) | `--spec-id`, `--quantity`(默认1), `--currency`(默认CNY) |
| `checkout get` | `--checkout-id` | |
| `checkout update` | `--checkout-id` + (`--product-id` 或 `--item`) | `--spec-id`, `--quantity`, `--currency` |
| `checkout complete` | `--checkout-id` | |
| `checkout cancel` | `--checkout-id` | |

### 其他

| 命令 | 说明 |
|------|------|
| `discover <host>` | 发现商业体能力，建立 session |
| `link` | OAuth 2.1 PKCE 绑定买家身份 |
| `call <capability-id>` | 通用能力调用 |
