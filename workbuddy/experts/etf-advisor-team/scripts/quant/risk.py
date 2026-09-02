"""
quant.risk —— 风险与财务健康指标门面（从 quant_scorer.py 重新导出）。

覆盖子命令：
  - m_score（Beneish M-Score 八因子造假预警）
  - altman_z（Altman Z''-Score 破产风险 · 新兴市场 4 因子）
  - piotroski_f（Piotroski F-Score 9 因子财务健康评分）

用于 汇总决策第 2 步风险红线排查、基本面质量诊断。
"""
from quant_scorer import (  # noqa: F401
    calc_m_score,
    calc_altman_z,
    calc_piotroski_f,
)

__all__ = [
    "calc_m_score",
    "calc_altman_z",
    "calc_piotroski_f",
]
