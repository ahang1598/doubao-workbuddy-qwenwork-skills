# 商品库-变体下的链接列表 API 参考

本页为 `linkfox-product-center-variant-listings` 技能调用的底层接口规格。SKILL.md 面向"怎么用"，本文档面向"接口精确格式"。

## 接口说明

> 工具中文名：商品库-变体下的链接列表

按 `skuId` 分页拉当前团队链接库里挂在这个变体下的链接卡片（含 isReference 区分）。

## 调用规范

- **请求地址**：`${LINKFOX_TOOL_GATEWAY}/product-center/v1/skill/product/variant/{skuId}/listings`，基础域名从环境变量 `LINKFOX_TOOL_GATEWAY` 读取。`{skuId}` 是 path variable。
- **请求方式**：GET。其他参数走 query string。
- **认证方式**：Header `Authorization: <api_key>`。
- **会话参数**：Query `agentSessionId=<session>`；脚本优先使用入参 `agentSessionId`，未传时自动取环境变量 `SESSION_ID`。

## 请求参数

| 参数 | 类型 | 必填 | 默认 | 位置 | 说明 |
|------|------|------|------|------|------|
| `skuId` | long | 是 | -- | path | 变体 SKU ID。 |
| `offerSource` | integer | 是 | -- | query | 来源类型，用于会话关联。调用方按自身角色硬编码传入（10=Listing-Agent, 11=选品, 12=生图, 13=市场分析, 14=视频, 15=通用）。 |
| `agentSessionId` | string | 否 | `SESSION_ID` | query | Agent 会话 ID。 |
| `platform` | string | 否 | -- | query | 平台筛选（如 `AMAZON`）。 |
| `marketplace` | string | 否 | -- | query | 站点筛选（如 `US`）。 |
| `isReference` | integer | 否 | -- | query | `0`=自有链接 `1`=参考链接，不传不过滤。 |
| `status` | integer | 否 | -- | query | 链接状态（业务枚举）。 |
| `pageNum` | integer | 否 | `1` | query | 页码，从 1 开始。 |
| `pageSize` | integer | 否 | `20` | query | 每页条数。 |

## 响应结构

顶层信封（`ResponseDto<T>`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | `200` 成功；其他见错误码表。 |
| `msg` | string | 业务消息。 |
| `traceId` | string | 后端 traceId。 |
| `data` | object | `PageResultVo<SkillListingCardDto>`。 |

`data`（`PageResultVo<SkillListingCardDto>`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | long | 满足条件的总数。 |
| `hasMore` | boolean | 是否还有下一页。 |
| `list` | array[ListingCard] | 链接卡片列表。 |

`list[]`（`SkillListingCardDto`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `listingId` | string（Long） | 链接 ID。 |
| `platform` | string | 平台。 |
| `marketplace` | string | 站点。 |
| `title` | string | 标题。 |
| `bulletPoints` | string | 五点描述。 |
| `keywords` | string | 关键词JSON。 |
| `isReference` | integer | 0=自有 1=参考。 |
| `status` | integer | 链接整体状态。 |
| `sourceUrl` | string | 来源 URL。 |
| `createTime` | integer | 创建时间，unix 秒。 |
| `updateTime` | integer | 更新时间，unix 秒。 |

## 错误码

| code | 含义 | 处理建议 |
|------|------|----------|
| 200 | 成功 | 解析 `data.list`。 |
| 401 | 未授权 | 检查 API Key。 |
| 403 | 变体不属于当前团队 | 友好提示。 |
| 404 | 变体不存在 | 友好提示。 |
| 500 | 服务器内部错误 | 拿 traceId 找运维。 |

## 计费

不计费。

## curl 示例

```bash
# 1) 首页
curl "$LINKFOX_TOOL_GATEWAY/product-center/v1/skill/product/variant/12345/listings" \
  -H "Authorization: $LINKFOX_AGENT_API_KEY"

# 2) 只看亚马逊美国站自有链接
curl "$LINKFOX_TOOL_GATEWAY/product-center/v1/skill/product/variant/12345/listings?platform=AMAZON&marketplace=US&isReference=0" \
  -H "Authorization: $LINKFOX_AGENT_API_KEY"
```

---

## Feedback API

- **POST** `https://skill-api.linkfox.com/api/v1/public/feedback`
- **Content-Type:** `application/json`

```json
{
  "skillName": "linkfox-product-center-variant-listings",
  "sentiment": "POSITIVE",
  "category": "OTHER",
  "content": "Results were accurate."
}
```
