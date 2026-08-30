# 链接找同款后处理

## 职责

链接解析和商品详情查询由 Agent + `ali1688-buyer` MCP 完成；本命令只处理最终 `find_product` 返回结果。

## MCP 调用

1. 1688 链接或纯数字 ID：用 WebFetch 抓取商品页面（`https://detail.1688.com/offer/{offerId}.html`），从 HTML 中提取主图 URL（`cbu01.alicdn.com` 域名的 `<img>` 标签）。
2. 调用 `find_product(imageUrl=主图URL, pageSize=10, scoreLevel="high", tags="4306497")`。

淘宝/天猫链接无法自动提取主图时，引导用户提供图片 URL 后调用 `find_product`。

## Python 后处理

```bash
python3 cli.py link_search \
  --url "https://detail.1688.com/offer/123456.html" \
  --image "https://...jpg" \
  --mcp-result-file /tmp/find_product.json
```

也支持 stdin：

```bash
cat /tmp/find_product.json | python3 cli.py link_search --url "原始链接" --image "主图URL"
```

## 输出

直接展示脚本返回 JSON 中的 `markdown` 字段；后续导出使用 `data.data.similar_products`。
