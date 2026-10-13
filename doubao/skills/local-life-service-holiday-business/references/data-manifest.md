# 数据指标清单

机器唯一清单为 [data-manifest.json](data-manifest.json)，本文件为对应中文说明。`DP` 表示数据平台抖音生意经，`BP` 表示商家后台抖音来客；`P0` 为每次运行必查，`P1` 仅在命中触发条件时采集。

## 计数与状态规则

- 每个子指标都单独形成一条记录，至少保存 `check_id`、`metric_key`、`source_id`、`actual_scope`、`window`、`status` 和原始口径。
- `status` 只允许 `observed`、`zero`、`unavailable`、`not_applicable`。`zero` 必须来自页面明确显示的零值；加载失败、无权限、无结果或未展示不得记为零。
- 一行只有在其全部 `metric_key` 子项均取得上述四态之一时，才计入 `checked`。同页看到了部分子项，整行仍未完成。
- P0 不得因快速分流、零值、页面缺入口或预计无数据而静默跳过。无法取得时仍须为每个子项记录 `unavailable` 或 `not_applicable`，并保留原因。
- P1 未命中触发条件时整行省略，不生成占位记录，也不计入完成度；一旦触发，则必须完成该行全部子项的四态记录。
- `expected_scope` 是应优先请求的层级。单店为 store，多店汇总为 store_set，必须对应本次分析范围。账号身份等元信息可为 merchant。商家账号一致性由本 Skill 读取两端页面 DOM 后判定；本清单的门店数仅作经营规模指标，不用于跨平台比较。

## DP0 · 数据平台核心指标

| check_id | 清单行 | metric_key 子项 | 来源／平台 | expected_scope | trigger | 完成规则 |
|---|---|---|---|---|---|---|
| `DP0-01` | 商家名称、groupid、门店数、区域数 | 商家名称 `merchant_name`；groupid `merchant_groupid`；门店数 `store_count`；区域数 `region_count` | 数据平台／抖音生意经 | `merchant` | 每次运行必查 | 4/4 子项均有合法状态；不得省略 |
| `DP0-02` | 成交金额、环比 | 成交金额 `transaction_amount`；成交金额环比 `transaction_amount_change_rate` | 数据平台／抖音生意经 | `store` / `store_set` | 每次运行必查 | 2/2 子项均有合法状态；不得省略 |
| `DP0-03` | 核销金额、环比 | 核销金额 `redemption_amount`；核销金额环比 `redemption_amount_change_rate` | 数据平台／抖音生意经 | `store` / `store_set` | 每次运行必查 | 2/2 子项均有合法状态；不得省略 |
| `DP0-04` | 退款金额、环比 | 退款金额 `refund_amount`；退款金额环比 `refund_amount_change_rate` | 数据平台／抖音生意经 | `store` / `store_set` | 每次运行必查 | 2/2 子项均有合法状态；不得省略 |
| `DP0-05` | 门店动销率、动销门店数 | 门店动销率 `selling_store_rate`；动销门店数 `selling_store_count` | 数据平台／抖音生意经 | `store` / `store_set` | 每次运行必查 | 2/2 子项均有合法状态；不得省略 |
| `DP0-06` | 日店均成交、日店均核销 | 日店均成交 `avg_daily_transaction_amount_per_store`；日店均核销 `avg_daily_redemption_amount_per_store` | 数据平台／抖音生意经 | `store` / `store_set` | 每次运行必查 | 2/2 子项均有合法状态；不得省略 |
| `DP0-07` | 商品榜单 Top5 | 商品榜单 Top5 `product_ranking_top5` | 数据平台／抖音生意经 | `store` / `store_set` | 每次运行必查 | 1/1 子项有合法状态；不得省略 |
| `DP0-08` | 商品概览：全部商品、动销商品、滞销商品 | 全部商品 `product_count_all`；动销商品 `product_count_selling`；滞销商品 `product_count_slow_moving` | 数据平台／抖音生意经 | `store` / `store_set` | 每次运行必查 | 3/3 子项均有合法状态；不得省略 |
| `DP0-09` | 搜索分析：搜索词、搜索曝光、搜索点击、搜索成交 | 搜索词 `search_terms`；搜索曝光 `search_impressions`；搜索点击 `search_clicks`；搜索成交 `search_transactions` | 数据平台／抖音生意经 | `store` / `store_set` | 每次运行必查 | 4/4 子项均有合法状态；不得省略 |

`collection.platform_p0.total` 固定为 9；`checked` 为以上九行中已满足完成规则的行数。

## DP1 · 数据平台扩展指标

| check_id | 清单行 | metric_key 子项 | 来源／平台 | expected_scope | trigger | 完成规则 |
|---|---|---|---|---|---|---|
| `DP1-01` | 成交来源分布：渠道、体裁 | 渠道分布 `transaction_source_by_channel`；体裁分布 `transaction_source_by_content_format` | 数据平台／抖音生意经 | `store` / `store_set` | 已有成交或核销，且来源结构会改变动作或排序；或用户明确关注渠道／体裁 | 未触发则整行省略；触发后 2/2 子项均有合法状态 |
| `DP1-02` | 退款原因分布 | 退款原因分布 `refund_reason_distribution` | 数据平台／抖音生意经 | `store` / `store_set` | 退款大于零、退款异常，或用户明确关注退款 | 未触发则整行省略；触发后 1/1 子项有合法状态 |
| `DP1-03` | 评价数据：评分、评价数 | 评分 `rating_score`；评价数 `review_count` | 数据平台／抖音生意经 | `store` / `store_set` | 评分或评价会改变经营动作，或用户明确关注口碑／评价 | 未触发则整行省略；触发后 2/2 子项均有合法状态 |
| `DP1-04` | 流量数据：曝光、访问、渠道分布 | 曝光 `traffic_impressions`；访问 `traffic_visits`；渠道分布 `traffic_channel_distribution` | 数据平台／抖音生意经 | `store` / `store_set` | 需要诊断曝光、访问到成交的承接，尤其有商品但无成交；或用户明确关注流量 | 未触发则整行省略；触发后 3/3 子项均有合法状态 |
| `DP1-05` | 门店榜单 | 门店榜单 `store_ranking` | 数据平台／抖音生意经 | `store` / `store_set` | 需要比较门店表现或解释多店差异，或用户明确关注门店排名 | 未触发则整行省略；触发后 1/1 子项有合法状态 |
| `DP1-06` | 行业竞争排名：概览层级 | 行业竞争概览排名 `industry_competition_overview_rank` | 数据平台／抖音生意经 | `city_category`；页面仅有更宽口径时为 `industry` | 同城同类位置或竞争机会会改变方案，或用户明确关注行业竞争 | 未触发则整行省略；触发后 1/1 子项有合法状态 |

## BP0 · 商家后台核心指标

| check_id | 清单行 | metric_key 子项 | 来源／平台 | expected_scope | trigger | 完成规则 |
|---|---|---|---|---|---|---|
| `BP0-01` | 商家名称：用于跨平台校验 | 商家名称 `merchant_name` | 商家后台／抖音来客 | `merchant` | 每次运行必查 | 1/1 子项有合法状态；不得省略 |
| `BP0-02` | 成交金额、核销金额、退款金额 | 成交金额 `transaction_amount`；核销金额 `redemption_amount`；退款金额 `refund_amount` | 商家后台／抖音来客 | `store` / `store_set` | 每次运行必查 | 3/3 子项均有合法状态；不得省略 |
| `BP0-03` | 曝光次数 | 曝光次数 `impression_count` | 商家后台／抖音来客 | `store` / `store_set` | 每次运行必查 | 1/1 子项有合法状态；不得省略 |
| `BP0-04` | 经营分、门店等级分布 | 经营分 `business_score`；门店等级分布 `store_grade_distribution` | 商家后台／抖音来客 | `store` / `store_set` | 每次运行必查 | 2/2 子项均有合法状态；不得省略 |
| `BP0-05` | 门店数、抖音号数 | 门店数 `store_count`；抖音号数 `douyin_account_count` | 商家后台／抖音来客 | `merchant` | 每次运行必查 | 2/2 子项均有合法状态；不得省略 |
| `BP0-06` | 违规状态、收款状态 | 违规状态 `violation_status`；收款状态 `payment_status` | 商家后台／抖音来客 | `merchant` | 每次运行必查 | 2/2 子项均有合法状态；不得省略 |

`collection.backend_p0.total` 固定为 6；`checked` 为以上六行中已满足完成规则的行数。

## V3完成度

每条items具有id、check_id、metric_key、priority、source_id、evidence_ref、actual_scope、scope_store_keys、window、status、raw_value和reason。规范见report-data-contract.md。每行全部子项验证通过才计数；P0不能以手填checked_ids代替明细。PRE-01的store_visits/product_count_onsale/ad_spend仅为预检补充，不增加P0分母。范围门禁高于P0检查，未对齐不继续凑必采数据。
