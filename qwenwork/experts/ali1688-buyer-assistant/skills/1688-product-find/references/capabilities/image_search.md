# 图片搜索后处理

## 职责

图片搜索 API 调用由 `ali1688-buyer` MCP 工具 `find_product` 完成；本命令只处理 MCP 返回结果。

## MCP 调用

```text
find_product(imageUrl="https://...jpg", pageSize=10, scoreLevel="high", tags="4306497")
```

本地图片的 base64 编码由客户端或 MCP 网关完成，Agent 不在 Python 脚本里读取图片或编码。

## Python 后处理

```bash
python3 cli.py image_search --image "https://...jpg" --mcp-result-file /tmp/find_product.json
```

也支持 stdin：

```bash
cat /tmp/find_product.json | python3 cli.py image_search --image "https://...jpg"
```

## 输出

直接展示脚本返回 JSON 中的 `markdown` 字段；后续导出使用 `data.data.similar_products`。
