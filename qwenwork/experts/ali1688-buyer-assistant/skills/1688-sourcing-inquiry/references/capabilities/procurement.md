# 采购询盘后处理

## 职责

采购询盘 API 调用由 `ali1688-buyer` MCP 工具 `1688_procurement_digital_human_tool` 完成；本命令只处理 MCP 返回结果。

## MCP 调用

```text
1688_procurement_digital_human_tool(
  offerName="衣服",
  count="10",
  demand="价格便宜"
)
```

## Python 后处理

```bash
python3 cli.py procurement \
  --offerName "衣服" \
  --count "10" \
  --demand "价格便宜" \
  --mcp-result-file /tmp/procurement.json
```

也支持 stdin：

```bash
cat /tmp/procurement.json | python3 cli.py procurement -n "衣服" -c "10" -d "价格便宜"
```

## 后处理逻辑

Python 脚本保留原有逻辑：

- 校验 `offerName` / `count` / `demand`。
- 校验 `count` 为纯数字。
- 解开 MCP / JSON-RPC 包装。
- 识别 MCP 工具失败返回并输出标准错误。
- 生成稳定成功 Markdown。

## 输出

直接展示脚本返回 JSON 中的 `markdown` 字段；原始 MCP 返回保存在 `data.data.raw`。

## 禁止

- 禁止提示用户配置 AK。
- 禁止调用浏览器、网页搜索或旧 HTTP 脚本降级。
- 禁止由 Agent 自行改写 MCP 原始返回为最终结果。
