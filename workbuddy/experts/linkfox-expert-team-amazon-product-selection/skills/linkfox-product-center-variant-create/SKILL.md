---
name: linkfox-product-center-variant-create
description: |
  商品库-创建变体(SKU)。新建商品并创建初始变体，或向已有商品追加变体（如颜色款、尺码款）。
  消歧：用户说"入库""保存到商品库""建商品"且无已有 ID 时走本 skill；往已有 SKU 追加图片或视频走 variant-update；往已有 Listing 追加走 listing-update。
---

# 创建变体（商品库）

## 核心特点
- **写操作**：需用户明确确认后再调用
- 团队隔离：变体创建在当前团队商品库中
- 两种模式由 `productId` 是否传值决定

## 参数概览

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| productId | Long | 否 | 空=新建商品+初始变体；有值=追加变体到已有商品 |
| productName | String | 条件必填 | productId 为空时必须提供 |
| skuName | String | 否 | 变体名称，不传则用 productName |
| brand | String | 否 | 品牌 |
| category | String | 否 | 类目路径 |
| targetPerson | String | 否 | 目标人群 |
| material | String | 否 | 材质描述 |
| sellingPoints | String | 否 | 卖点描述 |
| productType | Integer | 否 | 1=商品(默认)，2=服装 |
| offerSource | Integer | 是 | 来源类型，调用方按自身角色硬编码传入。**同时通过 query 与 body 传递**：query 用于会话来源绑定，body 写入 `sku.offerSource`（缺一不可，脚本已自动双写） |
| images | List&lt;String&gt; | 是 | 原图 URL 列表，1-30 张 |
| videos | List&lt;String&gt; | 否 | 视频 URL 列表，最多 5 条 |

### offerSource 枚举（调用方按自身角色硬编码传入）

| 值 | 含义 |
|----|------|
| 10 | Listing-Agent |
| 11 | 选品-Agent |
| 12 | 生图-Agent |
| 13 | 市场分析-Agent |
| 14 | 视频-Agent |
| 15 | 通用-Agent |

> 调用方必须按自身角色传入对应值，不得省略或让用户选择。

## 返回

| 字段 | 说明 |
|------|------|
| productId | 商品 ID |
| skuId | 新创建的变体 ID |

## 使用指引

### 初始变体（新建商品）
不传 productId，必须提供 productName 和 images：
```json
{
  "productName": "夏季透气运动鞋",
  "brand": "SportX",
  "images": ["https://...img1.jpg", "https://...img2.jpg"]
}
```

### 追加变体（已有商品）
传入 productId，将新变体挂到已有商品下：
```json
{
  "productId": 123456,
  "skuName": "黑色款",
  "images": ["https://...black1.jpg", "https://...black2.jpg"]
}
```

## 调用方式
脚本：`scripts/product_center_variant_create.py`

## 错误码
| code | 含义 |
|------|------|
| 200 | 成功 |
| 400 | 参数校验失败（images 为空、productName 缺失等） |
| 403 | 商品不属于当前团队（追加模式） |
| 404 | 商品不存在（追加模式） |

## 展示规则
- 成功后告知用户 productId 和 skuId
- 提示用户可用 listing-create 为该变体创建上架链接
- **幂等**：返回中含 `duplicate:true` 或 `_directive=DUPLICATE_STOP` 时，说明该变体已创建过，**禁止再次调用本 skill**，直接复用返回的 productId/skuId 继续后续步骤

## 适用与不适用

**适用**：
- 只建商品入库，暂不上架
- 为已有商品追加新的 SKU 变体（如颜色/尺码款）

**不适用**：
- 建商品后立即需要 listing → 直接用 `linkfox-product-center-listing-create` 模式二（不传 skuId），一步完成创建商品 + SKU + 挂 listing
