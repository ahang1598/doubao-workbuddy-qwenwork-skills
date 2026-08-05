# 飞书文档 payload 合同（legacy fallback）

仅当用户要求“生成飞书文档”后读取本文件。当前第二阶段首选中间产物已切换为 `doc.md`，合同见 `doc_markdown_contract.md`；本文件保留为 legacy fallback。字段全集与长解释见 `payload_fields.md`；示例 payload 是测试资产，默认不要读 `assets/example_payload.json`。

## 1. 原则

- payload 内容以第一阶段对话框正文为唯一母版；不重新取数、不重算、不改核心判断、不另写一版分析。
- payload 文本只允许把第一阶段正文**原句搬运**并字段化；不允许压缩、改写、同义改写或重新概括。payload 某段内容在正文中找不到原文片段时，回第一阶段补正文并重新 lint，不在飞书文档阶段现场发挥。
- 10 股行情、近7日复算、`role/select_reason`、四组分组来自第一阶段 facts；文档生成阶段不得手工重填。
- payload 生成后必须先水合，再校验，再构造 lark-doc XML。

## 2. 准出顺序

```bash
python3 -m json.tool work/<板块>_payload.json >/dev/null
python3 scripts/hydrate_payload_from_facts.py work/<板块>_facts.json work/<板块>_payload.json
python3 scripts/check_payload_against_chat.py work/<板块>_分析草稿.md work/<板块>_payload.json
python3 scripts/check_market_facts.py work/<板块>_payload.json
python3 scripts/validate_doc_payload.py work/<板块>_payload.json
```

`hydrate_payload_from_facts.py` 会覆盖 `stocks` / `divergence_groups[].stocks` 并写入 `_facts_hydration.stocks_sha256`；同时会从同目录 `<板块>_分析草稿.md` 自动抽取模块3四组解释写入 `divergence_groups[].feature`。缺指纹或水合后被手工改动，文档 payload 校验会报错；若草稿路径不标准，运行水合时用 `--chat work/<板块>_分析草稿.md` 显式传入。

`check_payload_against_chat.py` 会检查 payload 文本是否是第一阶段正文对应模块中的原文片段；失败时不要改 payload 文案凑过，回到第一阶段正文补足内容。

## 3. chat → payload 映射

生成飞书文档前按下表映射；所有文本字段必须原句复制或截取第一阶段正文中的连续原文片段，不做压缩、不做改写、不新增判断。

| 第一阶段正文 | payload 字段 | 要求 |
|---|---|---|
| 开篇核心结论 | `headline` / `summary` / `key_chips` | `headline` 只搬运 `标题：` 后的一句话核心判断；`summary` 搬运标题后的解释段，去掉打分复述；`key_chips` 搬运四个展示值 |
| `## 直接回答` | `answer.restate` / `answer.conclusion` / `answer.next` | 对应“问题 / 结论 / 下一步”三行 |
| 模块1本段结论 + 四维表 | `section_summaries.heat` / `dimensions[].read` | 解读必须来自表格或本段文字，不另写泛化点评 |
| 模块2本段结论 + 催化条目 | `section_summaries.catalysts` / `catalysts[].fact/why/verify` | fact/why/verify 分别映射正文三段 |
| 模块3本段结论 + 四组 | `section_summaries.divergence` / `divergence_groups[].feature` | 组员名单由 facts 水合；解释文字由水合脚本从 chat 模块3原句抽取，或在 payload 中原句搬运后由水合保留 |
| 模块4本段结论 + 信号 | `section_summaries.watch` / `watch_signals[].signal/watch/improve/worsen` | 每条映射正文信号，不新增新观察项 |
| 模块5本段结论 + 风险 | `section_summaries.risks` / `risks[].title/trigger/why/invalidate` | 每条映射正文风险，不新增空泛风险 |
| 模块6来源 | `sources[]` | 放正文实际使用的公开来源与数据终端；`name` 填来源名，`title` 填模块6原句中的标题 / 用途，`date` 填日期；有 URL 的展示为链接，无 URL 的展示为数据终端 |

## 4. 顶层必填

- `sector`
- `market`
- `timestamp`
- `index_caliber`
- `selected_stocks`
- `data_mode`（固定 `full`）
- `composite_score`
- `gauge_pill`
- `info_score`
- `market_score`
- `headline`
- `summary`
- `key_chips`
- `divergence`
- `answer`
- `section_summaries`
- `dimensions`
- `catalysts`
- `stocks`
- `divergence_groups`
- `watch_signals`
- `risks`
- `sources`
- `numeric_facts`

## 5. key_chips

必须恰好 4 张，每张带 `metric_key`，且不重复。

固定必有：
- `close_point`：目标概念板块指数 / 板块行情当日收盘点位
- `pe_ttm`：10 只代表股中市值最大那只的股票 PE(TTM)，`label` 写成 `<股票名> PE(TTM)`

另外两张二选一成对：
- 当日组：`daily_change` + `turnover_amount`
- 近7日组：`change_7d` + `turnover_7d`

除 `pe_ttm` 外，小卡都是目标板块口径：板块涨跌幅、板块成交额、板块近7个交易日涨跌幅、板块近7个交易日日均成交额。不要用 10 股样本合计 / 均值替代；目标板块字段不可得时回到第一阶段补取，不输出替代值。

每张都带：

```json
{
  "label": "...",
  "value": "...",
  "unit": "...",
  "metric_key": "...",
  "source": { "lane": "seed_finance_search", "as_of": "YYYY-MM-DD" },
  "fact": "facts_id"
}
```

## 6. dimensions

固定 4 个，顺序不可变：

1. 价格涨跌
2. 成交量能
3. 代表股表现
4. 估值位置

每项字段：
- `name`
- `track: "行情"`
- `value`
- `state`：确认 / 弱确认 / 背离
- `read`
- `source.lane: "seed_finance_search"`

`value` 逐字搬运模块1表格的“数值”列，不能压缩成单个裸数字；它应是紧凑证据短句。估值位置只按 10 只代表股 PE(TTM) 分析，不写板块 PE；如果 value 含 PE/PB/PS，必须写 TTM / 静态 / 动态 / LYR / 滚动等口径与时点。`read` 从模块1对应卡片解读搬运，不压缩、不改写。

## 7. catalysts

模块2时间线，精选 3-5 条，最多 6 条。每条：

- `date`：事件实际发生日，且不晚于 `timestamp`
- `tone`
- `category`
- `source_name`
- `title`
- `fact`
- `url`
- `why`
- `verify`
- `source`: `{ "lane": "general_search", "tier": 1 或 2, "level": "..." }`

来源只允许一级 / 二级。个人 / 自媒体 / 无法确认机构作者不得入选。聚合 / 分发承载页若有机构署名，只能标二级；标一级会报错。

## 8. stocks 与 divergence_groups

payload 草稿可以留空或粗填，但最终必须由 `hydrate_payload_from_facts.py` 从 facts 覆盖。

文档生成阶段只检查搬运一致性，不重复做：
- 10 股完整性
- 近7日复算
- 四组分组正确性
- `role/select_reason`

这些内容如有错，回第一阶段 facts 修正后重新水合。

## 9. watch_signals

建议 4 条，最多 4 条。每条：

- `signal`
- `watch`
- `improve`
- `worsen`
- `event_date`：有具体日历日期时必填，且必须晚于 `timestamp`

持续型阈值无固定日期可不填 `event_date`，但文本里不要写具体日期。不要出现“信息热度+1 / 行情热度-1”等内部评分语言。

## 10. risks

每条：
- `title`
- `trigger`
- `why`
- `invalidate`

风险要可观察、可证伪，不写空泛风险。

## 11. numeric_facts

登记 payload 中展示的关键数字，与第一阶段 facts 同源。市场数字必须：

- `kind` 为 `market` / `change` / `retracement` / `rebound` / `ratio` 等
- `tier: 1`
- `lane: "seed_finance_search"`
- 有 `source_name`
- 可复算项带原始分量

催化类事实用 `kind:"catalyst"`，`lane:"general_search"`，`tier` 只能 1/2。
