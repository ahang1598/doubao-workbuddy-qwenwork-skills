---
name: skill-backtest-overfit
description: "Detect backtest overfitting and selection bias from multiple testing. Use when a user has a backtest / factor result and asks whether the Sharpe is real, whether a strategy is overfit, or wants to validate results before trusting them. Computes Deflated Sharpe Ratio, Probability of Backtest Overfitting (PBO), multiple-testing haircut, and Minimum Track Record Length."
license: GPL-3.0
category: 工具
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-backtest-overfit
  repository_url: https://github.com/quantskills/skill-backtest-overfit
  project_type: skill
  collection: portfolio-risk-validation
---

## WorkBuddy 真实证据强制覆盖

本节优先于本 Skill 后续示例。此成员只审计主流程封存的真实 `selected_returns.csv` 和
`trials_matrix.csv`；不得自行连接本地数据 SDK，也不得用合成、模拟或随机行情替代缺失
证据。若上游收益证据缺失，必须返回阻塞。需要补取市场数据时，按共享 Runtime Skill
执行 `auth_status` 与 `call_pandadata`，保存真实结果后再进入统计审计。

## WorkBuddy 真实证据强制覆盖

本节优先于本 Skill 后续示例。此成员只审计主流程封存的真实 `selected_returns.csv` 和
`trials_matrix.csv`；不得自行连接本地数据 SDK，也不得用合成、模拟或随机行情替代缺失
证据。若上游收益证据缺失，必须返回阻塞。需要补取市场数据时，按共享 Runtime Skill
执行 `auth_status` 与 `call_pandadata`，保存真实结果后再进入统计审计。

## WorkBuddy 真实证据强制覆盖

本节优先于本 Skill 后续示例。此成员只审计主流程封存的真实 `selected_returns.csv` 和
`trials_matrix.csv`；不得自行连接本地数据 SDK，也不得用合成、模拟或随机行情替代缺失
证据。若上游收益证据缺失，必须返回阻塞。需要补取市场数据时，按共享 Runtime Skill
执行 `auth_status` 与 `call_pandadata`，保存真实结果后再进入统计审计。

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "说明待检验的回测、收益序列、试验次数及数据文件；可上传 selected_returns 和 trials_matrix",
    "required": true
  },
  "fields": [
    {
      "key": "n_trials",
      "label": "试验次数",
      "type": "number",
      "placeholder": "例如 200",
      "help": "请如实填写所有尝试过的参数或策略配置数量"
    },
    {
      "key": "periods_per_year",
      "label": "年化期数",
      "type": "number",
      "default": "252",
      "help": "日频通常为 252"
    },
    {
      "key": "haircut_method",
      "label": "多重检验方法",
      "type": "select",
      "default": "holm",
      "options": [
        { "value": "holm", "label": "Holm" },
        { "value": "bonferroni", "label": "Bonferroni" },
        { "value": "bhy", "label": "BHY" }
      ]
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}检验该回测的过拟合与多重选择偏差。{{#n_trials}}按真实试验次数 {{n_trials}} 计算。{{/n_trials}}{{#periods_per_year}}年化期数采用 {{periods_per_year}}。{{/periods_per_year}}{{#haircut_method}}多重检验校正采用 {{haircut_method}}。{{/haircut_method}}计算 DSR、PBO、Haircut Sharpe 和最小样本长度，缺少试验矩阵时明确降级项及局限，给出可追溯的通过/失败结论，输出中文报告。"
}
```

# skill-backtest-overfit

role: skill · output: OverfitReport (JSON + text) · paradigm: statistical validation of backtests

把"一个回测的 Sharpe 到底是不是真的"变成可计算、可引用、可归档的统计结论。这是因子流水线最后、也是最缺的**统计守门员**。

## 🎯 这个 Skill 解决什么问题

量化生态在**批量造因子/调参**：同一段历史数据上试了 N 个配置，挑出最好看的一个。问题是——**只要 N 够大，纯噪声里也必然能挑出一个 Sharpe 很高的"策略"**。常规 health-check（持仓数、换手率、回撤区间）抓不到这种选择偏差。

本 Skill 用四个有原始文献支撑的统计量回答："这个回测有多大概率是过拟合？"

- **Deflated Sharpe Ratio (DSR)** — 把"试了 N 次"的选择偏差从 Sharpe 里扣掉，给出"真 SR > 0"的概率。
- **PBO（回测过拟合概率）** — 样本内最优的配置，在样本外有多大概率沦为中等水平。
- **Haircut Sharpe** — 多重检验下给 Sharpe 打的折。
- **MinTRL** — 要多长样本，这个 Sharpe 才统计显著。

## ⚡ 工作流（Agent 按此执行）

1. **收集输入**：拿到①被选中策略的逐期收益序列；②（强烈建议）所有试过的配置组成的收益矩阵 `T×N`；③诚实的试验次数 `n_trials`（每个网格点、每个因子变体都算）。
2. **算 DSR / PSR / MinTRL**：`scripts/deflated_sharpe.py`。需要跨试验的 Sharpe 方差——有收益矩阵时自动估，没有则退化为单次估计（偏宽松，须提示用户）。
3. **算 PBO**：`scripts/pbo_cscv.py`，需要 `T×N` 收益矩阵，CSCV 组合对称交叉验证。
4. **算 Haircut**：`scripts/haircut.py`，Bonferroni / Holm / BHY 三选一。
5. **生成报告**：`scripts/overfit_report.py` 汇总四项 → `OverfitReport`（JSON + 文本），给出 PASS/FAIL 与触发原因。
6. **解释结论**：用业务语言告诉用户"该回测约有 X% 概率是数据挖掘噪声"，并指出最薄弱的统计项。

```bash
# 一行生成报告
python scripts/overfit_report.py --returns selected.csv --trials trials.csv --n-trials 200 --out report.json
# 离线演示（无需凭证，对比过拟合 vs 真实 edge）
# WorkBuddy: use sealed real return files
```

## 🗃️ 输入契约

| 输入 | 形态 | 必需 | 说明 |
|------|------|------|------|
| `selected_returns` | 1D 数组 / CSV 单列 | 是 | 被选中策略的**逐期**收益（非年化）|
| `trials_matrix` | `T×N` 矩阵 / CSV | 否（PBO 必需）| 每列一个被试配置的逐期收益 |
| `n_trials` | int | 是 | 诚实的多重检验次数 |
| `periods_per_year` | int | 否 | 默认 252，用于年化展示 |

输出 `OverfitReport`：`verdict / passed / deflated_sharpe_ratio / pbo / haircut / minimum_track_record_length / ...`

## 🔗 管线定位

```
因子挖掘(批量) → 评估 → 回测(skill-backtest) → [本 Skill：过拟合统计守门] → 上线
```

它是 `skill-backtest` 的**统计补充**：`skill-backtest` 给净值与启发式 health-check，本 Skill 给多重检验下的统计显著性。**任一统计项不过，先怀疑是过拟合，不要相信回测。**

## 📦 仓库结构

```
skill-backtest-overfit/
├── SKILL.md
├── README.md
├── requirements.txt
├── scripts/
│   ├── deflated_sharpe.py   # DSR / PSR / MinTRL  (Bailey & Lopez de Prado 2014)
│   ├── pbo_cscv.py          # PBO via CSCV        (Bailey et al. 2017)
│   ├── purged_kfold.py      # 净化+禁运 K-Fold CV (Lopez de Prado 2018, ch.7)
│   ├── haircut.py           # 多重检验 haircut    (Harvey & Liu 2015)
│   ├── overfit_report.py    # 汇总 → OverfitReport
├── references/
│   ├── methodology.md       # 公式推导 + 文献
│   └── anti-patterns.md     # 10 种过拟合陷阱
└── examples/
    └── run_demo.py          # 过拟合 vs 真实 edge 对照
```

## ⚠️ 使用规则

- **诚实申报 `n_trials`** 是本 Skill 成立的前提：少报 = 自欺。
- DSR/PSR 用**逐期**Sharpe，勿传年化值。
- PBO 需要足够多的配置列（N≥10 才有意义）；`n_blocks` 必须为偶数且 ≤ T。
- 只做研究/方法论参考，不构成投资建议。
