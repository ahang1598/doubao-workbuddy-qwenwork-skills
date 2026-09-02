"""
metrics.py — 全套策略绩效指标（纯 numpy/pandas 实现）

约定：
  - 输入 returns 为逐期算术收益（Series，DatetimeIndex）。
  - periods_per_year（年化期数）与序列频率一致：日频 252 / 周频 52 / 月频 12。
    若不一致，夏普等年化指标会失真——务必由调用方保证。
  - 无风险利率 rf_annual 为年化，内部换算为单期。

所有函数对空/极短序列做了防御，返回 None 而非抛异常。
"""
from __future__ import annotations
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 序列预处理
# ---------------------------------------------------------------------------
def nav_to_returns(nav: pd.Series) -> pd.Series:
    """净值序列 → 逐期算术收益。首期无收益，丢弃。"""
    nav = nav.dropna().astype(float)
    return nav.pct_change().dropna()


def returns_to_nav(returns: pd.Series, start: float = 1.0) -> pd.Series:
    """逐期收益 → 归一净值曲线（起点 start）。"""
    return (1.0 + returns).cumprod() * start


def infer_periods_per_year(idx: pd.DatetimeIndex) -> int:
    """按相邻日期中位间隔粗略推断年化期数。"""
    if len(idx) < 3:
        return 252
    deltas = np.diff(idx.values).astype("timedelta64[D]").astype(float)
    med = float(np.median(deltas))
    if med <= 2:
        return 252   # 日频（交易日）
    if med <= 10:
        return 52    # 周频
    if med <= 45:
        return 12    # 月频
    return 4         # 季频


# ---------------------------------------------------------------------------
# 收益 / 风险
# ---------------------------------------------------------------------------
def cumulative_return(returns: pd.Series) -> float | None:
    if len(returns) == 0:
        return None
    return float((1.0 + returns).prod() - 1.0)


def annualized_return(returns: pd.Series, ppy: int) -> float | None:
    """几何年化收益 = (∏(1+r))^(ppy/n) - 1。"""
    n = len(returns)
    if n == 0:
        return None
    total = (1.0 + returns).prod()
    if total <= 0:
        return -1.0
    return float(total ** (ppy / n) - 1.0)


def annualized_vol(returns: pd.Series, ppy: int) -> float | None:
    """年化波动 = 单期收益标准差 × sqrt(ppy)。"""
    if len(returns) < 2:
        return None
    return float(returns.std(ddof=1) * np.sqrt(ppy))


# ---------------------------------------------------------------------------
# 风险调整
# ---------------------------------------------------------------------------
def sharpe(returns: pd.Series, ppy: int, rf_annual: float = 0.0) -> float | None:
    """夏普比率 = (年化超额收益) / 年化波动。"""
    if len(returns) < 2:
        return None
    rf_period = rf_annual / ppy
    excess = returns - rf_period
    sd = excess.std(ddof=1)
    if sd == 0:
        return None
    return float(excess.mean() / sd * np.sqrt(ppy))


def sortino(returns: pd.Series, ppy: int, rf_annual: float = 0.0) -> float | None:
    """索提诺比率 = 年化超额收益 / 下行波动（只算低于目标的负偏差）。"""
    if len(returns) < 2:
        return None
    rf_period = rf_annual / ppy
    excess = returns - rf_period
    downside = excess[excess < 0]
    if len(downside) == 0:
        return None
    dd = np.sqrt((downside ** 2).mean())
    if dd == 0:
        return None
    return float(excess.mean() / dd * np.sqrt(ppy))


def calmar(returns: pd.Series, ppy: int) -> float | None:
    """Calmar = 年化收益 / |最大回撤|。"""
    ar = annualized_return(returns, ppy)
    mdd = max_drawdown(returns)
    if ar is None or mdd is None or mdd == 0:
        return None
    return float(ar / abs(mdd))


def omega(returns: pd.Series, threshold_annual: float = 0.0, ppy: int = 252) -> float | None:
    """Omega 比率 = 超过阈值的收益之和 / 低于阈值的损失之和。"""
    if len(returns) == 0:
        return None
    thr = threshold_annual / ppy
    diff = returns - thr
    gains = diff[diff > 0].sum()
    losses = -diff[diff < 0].sum()
    if losses == 0:
        return None
    return float(gains / losses)


# ---------------------------------------------------------------------------
# 回撤
# ---------------------------------------------------------------------------
def drawdown_series(returns: pd.Series) -> pd.Series:
    """逐期回撤序列（相对历史最高净值的百分比，<=0）。"""
    nav = returns_to_nav(returns)
    peak = nav.cummax()
    return nav / peak - 1.0


def max_drawdown(returns: pd.Series) -> float | None:
    if len(returns) == 0:
        return None
    return float(drawdown_series(returns).min())


def drawdown_table(returns: pd.Series, top_n: int = 5) -> list[dict]:
    """Top-N 回撤区间表：峰值日、谷底日、恢复日、深度、持续期、恢复期。"""
    if len(returns) == 0:
        return []
    nav = returns_to_nav(returns)
    peak = nav.cummax()
    dd = nav / peak - 1.0

    episodes = []
    in_dd = False
    peak_date = nav.index[0]
    trough_date = nav.index[0]
    trough_val = 0.0

    for date, d in dd.items():
        if not in_dd and d < 0:
            # 进入新回撤：峰值是前一个高点
            in_dd = True
            peak_date = peak.loc[:date].index[peak.loc[:date].argmax()] \
                if False else _peak_date_before(nav, date)
            trough_date = date
            trough_val = d
        elif in_dd:
            if d < trough_val:
                trough_val = d
                trough_date = date
            if d >= 0:  # 恢复到新高，回撤结束
                episodes.append(_make_episode(peak_date, trough_date, date,
                                               trough_val))
                in_dd = False
    if in_dd:  # 序列结束仍未恢复
        episodes.append(_make_episode(peak_date, trough_date, None, trough_val))

    episodes.sort(key=lambda e: e["depth"])  # depth 为负，最深在前
    return episodes[:top_n]


def _peak_date_before(nav: pd.Series, date) -> object:
    """回撤开始前的最近历史最高点日期。"""
    prefix = nav.loc[:date]
    running_max = prefix.cummax()
    # 最后一个 nav==running_max 的位置即峰值
    at_peak = prefix[prefix >= running_max]
    return at_peak.index[-2] if len(at_peak) >= 2 else prefix.index[0]


def _make_episode(peak_date, trough_date, recover_date, depth) -> dict:
    def _fmt(d):
        return None if d is None else pd.Timestamp(d).strftime("%Y-%m-%d")
    dur = None
    rec = None
    if peak_date is not None and trough_date is not None:
        dur = int((pd.Timestamp(trough_date) - pd.Timestamp(peak_date)).days)
    if recover_date is not None and trough_date is not None:
        rec = int((pd.Timestamp(recover_date) - pd.Timestamp(trough_date)).days)
    return {
        "peak_date": _fmt(peak_date),
        "trough_date": _fmt(trough_date),
        "recover_date": _fmt(recover_date),
        "depth": float(depth),
        "drawdown_days": dur,        # 峰→谷 持续天数
        "recovery_days": rec,        # 谷→恢复 天数（None=尚未恢复）
        "recovered": recover_date is not None,
    }


# ---------------------------------------------------------------------------
# 分布 / 尾部
# ---------------------------------------------------------------------------
def skewness(returns: pd.Series) -> float | None:
    if len(returns) < 3:
        return None
    return float(returns.skew())


def kurtosis(returns: pd.Series) -> float | None:
    """超额峰度（正态=0）。"""
    if len(returns) < 4:
        return None
    return float(returns.kurt())


def value_at_risk(returns: pd.Series, alpha: float = 0.05) -> float | None:
    """历史法 VaR（alpha 分位，返回为负数损失）。"""
    if len(returns) == 0:
        return None
    return float(np.quantile(returns, alpha))


def cvar(returns: pd.Series, alpha: float = 0.05) -> float | None:
    """条件 VaR（尾部平均损失）。"""
    if len(returns) == 0:
        return None
    var = np.quantile(returns, alpha)
    tail = returns[returns <= var]
    if len(tail) == 0:
        return float(var)
    return float(tail.mean())


def win_rate(returns: pd.Series) -> float | None:
    if len(returns) == 0:
        return None
    return float((returns > 0).mean())


def profit_loss_ratio(returns: pd.Series) -> float | None:
    """盈亏比 = 平均盈利 / |平均亏损|。"""
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    if len(wins) == 0 or len(losses) == 0:
        return None
    avg_loss = losses.mean()
    if avg_loss == 0:
        return None
    return float(wins.mean() / abs(avg_loss))


def best_worst(returns: pd.Series) -> tuple:
    if len(returns) == 0:
        return None, None
    return float(returns.max()), float(returns.min())


# ---------------------------------------------------------------------------
# 滚动指标
# ---------------------------------------------------------------------------
def rolling_sharpe(returns: pd.Series, window: int, ppy: int,
                   rf_annual: float = 0.0) -> pd.Series:
    if len(returns) < window:
        return pd.Series(dtype=float)
    rf_period = rf_annual / ppy
    excess = returns - rf_period
    mean = excess.rolling(window).mean()
    std = excess.rolling(window).std(ddof=1)
    return (mean / std * np.sqrt(ppy)).dropna()


def rolling_vol(returns: pd.Series, window: int, ppy: int) -> pd.Series:
    if len(returns) < window:
        return pd.Series(dtype=float)
    return (returns.rolling(window).std(ddof=1) * np.sqrt(ppy)).dropna()


def rolling_drawdown(returns: pd.Series) -> pd.Series:
    """逐期回撤（即 drawdown_series），用于滚动展示。"""
    return drawdown_series(returns)


# ---------------------------------------------------------------------------
# 时间聚合：月度收益矩阵 / 年度收益
# ---------------------------------------------------------------------------
def monthly_returns_matrix(returns: pd.Series) -> dict:
    """年×月 收益矩阵（复利聚合到月）。

    返回 {years:[...], months:[1..12], matrix:[[...]] (行=年, 列=月, None=缺)}。
    """
    if len(returns) == 0:
        return {"years": [], "months": list(range(1, 13)), "matrix": []}
    monthly = (1.0 + returns).resample("M").prod() - 1.0
    years = sorted({d.year for d in monthly.index})
    matrix = []
    for y in years:
        row = []
        for m in range(1, 13):
            vals = monthly[(monthly.index.year == y) & (monthly.index.month == m)]
            row.append(float(vals.iloc[0]) if len(vals) else None)
        matrix.append(row)
    return {"years": years, "months": list(range(1, 13)), "matrix": matrix}


def annual_returns(returns: pd.Series) -> dict:
    """年度收益（复利聚合到年）。返回 {year: ret}。"""
    if len(returns) == 0:
        return {}
    yearly = (1.0 + returns).resample("Y").prod() - 1.0
    return {int(d.year): float(v) for d, v in yearly.items()}


# ---------------------------------------------------------------------------
# 相对基准
# ---------------------------------------------------------------------------
def benchmark_stats(returns: pd.Series, bench_returns: pd.Series,
                    ppy: int) -> dict | None:
    """对齐后计算：超额年化、信息比率、Beta、跟踪误差、相关性。"""
    df = pd.concat([returns.rename("s"), bench_returns.rename("b")],
                   axis=1).dropna()
    if len(df) < 3:
        return None
    s, b = df["s"], df["b"]
    active = s - b
    te = float(active.std(ddof=1) * np.sqrt(ppy))          # 跟踪误差
    ir = None
    if active.std(ddof=1) != 0:
        ir = float(active.mean() / active.std(ddof=1) * np.sqrt(ppy))
    var_b = b.var(ddof=1)
    beta = float(s.cov(b) / var_b) if var_b != 0 else None
    corr = float(s.corr(b))
    excess_ann = None
    ar_s = annualized_return(s, ppy)
    ar_b = annualized_return(b, ppy)
    if ar_s is not None and ar_b is not None:
        excess_ann = float(ar_s - ar_b)
    return {
        "n_aligned": int(len(df)),
        "excess_annualized_return": excess_ann,
        "excess_annual": excess_ann,       # 超额年化收益
        "information_ratio": ir,           # 信息比率
        "beta": beta,
        "tracking_error": te,              # 年化跟踪误差
        "correlation": corr,
    }


# ---------------------------------------------------------------------------
# 汇总：一次性算全套
# ---------------------------------------------------------------------------
def compute_all(returns: pd.Series, ppy: int, rf_annual: float = 0.02,
                bench_returns: pd.Series | None = None,
                rolling_window: int | None = None) -> dict:
    """计算完整 tearsheet 指标字典。"""
    returns = returns.dropna().astype(float)
    if rolling_window is None:
        # 默认滚动窗口 ≈ 一个年化期（但不超过序列一半）
        rolling_window = max(3, min(ppy, len(returns) // 2))

    mdd = max_drawdown(returns)
    best, worst = best_worst(returns)

    result = {
        "n_periods": int(len(returns)),
        "periods_per_year": ppy,
        "rf_annual": rf_annual,
        "start_date": returns.index[0].strftime("%Y-%m-%d") if len(returns) else None,
        "end_date": returns.index[-1].strftime("%Y-%m-%d") if len(returns) else None,
        "summary": {
            "cumulative_return": cumulative_return(returns),
            "annualized_return": annualized_return(returns, ppy),
            "annualized_vol": annualized_vol(returns, ppy),
            "max_drawdown": mdd,
            "best_period": best,
            "worst_period": worst,
            "win_rate": win_rate(returns),
            "profit_loss_ratio": profit_loss_ratio(returns),
        },
        "risk_adjusted": {
            "sharpe": sharpe(returns, ppy, rf_annual),
            "sortino": sortino(returns, ppy, rf_annual),
            "calmar": calmar(returns, ppy),
            "omega": omega(returns, 0.0, ppy),
        },
        "distribution": {
            "skewness": skewness(returns),
            "kurtosis": kurtosis(returns),
            "var_95": value_at_risk(returns, 0.05),
            "cvar_95": cvar(returns, 0.05),
        },
        "drawdowns": drawdown_table(returns, top_n=5),
        "monthly_returns": monthly_returns_matrix(returns),
        "annual_returns": annual_returns(returns),
        "rolling_window": rolling_window,
    }

    # 滚动序列（转为 {date: value} 便于渲染 / JSON）
    rs = rolling_sharpe(returns, rolling_window, ppy, rf_annual)
    rv = rolling_vol(returns, rolling_window, ppy)
    rd = rolling_drawdown(returns)
    result["rolling"] = {
        "sharpe": {d.strftime("%Y-%m-%d"): float(v) for d, v in rs.items()},
        "vol": {d.strftime("%Y-%m-%d"): float(v) for d, v in rv.items()},
        "drawdown": {d.strftime("%Y-%m-%d"): float(v) for d, v in rd.items()},
    }

    # 净值曲线（用于 HTML 绘图）
    nav = returns_to_nav(returns)
    result["nav_curve"] = {d.strftime("%Y-%m-%d"): float(v) for d, v in nav.items()}

    if bench_returns is not None and len(bench_returns) > 0:
        result["vs_benchmark"] = benchmark_stats(returns, bench_returns, ppy)
    else:
        result["vs_benchmark"] = None

    return result
