# 亚马逊类目节点查询 API 参考

## 接口一：查子类目

- **请求地址**：`${LINKFOX_TOOL_GATEWAY}/amazon/nodes/lookup`
- **请求方式**：POST，Content-Type: application/json
- **认证方式**：Header `Authorization: <api_key>`，api_key 从环境变量 `LINKFOX_AGENT_API_KEY` 或 `LINKFOXAGENT_API_KEY` 读取（如未配置，提示用户前往 https://skill.linkfox.com/linkfoxskills/guide.htm 申请）

### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| marketId | string | 否 | `"1"` | 亚马逊站点 ID，见下方站点对照表 |
| nodeId | string | 否 | 空（根节点 -1） | 父节点 ID；为空时默认查根节点 |
| table | string | 否 | `"bsr_sales_nearly"` | 查询月份；`bsr_sales_nearly` 表示当前月近期数据，也可传历史月份格式如 `"202508"` |

### 站点对照表（marketId）

| marketId | 站点 |
|----------|------|
| 1 | 亚马逊-美国站 |
| 3 | 亚马逊-英国站 |
| 4 | 亚马逊-德国站 |
| 5 | 亚马逊-法国站 |
| 6 | 亚马逊-日本站 |
| 7 | 亚马逊-加拿大站 |
| 35691 | 亚马逊-意大利站 |
| 44551 | 亚马逊-西班牙站 |
| 44571 | 亚马逊-印度站 |
| 771770 | 亚马逊-墨西哥站 |

### 响应结构

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 响应状态码：`OK`-成功，`ERROR`-失败 |
| message | string | 响应消息 |
| size | integer | 返回数据条数 |
| costToken | integer | 消耗 token（默认 100） |
| items | array | 类目节点列表，详见 items 字段说明 |

**items 元素字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| nodeId | string | 节点 ID |
| label | string | 节点完整标签（含路径） |
| nodeLabel | string | 节点标签（英文名） |
| alias | string | 别名 |
| products | integer | 该节点下的商品数量 |
| nodeLabelLocale | string | 节点标签本地化名称 |
| nodeLabelPathLocale | string | 节点标签路径本地化（完整路径） |
| children | integer | 子节点数量 |
| parentId | string | 父节点 ID |

### curl 示例

```bash
# 查美国站根类目
curl -X POST https://tool-gateway.linkfox.com/amazon/nodes/lookup \
  -H "Authorization: $LINKFOXAGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"marketId": "1"}'

# 查 Home & Kitchen 子类目
curl -X POST https://tool-gateway.linkfox.com/amazon/nodes/lookup \
  -H "Authorization: $LINKFOXAGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"marketId": "1", "nodeId": "1055398"}'

# 查 2025 年 8 月历史数据的子类目
curl -X POST https://tool-gateway.linkfox.com/amazon/nodes/lookup \
  -H "Authorization: $LINKFOXAGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"marketId": "1", "nodeId": "2619525011", "table": "202508"}'
```

---

## 接口二：模糊查询类目

- **请求地址**：`${LINKFOX_TOOL_GATEWAY}/amazon/nodes/lookup/like`
- **请求方式**：POST，Content-Type: application/json
- **认证方式**：同上

### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| marketId | string | 否 | `"1"` | 亚马逊站点 ID，见上方站点对照表 |
| nodeId | string | 否 | -- | 节点 ID，用于精确过滤（可选） |
| nodeLabel | string | 否 | -- | 类目名称关键词，LIKE 模糊匹配，最大 1000 字符 |

### 响应结构

与接口一相同，返回 `code`、`message`、`size`、`costToken`、`items`，items 元素字段也一致。

### curl 示例

```bash
# 模糊搜索名称含 Health 的类目
curl -X POST https://tool-gateway.linkfox.com/amazon/nodes/lookup/like \
  -H "Authorization: $LINKFOXAGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"marketId": "1", "nodeLabel": "Health"}'

# 精确 nodeId + 名称过滤
curl -X POST https://tool-gateway.linkfox.com/amazon/nodes/lookup/like \
  -H "Authorization: $LINKFOXAGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"marketId": "1", "nodeId": "2619525011", "nodeLabel": "Household"}'
```

---

## 错误码

正常情况下，HTTP 状态码均为 200，业务成功与否通过响应体 `code` 字段区分（`OK` 表示成功，`ERROR` 表示失败）。HTTP 401 时表示认证失败。

| code | 含义 | 处理建议 |
|------|------|----------|
| OK | 成功 | 正常解析 `items` 字段 |
| ERROR | 业务异常 | 参考 `message` 字段获取错误原因 |
| HTTP 401 | 认证失败 | 检查请求头 `Authorization` 是否正确携带 API Key |

---

## Feedback API

> 此端点与上方工具 API 不同，不要混用 base URL。

- **POST** `https://skill-api.linkfox.com/api/v1/public/feedback`
- **Content-Type:** `application/json`

```json
{
  "skillName": "linkfox-amazon-category-lookup",
  "sentiment": "POSITIVE",
  "category": "OTHER",
  "content": "Results were accurate, user was satisfied."
}
```

**字段规则：**
- `skillName`：固定使用本 skill 的 `name` 值
- `sentiment`：`POSITIVE`（好评）、`NEUTRAL`（中性建议）、`NEGATIVE`（投诉/报错）三选一
- `category`：`BUG`、`COMPLAINT`、`SUGGESTION`、`OTHER` 四选一
- `content`：描述用户说了什么、实际发生了什么、为什么是问题或好评
