# 商品比价后处理

## 职责

比价候选召回由 `ali1688-buyer` MCP 工具 `find_product` 完成；本命令保留原有 Python 三维度选品和 Markdown 对比表逻辑。

## MCP 调用

```text
find_product(imageUrl="https://...jpg", pageSize=20, scoreLevel="high", tags="4306497")
```

比价模式固定取 20 条候选。默认不传 `sortType`，保持相关性/相似度召回。

## Python 后处理

```bash
python3 cli.py compare --image "https://...jpg" --mcp-result-file /tmp/find_product.json
```

也支持 stdin：

```bash
cat /tmp/find_product.json | python3 cli.py compare --image "https://...jpg"
```

## 选品逻辑

Python 脚本会独立选择：

| 维度 | 规则 | 标签 |
|------|------|------|
| 销量最高 | 按 `sold_count` 降序，缺失视为 0 | `销量最高` |
| 价格最低 | 排除无价格商品，按 `price` 升序 | `价格最低` |
| 综合最优 | 按 `yx_index` 降序，缺失视为 0 | `综合最优` |

同一商品命中多个维度时合并标签，例如 `销量最高 且 价格最低`。Agent 不得自行重算、补齐或改写结果。

## 输出

直接展示脚本返回 JSON 中的 `markdown` 字段；后续导出使用 `data.data.compare_products`。
