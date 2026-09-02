---
name: skill-strategy-tearsheet-report
description: "Institutional-grade strategy performance tearsheet. Use when a user has a NAV / return series (a strategy, fund, or backtest) and wants a full performance report: annualized return, Sharpe/Sortino/Calmar, max drawdown, rolling metrics, monthly return heatmap, drawdown table, and benchmark-relative stats. Outputs JSON + an HTML dashboard."
license: GPL-3.0-only
category: 工具
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-strategy-tearsheet-report
  repository_url: https://github.com/quantskills/skill-strategy-tearsheet-report
  project_type: skill
  collection: reporting
  status: community-draft
---

## WorkBuddy PandaData MCP 强制覆盖

本节优先于本 Skill 后续取数示例。策略收益必须来自上游封存的真实回测文件；基准数据先按
共享 Runtime Skill 调用 `auth_status` 与 `call_pandadata(get_index_daily)`，再把真实返回
保存为 CSV。只运行 `scripts/tearsheet_workbuddy.py --nav/--returns ... --benchmark-csv ...`。
禁止本地数据 SDK、样本回退和合成数据；缺少文件或 Connector 数据时必须返回阻塞。

## WorkBuddy PandaData MCP 强制覆盖

本节优先于本 Skill 后续取数示例。策略收益必须来自上游封存的真实回测文件；基准数据先按
共享 Runtime Skill 调用 `auth_status` 与 `call_pandadata(get_index_daily)`，再把真实返回
保存为 CSV。只运行 `scripts/tearsheet_workbuddy.py --nav/--returns ... --benchmark-csv ...`。
禁止本地数据 SDK、样本回退和合成数据；缺少文件或 Connector 数据时必须返回阻塞。

## WorkBuddy PandaData MCP 强制覆盖

本节优先于本 Skill 后续取数示例。策略收益必须来自上游封存的真实回测文件；基准数据先按
共享 Runtime Skill 调用 `auth_status` 与 `call_pandadata(get_index_daily)`，再把真实返回
保存为 CSV。只运行 `scripts/tearsheet_workbuddy.py --nav/--returns ... --benchmark-csv ...`。
禁止本地数据 SDK、样本回退和合成数据；缺少文件或 Connector 数据时必须返回阻塞。

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "上传净值/收益序列 CSV（date, nav 或 date, return），或给出基金代码；说明基准",
    "required": true
  },
  "fields": [
    {
      "key": "benchmark_symbol",
      "label": "基准代码",
      "type": "text",
      "placeholder": "如 000300.SH（沪深300）",
      "help": "留空则不做相对基准分析"
    },
    {
      "key": "periods_per_year",
      "label": "年化期数",
      "type": "number",
      "default": "252",
      "help": "日频 252，周频 52，月频 12"
    },
    {
      "key": "rf_annual",
      "label": "无风险利率（年化）",
      "type": "number",
      "default": "0.02",
      "help": "用于夏普/索提诺"
    }
  ],
  "prompt_template": "{{#task}}序列与要求：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}对上述净值/收益序列生成绩效 tearsheet。{{#benchmark_symbol}}基准采用 {{benchmark_symbol}}，做超额/信息比率/相关性分析。{{/benchmark_symbol}}{{#periods_per_year}}年化期数 {{periods_per_year}}。{{/periods_per_year}}{{#rf_annual}}无风险利率 {{rf_annual}}。{{/rf_annual}}计算年化收益/波动/夏普/索提诺/Calmar/最大回撤/滚动指标/月度收益/回撤区间，输出 JSON + HTML 看板与中文摘要。仅研究参考，不构成投资建议。"
}
```

# skill-strategy-tearsheet-report

role: skill · output: Tearsheet (JSON + HTML) · paradigm: performance analytics

把“一条净值曲线”变成机构级的完整绩效画像。这是组织里所有回测/因子技能都需要、却各自零散拼凑的**统一交付层**。

## 🎯 这个 Skill 解决什么问题

组织里一堆技能会产出净值/收益，但**绩效指标各算各的、格式不统一、没有可视化交付**。本 Skill 做一个标准 tearsheet 生成器：输入一条序列，输出完整、一致、可复现的绩效报告 + HTML 看板，能被任何上游回测技能当“最后一公里”调用。

指标全集：

- **收益/风险**：年化收益、年化波动、累计收益、最优/最差单期。
- **风险调整**：Sharpe、Sortino、Calmar、Omega。
- **回撤**：最大回撤、回撤持续期、Top-N 回撤区间表、恢复时间。
- **分布**：偏度、峰度、VaR/CVaR、胜率、盈亏比。
- **滚动**：滚动夏普、滚动波动、滚动回撤。
- **时间聚合**：月度收益热力图、年度收益条。
- **相对基准**（可选）：超额收益、信息比率、Beta、跟踪误差、相关性。

## ⚡ 工作流（Agent 按此执行）

1. **解析序列**：读 NAV 或 return（date 列 + 数值列），推断频率；给了基金代码则按自然年分段调用 `get_fund_daily`，用收盘价构造净值代理。
2. **取基准**（可选）：`get_index_daily` 拉基准净值，对齐日期。
3. **算指标**：`scripts/metrics.py`（收益/风险/回撤/分布/滚动）。
4. **渲染**：`scripts/render.py` 出 JSON + 自包含 HTML 看板（月度热力图、净值+回撤双轴、滚动夏普）。
5. **摘要**：中文一段话点出策略性格（趋势/均值回复）、最大痛点（回撤/尾部）、与基准关系。

```bash
python scripts/tearsheet_workbuddy.py --returns selected_returns.csv --benchmark-csv benchmark.csv --out tearsheet.json --html tearsheet.html
python examples/run_demo.py
```

## 🗃️ 输入契约

| 输入 | 形态 | 必需 | 说明 |
|------|------|------|------|
| `series` | CSV(date,nav) 或 (date,return) | 是 | 净值或逐期收益 |
| `benchmark_symbol` | str | 否 | 指数代码，做相对分析 |
| `periods_per_year` | int | 否 | 默认 252 |
| `rf_annual` | float | 否 | 默认 0.02 |

输出 `Tearsheet`：`summary{...} / risk_adjusted{...} / drawdowns[] / rolling{...} / monthly_returns[][] / vs_benchmark{...}` + HTML。

## 📦 输出契约

产物对象 `Tearsheet`（JSON + 自包含 HTML 看板）：

| 字段 | 说明 |
|------|------|
| `summary{...}` | 总收益/年化/波动等 |
| `risk_adjusted{...}` | 夏普/索提诺/卡玛等风险调整指标 |
| `drawdowns[] / rolling{...} / monthly_returns[][]` | 回撤/滚动/月度 |
| `vs_benchmark{...}` | 相对基准 |

文件产物：`--out tearsheet.json`、`--html tearsheet.html`。所有指标须标注序列频率与年化期数口径，基准来源（`get_index_daily`）与数据区间可溯源。

## 🔗 管线定位

```
因子/策略 → 回测(skill-backtest) → [本 Skill：绩效 tearsheet 交付] → 汇报/归档
```

它是回测的**下游交付标准**：任何产出净值的技能都可把序列丢给它，得到统一 tearsheet，避免每个技能重造绩效轮子。

## 📦 仓库结构

```
skill-strategy-tearsheet-report/
├── SKILL.md / README.md / requirements.txt
├── scripts/
│   ├── metrics.py        # 全套绩效指标
│   ├── render.py         # JSON + HTML 看板
│   └── tearsheet.py      # CLI 入口
├── references/
│   └── metrics-glossary.md   # 每个指标公式与解读
└── examples/
    └── run_demo.py
```

## ✅ 质量门槛

产物交付前须满足（不达标则降级并在报告显式声明，不静默通过）：

- **可溯源**：每个关键数字可回溯到具体 Pandadata 接口 + 数据日期；缺失数据进 `degraded[]`，绝不编造或用近似冒充真实值。
- **降级透明**：任一数据源为空/受限时，报告如实标注并降低结论置信度。
- **口径一致**：单位、频率、基准口径在报告中显式声明。
- **仅研究**：产物为研究/教育参考，不构成投资建议，不承诺收益。
- 年化期数须与序列频率一致（否则夏普失真）；月度热力图要求跨度≥2月。

## ⚠️ 使用规则

- 输入若为 NAV 先转对数/算术收益；缺失日期按频率补齐并标注。
- 年化期数必须与序列频率一致，否则夏普失真。
- 月度热力图要求序列跨度 ≥ 2 个月才有意义。
- 只做研究/绩效展示参考，不构成投资建议。
