---
name: linkfox-product-center-listing-detail
description: |
  商品库-Listing 详情。按 listingId 查询上架链接的完整信息（平台、标题、五点、价格、图片等）。
  消歧：已知 listingId 查链接走本 skill；只有 skuId 时先用 variant-listings 获取 listingId。
---

# 商品库-Listing 详情

按 `listingId` 拿到这条上架链接的**完整业务档案**——文案、平台元信息、状态机、外部抓取的价格/评分/销量、主副图与 A+ 图。

## 核心特点

- **完整字段**：listing 维度的全部业务字段（文案 + 平台元信息 + 状态机 + 外部抓取数据 + 图片列表），不像列表型只回卡片。
- **范围限定**：只看当前调用方所属团队（teamId 由网关注入身份后台解析）的链接库；查不到自家的会返业务错。
- **三套状态码**：`status`（链接整体状态）/ `imageStatus`（图片做完没）/ `linkingStatus`（与外部 ASIN 绑定状态），合起来判断"能不能继续做图/上架"。
- **图片分组**：`mainImages`（主副图）和 `aplusImages`（A+ 图）分两列表返回，便于做图前预览和挑选。

## 参数概览

- **必填字段**：`listingId`、`offerSource`（来源类型，用于会话关联。调用方按自身角色硬编码传入：10=Listing-Agent, 11=选品, 12=生图, 13=市场分析, 14=视频, 15=通用）

完整参数表、响应字段结构与错误码，见 [`references/api.md`](references/api.md)。

## 调用方式

- **API 端点**：`GET /product-center/v1/skill/product/listing/{listingId}`（完整参数/响应/错误码见 `references/api.md`）
- **Python 脚本**：`python scripts/product_center_listing_detail.py '<JSON 参数>'`
- **HTTP 方法**：原接口为 GET + `@PathVariable`；脚本内部把 `params.listingId` 替换到 URL 路径上。

**输出策略（脚本默认行为）**：
- 响应体 ≤ 8 KB：直接把完整 JSON 打印到 stdout
- 响应体较大（图片数组多时常见）：写入 `<cwd>/linkfox/<YYYY-MM-DD>/<session>/data/linkfox-product-center-listing-detail-<timestamp>.json`，stdout 只输出摘要（顶层 `code/msg/data` + 主图列表 `data.mainImages` 长度 + 前 3 条样本）

**读数据建议**：先看摘要判断字段够不够；要按字段深挖时优先用 `jq` 从保存的 json 文件按需抽取，避免整份 JSON 进入上下文。

## 使用指引

1. **listingId 必传**：不传或为空脚本立刻报错退出。listingId 一般来源于：
   - 用户直接给（最常见）
   - 上游 skill 返回（如 `linkfox-product-center-variant-listings`）
2. **不带 query 参数**：本接口只有 path variable `listingId`。

### 示例

**1. 查 listing 详情**
```json
{"listingId": 67890}
```

**2. 大对象落盘后用 jq 抽某字段**
```bash
python scripts/product_center_listing_detail.py '{"listingId": 67890}'
# 大响应落到 linkfox/<日期>/<session>/data/linkfox-product-center-listing-detail-<ts>.json
jq '.data.bulletPoints' linkfox/.../data/linkfox-product-center-listing-detail-*.json
jq '.data.mainImages[].thumbUrl' linkfox/.../data/linkfox-product-center-listing-detail-*.json
```

## 展示规则

1. **基础块**：`listingId / skuId / productId / platform / marketplace / title / brandName / sellerName` 列出。
2. **文案块**：`title / bulletPoints / bulletPointsTranslated / keywords` 整段展示，可能较长。
3. **抓取数据**：`price + currency / rating / reviewCount / salesVolume`（无数据时提示"暂未抓取"，不要展示空值）。
4. **状态码翻译**：`status / imageStatus / linkingStatus` 是数字枚举，按业务字典翻译，不要原始数字给用户。
5. **图片缩略**：`mainImages` 和 `aplusImages` 用缩略图带（`thumbUrl` 优先），`isPicked=1` 高亮。
6. **时间戳**：`createTime / updateTime` 是 unix 秒，转日期再展示。
7. **来源链接**：`sourceUrl` 直接给可点击外链；`sourceProductId`（如 ASIN）单独提示。

## 限制

- 单次只能查一个 listingId；批量查需要循环（注意上下文成本，必要时落盘 + jq）。
- 仅能查当前团队自有的 listing，不能跨团队。

## 适用与不适用

**适用**：
- 已知 listingId，要查 listing 完整业务字段（文案/状态/图片/抓取数据）
- 做图/翻译/上架前确认 listing 资料是否齐全（看 `imageStatus` / `linkingStatus`）
- 拿主副图/A+ 图列表做下一步处理

**不适用**：
- 想查亚马逊公开 listing（不在自家库）→ `linkfox-amazon-product-detail`
- 只有 ASIN/URL 没有 listingId → 先按 SKU/URL 找对应 listingId（无现成 skill 时通过 `linkfox-product-center-variant-listings` 兜回）
- 想看 SKU 维度业务档案 → `linkfox-product-center-variant-detail`
- 想改 listing 文案 → `linkfox-product-center-listing-update-copy`
- 想改 listing 图片 → `linkfox-product-center-listing-update-images`

## 反馈

参见 `references/api.md`。
