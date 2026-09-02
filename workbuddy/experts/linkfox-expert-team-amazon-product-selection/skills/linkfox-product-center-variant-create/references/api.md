---
# 创建变体 API

## 接口说明
创建变体（SKU），支持新建商品+初始变体或为已有商品追加变体。

## 调用规范
- **URL**: `${LINKFOX_TOOL_GATEWAY}/product-center/v1/skill/product/variant/create`
- **Method**: POST
- **Authentication**: Header `Authorization: <api_key>`
- **Session**: Query param `agentSessionId`（取自环境变量 SESSION_ID）

## 请求参数（JSON Body）

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| productId | Long | 否 | null | 空=新建商品；有值=追加变体 |
| productName | String | 条件 | — | productId 为空时必填，最大 500 字符 |
| skuName | String | 否 | — | 变体名称 |
| brand | String | 否 | — | 品牌，最大 200 字符 |
| category | String | 否 | — | 类目路径，最大 500 字符 |
| targetPerson | String | 否 | — | 目标人群，最大 500 字符 |
| material | String | 否 | — | 材质描述，最大 2500 字符 |
| sellingPoints | String | 否 | — | 卖点描述，最大 2500 字符 |
| productType | Integer | 否 | 1 | 1=商品，2=服装 |
| offerSource | Integer | 是 | — | 来源类型，调用方按自身角色硬编码传入（10=Listing-Agent, 11=选品, 12=生图, 13=市场分析, 14=视频, 15=通用）。**同时走 query + body**：query 经拦截器写入会话绑定 agentType，body 写入 `sku.offerSource`；脚本已自动双写 |
| images | List&lt;String&gt; | 是 | — | 原图 URL，1-30 张 |
| videos | List&lt;String&gt; | 否 | — | 视频 URL，最多 5 条 |

## 响应结构

```json
{
  "code": 200,
  "msg": "success",
  "traceId": "xxx",
  "data": {
    "productId": "123456",
    "skuId": "789012",
    "listingId": null
  }
}
```

## 错误码

| code | 含义 | 处理建议 |
|------|------|----------|
| 200 | 成功 | — |
| 400 | 参数校验失败 | 检查 images 非空、productName 条件 |
| 401 | 未授权 | 检查 API Key |
| 403 | 商品不属于当前团队 | 确认 productId 正确 |
| 404 | 商品不存在 | 确认 productId 有效 |
| 500 | 服务端错误 | 重试或联系管理员 |

## 计费
不计费。

## curl 示例
```bash
curl -X POST "${LINKFOX_TOOL_GATEWAY}/product-center/v1/skill/product/variant/create?agentSessionId=${SESSION_ID}" \
  -H "Authorization: ${LINKFOX_AGENT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"productName":"夏季运动鞋","images":["https://example.com/img1.jpg"]}'
```
