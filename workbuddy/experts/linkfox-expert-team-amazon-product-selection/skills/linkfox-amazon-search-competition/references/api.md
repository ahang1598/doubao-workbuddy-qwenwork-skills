# 前台搜索 6 段竞争格局分析 - API 参考

## 上游依赖

本 skill 调用 `linkfox-amazon-search`（`POST /amazon/search`）获取前台搜索数据。

## linkfox-amazon-search 参数

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| keyword | string | 是 | - | 搜索关键词（目标站点语言） |
| amazonDomain | string | 是 | amazon.com | 站点域名 |
| language | string | 否 | - | 语言代码 |
| sort | string | 否 | relevanceblender | 本 skill 固定 relevanceblender |
| page | integer | 否 | 1 | 本 skill 固定请求 page 1/2/3；**调用方必须保留页码** |

## 商品字段：文档 vs 实测

| 字段 | 文档类型 | 实测 | 本 skill 用法 |
|------|----------|------|----------------|
| asin | string | ≈100% | 去重主键 |
| title | string | ≈100% | 展示 |
| extractedPrice | float | ≈100% | **主用价格** |
| price | float | ≈100% | extractedPrice 缺失时回退 |
| currency | string | ≈100% | 展示 |
| rating | float | ≈99% | 评分分布 |
| ratings | integer | ≈99% | 评分数分布；新品清单筛选 |
| position | integer | ≈100% | **仅页内相对名次**；用于页内排序，不跨页比较 |
| sponsored | boolean | ≈100% | 去广告 |
| monthlySalesUnits | integer | 约 60%–90% | 有值用原值；**缺失记 50** |
| monthlySalesRevenue | **string**（如 `"284970.00"`） | 与 units 成对 | safe_float；缺失用 50×price 估算 |
| options | **string**（多为 `"See options"`） | 约 5%–10% | 非空 = 含变体（二值） |
| oldPrice / extractedOldPrice | float | 约 60% | 可选促销分析 |
| badges / offers / delivery | string | 不稳定 | 可选，不保证 |
| brand | string | **长期 0%** | **禁止依赖** |
| fulfillment | string | **长期 0%** | **禁止依赖** |
| sellerNation | string | **长期 0%** | **禁止依赖** |
| availableDate | string | **长期 0%** | **禁止依赖** |
| priceUnit / dimension / weight / tags | - | 长期 0% | 忽略 |

> `columns` 数组会声明 30+ 列，但 `products` 实例经常缺少 enrichment 字段。以 products 实测为准。

## 合并输入格式（给聚合脚本）

合并后的 JSON 应为数组，或带 `products` 键的对象。推荐每条在 Step 2 已写好：

```json
{
  "asin": "B0XXXX",
  "title": "...",
  "extractedPrice": 24.99,
  "rating": 4.5,
  "ratings": 7800,
  "monthlySalesUnits": 1000,
  "monthlySalesRevenue": "24990.00",
  "options": "See options",
  "sponsored": false,
  "page": 1,
  "page_position": 5,
  "organic_rank": 1,
  "units_imputed": false
}
```

若输入尚未重算 rank，脚本会在存在 `page` 字段时按 page + page_position 重算；若无 page，则仅按列表顺序编号并警告。

## 聚合脚本

```bash
python scripts/aggregate_competition.py <merged_products.json> [--inline] [--fixed-buckets] [--buckets <file.json|json>]
```

- 始终落盘到 `linkfox/<date>/<session>/data/linkfox-amazon-search-competition-<ts>.json`
- 响应 ≤ 8KB 全量打印；更大只打摘要；`--inline` 强制全量

## 计费

- 每次 linkfox-amazon-search：15 积分
- 本 skill 3 页：45 积分
- 聚合脚本：本地计算，不耗积分
