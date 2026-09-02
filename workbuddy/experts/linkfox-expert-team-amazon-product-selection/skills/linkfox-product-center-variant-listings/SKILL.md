---
name: linkfox-product-center-variant-listings
description: |
  商品库-变体下的链接列表。按 skuId 分页查询该变体下所有 Listing（平台、站点、标题、状态、是否参考链接），支持按平台、站点、状态筛选。
  消歧：已知 skuId 查其下链接集合走本 skill；查单条链接详情走 listing-detail。
---

# 商品库-变体下的链接列表

按 `skuId` 分页拉这个变体下挂的所有链接（含自有链接和参考链接）。卡片视图：每条只回核心字段，要看完整 listing 走 `linkfox-product-center-listing-detail`。

## 核心特点

- **范围限定**：只看当前调用方所属团队（teamId 由网关注入身份后台解析）的链接库；查不到自家的会返业务错。
- **多维筛选**：`platform / marketplace / isReference / status` 全部可选叠加，常用于"我在亚马逊美国站铺了哪些自有链接"。
- **卡片字段精简**：每条只回 listing 卡片字段（id / 平台 / 站点 / 标题 / 五点描述 / 关键词 / 状态 / 来源 URL / 封面图 / 时间戳），上下文友好。
- **分页**：`pageNum` / `pageSize`，默认 `1` / `20`。

## 参数概览

- **必填字段**：`skuId`、`offerSource`（来源类型，用于会话关联。调用方按自身角色硬编码传入：10=Listing-Agent, 11=选品, 12=生图, 13=市场分析, 14=视频, 15=通用）

完整参数表、响应字段结构与错误码，见 [`references/api.md`](references/api.md)。

## 调用方式

- **API 端点**：`GET /product-center/v1/skill/product/variant/{skuId}/listings`（完整参数/响应/错误码见 `references/api.md`）
- **Python 脚本**：`python scripts/product_center_variant_listings.py '<JSON 参数>'`
- **HTTP 方法**：原接口 GET + `@PathVariable skuId` + `@ModelAttribute SkillListingQueryVo`；脚本把 `skuId` 替换到 path，剩余字段拍成 query string。

**输出策略（脚本默认行为）**：
- 响应体 ≤ 8 KB：直接全量打印到 stdout
- 响应体较大：写入 `<cwd>/linkfox/<YYYY-MM-DD>/<session>/data/linkfox-product-center-variant-listings-<timestamp>.json`，stdout 只输出摘要（顶层字段 + `data.list` 长度 + 前 3 条样本）

**读数据建议**：先看摘要判断够不够；要按字段抽取时优先用 `jq` 从保存的 json 文件读。

## 使用指引

1. **skuId 必传**；缺失或空脚本立刻报错退出。
2. **筛选**：`platform`（如 `AMAZON`）/ `marketplace`（如 `US`）/ `isReference`（`0`=自有 `1`=参考）/ `status`（业务枚举）按需叠加。
3. **分页**：`pageNum` 默认 `1`，`pageSize` 默认 `20`。`hasMore=true` 才有下一页。

### 示例

**1. 拿首页（最常用）**
```json
{"skuId": 12345}
```

**2. 只看亚马逊美国站的自有链接**
```json
{"skuId": 12345, "platform": "AMAZON", "marketplace": "US", "isReference": 0}
```

**3. 翻第 2 页，每页 50 条**
```json
{"skuId": 12345, "pageNum": 2, "pageSize": 50}
```

## 展示规则

1. **表格**：`listingId / platform-marketplace（合并显示，如 AMAZON-US）/ title / bulletPoints / keywords / status 中文 / sourceUrl / 更新时间（unix→日期）`。
2. **isReference**：`0` 显示"自有"、`1` 显示"参考"。
3. **封面图**：当前接口不返回封面图，如需查看图片请用 `linkfox-product-center-listing-detail` 获取完整图片列表。
4. **来源 URL**：可点击外链；为空时不展示该列。
5. **空结果**：`data.total = 0` 时友好提示"该 SKU 下还没有挂链接"，并建议 `linkfox-product-center-listing-create`。
6. **分页提示**：`hasMore=true` 提示用户"还有更多链接，要继续看下一页吗"。

## 限制

- 单次最多 `pageSize` 条，深翻自行循环（注意上下文成本）。
- 仅当前团队自有 SKU 的链接，不能跨团队。
- 列表响应不含 listing 完整字段（如A+），需要走 `linkfox-product-center-listing-detail`。

## 适用与不适用

**适用**：
- "看这个 SKU 都铺到了哪些平台 / 站点"
- 选品 / 上架前盘点该变体下已有链接
- 与 `linkfox-product-center-listing-detail` 配合：先拿 listingId，再查完整字段

**不适用**：
- 想搜亚马逊公开商品 / 关键词 → `linkfox-amazon-search`
- 想看 SKU 维度的业务字段（卖点/材质等）→ `linkfox-product-center-variant-detail`
- 想看具体一条 listing 的完整数据 → `linkfox-product-center-listing-detail`

## 反馈

参见 `references/api.md`。
