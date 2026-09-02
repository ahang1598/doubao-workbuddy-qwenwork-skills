---
name: linkfox-1688-source-profiler
description: 1688 货源匹配与利润核算全流程。输入一个亚马逊 ASIN，自动通过 SIF 反查关键词 → 前台搜索获取候选商品 → AIGC 智能推导 1688 搜索词和价格区间 → B1 店雷达 + B2 以图搜图两路并行 → AIGC 多模态验证 → 11 项全量成本净利润核算。当用户提到1688货源匹配、找货源、利润核算、成本拆解、批发价反推、货源验证、1688 sourcing, profit calculation, cost breakdown, supplier matching时触发此技能。
---

# 1688 Source Profiler — 货源匹配与利润核算

输入一个亚马逊 ASIN，自动完成 SIF 关键词反查 → 前台搜索 + 并行预取 → AIGC 智能推导 → 两路并行采集 → AIGC 验证 → 利润核算，输出完整的货源对比 + 成本拆解 + 净利润报告。

## 工作流程

```
输入：ASIN
  ↓
Step 1：SIF 关键词反查 → 取 isMainKw/isAccurateKw 标签词 Top 5
  ↓
Step 2：用相关性最高的词前台搜索 1 页（取 Top 10 ASIN + imageUrl）
  同时并行：Keepa 商品详情 + Keepa 历史时序（取正常售价）+ SIF 流量概览 + 极目 niche 数据
  ↓
Step 3：AIGC 智能入参推导（Top 9 商品图 + 目标 ASIN 主图 → keyWord + 价格区间）
  ↓
Step 4：B1 店雷达 + B2 以图搜图 两路并行
  ↓
Step 5：AIGC 验证（标题预筛选 → 多模态对比）
  ↓
Step 6：利润核算（零广告策略 + 11 项全量成本 + FBA 费率查表，含极目 ACoS/退货率）
  ↓
Step 7：结果展示（B1+B2 并列，用户决策）
```

## Step 1 — 关键词反查（SIF → 卖家精灵 → JungleScout 三级兜底）

**首选**：调用 `linkfox-sif-asin-keywords`，参数：

```json
{"asin": "<ASIN>", "site": "US"}
```

从返回的关键词列表中，筛选 `isMainKw: true` 或 `isAccurateKw: true` 的词，按流量占比（trafficShare）降序排列，取 Top 5。

**二级兜底**：当 SIF 返回 `errcode≠200`、关键词列表为空、或无 `isMainKw`/`isAccurateKw` 标签词时，调用 `linkfox-sellersprite-traffic-keyword`：

```json
{"asin": "<ASIN>", "marketplace": "US", "trafficKeywordTypes": "primary,precise", "orderField": "purchaseRate", "orderDesc": true, "size": 50}
```

从返回的关键词列表中，取购买率最高的 Top 5。

**三级兜底**：当卖家精灵也返回空结果时，调用 `linkfox-junglescout-keyword-by-asin`：

```json
{"asin": "<ASIN>", "marketplace": "US"}
```

从返回的关键词列表中，取搜索量最高的 Top 5。

→ 得到：`精准关键词集合`（Top 5，含 keyword / translateKeyword / weeklySearchVolume / trafficShare）

## Step 2 — 前台搜索 + 新品筛选 + 多 ASIN 并行预取

**主调用**：用 Step 1 精准词集合 Top 1 做前台搜索，调用 `linkfox-amazon-search` 搜索首页（page 1，默认排序）：

> **选词规则**：SIF 路径取 trafficShare（流量占比）最大的词；卖家精灵兜底路径取 purchaseRate（购买率）最大的词。搜索量大不代表与该 ASIN 相关（可能是泛词或大品类词），trafficShare 反映该词对此 ASIN 的实际流量贡献，purchaseRate 反映搜索该词的用户购买意愿强度。

```json
{"keyword": "<精准词>", "amazonDomain": "amazon.com", "language": "en_US", "page": 1}
```

从返回结果中过滤 `sponsored: false`，按 `monthlySalesUnits` 降序取 Top 10，提取 `asin` + `title` + `extractedPrice` + `imageUrl` + `ratings` + `monthlySalesUnits`。Top 10 用于 Step 3 的 AIGC 入参推导（Top 9 竞品图）。

**新品筛选**（从首页全部非广告商品中，排除用户 ASIN）：
1. 取首页全部非广告商品
2. 按 `ratings`（评论数）升序排列
3. 取评论数最少的前 3 个

> **注意**：新品筛选范围是首页全部非广告商品，不是 Top 10。评论数最少的商品可能月销量为 0，排不进 Top 10，但正是我们要找的目标。

→ 得到：`新品 ASIN 列表`（最多 3 个）
→ **目标 ASIN 列表** = [用户 ASIN] + 新品 ASIN 列表（共 1-4 个）

**同时并行**（对目标 ASIN 列表中每个 ASIN 都做 Keepa + SIF，极目 niche 共享只做 1 次）：

| 调用 | 参数 | 产出 |
|------|------|------|
| `linkfox-keepa-product-request` × N | `{"asin": "<每个目标ASIN>", "domain": 1, "history": 0}` | fbaFees / referralFeePercentage / imageUrl / packageLength / packageWidth / packageHeight / packageWeight / categoryTreeId |
| `linkfox-keepa-product-series` × N | `{"asin": "<每个目标ASIN>", "domain": 1}` | buyboxPrice 曲线 → 取**正常售卖价**（非秒杀价） |
| `linkfox-sif-asin-summary` × N | `{"searchValue": "<每个目标ASIN>", "country": "US"}` | sponsoredProductsKeywordCount（零广告判断） |
| `linkfox-jiimore-get-niche-info-by-keyword` | `{"keyword": "<精准词>", "countryCode": "US", "page": 1, "pageSize": 50, "sortField": "unitsSoldT7", "sortType": "desc"}` | returnRateAnnual（退货率，小数0-1）/ acos（ACoS，小数0-1）→ 转为百分比用于 nicheTACoS |

> N = 目标 ASIN 列表长度（1-4）

> **⚠️ 售价取值规则（利润核算必须遵守）**：利润核算中的售价**不能直接用 Keepa 商品详情的 `price` 字段**（该字段可能命中秒杀/促销价）。必须从 `linkfox-keepa-product-series` 的 `buyboxPrice` 曲线中取**正常售卖价格**（非秒杀价）。判断方法：`buyboxPrice` 曲线中会出现两个价格水平交替（如 $44.99↔$49.99），较低的是 Deal/促销价，较高的是正常 Buy Box 价。取较高的那个作为利润核算售价。若曲线只有一个价格水平，直接取该值。

→ 得到：Top 10 候选商品 + 目标 ASIN 列表的 Keepa 商品详情 + Keepa 正常售价 + SIF 零广告判断 + 极目 niche 数据

## Step 3 — AIGC 智能入参推导（多 ASIN 并行）

对目标 ASIN 列表中的**每个 ASIN**，用相同的 Top 9 竞品商品图 + 该 ASIN 自己的主图（Keepa 的 imageUrl，共 10 张），调用 `linkfox-aigc-textgen` 做三合一分析。N 个 ASIN 并行发起 N 个 AIGC 调用。

prompt 模板见 `references/aigc-prompt-templates.md`。

产出（每个 ASIN 各一组）：
- **keyWord**：AIGC 推荐的 1688 中文搜索词（1 个品类词 + 1 个特征词，≤ 20 字符）
- **beginPrice / endPrice**：基于 AIGC 选出的视觉相似 ASIN 的 min/max 价格反推

价格反推公式：

> **核心逻辑**：Amazon 售价中，1688 批发采购成本通常占 25%~33%（即 1/4 ~ 1/3），剩余部分覆盖 FBA 费、佣金、头程、广告、利润等。用这个比例从 Amazon 售价反推 1688 批发价范围，再乘以汇率转成人民币（CNY）。

**输入定义**（全部来自 AIGC 任务2 的输出）：
- `similarMinPrice`：AIGC 判断为「部分匹配」及以上（含「匹配」+「部分匹配」）的所有候选 ASIN 中，**Amazon 售价的最低值**（USD）
- `similarMaxPrice`：同上候选中，**Amazon 售价的最高值**（USD）
- **关键**：不要只取「匹配」的候选——「匹配」通常很少（1-2 个），会导致价格区间过窄。必须纳入「部分匹配」候选扩大范围

**计算公式**：
```
汇率 = 7.2（CNY/USD）

beginPrice(CNY) = floor(similarMinPrice(USD) × (1/4) × 汇率) = floor(similarMinPrice × 1.8)
endPrice(CNY)   = ceil(similarMaxPrice(USD) × (1/3) × 汇率)  = ceil(similarMaxPrice × 2.4)
```

**系数解释**：
- `1/4`（下限系数）：1688 批发价 ≈ Amazon 售价的 25%。低于此价的货源质量可疑（尾货/次品）
- `1/3`（上限系数）：1688 批发价 ≈ Amazon 售价的 33%。高于此价利润空间不足
- `7.2`：CNY/USD 汇率，与利润核算脚本 `--exchange-rate` 保持一致

**完整示例**：
AIGC 判断 9 个候选中 4 个匹配/部分匹配，Amazon 售价分别为 $9.99 / $14.44 / $22.98 / $27.99
- similarMinPrice = $9.99, similarMaxPrice = $27.99
- beginPrice = floor(9.99 × 1.8) = **¥17**
- endPrice = ceil(27.99 × 2.4) = **¥68**

**边界情况处理**：

| 情况 | 处理方式 |
|------|---------|
| 只有 1 个匹配（min=max） | endPrice 放宽到 ceil(price × 3.0)（上限再上浮 25%） |
| 全部 9 个都不匹配 | 回退用品类全量价格区间（从搜索结果 extractedPrice 取 min~max） |
| 价格区间跨度过大（max/min > 5） | 仅取「匹配」候选（不含「部分匹配」）；若仍过大取中位数±30% |
| beginPrice < 1 | 设为 1 |
| endPrice > 9999 | 设为 9999 |

## Step 4 — B2 以图搜图 + B1 店雷达 两路并行采集（多 ASIN）

对目标 ASIN 列表中的**每个 ASIN**，并行发起 B2 以图搜图（优先，精准度高）+ B1 店雷达关键词搜索（补充，扩大范围）。N 个 ASIN 共 2N 个并行调用。

**B2 以图搜图**（`linkfox-1688-search-by-image`，优先）：
```json
{"imageUrl": "<该ASIN的主图URL>", "pageSize": 10}
```

**B1 店雷达关键词搜索**（`linkfox-dld-product-search`，补充）：
```json
{"keyWord": "<该ASIN的AIGC推荐搜索词>", "searchType": 1, "cycle": "30", "sortField": "saleCount30d", "sortType": "desc", "companyType": 2, "beginPrice": <反推下限>, "endPrice": <反推上限>, "pageSize": 20}
```

> `searchType: 1` 为模糊匹配（默认）。AIGC 推荐的搜索词已经很精准，模糊匹配能覆盖更多相关货源。

## Step 5 — AIGC 验证（多 ASIN，B1+B2 均需验证）

对目标 ASIN 列表中的**每个 ASIN**，将 B2 和 B1 的候选**合并后统一做 AIGC 验证**：

1. **标题预筛选**（`python scripts/title_prefilter.py`）：B1/B2 结果标题必须包含品类词，过滤明显不相关的
   ```bash
   python scripts/title_prefilter.py <1688_json_file> --category-word "<品类词>" --source <B1|B2>
   ```
2. **AIGC 批量多模态验证**：将每个 ASIN 的 B1 和 B2 预筛后候选合并，**一次调用** `linkfox-aigc-textgen`（批量传入 N-1 张 1688 候选图 + 1 张该 ASIN 的 Amazon 目标图），判断每个候选的匹配/部分匹配/不匹配
3. 保留匹配和部分匹配的，**每个 ASIN 只取 AIGC 相关性最高的 Top 3 个 1688 货源**（按 AIGC 判断的匹配度排序：匹配 > 部分匹配）

> **B2 优先逻辑**：B2 以图搜图用 Amazon 主图直接搜 1688，精准度高于 B1 关键词搜索。当 B2 结果中有"匹配"级别的候选时，优先保留 B2 的候选；B1 的候选作为补充。

prompt 模板见 `references/aigc-prompt-templates.md` 第 2 节（批量验证模板）。

### B1 搜索词优化兜底（B1+B2 验证效果不佳时触发）

当某个 ASIN 经过 Step 5 AIGC 验证后，**验证通过的 1688 货源不足 3 个**（含 0 个）时，用 Google AI 概览优化 B1 搜索词后重新搜索：

1. 调用 `linkfox-ai-mode-google-search`，用 Amazon 商品标题 + "1688 批发 货源 工厂 一件代发 中国供应商" 作为搜索词：
   ```json
   {"keyword": "<Amazon商品标题> 1688 批发 货源 工厂 一件代发 中国供应商"}
   ```
2. 从 Google AI 概览中提取更精准的 1688 搜索词建议（AI 会推荐拆分关键词、同义词、产地关键词等）
3. 用优化后的搜索词**重新调用 B1 店雷达搜索**（`linkfox-dld-product-search`），获取新的 1688 候选
4. 对重新搜索的结果**同样做 AIGC 多模态验证**，验证通过后合并到该 ASIN 的 Top 3 候选中

> **注意**：Google AI Mode 不直接返回 1688 商品，只提供搜索词优化建议。优化后的 B1 搜索仍需走完整的 AIGC 验证流程。

## Step 6 — 利润核算 + 综合推荐排序

**禁止手动计算，必须通过脚本执行**：`python scripts/step_4_calc_profit.py`（脚本从落盘 JSON 读取数据，输出成本拆解 JSON + 综合推荐列表 + stderr 参数来源日志）。

### 数据传递说明

| 脚本参数 | 来源步骤 | 来源文件 | 说明 |
|---------|---------|---------|------|
| `--keepa-files` | Step 2 | Keepa 商品详情 JSON（多个 ASIN 的文件，空格分隔） | FBA 费/佣金/包装尺寸/主图 |
| `--keepa-history-file` | Step 2 | Keepa 历史时序 JSON（`linkfox-keepa-product-series` 落盘文件） | 从 buyboxPrice 曲线取正常售价 |
| `--alibaba-files` | Step 5 | AIGC 验证后保留的 1688 候选 JSON（多个 ASIN 的文件，空格分隔） | 1688 货源价格，按销量降序不截断 |
| `--market-metrics-file` | Step 2 | 极目 niche JSON（`linkfox-jiimore-get-niche-info-by-keyword` 落盘文件） | 退货率/ACoS |
| `--sif-summary-file` | Step 2 | SIF 流量概览 JSON（多个 ASIN 的文件） | 零广告策略判断 |
| `--amazon-search-file` | Step 2 | 亚马逊搜索结果 JSON（`linkfox-amazon-search` 落盘文件） | monthlySalesUnits（综合推荐排序用） |
| `--niche-keyword` | Step 1 | SIF 精准词 Top 1 | 指定匹配哪个 niche 的指标 |
| `--recommend-top` | — | 默认 5 | 综合推荐列表长度 |

> **Step 3 → Step 4 传递**：AIGC 三合一分析输出的 `keyWord` + `beginPrice`/`endPrice` 直接填入 Step 4 的 B1 调用参数（agent 读取 AIGC 输出文本解析）。
> **Step 5 → Step 6 传递**：AIGC 验证后保留的候选商品列表写入 JSON 文件，作为 `--alibaba-files` 参数传入脚本。每个 JSON 文件**必须在顶层包含 `_target_asin` 字段**指定目标 ASIN，脚本优先按此字段匹配（避免文件顺序与 ASIN 顺序不一致导致错配）。

### 完整脚本调用命令

```bash
python scripts/step_4_calc_profit.py \
    --keepa-files <ASIN1_keepa.json> <ASIN2_keepa.json> <ASIN3_keepa.json> <ASIN4_keepa.json> \
    --keepa-history-file <Step2_keepa_product_series.json> \
    --alibaba-files <ASIN1_1688.json> <ASIN2_1688.json> <ASIN3_1688.json> <ASIN4_1688.json> \
    --market-metrics-file <Step2_jiimore_niche.json> \
    --sif-summary-file <Step2_sif_asin_summary.json> \
    --amazon-search-file <Step2_amazon_search.json> \
    --niche-keyword "<Step1_SIF精准词Top1>" \
    --recommend-top 5
```

> 注意：`--exchange-rate`（默认 7.2）、`--fba-head-cost`（默认 3.0）、`--ad-tacos`（默认 10.0）、`--default-return-rate`（默认 15.0）为可选参数，有合理默认值。弃置费/仓储费/入库配置费已移除命令行参数，由 `determine_fba_size_tier()` 根据 Keepa 包装尺寸自动查表（`references/fba-fee-table.md`）。

### 综合推荐排序逻辑

脚本在完成所有 ASIN 的利润核算后，自动执行跨 ASIN 综合推荐排序：

1. **每个 ASIN 只取利润最高的 1 个 1688 货源**（避免同一 ASIN 占多个推荐位）
2. **计算综合得分**：`综合得分 = 净利润 × 亚马逊月销量`（预期月净利润）
   - 直观含义：如果用这个 1688 货源去卖这个亚马逊 ASIN，每月能赚多少钱
   - 亚马逊月销量优先从搜索结果获取，不在搜索结果中的 ASIN 从 Keepa `monthlySalesUnits` 补充
3. **排序**：按综合得分降序排列
4. **输出 Top N**：取前 `--recommend-top` 条作为推荐列表

输出 JSON 中增加 `recommendations` 字段，包含 Top N 推荐。

**三大必传参数（缺一不可，缺失会在 stderr 输出警告）**：

| 参数 | 数据来源 | 作用 | 缺失后果 |
|------|---------|------|---------|
| `--keepa-history-file` | Step 2 Keepa 历史时序数据 | 从 `buyboxPrice` 曲线取**正常售卖价**（非秒杀价） | 售价可能命中秒杀价，利润计算错误 |
| `--market-metrics-file` | Step 2 极目 niche 数据 | 取 `returnRateAnnual`（退货率）和 `acos`（ACoS） | 退货率和 ACoS 用默认值，与实际市场不符 |
| `--niche-keyword` | Step 1 SIF 精准词 Top 1 | 指定匹配哪个 niche 的指标 | 可能匹配到错误的 niche |

**niche 选择规则**：优先取极目返回的 `nicheTitle` 与 SIF 精准词 Top 3 精确或包含匹配的 niche；若均无匹配则回退取首个 niche，并在报告中注明"未精确匹配，使用首个 niche 指标"。

**零广告策略判断**：
- SIF `sponsoredProductsKeywordCount == 0` **或** SIF 关键词反查 Top 10 中所有关键词均无广告位（`displayPositionTypes` 不含广告类型）→ 该 ASIN 实际无广告投放，**广告费 = $0**
- 否则 → 广告费 = 售价 × nicheTACoS（极目 ACoS × 广告占比；无极目数据时回退 adTACoS=10%）
- 报告中须注明采用的是零广告策略还是市场均值 ACoS 策略，并说明判断依据

**nicheTACoS 计算**（来自 Step 2 极目数据，极目 API 返回的 acos 是小数 0-1）：
- `nicheTACoS` = acos × 100（结果为百分比，如 acos=0.131653 × 100 = 13.17%）
- 极目响应中不返回广告占比字段，直接用 acos 作为 TACoS

**FBA 费率查表**（非固定值）：弃置费 / 仓储费率 / 入库配置费根据 Keepa 包装尺寸（packageLength/Width/Height/Weight）自动查表，费率表见 `references/fba-fee-table.md`。大件商品的弃置费远超 $0.50，旺季仓储费率也不是固定值，入库配置费按重量分档。

**11 项全量成本模型**：

| # | 成本项 | 计算方式 | 数据来源 |
|---|--------|---------|---------|
| 1 | 1688采购成本(USD) | 1688价格(¥) / 汇率7.2 | B1/B2 |
| 2 | FBA配送费 | fbaFees | Keepa |
| 3 | 亚马逊佣金 | 售价 × referralFeePercentage / 100 | Keepa |
| 4 | 广告费 | 见零广告策略判断 | SIF + 极目 |
| 5 | COGS | 1688成本 + FBA头程($3.0) | B1/B2 + 入参 |
| 6 | 退款管理费 | 佣金 × 20% | 计算 |
| 7 | 弃置费 | 按 Keepa 包装尺寸查 FBA 费率表 | Keepa + fba-fee-table |
| 8 | 单笔退货亏损 | FBA费 + 退款管理费 + COGS + 弃置费 | 计算 |
| 9 | 每件预期退货损失 | 退货率 × 单笔退货亏损 | 极目 |
| 10 | 月度仓储费 | (L×W×H mm³ / 28316846.6) × storageRate（按尺寸分档查表） | Keepa + fba-fee-table |
| 11 | 入库配置费 | 按重量分档查表 | Keepa + fba-fee-table |

**净利润** = 售价 - (1+2+3+4+9+10+11+FBA头程)
**净利润率** = 净利润 / 售价 × 100%

**弃置费处理（脚本已内置，无需手动处理）**：弃置费包含在"单笔退货损失"中，通过退货率折算后进入"预期退货损失"，**不单独加入总成本**。总成本公式为：`1688成本 + FBA费 + 佣金 + 广告费 + 预期退货损失 + 仓储费 + 入库配置费 + 头程`（不包含弃置费，因为弃置费已通过预期退货损失间接包含）。

**参数来源校验（脚本自动输出到 stderr，agent 必须检查）**：

脚本运行后会在 stderr 输出每个参数的来源和值，格式如下：
```
[参数来源] Keepa 历史时序数据: <文件路径>
  [售价校验] buyboxPrice 曲线有 2 个价格水平: 正常售卖价=$49.99, 秒杀价=$44.99
[参数来源] 极目 niche 数据: <文件路径>
  已解析 10 个 niche 的退货率, 10 个 niche 的 TACoS
  [退货率] 来源: 极目 niche 'laptop screen extender' 精确匹配 → 6.46%
  [ACoS] 来源: 极目 niche 'laptop screen extender' 精确匹配 → 27.09%
```

若 stderr 中出现 `[⚠️ 警告]` 行，说明有参数未从正确数据源获取，**必须修正后重新运行**，不得带警告提交结果。

**参数取值原则**：除头程运费（`--fba-head-cost`，无数据源，用默认值 $3.0）外，**所有成本参数禁止用默认值**，必须根据 Keepa 包装尺寸/重量 + 极目 niche 数据自动计算。

> **⚠️ 成本核算提醒（必须在报告利润章节末尾醒目展示）**：
> 以上利润核算基于初步筛选的 1688 货源价格，**仅供参考**。实际采购成本可能因供应商谈判、起订量、运费波动等因素变化。用户手工确认真正货源后，提供最终采购价格，我们将重新核算并更新本报告的产品成本核算部分。

## Step 7 — 推荐展示

- 按综合得分排序的推荐列表，不再并列展示 B1+B2
- **Top 1 推荐醒目展示**，附推荐理由（综合最优 / 利润最高 / 销量最高）
- 每条含：排名 / ASIN / ASIN 标题 / 亚马逊月销量 / 1688 offerId / 1688 标题 / 1688 价格 / 净利润 / 净利润率 / 综合得分
- 完整 11 项成本拆解附在每条推荐下方（可展开）
- **货源筛选提醒**（必须醒目展示）：1688 货源仅为初步筛选，待用户手工确认真正货源后重新核算

## 依赖 skill

| skill | 用途 | 调用步骤 |
|-------|------|---------|
| linkfox-sif-asin-keywords | ASIN 关键词反查（首选） | Step 1 |
| linkfox-sellersprite-traffic-keyword | ASIN 流量词反查（二级兜底） | Step 1 |
| linkfox-junglescout-keyword-by-asin | ASIN 关键词反查（三级兜底） | Step 1 |
| linkfox-amazon-search | 前台搜索候选商品 | Step 2 |
| linkfox-keepa-product-request | 商品详情（FBA费/佣金/包装尺寸/主图） | Step 2 |
| linkfox-keepa-product-series | 历史时序（buyboxPrice 曲线取正常售价） | Step 2 |
| linkfox-sif-asin-summary | 零广告判断 | Step 2 |
| linkfox-jiimore-get-niche-info-by-keyword | 极目 niche 数据（ACoS/退货率/广告占比） | Step 2 |
| linkfox-aigc-textgen | AIGC 入参推导 + 货源验证 | Step 3, 5 |
| linkfox-dld-product-search | B1 店雷达搜索 | Step 4 |
| linkfox-1688-search-by-image | B2 以图搜图 | Step 4 |
| linkfox-ai-mode-google-search | B1 搜索词优化兜底（B1+B2 验证不足时） | Step 5 |

## 限制

- 输入仅需一个亚马逊 ASIN，关键词通过 SIF 反查自动获取
- 自动扩展目标 ASIN 列表（用户 ASIN + 最多 3 个评论数最少的新品），Step 2 的并行调用量随目标 ASIN 数量线性增长，约消耗 100-200 积分
- AIGC 入参推导的准确性依赖于亚马逊搜索结果中是否有视觉相似的商品
- 1688 搜索词的准确性依赖于 AIGC 对产品特征的理解，偶发翻译偏差
- 综合推荐排序依赖亚马逊月销量（monthlySalesUnits），未传入 `--amazon-search-file` 时综合得分无法计算
- 汇率默认 7.2，不可配置
- 目前仅支持美国站（US）

## 适用与不适用

**适用**：
- 有一个亚马逊 ASIN，想找 1688 货源并核算利润
- 需要对比多个 1688 供应商的成本和利润
- 需要验证 1688 货源与亚马逊商品的实际匹配度

**不适用**：
- 没有 ASIN 的选品场景（需要先确定目标 ASIN）
- 只查单个 ASIN 的 1688 货源（直接用 linkfox-1688-search-by-image 即可）
- 1688 下单采购（用 linkfox-1688-procurement）
