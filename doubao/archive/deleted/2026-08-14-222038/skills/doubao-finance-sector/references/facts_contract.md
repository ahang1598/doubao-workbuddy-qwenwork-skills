# facts.json 合同（默认读取）

本文件是第一阶段 facts.json 的默认合同。长解释、完整枚举与示例见 `facts_schema.md`；报错无法判断时再读长参考。

## 1. 创建方式

不要从空白文件手写摘要型 JSON。优先生成骨架：

```bash
python3 scripts/init_facts.py \
  --sector "<板块名>" \
  --index-caliber "<概念板块 名称+代码>" \
  --stocks "股票1,股票2,股票3,股票4,股票5,股票6,股票7,股票8,股票9,股票10" \
  --timestamp "数据截至 YYYY-MM-DD 收盘" \
  --today "YYYY-MM-DD" \
  -o work/<板块>_facts.json
```

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

不要写成 `sector_name`、`sector_index`、`top_10_stocks`、`catalysts` 这类摘要结构。尤其不要在 `sector_index` 或 `facts[]` 中登记板块 PE / 板块市盈率。

## 2. meta

必填：

- `sector`：板块名。
- `index_caliber`：目标概念板块名称 + 代码。
- `selected_stocks`：恰好 10 只代表股名称。
- `timestamp`：如 `数据截至 2026-06-18 收盘`。这里的 `T` / `T0` 固定为最近一个已经完成收盘的交易日；盘中生成时不得把当日未收盘行情作为 `T`，应回退到上一已收盘交易日。未确定 `T0` 前不得搜索或登记行情数字；下文所有“当日”均指 `T0` 的已收盘行情。
- `today`：`YYYY-MM-DD`。
- `data_mode`：固定填 `full`。板块核心指标必须是目标板块自身数据。

## 3. sector_checks

必须登记目标板块 5 个核心指标，与 10 股一样先取数、先校验。采集阶段只填原始取数字段；派生字段由 `derive_facts.py` 统一生成。

| 字段 | 要求 |
|---|---|
| `close_point` | 目标概念板块指数 / 板块行情 `T0` 收盘点位 |
| `prev_close` | `T0` 前一交易日收盘点位，用于复算 `T0` 涨跌幅 |
| `daily_change` | 目标概念板块 `T0` 涨跌幅 %，脚本从 `close_point / prev_close` 复算 |
| `turnover_amount` | 目标概念板块全成分 / 官方板块口径 `T0` 成交额，亿元 |
| `change_7d` | 目标概念板块近7个交易日涨跌幅 %，脚本从 `d7_close_t / d7_close_base` 复算；当天为 T / Day 0，基准为 T-7 交易日收盘 |
| `turnover_7d` | 目标概念板块近7个交易日日均成交额，脚本从 `d7_turnovers` 复算，亿元 |
| `d7_close_base` | T-7 交易日收盘点位（从数据截止日 T 往前数第 7 个交易日） |
| `d7_close_t` | 截止日 T 收盘点位；可由脚本用 `close_point` 补齐 |
| `d7_turnovers` | 目标板块最近 7 个交易日成交额数组，长度为 7 |
| `as_of` / `source_name` | 数据时点与来源名 |
| `evidence` | 从 `seed_finance_search` / 同花顺返回结果复制的原始数据行摘要 |

派生口径：

- `daily_change = close_point / prev_close - 1`
- `change_7d = d7_close_t / d7_close_base - 1`；其中 `d7_close_t` 为数据截止日 T 收盘，`d7_close_base` 为 T-7 交易日收盘。注意：当天作为 Day 0，不能用最近 7 个交易日窗口第一天（T-6）作基准。
- `turnover_7d = avg(d7_turnovers)`

取数动作：板块近7日相关数据，第一轮就按 `T-7` 至 `T` 的 8 个已收盘交易日日线一次性拿齐；不要先取 `T-6` 至 `T` 再补 `T-7`。登记时从同一批日线切出 `d7_close_base`、`d7_close_t` 和 `d7_turnovers`。

除 `pe_ttm` 外，顶部小卡取 `sector_checks` 的目标板块口径；不得用 10 股样本合计 / 均值替代板块指标。

## 4. stock_checks

必须恰好 10 条，名称等于 `meta.selected_stocks`。采集阶段逐行填原始取数字段、角色、选取理由和 evidence；派生字段由 `derive_facts.py` 统一生成。

| 字段 | 要求 |
|---|---|
| `name` | 股票名称 |
| `change` | `T0` 涨跌幅 % |
| `turnover` | `T0` 成交额，亿元 |
| `pe_ttm` | 股票 `T0` PE(TTM)，必填；不得填板块 PE |
| `change_7d` | 近7个交易日涨跌幅 %，脚本从 `d7_close_t / d7_close_base` 复算；当天为 T / Day 0，基准为 T-7 交易日收盘 |
| `turnover_7d` | 近7个交易日日均成交额，脚本从 `d7_turnovers` 复算，亿元 |
| `d7_close_base` | T-7 交易日收盘价（从数据截止日 T 往前数第 7 个交易日） |
| `d7_close_t` | 截止日 T 收盘价 |
| `d7_turnovers` | 最近 7 个交易日成交额数组，长度为 7 |
| `role` | 定性角色 |
| `select_reason` | 为什么选入 10 只代表股 |
| `as_of` | 数据时点，不得晚于 `timestamp` |
| `source_name` | 同花顺数据库或同花顺具体口径 |
| `evidence` | 从 `seed_finance_search` / 同花顺返回结果复制的原始数据行摘要 |

派生口径：

- `change_7d = d7_close_t / d7_close_base - 1`；其中 `d7_close_t` 为数据截止日 T 收盘，`d7_close_base` 为 T-7 交易日收盘。注意：当天作为 Day 0，不能用最近 7 个交易日窗口第一天（T-6）作基准。
- `turnover_7d = avg(d7_turnovers)`

取数动作：逐股第一轮就取 `T-7` 至 `T` 的 8 个已收盘交易日日线；从同一批结果里登记 `T-7` 收盘价、`T` 收盘价，以及 `T-6` 至 `T` 的 7 个成交额。

`evidence` 不是结论改写，而是用于审计的取数留痕，至少包含数据终端名、标的名、日期和关键字段；没有 evidence 的数字即使数学自洽也不能通过。

## 5. divergence_groups

键固定：

```json
{
  "放量上攻": [],
  "缩量上行": [],
  "缩量回调": [],
  "放量杀跌": []
}
```

硬口径：

| 判定 | 放量：`turnover >= turnover_7d` | 缩量：`turnover < turnover_7d` |
|---|---|---|
| `change >= 0` | 放量上攻 | 缩量上行 |
| `change < 0` | 放量杀跌 | 缩量回调 |

`divergence_groups` 由 `derive_facts.py` 按硬口径生成，不手填。四组并集必须等于 10 只代表股，不得遗漏、重复或混入口径外股票。

## 6. facts[]

每条只登记一个展示数字或一条入选催化。

必填 / 常用字段：

- `id`：稳定短 id，字母开头。
- `metric`：指标名或事件名。
- `value` / `unit`：登记值和单位。
- `period` / `as_of`：期间和时点。
- `kind`：`market` / `change` / `retracement` / `rebound` / `ratio` / `fundamental` / `catalyst`。
- `tier`：1 / 2 / 3。
- `lane`：市场数字用 `seed_finance_search`；催化用 `general_search`。
- `source_type` / `source_name`：来源性质和来源名。
- `url`：催化必填；市场数字可选。
- `usage_type`：如 `hard_fact` / `media_view` / `broker_estimate` / `author_inference`。
- `body_use`：`yes` / `no`；正文只用非 `no` 条目。
- `exclude_reason`：`body_use:"no"` 时必填。
- `freshness_reason`：催化超过截止日前 14 个自然日但仍使用时填写。
- `evidence`：原文要点或数据行说明。

规则：

- 行情 / 市场数字必须 `tier:1`，来自 `seed_finance_search`。
- 催化只能 `tier:1` 或 `tier:2`，必须有 `source_name`、`level`、`url`。
- 二级事实正文要带限定措辞。
- 三级不得作展示数字或模块2最终催化。
- 禁止登记板块 PE / 板块市盈率；只登记股票 / 代表股 PE(TTM)。

## 7. 第一阶段 lint 顺序

填完原始取数字段后，先派生可计算项：

```bash
python3 scripts/derive_facts.py work/<板块>_facts.json
```

再跑 facts-only：

```bash
python3 scripts/lint_analysis.py --strict work/<板块>_facts.json
```

通过后再写草稿，写完再跑：

```bash
python3 scripts/lint_analysis.py --strict work/<板块>_分析草稿.md work/<板块>_facts.json
```

第一次失败时：

1. 完整读完所有错误。
2. 如果是字段别名、`lane`、嵌套 `source`、摘要型顶层这类机械问题，运行：

```bash
python3 scripts/repair_facts.py work/<板块>_facts.json
```

3. 修复或回填原始字段后，再运行 `derive_facts.py`，不要手工补 `daily_change`、`change_7d`、`turnover_7d` 或四组。
4. 如果缺真实行情字段、7日序列、来源、`role/select_reason` 或 `facts[]`，直接回填已收集数据，不靠 repair。
5. 只做局部修复，不推倒重建 facts.json。
