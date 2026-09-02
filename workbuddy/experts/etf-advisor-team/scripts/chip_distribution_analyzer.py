# -*- coding: utf-8 -*-
"""CYQ 完整筹码分布指标体系 (Chip Distribution Analyzer) — v1.17

═══════════════════════════════════════════════════════════════════════════════
为什么需要本脚本？
═══════════════════════════════════════════════════════════════════════════════
faces/筹码面.md 模块 2（筹码面）提出了**四大公理 + 五本源属性 + 五权属
分类 + 四大定律 + 筹码周期五阶段 + 四层指标体系 (L1-L4)**。其中 L1-L4 全部基础
指标必须由本脚本基于 K 线 + 换手率数据按通达信 CYQ（成本因子衰减）算法重建：

  L1 本源指标（5 个）：
    • 平均成本（avg_cost）
    • 获利比例（profit_ratio）= P(成本 < 当前价) 的累计概率
    • 套牢比例（trapped_ratio）= P(成本 > 当前价 × (1+套牢阈值))
    • 筹码集中度（concentration_70 / concentration_90）= 70% / 90% 筹码区间宽度
    • 锁定率（lockup_ratio）= 90 日无变动筹码占比

  L2 周期指标（4 个）：
    • 筹码峰下沿（peak_lower）/ 上沿（peak_upper）
    • 成本带迁移速度（cost_band_drift）
    • 筹码穿透率（penetration_rate）= 当前价穿过的累计筹码占比

  L3 风险指标（3 个）：
    • 抛压弹性（pressure_elasticity）= 套牢盘对短期反弹的承接强度
    • 筹码发散度（dispersion）= 筹码标准差 / 均值
    • 锁定衰减率（lockup_decay）= 锁定率 5 日变动

  L4 主力指标（2 个）：
    • 主力成本中枢估计（dealer_cost_anchor）
    • 主力筹码占比（dealer_chip_share）= 大成交量日筹码贡献率

═══════════════════════════════════════════════════════════════════════════════
通达信 CYQ 衰减算法（业界公认）
═══════════════════════════════════════════════════════════════════════════════
对每根 K 线，假设当日成交筹码均匀分布在 [最低, 最高] 价格区间，按
"换手率衰减 + 三角形/平顶分布" 重建价格-筹码密度直方图：

  对每根历史 bar：
    新增筹码权重 = 当日换手率 × 衰减因子^N
    其中 N = 距离当前的天数

  价格分桶：以 0.5% 为粒度（亦可设 0.1% 增加精度）
  分布形状：等概率三角形（开盘/收盘/最高/最低 加权 0.7/0.15/0.15）

═══════════════════════════════════════════════════════════════════════════════
使用方式
═══════════════════════════════════════════════════════════════════════════════
```bash
# 默认 250 日窗口、衰减因子 0.95（每日衰减 5%）
python scripts/chip_distribution_analyzer.py 600519

# 自定义窗口与衰减
python scripts/chip_distribution_analyzer.py 600519 \
    --window 250 --decay 0.95 --bin-pct 0.005

# 输出 JSON 到 stdout
python ... --json
```

输出文件：FinancialData/{code}_chip_distribution.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 让脚本可以独立运行（同目录导入）
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# 工作区根目录 → FinancialData
WORKSPACE_ROOT = SCRIPT_DIR.parents[2]
FINANCIAL_DATA_DIR = WORKSPACE_ROOT / "FinancialData"
FINANCIAL_DATA_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# K 线数据获取
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_kline_records(code: str, days: int = 250) -> List[Dict[str, Any]]:
    """优先调 stock_quote_scraper；缓存命中时读 FinancialData/{code}_kline.json。"""
    cache_path = FINANCIAL_DATA_DIR / f"{code}_kline.json"
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                recs = data.get("K线数据") or data.get("data") or []
                if recs and len(recs) >= min(days, 60):
                    return recs[-days:]
        except Exception:
            pass
    try:
        import stock_quote_scraper as quote_mod  # type: ignore
        result = quote_mod.fetch_kline(code, days=days)
        if isinstance(result, dict) and "K线数据" in result:
            return result["K线数据"]
        if isinstance(result, list):
            return result
    except Exception as e:
        print(f"⚠ K 线获取失败: {e}", file=sys.stderr)
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# CYQ 核心算法 — 价格-筹码密度直方图重建
# ═══════════════════════════════════════════════════════════════════════════════

def build_chip_histogram(records: List[Dict[str, Any]],
                         decay: float = 0.95,
                         bin_pct: float = 0.005) -> Tuple[List[float], List[float], Dict[str, Any]]:
    """构建当前时刻的筹码分布直方图。

    Args:
        records: K 线记录序列（按时间升序）
        decay: 衰减因子（每日，0.95 表示 5% 每日衰减）
        bin_pct: 价格分桶粒度（0.005 = 0.5%）

    Returns:
        (bin_centers, bin_weights, meta)
    """
    if not records:
        return [], [], {}

    # 1. 计算价格区间（基于全窗口最低-最高，扩展 ±5% 以容纳极值）
    all_high = [r.get("最高", 0) or 0 for r in records]
    all_low = [r.get("最低", 0) or 0 for r in records if (r.get("最低", 0) or 0) > 0]
    if not all_high or not all_low:
        return [], [], {}
    p_min = min(all_low) * 0.95
    p_max = max(all_high) * 1.05
    if p_min <= 0 or p_max <= p_min:
        return [], [], {}

    # 2. 对数空间分桶（按 bin_pct 等比例）
    log_min = math.log(p_min)
    log_max = math.log(p_max)
    n_bins = max(50, int((log_max - log_min) / math.log(1 + bin_pct)))
    n_bins = min(n_bins, 1000)  # 上限保护
    log_step = (log_max - log_min) / n_bins
    bin_centers = [math.exp(log_min + (i + 0.5) * log_step) for i in range(n_bins)]
    bin_lower = [math.exp(log_min + i * log_step) for i in range(n_bins)]
    bin_upper = [math.exp(log_min + (i + 1) * log_step) for i in range(n_bins)]
    weights = [0.0] * n_bins

    n = len(records)
    last_idx = n - 1

    # 3. 衰减权重 + 当日筹码均匀分布到 [low, high]
    for idx, rec in enumerate(records):
        days_back = last_idx - idx
        decay_weight = decay ** days_back
        turnover = rec.get("换手率(%)", 0) or 0
        if turnover <= 0:
            continue
        low = rec.get("最低", 0) or 0
        high = rec.get("最高", 0) or 0
        open_p = rec.get("开盘", 0) or 0
        close_p = rec.get("收盘", 0) or 0
        if low <= 0 or high <= low:
            continue

        # 当日"新增筹码权重" = 换手率（百分数）× 衰减
        new_chips = turnover * decay_weight

        # 三角形/平顶分布：以 (open + close) / 2 为中枢，[low, high] 为外延
        # 加权 60% 三角形（中枢概率最高）+ 40% 平顶
        center_p = (open_p + close_p) / 2 if (open_p > 0 and close_p > 0) else (low + high) / 2
        for i in range(n_bins):
            bl = bin_lower[i]
            bu = bin_upper[i]
            # 桶与 [low, high] 重叠区间
            ov_lo = max(bl, low)
            ov_hi = min(bu, high)
            if ov_hi <= ov_lo:
                continue
            ov_width = ov_hi - ov_lo
            day_width = high - low
            # 平顶分量
            flat_share = ov_width / day_width
            # 三角形分量（以 center_p 为顶）
            tri_share = _triangle_overlap(ov_lo, ov_hi, low, high, center_p) / day_width
            weight_share = 0.4 * flat_share + 0.6 * tri_share
            weights[i] += new_chips * weight_share

    # 4. 归一化
    total = sum(weights)
    if total > 0:
        weights = [w / total for w in weights]

    meta = {
        "n_bins": n_bins,
        "p_min": p_min,
        "p_max": p_max,
        "bin_pct": bin_pct,
        "decay": decay,
        "n_records": n,
    }
    return bin_centers, weights, meta


def _triangle_overlap(ov_lo: float, ov_hi: float, low: float, high: float, peak: float) -> float:
    """计算 [ov_lo, ov_hi] 区间在三角形分布（low/high 为底，peak 为顶）下的累计面积。"""
    if peak <= low:
        peak = (low + high) / 2
    if peak >= high:
        peak = (low + high) / 2
    # 三角形左半（low → peak）：高度 = 2*(x-low)/((high-low)*(peak-low))
    # 三角形右半（peak → high）：高度 = 2*(high-x)/((high-low)*(high-peak))
    base = high - low
    if base <= 0:
        return 0
    area = 0.0

    # 左半重叠
    seg_lo = max(ov_lo, low)
    seg_hi = min(ov_hi, peak)
    if seg_hi > seg_lo and (peak - low) > 0:
        # ∫ 2(x-low) / (base*(peak-low)) dx 从 seg_lo 到 seg_hi
        coef = 2.0 / (base * (peak - low))
        area += coef * (((seg_hi - low) ** 2 - (seg_lo - low) ** 2) / 2)
    # 右半重叠
    seg_lo = max(ov_lo, peak)
    seg_hi = min(ov_hi, high)
    if seg_hi > seg_lo and (high - peak) > 0:
        coef = 2.0 / (base * (high - peak))
        area += coef * (((high - seg_lo) ** 2 - (high - seg_hi) ** 2) / 2)
    return area * base  # 归一化回价格宽度


# ═══════════════════════════════════════════════════════════════════════════════
# L1-L4 指标计算
# ═══════════════════════════════════════════════════════════════════════════════

def compute_indicators(bin_centers: List[float],
                       weights: List[float],
                       current_price: float,
                       records: List[Dict[str, Any]],
                       trap_threshold: float = 0.05) -> Dict[str, Any]:
    """基于直方图与当前价计算 L1-L4 全部指标。"""
    if not bin_centers or not weights:
        return {}

    total_w = sum(weights)
    if total_w <= 0:
        return {}

    # ─── L1 本源指标 ─────────────────────────────────────────────
    avg_cost = sum(c * w for c, w in zip(bin_centers, weights)) / total_w

    profit_w = sum(w for c, w in zip(bin_centers, weights) if c <= current_price)
    profit_ratio = profit_w / total_w

    trap_floor = current_price * (1 + trap_threshold)
    trap_w = sum(w for c, w in zip(bin_centers, weights) if c >= trap_floor)
    trapped_ratio = trap_w / total_w

    concentration_70 = _concentration_width(bin_centers, weights, 0.70)
    concentration_90 = _concentration_width(bin_centers, weights, 0.90)

    lockup_ratio = _compute_lockup_ratio(records, lookback=90)

    # ─── L2 周期指标 ─────────────────────────────────────────────
    peak_lower, peak_upper = _compute_main_peak(bin_centers, weights, threshold=0.5)
    cost_band_drift = _compute_cost_drift(records, window=20)
    penetration_rate = _compute_penetration(bin_centers, weights, current_price)

    # ─── L3 风险指标 ─────────────────────────────────────────────
    dispersion = _compute_dispersion(bin_centers, weights, avg_cost)
    pressure_elasticity = _compute_pressure_elasticity(
        bin_centers, weights, current_price, trap_threshold)
    lockup_decay = _compute_lockup_decay(records)

    # ─── L4 主力指标 ─────────────────────────────────────────────
    dealer_cost_anchor, dealer_chip_share = _compute_dealer_metrics(records, top_pct=0.20)

    # ─── 综合评估 ─────────────────────────────────────────────
    chip_score = _compute_chip_health_score(
        profit_ratio, concentration_90, lockup_ratio, dispersion, pressure_elasticity)

    return {
        "current_price": round(current_price, 4),
        "L1_basic": {
            "avg_cost": round(avg_cost, 4),
            "profit_ratio": round(profit_ratio, 4),
            "trapped_ratio": round(trapped_ratio, 4),
            "trap_threshold_pct": trap_threshold * 100,
            "concentration_70_pct": round(concentration_70 * 100, 2),
            "concentration_90_pct": round(concentration_90 * 100, 2),
            "lockup_ratio_90d": round(lockup_ratio, 4),
        },
        "L2_cycle": {
            "peak_lower": round(peak_lower, 4) if peak_lower else None,
            "peak_upper": round(peak_upper, 4) if peak_upper else None,
            "cost_band_drift_20d_pct": round(cost_band_drift * 100, 2)
            if cost_band_drift is not None else None,
            "penetration_rate": round(penetration_rate, 4),
        },
        "L3_risk": {
            "dispersion": round(dispersion, 4),
            "pressure_elasticity": round(pressure_elasticity, 4),
            "lockup_decay_5d_pct": round(lockup_decay * 100, 2)
            if lockup_decay is not None else None,
        },
        "L4_dealer": {
            "dealer_cost_anchor": round(dealer_cost_anchor, 4)
            if dealer_cost_anchor else None,
            "dealer_chip_share": round(dealer_chip_share, 4),
        },
        "chip_health_score_0_100": chip_score,
    }


def _concentration_width(bin_centers: List[float], weights: List[float],
                          target_pct: float) -> float:
    """target_pct 累计筹码所占的价格区间宽度（相对中位数）。"""
    pairs = sorted(zip(bin_centers, weights), key=lambda x: x[1], reverse=True)
    cum = 0.0
    selected = []
    for c, w in pairs:
        if cum >= target_pct:
            break
        selected.append(c)
        cum += w
    if not selected:
        return 0.0
    p_lo, p_hi = min(selected), max(selected)
    median = (p_lo + p_hi) / 2 if p_hi > 0 else 1
    return (p_hi - p_lo) / median if median > 0 else 0.0


def _compute_lockup_ratio(records: List[Dict[str, Any]], lookback: int = 90) -> float:
    """近 lookback 日累计换手率的倒数趋势 → 锁定率近似。
    锁定率 = 1 - min(1, 近 lookback 日累计换手率 / 100)
    业界经验：累计换手 100% 约等于全部筹码完成一次交换 → 锁定率 0
    """
    if not records:
        return 0.0
    sub = records[-lookback:]
    cum_turnover = sum((r.get("换手率(%)", 0) or 0) for r in sub)
    return max(0.0, 1 - min(1.0, cum_turnover / 100.0))


def _compute_main_peak(bin_centers: List[float], weights: List[float],
                       threshold: float = 0.5) -> Tuple[Optional[float], Optional[float]]:
    """主筹码峰下沿/上沿：以最高峰为中心，扩展到密度 ≥ threshold * 峰值的连续区间。"""
    if not weights:
        return None, None
    max_w = max(weights)
    if max_w <= 0:
        return None, None
    peak_idx = weights.index(max_w)
    cutoff = max_w * threshold
    # 向左扩展
    lo = peak_idx
    while lo > 0 and weights[lo - 1] >= cutoff:
        lo -= 1
    # 向右扩展
    hi = peak_idx
    while hi < len(weights) - 1 and weights[hi + 1] >= cutoff:
        hi += 1
    return bin_centers[lo], bin_centers[hi]


def _compute_cost_drift(records: List[Dict[str, Any]], window: int = 20) -> Optional[float]:
    """成本带迁移速度 = (近 window 日均价 - 前 window 日均价) / 前 window 日均价。"""
    if len(records) < window * 2:
        return None
    recent = records[-window:]
    prior = records[-window * 2:-window]
    avg_recent = sum((r.get("收盘", 0) or 0) for r in recent) / len(recent)
    avg_prior = sum((r.get("收盘", 0) or 0) for r in prior) / len(prior)
    return (avg_recent - avg_prior) / avg_prior if avg_prior > 0 else None


def _compute_penetration(bin_centers: List[float], weights: List[float],
                         current_price: float) -> float:
    """筹码穿透率 = 当前价以下的累计筹码占比。"""
    if not weights:
        return 0.0
    total = sum(weights)
    if total <= 0:
        return 0.0
    below = sum(w for c, w in zip(bin_centers, weights) if c <= current_price)
    return below / total


def _compute_dispersion(bin_centers: List[float], weights: List[float],
                        avg_cost: float) -> float:
    """筹码发散度 = 加权标准差 / 加权均值。"""
    if avg_cost <= 0 or not weights:
        return 0.0
    total = sum(weights)
    if total <= 0:
        return 0.0
    var = sum(w * (c - avg_cost) ** 2 for c, w in zip(bin_centers, weights)) / total
    return math.sqrt(var) / avg_cost


def _compute_pressure_elasticity(bin_centers: List[float], weights: List[float],
                                 current_price: float, trap_threshold: float) -> float:
    """抛压弹性：套牢盘对价格反弹的承接强度 = 上方 5%-15% 区间筹码 / 上方 0%-5% 区间筹码。
    比值 < 1 表示近压力强（反弹易受抑），> 2 表示远压力强（反弹空间足）。
    """
    near_w = sum(w for c, w in zip(bin_centers, weights)
                 if current_price * (1 + trap_threshold) <= c <= current_price * 1.05)
    far_w = sum(w for c, w in zip(bin_centers, weights)
                if current_price * 1.05 < c <= current_price * 1.15)
    if near_w <= 0:
        return 5.0  # 上限
    return min(5.0, far_w / near_w)


def _compute_lockup_decay(records: List[Dict[str, Any]]) -> Optional[float]:
    """锁定衰减率 5 日变动。"""
    if len(records) < 95:
        return None
    cur = _compute_lockup_ratio(records, 90)
    prior = _compute_lockup_ratio(records[:-5], 90)
    return cur - prior


def _compute_dealer_metrics(records: List[Dict[str, Any]],
                             top_pct: float = 0.20) -> Tuple[Optional[float], float]:
    """主力成本中枢 + 主力筹码占比：取 top_pct 成交额最大的 K 线作为主力日，加权均价。"""
    if not records:
        return None, 0.0
    # 按成交额排序
    sorted_recs = sorted(records, key=lambda r: r.get("成交额", 0) or 0, reverse=True)
    n_top = max(1, int(len(sorted_recs) * top_pct))
    top_recs = sorted_recs[:n_top]
    total_amt = sum((r.get("成交额", 0) or 0) for r in records)
    top_amt = sum((r.get("成交额", 0) or 0) for r in top_recs)
    if top_amt <= 0:
        return None, 0.0
    weighted_avg = sum(((r.get("开盘", 0) + r.get("收盘", 0)) / 2) * (r.get("成交额", 0) or 0)
                       for r in top_recs) / top_amt
    share = top_amt / total_amt if total_amt > 0 else 0.0
    return weighted_avg, share


def _compute_chip_health_score(profit_ratio: float, concentration: float,
                                lockup_ratio: float, dispersion: float,
                                pressure_elasticity: float) -> int:
    """综合健康度 0-100：获利比例(25) + 集中度(25) + 锁定率(20) + 发散度(15) + 抛压弹性(15)。"""
    s1 = min(25, profit_ratio * 25 / 0.7)
    s2 = max(0, 25 - concentration * 100)
    s3 = lockup_ratio * 20
    s4 = max(0, 15 - dispersion * 100)
    s5 = min(15, pressure_elasticity * 7.5)
    return int(round(s1 + s2 + s3 + s4 + s5))


# ═══════════════════════════════════════════════════════════════════════════════
# 阶段判定（供 phase_triangle_detector 复用）
# ═══════════════════════════════════════════════════════════════════════════════

def classify_chip_phase(indicators: Dict[str, Any]) -> Dict[str, Any]:
    """筹码周期五阶段：分散→集中→锁定→发散→分散。"""
    if not indicators:
        return {"phase": "未知", "confidence": 0}

    L1 = indicators.get("L1_basic", {})
    L2 = indicators.get("L2_cycle", {})

    concentration = L1.get("concentration_90_pct", 100) / 100
    lockup = L1.get("lockup_ratio_90d", 0)
    drift = L2.get("cost_band_drift_20d_pct", 0) or 0
    profit_ratio = L1.get("profit_ratio", 0)

    # 决策树
    if concentration > 0.30 and drift < -2:
        phase = "分散下行"
        conf = 75
    elif concentration > 0.25 and drift > 2 and lockup < 0.3:
        phase = "集中初期"
        conf = 70
    elif concentration <= 0.15 and lockup >= 0.5:
        phase = "锁定主升"
        conf = 85
    elif concentration <= 0.20 and 0.3 <= lockup < 0.5 and drift > 0:
        phase = "集中加速"
        conf = 80
    elif concentration > 0.20 and lockup < 0.3 and drift < 0 and profit_ratio < 0.4:
        phase = "发散转折"
        conf = 75
    else:
        phase = "震荡过渡"
        conf = 60

    return {
        "phase": phase,
        "confidence": conf,
        "判定依据": {
            "集中度（90%）": f"{concentration*100:.1f}%",
            "锁定率": f"{lockup*100:.1f}%",
            "成本带 20 日迁移": f"{drift:.2f}%",
            "获利比例": f"{profit_ratio*100:.1f}%",
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════════════════════

def analyze(code: str, window: int = 250, decay: float = 0.95,
            bin_pct: float = 0.005, trap_threshold: float = 0.05) -> Dict[str, Any]:
    """完整分析流程。"""
    records = fetch_kline_records(code, days=window)
    if not records or len(records) < 30:
        return {"code": code, "error": f"K 线数据不足（{len(records)} 条）"}

    bin_centers, weights, meta = build_chip_histogram(records, decay=decay, bin_pct=bin_pct)
    if not bin_centers:
        return {"code": code, "error": "筹码直方图构建失败"}

    current_price = records[-1].get("收盘", 0)
    if current_price <= 0:
        return {"code": code, "error": "当前价无效"}

    indicators = compute_indicators(bin_centers, weights, current_price, records,
                                    trap_threshold=trap_threshold)
    phase = classify_chip_phase(indicators)

    # 输出 top 5 筹码峰
    peak_pairs = sorted(zip(bin_centers, weights), key=lambda x: x[1], reverse=True)[:5]
    top_peaks = [{"price": round(c, 4), "weight_pct": round(w * 100, 2)} for c, w in peak_pairs]

    return {
        "code": code,
        "as_of": records[-1].get("日期", ""),
        "window_days": len(records),
        "decay": decay,
        "bin_pct": bin_pct,
        "indicators": indicators,
        "chip_phase": phase,
        "top5_chip_peaks": top_peaks,
        "histogram_meta": meta,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CYQ 完整筹码分布指标体系 (v1.17 — faces/筹码面.md 模块 2 配套)")
    parser.add_argument("code", help="股票代码（6 位）")
    parser.add_argument("--window", type=int, default=250, help="K 线窗口（默认 250）")
    parser.add_argument("--decay", type=float, default=0.95, help="衰减因子（默认 0.95）")
    parser.add_argument("--bin-pct", type=float, default=0.005, help="价格分桶粒度（默认 0.5%%）")
    parser.add_argument("--trap-threshold", type=float, default=0.05,
                        help="套牢阈值（默认 5%%）")
    parser.add_argument("--json", action="store_true", help="JSON 输出到 stdout")
    parser.add_argument("--output", help="自定义输出路径")
    args = parser.parse_args()

    result = analyze(args.code, window=args.window, decay=args.decay,
                     bin_pct=args.bin_pct, trap_threshold=args.trap_threshold)

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = FINANCIAL_DATA_DIR / f"{args.code}_chip_distribution.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if "error" in result:
            print(f"[chip_distribution_analyzer] {args.code} 失败: {result['error']}")
            return 1
        ind = result.get("indicators", {})
        L1 = ind.get("L1_basic", {})
        phase = result.get("chip_phase", {})
        print(f"[chip_distribution_analyzer] {args.code} 完成 → {out_path}")
        print(f"  当前价: {result.get('indicators', {}).get('current_price')}")
        print(f"  平均成本: {L1.get('avg_cost')} | 获利比例: {L1.get('profit_ratio')}")
        print(f"  集中度(90%): {L1.get('concentration_90_pct')}% | 锁定率: {L1.get('lockup_ratio_90d')}")
        print(f"  筹码周期阶段: {phase.get('phase')} (置信 {phase.get('confidence')}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
