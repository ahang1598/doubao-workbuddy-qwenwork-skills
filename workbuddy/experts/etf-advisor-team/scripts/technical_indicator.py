#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
技术分析指标计算脚本 — 本地计算 + 第三方API交叉验证

功能：
  基于K线数据（JSON输入）计算常用技术指标，输出结构化JSON/Markdown。
  核心指标本地计算，同时支持 zhituapi / waizaowang 第三方API交叉验证。

支持指标：
  1. 均线系统（MA5/10/20/60/120/250 + 多空排列判断）
  2. MACD（DIF/DEA/MACD柱 + 金叉死叉信号）
  3. RSI（6/12/24日 + 超买超卖判断）— 本地计算
  4. KDJ（K/D/J值 + 金叉死叉信号）
  5. 布林带（上轨/中轨/下轨/带宽 + 突破信号）
  6. CCI（顺势指标，超买超卖+趋势判断）— v2新增
  7. ATR（真实波幅，波动率度量）— v2新增
  8. WR（威廉指标，超买超卖）— v2新增
  9. 支撑位/压力位（成交量加权密集区+前期显著高低点+智能整数关口+均线+Fibonacci）— v2增强
  10. 综合技术面评分与信号汇总（纳入CCI/ATR/WR）
  11. 第三方API交叉验证（zhituapi: MACD/KDJ/MA/BOLL）— v2新增

数据源：stock_quote_scraper.py 或 realtime_quote_enhanced.py 的K线输出

用法：
  # 从K线JSON文件计算全部指标
  python technical_indicator.py --kline-file FinancialData/600519_kline.json

  # 从stock_quote_scraper实时获取K线并计算
  python technical_indicator.py --code 600519

  # 仅计算特定指标
  python technical_indicator.py --code 600519 --indicators ma,macd,rsi

  # 启用第三方API交叉验证
  python technical_indicator.py --code 600519 --cross-validate

  # JSON输出
  python technical_indicator.py --code 600519 --json

  # 输出到文件
  python technical_indicator.py --code 600519 --output FinancialData/600519_technical.md

输出：JSON 或 Markdown 格式
"""

import argparse
import json
import math
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# ---------------------------------------------------------------------------
#  K线数据获取（可选：从同目录的 stock_quote_scraper 获取）
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def fetch_kline_data(code: str, days: int = 250) -> List[Dict]:
    """从 stock_quote_scraper 获取K线数据"""
    try:
        import stock_quote_scraper as quote_mod
        kline = quote_mod.fetch_kline(code, days=days)
        if isinstance(kline, dict):
            # stock_quote_scraper.fetch_kline 返回 "K线数据" 键而非 "data"
            return kline.get("K线数据", kline.get("data", []))
        return kline
    except ImportError:
        print("⚠ stock_quote_scraper 不可用，请使用 --kline-file 提供K线数据", file=sys.stderr)
        return []


def parse_kline_json(filepath: str) -> List[Dict]:
    """从JSON文件读取K线数据"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("data", data.get("klines", []))
    return data


# ---------------------------------------------------------------------------
#  辅助函数
# ---------------------------------------------------------------------------

def _safe_float(v, default=0.0):
    if v is None or v == "" or v == "-":
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _extract_prices(klines: List[Dict]) -> Tuple[List[float], List[float], List[float], List[float], List[float]]:
    """提取收盘价/最高价/最低价/开盘价/成交量序列（按时间正序）"""
    closes, highs, lows, opens, volumes = [], [], [], [], []
    for k in klines:
        if isinstance(k, dict):
            closes.append(_safe_float(k.get("close", k.get("收盘", 0))))
            highs.append(_safe_float(k.get("high", k.get("最高", 0))))
            lows.append(_safe_float(k.get("low", k.get("最低", 0))))
            opens.append(_safe_float(k.get("open", k.get("开盘", 0))))
            volumes.append(_safe_float(k.get("volume", k.get("成交量", k.get("成交量(手)", 0)))))
        elif isinstance(k, (list, tuple)) and len(k) >= 5:
            opens.append(_safe_float(k[1]))
            closes.append(_safe_float(k[2]))
            highs.append(_safe_float(k[3]))
            lows.append(_safe_float(k[4]))
            volumes.append(_safe_float(k[5]) if len(k) > 5 else 0)
    return closes, highs, lows, opens, volumes


# ---------------------------------------------------------------------------
#  1. 均线系统 (MA)
# ---------------------------------------------------------------------------

def calc_ma(closes: List[float], periods: List[int] = None) -> Dict[str, Any]:
    """计算多周期均线 + 多空排列判断"""
    if periods is None:
        periods = [5, 10, 20, 60, 120, 250]

    result = {"ma_values": {}, "arrangement": "无法判断", "current_vs_ma": {}}
    if not closes:
        return result

    current = closes[-1]

    for p in periods:
        key = f"MA{p}"
        if len(closes) >= p:
            ma_val = sum(closes[-p:]) / p
            result["ma_values"][key] = round(ma_val, 2)
            diff_pct = (current - ma_val) / ma_val * 100 if ma_val else 0
            result["current_vs_ma"][key] = {
                "value": round(ma_val, 2),
                "diff_pct": round(diff_pct, 2),
                "position": "上方" if current > ma_val else "下方",
            }
        else:
            result["ma_values"][key] = None

    # 多空排列判断
    valid_mas = [(p, result["ma_values"][f"MA{p}"]) for p in periods if result["ma_values"].get(f"MA{p}") is not None]
    if len(valid_mas) >= 3:
        vals = [v for _, v in valid_mas]
        if all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1)):
            result["arrangement"] = "多头排列（强势）"
        elif all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1)):
            result["arrangement"] = "空头排列（弱势）"
        else:
            above_count = sum(1 for _, v in valid_mas if current > v)
            if above_count >= len(valid_mas) * 0.7:
                result["arrangement"] = "偏多排列"
            elif above_count <= len(valid_mas) * 0.3:
                result["arrangement"] = "偏空排列"
            else:
                result["arrangement"] = "缠绕/震荡"

    return result


# ---------------------------------------------------------------------------
#  2. MACD
# ---------------------------------------------------------------------------

def calc_ema(data: List[float], period: int) -> List[float]:
    """指数移动平均"""
    if not data:
        return []
    ema = [data[0]]
    k = 2.0 / (period + 1)
    for i in range(1, len(data)):
        ema.append(data[i] * k + ema[-1] * (1 - k))
    return ema


def calc_macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, Any]:
    """计算MACD（DIF/DEA/MACD柱）+ 金叉死叉信号"""
    result = {"dif": None, "dea": None, "macd_bar": None, "signal": "无信号", "histogram_trend": "无法判断"}
    if len(closes) < slow + signal:
        return result

    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    dif = [ema_fast[i] - ema_slow[i] for i in range(len(closes))]
    dea = calc_ema(dif, signal)
    macd_bar = [(dif[i] - dea[i]) * 2 for i in range(len(closes))]

    result["dif"] = round(dif[-1], 4)
    result["dea"] = round(dea[-1], 4)
    result["macd_bar"] = round(macd_bar[-1], 4)

    # 金叉死叉信号（最近5日）
    for i in range(len(dif) - 1, max(len(dif) - 6, 0), -1):
        if i < 1:
            break
        if dif[i] > dea[i] and dif[i - 1] <= dea[i - 1]:
            result["signal"] = f"金叉（{len(dif) - i}日前）"
            break
        if dif[i] < dea[i] and dif[i - 1] >= dea[i - 1]:
            result["signal"] = f"死叉（{len(dif) - i}日前）"
            break

    # MACD柱趋势
    if len(macd_bar) >= 3:
        recent = macd_bar[-3:]
        if recent[-1] > recent[-2] > recent[-3]:
            result["histogram_trend"] = "红柱放大" if recent[-1] > 0 else "绿柱缩小"
        elif recent[-1] < recent[-2] < recent[-3]:
            result["histogram_trend"] = "红柱缩小" if recent[-1] > 0 else "绿柱放大"
        else:
            result["histogram_trend"] = "震荡"

    # 零轴位置
    if dif[-1] > 0 and dea[-1] > 0:
        result["axis_position"] = "零轴上方（多头区域）"
    elif dif[-1] < 0 and dea[-1] < 0:
        result["axis_position"] = "零轴下方（空头区域）"
    else:
        result["axis_position"] = "零轴附近（转换区域）"

    return result


# ---------------------------------------------------------------------------
#  3. RSI
# ---------------------------------------------------------------------------

def calc_rsi(closes: List[float], periods: List[int] = None) -> Dict[str, Any]:
    """计算RSI + 超买超卖判断"""
    if periods is None:
        periods = [6, 12, 24]

    result = {"rsi_values": {}, "signal": "中性"}
    if len(closes) < max(periods) + 1:
        return result

    for p in periods:
        gains, losses = [], []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))

        if len(gains) < p:
            continue

        avg_gain = sum(gains[-p:]) / p
        avg_loss = sum(losses[-p:]) / p

        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        result["rsi_values"][f"RSI{p}"] = round(rsi, 2)

    # 综合判断
    rsi6 = result["rsi_values"].get("RSI6", 50)
    if rsi6 >= 80:
        result["signal"] = "超买（RSI6≥80）"
    elif rsi6 >= 70:
        result["signal"] = "偏强/接近超买"
    elif rsi6 <= 20:
        result["signal"] = "超卖（RSI6≤20）"
    elif rsi6 <= 30:
        result["signal"] = "偏弱/接近超卖"
    else:
        result["signal"] = "中性"

    return result


# ---------------------------------------------------------------------------
#  4. KDJ
# ---------------------------------------------------------------------------

def calc_kdj(highs: List[float], lows: List[float], closes: List[float],
             n: int = 9, m1: int = 3, m2: int = 3) -> Dict[str, Any]:
    """计算KDJ + 金叉死叉信号"""
    result = {"k": None, "d": None, "j": None, "signal": "无信号"}
    if len(closes) < n:
        return result

    k_val, d_val = 50.0, 50.0
    k_list, d_list, j_list = [], [], []

    for i in range(n - 1, len(closes)):
        period_high = max(highs[i - n + 1:i + 1])
        period_low = min(lows[i - n + 1:i + 1])
        if period_high == period_low:
            rsv = 50.0
        else:
            rsv = (closes[i] - period_low) / (period_high - period_low) * 100

        k_val = (2 * k_val + rsv) / m1
        d_val = (2 * d_val + k_val) / m2
        j_val = 3 * k_val - 2 * d_val

        k_list.append(k_val)
        d_list.append(d_val)
        j_list.append(j_val)

    if k_list:
        result["k"] = round(k_list[-1], 2)
        result["d"] = round(d_list[-1], 2)
        result["j"] = round(j_list[-1], 2)

        # 金叉死叉
        if len(k_list) >= 2:
            if k_list[-1] > d_list[-1] and k_list[-2] <= d_list[-2]:
                result["signal"] = "金叉"
            elif k_list[-1] < d_list[-1] and k_list[-2] >= d_list[-2]:
                result["signal"] = "死叉"

        # 超买超卖
        if j_list[-1] > 100:
            result["overbought"] = True
            result["signal"] += "（J>100超买）" if result["signal"] != "无信号" else "J>100超买"
        elif j_list[-1] < 0:
            result["oversold"] = True
            result["signal"] += "（J<0超卖）" if result["signal"] != "无信号" else "J<0超卖"

    return result


# ---------------------------------------------------------------------------
#  5. 布林带 (Bollinger Bands)
# ---------------------------------------------------------------------------

def calc_bollinger(closes: List[float], period: int = 20, num_std: float = 2.0) -> Dict[str, Any]:
    """计算布林带 + 突破/缩口信号"""
    result = {"upper": None, "middle": None, "lower": None, "bandwidth": None, "signal": "通道内运行"}
    if len(closes) < period:
        return result

    recent = closes[-period:]
    middle = sum(recent) / period
    variance = sum((x - middle) ** 2 for x in recent) / period
    std = math.sqrt(variance)

    upper = middle + num_std * std
    lower = middle - num_std * std
    bandwidth = (upper - lower) / middle * 100 if middle else 0

    result["upper"] = round(upper, 2)
    result["middle"] = round(middle, 2)
    result["lower"] = round(lower, 2)
    result["bandwidth"] = round(bandwidth, 2)

    current = closes[-1]
    if current >= upper:
        result["signal"] = "触及/突破上轨（超强/超买）"
    elif current <= lower:
        result["signal"] = "触及/跌破下轨（超弱/超卖）"
    elif current > middle:
        result["signal"] = "中轨上方运行"
    else:
        result["signal"] = "中轨下方运行"

    # 缩口/扩口判断
    if len(closes) >= period * 2:
        prev_recent = closes[-period * 2:-period]
        prev_mid = sum(prev_recent) / period
        prev_var = sum((x - prev_mid) ** 2 for x in prev_recent) / period
        prev_std = math.sqrt(prev_var)
        prev_bw = (2 * num_std * prev_std) / prev_mid * 100 if prev_mid else 0
        if bandwidth < prev_bw * 0.7:
            result["mouth"] = "缩口（变盘信号）"
        elif bandwidth > prev_bw * 1.3:
            result["mouth"] = "扩口（趋势加速）"
        else:
            result["mouth"] = "正常"

    return result


# ---------------------------------------------------------------------------
#  6. CCI（顺势指标）— v2新增
# ---------------------------------------------------------------------------

def calc_cci(highs: List[float], lows: List[float], closes: List[float],
             period: int = 14) -> Dict[str, Any]:
    """计算CCI（Commodity Channel Index）+ 超买超卖/趋势判断"""
    result = {"cci": None, "signal": "无信号", "trend": "无法判断"}
    if len(closes) < period:
        return result

    # CCI = (TP - SMA(TP, N)) / (0.015 * MeanDeviation)
    # TP = (High + Low + Close) / 3
    tp_list = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(len(closes))]

    recent_tp = tp_list[-period:]
    sma_tp = sum(recent_tp) / period
    mean_dev = sum(abs(tp - sma_tp) for tp in recent_tp) / period

    if mean_dev == 0:
        result["cci"] = 0.0
    else:
        result["cci"] = round((tp_list[-1] - sma_tp) / (0.015 * mean_dev), 2)

    cci_val = result["cci"]

    # 超买超卖判断
    if cci_val >= 200:
        result["signal"] = "极度超买（CCI≥200）"
    elif cci_val >= 100:
        result["signal"] = "超买（CCI≥100）"
    elif cci_val <= -200:
        result["signal"] = "极度超卖（CCI≤-200）"
    elif cci_val <= -100:
        result["signal"] = "超卖（CCI≤-100）"
    else:
        result["signal"] = "中性区间（-100~+100）"

    # 趋势判断（基于CCI方向）
    if len(closes) >= period + 5:
        prev_tp = tp_list[-(period + 5):-5]
        prev_sma = sum(prev_tp) / period
        prev_md = sum(abs(tp - prev_sma) for tp in prev_tp) / period
        if prev_md > 0:
            prev_cci = (tp_list[-6] - prev_sma) / (0.015 * prev_md)
            if cci_val > prev_cci and cci_val > 0:
                result["trend"] = "多头加速"
            elif cci_val < prev_cci and cci_val < 0:
                result["trend"] = "空头加速"
            elif cci_val > prev_cci:
                result["trend"] = "回升"
            else:
                result["trend"] = "回落"

    return result


# ---------------------------------------------------------------------------
#  7. ATR（真实波幅）— v2新增
# ---------------------------------------------------------------------------

def calc_atr(highs: List[float], lows: List[float], closes: List[float],
             period: int = 14) -> Dict[str, Any]:
    """计算ATR（Average True Range）+ 波动率评估"""
    result = {"atr": None, "atr_pct": None, "volatility": "无法判断"}
    if len(closes) < period + 1:
        return result

    # TR = max(H-L, |H-Cprev|, |L-Cprev|)
    tr_list = []
    for i in range(1, len(closes)):
        h_l = highs[i] - lows[i]
        h_cp = abs(highs[i] - closes[i - 1])
        l_cp = abs(lows[i] - closes[i - 1])
        tr_list.append(max(h_l, h_cp, l_cp))

    if len(tr_list) < period:
        return result

    # 简单平均ATR
    atr = sum(tr_list[-period:]) / period
    result["atr"] = round(atr, 4)

    # ATR占比（波动率百分比）
    current = closes[-1]
    if current > 0:
        result["atr_pct"] = round(atr / current * 100, 2)

    # 波动率评估
    atr_pct = result["atr_pct"] or 0
    if atr_pct >= 5:
        result["volatility"] = "极高波动（ATR%≥5%）"
    elif atr_pct >= 3:
        result["volatility"] = "高波动（ATR%≥3%）"
    elif atr_pct >= 1.5:
        result["volatility"] = "中等波动"
    else:
        result["volatility"] = "低波动（ATR%<1.5%）"

    # 波动率趋势（近5日ATR vs 近14日ATR）
    if len(tr_list) >= period:
        atr_short = sum(tr_list[-5:]) / 5 if len(tr_list) >= 5 else atr
        if atr_short > atr * 1.2:
            result["vol_trend"] = "波动放大"
        elif atr_short < atr * 0.8:
            result["vol_trend"] = "波动收敛"
        else:
            result["vol_trend"] = "波动平稳"

    return result


# ---------------------------------------------------------------------------
#  8. WR（威廉指标）— v2新增
# ---------------------------------------------------------------------------

def calc_williams_r(highs: List[float], lows: List[float], closes: List[float],
                    periods: List[int] = None) -> Dict[str, Any]:
    """计算Williams %R + 超买超卖判断"""
    if periods is None:
        periods = [6, 10, 14]

    result = {"wr_values": {}, "signal": "中性"}
    if len(closes) < max(periods):
        return result

    for p in periods:
        if len(closes) < p:
            continue
        hh = max(highs[-p:])
        ll = min(lows[-p:])
        if hh == ll:
            wr = -50.0
        else:
            wr = (hh - closes[-1]) / (hh - ll) * -100  # WR范围: -100 ~ 0
        result["wr_values"][f"WR{p}"] = round(wr, 2)

    # 综合判断（基于WR14）
    wr14 = result["wr_values"].get("WR14", -50)
    if wr14 >= -20:
        result["signal"] = "超买（WR14≥-20）"
    elif wr14 >= -30:
        result["signal"] = "偏强/接近超买"
    elif wr14 <= -80:
        result["signal"] = "超卖（WR14≤-80）"
    elif wr14 <= -70:
        result["signal"] = "偏弱/接近超卖"
    else:
        result["signal"] = "中性"

    return result


# ---------------------------------------------------------------------------
#  9. 支撑位/压力位（v2增强版）
# ---------------------------------------------------------------------------

def _find_pivot_points(prices_high: List[float], prices_low: List[float],
                       window: int = 5) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
    """检测显著的局部高点(pivot high)和低点(pivot low)
    返回 (pivot_highs, pivot_lows)，每项为 (index, price) 列表"""
    pivot_highs, pivot_lows = [], []
    n = len(prices_high)
    for i in range(window, n - window):
        # pivot high: 当前最高价是前后 window 根K线中最高的
        if prices_high[i] == max(prices_high[i - window:i + window + 1]):
            pivot_highs.append((i, prices_high[i]))
        # pivot low: 当前最低价是前后 window 根K线中最低的
        if prices_low[i] == min(prices_low[i - window:i + window + 1]):
            pivot_lows.append((i, prices_low[i]))
    return pivot_highs, pivot_lows


def _calc_volume_profile(closes: List[float], volumes: List[float], highs: List[float],
                         lows: List[float], bins: int = 30) -> List[Dict]:
    """计算成交量分布（Volume Profile），返回按成交量排序的价格区间
    用于识别密集成交区作为支撑/压力位"""
    if not closes or not volumes or len(closes) != len(volumes):
        return []

    price_min = min(lows) if lows else min(closes)
    price_max = max(highs) if highs else max(closes)
    if price_max <= price_min:
        return []

    bin_size = (price_max - price_min) / bins
    if bin_size <= 0:
        return []

    # 将每根K线的成交量按价格区间分配
    vol_bins = [0.0] * bins
    for i in range(len(closes)):
        # K线覆盖的价格范围
        k_low = lows[i] if i < len(lows) else closes[i]
        k_high = highs[i] if i < len(highs) else closes[i]
        vol = volumes[i] if i < len(volumes) else 0

        # 将成交量均匀分配到覆盖的bins
        for b in range(bins):
            bin_low = price_min + b * bin_size
            bin_high = bin_low + bin_size
            # 计算K线与bin的重叠
            overlap_low = max(k_low, bin_low)
            overlap_high = min(k_high, bin_high)
            if overlap_high > overlap_low:
                k_range = k_high - k_low if k_high > k_low else 1
                ratio = (overlap_high - overlap_low) / k_range
                vol_bins[b] += vol * ratio

    # 构建结果：每个bin的中心价格和成交量
    profile = []
    for b in range(bins):
        center = price_min + (b + 0.5) * bin_size
        profile.append({"price": round(center, 2), "volume": vol_bins[b]})

    # 按成交量降序排列
    profile.sort(key=lambda x: -x["volume"])
    return profile


def _smart_round_levels(current: float) -> List[float]:
    """根据价格量级智能生成整数关口
    - 价格<10: 步长1
    - 10~50: 步长5
    - 50~200: 步长10
    - 200~1000: 步长50
    - >1000: 步长100
    """
    if current <= 0:
        return []

    if current < 10:
        step = 1
    elif current < 50:
        step = 5
    elif current < 200:
        step = 10
    elif current < 1000:
        step = 50
    else:
        step = 100

    base = int(current / step) * step
    levels = []
    for mult in range(-3, 5):
        lv = base + mult * step
        if lv > 0:
            levels.append(float(lv))
    return levels


def calc_support_resistance(closes: List[float], highs: List[float], lows: List[float],
                            volumes: List[float] = None,
                            ma_result: Dict = None) -> Dict[str, Any]:
    """v2增强版：成交量加权密集区 + 显著pivot点 + 智能整数关口 + Fibonacci + 均线"""
    result = {"supports": [], "resistances": [], "fibonacci": [], "current": None,
              "volume_profile_top3": []}
    if not closes:
        return result

    current = closes[-1]
    result["current"] = round(current, 2)

    candidates_support = []
    candidates_resistance = []

    # ── (a) 显著Pivot高低点（替代简单的窗口最值）──
    lookback_120 = min(120, len(highs))
    if lookback_120 >= 15:
        ph, pl = _find_pivot_points(
            highs[-lookback_120:], lows[-lookback_120:], window=5)
        # 取最近的几个显著高低点
        for _idx, price in sorted(pl, key=lambda x: -x[0])[:5]:  # 最近5个低点
            if price < current and abs(current - price) / current < 0.15:
                candidates_support.append({"price": round(price, 2),
                                           "source": "前期显著低点(pivot)",
                                           "weight": 3})
        for _idx, price in sorted(ph, key=lambda x: -x[0])[:5]:  # 最近5个高点
            if price > current and abs(price - current) / current < 0.15:
                candidates_resistance.append({"price": round(price, 2),
                                              "source": "前期显著高点(pivot)",
                                              "weight": 3})

    # 保留窗口最值作为补充
    for window in [10, 20, 60]:
        if len(lows) >= window:
            low_val = min(lows[-window:])
            if low_val < current:
                candidates_support.append({"price": round(low_val, 2),
                                           "source": f"近{window}日最低点", "weight": 2})
        if len(highs) >= window:
            high_val = max(highs[-window:])
            if high_val > current:
                candidates_resistance.append({"price": round(high_val, 2),
                                              "source": f"近{window}日最高点", "weight": 2})

    # ── (b) 成交量密集区（Volume Profile）──
    if volumes and len(volumes) == len(closes):
        # 使用近60日数据计算成交量分布
        vp_lookback = min(60, len(closes))
        vp = _calc_volume_profile(
            closes[-vp_lookback:], volumes[-vp_lookback:],
            highs[-vp_lookback:], lows[-vp_lookback:], bins=30)
        if vp:
            # 记录Top3密集成交区
            max_vol = max((v["volume"] for v in vp), default=1) or 1
            result["volume_profile_top3"] = [
                {"price": p["price"], "rel_volume": round(p["volume"] / max_vol * 100, 1)}
                for p in vp[:3]
            ]
            # 取成交量最大的5个价格区间作为支撑/压力候选
            for p in vp[:5]:
                vp_price = p["price"]
                if vp_price < current and abs(current - vp_price) / current < 0.12:
                    candidates_support.append({"price": vp_price,
                                               "source": "密集成交区(量价)", "weight": 4})
                elif vp_price > current and abs(vp_price - current) / current < 0.12:
                    candidates_resistance.append({"price": vp_price,
                                                  "source": "密集成交区(量价)", "weight": 4})

    # ── (c) 智能整数关口（按价格量级自适应步长）──
    round_levels = _smart_round_levels(current)
    for level in round_levels:
        if level < current and abs(current - level) / current < 0.10:
            candidates_support.append({"price": level, "source": "整数关口", "weight": 1})
        elif level > current and abs(level - current) / current < 0.10:
            candidates_resistance.append({"price": level, "source": "整数关口", "weight": 1})

    # ── (d) 黄金分割位（Fibonacci 0.382/0.5/0.618 回撤位）──
    fib_ratios = [0.382, 0.5, 0.618]
    fib_levels = []
    lookback = min(60, len(highs))
    if lookback >= 5:
        recent_high = max(highs[-lookback:])
        recent_low = min(lows[-lookback:])
        price_range = recent_high - recent_low

        if price_range > 0 and recent_high > recent_low:
            for ratio in fib_ratios:
                retrace_level = round(recent_high - price_range * ratio, 2)
                fib_levels.append({
                    "ratio": ratio, "price": retrace_level,
                    "source": f"黄金分割{ratio}",
                })
                if retrace_level < current and abs(current - retrace_level) / current < 0.15:
                    candidates_support.append({"price": retrace_level,
                                               "source": f"黄金分割{ratio}回撤位", "weight": 2})
                elif retrace_level > current and abs(retrace_level - current) / current < 0.15:
                    candidates_resistance.append({"price": retrace_level,
                                                  "source": f"黄金分割{ratio}回撤位", "weight": 2})

            result["fibonacci"] = {
                "swing_high": round(recent_high, 2),
                "swing_low": round(recent_low, 2),
                "levels": fib_levels,
            }

    # ── (e) 均线支撑/压力 ──
    if ma_result and ma_result.get("ma_values"):
        for key, val in ma_result["ma_values"].items():
            if val is None:
                continue
            if val < current and abs(current - val) / current < 0.08:
                candidates_support.append({"price": val, "source": f"{key}均线", "weight": 2})
            elif val > current and abs(val - current) / current < 0.08:
                candidates_resistance.append({"price": val, "source": f"{key}均线", "weight": 2})

    # ── 去重排序：按weight降序优先，同weight按价格接近当前价排序，取Top5 ──
    seen_s = set()
    for s in sorted(candidates_support,
                    key=lambda x: (-x.get("weight", 1), -x["price"])):
        p = round(s["price"], 2)
        if p not in seen_s:
            seen_s.add(p)
            entry = {"price": s["price"], "source": s["source"]}
            result["supports"].append(entry)
        if len(result["supports"]) >= 5:
            break

    seen_r = set()
    for r in sorted(candidates_resistance,
                    key=lambda x: (-x.get("weight", 1), x["price"])):
        p = round(r["price"], 2)
        if p not in seen_r:
            seen_r.add(p)
            entry = {"price": r["price"], "source": r["source"]}
            result["resistances"].append(entry)
        if len(result["resistances"]) >= 5:
            break

    return result


# ---------------------------------------------------------------------------
#  10. 综合技术面评分（v2: 纳入CCI/ATR/WR）
# ---------------------------------------------------------------------------

def calc_composite_score(ma_res: Dict, macd_res: Dict, rsi_res: Dict,
                         kdj_res: Dict, boll_res: Dict, sr_res: Dict,
                         cci_res: Dict = None, atr_res: Dict = None,
                         wr_res: Dict = None) -> Dict[str, Any]:
    """综合技术面评分（0-100），v2纳入CCI/ATR/WR"""
    score = 50  # 基准中性分
    signals = []

    # MA得分（±15）
    arr = ma_res.get("arrangement", "")
    if "多头排列" in arr:
        score += 15
        signals.append("▲ 均线多头排列")
    elif "偏多" in arr:
        score += 8
        signals.append("▲ 均线偏多")
    elif "空头排列" in arr:
        score -= 15
        signals.append("▼ 均线空头排列")
    elif "偏空" in arr:
        score -= 8
        signals.append("▼ 均线偏空")
    else:
        signals.append("► 均线缠绕")

    # MACD得分（±15）
    macd_sig = macd_res.get("signal", "")
    if "金叉" in macd_sig:
        score += 12
        signals.append(f"▲ MACD{macd_sig}")
    elif "死叉" in macd_sig:
        score -= 12
        signals.append(f"▼ MACD{macd_sig}")
    axis = macd_res.get("axis_position", "")
    if "多头" in axis:
        score += 3
    elif "空头" in axis:
        score -= 3

    # RSI得分（±10）
    rsi_sig = rsi_res.get("signal", "")
    if "超买" in rsi_sig:
        score -= 10
        signals.append(f"▼ RSI{rsi_sig}")
    elif "超卖" in rsi_sig:
        score += 10
        signals.append(f"▲ RSI{rsi_sig}")
    elif "偏强" in rsi_sig:
        score += 3
    elif "偏弱" in rsi_sig:
        score -= 3

    # KDJ得分（±10）
    kdj_sig = kdj_res.get("signal", "")
    if "金叉" in kdj_sig:
        score += 8
        signals.append(f"▲ KDJ{kdj_sig}")
    elif "死叉" in kdj_sig:
        score -= 8
        signals.append(f"▼ KDJ{kdj_sig}")
    if kdj_res.get("overbought"):
        score -= 5
    if kdj_res.get("oversold"):
        score += 5

    # 布林带得分（±5）
    boll_sig = boll_res.get("signal", "")
    if "上轨" in boll_sig:
        score -= 3
        signals.append("► 触及布林上轨")
    elif "下轨" in boll_sig:
        score += 3
        signals.append("► 触及布林下轨")

    # CCI得分（±8）— v2新增
    if cci_res:
        cci_sig = cci_res.get("signal", "")
        if "极度超买" in cci_sig:
            score -= 8
            signals.append(f"▼ CCI{cci_sig}")
        elif "超买" in cci_sig:
            score -= 4
            signals.append(f"► CCI{cci_sig}")
        elif "极度超卖" in cci_sig:
            score += 8
            signals.append(f"▲ CCI{cci_sig}")
        elif "超卖" in cci_sig:
            score += 4
            signals.append(f"▲ CCI{cci_sig}")

    # WR得分（±5）— v2新增
    if wr_res:
        wr_sig = wr_res.get("signal", "")
        if "超买" in wr_sig:
            score -= 5
            signals.append(f"▼ WR{wr_sig}")
        elif "超卖" in wr_sig:
            score += 5
            signals.append(f"▲ WR{wr_sig}")

    # ATR波动率信息（不直接加分，仅作信号提示）— v2新增
    if atr_res:
        vol = atr_res.get("volatility", "")
        vol_trend = atr_res.get("vol_trend", "")
        if "极高" in vol or "高波动" in vol:
            signals.append(f"⚡ {vol}")
        if vol_trend:
            signals.append(f"► 波动率{vol_trend}")

    # 确保范围
    score = max(0, min(100, score))

    # 综合判定
    if score >= 75:
        verdict = "强势看多"
    elif score >= 60:
        verdict = "偏多"
    elif score >= 40:
        verdict = "中性震荡"
    elif score >= 25:
        verdict = "偏空"
    else:
        verdict = "强势看空"

    return {
        "composite_score": score,
        "verdict": verdict,
        "signals": signals,
    }


# ---------------------------------------------------------------------------
#  格式化输出
# ---------------------------------------------------------------------------

def format_md(code: str, results: Dict[str, Any]) -> str:
    """格式化为Markdown报告"""
    lines = [
        f"# {code} 技术分析指标",
        f"**计算时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**K线数据量**: {results.get('kline_count', 0)} 根",
        "",
    ]

    # 综合评分
    comp = results.get("composite", {})
    if comp:
        lines.append("## 📊 综合技术面评分")
        lines.append("")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| **综合评分** | **{comp.get('composite_score', '-')}/100** |")
        lines.append(f"| **技术面判定** | **{comp.get('verdict', '-')}** |")
        lines.append("")
        for sig in comp.get("signals", []):
            lines.append(f"- {sig}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # MA
    ma = results.get("ma", {})
    if ma:
        lines.append("## 均线系统 (MA)")
        lines.append("")
        lines.append(f"**排列状态**: {ma.get('arrangement', '-')}")
        lines.append("")
        lines.append("| 均线 | 数值 | 当前价位 | 偏离% |")
        lines.append("|------|------|---------|-------|")
        for key, info in ma.get("current_vs_ma", {}).items():
            lines.append(f"| {key} | {info['value']} | {info['position']} | {info['diff_pct']:+.2f}% |")
        lines.append("")
        lines.append("---")
        lines.append("")

    # MACD
    macd = results.get("macd", {})
    if macd:
        lines.append("## MACD")
        lines.append("")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| DIF | {macd.get('dif', '-')} |")
        lines.append(f"| DEA | {macd.get('dea', '-')} |")
        lines.append(f"| MACD柱 | {macd.get('macd_bar', '-')} |")
        lines.append(f"| **信号** | **{macd.get('signal', '-')}** |")
        lines.append(f"| 柱趋势 | {macd.get('histogram_trend', '-')} |")
        lines.append(f"| 零轴位置 | {macd.get('axis_position', '-')} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    # RSI
    rsi = results.get("rsi", {})
    if rsi:
        lines.append("## RSI")
        lines.append("")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        for key, val in rsi.get("rsi_values", {}).items():
            lines.append(f"| {key} | {val} |")
        lines.append(f"| **判断** | **{rsi.get('signal', '-')}** |")
        lines.append("")
        lines.append("---")
        lines.append("")

    # KDJ
    kdj = results.get("kdj", {})
    if kdj:
        lines.append("## KDJ")
        lines.append("")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| K | {kdj.get('k', '-')} |")
        lines.append(f"| D | {kdj.get('d', '-')} |")
        lines.append(f"| J | {kdj.get('j', '-')} |")
        lines.append(f"| **信号** | **{kdj.get('signal', '-')}** |")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 布林带
    boll = results.get("bollinger", {})
    if boll:
        lines.append("## 布林带 (Bollinger Bands)")
        lines.append("")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 上轨 | {boll.get('upper', '-')} |")
        lines.append(f"| 中轨 | {boll.get('middle', '-')} |")
        lines.append(f"| 下轨 | {boll.get('lower', '-')} |")
        lines.append(f"| 带宽% | {boll.get('bandwidth', '-')} |")
        lines.append(f"| **信号** | **{boll.get('signal', '-')}** |")
        if boll.get("mouth"):
            lines.append(f"| 缩口/扩口 | {boll['mouth']} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 支撑压力位
    sr = results.get("support_resistance", {})
    if sr:
        lines.append("## 支撑位 / 压力位")
        lines.append("")
        lines.append(f"**当前价**: {sr.get('current', '-')}")
        lines.append("")
        if sr.get("volume_profile_top3"):
            lines.append("**密集成交区（Top3）**:")
            lines.append("")
            lines.append("| 价位 | 相对成交量% |")
            lines.append("|------|-----------|")
            for vp in sr["volume_profile_top3"]:
                lines.append(f"| {vp['price']} | {vp['rel_volume']}% |")
            lines.append("")
        if sr.get("supports"):
            lines.append("**支撑位**:")
            lines.append("")
            lines.append("| 价位 | 来源 |")
            lines.append("|------|------|")
            for s in sr["supports"]:
                lines.append(f"| {s['price']} | {s['source']} |")
            lines.append("")
        if sr.get("resistances"):
            lines.append("**压力位**:")
            lines.append("")
            lines.append("| 价位 | 来源 |")
            lines.append("|------|------|")
            for r in sr["resistances"]:
                lines.append(f"| {r['price']} | {r['source']} |")
            lines.append("")

    # CCI — v2新增
    cci = results.get("cci", {})
    if cci and cci.get("cci") is not None:
        lines.append("## CCI（顺势指标）")
        lines.append("")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| CCI(14) | {cci.get('cci', '-')} |")
        lines.append(f"| **信号** | **{cci.get('signal', '-')}** |")
        lines.append(f"| 趋势 | {cci.get('trend', '-')} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    # ATR — v2新增
    atr = results.get("atr", {})
    if atr and atr.get("atr") is not None:
        lines.append("## ATR（真实波幅）")
        lines.append("")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| ATR(14) | {atr.get('atr', '-')} |")
        lines.append(f"| ATR% | {atr.get('atr_pct', '-')}% |")
        lines.append(f"| **波动率** | **{atr.get('volatility', '-')}** |")
        if atr.get("vol_trend"):
            lines.append(f"| 波动趋势 | {atr['vol_trend']} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    # WR — v2新增
    wr = results.get("williams_r", {})
    if wr:
        lines.append("## WR（威廉指标）")
        lines.append("")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        for key, val in wr.get("wr_values", {}).items():
            lines.append(f"| {key} | {val} |")
        lines.append(f"| **判断** | **{wr.get('signal', '-')}** |")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 第三方交叉验证 — v2新增
    cv = results.get("cross_validation", {})
    if cv:
        lines.append("## 📡 第三方API交叉验证")
        lines.append("")
        if cv.get("source"):
            lines.append(f"**数据源**: {cv['source']}")
            lines.append("")
        if cv.get("comparisons"):
            lines.append("| 指标 | 本地计算 | 第三方值 | 偏差 | 一致性 |")
            lines.append("|------|---------|---------|------|--------|")
            for comp in cv["comparisons"]:
                lines.append(f"| {comp.get('indicator', '-')} | {comp.get('local', '-')} | "
                             f"{comp.get('remote', '-')} | {comp.get('deviation', '-')} | "
                             f"{comp.get('status', '-')} |")
            lines.append("")
        if cv.get("error"):
            lines.append(f"⚠️ 交叉验证未完成: {cv['error']}")
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  11. 第三方API交叉验证（zhituapi）— v2新增
# ---------------------------------------------------------------------------

# zhituapi token（免费额度，仅用于交叉验证）
_ZHITUAPI_TOKEN = os.environ.get("ZHITUAPI_TOKEN", "")

def _fetch_json(url: str, timeout: int = 8) -> Optional[Dict]:
    """通用HTTP GET请求，返回JSON或None"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def fetch_zhituapi_indicator(code: str, indicator: str, token: str = "") -> Optional[Dict]:
    """从zhituapi获取单个技术指标
    indicator: macd / kdj / ma / boll
    code: 股票代码（如 300308）
    """
    tk = token or _ZHITUAPI_TOKEN
    if not tk:
        return None
    # zhituapi URL格式: https://api.zhituapi.com/hs/latest/{indicator}/{code}/d?token={token}
    url = f"https://api.zhituapi.com/hs/latest/{indicator}/{code}/d?token={tk}"
    return _fetch_json(url)


def cross_validate_with_zhituapi(code: str, local_results: Dict,
                                  token: str = "") -> Dict[str, Any]:
    """将本地计算结果与zhituapi返回的指标进行交叉比对
    返回比对结果，包含每个指标的偏差和一致性判断"""
    cv_result = {"source": "zhituapi.com", "comparisons": [], "error": None}
    tk = token or _ZHITUAPI_TOKEN
    if not tk:
        cv_result["error"] = "未配置ZHITUAPI_TOKEN（设置环境变量 ZHITUAPI_TOKEN 即可启用）"
        return cv_result

    indicator_map = {
        "macd": {"remote_fields": [("dif", "dif"), ("dea", "dea"), ("macd", "macd_bar")],
                 "local_key": "macd"},
        "kdj": {"remote_fields": [("k", "k"), ("d", "d"), ("j", "j")],
                "local_key": "kdj"},
    }

    for api_name, mapping in indicator_map.items():
        local_data = local_results.get(mapping["local_key"], {})
        if not local_data:
            continue

        remote_data = fetch_zhituapi_indicator(code, api_name, tk)
        if not remote_data or remote_data.get("code") != 200:
            cv_result["comparisons"].append({
                "indicator": api_name.upper(),
                "local": "有数据", "remote": "请求失败",
                "deviation": "-", "status": "⚠ 无法验证"
            })
            continue

        # zhituapi返回格式：{"code": 200, "data": [{"dif": ..., "dea": ..., ...}]}
        items = remote_data.get("data", [])
        if not items:
            continue
        latest = items[-1] if isinstance(items, list) else items

        for remote_key, local_key in mapping["remote_fields"]:
            local_val = local_data.get(local_key)
            remote_val = latest.get(remote_key)
            if local_val is None or remote_val is None:
                continue
            try:
                local_f = float(local_val)
                remote_f = float(remote_val)
            except (ValueError, TypeError):
                continue

            # 计算偏差
            if abs(remote_f) > 0.001:
                dev_pct = abs(local_f - remote_f) / abs(remote_f) * 100
            elif abs(local_f) > 0.001:
                dev_pct = abs(local_f - remote_f) / abs(local_f) * 100
            else:
                dev_pct = 0.0

            if dev_pct < 3:
                status = "✅ 一致"
            elif dev_pct < 10:
                status = "⚠️ 小偏差"
            else:
                status = "❌ 偏差较大"

            cv_result["comparisons"].append({
                "indicator": f"{api_name.upper()}.{remote_key}",
                "local": round(local_f, 4),
                "remote": round(remote_f, 4),
                "deviation": f"{dev_pct:.1f}%",
                "status": status,
            })

    return cv_result


# ---------------------------------------------------------------------------
#  主计算入口
# ---------------------------------------------------------------------------

def calculate_all(klines: List[Dict], indicators: List[str] = None,
                  code: str = "", cross_validate: bool = False,
                  zhituapi_token: str = "") -> Dict[str, Any]:
    """计算全部（或指定）技术指标，v2支持CCI/ATR/WR + 第三方交叉验证"""
    closes, highs, lows, opens, volumes = _extract_prices(klines)
    if not closes:
        return {"error": "K线数据为空", "kline_count": 0}

    results = {"kline_count": len(closes)}
    all_indicators = indicators or [
        "ma", "macd", "rsi", "kdj", "bollinger",
        "cci", "atr", "williams_r",  # v2新增
        "support_resistance", "composite",
    ]

    ma_res = {}
    if "ma" in all_indicators or "support_resistance" in all_indicators or "composite" in all_indicators:
        ma_res = calc_ma(closes)
        results["ma"] = ma_res

    macd_res = {}
    if "macd" in all_indicators or "composite" in all_indicators:
        macd_res = calc_macd(closes)
        results["macd"] = macd_res

    rsi_res = {}
    if "rsi" in all_indicators or "composite" in all_indicators:
        rsi_res = calc_rsi(closes)
        results["rsi"] = rsi_res

    kdj_res = {}
    if "kdj" in all_indicators or "composite" in all_indicators:
        kdj_res = calc_kdj(highs, lows, closes)
        results["kdj"] = kdj_res

    boll_res = {}
    if "bollinger" in all_indicators or "composite" in all_indicators:
        boll_res = calc_bollinger(closes)
        results["bollinger"] = boll_res

    # v2新增指标
    cci_res = {}
    if "cci" in all_indicators or "composite" in all_indicators:
        cci_res = calc_cci(highs, lows, closes)
        results["cci"] = cci_res

    atr_res = {}
    if "atr" in all_indicators or "composite" in all_indicators:
        atr_res = calc_atr(highs, lows, closes)
        results["atr"] = atr_res

    wr_res = {}
    if "williams_r" in all_indicators or "composite" in all_indicators:
        wr_res = calc_williams_r(highs, lows, closes)
        results["williams_r"] = wr_res

    sr_res = {}
    if "support_resistance" in all_indicators:
        sr_res = calc_support_resistance(closes, highs, lows, volumes, ma_res)
        results["support_resistance"] = sr_res

    if "composite" in all_indicators:
        if not sr_res:
            sr_res = calc_support_resistance(closes, highs, lows, volumes, ma_res)
            results["support_resistance"] = sr_res
        results["composite"] = calc_composite_score(
            ma_res, macd_res, rsi_res, kdj_res, boll_res, sr_res,
            cci_res, atr_res, wr_res)

    # 第三方交叉验证（可选）
    if cross_validate and code:
        cv = cross_validate_with_zhituapi(code, results, zhituapi_token)
        results["cross_validation"] = cv

    return results


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def _print_utf8(text: str):
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()


def main():
    parser = argparse.ArgumentParser(
        description="技术分析指标计算脚本 — 本地计算 + 第三方API交叉验证",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("code_positional", nargs="?", default="", help="股票代码（位置参数，等同 --code）")
    parser.add_argument("--code", default="", help="股票代码（自动从 stock_quote_scraper 获取K线）")
    parser.add_argument("--kline-file", default="", help="K线JSON文件路径")
    parser.add_argument("--days", type=int, default=250, help="获取K线天数（默认250）")
    parser.add_argument("--indicators", default="",
                        help="指定指标（逗号分隔：ma,macd,rsi,kdj,bollinger,cci,atr,williams_r,"
                             "support_resistance,composite）")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    parser.add_argument("--output", "-o", default="", help="输出到文件")
    parser.add_argument("--cross-validate", action="store_true",
                        help="启用第三方API（zhituapi）交叉验证")
    parser.add_argument("--zhituapi-token", default="",
                        help="zhituapi token（也可设置环境变量 ZHITUAPI_TOKEN）")
    args = parser.parse_args()

    # 位置参数兼容：如果没有 --code 但有位置参数，则使用位置参数
    if not args.code and args.code_positional:
        args.code = args.code_positional

    # 获取K线数据
    klines = []
    if args.kline_file:
        klines = parse_kline_json(args.kline_file)
    elif args.code:
        klines = fetch_kline_data(args.code, args.days)
    else:
        parser.error("必须指定 --code 或 --kline-file")

    if not klines:
        _print_utf8(json.dumps({"error": "无法获取K线数据"}, ensure_ascii=False))
        sys.exit(1)

    # 指标列表
    indicators = None
    if args.indicators:
        indicators = [i.strip() for i in args.indicators.split(",")]

    # 计算
    code = args.code or "UNKNOWN"
    results = calculate_all(klines, indicators, code=code,
                            cross_validate=args.cross_validate,
                            zhituapi_token=args.zhituapi_token)

    # 输出
    if args.json:
        text = json.dumps(results, ensure_ascii=False, indent=2)
    else:
        text = format_md(code, results)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"✓ 输出到 {args.output}", file=sys.stderr)
    else:
        _print_utf8(text)


if __name__ == "__main__":
    main()
