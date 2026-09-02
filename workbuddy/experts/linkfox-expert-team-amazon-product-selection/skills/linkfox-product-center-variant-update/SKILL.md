---
name: linkfox-product-center-variant-update
description: |
  商品库-更新变体(SKU)。按 skuId 增量更新业务字段（名称、品牌、类目、卖点、状态等），支持追加图片和视频，只传需要修改的字段。
  消歧：修改 SKU 自身字段走本 skill；修改 listing 文案或图片走 listing-update；新建 SKU 走 variant-create；只有 listingId 时先用 listing-detail 反查 skuId。
---

# 商品库-更新变体

按 skuId 增量更新 SKU 的业务字段。**部分更新（PATCH 语义）**——只传想改的字段，没传的保持不变。**写操作**，调用前需要拿到用户明确指令。

## 核心特点

- **写操作**：会真实落库，调用前必须拿到用户明确"改成 XX"的指令。
- **范围限定**：目标 SKU 必须属于当前团队，否则 403。
- **PATCH 语义**：所有字段可选；只更新传入的字段，其它字段保持原值。
- **字段全面**：覆盖 SKU 维度所有业务字段（基础信息 / 卖点 / 服装专属 / 状态机三件套）。
- **追加媒体**：支持通过 `appendImages` / `appendVideos` 追加图片和视频到变体。

## 参数概览

- **必填字段**：`skuId`（path）、`offerSource`（query，来源类型，调用方按自身角色硬编码传入：10=Listing-Agent, 11=选品, 12=生图, 13=市场分析, 14=视频, 15=通用）

完整参数表、响应字段结构与错误码，见 [`references/api.md`](references/api.md)。

## 调用方式

- **API 端点**：`POST /product-center/v1/skill/product/variant/{skuId}/update`（完整参数/响应/错误码见 `references/api.md`）
- **Python 脚本**：`python scripts/product_center_variant_update.py '<JSON 参数>'`
- **HTTP 方法**：原接口 POST + `@PathVariable skuId` + `@RequestBody`；脚本把 `params.skuId` 替换到 path，剩余字段作为 JSON body。

**输出策略（脚本默认行为）**：
- 响应一般极小（只回 `{code, msg, traceId}`，data 为 null）：直接全量打印到 stdout

## 使用指引

1. **确认意图**：写操作，必须用户明确说"改 / 更新 / 改成 XX"才调；不确定时 AskUserQuestion 二次确认要改的字段。
2. **PATCH 语义**：**只传**想改的字段。如果用户只说"把卖点改成 XXX"，body 就只传 `sellingPoints`，不要把其它字段一起回填。
3. **状态码字段慎改**：`lifecyclePhase / profileStatus / inventoryStatus` 是业务流转状态，agent 不应主动改，除非用户明确指令。

### 示例

**1. 改 SKU 名称**
```json
{"skuId": 12345, "skuName": "经典款 - 白"}
```

**2. 同时改卖点和场景搭配**
```json
{
  "skuId": 12345,
  "sellingPoints": "纯棉透气、亲肤舒适、可机洗",
  "sceneStyling": "夏季出游、办公通勤"
}
```

**3. 改状态（用户明确指令）**
```json
{"skuId": 12345, "profileStatus": 2}
```

**4. 追加图片到变体**
```json
{
  "skuId": 12345,
  "appendImages": ["https://img.example.com/new-photo-1.jpg", "https://img.example.com/new-photo-2.jpg"]
}
```

## 展示规则

1. **更新成功**：报喜并列出**实际改了哪些字段**（与入参一致），便于用户确认。
2. **update 不返回最新数据**：如果用户问"现在的字段值是什么"，配合 `linkfox-product-center-variant-detail` 再查一次。
3. **失败**：按错误码做友好提示。
4. **追加媒体幂等**：`appendImages`/`appendVideos` 同一批 URL 重复追加会被自动去重、不会重复入库（改字段不受影响，始终生效）；无需重试。

## 限制

- 单次只改一个 SKU。
- 字段长度 / 枚举校验跟创建一致（见 api.md）。
- 不支持删除字段（传空字符串可能被解释为"清空字段"，按业务字典确认）。

## 适用与不适用

**适用**：
- "把这个 SKU 的卖点改成 XX"
- "更新一下材质"
- "把这个款的状态改成 XX"

**不适用**：
- 想改 listing 文案（标题/五点/关键词）→ `linkfox-product-center-listing-update-copy`
- 想改 listing 图片 → `linkfox-product-center-listing-update-images`
- 想新建 SKU → 当前 skill 集中没有"新建 SKU 但不创建 SPU"，需走前台或 `linkfox-product-center-product-create`

## 反馈

参见 `references/api.md`。
