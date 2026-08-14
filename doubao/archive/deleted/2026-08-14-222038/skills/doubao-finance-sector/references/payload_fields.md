# 飞书文档 payload 字段长参考

> 长参考文件：默认先读 `references/payload_contract.md`。只有 payload 报错看不懂、需要字段全集、或维护文档 payload 合同时，再读本文。飞书文档生成流程、hydrate 顺序和准出命令以 `payload_contract.md` 为准；硬校验以 `scripts/validate_doc_payload.py` 与 `scripts/check_market_facts.py` 为准；payload 文本必须从第一阶段正文原句搬运，不压缩、不改写。

## 字段分组

| 字段 | 用途 | 说明 |
|---|---|---|
| `sector` / `market` / `timestamp` / `index_caliber` | 文档元信息 | 顶部元数据行使用 |
| `selected_stocks` | 代表股说明 | 顶部和综合热度章节列出 10 只代表股 |
| `composite_score` / `info_score` / `market_score` | 热度分 | 1-5 分；综合分公式见 `scoring_and_divergence.md` |
| `gauge_pill` | 综合热度标签 | 简短定性标签 |
| `headline` / `summary` | 开篇核心结论 | 来自正文 `标题：` 与其后 summary |
| `key_chips` | 4 个核心指标 | 生成飞书高亮块 |
| `divergence` | 双轨背离卡 | `type` 可省，校验脚本按分数判定；`verdict` / `meaning` 必填 |
| `answer` | 直接回答 | `restate` / `conclusion` / `next` |
| `section_summaries` | 模块1-5本段结论 | 键：`heat` / `catalysts` / `divergence` / `watch` / `risks` |
| `dimensions` | 模块1四维度 | 固定四项：价格涨跌、成交量能、代表股表现、估值位置 |
| `catalysts` | 模块2催化 | 3-5 条，最多 6 条，必须可追溯 |
| `stocks` / `divergence_groups` | 模块3个股与四组 | 股票与组员由 facts 覆盖；解释文字从 chat 原句搬运 |
| `watch_signals` | 模块4盯盘信号 | 3-4 条，最多 4 条 |
| `risks` | 模块5风险 | 至少 3 条 |
| `sources` | 模块6来源 | 有 URL 的来源生成飞书链接，无 URL 的作为数据终端说明 |
| `numeric_facts` | 展示数字登记 | 用于复算和来源一致性校验 |
| `gaps` / `claim_to_source` | 内部留痕 | 不写入飞书正文，除非规范明确要求 |

## 关键对象形状

### key_chips

```json
{
  "label": "当日涨跌幅",
  "value": "+2.35",
  "unit": "%",
  "metric_key": "daily_change",
  "color": "up",
  "source": { "lane": "seed_finance_search", "as_of": "YYYY-MM-DD" },
  "fact": "facts_id"
}
```

`metric_key` 固定集合：`close_point`、`pe_ttm`、`daily_change`、`turnover_amount`、`change_7d`、`turnover_7d`。当日组和近7日组必须成对选择。

### divergence

```json
{
  "type": "信息热 · 行情冷",
  "verdict": "一句话判定",
  "meaning": "展开说明持续性、机会和风险"
}
```

`type` 若填写，必须与 `info_score` / `market_score` 按 3 分阈值落入的象限一致。

### dimensions

```json
{
  "name": "价格涨跌",
  "track": "行情",
  "value": "收盘点位 + 当日/近7日涨跌对比",
  "state": "确认",
  "read": "来自正文的连续原文片段",
  "source": { "lane": "seed_finance_search" }
}
```

四项顺序固定，不增加资金流、公开催化等旧维度。

### catalysts

```json
{
  "date": "YYYY-MM-DD",
  "tone": "利好",
  "category": "政策 / 产业 / 事件 / 风险 / 中性",
  "source_name": "来源名",
  "title": "事件标题",
  "fact": "事实原句",
  "url": "https://...",
  "why": "为什么重要的原句",
  "verify": "后续验证的原句",
  "source": { "lane": "general_search", "tier": 1, "level": "一级" }
}
```

模块2只允许一级 / 二级来源。聚合页看署名主体；个人、自媒体、无法确认机构主体不得入选。

### stocks 与 divergence_groups

文档生成阶段不要手工重填 10 股行情、近7日复算、`role/select_reason` 或四组分组。运行：

```bash
python3 scripts/hydrate_payload_from_facts.py work/<板块>_facts.json work/<板块>_payload.json
```

水合脚本会从 facts 覆盖 `stocks` 和 `divergence_groups[].stocks`，并写入 `_facts_hydration.stocks_sha256`。后续校验会检查指纹，防止文档生成阶段手工改动。

### watch_signals

```json
{
  "signal": "被观察的具体变量",
  "watch": "盯什么阈值 / 兑现点",
  "improve": "改善后主结论如何升级",
  "worsen": "恶化后主结论如何降级",
  "event_date": "YYYY-MM-DD"
}
```

`event_date` 仅用于有具体未来日期的预定型信号，且必须晚于数据截止日。持续型阈值可以不填。

### risks

```json
{
  "title": "风险标题",
  "trigger": "可观察触发条件",
  "why": "风险说明 / 影响机制",
  "invalidate": "证伪信号"
}
```

`why` 在飞书文档中作为说明段，不显示字段名。

## 常见报错

| 报错关键词 | 含义 | 修复 |
|---|---|---|
| `json.tool` | JSON 语法错误 | 修正逗号、引号、括号 |
| `不是第一阶段正文对应模块中的连续原文片段` | payload 文本不是原句搬运 | 回正文补足或从正文复制连续片段 |
| `stocks_sha256` / `hydrate` | 未水合或水合后手改 `stocks` / `divergence_groups` | 重新运行 `hydrate_payload_from_facts.py` |
| `source.lane` | 来源 lane 错误或缺失 | 行情项用 `seed_finance_search`，催化用 `general_search` |
| `tier` | 催化来源分级不合规 | 只保留一级 / 二级来源 |
| `composite_score` | 综合分公式不符 | 按 `round(0.55×行情 + 0.45×信息)` 修正 |
| `divergence.type` | 背离象限与分数不符 | 按信息/行情 3 分阈值修正 |
| `dimensions` | 四维度数量或顺序错误 | 固定为价格涨跌、成交量能、代表股表现、估值位置 |

交付路径必须通过 `validate_doc_payload.py`，不得把未通过校验的 payload 写入飞书文档。
