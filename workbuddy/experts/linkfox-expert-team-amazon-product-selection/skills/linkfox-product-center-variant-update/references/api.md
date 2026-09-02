# 商品库-更新变体 API 参考

本页为 `linkfox-product-center-variant-update` 技能调用的底层接口规格。SKILL.md 面向"怎么用"，本文档面向"接口精确格式"。

## 接口说明

> 工具中文名：商品库-更新变体

按 skuId 部分更新 SKU 的业务字段（PATCH 语义）。

## 调用规范

- **请求地址**：`${LINKFOX_TOOL_GATEWAY}/product-center/v1/skill/product/variant/{skuId}/update`，`{skuId}` 是 path variable。
- **请求方式**：POST，Content-Type: application/json，body 为 JSON。
- **认证方式**：Header `Authorization: <api_key>`。
- **会话参数**：Query `agentSessionId=<session>`；脚本优先使用入参 `agentSessionId`，未传时自动取环境变量 `SESSION_ID`。

## 请求参数

| 参数 | 类型 | 必填 | 默认 | 位置 | 说明 |
|------|------|------|------|------|------|
| `skuId` | long | 是 | -- | path | 变体 SKU ID。 |
| `agentSessionId` | string | 否 | `SESSION_ID` | query | Agent 会话 ID。 |
| `offerSource` | integer | 是 | -- | query | 来源类型，经拦截器用于会话来源绑定 agentType。调用方按自身角色硬编码传入（10=Listing-Agent, 11=选品, 12=生图, 13=市场分析, 14=视频, 15=通用）。 |
| `skuName` | string | 否 | -- | body | SKU 名称（变体名）。 |
| `brand` | string | 否 | -- | body | 品牌。 |
| `category` | string | 否 | -- | body | 产品类目路径。 |
| `targetPerson` | string | 否 | -- | body | 目标受众。 |
| `productSize` | string | 否 | -- | body | 商品尺寸描述。 |
| `material` | string | 否 | -- | body | 材质描述。 |
| `usage` | string | 否 | -- | body | 使用方法。 |
| `sellingPoints` | string | 否 | -- | body | 卖点描述。 |
| `marketingPoints` | string | 否 | -- | body | 核心营销卖点提炼。 |
| `clothingProfile` | string | 否 | -- | body | 服装基础档案（productType=2 才有意义）。 |
| `craftsmanship` | string | 否 | -- | body | 工艺细节精解（服装类）。 |
| `wearingExperience` | string | 否 | -- | body | 功能性与穿着体验（服装类）。 |
| `sceneStyling` | string | 否 | -- | body | 场景适配与穿搭方案。 |
| `lifecyclePhase` | integer | 否 | -- | body | 生命周期相位（业务枚举）。 |
| `profileStatus` | integer | 否 | -- | body | 资料完整度状态（业务枚举）。 |
| `inventoryStatus` | integer | 否 | -- | body | 库存状态（业务枚举）。 |
| `appendImages` | List of String | 否 | -- | body | 追加图片URL列表。 |
| `appendVideos` | List of String | 否 | -- | body | 追加视频URL列表。 |

> body 字段全部可选；只传需要修改的字段，未传字段保持原值。

## 响应结构

顶层信封（`ResponseDto<Void>`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | `200` 成功；其他见错误码表。 |
| `msg` | string | 业务消息。 |
| `traceId` | string | 后端 traceId。 |
| `data` | null | 无返回数据。 |

## 错误码

| code | 含义 | 处理建议 |
|------|------|----------|
| 200 | 成功 | 提示用户已更新指定字段。 |
| 400 | 参数校验失败 | 看 `msg`。 |
| 401 | 未授权 | 检查 API Key。 |
| 403 | 变体不属于当前团队 | 友好提示。 |
| 404 | 变体不存在 | 友好提示。 |
| 500 | 服务器内部错误 | 拿 traceId 找运维。 |

## 计费

不计费。

## curl 示例

```bash
curl -X POST "$LINKFOX_TOOL_GATEWAY/product-center/v1/skill/product/variant/12345/update" \
  -H "Authorization: $LINKFOX_AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"skuName":"经典款 - 白","sellingPoints":"纯棉透气"}'
```

---

## Feedback API

- **POST** `https://skill-api.linkfox.com/api/v1/public/feedback`
- **Content-Type:** `application/json`

```json
{
  "skillName": "linkfox-product-center-variant-update",
  "sentiment": "POSITIVE",
  "category": "OTHER",
  "content": "Updated successfully."
}
```
