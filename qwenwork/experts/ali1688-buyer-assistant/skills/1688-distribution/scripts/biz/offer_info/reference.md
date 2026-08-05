# 商品分销参谋数据查询参考文档

> 本文档供 AI 在需要查询商品详细分销参谋数据时按需加载。

## 接口信息

- **工具名**：`distribution_offer_info`
- **参数**：`{"offerId": "商品ID"}`
- **用途**：查询单个商品的分销参谋详情，包括分销价、渠道支持、参谋指标、运费、服务保障、品牌信息等

## 调用方式

```bash
python3 scripts/cli.py offer_info query --offer_id="1021484012198"

# 提取决策因素（用于选品分析）
python3 scripts/cli.py offer_info query --offer_id="1021484012198" --decision=true
```

## 返回数据结构

### 核心字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `offerId` | Long | 商品 ID |
| `priceInInfo` | Object | 分销价信息 |
| `supportList` | Array | 支持的面单渠道列表 |
| `adviseList` | Array | 代发参谋建议数据（核心指标） |
| `freightInfo` | Object | 运费信息 |
| `protectionInfoList` | Array | 分销服务保障列表 |
| `brandInfo` | Object | 品牌分销信息（仅品牌商品） |
| `downstreamPerformance` | Object | 下游渠道表现 |
| `goodsOwnerInfo` | Object | 货主信息 |
| `alreadyUpgrade` | Boolean | 是否已升级为分销品 |

### 分销价信息（priceInInfo）

| 字段 | 说明 |
|------|------|
| `onePiecePriceInteger` + `onePiecePriceDecimal` | 一件包邮价 |
| `multiPiecePriceInteger` + `multiPiecePriceDecimal` | 分销专属价 |
| `startNum` | 起批量 |
| `onePieceFreePostage` | 是否支持一件包邮 |
| `freepostage` | 多件是否包邮 |

### 运费信息（freightInfo）

| 字段 | 说明 |
|------|------|
| `freeDeliverFee` | 是否包邮 |
| `officialLogistics` | 是否官方物流 |
| `totalCost` | 运费金额 |

### 品牌信息（brandInfo）

| 字段 | 说明 |
|------|------|
| `isBrandOffer` | 是否品牌商品 |
| `isAuth` | 当前买家是否已获得品牌授权 |
| `brandName` | 品牌名称 |

> 🚫 **品牌授权检查（重要）**：当 `isBrandOffer=true` 且 `isAuth=false` 时，该商品 **不能铺货**，否则有侵权风险。必须引导用户先申请品牌授权：
> `https://air.1688.com/app/channel-fe/distribution-work/brand.html#/auth_apply?offerId={offerId}`

### 下游渠道表现（downstreamPerformance）

| 字段 | 说明 |
|------|------|
| `highExperienceScoreList` | 商品体验分高的渠道 |
| `highPerfectLgtRateList` | 完美履约率高的渠道 |

### 服务保障（protectionInfoList）

每项包含 `serviceName`（服务名称）和 `description`（服务描述）。

## 选品决策分析流程

选品后，对候选商品批量查询分销参谋数据，综合以下维度进行分析：

### 推荐维度（正面因素）

1. **价格优势**：一件包邮价低、分销专属价有折扣
2. **包邮支持**：支持一件包邮 > 多件包邮 > 不包邮
3. **渠道匹配**：商品支持用户目标渠道的密文面单
4. **高体验分**：在目标渠道有高体验分（影响店铺权重）
5. **高履约率**：在目标渠道有高完美履约率（影响物流评分）
6. **服务保障**：有退换货保障、品质保障等
7. **官方物流**：使用官方物流更可靠
8. **已升级分销品**：已升级的商品铺货更顺畅

### 风险维度（负面因素）

1. **品牌未授权（严重）**：品牌商品但未获得授权，**不能铺货，有侵权风险**。必须引导用户申请授权：`[申请品牌授权](https://air.1688.com/app/channel-fe/distribution-work/brand.html#/auth_apply?offerId={offerId})`
2. **运费高**：非包邮且运费高，影响利润
3. **起批量高**：起批量过高不适合小卖家
4. **渠道不匹配**：不支持用户目标渠道

### 分析输出格式

对每个候选商品输出：
```
### [{offerId}](https://detail.1688.com/offer/{offerId}.html) {title}

**推荐指数**：⭐⭐⭐⭐⭐（5/5）

**推荐理由**：
- ✅ 一件包邮价 ¥22.0，价格有竞争力
- ✅ 支持抖音、拼多多密文面单
- ✅ 抖音渠道体验分高
- ✅ 有 7 天无理由退货保障

**风险提示**：
- 🚫 品牌商品未授权，不能铺货，有侵权风险
- 👉 [申请品牌授权](https://air.1688.com/app/channel-fe/distribution-work/brand.html#/auth_apply?offerId={offerId})

**综合建议**：需先完成品牌授权申请后才能铺货
```

