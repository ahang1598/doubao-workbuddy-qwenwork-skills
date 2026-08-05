# facts.json 字段全集与错误速查

> 长参考文件：默认先读 `references/facts_contract.md`。只有 facts lint 错误看不懂、需要字段全集、或需要对照完整示例时，再读本文。完整示例在 `assets/example_facts.json`，不要把示例全文加载进上下文，除非确实要比对结构。

## 1. 原理

facts.json 是第一阶段的数字与催化边界。正文和飞书文档 payload 只能使用这里登记且裁定可用的事实，或 `derive_facts.py` 从原始取数字段复算出的派生值。

顶层只能是：

```json
{
  "meta": {},
  "sector_checks": {},
  "stock_checks": [],
  "divergence_groups": {},
  "facts": []
}
```

不要写成 `sector_name`、`top_10_stocks`、`sector_index`、`catalysts` 这类摘要结构。尤其禁止在 `sector_index` 或 `facts[]` 中登记板块 PE / 板块市盈率；只回填股票 / 代表股 PE(TTM)。

## 2. 推荐创建方式

优先用骨架脚本，不从空白文件手写：

```bash
python3 scripts/init_facts.py \
  --sector "<板块名>" \
  --index-caliber "<目标概念板块 名称+代码>" \
  --stocks "股票1,股票2,股票3,股票4,股票5,股票6,股票7,股票8,股票9,股票10" \
  --timestamp "数据截至 YYYY-MM-DD 收盘" \
  --today "YYYY-MM-DD" \
  -o work/<板块>_facts.json
```

若已经误写为摘要型 JSON，可先转换骨架：

```bash
python3 scripts/init_facts.py --from-summary work/<板块>_facts.json -o work/<板块>_facts.fixed.json
```

转换不会凭空补 7 日序列、来源链接或代表股理由，仍需回填真实数据。

## 3. lint 会查什么

facts-only lint：

```bash
python3 scripts/lint_analysis.py --strict work/<板块>_facts.json
```

会检查：

1. `meta` 是否有板块、目标概念板块、10 股、数据时点、`data_mode`。
2. `sector_checks` 是否登记目标板块收盘、前收、成交额、T-7/T 收盘分量、T-6 至 T 的 7 个交易日成交额数组、派生指标及原始取数证据。
3. `stock_checks` 是否恰好 10 条，且名单等于 `meta.selected_stocks`。
4. 每股是否有 `role`、`select_reason`、`source_name`、`as_of`、`evidence`。
5. 每股是否有当日 `change`、`turnover`、股票 `pe_ttm`。
6. 每股是否有近7日原始分量 `d7_close_base`、`d7_close_t`、长度为 7 的 `d7_turnovers`，并已派生 `change_7d`、`turnover_7d`。
7. 板块与个股近7日涨跌 / 日均成交额是否能从原始分量复算一致。
8. `divergence_groups` 四组并集是否等于 10 股，并按硬口径归类。
9. `facts[]` 是否非空；展示数字与最终入选模块2催化是否有必要字段。
10. 若同时传入草稿，正文数字是否绑定 `{fact:id}`，模块结构和固定结尾是否合规。

## 4. lint 失败怎么修

第一次失败后，完整读完所有错误，再判断类型：

| 报错关键词 | 默认动作 |
|---|---|
| `meta.* 缺失` / `selected_stocks` | 补 `sector`、`index_caliber`、`timestamp`、`today`、`data_mode`、10 股名单 |
| `sector_checks` / `板块近7日复算` | 补目标板块原始字段及近7日分量，运行 `derive_facts.py`；不得用 10 股样本替代 |
| `stock_checks` / `缺少有效` | 只补对应股票字段，不重新生成整份 facts |
| `d7_turnovers` / `近7日复算` | 回到已取数据，修该股票的 7 日原始分量，再运行 `derive_facts.py` |
| `role` / `select_reason` | 补代表股角色和选取理由 |
| `source_name` / `as_of` / `evidence` | 补来源名、数据时点和原始取数证据；时点不得晚于截止日 |
| `divergence_groups` / `放量` / `缩量` | 运行 `derive_facts.py` 自动重排；若仍错，修对应股票的 `change` / `turnover` / 7日成交分量 |
| `lane` / `source` / 字段别名 | 若属机械问题，可运行 `repair_facts.py` |
| `facts[]` 为空 | 登记会进入正文 / 飞书文档的展示数字和最终入选催化 |
| `催化` / `三级` / `个人` / `自媒体` | 换一级/二级来源；找不到则 `body_use:"no"` |

机械问题才运行 repair：

```bash
python3 scripts/repair_facts.py work/<板块>_facts.json
python3 scripts/derive_facts.py work/<板块>_facts.json
python3 scripts/lint_analysis.py --strict work/<板块>_facts.json
```

`repair_facts.py` 可修字段别名、嵌套 `source`、`lane` 顶层化、摘要型顶层迁移；`derive_facts.py` 负责涨跌幅、近7日日均成交额和四组。两个脚本都不会编造 7 日价格 / 成交序列、来源 URL、`role/select_reason` 或 `facts[]`。

只有 JSON 损坏无法定位、或当前文件确实是摘要型结构时，才另存新骨架。迁移时保留已确认的来源、股票名单、催化与复算分量。

## 5. meta

| 字段 | 要求 |
|---|---|
| `sector` | 板块名 |
| `index_caliber` | 目标概念板块名称 + 代码 |
| `selected_stocks` | 恰好 10 只代表股名称 |
| `timestamp` | 如 `数据截至 2026-06-18 收盘` |
| `today` | `YYYY-MM-DD` |
| `data_mode` | 固定填 `full` |

## 6. sector_checks

必须登记目标板块 5 个核心指标。采集阶段先填原始取数字段；派生字段由 `derive_facts.py` 统一生成。

全局时间锚：`T` / `T0` 固定为最近一个已经完成收盘的交易日；盘中生成时不得把当日未收盘行情作为 `T`，应使用上一已收盘交易日，并在 `meta.timestamp` 写清“数据截至 YYYY-MM-DD 收盘”。未确定 `T0` 前不得搜索或登记行情数字；下文所有“当日”均指 `T0` 的已收盘行情。

| 字段 | 要求 |
|---|---|
| `close_point` | 目标概念板块指数 / 板块行情 `T0` 收盘点位 |
| `prev_close` | 前一交易日收盘点位 |
| `daily_change` | 目标概念板块 `T0` 涨跌幅 %，脚本从 `close_point / prev_close` 复算 |
| `turnover_amount` | 目标概念板块全成分 / 官方板块口径 `T0` 成交额，亿元 |
| `change_7d` | 目标概念板块近7个交易日涨跌幅 %，脚本从 `d7_close_t / d7_close_base` 复算；当天为 T / Day 0，基准为 T-7 交易日收盘 |
| `turnover_7d` | 目标概念板块近7个交易日日均成交额，脚本从 `d7_turnovers` 复算，亿元 |
| `d7_close_base` | T-7 交易日收盘点位（从数据截止日 T 往前数第 7 个交易日） |
| `d7_close_t` | 数据截止日 T 收盘点位；可由脚本用 `close_point` 补齐 |
| `d7_turnovers` | 目标板块最近 7 个交易日成交额数组，长度为 7 |
| `as_of` | 数据时点，不得晚于 `meta.timestamp` |
| `source_name` | 同花顺数据库或同花顺具体口径 |
| `evidence` | 从 `seed_finance_search` / 同花顺返回结果复制的原始数据行摘要 |

派生口径：

- `daily_change = close_point / prev_close - 1`
- `change_7d = d7_close_t / d7_close_base - 1`；`d7_close_t` 为 T 日收盘，`d7_close_base` 为 T-7 交易日收盘。当天作为 Day 0，不用 T-6 作基准。
- `turnover_7d = avg(d7_turnovers)`

取数动作：近7日相关字段不要分两次补取；第一轮就取 `T-7` 至 `T` 的 8 个已收盘交易日日线，再从同一批结果切出涨跌幅首尾收盘价和成交额 7 日窗口。

除 `pe_ttm` 外，核心小卡用这里的目标板块口径；不得用 10 股样本合计 / 均值替代板块指标。

## 7. stock_checks

必须恰好 10 条，名称等于 `meta.selected_stocks`。采集阶段先填原始取数字段、角色、选取理由和 evidence；派生字段由 `derive_facts.py` 统一生成。

| 字段 | 要求 |
|---|---|
| `name` | 股票名称 |
| `change` | `T0` 涨跌幅 % |
| `turnover` | `T0` 成交额，亿元 |
| `pe_ttm` | 股票 `T0` PE(TTM)，必填；不得填板块 PE |
| `change_7d` | 近7个交易日涨跌幅 %，脚本从 `d7_close_t / d7_close_base` 复算；当天为 T / Day 0，基准为 T-7 交易日收盘 |
| `turnover_7d` | 近7个交易日日均成交额，脚本从 `d7_turnovers` 复算，亿元 |
| `d7_close_base` | T-7 交易日收盘价（从数据截止日 T 往前数第 7 个交易日） |
| `d7_close_t` | 数据截止日 T 收盘价 |
| `d7_turnovers` | 最近 7 个交易日成交额数组，长度为 7 |
| `role` | 代表股定性角色 |
| `select_reason` | 为什么选入 10 只代表股；一句话，不带涨跌/成交数字 |
| `as_of` | 数据时点，不得晚于 `meta.timestamp` |
| `source_name` | 同花顺数据库或同花顺具体口径 |
| `evidence` | 从 `seed_finance_search` / 同花顺返回结果复制的原始数据行摘要 |

派生口径：

- `change_7d = d7_close_t / d7_close_base - 1`；`d7_close_t` 为 T 日收盘，`d7_close_base` 为 T-7 交易日收盘。当天作为 Day 0，不用 T-6 作基准。
- `turnover_7d = avg(d7_turnovers)`

取数动作：逐股近7日相关字段也按 `T-7` 至 `T` 的 8 个已收盘交易日日线一次取齐；不要先取 7 日成交额再补涨跌幅基准。

`evidence` 用来防止“自洽假数据”：至少包含数据终端名、标的名、日期和关键字段；不能只写“来自同花顺”或分析性结论。

## 8. divergence_groups

键固定：

```json
{
  "放量上攻": [],
  "缩量上行": [],
  "缩量回调": [],
  "放量杀跌": []
}
```

`divergence_groups` 由 `derive_facts.py` 生成。四组并集必须等于 10 只代表股。硬口径：

| 判定 | 放量：`turnover >= turnover_7d` | 缩量：`turnover < turnover_7d` |
|---|---|---|
| `change >= 0` | 放量上攻 | 缩量上行 |
| `change < 0` | 放量杀跌 | 缩量回调 |

文档生成阶段只能通过 `hydrate_payload_from_facts.py` 复用这张表，不得在 payload 重新分组。

## 9. facts[]

每条只登记一个展示数字或一条最终入选催化。

| 字段 | 要求 |
|---|---|
| `id` | 稳定短 id，字母开头 |
| `metric` | 指标名或事件名 |
| `value` / `unit` | 登记值和单位 |
| `period` / `as_of` | 期间 / 时点；`as_of` 不得晚于 `timestamp` |
| `kind` | `market` / `change` / `retracement` / `rebound` / `ratio` / `fundamental` / `catalyst` |
| `lane` | 市场数字用 `seed_finance_search`；催化用 `general_search` |
| `tier` | 1 / 2 / 3 |
| `source_type` | 来源性质，如 `finance_database`、`official_release`、`mainstream_media` |
| `source_name` | 来源名 |
| `url` | 催化必填；市场数字可选 |
| `usage_type` | `hard_fact` / `media_view` / `broker_estimate` / `author_inference` 等 |
| `body_use` | `yes` / `no`；正文只用非 `no` 条目 |
| `exclude_reason` | `body_use:"no"` 时必填 |
| `level` | 催化建议填：`一手` / `权威` / `二级` |
| `freshness_reason` | 催化超过截止日前 14 个自然日但仍使用时填写 |
| `evidence` | 原文要点或数据行说明 |

硬规则：

- 行情 / 市场数字必须 `tier:1`，来自 `seed_finance_search`。
- 上市公司个股收入、利润、毛利率等业务 / 财务数字必须来自 `seed_finance_search` 或经其核验。
- 行业经营、需求、第三方统计等非个股事实可为一级或二级；二级须限定措辞。
- `kind:"catalyst"` 只能 `tier:1` 或 `tier:2`，必须有 `source_name`、`level`、`url`；三级不得作为模块2最终催化。
- 禁止登记板块 PE / 板块市盈率；只登记股票 / 代表股 PE(TTM)。

常见 `source_type`：`finance_database`、`company_announcement`、`exchange_filing`、`official_release`、`official_news_agency`、`broker_research`、`broker_estimate`、`mainstream_media`、`industry_data`、`aggregator_ugc`、`rumor`、`calculation`。

常见 `usage_type`：

| `usage_type` | 正文口吻 |
|---|---|
| `hard_fact` / `official_statement` | 可写“显示 / 披露 / 为” |
| `broker_research_view` | “XX证券研报认为” |
| `broker_estimate` | “据券商研报估算 / 机构预计” |
| `media_view` | “据XX报道” |
| `industry_data` | “据XX数据” |
| `rumor_lead` | 只作线索，不进正式事实 |
| `author_inference` | “可能 / 指向 / 仍需验证” |

## 9. 可复算项

| `kind` | 分量字段 | 复算 |
|---|---|---|
| `change` | `prev_close` / `last_close` / `change_pct` | `(last/prev - 1) * 100` |
| `retracement` | `range_high` / `range_low` / `range_pct` | `(low/high - 1) * 100` |
| `rebound` | `from_low` / `rebound_to` / `rebound_pct` | `(to/low - 1) * 100` |
| `ratio` | `numerator` / `denominator` / `value` / `as_pct` | `num/den` 或 `num/den*100` |

复算容差为 0.6 个百分点或 6% 相对误差（取大者）。对不上即 lint / 复算门报错。

## 10. 与正文和 payload 绑定

- 第一阶段草稿：正文数字后用 `{fact:id}` 绑定事实；发给用户前去掉内部标记。
- 文档 payload：展示项用 `fact:"id"` 与 `value_num` 绑定；`numeric_facts` 与 facts.json 同源。
- 10 股 `stock_checks` 与 `divergence_groups` 通过 `hydrate_payload_from_facts.py` 自动映射到 payload，不在文档生成阶段重复填。

## 11. 填写顺序

1. 填 `meta`。
2. 填 `sector_checks` 原始字段：`T0` 收盘、前收、`T0` 成交额、近7日收盘基准和 7 个成交额。
3. 逐行填 10 股 `stock_checks` 原始字段：`T0` 涨跌、`T0` 成交额、`T0` PE(TTM)、近7日收盘基准 / 截止收盘 / 7 个成交额、`role`、`select_reason`、来源证据。
4. 运行 `python3 scripts/derive_facts.py work/<板块>_facts.json` 生成 `daily_change`、`change_7d`、`turnover_7d` 和四组。
5. 登记会进入正文 / 飞书文档的展示数字。
6. 模块2只登记最终入选的 3-5 条催化；候选线索留在取数笔记即可。
7. 裁定每条 facts：不可用的标 `body_use:"no"` + `exclude_reason`。
8. 跑 facts-only lint；通过后再写正文。
