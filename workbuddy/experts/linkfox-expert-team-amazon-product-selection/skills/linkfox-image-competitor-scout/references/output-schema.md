# 输出契约（Output Schema）

最终交付是一个 `skill-output` envelope，`subject=product_list`，`component=ProductListRenderer`。
契约内联于此，运行时无需引用外部 skill。

## 顶层 envelope

```json
{
  "type": "skill-output",
  "skill": "linkfox-image-competitor-scout",
  "version": "v1",
  "id": "product-list-<YYYYMMDD>",
  "subject": "product_list",
  "label": "多平台竞品 · <date> · amazon/walmart/tiktok/ebay/ozon",
  "icon": "📦",
  "component": "ProductListRenderer",
  "props": {
    "summary": "跨 N 个平台抓取：amazon 10 条；walmart 10 条；…（每平台按销量 Top）。",
    "data": {
      "type": "productList",
      "total": 50,
      "products": [ /* 每条带 platform 标记，见下 */ ],
      "platformColumns": { /* 各平台列顺序，见下 */ }
    }
  },
  "data_sources": [ {"tool": "..."} ],
  "caveats": [ "..." ]
}
```

必填顶层字段：`type / skill / version / id / subject / label / component`。
`(subject, component)` 必须为 `(product_list, ProductListRenderer)`。

## 按平台自适应列（核心设计）

`props.data.platformColumns` 给出每个平台的列顺序；`products` 内每条只含其平台的字段（**抓不到的列不写**，前端按 platformColumns 渲染对应分组）。

```json
"platformColumns": {
  "amazon":  ["imageUrl","title","site","asin","price","category","bsr","unitsSold","revenue","fulfillment","weight","dimensions"],
  "walmart": ["imageUrl","title","site","itemId","price","category","unitsSold","revenue","fulfillment"],
  "tiktok":  ["imageUrl","title","site","itemId","price","category","unitsSold","revenue"],
  "ebay":    ["imageUrl","title","site","itemId","price","soldQuantity","fulfillment","seller"],
  "ozon":    ["imageUrl","title","itemId","price","category","unitsSold","revenue","rating"]
}
```

## ProductItem 字段（并集，按平台取子集）

| 字段 | 类型 | 含义 | 哪些平台有 |
|------|------|------|-----------|
| `platform` | string | amazon/walmart/tiktok/ebay/ozon | 全部（必有） |
| `site` | string | 站点/区域 | amazon/walmart/tiktok/ebay |
| `asin` | string | ASIN | amazon |
| `itemId` | string | 平台商品 ID（ItemId/productId/SKU） | walmart/tiktok/ebay/ozon |
| `imageUrl` | string | 主图 | 全部 |
| `title` | string | 标题 | 全部 |
| `price` | number | 价格（配合 currency） | 全部 |
| `currency` | string | 币种 | 全部 |
| `category` | string | 品类（叶子节点） | amazon/walmart/tiktok/ozon |
| `bsr` | number | BSR（越小越好） | amazon |
| `unitsSold` | number | 销量（口径见下） | amazon/walmart/tiktok/ozon |
| `soldQuantity` | number | 历史已售数量 | ebay |
| `revenue` | number | 销售额（TikTok 为 GMV） | amazon/walmart/tiktok/ozon |
| `fulfillment` | string | 配送方式 | amazon/walmart/ebay |
| `weight` | string | 重量 | amazon |
| `dimensions` | string | 尺寸 | amazon |
| `rating` | number | 评分（0~5） | ozon |
| `seller` | string | 卖家 | ebay |

### 单位 / 精度
- `price` / `revenue`：纯数值，不带货币符号（靠 `currency`）。
- `bsr`：整数，越小越好；无则不写。
- 销量口径不一：Amazon=Keepa 月销估算、Walmart/Ozon=统计期销量、TikTok=累计销量、eBay=历史已售。

### 排序与条数
- 按 `unitsSold`（eBay 按 `soldQuantity`）降序，取 Top `top_n`（默认 10）。
- 平台、站点目前均为**单选**：每次运行只产出一个平台的列表（脚本仍支持多平台合并，单选为运行时约束）。
- 缺销量的条目排末尾。

## 常见错法
- ❌ 产品塞 envelope 顶层 → 必须放 `props.data.products`。
- ❌ 给抓不到的列填 `"N/A"` → 直接不写该字段。
- ❌ 自己拼 HTML → 报告交 `linkfox-report-generator`。
- ❌ `version: 1` → 必须 `"v1"`。
