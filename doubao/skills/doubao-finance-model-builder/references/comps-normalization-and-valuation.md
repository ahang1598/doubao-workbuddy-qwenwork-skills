# 标准化、计算与估值规则

## 目录

- 单位与输入模式
- 完全稀释股本
- 除息后 BVPS 与 ROE
- 标准 EV bridge
- LTM、NTM 与 FCF
- 交易倍数与统计
- 隐含价值
- 市场隐含预期
- 敏感性与情景
- 质量门

## 单位与输入模式

同一脚本输入中的所有公司使用同一币种和规模单位。建议金额使用“报告币种百万”，股本使用“百万股”，股价和 BVPS 使用“报告币种/股”。由此市值、权益和 EV 均为“报告币种百万”。ROE 与 FCF Yield 使用小数，例如 12% 输入 `0.12`。

`scripts/comps/calculate_comps.py` 接受 UTF-8 JSON。以下示例只说明字段，不代表真实公司：

```json
{
  "valuation_date": "2026-07-10",
  "currency": "CNY",
  "unit": "millions",
  "output_mode": "decision-brief",
  "data_tier": "A",
  "fx_rates": [
    {"pair": "HKD/CNY", "rate": 0.90, "rate_date": "2026-07-10", "source_id": "fx-01"}
  ],
  "target_ticker": "600036.SH",
  "valuation_profile": {
    "industry": "bank",
    "economic_model": "deposit-funded commercial bank",
    "stage": "mature-stable",
    "primary_metrics": ["price_to_book"],
    "secondary_metrics": ["ltm_pe", "ntm_pe", "ltm_roe"],
    "rejected_metrics": ["ltm_ev_revenue", "ltm_ev_ebitda"]
  },
  "companies": [
    {
      "name": "Target Bank",
      "ticker": "600036.SH",
      "classification": "Target",
      "price": 35.0,
      "price_date": "2026-07-10",
      "share_count_date": "2026-06-30",
      "share_count": {
        "basic_shares": 25220.0,
        "incremental_options": 0.0,
        "unvested_rsus": 0.0,
        "performance_shares": 0.0,
        "convertible_incremental_shares": 0.0,
        "other_dilution": 0.0,
        "settled_issuance_shares": 0.0,
        "settled_buyback_shares": 0.0,
        "unsettled_asr_estimated_shares": 0.0
      },
      "balance_sheet_date": "2026-03-31",
      "estimate_date": "2026-07-10",
      "debt": 0.0,
      "cash": 0.0,
      "cash_bridge": {
        "cash_and_equivalents": 0.0,
        "term_deposits": 0.0,
        "short_term_investments": 0.0,
        "restricted_cash": 0.0,
        "operating_cash_reserve": 0.0,
        "deductible_cash": 0.0
      },
      "preferred_equity": 0.0,
      "noncontrolling_interest": 0.0,
      "debt_like_adjustments": 0.0,
      "non_operating_investments": 0.0,
      "ltm_net_income": 150000.0,
      "ntm_net_income": 160000.0,
      "common_equity": 1150000.0,
      "book_value_shares": 25220.0,
      "reported_bvps": 45.60,
      "average_common_equity": 1100000.0,
      "dividends": [
        {
          "type": "final",
          "ex_date": "2026-07-03",
          "dps": 2.00,
          "equity_already_reduced": false,
          "eligible_shares": 25220.0
        }
      ]
    },
    {
      "name": "Core Bank A",
      "ticker": "COREA",
      "classification": "Core",
      "peer_role": "Commercial Core",
      "selection_rationale": "同类客户、产品和监管框架",
      "classification_rationale": "业务重叠和数据质量满足核心门槛",
      "metric_rationale": "银行使用P/B和P/E，弃用工业企业EV倍数",
      "data_quality": "Pass",
      "peer_scores": {
        "business_overlap": 5,
        "business_model": 5,
        "revenue_structure": 4,
        "market_cap_band": 4
      },
      "price": 10.0,
      "diluted_shares": 10000.0,
      "price_date": "2026-07-10",
      "balance_sheet_date": "2026-03-31",
      "ltm_net_income": 12000.0,
      "common_equity": 100000.0,
      "book_value_shares": 10000.0,
      "average_common_equity": 96000.0,
      "dividends": []
    }
  ],
  "market_implied_requests": [
    {"name": "Core P/B median", "metric": "price_to_book", "benchmark": 1.0}
  ],
  "sensitivity": {
    "metric": "price_to_book",
    "anchors": [0.9, 1.0, 1.1],
    "fundamentals": [42.0, 44.0, 46.0],
    "fundamental_label": "adjusted BVPS"
  },
  "scenarios": [
    {"name": "base", "metric": "price_to_book", "anchor": 1.0, "fundamental": 44.0}
  ],
  "analysis_summary": {
    "conclusion": "示例结论；正式结论必须连接目标公司与同行基本面差异",
    "peer_comparison": "逐项比较增长、盈利、现金转化、资产负债表和风险",
    "premium_discount_rationale": "说明溢折价方向、幅度和证据",
    "invalidation_conditions": ["条件一", "条件二", "条件三"]
  }
}
```

对非目标公司使用 `Core`、`Secondary` 或 `Excluded`，并提供 `peer_scores` 和 `data_quality`。脚本只用 Core 计算统计。可只提供 `diluted_shares`；若同时提供 `share_count`，脚本按 bridge 推导并用其结果。

每个非目标公司还必须提供 `peer_role`、`selection_rationale`、`classification_rationale` 和 `metric_rationale`。缺少同行分析时计算仍可形成审计底稿，但 `model_status_code` 为 `INCOMPLETE`，报告不得输出推荐倍数或隐含价值区间。

每个目标、核心和辅助公司还必须提供 `field_sources`，至少映射 `price`、`diluted_shares`、`capital_structure` 和 `primary_fundamentals`；非目标公司再映射 `peer_analysis`。每个映射值必须引用 `source_ledger` 中真实存在的 `source_id`。来源台账只有一行、映射为空对象或引用不存在的来源ID时状态均为 `INCOMPLETE`。

此外每家公司必须提供：

- `share_count_date = valuation_date`；
- `price_basis = unadjusted_close`，`price_date` 为估值日或此前不超过7个日历日的最近交易日；
- `reference_market_cap`、与价格日相同的 `market_cap_date`、`market_cap_source_id` 和默认不高于2%的 `market_cap_tolerance_pct`；
- `corporate_action_review`，包含最近可靠股本日、检索起止日、来源ID、完整性确认和公司行动清单。

估值日前已生效公司行动必须计入股数，最后一项行动后的股数必须与完全稀释股本一致。`price × diluted_shares` 与独立市值超容差、使用复权价格、股数日早于估值日或检索截止日未覆盖估值日时，脚本直接失败。`field_sources` 还必须映射 `corporate_actions` 和 `market_cap_cross_check`。

正式结论使用 `analysis_summary` 保存目标公司与核心同行的逐项比较、溢折价理由和至少三项失效条件。脚本统计结果不能替代这些分析判断。

`fx_rates` 在跨币种估值时必需；`rate_date` 不得晚于估值日，原则上与价格日一致。`cash` 是进入 EV 公式的可扣现金，必须与 `cash_bridge.deductible_cash` 一致。所有示例数值仅用于说明模式。

报告渲染时，`model_status_code != PASS` 必须同时屏蔽推荐倍数、隐含每股价值、情景估值和二维敏感性，不得只屏蔽首页摘要。

## 完全稀释股本

使用基准日可得的期末或最新基本股份，而不是未经调整的加权平均股份：

“最新”不是最近年报的同义词。先以最近可靠股本披露为起点，再把此后的送股、转增、拆合股、增发、回购注销、转换及A/H/ADR变化滚存至估值日；只读取年报股数不得进入倍数计算。

```text
Fully diluted shares
= basic shares
+ incremental in-the-money options
+ unvested RSUs
+ probable performance shares
+ convertible incremental shares
+ other dilution
+ settled issuance not yet reflected
- settled buybacks not yet reflected
```

### 工具处理规则

- 期权按库存股法计算增量，不加入全部期权名义股数。
- RSU 通常全额稀释；PSU 依据基准日可合理支持的实现条件。
- 可转债若以 if-converted 股份进入股本，应从净债务 bridge 删除同一工具，避免双计。
- 只扣减截至基准日已经回购并结算、且未反映在基本股份起点中的股份。
- 回购授权不减少股本；尚未结算的 ASR 预计最终交付仅披露，不进入基准股本。
- ASR 初始交付、最终结算和最新基本股份之间逐项勾稽，防止重复扣减。

脚本对 `share_count` 与直接提供的 `diluted_shares` 差异超过 1% 发出警告，并使用组成项 bridge。

## 除息后 BVPS 与 ROE

### BVPS 口径

以归属于普通股股东的权益为分子，使用与该权益日期匹配的基本股份为分母：

```text
Reported BVPS = common equity / book-value shares
```

若价格已经除息而所用普通股权益尚未扣除该股息：

```text
Dividend deduction = DPS × eligible shares
Adjusted common equity = reported common equity - dividend deduction
Adjusted BVPS = adjusted common equity / book-value shares
```

当 eligible shares 与 book-value shares 相同，Adjusted BVPS 等于 Reported BVPS 减 DPS。只有 `ex_date <= price_date` 且 `equity_already_reduced = false` 时脚本才扣除。每项股息必须明确会计确认状态，避免仅凭除权日重复扣减已经确认的应付股息。

若只有可靠的 `reported_bvps` 而无普通股权益，可直接按同证券每股股息调整；存在不同权利股份或 eligible shares 时必须取得权益与股本 bridge，不得简化。

### P/B 与 ROE

```text
P/B = current price / adjusted BVPS
LTM ROE = LTM common net income / average common equity
```

脚本优先用 LTM 净利润和平均普通股权益计算 ROE；只有平均权益不可得时才使用输入的 `ltm_roe`。P/B 和 ROE 必须同为归属于普通股股东口径。

对银行 Core 样本至少四家且 ROE 有足够离散度时，脚本计算：

```text
P/B = alpha + beta × LTM ROE
```

检查 `r_squared`、影响点、目标残差和预测 P/B。回归是相对定价交叉验证，不是结构模型，也不代表因果关系；资产质量、增长、资本充足率和风险成本仍需单独判断。

## 标准 EV bridge

对非金融公司统一使用完全稀释股权价值：

```text
Fully diluted equity value = price × fully diluted shares
Net debt bridge = debt + preferred equity + NCI + debt-like adjustments
                  - cash - non-operating investments
Enterprise value = fully diluted equity value + net debt bridge
```

### 组成项规则

- **Debt**：计入有息借款、票据和可比口径下的其他融资负债。
- **Cash**：只扣可自由支配、未受限且超过经营需要的现金口径；保留报告现金与可扣现金的差异。至少桥接现金等价物、定期存款、短期投资、受限现金、经营现金准备和可扣现金。现金流量表期末现金不得自动等同于 EV 可扣现金。
- **Non-operating investments**：只有资产可分离、可变现、非核心经营所需且未在同行 EBITDA 或收入中贡献时才扣除。对 Salesforce、美团等持有大额投资的公司逐项判断，不把所有短期投资自动视为多余现金。
- **NCI**：若合并 EBITDA/收入包含非全资子公司，则 EV 加入对应少数股东权益；若分母已剔除该分部则不加。
- **Preferred equity**：按索取权和可转换状态处理；不得同时计入稀释股本。
- **Debt-like adjustments**：养老金缺口、租赁负债、供应链融资、应收账款融资、资产退休义务等只在同行口径一致且经济含义成立时加入。
- **Leases**：若 EV 加租赁负债，则 EBITDA 需采用对应租赁口径；不得一边加租赁债务、一边使用租赁后 EBITDA。

银行、保险和证券公司的债务、存款、客户资金和交易性负债属于经营模型组成，不使用上述工业企业式 EV bridge 作为主估值基础。可以为信息完整保留字段，但主锚走股权价值口径。

建议同时展示：

```text
Reported liquid resources
- restricted cash
- operating cash reserve
= deductible cash [A]

Standard EV = equity value + debt and claims - reported unrestricted liquidity
Adjusted EV = equity value + debt and claims - deductible cash - separable investments
```

当经营现金准备或投资折价主观性较高时，用标准EV与调整EV形成区间，不用单点调整掩盖判断。

## LTM、NTM 与 FCF

LTM 使用基准日前已公开的最近四个季度或等价年度。公司改变财年、完成并购或重述数据时，说明报告与备考口径。

优先使用真正 NTM 一致预期。若只有 FY1 与 FY2，可按剩余月份日历化：

```text
months_FY1 = valuation date 至 FY1 年末覆盖的月份
NTM = FY1 × months_FY1 / 12 + FY2 × (12 - months_FY1) / 12
```

若估值日在 FY1 开始前、跨越不规则财年或季度季节性显著，应按季度估计构造，不机械套用月份权重。所有日历化标记 `[D]`，披露供应商、快照、FY1/FY2 原值和权重。

定义报告 FCF：

```text
FCF = cash flow from operations - capital expenditures
```

FCF 不加回 SBC。一次性营运资本、重组现金流、并购费用或资本化软件支出可形成 `[A]` 口径，但必须保留报告 FCF。对重资产扩产公司，负 FCF 可能是扩产阶段结果，不自动代表经营失效，也不适合作为单一主锚。

## 交易倍数与统计

脚本计算：

```text
EV/Revenue = enterprise value / revenue
EV/EBITDA = enterprise value / EBITDA
P/E = fully diluted equity value / net income
P/S = fully diluted equity value / revenue
FCF Yield = FCF / fully diluted equity value
P/B = price / adjusted BVPS
ROE = net income / average common equity
```

LTM 与 NTM 分开计算。收入、EBITDA、净利润、FCF、BVPS 或 ROE 为零、负值或经济含义失真时，对应指标标记 `NM` 并排除统计。报告值和调整值并列，不得把 adjusted EPS 冒充 GAAP EPS。

P/S 与 EV/Revenue 使用同一收入期间和收入确认口径，但分子不同：P/S 使用完全稀释股权价值，EV/Revenue 使用企业价值。只有资本结构足够接近时才把 P/S 作为主统计；否则将其降为辅助指标并解释与 EV/Revenue 的差异。总额法/净额法、一次性授权或里程碑收入、平台补贴和并购备考收入必须先标准化。

只用 Core 正数有效观测值。脚本采用线性插值：排序后位置为 `(n-1)×p`，在相邻值间插值，计算 p=0.25、0.50、0.75。披露每个指标样本数；不得纳入 `NA`、`NM`、Secondary 或 Excluded。

## 隐含价值

### EV 倍数

```text
Implied EV = selected multiple × target financial metric
Implied equity value = implied EV - target net debt bridge
Implied share value = implied equity value / fully diluted shares
```

### P/E

```text
Implied equity value = selected P/E × target net income
Implied share value = implied equity value / fully diluted shares
```

### P/S

```text
Implied equity value = selected P/S × target revenue
Implied share value = implied equity value / fully diluted shares
```

P/S 不经过净债务调节。若目标公司与同行的净现金、净负债、优先股、少数股东权益或非经营投资差异显著，应优先使用 EV/Revenue，并只把 P/S 作为股权投资者视角的辅助验证。

当 `ltm_ps` 或 `ntm_ps` 被列入 `valuation_profile.primary_metrics` 时，同时设置：

```json
{
  "ps_revenue_basis_checked": true,
  "ps_capital_structure_comparable": true
}
```

前者表示收入确认、总额法/净额法和一次性收入已经标准化；后者表示目标公司与核心可比公司的净现金、净负债及其他优先索取权差异不会显著扭曲 P/S。缺少任一确认时脚本发出警告。

### FCF Yield

```text
Implied equity value = target FCF / selected FCF yield
```

收益率越高，估值越低。因此 Core FCF Yield P75 产生价值低端，P25 产生价值高端。

### P/B

```text
Implied share value = selected P/B × target adjusted BVPS
```

使用已经完成除息匹配的 BVPS。若同股不同权、增发或回购导致每股口径发生变化，应先重做 BVPS 和股份 bridge。

不得机械平均不同主辅指标。先确定主锚区间，再用辅助锚验证是否出现方向性冲突；冲突应解释口径或经营原因。

## 市场隐含预期

`market_implied_requests` 接受一个或多个“指标 + 基准倍数/收益率”请求。脚本在当前价格下反推：

```text
EV multiple: implied revenue or EBITDA = current EV / benchmark multiple
P/E: implied net income = current equity value / benchmark P/E
P/S: implied revenue = current equity value / benchmark P/S
FCF Yield: implied FCF = current equity value × benchmark yield
P/B: implied BVPS = current price / benchmark P/B
```

将结果与当前 LTM、NTM 一致预期或调整后 BVPS比较，报告差异。只有具备利润率、资本周转、分红或增长模型时，才把隐含财务指标继续翻译为增长、ROE 或利润率；否则停止在直接可解层，避免伪精确。

## 敏感性与情景

### 二维敏感性

`sensitivity` 使用：

- `metric`：主估值锚。
- `anchors`：倍数或收益率轴。
- `fundamentals`：目标财务指标轴；P/B 为 BVPS/股，P/S 为营业收入金额，其余通常为金额。
- 可选 `net_debt_bridge`、`diluted_shares`：覆盖目标公司基准值。

区间必须来自同行 P25–P75、建议溢折价、可观察一致预期范围或有依据的经营情景。不得用任意 ±10% 代替证据。

### 情景

`scenarios` 逐项输入名称、指标、锚、财务指标，可选净债务和稀释股本。悲观、基准、乐观情景应分别改变真正不确定的驱动项：

- 倍数反映市场风险偏好与相对质量。
- 财务指标反映经营结果。
- 净债务反映资本配置、投资资产可变现性和现金消耗。
- 股本反映 SBC、融资、回购和可转工具。

不要把所有风险只反映为倍数变化。

## 质量门

运行脚本前确认：

- 所有日期不晚于估值基准日，价格日例外仅为此前最近交易日。
- 所有公司使用同一币种与规模单位。
- Core/Secondary/Excluded 均有四维评分和数据质量。
- 目标公司与同行的 LTM/NTM 期间一致。
- 完全稀释股本没有重复计入可转债、ASR 或已反映回购。
- 价格含权状态与 BVPS 股息状态一致。
- EV bridge 中现金、投资、租赁、NCI 和可转工具未重复或错配。
- 主锚至少有三项 Core 有效值；P/B–ROE 回归至少四项且 ROE 有离散度。
- P/S 主锚已通过收入确认和资本结构可比性检查，并与 EV/Revenue 的方向和差异完成解释。
- 输入脚本的调整值均能回溯到 `[R]`、`[E]` 与明确公式。

检查输出 `warnings`，逐项解决或在报告披露。警告不等于自动否定结论，但不得静默忽略。

<!-- END OF FILE: comps-normalization-and-valuation.md -->
