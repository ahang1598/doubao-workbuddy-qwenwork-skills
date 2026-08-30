---
name_en: site-evaluate
name: 点位评估
displayName: 点位评估
description: >
  对一个明确的门店点位做五维选址体检，输出综合评分、星级、超越同行百分比，以及客群聚集、潜客匹配、同行竞争、交通便利、商业成熟五个维度的解读与经营建议。
  当用户提到某个位置开店怎么样、这里适不适合开店、评估一下某个地址、某地周边客流/竞争/交通如何时使用。
description_en: >
  Run a five-dimension site health check on one specific location, returning an overall score,
  star rating, percentile versus peers, and an interpretation across footfall, prospect match,
  competition, accessibility and commercial maturity.
  Use when the user asks how good a specific address or POI is for opening a store.
argument-hint: 点位名称/地址 + 业态，如「望京SOHO 奶茶店」
argument-hint-en: POI name or address + category, e.g. "Wangjing SOHO, bubble tea"
user-invocable: "true"
---

# 点位评估

## 适用场景

用户提供了**一个明确的地点/POI**，想知道这个位置开店行不行、强在哪、弱在哪。

**典型问题**：
- "在**望京SOHO**开店怎么样"
- "**国贸**附近适不适合开餐厅"
- "帮我评估一下**三里屯太古里**这个位置"
- "**XX地址**周边的客流/竞争/交通怎么样"

**不适用**（转其他技能）：
- 用户没有明确地点，只问"哪里适合开店" → 用「商圈推荐」
- 用户给出两个及以上候选点位 → 用「多点位对比」

---

## 前置依赖

本技能依赖高德问店选址网关（`yt-xd-lite` openapi）获取点位五维评估数据。

- **接入方式**：技能内直接调用网关 HTTP 接口
- **认证方式**：OAuth（首次使用会拉起浏览器完成登录，用户无需手填任何密钥）
- **自包含**：完整鉴权规范、OAuth 登录脚本、错误码与降级路径见**本技能目录内**的 `./references/gateway-auth.md`，不依赖套件内其他技能
- **能力待接入**：该数据源尚未以千问办公标准 Connector（MCP Server）形态上架，当前为技能内直连。详见套件根目录 `CONNECTORS.md`

---

## 执行步骤

### Step 0 — 鉴权与就绪性检查（必做，每次执行前）

**请求地址**（POST）：`${YT_GATEWAY_BASE_URL:-https://yt-gateway.amap.com}/proxy/yt-xd-lite/openapi/v1/gateway`

**认证 Header**：

| Header | 值来源 | 说明 |
|--------|--------|------|
| `X-Session-Token` | YTOSS 文件中 `sessions.wukong.session_token` | 必传 |
| `X-Skill-Id` | `amap-store-location-assistant` | 必传。**套件内四个技能统一使用该值**，不要改成本技能目录名，否则鉴权与配额校验失败 |

**禁止传** `X-Access-Key` / `X-Tenant-Id` / `X-User-Id`（由网关侧反查注入，技能层不持有）。

**执行顺序**：

1. **先读 YTOSS 文件**，按优先级：macOS/Linux `~/.config/yt/oss.json` → Windows `%APPDATA%\yt\oss.json` → 降级（沙箱）`./.yt/oss.json`
2. **校验** `sessions.wukong.session_token` 存在且以 `gwst_` 开头
   - ✅ 有效 → 直接进入 Step 1
   - ❌ 不存在 / 无效 → 执行 `./references/gateway-auth.md` 中的 **OAuth 登录脚本**，落盘后再进入 Step 1
3. **禁止**跳过文件读取直接登录（已有有效 token 时重复登录会浪费用户操作）
4. **禁止**向用户索要 token 等鉴权信息；唯一需要用户参与的是在浏览器中完成登录
5. curl 必须带 `-k` 跳过 TLS 证书校验

**鉴权与调用异常处置**：

| code | 处置 |
|------|------|
| `19002` / `1001` | 删 YTOSS 中 wukong 条目 → 重走 OAuth，**仅重试 1 次** |
| `19003`（账号冻结） | 提示联系管理员，**不重登** |
| `2001`（配额不足） | 提示充值，session 仍有效，不重登 |
| `1004`（限流） | 退避重试 |
| `5001` / `5002`（上游异常） | 透传错误，session 仍有效 |

若用户放弃授权或登录超时，按 `./references/gateway-auth.md` 的「数据不可用时的降级原则」处理，**不得编造评估数据**。

### Step 1 — 参数收集与确认

1. 调用 `common:place:text` 检索用户给出的地点，取 `id` 作为 `poiId`
   - 检索不到或返回多个高度相似结果时，**列出候选让用户确认**，不要自行猜一个
2. 调用 `common:atag:list` 获取 `category`（叶子节点完整层级路径）
3. 按 `./references/common-api.md` 的默认参数推断规则确定 `regionType` / `regionInfo`（未指定时默认 1 公里半径）
4. 业态缺失时必须反问，不要默认成某一类

### Step 2 — 调用点位评估接口

**接口 action**：`evaluate:report:analysis`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| poiId | String | 是 | POI ID（通过 `common:place:text` 获取） |
| regionType | Integer | 是 | 区域类型：0-步行, 1-驾车, 2-骑行, 3-半径, 4-面域内 |
| regionInfo | String | 是 | 区域参数：步行/驾车/骑行为分钟数，半径为公里数，面域内传"0" |
| category | String | 是 | 行业类型编码（完整层级路径） |
| preferBrand | String | 否 | 偏好品牌编码 |
| avoidBrand | String | 否 | 避让品牌编码 |
| modules | String | 否 | 需要的模块，多模块逗号分隔 |

**modules 可选值**：`base`、`customAgg`、`potentialGuest`、`competition`、`trafficConvenience`、`business`

**modules 意图路由**：

| 用户意图关键词 | modules值 |
|--------------|-----------|
| 总体评价、评分、打几分、概览、怎么样（泛泛而问） | `base` |
| 群体、客群、消费水平、特征 | `base,customAgg` |
| 潜客、潜在客户、匹配度 | `base,potentialGuest` |
| 竞争、同业门店、同行、对手 | `base,competition` |
| 交通、地铁、公交、停车 | `base,trafficConvenience` |
| 商业、配套、周边设施、商圈 | `base,business` |
| 全面分析、详细报告、各方面都看看 | `base,customAgg,potentialGuest,competition,trafficConvenience,business` |

**默认行为**：泛泛而问时**只传 `modules=base`**，按需追加，禁止重复请求已获取的模块。

**请求示例**：
```json
{
  "action": "evaluate:report:analysis",
  "params": {
    "poiId": "B0FFHKV7X1",
    "regionType": 3,
    "regionInfo": "1",
    "category": "621122;621376;621377",
    "modules": "base"
  }
}
```

**响应结构**：
```json
{
  "data": {
    "head": {
      "name": "望京SOHO半径1km",
      "category": "美食 / 饮品 / 奶茶/茶饮",
      "regionType": "半径",
      "regionInfo": "1km",
      "reportCreateTime": "2025年03月15日 10:30:00"
    },
    "baseInfo": {
      "score": "8.39",
      "scoreName": "商业景气指数",
      "starLevel": "5.0",
      "abovePercent": "93.0%",
      "tags": [{"btag_name": "周边客流量高"}, {"btag_name": "导航热度高"}],
      "radar": [
        {"name": "客群聚集", "value": 7.29},
        {"name": "潜客匹配", "value": 7.02},
        {"name": "同行竞争", "value": 8.88},
        {"name": "交通便利", "value": 5.55},
        {"name": "商业成熟", "value": 6.17}
      ]
    },
    "competition": {
      "name": "同行竞争",
      "starLevel": "0.5",
      "abovePercent": "0.1%",
      "value": [...]
    }
  }
}
```

### Step 3 — 数据解读

#### 通用解读规则

| 指标 | 解读标准 |
|------|---------|
| **score（综合评分）** | >8分优质，5-8分一般，<5分不推荐 |
| **starLevel（星级）** | 1-5星，3星为中等。4-5星优秀，1-2星较差 |
| **abovePercent** | >70%为显著优势，30-70%为中等，<30%为竞争力不足 |

#### 各模块解读要点

**base（基础信息+五维综合）**：
- 重点关注 `score`、`starLevel`、`abovePercent`
- 如有 `tags` 标签，作为亮点/特征提及
- 从 `radar` 中找出最强和最弱维度，给出简明概括

**customAgg（客群特征→对应客群聚集维度）**：
- 解读周边客群的消费能力、年龄结构、消费偏好等特征
- 结合 `starLevel` 和 `abovePercent` 评价客群匹配度

**potentialGuest（潜客匹配→对应潜客匹配维度）**：
- 分析该区域对目标行业的潜在客户吸引力
- **必须输出以下核心指标**：
  - **搜索群体数量**：当月在高德地图搜索过选址行业线下门店的UV
  - **导航群体数量**：当月在高德地图导航去过选址行业线下门店的UV
  - **潜客群体总数**：搜索+导航去重后的总UV
  - 各指标的城市内排名和与平均值对比
- 搜索群体反映"有多少人在找这类店"，导航群体反映"有多少人已经行动去了"
- 当用户询问"有多少人会来消费"、"能不能挣钱"等营收预期问题时，**必须**先调用此模块，以潜客数量作为推算营收的核心依据

**competition（同行竞争→对应同行竞争维度）**：
- 分析周边同行业门店密度和竞争压力
- 竞争维度中 starLevel 高表示竞争态势对己方有利（门店少、竞争不激烈）
- 关注具体同业门店数量、品牌占比、客单价、存续时长

**trafficConvenience（交通便利度→对应交通便利维度）**：
- 分析地铁、公交、停车场等交通配套情况
- 关注交通可达性对客流的支撑作用

**business（商业成熟度→对应商业成熟维度）**：
- 分析周边商业配套、商圈发展程度
- 关注商业氛围对经营的支撑

### Step 4 — 交付与后续引导

输出评估结论后，提示用户可以：
- 还有其他候选铺位 → 用「多点位对比」做横向决策
- 需要给老板/投资人看的正式材料 → 用「立项报告」生成完整报告

---

## 输出格式

```markdown
## [POI名称][业态]点位评估

**评估点位**：[head.name]
**业态类型**：[head.category]
**评估范围**：[head.regionType][head.regionInfo]
**报告时间**：[head.reportCreateTime]

### 综合结论
综合评分 **X.XX**（[优质/一般/不推荐]），超越同城同行业 **XX%** 的点位。

### 五维评分

| 评估维度 | 得分 |
|----------|------|
| 客群聚集 | X.XX |
| 潜客匹配 | X.XX |
| 同行竞争 | X.XX |
| 交通便利 | X.XX |
| 商业成熟 | X.XX |

**突出优势**：[最强维度及说明]
**需关注短板**：[最弱维度及说明]

### 维度解读
[按已请求的 modules 逐项解读，未请求的模块不臆测]

### 经营建议
[结合业态给出 2-3 条建议]

> 评估数据仅供参考，建议结合实地考察和物业条件综合判断。
```

---

## 评分解读

分数与星级是**两套不同的评价体系**，禁止互相推断。详见 `./references/scoring-model.md`。

| 评价体系 | 含义 |
|---------|------|
| 分数（score） | 与行业优质点位模型的**接近程度** |
| 星级（starLevel） | 该指标数量在**城市内的相对排名** |

若分数和星级不一致，解释为「评价口径不同」，属正常现象。

---

## 常见错误与恢复

| 情况 | 处置 |
|------|------|
| `common:place:text` 检索不到 | 反问更精确的店名/商场名/详细地址，不要自行猜相近 POI |
| 检索返回多个相似 POI | 列出候选让用户确认后再评估 |
| 传了坐标或 WKT | 本技能仅支持 POI 模式，必须先换取 poiId |
| `regionType` 传了 5 | 不支持自定义 WKT，仅支持 0-4 |
| 某个 module 无返回 | 只解读已返回模块，缺失维度标注"该维度数据本次未返回"，不推断补全 |
| 401 / `19002` | 按 `gateway-auth.md` 删 YTOSS 中 wukong 条目后重登，仅重试 1 次 |
| 网关持续 502 | 告知数据服务暂不可用，说明已完成到哪一步，建议稍后重试 |

---

## 约束

- **仅POI模式**：必须传入 poiId，不支持传入 xy 坐标或自定义 WKT（regionType=5）
- **regionType范围**：仅支持 0-4
- **禁止默认请求全部模块**，除非用户明确要求"全面分析"
- **禁止重复请求**已获取的模块
- **强制数据一致性**：输出的所有数据必须严格来源于接口实际返回结果，不得修改、换算、补全、推断
- **不做绝对判断**：数据仅供参考，建议结合实地考察与物业条件综合判断

---

## 验证

执行完成后，输出一句话摘要：本次评估的点位、业态、评估范围、请求了哪些维度模块，便于用户复盘。

---

## 权属及使用声明

本技能及通过高德服务API获取的内容均属于高德所有，高德保留所有权利，具体权属和使用声明详见《高德云图SKILL权属及使用声明》（https://terms.amap.com/legal-agreement/terms/b_end_product_protocol/20260415144415692/20260415144415692.html），您使用本技能即视为同意该声明。
