---
name: linkfox-product-center-variant-detail
description: |
  商品库-变体详情。按 skuId 查询 SKU 的完整业务信息（基础属性、卖点、服装字段、图片、状态等）。
  消歧：已知 skuId 查 SKU 信息走本 skill（即使用户没说"详情"）；只有 listingId 时先用 listing-detail 反查 skuId。
---

# 商品库-变体详情

按 `skuId` 拿到商品库里这个变体的**完整业务档案**——SKU 维度的所有面（基础信息、营销卖点、生命周期、原图列表）。

## 核心特点

- **完整字段**：返回 SKU 维度的全部业务字段（不像列表型只回卡片）。
- **范围限定**：只看当前调用方所属团队（teamId 由网关注入身份后台解析）的商品库；查不到自家的 SKU 会返回业务错。
- **原图列表**：包含该 SKU 关联的原图（imageId / imageUrl / thumbUrl / imageType / isPicked），可直接用于做图前预览。
- **状态字段**：`lifecyclePhase` / `profileStatus` / `inventoryStatus` 三个状态码，便于决策"能不能继续做图/上架"。

## 参数概览

- **必填字段**：`skuId`、`offerSource`（来源类型，用于会话关联。调用方按自身角色硬编码传入：10=Listing-Agent, 11=选品, 12=生图, 13=市场分析, 14=视频, 15=通用）

完整参数表（含类型、说明）、响应字段结构与错误码，见 [`references/api.md`](references/api.md)。

## 调用方式

- **API 端点**：`GET /product-center/v1/skill/product/variant/{skuId}`（完整参数/响应/错误码见 `references/api.md`）
- **Python 脚本**：`python scripts/product_center_variant_detail.py '<JSON 参数>'`
- **HTTP 方法**：原接口为 GET + `@PathVariable`；脚本内部把 `params.skuId` 替换到 URL 路径上。

**输出策略（脚本默认行为）**：
- 响应体 ≤ 8 KB：直接把完整 JSON 打印到 stdout
- 响应体较大（含原图数组等）：写入 `<cwd>/linkfox/<YYYY-MM-DD>/<session>/data/linkfox-product-center-variant-detail-<timestamp>.json`（`<session>` 取自环境变量 `SESSION_ID`；**禁止写入 /tmp**，当前目录不可写则报错），stdout 只输出摘要（顶层字段 `code/msg/data` + 原图列表 `data.images` 长度 + 前 3 条样本）

**读数据建议**：先看摘要判断字段够不够；要按字段深挖时优先用 `jq` 从保存的 json 文件按需抽取，避免整份 JSON 进入上下文。

## 使用指引

1. **skuId 必传**：不传或为空脚本会报错并退出。skuId 一般来源于：
   - 用户直接给（最常见）
   - 上游 skill 返回（如 `linkfox-product-center-variant-listings` 列出过的）
2. **不带 query 参数**：本接口除了 path variable `skuId` 外没有其他参数。

### 示例

**1. 查变体详情**
```json
{"skuId": 12345}
```

**2. 把脚本结果存大对象后用 jq 抽某字段**
```bash
python scripts/product_center_variant_detail.py '{"skuId": 12345}'
# 大响应会落到 linkfox/<日期>/<session>/data/linkfox-product-center-variant-detail-<ts>.json
jq '.data.sellingPoints' linkfox/.../data/linkfox-product-center-variant-detail-*.json
```

## 展示规则

1. **基础信息块**：`skuName / skuCode / brand / category / targetPerson / productSize / productType` 一组列出（productType: `1=商品 2=服装` 中文翻译）。
2. **卖点块**：`sellingPoints / marketingPoints / sceneStyling / wearingExperience` 整段展示，因为可能较长。
3. **服装专属**（`productType=2` 时才显示）：`clothingProfile / craftsmanship / material`。
4. **原图缩略**：`images` 列表用缩略图带（`thumbUrl` 优先），点开看大图（`imageUrl`）。
5. **视频**：`videos` 列表单独展示，标注为视频类型；为空时不展示该区块。
6. **状态码翻译**：`lifecyclePhase / profileStatus / inventoryStatus` 是数字枚举，要按业务字典翻译，不要原始数字给用户。
7. **空字段**：业务字段（卖点/材质/工艺等）可能为空，提示用户"该字段尚未补充"，不要展示空字符串。

## 限制

- 单次只能查一个 skuId；批量查需要循环（注意上下文成本，必要时落盘 + jq）。
- 仅能查当前团队自有的 SKU，不能跨团队查。

## 适用与不适用

**适用**：
- 已知 skuId，要查 SKU 完整业务字段（卖点/材质/工艺/尺寸/品牌等）
- 做图/上架前确认变体资料是否齐全（看 `profileStatus`）
- 拿原图列表做下一步处理

**不适用**：
- 想搜亚马逊/平台公开商品 → `linkfox-amazon-product-detail` / `linkfox-amazon-search`
- 只有 listingId 没有 skuId → 先用 `linkfox-product-center-listing-detail` 拿 skuId
- 想看该 SKU 下的链接列表 → `linkfox-product-center-variant-listings`

## 反馈

参见 `references/api.md`。
