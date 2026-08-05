# 文本搜索后处理

## 职责

API 调用由 `ali1688-buyer` MCP 工具 `find_product` 完成；本命令只处理 MCP 返回结果。

## MCP 调用

```text
find_product(query="黑色连帽卫衣", pageSize=10, scoreLevel="high", tags="4306497")
```

## Python 后处理

```bash
python3 cli.py text_search --query "黑色连帽卫衣" --mcp-result-file /tmp/find_product.json
```

也支持 stdin：

```bash
cat /tmp/find_product.json | python3 cli.py text_search --query "黑色连帽卫衣"
```

## 输出

直接展示脚本返回 JSON 中的 `markdown` 字段；后续导出使用 `data.data.similar_products`。
