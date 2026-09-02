# 更新 Listing API

## 接口说明
统一入口更新 listing 的文案和追加图片。

## 调用规范
- **URL**: `${LINKFOX_TOOL_GATEWAY}/product-center/v1/skill/product/listing/{listingId}/update`
- **Method**: POST
- **Authentication**: Header `Authorization: <api_key>`
- **Session**: Query param `agentSessionId`（取自环境变量 SESSION_ID）

## 请求参数

### 路径参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| listingId | Long | 是 | 目标 listing ID |

### JSON Body

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| title | String | 否 | — | 标题，最大 1000 字符 |
| bulletPoints | String | 否 | — | 五点描述，最大 5000 字符 |
| keywords | String | 否 | — | 关键词 JSON 字符串，最大 5000 字符 |
| appendImages | List<String> | 否 | — | 追加图片 URL 列表 |
| imageType | Integer | 否 | 1 | 图片类型：1=主副图，2=A+图，99=其他 |
| offerSource | Integer | 是 | — | **走 query 而非 body**（经拦截器用于会话来源绑定 agentType），调用方按自身角色硬编码传入（10=Listing-Agent, 11=选品, 12=生图, 13=市场分析, 14=视频, 15=通用） |

所有 body 字段可选但至少传一个有效值（offerSource 为 query 参数，必传）。

## 响应结构

```json
{
  "code": 200,
  "msg": "success",
  "traceId": "xxx",
  "data": null
}
```

## 错误码

| code | 含义 | 处理建议 |
|------|------|----------|
| 200 | 成功 | — |
| 400 | 参数校验失败 | 检查至少传了一个有效字段 |
| 401 | 未授权 | 检查 API Key |
| 403 | listing 不属于当前团队 | 确认 listingId 正确 |
| 404 | listing 不存在 | 确认 listingId 有效 |
| 500 | 服务端错误 | 重试或联系管理员 |

## 计费
不计费。

## curl 示例
```bash
curl -X POST "${LINKFOX_TOOL_GATEWAY}/product-center/v1/skill/product/listing/123456/update?agentSessionId=${SESSION_ID}" \
  -H "Authorization: ${LINKFOX_AGENT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title","bulletPoints":"Point 1\nPoint 2"}'
```
