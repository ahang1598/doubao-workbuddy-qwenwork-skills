---
name: linkfox-product-center-listing-create
description: |
  商品库-创建上架链接(Listing)。在已有 SKU 下新增链接，或从零开始连商品和 SKU 一起创建后挂载链接。
  消歧：给已有 SKU 新增链接走本 skill；只建商品不上架走 variant-create；修改已有 listing 走 listing-update。
---

# 商品库-创建 Listing

为当前团队商品库创建一条新的上架链接（自有或参考），返回 `listingId`。支持两种模式：**模式一**——选择已有 SKU 创建；**模式二**——不选商品，自动创建 SKU 再挂载 Listing。支持创建时一次性写入标题、五点描述、关键词、图片。

## 核心特点

- **写操作**：会真实落库，调用前必须拿到用户明确"上架/绑定"的指令。
- **范围限定**：链接落到当前调用方所属团队的库；若传 `skuId`，目标 SKU 必须属于当前团队，否则 403。
- **两种模式**：
  - **模式一（已有 SKU）**：传 `skuId`，直接在该 SKU 下挂链接。
  - **模式二（自动创建）**：不传 `skuId`，传 `productName` + `productImages`（可选 `productVideos`），后端自动创建商品+SKU 后再挂链接。
- **平台 + 站点必填**：`platform` / `marketplace` 不能为空；自有链接 vs 参考链接通过 `isReference` 区分。
- **一次性填写内容**：创建时可同时传入 `title`（标题）、`bulletPoints`（五点描述）、`keywords`（关键词）、`imageUrls` + `imageType`（图片）。
- **可选 sourceUrl**：当用户给出已知商品页 URL 时填入（参考链接场景常用）。

## 参数概览

- **必填字段**：`platform`、`marketplace`、`offerSource`（query，来源类型，调用方按自身角色硬编码传入：10=Listing-Agent, 11=选品, 12=生图, 13=市场分析, 14=视频, 15=通用；listing 记录自身来源后端硬编码为 Agent）
- **条件必填**：`skuId`（模式一）或 `productName` + `productImages`（模式二，可选 `productVideos`）

完整参数表、响应字段结构与错误码，见 [`references/api.md`](references/api.md)。

## 调用方式

- **API 端点**：`POST /product-center/v1/skill/product/listing/create`（完整参数/响应/错误码见 `references/api.md`）
- **Python 脚本**：`python scripts/product_center_listing_create.py '<JSON 参数>'`
- **HTTP 方法**：原接口 POST + `@RequestBody`；脚本把 params 整体作为 JSON body。

**输出策略（脚本默认行为）**：
- 响应一般小（只回三件 ID）：直接全量打印到 stdout

## 使用指引

1. **确认意图**：写操作，必须用户明确说"建链接 / 上架 / 绑定"才调。
2. **模式一（已有 SKU）**：传 `skuId`（属于当前团队） + `platform` + `marketplace`。
3. **模式二（自动创建）**：不传 `skuId`，必传 `productName` + `productImages` + `platform` + `marketplace`，可选传 `productVideos`（视频 URL 列表，最多 5 条）。
4. **可选**：
   - `isReference`：`0`=自有链接，`1`=参考链接（默认按业务约定）
   - `sourceUrl`：参考链接场景常用——给出已知 URL 让后端记录来源
   - `title`：listing 标题
   - `bulletPoints`：五点描述（脚本会自动清洗 markdown 标记：去掉 `**`/`__`/`` ` ``/行首 `#`/`- `/`* ` 等，保留纯文本，避免字面符号显示到前台）
   - `keywords`：关键词，JSON 字符串格式如下：
     ```json
     {"core":["主词"],"highWeight":["高权重词"],"title":["标题词1","标题词2"],"bullet":["五点词"],"description":["描述词"],"backend":["后台搜索词"]}
     ```
     规则：title 最多 3 个、bullet 最多 5 个、description 最多 5 个，总计不超过 20 个。
   - `imageUrls` + `imageType`：listing 图片
5. **平台 + 站点要规范**：常见值如 `platform=AMAZON`、`marketplace` 用两位国家代码 `US/UK/DE/JP/CA/...`。

### imageType 枚举

| 值 | 含义 |
|----|------|
| 1 | 主副图（默认） |
| 2 | A+图 |
| 99 | 其他 |

### offerSource 枚举（调用方按自身角色硬编码传入）

| 值  | 含义            |
|----|---------------|
| 10 | Listing-Agent |
| 11 | 选品-Agent      |
| 12 | 生图-Agent      |
| 13 | 市场分析-Agent    |
| 14 | 视频-Agent      |
| 15 | 通用-Agent      |

> 调用方必须按自身角色传入对应值，不得省略或让用户选择。

### 示例

**1. 模式一：把已有 SKU 上到亚马逊美国站（自有链接）**
```json
{"skuId": 12345, "platform": "AMAZON", "marketplace": "US", "isReference": 0}
```

**2. 模式一：录入一条参考链接**
```json
{
  "skuId": 12345,
  "platform": "AMAZON",
  "marketplace": "US",
  "isReference": 1,
  "sourceUrl": "https://www.amazon.com/dp/B0XXXXXXXX"
}
```

**3. 模式二：不选商品直接建 listing（自动创建 SKU）**
```json
{
  "productName": "夏季透气男士T恤",
  "productImages": ["https://img.example.com/sku-main.jpg", "https://img.example.com/sku-side.jpg"],
  "productVideos": ["https://img.example.com/sku-video.mp4"],
  "platform": "AMAZON",
  "marketplace": "US",
  "isReference": 0
}
```

**4. 一次性创建 listing 并填写内容（标题+五点+关键词+图片）**
```json
{
  "skuId": 12345,
  "platform": "AMAZON",
  "marketplace": "US",
  "isReference": 0,
  "title": "Men's Breathable Cotton T-Shirt Summer Casual",
  "bulletPoints": "【Premium Cotton】100% pure cotton...\n【Breathable Design】Mesh ventilation...\n【Versatile Style】Casual and office...\n【Easy Care】Machine washable...\n【Size Range】S-3XL available",
  "keywords": "{\"core\":[\"mens cotton t-shirt\"],\"highWeight\":[\"breathable summer tee\"],\"title\":[\"mens t-shirt\",\"cotton tee\",\"summer shirt\"],\"bullet\":[\"breathable\",\"lightweight\"],\"description\":[\"casual wear\"],\"backend\":[\"mens top\"]}",
  "imageUrls": ["https://img.example.com/listing-main.jpg", "https://img.example.com/listing-2.jpg"],
  "imageType": 1
}
```

## 展示规则

1. **创建成功**：报喜并展示 `listingId`，提示"已挂到 [platform-marketplace]"。
2. **后续动作引导**：建议下一步可做的事——做图、补全文案（`linkfox-product-center-listing-update`）。
3. **失败**：按错误码做友好提示。
4. **幂等**：返回含 `duplicate:true` 或 `_directive=DUPLICATE_STOP` 时，说明该链接已创建过，**禁止再次调用本 skill**，直接复用返回的 productId/skuId/listingId 继续后续步骤。

## 限制

- 单次只能建一条 listing。
- 模式一：skuId 必须属于当前团队。
- 模式二：必须传 `productName` 和 `productImages`，可选传 `productVideos`。
- 同一 SKU + platform + marketplace 重复创建可能业务校验拒绝（看 `msg`）。

## 适用与不适用

**适用**：
- 用户已确定要把某个 SKU 上到某平台/站点
- 录入参考链接（用于做图参考、关键词参考）

**不适用**：
- 想新建 SPU 商品 → `linkfox-product-center-product-create`
- 想按 URL 自动解析创建 → 走前台或 URL 解析类 skill（不在本 skill 集中）
- 想改已有 listing 的字段 → `linkfox-product-center-listing-update-copy` / `linkfox-product-center-listing-update-images`

## 反馈

参见 `references/api.md`。
