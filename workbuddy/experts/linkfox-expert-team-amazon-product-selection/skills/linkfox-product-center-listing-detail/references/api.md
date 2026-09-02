# 商品库-Listing 详情 API 参考

本页为 `linkfox-product-center-listing-detail` 技能调用的底层接口规格。SKILL.md 面向"怎么用"，本文档面向"接口精确格式"。

## 接口说明

> 工具中文名：商品库-Listing 详情

按 `listingId` 拿到当前团队链接库里该 listing 的完整业务档案（文案 + 平台 + 状态 + 抓取数据 + 主副/A+图）。

## 调用规范

- **请求地址**：`${LINKFOX_TOOL_GATEWAY}/product-center/v1/skill/product/listing/{listingId}`，基础域名从环境变量 `LINKFOX_TOOL_GATEWAY` 读取。`{listingId}` 是 path variable，从入参 `params.listingId` 取值。
- **请求方式**：GET。无 query 参数、无 body。
- **认证方式**：Header `Authorization: <api_key>`，api_key 从环境变量 `LINKFOX_AGENT_API_KEY` 读取。
- **会话参数**：Query `agentSessionId=<session>`；脚本优先使用入参 `agentSessionId`，未传时自动取环境变量 `SESSION_ID`。

## 请求参数

| 参数 | 类型 | 必填 | 默认 | 位置 | 说明 |
|------|------|------|------|------|------|
| `listingId` | long | 是 | -- | path | 链接 ID。 |
| `offerSource` | integer | 是 | -- | query | 来源类型，用于会话关联。调用方按自身角色硬编码传入（10=Listing-Agent, 11=选品, 12=生图, 13=市场分析, 14=视频, 15=通用）。 |
| `agentSessionId` | string | 否 | `SESSION_ID` | query | Agent 会话 ID。 |

## 响应结构

顶层信封（`ResponseDto<T>`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 业务状态码：`200` 成功；其他见错误码表。 |
| `msg` | string | 业务消息。 |
| `traceId` | string | 后端 traceId。 |
| `data` | object | `SkillListingDto`。 |

`data`（`SkillListingDto`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `listingId` | string（Long） | 链接 ID。 |
| `skuId` | string（Long） | 所属 SKU。 |
| `productId` | string（Long） | 所属 SPU。 |
| `platform` | string | 平台（如 `AMAZON`）。 |
| `marketplace` | string | 站点（如 `US`）。 |
| `title` | string | 标题。 |
| `bulletPoints` | string | 五点描述（原文）。 |
| `bulletPointsTranslated` | string | 五点描述（译文）。 |
| `keywords` | string | 关键词。 |
| `sourceUrl` | string | 来源 URL。 |
| `sourceProductId` | string | 来源商品 ID（如 ASIN）。 |
| `isReference` | integer | 0=自有链接 1=参考链接。 |
| `offerSource` | integer | 来源类型枚举。 |
| `status` | integer | 链接整体状态（业务枚举）。 |
| `imageStatus` | integer | 图片状态：0=待做图 1=生成中 2=已完成。 |
| `linkingStatus` | integer | 与外部商品的绑定状态（业务枚举）。 |
| `createTime` | integer | 创建时间，unix 秒。 |
| `updateTime` | integer | 更新时间，unix 秒。 |
| `price` | string | 价格（外部抓取，可能为空）。 |
| `currency` | string | 货币。 |
| `rating` | string | 评分。 |
| `reviewCount` | string | 评论数。 |
| `salesVolume` | string | 销量。 |
| `brandName` | string | 品牌（外部抓取）。 |
| `sellerName` | string | 卖家（外部抓取）。 |
| `mainImages` | array[Image] | 主副图列表。 |
| `aplusImages` | array[Image] | A+ 图列表。 |

`mainImages[]` / `aplusImages[]`（`SkillImageDto`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `imageId` | string（Long） | 图片 ID。 |
| `imageUrl` | string | 原图 URL。 |
| `thumbUrl` | string | 缩略图 URL。 |
| `imageType` | integer | 图片类型（业务枚举）。 |
| `isPicked` | integer | 是否被挑选：0=未挑 1=已挑。 |

## 错误码

| code | 含义 | 处理建议 |
|------|------|----------|
| 200 | 成功 | 解析 `data`。 |
| 401 | 未授权 | 检查 API Key。 |
| 403 | 链接不属于当前团队 | 友好提示用户该 listing 不在自家库。 |
| 404 | 链接不存在 | 友好提示"未找到该链接"。 |
| 500 | 服务器内部错误 | 拿 `traceId` 找运维。 |

## 计费

不计费。

## curl 示例

```bash
curl "$LINKFOX_TOOL_GATEWAY/product-center/v1/skill/product/listing/67890" \
  -H "Authorization: $LINKFOX_AGENT_API_KEY"
```

---

## Feedback API

- **POST** `https://skill-api.linkfox.com/api/v1/public/feedback`
- **Content-Type:** `application/json`

```json
{
  "skillName": "linkfox-product-center-listing-detail",
  "sentiment": "POSITIVE",
  "category": "OTHER",
  "content": "Results were accurate."
}
```
