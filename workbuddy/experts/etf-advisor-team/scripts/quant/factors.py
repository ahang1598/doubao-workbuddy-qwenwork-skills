"""
quant.factors —— 因子、情景与市场判定指标门面（从 quant_scorer.py 重新导出）。

覆盖子命令：
  - crowding（拥挤度五维百分制打分）
  - policy（政策力度四维打分）
  - scenario_profit（三情景概率加权净利润 + 灵敏度分析）
  - market_regime（市场底部/顶部信号计数器）

服务于第 3 步五维辅助验证、第 4-B 步辅助计算、总仓位中枢确定。
"""
from quant_scorer import (  # noqa: F401
    calc_crowding,
    calc_policy,
    calc_scenario_profit,
    calc_market_regime,
)

__all__ = [
    "calc_crowding",
    "calc_policy",
    "calc_scenario_profit",
    "calc_market_regime",
]
