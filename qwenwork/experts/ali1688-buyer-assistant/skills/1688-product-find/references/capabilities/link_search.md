# 链接找同款后处理

## 职责

链接解析和商品详情查询由 Agent + `ali1688-buyer` MCP 完成；本命令只处理最终 `find_product` 返回结果。

## MCP 调用

1. 1688 链接或纯数字 ID：提取 `offerId`。
2. 调用 `offer_query_for_trade(offerId=...)` 获取 `image`。
3. 调用 `find_product(imageUrl=image, pageSize=10, scoreLevel="high", tags="4306497")`。

淘宝/天猫链接不能自动提取主图时，引导用户提供图片 URL 后调用 `find_product`。

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
