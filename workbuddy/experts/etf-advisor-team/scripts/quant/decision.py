"""
quant.decision —— 决策与仓位指标门面（从 quant_scorer.py 重新导出）。

覆盖子命令：
  - win_rate（六维胜率评估）
  - risk_reward（收益风险比 + 凯利公式 + 容错率）
  - decision_matrix（六维口径决策矩阵查表）
  - position_sizing（账户级风控仓位倒推）
  - position_check（位置充分性三维检验 · 波段/中长线买入前置）
  - odds_decay（赔率衰减评估）

汇总决策第 4-B 步定量计算的三件套（win_rate + risk_reward + decision_matrix）
与仓位倒推均汇集于此。
"""
from quant_scorer import (  # noqa: F401
    calc_win_rate,
    calc_risk_reward,
    calc_decision_matrix,
    calc_position_sizing,
    calc_position_check,
    calc_odds_decay,
)

__all__ = [
    "calc_win_rate",
    "calc_risk_reward",
    "calc_decision_matrix",
    "calc_position_sizing",
    "calc_position_check",
    "calc_odds_decay",
]
