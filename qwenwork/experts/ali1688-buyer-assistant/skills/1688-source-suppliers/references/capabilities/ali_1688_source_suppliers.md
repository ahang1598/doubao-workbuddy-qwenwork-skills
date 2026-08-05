# 1688 供应商查询后处理

## 职责

供应商查询 API 调用由 `ali1688-buyer` MCP 工具 `1688_source_suppliers` 完成；本命令只处理 MCP 返回结果。

## MCP 调用

```text
1688_source_suppliers(query="不锈钢保温杯供应商")
```

## Python 后处理

```bash
python3 cli.py ali_1688_source_suppliers \
  --query "不锈钢保温杯供应商" \
  --mcp-result-file /tmp/source_suppliers.json
```

也支持 stdin：

```bash
cat /tmp/source_suppliers.json | python3 cli.py ali_1688_source_suppliers -q "不锈钢保温杯供应商"
```

## 后处理逻辑

Python 脚本保留原有逻辑：

- 解开 MCP / JSON-RPC 包装。
- 兼容 `originResponses`、`data.result.originResponses`、`data.result.model`。
- 查找 `currentPhase == "RETRIEVAL"` 的数据。
- 从 `responseData.data` 提取供应商列表。
- 解析 `extInfos` 中的 JSON 字符串数组。
- 过滤缺少公司名称、合作方式或服务类型的记录。
- 生成 Markdown 供应商表格。

## 输出

直接展示脚本返回 JSON 中的 `markdown` 字段；后续分析使用 `data.factories`。

## 禁止

- 禁止提示用户配置 AK。
- 禁止调用浏览器、网页搜索或旧 HTTP 脚本降级。
- 禁止由 Agent 自行解析、筛选、格式化 MCP 原始供应商数据。
