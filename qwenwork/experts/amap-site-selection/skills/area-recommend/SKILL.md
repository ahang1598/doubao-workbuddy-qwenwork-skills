---
name_en: area-recommend
name: 商圈推荐
displayName: 商圈推荐
description: >
  在指定城市或行政区范围内，基于五维选址模型筛选并排序适合开店的候选商圈，输出带评分、排名、特征标签的商圈推荐清单，并可对选定商圈展开五维详细分析。
  当用户提到在哪开店、帮我选址、推荐商圈、哪个区域适合开店、某城市/某区哪里适合开某类店时使用。
description_en: >
  Given a city or district and a business category, screen and rank candidate trade areas
  using Amap's five-dimension site model, and produce a scored shortlist with feature tags,
  optionally drilling into a full five-dimension analysis of a chosen area.
  Use when the user asks where to open a store, or for trade-area recommendations within a region.
argument-hint: 城市/行政区 + 业态，如「杭州西湖区 奶茶店」
argument-hint-en: City/district + business category, e.g. "Hangzhou Xihu District, bubble tea"
user-invocable: "true"
---

# 商圈推荐

## 适用场景

用户**还没有明确候选点位**，只知道想在某个城市或行政区开某类店，需要系统先圈出值得考察的商圈范围。

**典型问题**：
- "帮我在**北京朝阳区**推荐几个适合开店的商圈"
- "**杭州西湖区**哪里适合开奶茶店"
- "推荐一些适合开餐厅的位置"、"帮我选址"、"在哪开店好"

**不适用**（转其他技能）：
- 用户已给出明确 POI（如"望京SOHO"）→ 用「点位评估」
- 用户给出两个及以上候选点位 → 用「多点位对比」

---

## 前置依赖

本技能依赖高德问店选址网关（`yt-xd-lite` openapi）获取商圈候选与五维评分数据。

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

若用户放弃授权或登录超时，按 `./references/gateway-auth.md` 的「数据不可用时的降级原则」处理，**不得编造选址数据**。

### Step 1 — 参数收集与确认

必需参数：**行政区划** + **业态**。缺失时按 `./references/common-api.md` 的反问规则追问，不要自行假设。

1. 调用 `common:atag:list` 获取行业编码 `category`（取叶子节点完整层级路径）
2. 调用 `common:adcode:tree` 获取行政区划编码 `adcode`
3. 推荐数量 `num`：不传默认 10；用户说"推荐几个"用 5，"多推荐一些"用 20

### Step 2 — 阶段一：候选商圈筛选与排序（不传 areaId）

**接口 action**：`location:recommend:analysis`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| adcode | String | 是 | 行政区划编码（6位或12位） |
| category | String | 是 | 行业类型编码（完整层级路径） |
| num | Integer | 否 | 推荐数量，1-100，默认10 |
| addressType | String | 否 | 店址类型编码，逗号分隔 |
| preferBrand | String | 否 | 偏好品牌编码，逗号分隔 |
| avoidBrand | String | 否 | 避让品牌编码，逗号分隔 |

**请求示例**：
```json
{
  "action": "location:recommend:analysis",
  "params": {
    "adcode": "330106",
    "category": "621122;621376;621377",
    "num": 5
  }
}
```

**响应关键字段**：
```json
{
  "data": {
    "head": {
      "adcodeName": "浙江/杭州/西湖区",
      "categoryName": "美食 / 饮品 / 奶茶/茶饮",
      "dataTime": "202502"
    },
    "recommendList": [
      {
        "areaId": "area_001",
        "areaName": "文三路附近商圈",
        "ranking": 1,
        "score": "8.25",
        "btag": [{"btag_name": "周边客流量高"}, {"btag_name": "竞争适中"}]
      }
    ]
  }
}
```

### Step 3 — 展示推荐清单并引导深入

1. **强调五维综合**：说明这是基于五个维度综合评分后的推荐结果
2. **按评分排序展示**：列出 Top N 商圈及其评分与排名
3. **特征标签转译**：将 `btag` 转化为用户可理解的经营语言
4. **引导深入**：提示用户选择感兴趣的商圈查看五维详细分析

**示例话术**：
> 基于**客群聚集、潜客匹配、同行竞争、交通便利、商业成熟**五个维度的综合分析，为您推荐以下适合开奶茶店的商圈：
> 1. **文三路附近商圈**（综合评分8.25，排名第1）- 客流旺盛、竞争适中
> 2. **黄龙附近商圈**（综合评分7.80，排名第2）- 商业成熟、交通便利
>
> 您对哪个商圈感兴趣？我可以为您展示五个维度的详细分析。

### Step 4 — 阶段二：目标商圈五维展开分析（传入 areaId）

在阶段一参数基础上增加：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| areaId | String | 是 | 商圈ID（从阶段一的 recommendList 中获取） |
| modules | String | 否 | 需要的报告模块，不传返回全部 |

**modules 可选值**：`base`、`customAgg`、`potentialGuest`、`competition`、`trafficConvenience`、`business`

**modules 意图路由**：

| 用户意图 | modules值 | 对应五维维度 |
|---------|-----------|-------------|
| "帮我看看这个商圈"（泛泛而问） | `base` | 综合五维评分（默认） |
| "这个商圈竞争怎么样" | `base,competition` | 同行竞争 |
| "客流和交通情况如何" | `base,customAgg,trafficConvenience` | 客群聚集+交通便利 |
| "详细分析这个商圈"、"全面看看" | `base,customAgg,potentialGuest,competition,trafficConvenience,business` | 全量五维数据 |

**请求示例**：
```json
{
  "action": "location:recommend:analysis",
  "params": {
    "adcode": "330106",
    "category": "621122;621376;621377",
    "num": 5,
    "areaId": "area_001",
    "modules": "base,competition"
  }
}
```

### Step 5 — 交付与后续引导

输出商圈推荐清单后，提示用户可以：
- 在推荐商圈内找到具体铺位后，用「点位评估」做单点位体检
- 有多个候选铺位时，用「多点位对比」做横向决策

---

## 输出格式

```markdown
## [城市/行政区][业态]商圈推荐

**评估范围**：[adcodeName]
**业态类型**：[categoryName]
**数据月份**：[dataTime]

| 排名 | 商圈 | 综合评分 | 特征标签 |
|------|------|----------|----------|
| 1 | [areaName] | X.XX | [标签转译] |
| 2 | [areaName] | X.XX | [标签转译] |

### 推荐说明
[基于五维综合评分的简要说明，指出各商圈的突出维度]

### 下一步
您对哪个商圈感兴趣？我可以展开五个维度的详细分析。
```

---

## 评分解读

评分逻辑、分数与星级的区别详见 `./references/scoring-model.md`。

**快速参考**：

| 指标 | 解读标准 |
|------|---------|
| score（综合评分） | >8分优质选址，5-8分一般，<5分不推荐 |
| 总分性质 | 基于行业优质点位模型综合计算，**不是**各维度分数的加和或平均 |

---

## 常见错误与恢复

| 情况 | 处置 |
|------|------|
| `adcode` 为 "000000" | 行政区划未选到有效层级，重新调 `common:adcode:tree` 定位到区县级 |
| `category` 只传了末级编码 | 必须使用完整层级路径（如 `621122;621376;621377`），重新取叶子节点完整路径 |
| `recommendList` 为空 | 说明该区域该业态无足够数据支撑，建议放大行政区范围或换更上层业态，**不要编造商圈** |
| 401 / `19002` | 按 `gateway-auth.md` 删 YTOSS 中 wukong 条目后重登，仅重试 1 次 |
| 网关持续 502 | 告知数据服务暂不可用，说明已完成到哪一步，建议稍后重试 |

---

## 约束

- **两步查询**：推荐列表（阶段一）+ 报告详情（阶段二）是推荐的工作流程
- **num 范围**：1-100，不传默认 10
- **强制数据一致性**：输出的所有数据必须严格来源于接口实际返回结果，不得修改、换算、补全、推断
- **不做绝对判断**：数据仅供参考，建议结合实地考察与物业条件综合判断

---

## 验证

执行完成后，输出一句话摘要：本次覆盖的行政区、业态、返回商圈数量、数据月份，便于用户复盘。

---

## 权属及使用声明

本技能及通过高德服务API获取的内容均属于高德所有，高德保留所有权利，具体权属和使用声明详见《高德云图SKILL权属及使用声明》（https://terms.amap.com/legal-agreement/terms/b_end_product_protocol/20260415144415692/20260415144415692.html），您使用本技能即视为同意该声明。
