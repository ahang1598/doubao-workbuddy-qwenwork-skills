"""
quant.valuation —— 估值类指标门面（从 quant_scorer.py 重新导出）。

覆盖子命令：
  - bank_pb_roe / roic_wacc / fcff / dcf / irr / erp / peg / ev_ebitda / valuation_percentile

数据依赖：大多需要最近一期财报 + 行业均值 + 历史分位序列。
"""
from quant_scorer import (  # noqa: F401
    calc_bank_pb_roe,
    calc_roic_wacc,
    calc_fcff,
    calc_dcf,
    calc_irr,
    calc_erp,
    calc_peg,
    calc_ev_ebitda,
    calc_valuation_percentile,
)

__all__ = [
    "calc_bank_pb_roe",
    "calc_roic_wacc",
    "calc_fcff",
    "calc_dcf",
    "calc_irr",
    "calc_erp",
    "calc_peg",
    "calc_ev_ebitda",
    "calc_valuation_percentile",
]
