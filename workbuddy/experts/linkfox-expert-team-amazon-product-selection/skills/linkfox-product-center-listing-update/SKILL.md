---
name: linkfox-product-center-listing-update
description: |
  商品库-更新 Listing。按 listingId 增量更新文案（标题、五点、关键词）或追加图片，只传需要修改的字段。
  消歧：修改链接文案或图片走本 skill；修改 SKU 业务字段走 variant-update；新建链接走 listing-create；只有 skuId 时先用 variant-listings 反查 listingId。
---

# 更新 Listing（商品库）

## 核心特点
- **写操作**：需用户明确确认后再调用
- 统一入口：文案更新和图片追加在一个接口完成
- PATCH 语义：只传需要修改的字段
- 团队隔离：目标 listing 必须属于当前团队

## 参数概览

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| listingId | Long | 是 | 路径参数，目标 listing ID |
| offerSource | Integer | 是 | 来源类型，调用方按自身角色硬编码传入（**走 query 用于会话来源绑定，非 body**） |
| title | String | 否 | 标题 |
| bulletPoints | String | 否 | 五点描述（脚本自动清洗 markdown 标记：去掉 `**`/`__`/`` ` ``/行首 `#`/`- `/`* `，保留纯文本） |
| keywords | String | 否 | 关键词 JSON（格式见下方说明） |
| appendImages | List&lt;String&gt; | 否 | 追加图片 URL 列表 |
| imageType | Integer | 否 | 图片类型：1=主副图(默认)，2=A+图，99=其他 |

所有字段可选但至少传一个有效值。

## keywords 格式

keywords 为 JSON 字符串，结构如下：
```json
{
  "core": ["主词1", "主词2"],
  "highWeight": ["高权重词"],
  "title": ["标题词1", "标题词2", "标题词3"],
  "bullet": ["五点词1", "五点词2"],
  "description": ["描述词"],
  "backend": ["后台搜索词"]
}
```
规则：title 最多 3 个、bullet 最多 5 个、description 最多 5 个，总计不超过 20 个关键词。

## 图片类型枚举

| imageType | 含义 |
|-----------|------|
| 1 | 主副图（白底/卖点/模特/种草/尺码/特写等） |
| 2 | A+图（高级A+/普通A+/自定义A+） |
| 99 | 其他 |

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

## 使用指引

### 只更新文案
```json
{
  "listingId": 123456,
  "title": "New Premium Running Shoes",
  "bulletPoints": "Breathable mesh upper\nLightweight EVA sole\n..."
}
```

### 更新文案含关键词
```json
{
  "listingId": 123456,
  "title": "Men's Breathable Cotton T-Shirt",
  "bulletPoints": "【Premium Cotton】100% pure cotton\n【Breathable】Mesh ventilation",
  "keywords": "{\"core\":[\"mens cotton t-shirt\"],\"highWeight\":[\"breathable tee\"],\"title\":[\"mens t-shirt\",\"cotton tee\"],\"bullet\":[\"breathable\",\"lightweight\"],\"backend\":[\"mens top\"]}"
}
```

> 注意：`keywords` 的值是一个 **JSON 字符串**（外层有引号、内层需转义），不是嵌套对象。
```

### 只追加图片
```json
{
  "listingId": 123456,
  "appendImages": ["https://...img1.jpg", "https://...img2.jpg"],
  "imageType": 2
}
```

### 同时更新文案和追加图片
```json
{
  "listingId": 123456,
  "title": "Updated Title",
  "bulletPoints": "Point 1\nPoint 2",
  "appendImages": ["https://...img1.jpg"],
  "imageType": 1
}
```

## 调用方式
脚本：`scripts/product_center_listing_update.py`

## 错误码
| code | 含义 |
|------|------|
| 200 | 成功 |
| 400 | 参数校验失败 |
| 403 | listing 不属于当前团队 |
| 404 | listing 不存在 |

## 展示规则
- 成功后简要告知已更新的字段
- 图片追加为增量操作，不会覆盖已有图片
- **追加图片幂等**：`appendImages` 同一批 URL+类型 重复追加会被自动去重、不会重复入库（改文案不受影响，始终生效）；无需重试
