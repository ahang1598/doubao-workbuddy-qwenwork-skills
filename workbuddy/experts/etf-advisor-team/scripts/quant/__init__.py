"""
quant 子包 —— quant_scorer.py 的**主题分组门面**。

---

## 为什么有这个子包？

`scripts/quant_scorer.py` 是本团队体量最大的脚本（~3060 行 · 23 个 `calc_*` 子命令），
历史原因下所有指标都挂在一个 argparse 入口里，便于 CLI 调用但不利于 Python 代码中
按主题定位函数。

本子包不做物理重构（避免大文件 diff 与回归风险），而是通过**门面（facade）**把
23 个 `calc_*` 函数按主题分成 4 组重新导出：

- `quant.valuation`：估值类（DCF/PEG/EV-EBITDA/ERP/PB-ROE/ROIC-WACC 等）
- `quant.risk`：风险与财务健康（M-Score/Altman Z/Piotroski F 等）
- `quant.decision`：决策与仓位（win_rate/risk_reward/decision_matrix/position_* 等）
- `quant.factors`：因子与情景（crowding/policy/market_regime/scenario_profit 等）

## 使用方式

**CLI（原样）**：
```bash
python scripts/quant_scorer.py dcf --json-input dcf_data.json
```

**Python API（主题分组）**：
```python
from quant.valuation import calc_dcf, calc_peg
from quant.risk import calc_altman_z, calc_m_score
from quant.decision import calc_win_rate, calc_decision_matrix

result = calc_dcf(...)
```

两种用法 100% 等价——底层都是同一份实现，子模块只是"按主题 re-export"。

## 和原脚本的关系

- 原 `quant_scorer.py` 保持不变，仍是 CLI 入口与 calc_* 函数的**唯一实现源**
- 本子包是**可选层**：不想用主题分组时直接 `from quant_scorer import calc_xxx` 亦可
- 未来如需真正物理拆分，只需把 `calc_*` 的函数体剪到对应子模块，
  再反向让 `quant_scorer.py` 从子模块 import 即可，迁移路径清晰
"""

from . import valuation, risk, decision, factors  # noqa: F401

__all__ = ["valuation", "risk", "decision", "factors"]
