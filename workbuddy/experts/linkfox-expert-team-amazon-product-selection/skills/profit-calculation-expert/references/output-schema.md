# 产物输出契约

## 1. 路径协议

运行期落盘走 `scripts/linkfox_paths.py`：

| 类型 | 函数 | 落点 |
|------|------|------|
| 中间数据 | `resolve_data_path(slug, ts)` | 会话目录 data 子目录 |
| 最终报告 | `resolve_report_path(slug, ts, ext)` | 会话目录 reports 子目录 |

## 2. 传输层

最终 HTML 报告由 `linkfox-report-generator` 生成并落盘。中间 JSON 通过 stdout `Saved full response:` 行通知。

## 3. 载荷层

S4 净利润数据 JSON 结构：

```json
[
  {
    "asin": "B0XXXXXXXX",
    "title": "商品标题",
    "brand": "品牌",
    "category": "Nightgowns & Sleepshirts",
    "price": 19.99,
    "bsr": 20340,
    "rating": 4.8,
    "fba_fees": 3.82,
    "referral_fee": 2.00,
    "ad_cost": 2.49,
    "cogs": 3.97,
    "refund_admin_fee": 0.40,
    "disposal_fee": 0.50,
    "single_return_loss": 8.69,
    "expected_return_loss": 0.57,
    "storage_fee": 0.12,
    "inbound_placement_fee": 0.40,
    "fba_head_cost": 3.00,
    "total_cost": 12.48,
    "net_profit": 7.51,
    "net_margin": 37.6,
    "return_rate_pct": 6.58,
    "niche_tacos": 12.43,
    "cost_1688": 0.97,
    "products_1688": [
      {
        "offerId": "123456789",
        "title": "1688标题",
        "price_cny": 7.00,
        "price_usd": 0.97,
        "salesQuantity": 8799,
        "net_profit": 7.51,
        "net_margin": 37.6
      }
    ]
  }
]
```
