# 商品库-创建 Listing API 参考

本页为 `linkfox-product-center-listing-create` 技能调用的底层接口规格。SKILL.md 面向"怎么用"，本文档面向"接口精确格式"。

## 接口说明

> 工具中文名：商品库-创建 Listing

为已有 SKU 加一条新的上架链接（自有或参考），返回 `listingId`。

## 调用规范

- **请求地址**：`${LINKFOX_TOOL_GATEWAY}/product-center/v1/skill/product/listing/create`，基础域名从环境变量 `LINKFOX_TOOL_GATEWAY` 读取。
- **请求方式**：POST，Content-Type: application/json。
- **认证方式**：Header `Authorization: <api_key>`。
- **会话参数**：Query `agentSessionId=<session>`；脚本优先使用入参 `agentSessionId`，未传时自动取环境变量 `SESSION_ID`。

## 请求参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `skuId` | long | 否 | -- | 目标 SKU ID，必须属于当前团队。空则自动创建商品+SKU。 |
| `productName` | string | 条件必填 | -- | skuId为空时必填，商品名称。 |
| `productImages` | List of String | 条件必填 | -- | skuId为空时必填，SKU原图。 |
| `productVideos` | List of String | 否 | -- | skuId为空时可选，SKU视频URL列表，最多5条。 |
| `platform` | string | 是 | -- | 平台，如 `AMAZON`。 |
| `marketplace` | string | 是 | -- | 站点，如 `US` / `UK` / `DE` 等。 |
| `isReference` | integer | 否 | -- | `0`=自有链接 `1`=参考链接，默认按业务约定。 |
| `sourceUrl` | string | 否 | -- | 已知商品页 URL（参考链接场景常用）。 |
| `title` | string | 否 | -- | listing标题。 |
| `bulletPoints` | string | 否 | -- | 五点描述。 |
| `keywords` | string | 否 | -- | 关键词JSON。 |
| `imageUrls` | List of String | 否 | -- | listing图片URL列表。 |
| `imageType` | integer | 否 | 1 | 1=主副图(默认)，2=A+图，99=其他。 |
| `offerSource` | integer | 是 | -- | **走 query**（经拦截器用于会话来源绑定 agentType）。调用方按自身角色硬编码传入（10=Listing-Agent, 11=选品, 12=生图, 13=市场分析, 14=视频, 15=通用）。注意：listing 记录自身的 offerSource 后端硬编码为 Agent，此值不影响记录。 |
| `agentSessionId` | string | 否 | `SESSION_ID` | Agent 会话 ID，脚本会作为 query 参数透传。 |

## 响应结构

顶层信封（`ResponseDto<T>`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | `200` 成功；其他见错误码表。 |
| `msg` | string | 业务消息。 |
| `traceId` | string | 后端 traceId。 |
| `data` | object | `SkillCreateResultDto`。 |

`data`（`SkillCreateResultDto`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `productId` | string（Long） | SKU 所属 SPU ID。 |
| `skuId` | string（Long） | 入参的 SKU ID（回显）。 |
| `listingId` | string（Long） | 新创建的 listing ID。 |

## 错误码

| code | 含义 | 处理建议 |
|------|------|----------|
| 200 | 成功 | 解析 `data.listingId`。 |
| 400 | 参数校验失败 | 看 `msg`，引导用户改入参。 |
| 401 | 未授权 | 检查 API Key。 |
| 403 | 目标 SKU 不属于当前团队 | 友好提示。 |
| 404 | SKU 不存在 | 友好提示。 |
| 500 | 服务器内部错误 | 拿 traceId 找运维。 |

## 计费

不计费。

## curl 示例

```bash
# 模式一：已有 SKU 创建 listing
curl -X POST "$LINKFOX_TOOL_GATEWAY/product-center/v1/skill/product/listing/create" \
  -H "Authorization: $LINKFOX_AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"skuId":12345,"platform":"AMAZON","marketplace":"US","isReference":0}'

# 模式二：不选商品自动创建 SKU 再挂载
curl -X POST "$LINKFOX_TOOL_GATEWAY/product-center/v1/skill/product/listing/create" \
  -H "Authorization: $LINKFOX_AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"productName":"夏季透气男士T恤","productImages":["https://img.example.com/sku-main.jpg"],"productVideos":["https://img.example.com/video.mp4"],"platform":"AMAZON","marketplace":"US","isReference":0}'

# 一次性创建并填写内容
curl -X POST "$LINKFOX_TOOL_GATEWAY/product-center/v1/skill/product/listing/create" \
  -H "Authorization: $LINKFOX_AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"skuId":12345,"platform":"AMAZON","marketplace":"US","isReference":0,"title":"Mens Cotton T-Shirt","bulletPoints":"point1","keywords":"{\"core\":[\"t-shirt\"],\"title\":[\"mens tee\"],\"bullet\":[\"breathable\"],\"backend\":[\"cotton top\"]}","imageUrls":["https://img.example.com/main.jpg"],"imageType":1}'
```

---

## Feedback API

- **POST** `https://skill-api.linkfox.com/api/v1/public/feedback`
- **Content-Type:** `application/json`

```json
{
  "skillName": "linkfox-product-center-listing-create",
  "sentiment": "POSITIVE",
  "category": "OTHER",
  "content": "Created successfully."
}
```
