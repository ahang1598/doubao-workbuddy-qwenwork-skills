# 商品库-变体详情 API 参考

本页为 `linkfox-product-center-variant-detail` 技能调用的底层接口规格。SKILL.md 面向"怎么用"的决策层，本文档面向"接口精确格式"。

## 接口说明

> 工具中文名：商品库-变体详情

按 `skuId` 拿到当前团队商品库里该变体的完整业务档案（基础信息 + 卖点/营销 + 生命周期 + 原图列表）。

## 调用规范

- **请求地址**：`${LINKFOX_TOOL_GATEWAY}/product-center/v1/skill/product/variant/{skuId}`，其中基础域名从环境变量 `LINKFOX_TOOL_GATEWAY` 读取，未配置时报错退出。`{skuId}` 是 path variable，从入参 `params.skuId` 取值。
- **请求方式**：GET。无 query 参数、无 body。
- **认证方式**：Header `Authorization: <api_key>`，api_key 从环境变量 `LINKFOX_AGENT_API_KEY` 读取。未配置时按 SKILL.md 提示获取。
- **会话参数**：Query `agentSessionId=<session>`；脚本优先使用入参 `agentSessionId`，未传时自动取环境变量 `SESSION_ID`。

## 请求参数

| 参数 | 类型 | 必填 | 默认 | 位置 | 说明 |
|------|------|------|------|------|------|
| `skuId` | long | 是 | -- | path | 变体 SKU ID。 |
| `offerSource` | integer | 是 | -- | query | 来源类型，用于会话关联。调用方按自身角色硬编码传入（10=Listing-Agent, 11=选品, 12=生图, 13=市场分析, 14=视频, 15=通用）。 |
| `agentSessionId` | string | 否 | `SESSION_ID` | query | Agent 会话 ID。 |

## 响应结构

顶层信封（项目 `ResponseDto<T>`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 业务状态码：`200` 成功；其他非 200 见错误码表。 |
| `msg` | string | 业务消息。 |
| `traceId` | string | 后端 traceId，调用失败时一并提供给运维。 |
| `data` | object | `SkillVariantDto`，见下表。 |

`data`（`SkillVariantDto`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `skuId` | string（Long） | 变体 SKU ID。 |
| `productId` | string（Long） | 所属商品 SPU ID。 |
| `skuName` | string | SKU 名称（变体名）。 |
| `skuCode` | string | SKU 编码。 |
| `brand` | string | 品牌。 |
| `category` | string | 产品类目路径。 |
| `targetPerson` | string | 目标受众。 |
| `productSize` | string | 商品尺寸描述。 |
| `material` | string | 材质描述。 |
| `usage` | string | 使用方法。 |
| `sellingPoints` | string | 卖点描述。 |
| `marketingPoints` | string | 核心营销卖点提炼。 |
| `clothingProfile` | string | 服装基础档案（productType=2 时才有）。 |
| `craftsmanship` | string | 工艺细节精解（服装类）。 |
| `wearingExperience` | string | 功能性与穿着体验（服装类）。 |
| `sceneStyling` | string | 场景适配与穿搭方案。 |
| `mainImageUrl` | string | 主图 URL。 |
| `offerSource` | integer | 创建来源：`1=手动建库 2=URL解析 3=Agent 4=套图`。 |
| `lifecyclePhase` | integer | 生命周期相位（业务枚举，按字典翻译）。 |
| `profileStatus` | integer | 资料完整度状态（业务枚举）。 |
| `inventoryStatus` | integer | 库存状态（业务枚举）。 |
| `productType` | integer | 商品类型：`1=商品 2=服装`。 |
| `images` | array[Image] | 原图列表（mediaType=1），元素结构见下。 |
| `videos` | array[Image] | 视频列表（mediaType=2），元素结构同 images。 |

`images[]` / `videos[]`（`SkillImageDto`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `imageId` | string（Long） | 图片 ID。 |
| `imageUrl` | string | 原图 URL。 |
| `thumbUrl` | string | 缩略图 URL。 |
| `imageType` | integer | 图片类型（业务枚举）。 |
| `isPicked` | integer | 是否被挑选：`0=未挑 1=已挑`。 |

## 错误码

| code | 含义 | 处理建议 |
|------|------|----------|
| 200 | 成功 | 正常解析 `data` 字段。 |
| 401 | 未授权 | 检查 `Authorization` Header 的 API Key 是否正确；网关侧也可能因 memberId 无法解析而拒绝。 |
| 4xx | 业务错（如 SKU 不存在 / 不属于当前 team）| 看 `msg` 字段；若用户给的是别人的 skuId，要友好提示"该 SKU 不在你的商品库"。 |
| 500 | 服务器内部错误 | 拿 `traceId` 找运维查后端日志。 |

错误响应示例：
```json
{"code":500,"msg":"服务器内部错误","traceId":"xxx"}
```

## 计费

不计费（团队内自有数据查询）。

## curl 示例

```bash
curl "$LINKFOX_TOOL_GATEWAY/product-center/v1/skill/product/variant/12345" \
  -H "Authorization: $LINKFOX_AGENT_API_KEY"
```

---

## Feedback API

> 该端点与上方工具 API 分离，请勿混用 base URL。

- **POST** `https://skill-api.linkfox.com/api/v1/public/feedback`
- **Content-Type:** `application/json`

```json
{
  "skillName": "linkfox-product-center-variant-detail",
  "sentiment": "POSITIVE",
  "category": "OTHER",
  "content": "Results were accurate."
}
```

**字段规则：**
- `skillName`：使用 SKILL.md frontmatter 的 `name`
- `sentiment`：`POSITIVE` / `NEUTRAL` / `NEGATIVE`
- `category`：`BUG` / `COMPLAINT` / `SUGGESTION` / `OTHER`
- `content`：用户说了什么/期望什么、实际发生了什么、为什么是问题/赞赏
