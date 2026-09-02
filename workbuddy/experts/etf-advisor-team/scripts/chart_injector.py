#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chart_injector.py — 为交易决策报告注入高价值SVG图表

⚠️ 方案 B 下本脚本已不再作为独立入口使用：
    v8（2026-04 方案 B）起，日常交付链路：
      Markdown(纯文字) → md2html_report.py → 自动内嵌 inline SVG → .html
    图表的 "向 HTML 锚点注入" 由 `md2html_report.py` 的 `inject_charts_by_anchor()` 完成。
    `chart_generator.py` 通过 `build_charts_inmemory()` 在内存中生成 SVG，
    内部复用本文件里 9 个 `chart_*` 生成函数的核心绘图逻辑（作为函数库使用）。
    **不再**产生独立的 .svg 文件，.md 也不含图片引用。
    因此你在常规分析任务里**不应该直接调用本脚本**（它只作为底层渲染函数库存在）。

用法（仅调试场景）: python scripts/chart_injector.py <html_file>
功能: 读取 FinancialData 中的数据，生成纯 inline SVG 图表，注入到指定 HTML 报告中
"""
import sys, os, re, json, math
from pathlib import Path

# Windows PowerShell / CMD 下强制 stdout/stderr 使用 UTF-8 编码，
# 避免 ✅/⚠️/🔧 等特殊字符触发 UnicodeEncodeError 导致脚本崩溃。
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ============================================================
# 配置
# ============================================================
# 动态获取 WORKSPACE：优先使用环境变量，否则从脚本位置向上推导
# 本脚本位于 scripts/，故向上三级即工作区根
_SCRIPT_DIR = Path(__file__).resolve().parent  # scripts/
WORKSPACE = Path(os.environ.get("CODEBUDDY_WORKSPACE", _SCRIPT_DIR.parent.parent.parent))
FIN_DIR = WORKSPACE / "FinancialData"

# 色彩方案 — 白底主题，A 股红绿配色（红涨绿跌）
C = dict(
    bg="#ffffff", panel="#fafbfc", line="#e1e6ec", text="#1a1a1a",
    muted="#6b7785", accent="#d84033", ok="#1a9c5c", warn="#e8870c",
    blue="#1565c0", purple="#7a4fcc", teal="#0d8c7a", orange="#e8870c",
    red_candle="#d84033", green_candle="#1a9c5c",  # A 股：红涨 / 绿跌
    grid="#eef1f5", grid_light="#f5f7fa",
)

# ============================================================
# 数据解析工具
# ============================================================
def parse_md_table(text, header_match=None):
    """解析markdown表格为list of dict"""
    lines = text.strip().split('\n')
    results = []
    headers = None
    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            if headers is not None and not line:
                break  # 表结束
            continue
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if headers is None:
            if header_match and not any(header_match in c for c in cells):
                continue
            headers = cells
            continue
        if all(set(c) <= set('-: ') for c in cells):
            continue  # 分隔行
        if len(cells) == len(headers):
            results.append(dict(zip(headers, cells)))
    return results

def safe_float(s, default=0.0):
    """安全转浮点"""
    if s is None:
        return default
    s = str(s).replace(',', '').replace('亿', '').replace('元', '').replace('%', '').strip()
    if s in ('—', '-', 'None', '', 'N/A'):
        return default
    try:
        return float(s)
    except:
        return default

def read_file(path):
    for enc in ('utf-8', 'gbk', 'latin-1'):
        try:
            return Path(path).read_text(encoding=enc)
        except:
            continue
    return ''

# ============================================================
# 图表 1: K线 + 均线曲线 + 成交量 + 布林带 + 支撑/压力位
# ============================================================

def _compute_ma(closes, period):
    """滚动计算均线序列，长度不足的位置填 None"""
    ma = [None] * len(closes)
    for i in range(period - 1, len(closes)):
        ma[i] = sum(closes[i - period + 1:i + 1]) / period
    return ma

def _compute_bollinger(closes, period=20, k=2):
    """计算布林带：返回 (upper, mid, lower) 三条序列"""
    n = len(closes)
    upper = [None] * n
    mid = [None] * n
    lower = [None] * n
    for i in range(period - 1, n):
        window = closes[i - period + 1:i + 1]
        avg = sum(window) / period
        var = sum((x - avg) ** 2 for x in window) / period
        std = var ** 0.5
        mid[i] = avg
        upper[i] = avg + k * std
        lower[i] = avg - k * std
    return upper, mid, lower

def _find_support_resistance(klines, closes):
    """从近期K线找关键支撑位和压力位"""
    if not closes:
        return [], []
    current = closes[-1]
    # 近期高低点
    highs = [safe_float(d.get('最高', 0)) for d in klines if safe_float(d.get('最高', 0)) > 0]
    lows = [safe_float(d.get('最低', 0)) for d in klines if safe_float(d.get('最低', 0)) > 0]
    if not highs or not lows:
        return [], []

    # 价格聚类 — 找出频繁出现的价格区域
    price_step = max(1, round(current * 0.005))  # 0.5% 为一个 bin
    from collections import Counter
    bins = Counter()
    for h in highs:
        bins[round(h / price_step) * price_step] += 1
    for l in lows:
        bins[round(l / price_step) * price_step] += 1

    # 整数关口
    base = int(current / 50) * 50
    for p in range(base - 200, base + 250, 50):
        if p > 0:
            bins[p] += 2  # 整数关口加权

    supports = []
    resistances = []
    for price, count in bins.most_common(20):
        if price < current * 0.995 and count >= 2:
            supports.append(price)
        elif price > current * 1.005 and count >= 2:
            resistances.append(price)

    supports.sort(reverse=True)
    resistances.sort()
    return supports[:3], resistances[:3]


def chart_kline(kline_records, display_days=120):
    """生成增强版K线图：120日K线 + MA曲线 + 成交量 + 布林带 + 支撑压力位

    Parameters:
        kline_records: list[dict] — 原始K线数据（fetch_kline 返回的 'K线数据' 列表）
                       每条记录: {日期, 开盘, 收盘, 最高, 最低, 成交量(手), 涨跌幅(%), ...}
        display_days:  int — 展示天数（默认120天）
    """
    if not kline_records:
        return ''

    # 取最后 display_days 条用于绘图
    data = kline_records[-display_days:]
    n = len(data)
    if n < 5:
        return ''

    # 提取序列
    closes = [safe_float(d.get('收盘', 0)) for d in data]
    opens = [safe_float(d.get('开盘', 0)) for d in data]
    highs = [safe_float(d.get('最高', 0)) for d in data]
    lows = [safe_float(d.get('最低', 0)) for d in data]
    volumes = [safe_float(d.get('成交量(手)', 0)) for d in data]

    # ---- 动态计算均线 ----
    # 为保证MA60在首日就有值，可以使用 kline_records 中更多的前置数据
    all_closes = [safe_float(d.get('收盘', 0)) for d in kline_records]
    offset = len(kline_records) - n  # data[0] 在 kline_records 中的位置
    ma_periods = [(5, "#f39c12", "MA5"), (10, "#3498db", "MA10"),
                  (20, "#9b59b6", "MA20"), (60, "#1abc9c", "MA60")]
    ma_full = {}
    for period, color, label in ma_periods:
        full_ma = _compute_ma(all_closes, period)
        ma_full[label] = full_ma[offset:]  # 截取 display 部分

    # ---- 布林带 (20日) ----
    boll_upper_full, boll_mid_full, boll_lower_full = _compute_bollinger(all_closes, 20, 2)
    boll_upper = boll_upper_full[offset:]
    boll_mid = boll_mid_full[offset:]
    boll_lower = boll_lower_full[offset:]

    # ---- 支撑/压力位 ----
    supports, resistances = _find_support_resistance(data, closes)

    # ---- SVG 布局 ----
    W = 920
    H_CHART = 280
    H_VOL = 80
    PADDING_L, PADDING_R, PADDING_T = 62, 40, 30
    GAP = 15
    H_TOTAL = PADDING_T + H_CHART + GAP + H_VOL + 40

    chart_area_w = W - PADDING_L - PADDING_R
    spacing = chart_area_w / n
    candle_w = max(1.5, min(8, spacing * 0.65))

    # ---- 价格范围（含MA和布林带） ----
    all_vis_prices = [p for p in closes + highs + lows if p > 0]
    for label in ma_full:
        all_vis_prices.extend([v for v in ma_full[label] if v is not None and v > 0])
    all_vis_prices.extend([v for v in boll_upper if v is not None and v > 0])
    all_vis_prices.extend([v for v in boll_lower if v is not None and v > 0])
    if not all_vis_prices:
        return ''
    price_min = min(all_vis_prices) * 0.98
    price_max = max(all_vis_prices) * 1.02

    def py(price):
        if price_max == price_min:
            return PADDING_T + H_CHART / 2
        return PADDING_T + H_CHART * (1 - (price - price_min) / (price_max - price_min))

    def px(i):
        return PADDING_L + spacing * (i + 0.5)

    # ---- 成交量范围 ----
    valid_vols = [v for v in volumes if v > 0]
    max_vol = max(valid_vols) if valid_vols else 1
    vol_top = PADDING_T + H_CHART + GAP
    vol_bottom = vol_top + H_VOL

    # ========== 开始构建 SVG ==========
    svg = []
    svg.append(f'<svg viewBox="0 0 {W} {H_TOTAL}" xmlns="http://www.w3.org/2000/svg" '
               f'role="img" aria-label="K线走势图" style="font-family:system-ui,sans-serif">')

    # ---- defs: 渐变 ----
    svg.append('<defs>')
    svg.append(f'<linearGradient id="bollGrad" x1="0" y1="0" x2="0" y2="1">'
               f'<stop offset="0%" stop-color="{C["blue"]}" stop-opacity="0.08"/>'
               f'<stop offset="50%" stop-color="{C["blue"]}" stop-opacity="0.04"/>'
               f'<stop offset="100%" stop-color="{C["blue"]}" stop-opacity="0.08"/>'
               f'</linearGradient>')
    svg.append('</defs>')

    # ---- 背景网格 ----
    price_ticks = 6
    for i in range(price_ticks + 1):
        yy = PADDING_T + H_CHART * i / price_ticks
        pv = price_max - (price_max - price_min) * i / price_ticks
        svg.append(f'<line x1="{PADDING_L}" y1="{yy:.1f}" x2="{W-PADDING_R}" y2="{yy:.1f}" '
                   f'stroke="{C["grid_light"]}" stroke-width="0.5"/>')
        svg.append(f'<text x="{PADDING_L-5}" y="{yy+4:.1f}" fill="{C["muted"]}" '
                   f'font-size="9" text-anchor="end">{pv:.1f}</text>')

    # ---- 布林带填充区域 ----
    boll_poly_top = []
    boll_poly_bot = []
    for i in range(n):
        if boll_upper[i] is not None and boll_lower[i] is not None:
            boll_poly_top.append(f'{px(i):.1f},{py(boll_upper[i]):.1f}')
            boll_poly_bot.append(f'{px(i):.1f},{py(boll_lower[i]):.1f}')
    if boll_poly_top:
        boll_poly_bot.reverse()
        svg.append(f'<polygon points="{" ".join(boll_poly_top + boll_poly_bot)}" fill="url(#bollGrad)"/>')

    # 布林带上下轨线
    upper_pts = ' '.join(f'{px(i):.1f},{py(boll_upper[i]):.1f}'
                         for i in range(n) if boll_upper[i] is not None)
    lower_pts = ' '.join(f'{px(i):.1f},{py(boll_lower[i]):.1f}'
                         for i in range(n) if boll_lower[i] is not None)
    if upper_pts:
        svg.append(f'<polyline points="{upper_pts}" fill="none" stroke="{C["blue"]}" '
                   f'stroke-width="0.8" stroke-dasharray="4 2" opacity="0.5"/>')
    if lower_pts:
        svg.append(f'<polyline points="{lower_pts}" fill="none" stroke="{C["blue"]}" '
                   f'stroke-width="0.8" stroke-dasharray="4 2" opacity="0.5"/>')

    # ---- 支撑/压力位水平线 ----
    for sp in supports[:2]:
        if price_min <= sp <= price_max:
            yy = py(sp)
            svg.append(f'<line x1="{PADDING_L}" y1="{yy:.1f}" x2="{W-PADDING_R}" y2="{yy:.1f}" '
                       f'stroke="{C["ok"]}" stroke-width="0.8" stroke-dasharray="8 4" opacity="0.6"/>')
            svg.append(f'<text x="{W-PADDING_R+2}" y="{yy+3:.1f}" fill="{C["ok"]}" '
                       f'font-size="8">S {sp:.0f}</text>')
    for rp in resistances[:2]:
        if price_min <= rp <= price_max:
            yy = py(rp)
            svg.append(f'<line x1="{PADDING_L}" y1="{yy:.1f}" x2="{W-PADDING_R}" y2="{yy:.1f}" '
                       f'stroke="{C["accent"]}" stroke-width="0.8" stroke-dasharray="8 4" opacity="0.6"/>')
            svg.append(f'<text x="{W-PADDING_R+2}" y="{yy+3:.1f}" fill="{C["accent"]}" '
                       f'font-size="8">R {rp:.0f}</text>')

    # ---- K线蜡烛 ----
    for i, d in enumerate(data):
        o = opens[i]
        c = closes[i]
        h = highs[i]
        lo = lows[i]
        if o == 0 or c == 0:
            continue

        cx = px(i)
        is_up = c >= o
        color = C["red_candle"] if is_up else C["green_candle"]
        body_top = py(max(o, c))
        body_bot = py(min(o, c))
        body_h = max(body_bot - body_top, 1)

        # 影线
        svg.append(f'<line x1="{cx:.1f}" y1="{py(h):.1f}" x2="{cx:.1f}" y2="{py(lo):.1f}" '
                   f'stroke="{color}" stroke-width="1"/>')
        # 实体
        opacity = "0.95" if is_up else "0.85"
        svg.append(f'<rect x="{cx-candle_w/2:.1f}" y="{body_top:.1f}" '
                   f'width="{candle_w:.1f}" height="{body_h:.1f}" rx="0.5" '
                   f'fill="{color}" opacity="{opacity}"/>')

        # 成交量柱子
        vol = volumes[i]
        bar_h = H_VOL * vol / max_vol if max_vol > 0 and vol > 0 else 0
        bar_color = C["red_candle"] if is_up else C["green_candle"]
        svg.append(f'<rect x="{cx-candle_w/2:.1f}" y="{vol_bottom-bar_h:.1f}" '
                   f'width="{candle_w:.1f}" height="{bar_h:.1f}" rx="0.5" '
                   f'fill="{bar_color}" opacity="0.55"/>')

    # ---- 日期标签（自适应间隔）----
    label_interval = max(1, n // 12)  # 最多显示约12个日期标签
    for i, d in enumerate(data):
        date_str = d.get('日期', '')
        if date_str and (i % label_interval == 0 or i == n - 1):
            short_date = date_str[5:]  # MM-DD
            cx = px(i)
            svg.append(f'<text x="{cx:.1f}" y="{H_TOTAL-5:.1f}" fill="{C["muted"]}" '
                       f'font-size="8" text-anchor="middle">{short_date}</text>')

    # ---- MA 均线曲线 ----
    for period, color, label in ma_periods:
        ma_vals = ma_full[label]
        pts = []
        for i in range(n):
            if ma_vals[i] is not None:
                pts.append(f'{px(i):.1f},{py(ma_vals[i]):.1f}')
        if pts:
            svg.append(f'<polyline points="{" ".join(pts)}" fill="none" '
                       f'stroke="{color}" stroke-width="1.2" stroke-linejoin="round" opacity="0.85"/>')

    # ---- 当前价标注 ----
    current_price = closes[-1]
    if current_price > 0:
        yy = py(current_price)
        svg.append(f'<line x1="{PADDING_L}" y1="{yy:.1f}" x2="{W-PADDING_R}" y2="{yy:.1f}" '
                   f'stroke="{C["warn"]}" stroke-width="1" stroke-dasharray="2 2" opacity="0.8"/>')
        svg.append(f'<rect x="{PADDING_L-60}" y="{yy-8:.1f}" width="57" height="16" rx="3" '
                   f'fill="{C["warn"]}" opacity="0.9"/>')
        svg.append(f'<text x="{PADDING_L-31}" y="{yy+4:.1f}" fill="#fff" font-size="10" '
                   f'text-anchor="middle" font-weight="700">{current_price:.1f}</text>')

    # ---- 成交量刻度 ----
    vol_label = f'{max_vol/10000:.0f}万手' if max_vol >= 10000 else f'{max_vol:.0f}手'
    svg.append(f'<text x="{PADDING_L-5}" y="{vol_top+12:.1f}" fill="{C["muted"]}" '
               f'font-size="8" text-anchor="end">{vol_label}</text>')
    svg.append(f'<text x="{PADDING_L-5}" y="{vol_bottom:.1f}" fill="{C["muted"]}" '
               f'font-size="8" text-anchor="end">0</text>')

    # ---- 区域标签 ----
    svg.append(f'<text x="{PADDING_L}" y="{PADDING_T-12}" fill="{C["text"]}" '
               f'font-size="11" font-weight="700">价格(元)</text>')
    svg.append(f'<text x="{PADDING_L}" y="{vol_top-3}" fill="{C["muted"]}" font-size="9">成交量</text>')

    # ---- 图例 ----
    legend_x = PADDING_L + 80
    legend_y = PADDING_T - 15
    for idx, (period, color, label) in enumerate(ma_periods):
        lx = legend_x + idx * 72
        svg.append(f'<line x1="{lx}" y1="{legend_y}" x2="{lx+18}" y2="{legend_y}" '
                   f'stroke="{color}" stroke-width="1.5"/>')
        svg.append(f'<text x="{lx+22}" y="{legend_y+3}" fill="{color}" font-size="9">{label}</text>')
    # 布林带图例
    boll_lx = legend_x + len(ma_periods) * 72
    svg.append(f'<rect x="{boll_lx}" y="{legend_y-4}" width="18" height="8" rx="2" '
               f'fill="{C["blue"]}" opacity="0.2" stroke="{C["blue"]}" stroke-width="0.5" stroke-dasharray="3 1"/>')
    svg.append(f'<text x="{boll_lx+22}" y="{legend_y+3}" fill="{C["blue"]}" font-size="9">BOLL</text>')

    svg.append('</svg>')

    # 确定标题中的天数
    title_days = n
    first_date = data[0].get('日期', '')[:10] if data else ''
    last_date = data[-1].get('日期', '')[:10] if data else ''
    subtitle_parts = [
        f"红涨绿跌 | {title_days}个交易日({first_date}~{last_date})",
        "MA5/10/20/60 + BOLL(20,2) | 底部=真实成交量",
    ]

    return wrap_chart_card(
        '\n'.join(svg),
        f"近{title_days}日K线走势",
        ' | '.join(subtitle_parts)
    )


# ============================================================
# 图表 2: 核心指标卡片矩阵（动态数据）
# ============================================================
def _parse_fundamental_kv(text, section_header, key):
    """从 fundamental.md 中解析指定章节的键值对"""
    if not text:
        return None
    # 定位章节
    idx = text.find(section_header)
    if idx < 0:
        return None
    chunk = text[idx:idx + 3000]
    for line in chunk.split('\n'):
        line = line.strip()
        if line.startswith('|') and key in line:
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if len(cells) >= 2 and key in cells[0]:
                return cells[1]
    return None


def _safe_float(val, default=None):
    """安全转换为 float"""
    if val is None:
        return default
    try:
        return float(str(val).replace(',', '').replace('%', '').replace('x', '').strip())
    except (ValueError, TypeError):
        return default


def _format_market_cap(val_yi):
    """格式化市值（亿元）显示"""
    if val_yi is None:
        return ("N/A", "亿")
    if val_yi >= 10000:
        return (f"{val_yi/10000:.2f}", "万亿")
    return (f"{val_yi:.0f}", "亿")


def _market_cap_label(val_yi):
    """根据市值大小给出标签"""
    if val_yi is None:
        return "—"
    if val_yi >= 5000:
        return "超大盘"
    elif val_yi >= 1000:
        return "大盘"
    elif val_yi >= 300:
        return "中盘"
    else:
        return "小盘"


def _roe_label(val):
    """根据 ROE 给出评级标签"""
    if val is None:
        return "—"
    if val >= 30:
        return "卓越"
    elif val >= 20:
        return "优秀"
    elif val >= 15:
        return "良好"
    elif val >= 10:
        return "一般"
    else:
        return "偏低"


def _pct_label(pct):
    """根据历史分位给出标签"""
    if pct is None:
        return "—"
    return f"{pct:.0f}%分位"


def _pe_pct_color(pct):
    """根据分位数选择颜色"""
    if pct is None:
        return C["muted"]
    if pct >= 80:
        return C["accent"]
    elif pct >= 50:
        return C["warn"]
    else:
        return C["ok"]


def chart_metric_cards(code, fundamental_text, realtime_data=None, fundamental_json=None):
    """生成核心指标卡片矩阵 — 动态读取 FinancialData

    Parameters:
        code:               股票代码
        fundamental_text:   fundamental.md 原始文本
        realtime_data:      realtime.json 解析后的 dict（可选）
        fundamental_json:   fundamental.json 解析后的 dict（可选，用于多源回退）
    """
    from datetime import datetime

    # ---------- 提取数据 ----------
    # 1) 最新价 & 涨跌幅
    price = None
    change_pct = None
    if realtime_data:
        price = _safe_float(realtime_data.get("最新价"))
        change_pct = _safe_float(realtime_data.get("涨跌幅"))

    if price is None:
        price = _safe_float(_parse_fundamental_kv(fundamental_text, "## 实时估值", "最新价"))

    # 2) PE / PB — 主源: fundamental.md ## 实时估值
    pe_ttm = _safe_float(_parse_fundamental_kv(fundamental_text, "## 实时估值", "PE(TTM)"))
    pb = _safe_float(_parse_fundamental_kv(fundamental_text, "## 实时估值", "PB"))

    # 4) 总市值 — 主源: fundamental.md ## 实时估值
    mktcap_str = _parse_fundamental_kv(fundamental_text, "## 实时估值", "总市值(亿)")
    mktcap = _safe_float(mktcap_str)

    # ---------- 多源回退: PE / PB / 市值 ----------
    # Fallback-1: realtime.json（PE/总市值）
    if pe_ttm is None and realtime_data:
        pe_ttm = _safe_float(realtime_data.get("PE"))
    if mktcap is None and realtime_data:
        raw_mktcap = _safe_float(realtime_data.get("总市值"))
        if raw_mktcap is not None:
            mktcap = raw_mktcap / 1e8  # 元 → 亿

    # Fallback-2: fundamental.json valuation 对象
    if fundamental_json:
        val = fundamental_json.get("valuation", {})
        if pe_ttm is None:
            pe_ttm = _safe_float(val.get("PE(TTM)"))
        if pb is None:
            pb = _safe_float(val.get("PB"))
        if mktcap is None:
            mktcap = _safe_float(val.get("总市值(亿)"))

    # Fallback-3: fundamental.md ## 估值历史分位（当前值）
    if pe_ttm is None:
        pe_ttm = _safe_float(_parse_fundamental_kv(fundamental_text, "## 估值历史分位", "当前PE(TTM)"))
    if pb is None:
        pb = _safe_float(_parse_fundamental_kv(fundamental_text, "## 估值历史分位", "当前PB(MRQ)"))

    # 3) PE / PB 分位
    pe_pct = _safe_float(_parse_fundamental_kv(fundamental_text, "## 估值历史分位", "PE历史分位"))
    pb_pct = _safe_float(_parse_fundamental_kv(fundamental_text, "## 估值历史分位", "PB历史分位"))

    # 5) ROE / 毛利率 / 净利润 — 取最新年报（类型=="年报"的第一条）
    roe_val = None
    gm_val = None
    np_val = None
    np_yoy = None
    if fundamental_text:
        # 搜索主要财务指标表中的年报行
        for line in fundamental_text.split('\n'):
            if '| ' in line and '年报' in line:
                cells = [c.strip() for c in line.split('|')[1:-1]]
                if len(cells) >= 9:
                    roe_val = roe_val or _safe_float(cells[7].replace('%', ''))
                    gm_val = gm_val or _safe_float(cells[8].replace('%', ''))
                    np_val = np_val or _safe_float(cells[5])
                    np_yoy = np_yoy or cells[6]  # 保留原始字符串（含%）
                    break  # 只取第一条年报

    # 6) FCF — 取最新年报：经营净现金流 - abs(投资净现金流)
    fcf_val = None
    if fundamental_text:
        cf_section = fundamental_text.find("## 现金流质量")
        if cf_section >= 0:
            for line in fundamental_text[cf_section:].split('\n'):
                if '|' in line and ('年报' in line or '12-31' in line):
                    cells = [c.strip() for c in line.split('|')[1:-1]]
                    # 表头: 报告期 | 销售收现 | 经营净现金流 | 投资净现金流 | 筹资净现金流
                    if len(cells) >= 4 and '12-31' in cells[0]:
                        ocf = _safe_float(cells[2])
                        icf = _safe_float(cells[3])
                        if ocf is not None and icf is not None:
                            fcf_val = ocf + icf  # 投资现金流本身为负值
                        break

    # ---------- 组装指标卡片 ----------
    price_str = f"{price:.2f}" if price else "N/A"
    price_sub = f"{change_pct:+.2f}%" if change_pct is not None else "—"
    price_color = C["ok"] if (change_pct or 0) >= 0 else C["accent"]

    pe_str = f"{pe_ttm:.1f}" if pe_ttm else "N/A"
    pb_str = f"{pb:.2f}" if pb else "N/A"
    roe_str = f"{roe_val:.2f}" if roe_val else "N/A"

    mktcap_disp, mktcap_unit = _format_market_cap(mktcap)

    gm_str = f"{gm_val:.2f}" if gm_val else "N/A"
    np_str = f"{np_val:.2f}" if np_val else "N/A"
    np_sub = np_yoy.strip() if np_yoy else "—"
    if np_sub != "—" and not np_sub.startswith('+') and not np_sub.startswith('-'):
        np_sub = "+" + np_sub  # 正增长加上+号

    fcf_str = f"{fcf_val:.2f}" if fcf_val else "N/A"
    fcf_sub = "正向充裕" if fcf_val and fcf_val > 0 else ("负向" if fcf_val and fcf_val < 0 else "—")
    fcf_color = C["teal"] if fcf_val and fcf_val > 0 else C["accent"]

    metrics = [
        ("最新价", price_str, "元", price_sub, price_color),
        ("PE(TTM)", pe_str, "x", _pct_label(pe_pct), _pe_pct_color(pe_pct)),
        ("PB", pb_str, "x", _pct_label(pb_pct), _pe_pct_color(pb_pct)),
        ("ROE", roe_str, "%", _roe_label(roe_val), C["ok"] if (roe_val or 0) >= 15 else C["warn"]),
        ("市值", mktcap_disp, mktcap_unit, _market_cap_label(mktcap), C["blue"]),
        ("毛利率", gm_str, "%", "—", C["ok"] if (gm_val or 0) >= 30 else C["warn"]),
        ("净利润", np_str, "亿", np_sub, C["ok"] if np_sub.startswith('+') else C["accent"]),
        ("FCF", fcf_str, "亿", fcf_sub, fcf_color),
    ]

    W = 860
    cols = 4
    rows = 2
    card_w = (W - 30) / cols - 10
    card_h = 80
    H = rows * (card_h + 10) + 20

    svg_parts = [f'<svg viewBox="0 0 {W} {H:.0f}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="核心指标卡片">']

    for idx, (label, value, unit, sub, color) in enumerate(metrics):
        col = idx % cols
        row = idx // cols
        x = 10 + col * (card_w + 10)
        y = 10 + row * (card_h + 10)

        svg_parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{card_w:.1f}" height="{card_h}" rx="8" fill="{C["panel"]}" stroke="{C["line"]}" stroke-width="1"/>')
        svg_parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="4" height="{card_h}" rx="2" fill="{color}"/>')
        svg_parts.append(f'<text x="{x+14:.1f}" y="{y+20:.1f}" fill="{C["muted"]}" font-size="11">{label}</text>')
        svg_parts.append(f'<text x="{x+14:.1f}" y="{y+48:.1f}" fill="{C["text"]}" font-size="22" font-weight="700">{value}<tspan font-size="12" fill="{C["muted"]}"> {unit}</tspan></text>')
        svg_parts.append(f'<text x="{x+14:.1f}" y="{y+68:.1f}" fill="{color}" font-size="10" font-weight="600">{sub}</text>')

    svg_parts.append('</svg>')

    date_str = datetime.now().strftime("%Y-%m-%d")
    return wrap_chart_card(
        '\n'.join(svg_parts),
        "核心指标一览",
        f"实时行情 + 估值 + 盈利质量 | 数据截至 {date_str}"
    )


# ============================================================
# 图表 3: 年度营收+净利润趋势
# ============================================================
def chart_annual_trend(fundamental_text):
    """年度营收(柱) + 净利润(折线) 经典柱线混合图"""
    # 提取年报数据
    annual_data = []
    tables = parse_md_table(fundamental_text, '报告期')
    for row in tables:
        period = row.get('报告期', '')
        typ = row.get('类型', '')
        if typ == '年报' and period.endswith('-12-31'):
            year = period[:4]
            revenue = safe_float(row.get('营收(亿)', 0))
            profit = safe_float(row.get('净利(亿)', 0))
            if revenue > 0:
                annual_data.append((year, revenue, profit))

    annual_data.sort(key=lambda x: x[0])
    annual_data = [d for d in annual_data if d[0] >= '2018']

    if len(annual_data) < 3:
        return ''

    W, H = 860, 320
    PL, PR, PT, PB = 65, 80, 45, 55
    chart_w = W - PL - PR
    chart_h = H - PT - PB

    n = len(annual_data)
    max_rev = max(d[1] for d in annual_data)
    max_profit = max(d[2] for d in annual_data)
    # 左轴=营收, 右轴=净利润（顶部留 15% 空间给标签）
    rev_ceil = math.ceil(max_rev * 1.15 / 50) * 50
    profit_ceil = math.ceil(max_profit * 1.15 / 20) * 20

    # 计算 YoY 增速
    rev_yoy = [None]
    profit_yoy = [None]
    for i in range(1, n):
        prev_rev = annual_data[i - 1][1]
        prev_profit = annual_data[i - 1][2]
        rev_yoy.append(round((annual_data[i][1] / prev_rev - 1) * 100, 1) if prev_rev > 0 else None)
        profit_yoy.append(round((annual_data[i][2] / prev_profit - 1) * 100, 1) if prev_profit > 0 else None)

    def x_pos(i):
        return PL + chart_w * (i + 0.5) / n

    def y_rev(v):
        return PT + chart_h * (1 - v / rev_ceil) if rev_ceil > 0 else PT + chart_h / 2

    def y_profit(v):
        return PT + chart_h * (1 - v / profit_ceil) if profit_ceil > 0 else PT + chart_h / 2

    svg = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
           f'role="img" aria-label="年度营收与净利润趋势" style="font-family:system-ui,sans-serif">']

    # 渐变定义
    svg.append(f'<defs>')
    svg.append(f'<linearGradient id="revBarGrad" x1="0" y1="0" x2="0" y2="1">'
               f'<stop offset="0%" stop-color="{C["blue"]}" stop-opacity="0.7"/>'
               f'<stop offset="100%" stop-color="{C["blue"]}" stop-opacity="0.25"/>'
               f'</linearGradient>')
    svg.append(f'<linearGradient id="profitAreaGrad" x1="0" y1="0" x2="0" y2="1">'
               f'<stop offset="0%" stop-color="{C["ok"]}" stop-opacity="0.2"/>'
               f'<stop offset="100%" stop-color="{C["ok"]}" stop-opacity="0.02"/>'
               f'</linearGradient>')
    svg.append(f'</defs>')

    # 网格 + 双轴刻度
    for i in range(5):
        yy = PT + chart_h * i / 4
        rev_val = rev_ceil * (1 - i / 4)
        profit_val = profit_ceil * (1 - i / 4)
        svg.append(f'<line x1="{PL}" y1="{yy:.1f}" x2="{W-PR}" y2="{yy:.1f}" '
                   f'stroke="{C["grid_light"]}" stroke-width="0.5"/>')
        svg.append(f'<text x="{PL-5}" y="{yy+4:.1f}" fill="{C["blue"]}" '
                   f'font-size="10" text-anchor="end">{rev_val:.0f}</text>')
        svg.append(f'<text x="{W-PR+5}" y="{yy+4:.1f}" fill="{C["ok"]}" '
                   f'font-size="10" text-anchor="start">{profit_val:.0f}</text>')

    # ---- 营收：柱状图（左轴）----
    bar_w = min(50, chart_w / n * 0.55)
    for i, (year, rev, profit) in enumerate(annual_data):
        cx = x_pos(i)
        h_bar = chart_h * rev / rev_ceil if rev_ceil > 0 else 0
        bar_top = PT + chart_h - h_bar
        svg.append(f'<rect x="{cx - bar_w/2:.1f}" y="{bar_top:.1f}" '
                   f'width="{bar_w:.1f}" height="{h_bar:.1f}" rx="3" '
                   f'fill="url(#revBarGrad)"/>')
        # 柱顶营收数值
        svg.append(f'<text x="{cx:.1f}" y="{bar_top - 5:.1f}" fill="{C["blue"]}" '
                   f'font-size="9" text-anchor="middle" font-weight="600">{rev:.0f}</text>')
        # 柱内 YoY（第二年起）
        if rev_yoy[i] is not None and h_bar > 25:
            yoy_color = C["red_candle"] if rev_yoy[i] >= 0 else C["green_candle"]
            yoy_sign = "+" if rev_yoy[i] >= 0 else ""
            svg.append(f'<text x="{cx:.1f}" y="{bar_top + 16:.1f}" fill="{yoy_color}" '
                       f'font-size="8" text-anchor="middle" opacity="0.9">'
                       f'{yoy_sign}{rev_yoy[i]:.0f}%</text>')

    # ---- 净利润：面积 + 折线（右轴）----
    # 面积填充
    area_pts = f'{x_pos(0):.1f},{PT + chart_h:.1f} '
    area_pts += ' '.join(f'{x_pos(i):.1f},{y_profit(d[2]):.1f}' for i, d in enumerate(annual_data))
    area_pts += f' {x_pos(n-1):.1f},{PT + chart_h:.1f}'
    svg.append(f'<polygon points="{area_pts}" fill="url(#profitAreaGrad)"/>')

    # 折线
    profit_points = ' '.join(f'{x_pos(i):.1f},{y_profit(d[2]):.1f}' for i, d in enumerate(annual_data))
    svg.append(f'<polyline points="{profit_points}" fill="none" stroke="{C["ok"]}" '
               f'stroke-width="2.5" stroke-linejoin="round"/>')

    # 数据点 + 标签 + X轴年份
    for i, (year, rev, profit) in enumerate(annual_data):
        cx = x_pos(i)
        py = y_profit(profit)
        # 净利润圆点
        svg.append(f'<circle cx="{cx:.1f}" cy="{py:.1f}" r="4.5" fill="{C["ok"]}" '
                   f'stroke="{C["panel"]}" stroke-width="2"/>')
        # 净利润数值（偏右上避让柱子）
        label_offset_x = 18 if i < n - 1 else -18
        anchor = "start" if i < n - 1 else "end"
        svg.append(f'<text x="{cx + label_offset_x:.1f}" y="{py - 2:.1f}" fill="{C["ok"]}" '
                   f'font-size="9" text-anchor="{anchor}" font-weight="700">{profit:.1f}</text>')
        # 净利润 YoY
        if profit_yoy[i] is not None:
            yoy_color = C["red_candle"] if profit_yoy[i] >= 0 else C["green_candle"]
            yoy_sign = "+" if profit_yoy[i] >= 0 else ""
            svg.append(f'<text x="{cx + label_offset_x:.1f}" y="{py + 10:.1f}" fill="{yoy_color}" '
                       f'font-size="7.5" text-anchor="{anchor}" opacity="0.85">'
                       f'{yoy_sign}{profit_yoy[i]:.0f}%</text>')
        # X轴年份
        svg.append(f'<text x="{cx:.1f}" y="{H-15:.1f}" fill="{C["muted"]}" '
                   f'font-size="11" text-anchor="middle" font-weight="600">{year}</text>')

    # 轴标签
    svg.append(f'<text x="{PL}" y="{PT-18}" fill="{C["blue"]}" '
               f'font-size="11" font-weight="600">营收(亿)</text>')
    svg.append(f'<text x="{W-PR}" y="{PT-18}" fill="{C["ok"]}" '
               f'font-size="11" font-weight="600" text-anchor="end">净利润(亿)</text>')

    # 图例
    lx = W / 2 - 90
    ly = PT - 32
    svg.append(f'<rect x="{lx}" y="{ly}" width="14" height="10" rx="2" fill="url(#revBarGrad)"/>')
    svg.append(f'<text x="{lx+18}" y="{ly+9}" fill="{C["muted"]}" font-size="10">营收(柱)</text>')
    svg.append(f'<line x1="{lx+85}" y1="{ly+5}" x2="{lx+103}" y2="{ly+5}" '
               f'stroke="{C["ok"]}" stroke-width="2.5"/>')
    svg.append(f'<circle cx="{lx+94}" cy="{ly+5}" r="3" fill="{C["ok"]}"/>')
    svg.append(f'<text x="{lx+107}" y="{ly+9}" fill="{C["muted"]}" font-size="10">净利润(线)</text>')

    svg.append('</svg>')

    return wrap_chart_card(
        '\n'.join(svg),
        "年度营收与净利润趋势（2018-2025）",
        "柱=营收(左轴) | 线=净利润(右轴) | 标注=YoY同比增速"
    )


# ============================================================
# 图表 4: 季度毛利率趋势
# ============================================================
def chart_gross_margin(fundamental_text):
    """季度毛利率折线+面积图"""
    tables = parse_md_table(fundamental_text, '报告期')
    # 取Q1-Q4的毛利率数据
    qtr_data = []
    for row in tables:
        period = row.get('报告期', '')
        typ = row.get('类型', '')
        gm = safe_float(row.get('毛利率', 0))
        if gm > 0 and period >= '2020' and typ in ('年报', 'Q3', '中报', 'Q1'):
            # 构建季度标签
            if typ == 'Q1' or period.endswith('-03-31'):
                qlabel = period[:4] + 'Q1'
            elif typ == '中报' or period.endswith('-06-30'):
                qlabel = period[:4] + 'Q2'
            elif typ == 'Q3' or period.endswith('-09-30'):
                qlabel = period[:4] + 'Q3'
            elif typ == '年报' or period.endswith('-12-31'):
                qlabel = period[:4] + 'Q4'
            else:
                continue
            qtr_data.append((qlabel, gm))

    qtr_data.sort(key=lambda x: x[0])
    # 去重，保留最后一个
    seen = {}
    for qlabel, gm in qtr_data:
        seen[qlabel] = gm
    qtr_data = sorted(seen.items())

    if len(qtr_data) < 4:
        return ''

    W, H = 860, 240
    PL, PR, PT, PB = 55, 30, 35, 50
    chart_w = W - PL - PR
    chart_h = H - PT - PB

    n = len(qtr_data)
    gm_min = min(d[1] for d in qtr_data) - 2
    gm_max = max(d[1] for d in qtr_data) + 2

    def xp(i):
        return PL + chart_w * i / (n - 1) if n > 1 else PL + chart_w / 2

    def yp(v):
        if gm_max == gm_min:
            return PT + chart_h / 2
        return PT + chart_h * (1 - (v - gm_min) / (gm_max - gm_min))

    svg = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="季度毛利率趋势">']

    # 网格
    ticks = 5
    for i in range(ticks + 1):
        yy = PT + chart_h * i / ticks
        val = gm_max - (gm_max - gm_min) * i / ticks
        svg.append(f'<line x1="{PL}" y1="{yy:.1f}" x2="{W-PR}" y2="{yy:.1f}" stroke="{C["grid_light"]}" stroke-width="0.5"/>')
        svg.append(f'<text x="{PL-5}" y="{yy+4:.1f}" fill="{C["muted"]}" font-size="10" text-anchor="end">{val:.1f}%</text>')

    # 渐变面积
    area_points = f'{xp(0):.1f},{PT + chart_h:.1f} '
    area_points += ' '.join(f'{xp(i):.1f},{yp(d[1]):.1f}' for i, d in enumerate(qtr_data))
    area_points += f' {xp(n-1):.1f},{PT + chart_h:.1f}'

    svg.append(f'<defs><linearGradient id="gmGrad" x1="0" y1="0" x2="0" y2="1">'
               f'<stop offset="0%" stop-color="{C["teal"]}" stop-opacity="0.3"/>'
               f'<stop offset="100%" stop-color="{C["teal"]}" stop-opacity="0.02"/>'
               f'</linearGradient></defs>')
    svg.append(f'<polygon points="{area_points}" fill="url(#gmGrad)"/>')

    # 折线
    line_points = ' '.join(f'{xp(i):.1f},{yp(d[1]):.1f}' for i, d in enumerate(qtr_data))
    svg.append(f'<polyline points="{line_points}" fill="none" stroke="{C["teal"]}" stroke-width="2.5" stroke-linejoin="round"/>')

    # 数据点+标签
    for i, (qlabel, gm) in enumerate(qtr_data):
        cx = xp(i)
        cy = yp(gm)
        svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.5" fill="{C["teal"]}" stroke="#fff" stroke-width="1"/>')
        # 只标注部分避免拥挤
        if i % 2 == 0 or i == n - 1:
            svg.append(f'<text x="{cx:.1f}" y="{cy-10:.1f}" fill="{C["teal"]}" font-size="9" text-anchor="middle" font-weight="600">{gm:.1f}%</text>')
        # X轴标签
        if i % 3 == 0 or i == n - 1:
            svg.append(f'<text x="{cx:.1f}" y="{H-15:.1f}" fill="{C["muted"]}" font-size="9" text-anchor="middle" transform="rotate(-30 {cx:.1f} {H-15:.1f})">{qlabel}</text>')

    svg.append(f'<text x="{PL}" y="{PT-12}" fill="{C["teal"]}" font-size="11" font-weight="600">毛利率(%)</text>')
    svg.append('</svg>')

    return wrap_chart_card(
        '\n'.join(svg),
        "季度毛利率趋势（2020-2025）",
        "综合毛利率(非单季) | 42%为2025年报水平"
    )


# ============================================================
# 图表 5: 三项现金流结构图
# ============================================================
def chart_cashflow(fundamental_text):
    """三项现金流年度柱状图"""
    # 解析现金流数据
    cf_data = []
    lines = fundamental_text.split('\n')
    in_cf = False
    headers = None
    for line in lines:
        if '现金流质量' in line:
            in_cf = True
            continue
        if in_cf and line.strip().startswith('|'):
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if headers is None:
                headers = cells
                continue
            if all(set(c) <= set('-: ') for c in cells):
                continue
            if len(cells) >= 4:
                row = dict(zip(headers, cells))
                cf_data.append(row)
        elif in_cf and line.strip().startswith('---'):
            if headers:
                break

    # 只取年报数据
    annual_cf = []
    for row in cf_data:
        period = row.get('报告期', '')
        if period.endswith('-12-31') and period >= '2019':
            year = period[:4]
            ocf = safe_float(row.get('经营净现金流(亿)', 0))
            icf = safe_float(row.get('投资净现金流(亿)', 0))
            fcf = safe_float(row.get('筹资净现金流(亿)', 0))
            annual_cf.append((year, ocf, icf, fcf))

    annual_cf.sort()
    if len(annual_cf) < 3:
        return ''

    W, H = 860, 280
    PL, PR, PT, PB = 55, 30, 35, 55
    chart_w = W - PL - PR
    chart_h = H - PT - PB

    n = len(annual_cf)
    all_vals = []
    for _, o, i, f in annual_cf:
        all_vals.extend([o, i, f])
    v_max = max(all_vals) * 1.15
    v_min = min(all_vals) * 1.15

    def yp(v):
        total_range = v_max - v_min
        if total_range == 0:
            return PT + chart_h / 2
        return PT + chart_h * (1 - (v - v_min) / total_range)

    group_w = chart_w / n
    bar_w = min(22, group_w * 0.25)

    svg = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="三项现金流结构">']

    # 零线
    y_zero = yp(0)
    svg.append(f'<line x1="{PL}" y1="{y_zero:.1f}" x2="{W-PR}" y2="{y_zero:.1f}" stroke="{C["line"]}" stroke-width="1.5"/>')

    # 网格
    for tick_val in range(-40, 121, 20):
        if v_min <= tick_val <= v_max:
            yy = yp(tick_val)
            svg.append(f'<line x1="{PL}" y1="{yy:.1f}" x2="{W-PR}" y2="{yy:.1f}" stroke="{C["grid_light"]}" stroke-width="0.5"/>')
            svg.append(f'<text x="{PL-5}" y="{yy+4:.1f}" fill="{C["muted"]}" font-size="10" text-anchor="end">{tick_val}</text>')

    # 柱子
    colors = [C["blue"], C["accent"], C["purple"]]
    labels_legend = ["经营", "投资", "筹资"]

    for i, (year, ocf, icf, fcf) in enumerate(annual_cf):
        cx = PL + group_w * (i + 0.5)
        vals = [ocf, icf, fcf]

        for j, v in enumerate(vals):
            bx = cx + (j - 1) * (bar_w + 3)
            if v >= 0:
                top = yp(v)
                bot = y_zero
            else:
                top = y_zero
                bot = yp(v)
            bh = abs(bot - top)
            svg.append(f'<rect x="{bx - bar_w/2:.1f}" y="{min(top,bot):.1f}" width="{bar_w:.1f}" height="{max(bh,1):.1f}" rx="2" fill="{colors[j]}" opacity="0.85"/>')
            # 数值
            label_y = min(top, bot) - 5 if v >= 0 else max(top, bot) + 12
            svg.append(f'<text x="{bx:.1f}" y="{label_y:.1f}" fill="{colors[j]}" font-size="8" text-anchor="middle">{v:.0f}</text>')

        # 年份
        svg.append(f'<text x="{cx:.1f}" y="{H-15:.1f}" fill="{C["muted"]}" font-size="11" text-anchor="middle">{year}</text>')

    # 图例
    for j, (label, color) in enumerate(zip(labels_legend, colors)):
        lx = W / 2 - 80 + j * 70
        svg.append(f'<rect x="{lx}" y="{PT-22}" width="12" height="8" rx="2" fill="{color}"/>')
        svg.append(f'<text x="{lx+16}" y="{PT-14}" fill="{C["muted"]}" font-size="10">{label}</text>')

    svg.append(f'<text x="{PL}" y="{PT-12}" fill="{C["text"]}" font-size="11" font-weight="600">单位：亿元</text>')
    svg.append('</svg>')

    return wrap_chart_card(
        '\n'.join(svg),
        "三项现金流年度结构（2019-2025）",
        "经营现金流(蓝) | 投资现金流(红) | 筹资现金流(紫)"
    )


# ============================================================
# 图表 6: FCF自由现金流趋势
# ============================================================
def chart_fcf(fundamental_text):
    """年度FCF折线+柱图"""
    # 解析FCF数据 — 用更精确的标题匹配
    fcf_data = []
    lines = fundamental_text.split('\n')
    in_fcf = False
    headers = None
    for line in lines:
        if '资本支出与自由现金流' in line:
            in_fcf = True
            headers = None  # 重置
            continue
        if not in_fcf:
            continue
        stripped = line.strip()
        if stripped.startswith('|'):
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            if headers is None:
                headers = cells
                continue
            if all(set(c) <= set('-: ') for c in cells):
                continue
            if len(cells) >= 3:
                row = dict(zip(headers, cells))
                fcf_data.append(row)
        elif stripped.startswith('---') or (stripped.startswith('#') and headers):
            break

    # 只取年报
    annual_fcf = []
    for row in fcf_data:
        period = row.get('报告期', '')
        if period.endswith('-12-31') and period >= '2019':
            year = period[:4]
            ocf = safe_float(row.get('经营现金流(亿)', 0))
            capex = safe_float(row.get('CAPEX(亿)', 0))
            fcf = safe_float(row.get('FCF(亿)', 0))
            annual_fcf.append((year, ocf, capex, fcf))

    annual_fcf.sort()
    if len(annual_fcf) < 3:
        return ''

    W, H = 860, 250
    PL, PR, PT, PB = 55, 30, 35, 50
    chart_w = W - PL - PR
    chart_h = H - PT - PB

    n = len(annual_fcf)
    all_vals = [d[3] for d in annual_fcf] + [d[0+1] for d in annual_fcf]
    v_max = max(all_vals) * 1.15
    v_min = min(min(all_vals), 0) * 1.15

    def yp(v):
        total = v_max - v_min
        if total == 0:
            return PT + chart_h / 2
        return PT + chart_h * (1 - (v - v_min) / total)

    def xp(i):
        return PL + chart_w * i / (n - 1) if n > 1 else PL + chart_w / 2

    svg = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="FCF趋势">']

    # 零线
    if v_min < 0:
        y_zero = yp(0)
        svg.append(f'<line x1="{PL}" y1="{y_zero:.1f}" x2="{W-PR}" y2="{y_zero:.1f}" stroke="{C["line"]}" stroke-width="1"/>')

    # 网格
    for i in range(5):
        yy = PT + chart_h * i / 4
        val = v_max - (v_max - v_min) * i / 4
        svg.append(f'<line x1="{PL}" y1="{yy:.1f}" x2="{W-PR}" y2="{yy:.1f}" stroke="{C["grid_light"]}" stroke-width="0.5"/>')
        svg.append(f'<text x="{PL-5}" y="{yy+4:.1f}" fill="{C["muted"]}" font-size="10" text-anchor="end">{val:.0f}</text>')

    bar_w = min(40, chart_w / n * 0.5)
    y_zero = yp(0)

    # 经营现金流柱子（浅色背景）
    for i, (year, ocf, capex, fcf) in enumerate(annual_fcf):
        cx = xp(i)
        h_bar = abs(yp(ocf) - y_zero)
        top = min(yp(ocf), y_zero)
        svg.append(f'<rect x="{cx - bar_w/2:.1f}" y="{top:.1f}" width="{bar_w:.1f}" height="{h_bar:.1f}" rx="3" fill="{C["blue"]}" opacity="0.25"/>')

    # FCF折线
    fcf_points = ' '.join(f'{xp(i):.1f},{yp(d[3]):.1f}' for i, d in enumerate(annual_fcf))
    svg.append(f'<polyline points="{fcf_points}" fill="none" stroke="{C["ok"]}" stroke-width="2.5" stroke-linejoin="round"/>')

    # 经营现金流折线
    ocf_points = ' '.join(f'{xp(i):.1f},{yp(d[1]):.1f}' for i, d in enumerate(annual_fcf))
    svg.append(f'<polyline points="{ocf_points}" fill="none" stroke="{C["blue"]}" stroke-width="2" stroke-dasharray="6 3"/>')

    # 数据点+标签
    for i, (year, ocf, capex, fcf) in enumerate(annual_fcf):
        cx = xp(i)
        # FCF点
        svg.append(f'<circle cx="{cx:.1f}" cy="{yp(fcf):.1f}" r="4" fill="{C["ok"]}" stroke="#fff" stroke-width="1"/>')
        svg.append(f'<text x="{cx:.1f}" y="{yp(fcf)-10:.1f}" fill="{C["ok"]}" font-size="9" text-anchor="middle" font-weight="600">{fcf:.1f}</text>')
        # OCF点
        svg.append(f'<circle cx="{cx:.1f}" cy="{yp(ocf):.1f}" r="3" fill="{C["blue"]}" stroke="#fff" stroke-width="1"/>')
        svg.append(f'<text x="{cx:.1f}" y="{yp(ocf)-10:.1f}" fill="{C["blue"]}" font-size="8" text-anchor="middle">{ocf:.0f}</text>')
        # X轴
        svg.append(f'<text x="{cx:.1f}" y="{H-15:.1f}" fill="{C["muted"]}" font-size="11" text-anchor="middle">{year}</text>')

    # 图例
    svg.append(f'<line x1="{W/2-90}" y1="{PT-18}" x2="{W/2-70}" y2="{PT-18}" stroke="{C["ok"]}" stroke-width="2.5"/>')
    svg.append(f'<text x="{W/2-65}" y="{PT-14}" fill="{C["muted"]}" font-size="10">FCF</text>')
    svg.append(f'<line x1="{W/2}" y1="{PT-18}" x2="{W/2+20}" y2="{PT-18}" stroke="{C["blue"]}" stroke-width="2" stroke-dasharray="4 2"/>')
    svg.append(f'<text x="{W/2+25}" y="{PT-14}" fill="{C["muted"]}" font-size="10">经营现金流</text>')

    svg.append('</svg>')

    return wrap_chart_card(
        '\n'.join(svg),
        "自由现金流(FCF)趋势（2019-2025）",
        "FCF = 经营现金流 - CAPEX | 2025年FCF 81亿创历史新高"
    )


# ============================================================
# 图表 7: PE/PB历史分位仪表盘
# ============================================================
def chart_valuation_gauge(fundamental_text):
    """PE/PB分位仪表盘 — 动态读取 fundamental.md 数据

    Parameters:
        fundamental_text:  fundamental.md 原始文本
    """
    # ---------- 从 fundamental.md 解析估值分位数据 ----------
    pe_current = _safe_float(_parse_fundamental_kv(fundamental_text, "## 估值历史分位", "当前PE(TTM)"), 0)
    pe_pct = _safe_float(_parse_fundamental_kv(fundamental_text, "## 估值历史分位", "PE历史分位"), 50)
    pb_current = _safe_float(_parse_fundamental_kv(fundamental_text, "## 估值历史分位", "当前PB(MRQ)"), 0)
    pb_pct = _safe_float(_parse_fundamental_kv(fundamental_text, "## 估值历史分位", "PB历史分位"), 50)
    ps_current = _safe_float(_parse_fundamental_kv(fundamental_text, "## 估值历史分位", "当前PS(TTM)"), 0)
    dividend_yield = _safe_float(_parse_fundamental_kv(fundamental_text, "## 股息率", "当前股息率"), 0)
    data_points = _parse_fundamental_kv(fundamental_text, "## 估值历史分位", "数据点数") or "1250"

    # 解析 PE/PB 区间 (格式: "15.4 ~ 108.6")
    pe_range_str = _parse_fundamental_kv(fundamental_text, "## 估值历史分位", "PE区间") or ""
    pb_range_str = _parse_fundamental_kv(fundamental_text, "## 估值历史分位", "PB区间") or ""

    def _parse_range(s):
        parts = re.split(r'[~～\-–—]', s.replace(' ', ''))
        if len(parts) == 2:
            lo = _safe_float(parts[0])
            hi = _safe_float(parts[1])
            if lo is not None and hi is not None:
                return lo, hi
        return 0, 100

    pe_min, pe_max = _parse_range(pe_range_str)
    pb_min, pb_max = _parse_range(pb_range_str)

    # 如果数据全为 0，说明解析失败，返回空
    if pe_current == 0 and pb_current == 0:
        print("  ⚠️ 无法从 fundamental.md 解析估值分位数据")
        return ''

    W, H = 860, 220
    gauge_r = 75
    cx1, cx2 = W * 0.28, W * 0.72
    cy = 140

    def arc_path(cx, cy, r, start_angle, end_angle, large=0):
        sa = math.radians(start_angle)
        ea = math.radians(end_angle)
        x1 = cx + r * math.cos(sa)
        y1 = cy + r * math.sin(sa)
        x2 = cx + r * math.cos(ea)
        y2 = cy + r * math.sin(ea)
        sweep = 1
        return f'M {x1:.1f} {y1:.1f} A {r} {r} 0 {large} {sweep} {x2:.1f} {y2:.1f}'

    svg = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="估值分位仪表盘">']

    for idx, (cx, label, val, pct, vmin, vmax, unit) in enumerate([
        (cx1, "PE(TTM)", pe_current, pe_pct, pe_min, pe_max, "x"),
        (cx2, "PB", pb_current, pb_pct, pb_min, pb_max, "x"),
    ]):
        start_deg = 180
        end_deg = 360
        svg.append(f'<path d="{arc_path(cx, cy, gauge_r, start_deg, end_deg, 1)}" fill="none" stroke="{C["grid_light"]}" stroke-width="14" stroke-linecap="round"/>')

        seg_colors = [(C["ok"], 0, 30), (C["warn"], 30, 70), (C["accent"], 70, 100)]
        for color, s, e in seg_colors:
            sa = start_deg + (end_deg - start_deg) * s / 100
            ea = start_deg + (end_deg - start_deg) * e / 100
            svg.append(f'<path d="{arc_path(cx, cy, gauge_r, sa, ea, 0)}" fill="none" stroke="{color}" stroke-width="14" stroke-linecap="butt" opacity="0.4"/>')

        needle_angle = start_deg + (end_deg - start_deg) * min(pct, 100) / 100
        na = math.radians(needle_angle)
        nx = cx + (gauge_r - 5) * math.cos(na)
        ny = cy + (gauge_r - 5) * math.sin(na)
        svg.append(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="{C["text"]}" stroke-width="2.5" stroke-linecap="round"/>')
        svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{C["text"]}"/>')
        svg.append(f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="4" fill="{C["accent"]}"/>')

        color = C["accent"] if pct >= 70 else (C["warn"] if pct >= 30 else C["ok"])
        svg.append(f'<text x="{cx:.1f}" y="{cy+5:.1f}" fill="{color}" font-size="26" font-weight="700" text-anchor="middle">{val:.1f}{unit}</text>')
        svg.append(f'<text x="{cx:.1f}" y="{cy+25:.1f}" fill="{C["muted"]}" font-size="12" text-anchor="middle">{label}</text>')

        pct_color = C["accent"] if pct >= 80 else C["warn"]
        svg.append(f'<text x="{cx:.1f}" y="{cy+42:.1f}" fill="{pct_color}" font-size="13" font-weight="700" text-anchor="middle">{pct:.0f}% 历史分位</text>')
        svg.append(f'<text x="{cx - gauge_r:.1f}" y="{cy+15:.1f}" fill="{C["muted"]}" font-size="9" text-anchor="middle">{vmin}</text>')
        svg.append(f'<text x="{cx + gauge_r:.1f}" y="{cy+15:.1f}" fill="{C["muted"]}" font-size="9" text-anchor="middle">{vmax}</text>')

    svg.append(f'<text x="{W/2}" y="28" fill="{C["text"]}" font-size="14" font-weight="700" text-anchor="middle">估值历史分位</text>')
    svg.append(f'<text x="{W/2}" y="46" fill="{C["muted"]}" font-size="11" text-anchor="middle">基于{data_points}个交易日数据 | 指针越偏右=越贵</text>')

    ps_str = f"PS(TTM) = {ps_current:.2f}x" if ps_current else "PS 数据缺失"
    div_str = f"股息率 = {dividend_yield:.2f}%" if dividend_yield else "股息率数据缺失"
    svg.append(f'<text x="{W/2}" y="{H-10:.1f}" fill="{C["muted"]}" font-size="10" text-anchor="middle">{ps_str} | {div_str}</text>')

    svg.append('</svg>')

    # 动态生成副标题
    def _val_label(pct):
        if pct >= 80: return "极度高估"
        if pct >= 60: return "偏高估"
        if pct >= 40: return "合理"
        if pct >= 20: return "偏低估"
        return "极度低估"

    subtitle = f"PE {pe_pct:.0f}%分位 | PB {pb_pct:.0f}%分位 — {_val_label(max(pe_pct, pb_pct))}（历史{'顶部' if max(pe_pct, pb_pct) >= 80 else '底部' if max(pe_pct, pb_pct) <= 20 else '中部'}区域）"

    return wrap_chart_card(
        '\n'.join(svg),
        "估值历史分位仪表盘",
        subtitle
    )


# ============================================================
# 图表 8: 同业对比柱状图（PE / PB / ROE / 毛利率）
# ============================================================
def chart_peer_comparison(fundamental_text, peer_data=None):
    """同业对比柱状图 — 标的 vs 3-5 个行业可比公司在 PE/PB/ROE/毛利率四个维度

    Parameters:
        fundamental_text: fundamental.md 原始文本（用于提取标的自身数据）
        peer_data: list[dict] — 可比公司数据，格式:
                   [{"name": "新易盛", "pe": 18, "pb": 3.5, "roe": 25, "gm": 30},
                    {"name": "天孚通信", "pe": 25, ...},
                    ...]
                   若为 None，返回空字符串（需由渲染 pipeline 事先准备数据）
    """
    if not peer_data or len(peer_data) == 0:
        return ''

    # 提取标的自身数据
    self_name = "标的"
    # 从 fundamental.md 标题行提取简称：## 标的：XX (300308)
    m = re.search(r'标的[：:]\s*([^\s(（]+)', fundamental_text)
    if m:
        self_name = m.group(1).strip()

    self_pe = _safe_float(_parse_fundamental_kv(fundamental_text, "## 实时估值", "PE(TTM)"))
    self_pb = _safe_float(_parse_fundamental_kv(fundamental_text, "## 实时估值", "PB"))

    # 提取最新年报 ROE / 毛利率
    self_roe = None
    self_gm = None
    for line in fundamental_text.split('\n'):
        if '| ' in line and '年报' in line:
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if len(cells) >= 9:
                self_roe = _safe_float(cells[7].replace('%', ''))
                self_gm = _safe_float(cells[8].replace('%', ''))
                break

    # 拼装所有公司数据：标的 + 可比
    all_companies = [{
        "name": self_name,
        "pe": self_pe,
        "pb": self_pb,
        "roe": self_roe,
        "gm": self_gm,
        "is_self": True,
    }]
    for p in peer_data:
        all_companies.append({
            "name": str(p.get("name", "?"))[:6],
            "pe": _safe_float(p.get("pe")),
            "pb": _safe_float(p.get("pb")),
            "roe": _safe_float(p.get("roe")),
            "gm": _safe_float(p.get("gm")),
            "is_self": False,
        })

    # 四个指标维度
    dims = [
        ("PE(TTM)", "pe", "x", C["blue"]),
        ("PB", "pb", "x", C["purple"]),
        ("ROE", "roe", "%", C["ok"]),
        ("毛利率", "gm", "%", C["teal"]),
    ]

    n_companies = len(all_companies)
    W = 860
    subchart_h = 130
    H = 40 + 4 * (subchart_h + 10) + 20  # 4 个维度纵向堆叠
    PL, PR = 90, 40
    chart_w = W - PL - PR

    svg = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
           f'role="img" aria-label="同业对比" style="font-family:system-ui,sans-serif">']

    svg.append(f'<text x="{W/2}" y="24" fill="{C["text"]}" font-size="14" '
               f'font-weight="700" text-anchor="middle">同业对比（{self_name} vs {len(peer_data)} 家可比）</text>')

    for d_idx, (dim_label, dim_key, unit, color) in enumerate(dims):
        y_top = 40 + d_idx * (subchart_h + 10)
        # 维度标题
        svg.append(f'<text x="{PL}" y="{y_top + 12}" fill="{color}" '
                   f'font-size="11" font-weight="700">{dim_label}</text>')

        vals = [(co["name"], co.get(dim_key), co["is_self"]) for co in all_companies]
        valid_vals = [v for _, v, _ in vals if v is not None]
        if not valid_vals:
            continue
        v_max = max(valid_vals) * 1.15
        v_min = min(0, min(valid_vals))  # 含负值时下限为负

        # 轴范围
        def yp(v, y_top=y_top):
            base = y_top + subchart_h - 20
            top = y_top + 20
            range_total = v_max - v_min
            if range_total == 0:
                return (base + top) / 2
            return top + (base - top) * (v_max - v) / range_total

        # 零线
        if v_min < 0:
            y_zero = yp(0)
            svg.append(f'<line x1="{PL}" y1="{y_zero:.1f}" x2="{W-PR}" y2="{y_zero:.1f}" '
                       f'stroke="{C["line"]}" stroke-width="0.8"/>')

        # 柱子
        group_w = chart_w / n_companies
        bar_w = min(42, group_w * 0.5)
        for i, (name, val, is_self) in enumerate(vals):
            cx = PL + group_w * (i + 0.5)
            if val is None:
                svg.append(f'<text x="{cx:.1f}" y="{y_top + subchart_h - 25:.1f}" '
                           f'fill="{C["muted"]}" font-size="9" text-anchor="middle">N/A</text>')
                svg.append(f'<text x="{cx:.1f}" y="{y_top + subchart_h - 5:.1f}" '
                           f'fill="{C["muted"]}" font-size="9" text-anchor="middle">{name}</text>')
                continue

            h_bar = abs(yp(val) - yp(0) if v_min < 0 else (y_top + subchart_h - 20) - yp(val))
            if v_min < 0 and val < 0:
                bar_top = yp(0)
            else:
                bar_top = yp(val)

            # 标的用强调色（accent），可比用维度色 + 半透明
            bar_color = C["accent"] if is_self else color
            bar_opacity = "1.0" if is_self else "0.55"
            stroke = f'stroke="{C["text"]}" stroke-width="1.5"' if is_self else ''
            svg.append(f'<rect x="{cx - bar_w/2:.1f}" y="{bar_top:.1f}" '
                       f'width="{bar_w:.1f}" height="{max(h_bar, 1):.1f}" rx="3" '
                       f'fill="{bar_color}" opacity="{bar_opacity}" {stroke}/>')
            # 数值
            label_y = bar_top - 4 if val >= 0 else bar_top + h_bar + 12
            svg.append(f'<text x="{cx:.1f}" y="{label_y:.1f}" fill="{bar_color}" '
                       f'font-size="10" text-anchor="middle" font-weight="700">'
                       f'{val:.1f}{unit}</text>')
            # 公司名
            name_color = C["accent"] if is_self else C["muted"]
            name_weight = "700" if is_self else "400"
            svg.append(f'<text x="{cx:.1f}" y="{y_top + subchart_h - 5:.1f}" '
                       f'fill="{name_color}" font-size="9" text-anchor="middle" '
                       f'font-weight="{name_weight}">{name}</text>')

    svg.append('</svg>')

    return wrap_chart_card(
        '\n'.join(svg),
        "同业对比（四维度）",
        f"{self_name}（红色强调）vs 行业可比公司 | PE / PB / ROE / 毛利率"
    )


# ============================================================
# 图表 9: 胜率/赔率综合仪表盘
# ============================================================
def chart_winrate_dashboard(winrate_data):
    """胜率/赔率综合仪表盘 — 六维加权胜率 + 收益风险比 + 三情景概率

    Parameters:
        winrate_data: dict — 格式:
            {
                "dimensions": [  # 6 个维度的评分（0-100）
                    {"name": "基本面", "score": 85, "weight": 0.25},
                    {"name": "政策面", "score": 70, "weight": 0.10},
                    {"name": "技术面", "score": 60, "weight": 0.20},
                    {"name": "资金面", "score": 75, "weight": 0.15},
                    {"name": "筹码面", "score": 55, "weight": 0.15},
                    {"name": "消息面", "score": 65, "weight": 0.15},
                ],
                "composite_winrate": 70,  # 综合胜率百分比
                "risk_reward": 2.8,        # 收益风险比
                "scenarios": {             # 三情景概率
                    "bull": {"prob": 30, "target": 145},
                    "base": {"prob": 50, "target": 120},
                    "bear": {"prob": 20, "target": 85},
                }
            }
        若任何关键字段缺失，返回空字符串
    """
    if not winrate_data:
        return ''
    dims = winrate_data.get("dimensions") or []
    composite = _safe_float(winrate_data.get("composite_winrate"))
    rr = _safe_float(winrate_data.get("risk_reward"))
    scenarios = winrate_data.get("scenarios") or {}
    if not dims or composite is None:
        return ''

    W, H = 860, 320
    svg = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
           f'role="img" aria-label="胜率赔率仪表盘" style="font-family:system-ui,sans-serif">']

    svg.append(f'<text x="{W/2}" y="28" fill="{C["text"]}" font-size="14" '
               f'font-weight="700" text-anchor="middle">胜率 / 赔率综合仪表盘</text>')

    # === 左侧: 六维加权胜率柱图 ===
    left_x0, left_w = 30, 360
    left_y0 = 60
    bar_total_h = 200
    # 背景
    svg.append(f'<rect x="{left_x0}" y="{left_y0 - 10}" width="{left_w}" '
               f'height="{bar_total_h + 50}" rx="6" fill="{C["panel"]}" '
               f'stroke="{C["line"]}" stroke-width="0.5"/>')
    svg.append(f'<text x="{left_x0 + 10}" y="{left_y0 + 5}" fill="{C["muted"]}" '
               f'font-size="11" font-weight="600">六维加权胜率</text>')

    n_dims = len(dims)
    bar_group_w = (left_w - 40) / n_dims
    bar_w = min(36, bar_group_w * 0.55)
    bars_y_base = left_y0 + bar_total_h + 10

    for i, d in enumerate(dims):
        name = str(d.get("name", ""))[:4]
        score = _safe_float(d.get("score"), 0)
        weight = _safe_float(d.get("weight"), 0)
        cx = left_x0 + 20 + bar_group_w * (i + 0.5)
        h_bar = bar_total_h * min(score / 100, 1.0)
        bar_top = bars_y_base - h_bar

        # 根据分数着色
        if score >= 75:
            bcolor = C["ok"]
        elif score >= 50:
            bcolor = C["warn"]
        else:
            bcolor = C["accent"]

        svg.append(f'<rect x="{cx - bar_w/2:.1f}" y="{bar_top:.1f}" '
                   f'width="{bar_w:.1f}" height="{max(h_bar, 1):.1f}" rx="3" '
                   f'fill="{bcolor}" opacity="0.85"/>')
        # 分数
        svg.append(f'<text x="{cx:.1f}" y="{bar_top - 4:.1f}" fill="{bcolor}" '
                   f'font-size="10" text-anchor="middle" font-weight="700">{score:.0f}</text>')
        # 维度名
        svg.append(f'<text x="{cx:.1f}" y="{bars_y_base + 14:.1f}" fill="{C["text"]}" '
                   f'font-size="9" text-anchor="middle">{name}</text>')
        # 权重
        svg.append(f'<text x="{cx:.1f}" y="{bars_y_base + 26:.1f}" fill="{C["muted"]}" '
                   f'font-size="8" text-anchor="middle">w={weight:.0%}</text>')

    # === 右侧上: 综合胜率大数 ===
    right_x0 = 430
    right_w = 400
    top_card_h = 130

    # 综合胜率卡片
    cr_color = C["ok"] if composite >= 70 else (C["warn"] if composite >= 50 else C["accent"])
    svg.append(f'<rect x="{right_x0}" y="{left_y0 - 10}" width="{right_w}" '
               f'height="{top_card_h}" rx="6" fill="{C["panel"]}" '
               f'stroke="{cr_color}" stroke-width="1.5"/>')
    svg.append(f'<text x="{right_x0 + 10}" y="{left_y0 + 5}" fill="{C["muted"]}" '
               f'font-size="11" font-weight="600">综合胜率</text>')
    svg.append(f'<text x="{right_x0 + 100}" y="{left_y0 + 75}" fill="{cr_color}" '
               f'font-size="56" font-weight="700" text-anchor="middle">{composite:.0f}</text>')
    svg.append(f'<text x="{right_x0 + 145}" y="{left_y0 + 75}" fill="{C["muted"]}" '
               f'font-size="18" font-weight="500">%</text>')

    # 收益风险比
    if rr is not None:
        rr_color = C["ok"] if rr >= 2.5 else (C["warn"] if rr >= 1.5 else C["accent"])
        svg.append(f'<text x="{right_x0 + 260}" y="{left_y0 + 30}" fill="{C["muted"]}" '
                   f'font-size="11" font-weight="600">收益风险比</text>')
        svg.append(f'<text x="{right_x0 + 310}" y="{left_y0 + 72}" fill="{rr_color}" '
                   f'font-size="38" font-weight="700" text-anchor="middle">{rr:.1f}</text>')
        svg.append(f'<text x="{right_x0 + 310}" y="{left_y0 + 92}" fill="{C["muted"]}" '
                   f'font-size="10" text-anchor="middle">:1</text>')

    # === 右侧下: 三情景概率条 ===
    scenario_y = left_y0 + top_card_h + 10
    scenario_h = 120
    svg.append(f'<rect x="{right_x0}" y="{scenario_y}" width="{right_w}" '
               f'height="{scenario_h}" rx="6" fill="{C["panel"]}" '
               f'stroke="{C["line"]}" stroke-width="0.5"/>')
    svg.append(f'<text x="{right_x0 + 10}" y="{scenario_y + 16}" fill="{C["muted"]}" '
               f'font-size="11" font-weight="600">三情景概率 × 目标价</text>')

    labels = [("bull", "乐观", C["ok"]), ("base", "基准", C["warn"]), ("bear", "悲观", C["accent"])]
    sc_bar_y = scenario_y + 32
    sc_bar_h = 24
    sc_x0 = right_x0 + 20
    sc_w_total = right_w - 40

    total_prob = sum(_safe_float(scenarios.get(k, {}).get("prob"), 0) for k, _, _ in labels)
    if total_prob > 0:
        cursor_x = sc_x0
        for k, lbl, col in labels:
            sc = scenarios.get(k, {})
            prob = _safe_float(sc.get("prob"), 0)
            target = _safe_float(sc.get("target"))
            seg_w = sc_w_total * prob / total_prob
            svg.append(f'<rect x="{cursor_x:.1f}" y="{sc_bar_y}" '
                       f'width="{seg_w:.1f}" height="{sc_bar_h}" '
                       f'fill="{col}" opacity="0.8"/>')
            svg.append(f'<text x="{cursor_x + seg_w/2:.1f}" y="{sc_bar_y + 16}" '
                       f'fill="#fff" font-size="11" text-anchor="middle" '
                       f'font-weight="700">{lbl} {prob:.0f}%</text>')
            # 目标价（下方）
            target_str = f"目标 {target:.0f}" if target else "—"
            svg.append(f'<text x="{cursor_x + seg_w/2:.1f}" y="{sc_bar_y + sc_bar_h + 18}" '
                       f'fill="{col}" font-size="10" text-anchor="middle" '
                       f'font-weight="600">{target_str}</text>')
            cursor_x += seg_w

    svg.append('</svg>')

    # 副标题
    _composite_label = "高胜率" if composite >= 70 else ("中性" if composite >= 50 else "低胜率")
    _rr_label = f"收益风险比 {rr:.1f}" if rr else ""
    subtitle_parts = [f"综合胜率 {composite:.0f}%（{_composite_label}）"]
    if _rr_label:
        subtitle_parts.append(_rr_label)
    subtitle_parts.append("权重和 = " + f"{sum(_safe_float(d.get('weight'), 0) for d in dims):.0%}")

    return wrap_chart_card(
        '\n'.join(svg),
        "胜率 / 赔率综合仪表盘",
        " | ".join(subtitle_parts),
    )


# ============================================================
# 图表 10: PE/PB-Band 历史估值带（P0-4 新增 2026-05）
# ============================================================
def chart_pe_band(fundamental_text):
    """PE-Band / PB-Band 5 档分位带 + 当前位置标注。

    数据来源：报告 §2.5-B0 渲染前需先在 fundamental.md 或 _fundamental.json 中提供
    `pe_band` / `pb_band` 字段，包含历史 PE-TTM/PB-LF 时间序列（[(date, pe), ...]）+
    当前值。若数据缺失，返回空串触发 [skip]。
    """
    # 优先从 fundamental.md 中的 "PE-Band 历史 5 年分位表" 解析 5 档分位
    # 表头："分位档 | PE 估值 | 对应隐含股价 | vs 当前 | 历史触发期"
    pe_rows = []
    pb_rows = []
    cur_pe = cur_pb = cur_price = None
    pe_section = pb_section = False
    headers = None
    for line in fundamental_text.split('\n'):
        s = line.strip()
        if 'PE-Band' in s or 'PE/PB-Band' in s:
            pe_section, pb_section = True, False
            headers = None
            continue
        if 'PB-Band' in s:
            pe_section, pb_section = False, True
            headers = None
            continue
        if not (pe_section or pb_section):
            continue
        if s.startswith('|'):
            cells = [c.strip().lstrip('*').rstrip('*').strip() for c in s.split('|')[1:-1]]
            if headers is None:
                headers = cells
                continue
            if all(set(c) <= set('-: ') for c in cells):
                continue
            if len(cells) >= 3:
                row = dict(zip(headers, cells))
                if pe_section:
                    pe_rows.append(row)
                else:
                    pb_rows.append(row)
        elif s.startswith('#') and headers:
            pe_section = pb_section = False
            headers = None

    def _num(x):
        try:
            return float(re.sub(r'[^\d.\-]', '', str(x)))
        except Exception:
            return None

    # 抽取 5 档分位 + 当前
    def _parse_band(rows):
        bands, cur = [], None
        for r in rows:
            key = (r.get('分位档') or r.get('档位') or list(r.values())[0]).strip()
            val = _num(r.get('PE 估值') or r.get('PB倍数') or r.get('PE') or list(r.values())[1] if len(r) > 1 else None)
            price = _num(r.get('对应隐含股价') or r.get('对应价格') or '')
            if val is None:
                continue
            if '当前' in key:
                cur = (val, price)
            else:
                bands.append((key, val))
        return bands, cur

    pe_bands, pe_cur = _parse_band(pe_rows)
    pb_bands, pb_cur = _parse_band(pb_rows)

    if len(pe_bands) < 3 or pe_cur is None:
        return ''  # 数据不足，跳过

    # 画 PE-Band 一张图（PB 共用同结构，作为补充信息列在右侧标注）
    W, H = 860, 280
    PL, PR, PT, PB = 70, 100, 30, 60
    chart_w = W - PL - PR
    chart_h = H - PT - PB

    vals = [v for _, v in pe_bands] + [pe_cur[0]]
    v_max = max(vals) * 1.15
    v_min = min(min(vals) * 0.85, 0)

    def yp(v):
        if v_max == v_min:
            return PT + chart_h / 2
        return PT + chart_h * (1 - (v - v_min) / (v_max - v_min))

    svg = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="PE-Band 历史估值带">']

    # 5 档分位带（不同颜色填充）
    band_colors = [
        ("最高", "#ffe8e6", C["accent"]),       # 红
        ("75",   "#fff5e1", C["warn"]),
        ("50",   "#e8f4ff", C["blue"]),
        ("25",   "#e8f7ee", C["ok"]),
        ("最低", "#f0f4f8", C["muted"]),
    ]

    # 按 PE 值降序排列分位（最高在上）
    sorted_bands = sorted(pe_bands, key=lambda x: -x[1])
    prev_y = PT
    for i, (label, val) in enumerate(sorted_bands):
        cur_y = yp(val)
        fill, line_color = (band_colors[i % len(band_colors)][1], band_colors[i % len(band_colors)][2])
        svg.append(f'<rect x="{PL}" y="{prev_y:.1f}" width="{chart_w}" height="{max(0, cur_y - prev_y):.1f}" fill="{fill}" opacity="0.55"/>')
        svg.append(f'<line x1="{PL}" y1="{cur_y:.1f}" x2="{PL+chart_w}" y2="{cur_y:.1f}" stroke="{line_color}" stroke-width="1.5" stroke-dasharray="5 3"/>')
        svg.append(f'<text x="{PL+chart_w+8}" y="{cur_y+4:.1f}" fill="{line_color}" font-size="11" font-weight="600">{label}: {val:.1f}x</text>')
        prev_y = cur_y

    # X 轴：5 档分位档名
    svg.append(f'<line x1="{PL}" y1="{PT+chart_h}" x2="{PL+chart_w}" y2="{PT+chart_h}" stroke="{C["line"]}" stroke-width="1"/>')

    # 当前 PE 点（用一根竖线 + 标签）
    cx = PL + chart_w * 0.5
    cy = yp(pe_cur[0])
    svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="{C["accent"]}" stroke="#fff" stroke-width="2"/>')
    svg.append(f'<text x="{cx:.1f}" y="{cy-12:.1f}" fill="{C["accent"]}" font-size="12" font-weight="700" text-anchor="middle">当前 PE: {pe_cur[0]:.1f}x</text>')

    # Y 轴标签
    for i in range(5):
        yy = PT + chart_h * i / 4
        val = v_max - (v_max - v_min) * i / 4
        svg.append(f'<text x="{PL-8}" y="{yy+4:.1f}" fill="{C["muted"]}" font-size="10" text-anchor="end">{val:.0f}x</text>')

    # 标题与说明
    svg.append(f'<text x="{PL}" y="{H-25}" fill="{C["muted"]}" font-size="11">PE-TTM 历史 5 档分位 + 当前位置（向右拖拽对应隐含股价档位）</text>')
    if pb_cur:
        svg.append(f'<text x="{PL}" y="{H-10}" fill="{C["muted"]}" font-size="11">PB-LF 当前: {pb_cur[0]:.2f}x（与 PE 形成估值双视角）</text>')

    svg.append('</svg>')

    return wrap_chart_card(
        '\n'.join(svg),
        "PE-Band 历史 5 年估值带",
        f"5 档分位线 + 当前 PE-TTM {pe_cur[0]:.1f}x 标注"
    )


# ============================================================
# 图表 11: 股价走势 vs 沪深 300 超额收益（P0-5 新增 2026-05）
# ============================================================
def chart_price_excess(stock_kline, hs300_kline):
    """近 250 日股价归一化走势 vs 沪深 300 双线图 + 累计超额收益面积。

    stock_kline / hs300_kline：list of dict，每项含"日期"/"收盘"。
    渲染：左轴归一化（起点=100）的两条线，右轴累计超额收益（个股−沪深300 同期收益）。
    """
    def _parse(records):
        out = []
        for r in records or []:
            d = r.get('日期') or r.get('date')
            c = r.get('收盘') or r.get('close')
            try:
                c = float(c)
            except Exception:
                continue
            if d and c > 0:
                out.append((d, c))
        out.sort(key=lambda x: x[0])
        return out

    s = _parse(stock_kline)
    h = _parse(hs300_kline)
    if len(s) < 30 or len(h) < 30:
        return ''

    # 按日期内联对齐
    h_map = {d: c for d, c in h}
    pairs = [(d, c, h_map[d]) for d, c in s if d in h_map]
    if len(pairs) < 30:
        return ''

    # 取最近 250 个交易日
    pairs = pairs[-250:]
    s0, h0 = pairs[0][1], pairs[0][2]
    norm_s = [(d, c / s0 * 100, h_c / h0 * 100) for d, c, h_c in pairs]
    # 超额收益（累计）
    excess = [(d, (c / s0 - h_c / h0) * 100) for d, c, h_c in [(p[0], p[1], p[2]) for p in pairs]]

    W, H = 860, 300
    PL, PR, PT, PB = 55, 55, 30, 60
    chart_w = W - PL - PR
    chart_h = H - PT - PB

    all_norm = [v for _, sv, hv in norm_s for v in (sv, hv)]
    v_max = max(all_norm) * 1.05
    v_min = min(all_norm) * 0.95

    all_excess = [e for _, e in excess]
    e_max = max(all_excess + [0]) * 1.15 or 10
    e_min = min(all_excess + [0]) * 1.15 or -10

    n = len(pairs)

    def xp(i):
        return PL + chart_w * i / (n - 1) if n > 1 else PL + chart_w / 2

    def yp(v):
        if v_max == v_min:
            return PT + chart_h / 2
        return PT + chart_h * (1 - (v - v_min) / (v_max - v_min))

    def yp_e(v):
        if e_max == e_min:
            return PT + chart_h / 2
        return PT + chart_h * (1 - (v - e_min) / (e_max - e_min))

    svg = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="股价 vs 沪深300">']

    # 网格
    for i in range(5):
        yy = PT + chart_h * i / 4
        val = v_max - (v_max - v_min) * i / 4
        svg.append(f'<line x1="{PL}" y1="{yy:.1f}" x2="{PL+chart_w}" y2="{yy:.1f}" stroke="{C["grid_light"]}" stroke-width="0.5"/>')
        svg.append(f'<text x="{PL-6}" y="{yy+4:.1f}" fill="{C["muted"]}" font-size="10" text-anchor="end">{val:.0f}</text>')
        e_val = e_max - (e_max - e_min) * i / 4
        svg.append(f'<text x="{PL+chart_w+6}" y="{yy+4:.1f}" fill="{C["accent"]}" font-size="10">{e_val:+.1f}%</text>')

    # 100 基准线
    svg.append(f'<line x1="{PL}" y1="{yp(100):.1f}" x2="{PL+chart_w}" y2="{yp(100):.1f}" stroke="{C["muted"]}" stroke-width="1" stroke-dasharray="4 3"/>')

    # 超额收益面积（淡红）
    excess_pts = [(xp(i), yp_e(e)) for i, (_, e) in enumerate(excess)]
    zero_y = yp_e(0)
    path_d = f'M {excess_pts[0][0]:.1f} {zero_y:.1f}'
    for x, y in excess_pts:
        path_d += f' L {x:.1f} {y:.1f}'
    path_d += f' L {excess_pts[-1][0]:.1f} {zero_y:.1f} Z'
    svg.append(f'<path d="{path_d}" fill="{C["accent"]}" opacity="0.10"/>')
    svg.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in excess_pts)}" fill="none" stroke="{C["accent"]}" stroke-width="1.5" stroke-dasharray="3 2"/>')

    # 个股归一化线
    stock_pts = ' '.join(f'{xp(i):.1f},{yp(sv):.1f}' for i, (_, sv, _) in enumerate(norm_s))
    svg.append(f'<polyline points="{stock_pts}" fill="none" stroke="{C["accent"]}" stroke-width="2.5" stroke-linejoin="round"/>')

    # 沪深300 归一化线
    hs_pts = ' '.join(f'{xp(i):.1f},{yp(hv):.1f}' for i, (_, _, hv) in enumerate(norm_s))
    svg.append(f'<polyline points="{hs_pts}" fill="none" stroke="{C["blue"]}" stroke-width="2"/>')

    # 终点标注
    last = norm_s[-1]
    svg.append(f'<text x="{PL+chart_w+4}" y="{yp(last[1]):.1f}" fill="{C["accent"]}" font-size="11" font-weight="700">{last[1]:.0f}</text>')
    svg.append(f'<text x="{PL+chart_w+4}" y="{yp(last[2])+12:.1f}" fill="{C["blue"]}" font-size="11" font-weight="600">{last[2]:.0f}</text>')

    # X 轴日期（首/中/末三个）
    date_idxs = [0, n // 2, n - 1]
    for i in date_idxs:
        svg.append(f'<text x="{xp(i):.1f}" y="{H-30}" fill="{C["muted"]}" font-size="10" text-anchor="middle">{pairs[i][0]}</text>')

    # 图例
    legend_y = H - 12
    svg.append(f'<line x1="{PL}" y1="{legend_y-4}" x2="{PL+18}" y2="{legend_y-4}" stroke="{C["accent"]}" stroke-width="2.5"/>')
    svg.append(f'<text x="{PL+24}" y="{legend_y}" fill="{C["muted"]}" font-size="11">个股归一化</text>')
    svg.append(f'<line x1="{PL+120}" y1="{legend_y-4}" x2="{PL+138}" y2="{legend_y-4}" stroke="{C["blue"]}" stroke-width="2"/>')
    svg.append(f'<text x="{PL+144}" y="{legend_y}" fill="{C["muted"]}" font-size="11">沪深 300 归一化</text>')
    svg.append(f'<rect x="{PL+260}" y="{legend_y-9}" width="14" height="8" fill="{C["accent"]}" opacity="0.20"/>')
    svg.append(f'<text x="{PL+280}" y="{legend_y}" fill="{C["muted"]}" font-size="11">累计超额（右轴）</text>')

    svg.append('</svg>')

    cum_excess = excess[-1][1]
    return wrap_chart_card(
        '\n'.join(svg),
        f"近 {n} 日股价走势 vs 沪深 300",
        f"归一化（起点=100）+ 累计超额收益 {cum_excess:+.1f}%"
    )


# ============================================================
# chart_timeline — 公司发展历程时间轴（P1-10）
# ============================================================
def chart_timeline(fundamental_text):
    """从 §2.0 公司概况 / 发展历程章节解析关键里程碑，渲染水平时间轴 SVG。

    解析规则（OR 命中其一即可）：
      A. Markdown 表格：表头含"年份"或"时间" + "事件"或"里程碑"
      B. 列表行格式：`- YYYY[/MM]?  事件描述`（支持 yyyy / yyyy-mm / yyyy.mm / yyyy 年 / yyyy 年 mm 月）

    至少需要 4 个里程碑才渲染；否则返回空串触发 [skip]。
    """
    if not fundamental_text:
        return ''

    text = fundamental_text
    events = []  # [(year:int, month:int|None, label:str)]

    # 策略 A：先尝试解析表格（"年份/时间 | 事件/里程碑/重大事件"）
    sections = re.split(r'\n#{2,5}\s+', '\n' + text)
    for sec in sections:
        if not re.search(r'(发展历程|公司沿革|大事记|里程碑|历史沿革)', sec[:80]):
            continue
        tbl_rows = parse_md_table(sec, header_match='年份') or parse_md_table(sec, header_match='时间')
        for r in tbl_rows:
            year_str = ''
            label = ''
            for k, v in r.items():
                if '年份' in k or '时间' in k or '年代' in k:
                    year_str = (v or '').strip()
                elif '事件' in k or '里程碑' in k or '大事' in k or '重大' in k or '说明' in k:
                    label = (v or '').strip()
            if year_str and label:
                # 提取 yyyy
                ym = re.search(r'(19|20)\d{2}', year_str)
                if ym:
                    y = int(ym.group(0))
                    mm_m = re.search(r'[-./年]\s*(\d{1,2})', year_str)
                    m = int(mm_m.group(1)) if mm_m else None
                    events.append((y, m, label[:30]))
        if events:
            break

    # 策略 B：fallback 解析列表行 `- 1998 公司前身成立`
    if not events:
        line_re = re.compile(r'^[\-\*]\s*((?:19|20)\d{2})(?:[-./年]\s*(\d{1,2})(?:月)?)?\s*[:：、，,\.\s]+(.+?)$', re.MULTILINE)
        for m in line_re.finditer(text):
            y = int(m.group(1))
            mm = int(m.group(2)) if m.group(2) else None
            label = m.group(3).strip()[:30]
            events.append((y, mm, label))

    if len(events) < 4:
        return ''

    # 去重 + 排序（最多取 12 条，避免过密）
    events = sorted(set(events), key=lambda x: (x[0], x[1] or 0))
    if len(events) > 12:
        # 均匀采样 12 个
        step = len(events) / 12
        events = [events[int(i * step)] for i in range(12)]

    n = len(events)
    W, H = 860, 220
    PL, PR, PT, PB = 50, 50, 50, 60
    chart_w = W - PL - PR
    chart_h = H - PT - PB

    y_min = events[0][0]
    y_max = events[-1][0]
    span = max(1, y_max - y_min)

    def xp(year, mm):
        f = mm / 12 if mm else 0
        return PL + chart_w * (year - y_min + f) / span

    axis_y = PT + chart_h / 2

    svg = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="发展历程时间轴">']
    # 主轴线
    svg.append(f'<line x1="{PL}" y1="{axis_y}" x2="{PL+chart_w}" y2="{axis_y}" stroke="{C["accent"]}" stroke-width="2.5"/>')
    # 年份刻度（每 2-3 年标一次）
    n_ticks = min(8, span + 1)
    for i in range(n_ticks + 1):
        yr = y_min + int(span * i / max(1, n_ticks))
        x = PL + chart_w * i / max(1, n_ticks)
        svg.append(f'<line x1="{x:.1f}" y1="{axis_y-4}" x2="{x:.1f}" y2="{axis_y+4}" stroke="{C["muted"]}" stroke-width="1"/>')
        svg.append(f'<text x="{x:.1f}" y="{H-30}" fill="{C["muted"]}" font-size="11" text-anchor="middle">{yr}</text>')

    # 事件节点：交错上下排布以减少标签重叠
    colors_cycle = [C["accent"], C["blue"], C["ok"], C["orange"], C["purple"], C["teal"]]
    for i, (y, m, label) in enumerate(events):
        x = xp(y, m)
        above = (i % 2 == 0)
        bubble_y = axis_y - 32 if above else axis_y + 32
        color = colors_cycle[i % len(colors_cycle)]
        # 连接线
        svg.append(f'<line x1="{x:.1f}" y1="{axis_y}" x2="{x:.1f}" y2="{bubble_y + (10 if above else -10):.1f}" stroke="{color}" stroke-width="1" stroke-dasharray="2 2"/>')
        # 圆点
        svg.append(f'<circle cx="{x:.1f}" cy="{axis_y}" r="5" fill="{color}" stroke="#ffffff" stroke-width="1.5"/>')
        # 年份徽章
        yr_label = f"{y}" + (f".{m:02d}" if m else "")
        bt_y = bubble_y - 6 if above else bubble_y + 14
        svg.append(f'<text x="{x:.1f}" y="{bt_y:.1f}" fill="{color}" font-size="11" font-weight="700" text-anchor="middle">{yr_label}</text>')
        # 事件标签（XML 转义）
        esc_label = label.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        bl_y = bubble_y + 8 if above else bubble_y + 28
        svg.append(f'<text x="{x:.1f}" y="{bl_y:.1f}" fill="{C["text"]}" font-size="10" text-anchor="middle">{esc_label}</text>')

    svg.append('</svg>')
    return wrap_chart_card(
        '\n'.join(svg),
        f"公司发展历程时间轴（{y_min}–{y_max}）",
        f"关键里程碑 {n} 个事件 · 交错排版"
    )


# ============================================================
# chart_ownership — 股权结构树图（P2-11）
# ============================================================
def chart_ownership(fundamental_text):
    """从 §2.0 / 股权结构章节解析"控股股东 + 持股比例 + 主要子公司"，渲染三层树形 SVG。

    解析规则（OR 命中其一即可）：
      A. 表格："股东名称|持股比例|股东性质" 或 "子公司名称|持股比例|主营"
      B. 一句话："实际控制人为 XXX，持股 XX%"

    至少需要 3 个股东（含实控人）才渲染；否则返回空串。
    """
    if not fundamental_text:
        return ''

    text = fundamental_text
    shareholders = []   # [(name, pct, role)]
    controller = None   # str
    subsidiaries = []   # [(name, pct, biz)]

    # 抓控股股东表
    sections = re.split(r'\n#{2,5}\s+', '\n' + text)
    for sec in sections:
        if re.search(r'(股权结构|股东|实际控制|控股股东)', sec[:60]):
            rows = parse_md_table(sec, header_match='股东') or parse_md_table(sec, header_match='持股')
            for r in rows:
                name = pct = role = ''
                for k, v in r.items():
                    if '股东名称' in k or '名称' in k or '股东' in k:
                        name = (v or '').strip()
                    elif '持股' in k or '比例' in k or '%' in k:
                        pct = (v or '').strip()
                    elif '性质' in k or '类型' in k or '关系' in k:
                        role = (v or '').strip()
                if name and pct:
                    pct_val = safe_float(pct)
                    if pct_val > 0:
                        shareholders.append((name[:14], pct_val, role[:8] or ''))
            if shareholders:
                break

    # 抓子公司表
    for sec in sections:
        if re.search(r'(主要子公司|参控股公司|子公司情况|控股子公司)', sec[:60]):
            rows = parse_md_table(sec, header_match='子公司') or parse_md_table(sec, header_match='公司名称')
            for r in rows:
                name = pct = biz = ''
                for k, v in r.items():
                    if '名称' in k or '子公司' in k:
                        name = (v or '').strip()
                    elif '持股' in k or '比例' in k:
                        pct = (v or '').strip()
                    elif '业务' in k or '主营' in k:
                        biz = (v or '').strip()
                if name:
                    subsidiaries.append((name[:14], safe_float(pct or '100'), biz[:18] or ''))
            if subsidiaries:
                break

    # 抓实际控制人
    m = re.search(r'实(?:际)?控制人[^\n]{0,30}?([\u4e00-\u9fa5A-Za-z·]{2,12})', text)
    if m:
        controller = m.group(1)

    if len(shareholders) < 3:
        return ''

    shareholders = sorted(shareholders, key=lambda x: -x[1])[:6]
    subsidiaries = subsidiaries[:5]

    W = 860
    H = 380 if subsidiaries else 260
    PT, PB = 30, 40

    svg = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="股权结构树图">']

    # 层 1：实控人（顶部居中）
    layer1_y = PT + 10
    if controller:
        c_x = W / 2
        svg.append(f'<rect x="{c_x-90:.1f}" y="{layer1_y}" width="180" height="40" rx="6" fill="{C["accent"]}" opacity="0.95"/>')
        svg.append(f'<text x="{c_x:.1f}" y="{layer1_y+18:.1f}" fill="#ffffff" font-size="11" text-anchor="middle">实际控制人</text>')
        svg.append(f'<text x="{c_x:.1f}" y="{layer1_y+34:.1f}" fill="#ffffff" font-size="13" font-weight="700" text-anchor="middle">{controller}</text>')

    # 层 2：主要股东（横向排列）
    layer2_y = layer1_y + 80
    n_sh = len(shareholders)
    box_w = min(140, (W - 80) / n_sh - 8)
    total_w = box_w * n_sh + 12 * (n_sh - 1)
    start_x = (W - total_w) / 2
    for i, (name, pct, role) in enumerate(shareholders):
        x = start_x + i * (box_w + 12)
        # 颜色：第一大股东突出
        color = C["accent"] if i == 0 else C["blue"]
        opacity = "0.85" if i == 0 else "0.70"
        # 连接线（实控人→大股东）
        if controller:
            svg.append(f'<line x1="{W/2:.1f}" y1="{layer1_y+40}" x2="{x+box_w/2:.1f}" y2="{layer2_y}" stroke="{C["muted"]}" stroke-width="1" stroke-dasharray="3 2"/>')
        svg.append(f'<rect x="{x:.1f}" y="{layer2_y}" width="{box_w:.1f}" height="56" rx="5" fill="{color}" opacity="{opacity}"/>')
        esc_name = name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        svg.append(f'<text x="{x+box_w/2:.1f}" y="{layer2_y+20:.1f}" fill="#ffffff" font-size="11" font-weight="600" text-anchor="middle">{esc_name}</text>')
        svg.append(f'<text x="{x+box_w/2:.1f}" y="{layer2_y+36:.1f}" fill="#ffffff" font-size="14" font-weight="700" text-anchor="middle">{pct:.2f}%</text>')
        if role:
            svg.append(f'<text x="{x+box_w/2:.1f}" y="{layer2_y+50:.1f}" fill="#ffffff" font-size="9" text-anchor="middle" opacity="0.85">{role}</text>')

    # 层 3：上市公司（中央）
    layer3_y = layer2_y + 90
    svg.append(f'<rect x="{W/2-110:.1f}" y="{layer3_y}" width="220" height="44" rx="6" fill="{C["text"]}" opacity="0.95"/>')
    svg.append(f'<text x="{W/2:.1f}" y="{layer3_y+18:.1f}" fill="#ffffff" font-size="11" text-anchor="middle">上市公司主体</text>')
    svg.append(f'<text x="{W/2:.1f}" y="{layer3_y+36:.1f}" fill="#ffffff" font-size="13" font-weight="700" text-anchor="middle">本公司（A股上市）</text>')
    # 大股东→上市公司连线
    for i in range(n_sh):
        x = start_x + i * (box_w + 12) + box_w / 2
        svg.append(f'<line x1="{x:.1f}" y1="{layer2_y+56}" x2="{W/2:.1f}" y2="{layer3_y}" stroke="{C["muted"]}" stroke-width="0.8"/>')

    # 层 4：主要子公司
    if subsidiaries:
        layer4_y = layer3_y + 90
        n_sub = len(subsidiaries)
        sub_w = min(140, (W - 80) / n_sub - 8)
        sub_total = sub_w * n_sub + 12 * (n_sub - 1)
        sub_start = (W - sub_total) / 2
        for i, (name, pct, biz) in enumerate(subsidiaries):
            x = sub_start + i * (sub_w + 12)
            svg.append(f'<line x1="{W/2:.1f}" y1="{layer3_y+44}" x2="{x+sub_w/2:.1f}" y2="{layer4_y}" stroke="{C["muted"]}" stroke-width="0.8"/>')
            svg.append(f'<rect x="{x:.1f}" y="{layer4_y}" width="{sub_w:.1f}" height="50" rx="4" fill="{C["panel"]}" stroke="{C["ok"]}" stroke-width="1.5"/>')
            esc_name = name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            svg.append(f'<text x="{x+sub_w/2:.1f}" y="{layer4_y+16:.1f}" fill="{C["text"]}" font-size="11" font-weight="600" text-anchor="middle">{esc_name}</text>')
            svg.append(f'<text x="{x+sub_w/2:.1f}" y="{layer4_y+30:.1f}" fill="{C["ok"]}" font-size="11" font-weight="700" text-anchor="middle">{pct:.0f}%</text>')
            if biz:
                esc_biz = biz.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                svg.append(f'<text x="{x+sub_w/2:.1f}" y="{layer4_y+44:.1f}" fill="{C["muted"]}" font-size="9" text-anchor="middle">{esc_biz}</text>')

    svg.append('</svg>')
    return wrap_chart_card(
        '\n'.join(svg),
        "股权结构树图",
        f"实控人 → {n_sh} 大股东 → 上市公司 → {len(subsidiaries)} 主要子公司"
    )


# ============================================================
# chart_sentiment — 行业景气度仪表盘（P2-15）
# ============================================================
def chart_sentiment(fundamental_text):
    """从 §1（行业层）章节解析 3-4 项景气度指标，渲染指标卡 + 微型折线图组合仪表盘。

    解析规则：
      表头含"指标"或"景气度" + "近 12 个月趋势"或"最新值" + "同比"或"YoY"
      或：表头含"产能利用率/资本开支/价格指数/库存"等关键词
    至少需要 3 个指标才渲染；否则返回空串。
    """
    if not fundamental_text:
        return ''

    text = fundamental_text
    indicators = []  # [(name, latest, yoy_pct, trend_history: list[float])]

    # 寻找行业景气度章节
    target_section = None
    sections = re.split(r'\n(#{2,5}\s+.+)\n', '\n' + text)
    for i in range(1, len(sections) - 1, 2):
        header = sections[i]
        body = sections[i + 1]
        if re.search(r'(行业景气|景气度|行业层|产能利用率|行业资本开支)', header):
            target_section = body
            break
    if not target_section:
        # 第二次尝试：直接搜索关键短语周边的表格
        for sec in re.split(r'\n#{2,5}\s+', text):
            if re.search(r'(景气度|产能利用率|资本开支|价格指数|库存周期)', sec[:200]):
                target_section = sec
                break

    if not target_section:
        return ''

    # 解析表格（任意有 "指标" 列的表）
    rows = parse_md_table(target_section, header_match='指标') or parse_md_table(target_section, header_match='景气')
    for r in rows:
        name = ''
        latest = None
        yoy = None
        trend = []
        for k, v in r.items():
            v_clean = (v or '').strip()
            if '指标' in k or '景气' in k or '名称' in k:
                name = v_clean[:14]
            elif '最新' in k or '当前' in k or '现值' in k:
                latest = safe_float(v_clean)
            elif '同比' in k or 'YoY' in k or 'yoy' in k:
                yoy = safe_float(v_clean)
            elif '趋势' in k or '12' in k or '近12' in k or '走势' in k:
                # 拆分数字（支持逗号/斜杠/空格分隔）
                nums = re.findall(r'-?\d+(?:\.\d+)?', v_clean)
                trend = [float(x) for x in nums][:12]
        if name and (latest is not None or trend):
            indicators.append((name, latest, yoy, trend))

    indicators = indicators[:4]
    if len(indicators) < 3:
        return ''

    n = len(indicators)
    W = 860
    card_w = (W - 60 - 16 * (n - 1)) / n
    card_h = 130
    H = 30 + card_h + 20

    svg = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="行业景气度仪表盘">']

    for i, (name, latest, yoy, trend) in enumerate(indicators):
        cx = 30 + i * (card_w + 16)
        cy = 20
        # 卡片背景
        svg.append(f'<rect x="{cx:.1f}" y="{cy}" width="{card_w:.1f}" height="{card_h}" rx="6" fill="{C["panel"]}" stroke="{C["line"]}" stroke-width="1"/>')
        # 指标名
        esc_name = name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        svg.append(f'<text x="{cx+12:.1f}" y="{cy+22:.1f}" fill="{C["muted"]}" font-size="11">{esc_name}</text>')
        # 最新值
        if latest is not None:
            svg.append(f'<text x="{cx+12:.1f}" y="{cy+48:.1f}" fill="{C["text"]}" font-size="22" font-weight="700">{latest:.1f}</text>')
        # 同比
        if yoy is not None:
            yoy_color = C["accent"] if yoy >= 0 else C["ok"]
            arrow = "↑" if yoy >= 0 else "↓"
            svg.append(f'<text x="{cx+12:.1f}" y="{cy+66:.1f}" fill="{yoy_color}" font-size="12" font-weight="600">YoY {arrow} {abs(yoy):.1f}%</text>')
        # 微型折线（卡片下半区）
        if trend and len(trend) >= 2:
            tx0 = cx + 12
            ty0 = cy + 80
            tw = card_w - 24
            th = 40
            t_max = max(trend) * 1.05
            t_min = min(trend) * 0.95
            t_span = t_max - t_min if t_max != t_min else 1
            pts = []
            for j, v in enumerate(trend):
                px = tx0 + tw * j / (len(trend) - 1)
                py = ty0 + th * (1 - (v - t_min) / t_span)
                pts.append(f'{px:.1f},{py:.1f}')
            color = C["accent"] if (yoy or 0) >= 0 else C["ok"]
            # 填充面积
            area_d = f"M {pts[0]}"
            for p in pts[1:]:
                area_d += f" L {p}"
            area_d += f" L {tx0+tw:.1f} {ty0+th:.1f} L {tx0:.1f} {ty0+th:.1f} Z"
            svg.append(f'<path d="{area_d}" fill="{color}" opacity="0.10"/>')
            svg.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2"/>')
            # 端点
            last_x, last_y = pts[-1].split(',')
            svg.append(f'<circle cx="{last_x}" cy="{last_y}" r="3" fill="{color}"/>')

    svg.append('</svg>')
    return wrap_chart_card(
        '\n'.join(svg),
        "行业景气度仪表盘",
        f"{n} 项关键指标 · 最新值 + YoY + 近 12 期趋势"
    )


# ============================================================
# 辅助函数
# ============================================================
def wrap_chart_card(svg_content, title, subtitle):
    """用 chart-card 包装 SVG"""
    return (f'<div class="chart-card">'
            f'<div class="chart-title">{title}</div>'
            f'<div class="chart-subtitle">{subtitle}</div>'
            f'<div class="svg-wrap">{svg_content}</div>'
            f'</div>')


# ============================================================
# 注入逻辑
# ============================================================
def _extract_code_from_path(html_path):
    """从报告文件名中提取股票代码（如 交易决策报告_300308_中际旭创.html → 300308）"""
    import re as _re
    fname = Path(html_path).stem
    m = _re.search(r'(\d{6})', fname)
    return m.group(1) if m else None


def _fetch_kline_for_chart(code, days=250):
    """调用 stock_quote_scraper.fetch_kline 获取原始K线数据供图表使用"""
    try:
        scripts_dir = Path(__file__).parent / "scripts"
        sys.path.insert(0, str(scripts_dir))
        from stock_quote_scraper import fetch_kline
        data = fetch_kline(code, days)
        if isinstance(data, dict) and not data.get("error"):
            return data.get("K线数据", [])
    except Exception as e:
        print(f"[WARN] 实时K线获取失败({e})，尝试从缓存读取...")
    # 降级: 尝试读取已有的 _quote.md 中的10条记录（功能退化但不报错）
    return []


_SUP_TAG_RE = re.compile(r'<sup>[^<]*</sup>', re.IGNORECASE)


def _strip_sup_tags(html_text: str):
    """剥离 <sup>N</sup> 脚标标签，返回 (stripped_text, offset_map)。

    offset_map 将 stripped_text 中的位置映射回原始 html_text 的位置。
    这样正则可以在 stripped_text 上匹配（避免 [^<]* 被 <sup> 打断），
    然后通过 offset_map 映射回原始 HTML 进行注入。
    """
    offset_map = []      # offset_map[stripped_pos] = original_pos
    result_chars = []
    last_end = 0
    for m in _SUP_TAG_RE.finditer(html_text):
        # 复制匹配之前的部分
        segment = html_text[last_end:m.start()]
        for i, ch in enumerate(segment):
            offset_map.append(last_end + i)
            result_chars.append(ch)
        last_end = m.end()
    # 复制剩余部分
    segment = html_text[last_end:]
    for i, ch in enumerate(segment):
        offset_map.append(last_end + i)
        result_chars.append(ch)
    # 哨兵：末尾位置
    offset_map.append(len(html_text))
    return ''.join(result_chars), offset_map


def _fallback_section_end_inject(html, chart_html, chart_name, section_name, *section_keywords):
    """锚点 fallback 策略：按章节标题关键词找到对应 h3/h4/h5，在该章节末尾插入。

    未命中所有 fallback 关键词时返回 None，调用方仍可视作静默失败。
    """
    if not section_keywords:
        return None
    # 构造"章节开始"和"下一个同级或更高级章节开始"的边界
    for kw in section_keywords:
        # 找到包含该关键词的 h3/h4/h5
        heading_pat = r'<h([345])[^>]*>[^<]*' + re.escape(kw) + r'[^<]*</h\1>'
        m = re.search(heading_pat, html, re.IGNORECASE)
        if not m:
            continue
        level = m.group(1)
        # 查找该章节的结束位置：下一个同级或更高级 <hN>
        level_int = int(level)
        # 构造同级或更高级标题的正则：h2/h3/…/h{level}
        higher_levels = ''.join(str(i) for i in range(2, level_int + 1))
        end_pat = r'<h[' + higher_levels + r'][^>]*>'
        after = html[m.end():]
        end_m = re.search(end_pat, after)
        if end_m:
            insert_pos = m.end() + end_m.start()
        else:
            # 找不到下一章节，插入文档末尾之前
            footer_m = re.search(r'<footer|</body>', after)
            insert_pos = (m.end() + footer_m.start()) if footer_m else len(html)
        result = html[:insert_pos] + '\n' + chart_html + '\n' + html[insert_pos:]
        print(f"  🔧 {chart_name} → {section_name}（fallback：{kw} 章节末尾）")
        return result
    return None


def _fuzzy_inject_after(html, chart_html, chart_name, section_name, *patterns, fallback_keywords=()):
    """在首个匹配的锚点之 **后** 插入 chart_html。

    按 patterns 优先级依次尝试正则匹配；首个匹配即注入并返回新 html。
    匹配前剥离 <sup> 脚标，避免 [^<]* 被脚标打断。
    全部 patterns 未命中时，若提供 fallback_keywords 则尝试按章节关键词插入章节末尾。
    返回 None 表示所有策略均未匹配。
    """
    stripped, omap = _strip_sup_tags(html)
    for pat in patterns:
        m = re.search(pat, stripped, re.IGNORECASE | re.DOTALL)
        if m:
            pos = omap[m.end()]
            result = html[:pos] + '\n' + chart_html + html[pos:]
            print(f"  ✅ {chart_name} → {section_name}")
            return result
    # 所有精确锚点失败，尝试 fallback
    if fallback_keywords:
        result = _fallback_section_end_inject(html, chart_html, chart_name, section_name, *fallback_keywords)
        if result is not None:
            return result
    print(f"  ⚠️ 未找到{section_name}锚点（{chart_name}）")
    return None


def _fuzzy_inject_before(html, chart_html, chart_name, section_name, *patterns, fallback_keywords=()):
    """在首个匹配的锚点之 **前** 插入 chart_html。

    按 patterns 优先级依次尝试正则匹配；首个匹配即注入并返回新 html。
    匹配前剥离 <sup> 脚标，避免 [^<]* 被脚标打断。
    全部 patterns 未命中时，若提供 fallback_keywords 则尝试按章节关键词插入章节末尾。
    返回 None 表示所有策略均未匹配。
    """
    stripped, omap = _strip_sup_tags(html)
    for pat in patterns:
        m = re.search(pat, stripped, re.IGNORECASE | re.DOTALL)
        if m:
            pos = omap[m.start()]
            result = html[:pos] + chart_html + '\n' + html[pos:]
            print(f"  ✅ {chart_name} → {section_name}")
            return result
    # fallback
    if fallback_keywords:
        result = _fallback_section_end_inject(html, chart_html, chart_name, section_name, *fallback_keywords)
        if result is not None:
            return result
    print(f"  ⚠️ 未找到{section_name}锚点（{chart_name}）")
    return None


def inject_charts(html_path, stock_code=None):
    """将图表注入到 HTML 报告中

    Parameters:
        html_path:   HTML报告文件路径
        stock_code:  股票代码（如 '300308'）。若为 None，从文件名自动提取。
    """
    html_text = read_file(html_path)
    if not html_text:
        print(f"[ERROR] 无法读取 {html_path}")
        return False

    # 自动提取股票代码
    code = stock_code or _extract_code_from_path(html_path)
    if not code:
        print(f"[ERROR] 无法从文件名提取股票代码，请通过 stock_code 参数传入")
        return False
    print(f"[INFO] 股票代码: {code}")

    # 读取数据源
    quote_text = read_file(FIN_DIR / f"{code}_quote.md")
    fundamental_text = read_file(FIN_DIR / f"{code}_fundamental.md")

    # 读取实时行情 JSON（用于 metric_cards 的价格/涨跌幅数据）
    realtime_data = None
    realtime_path = FIN_DIR / f"{code}_realtime.json"
    if realtime_path.exists():
        try:
            realtime_data = json.loads(realtime_path.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"[WARN] 读取 realtime JSON 失败: {e}")

    # 读取基本面 JSON（用于 PE/PB/市值 多源回退）
    fundamental_json = None
    fundamental_json_path = FIN_DIR / f"{code}_fundamental.json"
    if fundamental_json_path.exists():
        try:
            fundamental_json = json.loads(fundamental_json_path.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"[WARN] 读取 fundamental JSON 失败: {e}")

    # 生成所有图表
    charts = {}

    print("[1/7] 生成核心指标卡片...")
    charts['metrics'] = chart_metric_cards(code, fundamental_text, realtime_data, fundamental_json)

    print("[2/7] 生成K线走势图(增强版)...")
    kline_records = _fetch_kline_for_chart(code, 250)
    if kline_records:
        print(f"  获取到 {len(kline_records)} 条K线数据")
        charts['kline'] = chart_kline(kline_records, display_days=120)
    else:
        print("  ⚠️ 无法获取K线数据，跳过K线图")
        charts['kline'] = ''

    print("[3/7] 生成年度营收净利润趋势...")
    charts['annual'] = chart_annual_trend(fundamental_text)

    print("[4/7] 生成季度毛利率趋势...")
    charts['gm'] = chart_gross_margin(fundamental_text)

    print("[5/7] 生成三项现金流结构...")
    charts['cashflow'] = chart_cashflow(fundamental_text)

    print("[6/7] 生成FCF趋势...")
    charts['fcf'] = chart_fcf(fundamental_text)

    print("[7/7] 生成PE/PB分位仪表盘...")
    charts['valuation'] = chart_valuation_gauge(fundamental_text)

    # 图表 8 / 9（可选，依赖外部提供的结构化数据）
    # 同业对比数据：由渲染 pipeline 预先准备，放在 FinancialData/{code}_peers.json
    peer_data = None
    peer_path = FIN_DIR / f"{code}_peers.json"
    if peer_path.exists():
        try:
            peer_data = json.loads(peer_path.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"[WARN] 读取 peers JSON 失败: {e}")
    if peer_data:
        print("[8/9] 生成同业对比柱状图...")
        charts['peer'] = chart_peer_comparison(fundamental_text, peer_data)
    else:
        charts['peer'] = ''

    # 胜率仪表盘数据：由报告作者提供结构化数据，放在 FinancialData/{code}_winrate.json
    winrate_data = None
    winrate_path = FIN_DIR / f"{code}_winrate.json"
    if winrate_path.exists():
        try:
            winrate_data = json.loads(winrate_path.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"[WARN] 读取 winrate JSON 失败: {e}")
    if winrate_data:
        print("[9/9] 生成胜率/赔率仪表盘...")
        charts['winrate'] = chart_winrate_dashboard(winrate_data)
    else:
        charts['winrate'] = ''

    # 统计
    success = sum(1 for v in charts.values() if v)
    print(f"\n生成完毕: {success}/{len(charts)} 个图表")

    # === 注入策略（模糊/正则匹配，容错多种模板变体）===
    # 每个注入位置使用 _fuzzy_inject(): 按优先级尝试多个正则，首个匹配即注入

    modified = html_text

    # ---------- 幂等: 先移除所有已知 chart-card（防止重复注入）----------
    # 标题模式用正则匹配，兼容年份后缀如 "（2020-2025）"
    _chart_titles_to_remove = [
        r"核心指标一览",
        r"近\d+日K线走势",
        r"K线走势与关键价位",
        r"年度营收与净利润趋势.*",
        r"季度毛利率趋势.*",
        r"三项现金流年度结构.*",
        r"自由现金流\(FCF\)趋势.*",
        r"(?:PE/PB |估值)历史分位仪表盘.*",
        r"同业对比（四维度）",
        r"胜率\s*/\s*赔率综合仪表盘",
    ]
    for title_pat in _chart_titles_to_remove:
        # chart-card 结构: <div class="chart-card"><div class="chart-title">X</div>
        #   <div class="chart-subtitle">Y</div><div class="svg-wrap">...svg...</div></div>
        # 用 </svg> 作为内部定位锚，再匹配到 chart-card 的闭合 </div>
        old_chart_re = re.compile(
            r'<div\s+class="chart-card">\s*<div\s+class="chart-title">'
            + title_pat
            + r'</div>.*?</svg>\s*</div>\s*</div>\n?',
            re.DOTALL
        )
        modified = old_chart_re.sub('', modified)

    # ---------- 注入 1: 核心指标卡片 → "核心结论"标题之后 ----------
    if charts['metrics']:
        ok = _fuzzy_inject_after(
            modified, charts['metrics'], '核心指标卡片', '核心结论章节',
            # A型: <h3 id="sec-1">一、核心结论与操作指令</h3>
            r'<h3[^>]*>[^<]*核心结论[^<]*</h3>',
            # B型: <h2>📋 一、核心结论与操作指令</h2>  或  <h2><span...>📋</span>一、核心结论...</h2>
            r'<h2[^>]*>(?:<span[^>]*>[^<]*</span>)?[^<]*核心结论[^<]*</h2>',
            # C型: <div class="subsection-title">一、核心结论与操作指令</div>
            r'<div[^>]*class="[^"]*subsection-title[^"]*"[^>]*>[^<]*核心结论[^<]*</div>',
            # D型(简化报告): <h1>核心结论</h1>
            r'<h1[^>]*>[^<]*核心结论[^<]*</h1>',
        )
        if ok:
            modified = ok

    # ---------- 注入 2: K线走势图 → "关键价位"表格/图表之前 ----------
    if charts['kline']:
        ok = _fuzzy_inject_before(
            modified, charts['kline'], 'K线走势图', '技术面章节',
            # A: 关键价位分布图 chart-card（图表模式）
            r'<div[^>]*class="chart-card"[^>]*><div[^>]*class="chart-title"[^>]*>关键价位分布图</div>',
            # B: 📊 关键价位 callout（表格模式）
            r'<div[^>]*class="[^"]*callout[^"]*"[^>]*>[^<]*<strong>[^<]*关键价位[^<]*</strong>[^<]*</div>',
            # C: 📊 K线关键位 callout（报告变体）
            r'<div[^>]*class="[^"]*callout[^"]*"[^>]*>[^<]*<strong>[^<]*K线关键位[^<]*</strong>[^<]*</div>',
            # D: 📊 关键支撑/压力 callout
            r'<div[^>]*class="[^"]*callout[^"]*"[^>]*>[^<]*<strong>[^<]*关键支撑[^<]*</strong>[^<]*</div>',
        )
        if ok:
            modified = ok
        else:
            # 降级E: 在"技术面"章节标题之后（最宽松的fallback）
            ok = _fuzzy_inject_after(
                modified, charts['kline'], 'K线走势图', '技术面章节标题之后',
                # h4/h3/h2 技术面标题
                r'<h[2-5][^>]*>[^<]*技术面[^<]*</h[2-5]>',
            )
            if ok:
                modified = ok

    # ---------- 注入 3: 年度趋势 → "分季度趋势"callout之前 ----------
    if charts['annual']:
        ok = _fuzzy_inject_before(
            modified, charts['annual'], '年度趋势图', '企业层章节',
            # A型: <div class="callout callout-data">📊 <strong>分季度趋势</strong></div>
            r'<div[^>]*class="[^"]*callout[^"]*"[^>]*>[^<]*<strong>[^<]*分季度趋势[^<]*</strong>[^<]*</div>',
            # B型: <p><strong>分季度趋势</strong>...</p>
            r'<p[^>]*><strong>[^<]*分季度趋势[^<]*</strong>',
            # C型: "分季度营收趋势" callout（不同报告变体）
            r'<div[^>]*class="[^"]*callout[^"]*"[^>]*>[^<]*<strong>[^<]*分季度营收趋势[^<]*</strong>[^<]*</div>',
            r'<p[^>]*><strong>[^<]*分季度营收趋势[^<]*</strong>',
        )
        if ok:
            modified = ok
        else:
            # 降级E: 在"核心财务数据" callout 之后注入
            ok = _fuzzy_inject_after(
                modified, charts['annual'], '年度趋势图', '核心财务数据之后',
                r'<div[^>]*class="[^"]*callout[^"]*"[^>]*>[^<]*<strong>[^<]*核心财务数据[^<]*</strong>[^<]*</div>',
                fallback_keywords=('企业层', '4.1.3', '核心财务'),
            )
            if ok:
                modified = ok

    # ---------- 注入 4: 毛利率趋势 → "产能与运营数据"callout之前 ----------
    if charts['gm']:
        ok = _fuzzy_inject_before(
            modified, charts['gm'], '毛利率趋势图', '企业层章节',
            # A型: <div class="callout callout-data">📊 <strong>产能与运营数据</strong></div>
            r'<div[^>]*class="[^"]*callout[^"]*"[^>]*>[^<]*<strong>[^<]*产能与运营[^<]*</strong>[^<]*</div>',
            # B型: 直接含"产能"的p/strong
            r'<p[^>]*><strong>[^<]*产能与运营[^<]*</strong>',
        )
        if ok:
            modified = ok
        else:
            # 降级D: 年度趋势图表之后
            ok = _fuzzy_inject_after(
                modified, charts['gm'], '毛利率趋势图', '年度趋势图表之后',
                r'<div\s+class="chart-card">\s*<div\s+class="chart-title">年度营收与净利润趋势[^<]*</div>.*?</svg>\s*</div>\s*</div>',
            )
            if ok:
                modified = ok
            else:
                # 降级E: 在"分季度营收趋势" callout 之前
                ok = _fuzzy_inject_before(
                    modified, charts['gm'], '毛利率趋势图', '分季度趋势之前',
                    r'<div[^>]*class="[^"]*callout[^"]*"[^>]*>[^<]*<strong>[^<]*分季度.*?趋势[^<]*</strong>[^<]*</div>',
                    r'<p[^>]*><strong>[^<]*分季度.*?趋势[^<]*</strong>',
                    fallback_keywords=('企业层', '4.1.3', '产能与运营'),
                )
                if ok:
                    modified = ok

    # ---------- 注入 5: 三项现金流 → "ROIC vs WACC"或"情景估值"之前 ----------
    if charts['cashflow']:
        ok = _fuzzy_inject_before(
            modified, charts['cashflow'], '三项现金流', '企业层章节',
            # A型: <p><strong>五、ROIC vs WACC 增长质量验证</strong></p>
            r'<p[^>]*><strong>[^<]*ROIC[^<]*WACC[^<]*验证[^<]*</strong></p>',
            # B型: <p class="md-paragraph"><strong>五、ROIC vs WACC...</strong></p>
            r'<p[^>]*><strong>[^<]*ROIC[^<]*WACC[^<]*</strong></p>',
            # C型: 章节编号可能不同（四/五/六）
            r'<p[^>]*><strong>[一二三四五六七八九十\d]+[、.．]\s*ROIC[^<]*</strong></p>',
            # D型(简化报告): <p><strong>ROIC vs WACC</strong>: 内联文本...</p>
            r'<p[^>]*><strong>[^<]*ROIC[^<]*WACC[^<]*</strong>',
        )
        if ok:
            modified = ok
        else:
            # 降级E: 在"情景估值" callout 之前
            ok = _fuzzy_inject_before(
                modified, charts['cashflow'], '三项现金流', '情景估值之前',
                r'<div[^>]*class="[^"]*callout[^"]*"[^>]*>[^<]*<strong>[^<]*情景估值[^<]*</strong>[^<]*</div>',
                r'<p[^>]*><strong>[^<]*情景估值[^<]*</strong>',
                fallback_keywords=('企业层', '4.1.3', '4.1.5', '估值'),
            )
            if ok:
                modified = ok

    # ---------- 注入 6: FCF趋势 → "ROIC / WACC 对比"图表之前 或 现金流之后 或 情景估值之前 ----------
    if charts['fcf']:
        ok = _fuzzy_inject_before(
            modified, charts['fcf'], 'FCF趋势图', '企业层章节',
            # 精确: <div class="chart-card"><div class="chart-title">ROIC / WACC 对比</div>
            r'<div[^>]*class="chart-card"[^>]*><div[^>]*class="chart-title"[^>]*>ROIC\s*/\s*WACC\s*对比</div>',
            # 宽松: 任何chart-title中含ROIC和WACC
            r'<div[^>]*class="chart-title"[^>]*>[^<]*ROIC[^<]*WACC[^<]*</div>',
        )
        if ok:
            modified = ok
        else:
            # 降级D: FCF紧跟三项现金流图表之后
            ok = _fuzzy_inject_after(
                modified, charts['fcf'], 'FCF趋势图', '三项现金流图表之后',
                r'<div\s+class="chart-card">\s*<div\s+class="chart-title">三项现金流年度结构[^<]*</div>.*?</svg>\s*</div>\s*</div>',
            )
            if ok:
                modified = ok
            else:
                # 降级E: 在"情景估值" callout 之前
                ok = _fuzzy_inject_before(
                    modified, charts['fcf'], 'FCF趋势图', '情景估值之前',
                    r'<div[^>]*class="[^"]*callout[^"]*"[^>]*>[^<]*<strong>[^<]*情景估值[^<]*</strong>[^<]*</div>',
                    r'<p[^>]*><strong>[^<]*情景估值[^<]*</strong>',
                    fallback_keywords=('企业层', '4.1.3', '4.1.5', '估值'),
                )
                if ok:
                    modified = ok

    # ---------- 注入 7: PE/PB仪表盘 → "情景估值"callout之前 ----------
    if charts['valuation']:
        ok = _fuzzy_inject_before(
            modified, charts['valuation'], 'PE/PB仪表盘', '估值章节',
            # A型: <div class="callout callout-data">📊 <strong>情景估值与目标价区间</strong></div>
            r'<div[^>]*class="[^"]*callout[^"]*"[^>]*>[^<]*<strong>[^<]*情景估值[^<]*</strong>[^<]*</div>',
            # B型: <p><strong>情景估值区间</strong>...</p>
            r'<p[^>]*><strong>[^<]*情景估值[^<]*</strong>',
            # 放宽: 任何包含"估值水位"或"估值区间"的 callout
            r'<div[^>]*class="[^"]*callout[^"]*"[^>]*>[^<]*<strong>[^<]*估值水位[^<]*</strong>[^<]*</div>',
            r'<div[^>]*class="[^"]*callout[^"]*"[^>]*>[^<]*<strong>[^<]*当前估值[^<]*</strong>[^<]*</div>',
            fallback_keywords=('估值与定价', '4.1.5', '估值'),
        )
        if ok:
            modified = ok

    # ---------- 注入 8: 同业对比柱状图 → "同业对比" / "竞争格局" / "行业可比"章节之后 ----------
    if charts.get('peer'):
        ok = _fuzzy_inject_after(
            modified, charts['peer'], '同业对比柱状图', '同业对比章节',
            # 精确: h4/h3 含"同业对比" / "可比公司"
            r'<h[2-5][^>]*>[^<]*同业对比[^<]*</h[2-5]>',
            r'<h[2-5][^>]*>[^<]*可比公司[^<]*</h[2-5]>',
            r'<h[2-5][^>]*>[^<]*竞争格局[^<]*</h[2-5]>',
            # callout: 📊 同业对比
            r'<div[^>]*class="[^"]*callout[^"]*"[^>]*>[^<]*<strong>[^<]*同业对比[^<]*</strong>[^<]*</div>',
        )
        if ok:
            modified = ok

    # ---------- 注入 9: 胜率/赔率仪表盘 → "综合研判" / "综合胜率" / "交易计划"章节之前 ----------
    if charts.get('winrate'):
        ok = _fuzzy_inject_before(
            modified, charts['winrate'], '胜率/赔率仪表盘', '综合研判章节',
            # 精确: h3 含"综合研判" / "综合胜率"
            r'<h3[^>]*>[^<]*综合研判[^<]*</h3>',
            r'<h3[^>]*>[^<]*综合胜率[^<]*</h3>',
            # 兼容: 交易计划 / 操作计划 章节
            r'<h3[^>]*>[^<]*交易计划[^<]*</h3>',
            r'<h3[^>]*>[^<]*操作计划[^<]*</h3>',
        )
        if ok:
            modified = ok
        else:
            # 降级: 综合研判 callout 之前
            ok = _fuzzy_inject_before(
                modified, charts['winrate'], '胜率/赔率仪表盘', '综合研判callout之前',
                r'<div[^>]*class="[^"]*callout[^"]*"[^>]*>[^<]*<strong>[^<]*综合研判[^<]*</strong>[^<]*</div>',
                r'<p[^>]*><strong>[^<]*综合研判[^<]*</strong>',
            )
            if ok:
                modified = ok

    # 写回
    Path(html_path).write_text(modified, encoding='utf-8')
    print(f"\n✅ 所有图表已注入到 {html_path}")
    print(f"   文件大小: {len(modified):,} 字节")
    return True


# ============================================================
# 主入口
# ============================================================
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python scripts/chart_injector.py <html_file> [--code <股票代码>]")
        sys.exit(1)

    html_file = sys.argv[1]
    if not os.path.exists(html_file):
        print(f"[ERROR] 文件不存在: {html_file}")
        sys.exit(1)

    # 可选 --code 参数
    code_arg = None
    if '--code' in sys.argv:
        idx = sys.argv.index('--code')
        if idx + 1 < len(sys.argv):
            code_arg = sys.argv[idx + 1]

    success = inject_charts(html_file, stock_code=code_arg)
    sys.exit(0 if success else 1)
