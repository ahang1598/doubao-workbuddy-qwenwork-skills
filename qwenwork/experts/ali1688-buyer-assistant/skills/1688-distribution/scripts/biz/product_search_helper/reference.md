# 选品助手参考文档

选品助手提供两种选品模式，根据用户输入自动判断：

| 模式 | 触发条件 | 接口工具名 |
|------|---------|-----------|
| 关键词选品 | 用户提供**文字描述** | `distribution_select_offer` |
| 图搜选品 | 用户提供**图片链接或图片文件** | `same_img_offer_search` |

**完整流程：选品 → 选品决策分析 → 展示推荐 → 确认铺货**

---

## 一、关键词选品

### MCP 工具调用参数

MCP 工具名：`distribution_select_offer`

调用时传入参数 `params`，值为 **JSON 字符串**，内部结构如下：

```json
{
  "sceneType": "agenticSelection",
  "retrieveFilters": [{"code": "title", "value": ["垃圾袋"], "queryType": "contains_any"}],
  "pageNo": 1,
  "pageSize": 20,
  "rankType": "ASC",
  "rankField": "df_price"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `sceneType` | string | **是** | 固定传 `"agenticSelection"`，不可省略 |
| `retrieveFilters` | array | 是 | 筛选条件列表（见下方详细说明） |
| `pageNo` | int | 否 | 页码，默认 1 |
| `pageSize` | int | 否 | 每页数量，默认 20，最大 50 |
| `rankType` | string | 否 | `"ASC"` 升序 / `"DESC"` 降序 |
| `rankField` | string | 否 | 排序字段，如 `"df_price"`、`"fx_ord_cnt_30d"` |

> **重要：`sceneType` 必须始终传入 `"agenticSelection"`，缺少则接口无法识别调用来源。**

### CLI 调用

```bash
# 基础调用
python3 scripts/cli.py product_search_helper search --filters='[{"code":"title","value":["垃圾袋"],"queryType":"contains_any"}]'

# 包邮 + 一件代发 + 按价格升序
python3 scripts/cli.py product_search_helper search --filters='[{"code":"title","value":["垃圾袋"],"queryType":"contains_any"},{"code":"is_free_post","value":"Y","queryType":"equal"},{"code":"is_yjdf","value":"Y","queryType":"equal"}]' --rank_type=ASC --rank_field=df_price

# 价格区间
python3 scripts/cli.py product_search_helper search --filters='[{"code":"title","value":["垃圾袋"],"queryType":"contains_any"},{"code":"df_price","value":[5.0,10.0],"queryType":"range"}]'
```

### 筛选条件（retrieveFilters）

从用户描述中提取筛选条件，每个条件格式：
```json
{ "code": "字段key", "value": ["值"], "queryType": "操作符" }
```

**操作符说明**：

| queryType | 含义 | 适用场景 |
|-----------|------|---------|
| `contains_any` | 包含任意一个 | 关键词、STRING 多值 |
- `equal`：等于（用于 Y/N 类型的 STRING 字段）
- `range`：范围查询（用于 DOUBLE/BIGINT 数值区间，value 格式: [最小值, 最大值]，null 表示不限制）

### 筛选字段速查表

**商品基础**

| 用户说 | 字段 key | 类型 | 用法示例 |
|--------|---------|------|---------|
| 关键词/标题 | `title` | STRING | `contains_any: ["垃圾袋", "加厚"]` |
| 一级类目 | `cate_level1_name` | STRING | `contains_any: ["家居"]` |
| 二级类目 | `cate_level2_name` | STRING | `contains_any: ["清洁用品"]` |
| 叶子类目 | `cate_name` | STRING | `contains_any: ["垃圾袋"]` |

**价格与物流**

| 用户说 | 字段 key | 类型 | 用法示例 |
|--------|---------|------|---------|
| 包邮 | `is_free_post` | STRING | `equal: "Y"` |
| 一件代发 | `is_yjdf` | STRING | `equal: "Y"` |
| 代发价格范围 | `df_price` | DOUBLE | `range: [5.0, 10.0]` |
| 代发邮费范围 | `df_post` | DOUBLE | `range: [null, 5.0]` |

**发货与服务**

| 用户说 | 字段 key | 类型 | 用法示例 |
|--------|---------|------|---------|
| 24小时发货 | `is_24hour_send_fx` | STRING | `equal: "Y"` |
| 48小时发货 | `is_48hour_send_fx` | STRING | `equal: "Y"` |
| 7天无理由退货 | `is_no_reason_to_return_7d_fx` | STRING | `equal: "Y"` |
| 退款处理快 | `is_rfd_process_fast` | STRING | `equal: "Y"` |
| 24小时揽收率高 | `is_24h_got_rate_high` | STRING | `equal: "Y"` |
| 48小时揽收率高 | `is_48h_got_rate_high` | STRING | `equal: "Y"` |
| 先采后付 | `is_xchf` | STRING | `equal: "Y"` |
| 实力工厂 | `is_shili_factory` | STRING | `equal: "Y"` |

**销量与数据**

| 用户说 | 字段 key | 类型 | 用法示例 |
|--------|---------|------|---------|
| 近30天分销订单量 | `fx_ord_cnt_30d` | BIGINT | `range: [100, null]` |
| 近30天订单量 | `ord_cnt_30d` | BIGINT | `range: [500, null]` |
| 7天内新品 | `is_7d_create` | STRING | `equal: "Y"` |
| 30天内新品 | `is_30d_create` | STRING | `equal: "Y"` |

**品质评分**

| 用户说 | 字段 key | 类型 | 用法示例 |
|--------|---------|------|---------|
| 淘宝商品体验分高 | `is_tb_pxi_score_high` | STRING | `equal: "Y"` |
| 货描相符大于均值 | `is_score_hm_high` | STRING | `equal: "Y"` |
| 响应速度大于均值 | `is_score_xy_high` | STRING | `equal: "Y"` |
| 发货速度大于均值 | `is_score_fh_high` | STRING | `equal: "Y"` |

**密文面单渠道（channels 字段）**

`channels` 使用 `and` 作为 `queryType`，`value` 为渠道枚举数组：

| 渠道 | 枚举值 |
|------|--------|
| 抖音 | `dy` |
| 拼多多 | `pdd` |
| 淘宝 | `tb` |
| 京东 | `jd` |
| 小红书 | `xhs` |

示例 — 用户说"支持抖音和拼多多密文面单"：
```json
{ "code": "channels", "value": ["dy", "pdd"], "queryType": "and" }
```

### 分页与排序

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `page_no` | int | 页码，从 1 开始 | 1 |
| `page_size` | int | 每页数量，最大 50 | 20 |
| `rank_type` | string | `ASC` 升序 / `DESC` 降序 | 默认排序 |
| `rank_field` | string | 排序字段（`df_price`、`fx_ord_cnt_30d` 等） | 默认排序 |

### 返回结构

```json
{
  "success": true,
  "data": {
    "total": 1486,
    "data": [
      {
        "offerId": "894529405810",
        "title": "户外便携式懒人充气沙发...",
        "dfPrice": 22.0,
        "dfPost": 2.53,
        "offerPic": "https://cbu01.alicdn.com/...",
        "fxOrdCnt30d": "120",
        "ordCnt30d": "280",
        "ciphertextInfoList": [
          { "name": "淘宝(菜鸟)", "key": "thyny" },
          { "name": "抖音", "key": "douyin" },
          { "name": "拼多多", "key": "pinduoduo" }
        ],
        "baseServiceInfo": {
          "isFreePost": false,
          "isYjdf": true,
          "isNoReasonToReturn7dFx": true
        }
      }
    ]
  }
}
```

> 商品数组在 `data.data`（外层 data 是接口返回，内层 data 是商品列表），`data.total` 是总数。

---

## 二、图搜选品

### MCP 工具调用参数

MCP 工具名：`same_img_offer_search`

调用时传入参数 `sceneSearchParamStr`，值为 **JSON 字符串**，内部结构如下：

```json
{
  "searchMode": "IMAGE_SEARCH",
  "sceneCode": "fxyx",
  "imageParam": {
    "imageAddress": "https://cbu01.alicdn.com/img/ibank/O1CN01tbX36m2DY14B3EBzK_!!2203087508620-0-cib.jpg"
  },
  "pageIndex": 1,
  "pageSize": 20,
  "keyword": "",
  "filter": [],
  "sortModel": null,
  "terminal": "PC"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `searchMode` | string | **是** | 固定传 `"IMAGE_SEARCH"` |
| `sceneCode` | string | **是** | 固定传 `"fxyx"`，不可省略 |
| `imageParam` | object | **是** | 图片参数对象（见下方说明） |
| `pageIndex` | int | 是 | 页码，默认 1 |
| `pageSize` | int | 是 | 每页数量，默认 20，最大 50 |
| `keyword` | string | 是 | 辅助关键词，无关键词时传空字符串 `""` |
| `filter` | array | 是 | 筛选条件列表，无筛选时传 `[]` |
| `sortModel` | object/null | 是 | 排序对象，无排序时传 `null`；有排序时传 `{"field": "price", "desc": true}` |
| `terminal` | string | **是** | 固定传 `"PC"` |

`imageParam` 字段说明：

| 字段 | 说明 |
|------|------|
| `imageAddress` | 图片 URL（与 `imageBase64` 二选一） |
| `imageBase64` | 图片 Base64 编码（与 `imageAddress` 二选一） |
| `region` | 主体圈选坐标，格式 `"x1,y1,x2,y2"`（可选） |

> **重要：`sceneCode` 必须始终传入 `"fxyx"`，`searchMode` 必须传 `"IMAGE_SEARCH"`，缺少则图搜接口无法正确识别场景。**

### CLI 调用

```bash
# 图片 URL 搜索
python3 scripts/cli.py product_search_helper search --image_url="https://example.com/sample.jpg"

# 图片 + 辅助关键词
python3 scripts/cli.py product_search_helper search --image_url="https://example.com/sample.jpg" --keyword="连衣裙"

# 图片 + 主体圈选
python3 scripts/cli.py product_search_helper search --image_url="https://example.com/sample.jpg" --region="100,100,300,400"
```

### 图片参数

| 参数 | 说明 | 备注 |
|------|------|------|
| `image_url` | 图片 URL 地址 | 用户给链接时使用 |
| `image_base64` | 图片 Base64 编码 | 用户直接给图片时使用 |
| `region` | 主体圈选坐标（可选） | 格式："x1,y1,x2,y2" |

> **二选一**：`image_url` 和 `image_base64` 至少传一个。

### 其他参数

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `page_no` | int | 页码 | 1 |
| `page_size` | int | 每页大小，最大 50 | 20 |
| `keyword` | string | 辅助关键词（可选） | - |
| `rank_field` | string | 排序字段（如 `price`） | - |
| `rank_type` | string | `ASC` / `DESC` | - |

### 返回结构

```json
{
  "success": true,
  "data": {
    "total": 100,
    "data": [
      {
        "offerId": 7890123456,
        "title": "2026新款夏季女装连衣裙",
        "offerPic": "https://cbu01.alicdn.com/...",
        "price": 39.9,
        "yjby": true,
        "ciphertextInfoList": [],
        "dfSalesForSort": null
      }
    ],
    "extendInfo": {
      "yoloCropRegion": "0.1,0.2,0.8,0.9"
    }
  }
}
```

**图搜特有字段**：
- `yjby`：是否一件代发包邮（true 时 price 为包邮价）
- `dfSalesForSort`：月代发销量（精确值，用于排序）
- `extendInfo.yoloCropRegion`：YOLO 模型识别的主体裁剪区域

> 图搜超时 60 秒（比关键词选品更长），商品字段与关键词选品一致，后续流程相同。

---

## 三、选品后处理规则

1. 按 SKILL.md 中的「选品数量策略」确定展示数量（用户指定 N 个 → 超量请求再精选 N 个）
2. **自动触发选品决策分析**（见下方）
3. 综合展示选品数据 + 参谋分析结果给用户
4. 询问用户确认要铺货的商品（可全选或选择部分）

---

## 四、选品决策分析

选品返回后，**自动**对候选商品批量查询分销参谋数据，综合分析后给出推荐。

### 执行步骤

1. 加载分销参谋参考文档：`read_file: scripts/biz/offer_info/reference.md`
2. 对每个候选商品调用分销参谋接口：
   ```bash
   python3 scripts/cli.py offer_info query --offer_id="{offerId}" --decision=true
   ```
3. 综合选品数据 + 参谋数据，生成推荐分析
4. 按推荐指数排序展示，询问用户确认铺货商品

### 推荐维度（正面因素）

| 维度 | 数据来源 | 判断标准 |
|------|----------|----------|
| 价格优势 | 选品 `dfPrice` + 参谋 `priceInInfo` | 一件包邮价低、分销专属价有折扣 |
| 包邮支持 | 参谋 `priceInInfo.onePieceFreePostage` | 一件包邮 > 多件包邮 > 不包邮 |
| 渠道匹配 | 参谋 `supportList` | 支持用户目标渠道的密文面单 |
| 高体验分 | 参谋 `downstreamPerformance.highExperienceScoreList` | 在目标渠道有高体验分 |
| 高履约率 | 参谋 `downstreamPerformance.highPerfectLgtRateList` | 在目标渠道有高完美履约率 |
| 服务保障 | 参谋 `protectionInfoList` | 有退换货保障、晚揽必赔等 |
| 代发数据 | 参谋 `adviseList` | 近30天代发量大、揽收率高 |
| 分销品 | 参谋 `alreadyUpgrade` | 已升级为分销品，铺货更顺畅 |

### 风险维度（负面因素）

| 维度 | 数据来源 | 判断标准 |
|------|----------|----------|
| 品牌未授权（严重） | 参谋 `brandInfo.isBrandOffer` + `isAuth` | 品牌商品但未授权，**不能铺货，有侵权风险**。必须引导用户申请授权 |
| 运费高 | 参谋 `freightInfo` | 非包邮且运费高，影响利润 |
| 起批量高 | 参谋 `priceInInfo.startNum` | 起批量过高不适合小卖家 |
| 渠道不匹配 | 参谋 `supportList` | 不支持用户目标渠道 |
| 包邮排除区域多 | 参谋 `priceInInfo.excludeAreaList` | 排除区域过多影响覆盖范围 |

### 展示格式

**每个商品必须包含商品链接**：`https://detail.1688.com/offer/{offerId}.html`，**链接必须嵌入到商品ID中**。offerId 从接口返回数据中获取（文搜和图搜都有返回 offerId 字段）。

```
### [{offerId}](https://detail.1688.com/offer/{offerId}.html) {title}

**推荐指数**：⭐⭐⭐⭐⭐（5/5）

**选品数据**：
- 代发价 ¥{dfPrice} | 邮费 ¥{dfPost} | 近30天分销订单 {fxOrdCnt30d}

**参谋分析**：
- ✅ 一件包邮，价格有竞争力
- ✅ 支持抖音、拼多多等 6 个渠道密文面单
- ✅ 近30天代发 9000+，48h揽收率 100%
- ✅ 有官方仓退货、晚揽必赔保障

**风险提示**：
- 🚫 品牌商品未授权，不能铺货，有侵权风险
- 👉 [申请品牌授权](https://air.1688.com/app/channel-fe/distribution-work/brand.html#/auth_apply?offerId={offerId})

**综合建议**：需先完成品牌授权申请后才能铺货
```

> **图搜字段映射**：图搜返回的字段名与文搜略有不同，但 `offerId` 和 `title` 是相同的。图搜中 `price` 对应文搜的 `dfPrice`，`yjby=true` 表示包邮。无论文搜还是图搜，商品链接的拼接方式都是 `https://detail.1688.com/offer/{offerId}.html`。

---

## 五、品牌授权检查（重要）

选品决策分析时，必须检查每个候选商品的品牌授权状态：

- **`isBrandOffer=true` 且 `isBrandAuth=false`**：该商品 **不能铺货**，有侵权风险
- 必须在展示时明确标记，并给出授权申请链接：
  `[申请品牌授权](https://air.1688.com/app/channel-fe/distribution-work/brand.html#/auth_apply?offerId={offerId})`
- 用户确认铺货时，**自动排除未授权品牌商品**，并提示用户原因

---

## 六、铺货后续触发逻辑

铺货完成后，若当前会话中有选品候选列表：

1. 检查候选列表中是否还有未铺货的商品
2. 如果有，主动询问用户：「还有 N 个商品未铺货，是否继续铺货？」
3. 用户确认后，跳过已铺货商品，继续铺货剩余商品
4. 重复直到所有商品处理完毕或用户主动停止