"""
render.py — Tearsheet 渲染：JSON + 自包含 HTML 看板 + 中文一段话摘要

HTML 完全自包含：内联 CSS + 手绘 SVG 图表，无任何外部 CDN 依赖，
浏览器直接双击打开即可查看。看板含：
  - 关键指标卡片
  - 月度收益热力图（年×月矩阵，绿涨红跌）
  - 净值 + 回撤 双轴曲线（SVG）
  - 滚动夏普曲线（SVG）
  - Top-N 回撤区间表
  - 中文一段话摘要
  - 免责声明
"""
from __future__ import annotations
import json
import html


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------
def to_json(tearsheet: dict) -> str:
    return json.dumps(tearsheet, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 中文摘要
# ---------------------------------------------------------------------------
def _pct(x, digits=2):
    if x is None:
        return "—"
    return f"{x * 100:.{digits}f}%"


def _num(x, digits=2):
    if x is None:
        return "—"
    return f"{x:.{digits}f}"


def build_summary_text(t: dict) -> str:
    """生成中文一段话摘要，点出策略性格 / 痛点 / 与基准关系。"""
    s = t["summary"]
    ra = t["risk_adjusted"]
    dist = t["distribution"]
    parts = []
    parts.append(
        f"区间 {t.get('start_date')} 至 {t.get('end_date')}（共 {t['n_periods']} 期，"
        f"年化期数 {t['periods_per_year']}）："
        f"累计收益 {_pct(s['cumulative_return'])}，年化收益 {_pct(s['annualized_return'])}，"
        f"年化波动 {_pct(s['annualized_vol'])}，夏普 {_num(ra['sharpe'])}、"
        f"索提诺 {_num(ra['sortino'])}、Calmar {_num(ra['calmar'])}。"
    )
    # 策略性格
    sharpe = ra.get("sharpe")
    if sharpe is not None:
        if sharpe >= 1.5:
            character = "风险调整后表现优异，收益对波动的补偿充分"
        elif sharpe >= 0.8:
            character = "风险调整后表现中等，收益与波动大体匹配"
        elif sharpe >= 0:
            character = "风险调整后表现偏弱，波动对收益的侵蚀明显"
        else:
            character = "区间内为负收益，风险调整指标为负"
        parts.append(f"整体看，{character}。")
    # 最大痛点：回撤 / 尾部
    mdd = s.get("max_drawdown")
    cvar = dist.get("cvar_95")
    pain = []
    if mdd is not None:
        pain.append(f"最大回撤 {_pct(mdd)}")
    dd = t.get("drawdowns") or []
    if dd:
        top = dd[0]
        rec = "尚未恢复" if not top.get("recovered") else f"恢复用时 {top.get('recovery_days')} 天"
        pain.append(f"最深回撤自 {top.get('peak_date')} 起、谷底 {top.get('trough_date')}（{rec}）")
    if cvar is not None:
        pain.append(f"5% 尾部平均损失(CVaR) {_pct(cvar)}")
    if pain:
        parts.append("主要痛点：" + "；".join(pain) + "。")
    # 分布
    skew = dist.get("skewness")
    kurt = dist.get("kurtosis")
    if skew is not None and kurt is not None:
        tail = "厚尾" if kurt > 1 else "接近正态"
        side = "左偏（大跌风险）" if skew < -0.2 else ("右偏（大涨居多）" if skew > 0.2 else "基本对称")
        parts.append(f"收益分布{side}、{tail}（偏度 {_num(skew)}，超额峰度 {_num(kurt)}）。")
    # 与基准
    vb = t.get("vs_benchmark")
    if vb:
        parts.append(
            f"相对基准：超额年化 {_pct(vb.get('excess_annual'))}，信息比率 {_num(vb.get('information_ratio'))}，"
            f"Beta {_num(vb.get('beta'))}，跟踪误差 {_pct(vb.get('tracking_error'))}，"
            f"相关性 {_num(vb.get('correlation'))}。"
        )
    return "".join(parts)


# ---------------------------------------------------------------------------
# SVG 绘图工具
# ---------------------------------------------------------------------------
def _heat_color(v):
    """月度热力图配色：正绿负红，深浅按幅度。"""
    if v is None:
        return "#f0f0f0"
    # 归一到 [0,1]，±8% 饱和
    cap = 0.08
    x = max(-1.0, min(1.0, v / cap))
    if x >= 0:
        # 白→绿
        g = int(120 + 100 * x)
        r = int(235 - 160 * x)
        b = int(235 - 160 * x)
        return f"rgb({r},{g},{b})"
    else:
        x = -x
        r = int(180 + 60 * x)
        g = int(235 - 170 * x)
        b = int(235 - 170 * x)
        return f"rgb({r},{g},{b})"


def _svg_line_chart(series_dict, width=760, height=200, color="#2b6cb0",
                    fill=False, zero_line=False, title=""):
    """把 {date_str: value} 画成 SVG 折线。"""
    items = list(series_dict.items())
    if len(items) < 2:
        return f'<div class="chart-empty">（{html.escape(title)} 数据不足）</div>'
    values = [v for _, v in items]
    vmin, vmax = min(values), max(values)
    if zero_line:
        vmin = min(vmin, 0.0)
        vmax = max(vmax, 0.0)
    if vmax == vmin:
        vmax = vmin + 1e-9
    pad_l, pad_r, pad_t, pad_b = 50, 12, 12, 24
    pw = width - pad_l - pad_r
    ph = height - pad_t - pad_b
    n = len(items)

    def x(i):
        return pad_l + pw * i / (n - 1)

    def y(v):
        return pad_t + ph * (1 - (v - vmin) / (vmax - vmin))

    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, (_, v) in enumerate(items))
    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" '
             f'preserveAspectRatio="xMidYMid meet" class="svg-chart">']
    # 网格 + y 轴标签
    for frac in (0, 0.25, 0.5, 0.75, 1.0):
        gv = vmin + (vmax - vmin) * frac
        gy = y(gv)
        parts.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width - pad_r}" '
                     f'y2="{gy:.1f}" stroke="#eee" stroke-width="1"/>')
        parts.append(f'<text x="{pad_l - 6}" y="{gy + 3:.1f}" text-anchor="end" '
                     f'font-size="10" fill="#888">{gv:.3g}</text>')
    if zero_line and vmin < 0 < vmax:
        zy = y(0.0)
        parts.append(f'<line x1="{pad_l}" y1="{zy:.1f}" x2="{width - pad_r}" '
                     f'y2="{zy:.1f}" stroke="#bbb" stroke-width="1" stroke-dasharray="3,3"/>')
    if fill:
        area = f"{pad_l},{pad_t + ph} " + pts + f" {x(n - 1):.1f},{pad_t + ph}"
        parts.append(f'<polygon points="{area}" fill="{color}22"/>')
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.6"/>')
    # x 轴首末日期
    parts.append(f'<text x="{pad_l}" y="{height - 6}" font-size="10" fill="#888">{items[0][0]}</text>')
    parts.append(f'<text x="{width - pad_r}" y="{height - 6}" text-anchor="end" '
                 f'font-size="10" fill="#888">{items[-1][0]}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _svg_dual_axis(nav_dict, dd_dict, width=760, height=240):
    """净值（上，蓝线）+ 回撤（下，红色填充）双轴图。"""
    nav_items = list(nav_dict.items())
    if len(nav_items) < 2:
        return '<div class="chart-empty">（净值数据不足）</div>'
    pad_l, pad_r, pad_t, pad_b = 50, 50, 12, 24
    pw = width - pad_l - pad_r
    # 上下分区：净值占 62%，回撤占 34%
    nav_h = (height - pad_t - pad_b) * 0.6
    dd_top = pad_t + nav_h + 10
    dd_h = (height - pad_t - pad_b) * 0.34

    nav_vals = [v for _, v in nav_items]
    nmin, nmax = min(nav_vals), max(nav_vals)
    if nmax == nmin:
        nmax = nmin + 1e-9
    n = len(nav_items)

    def x(i):
        return pad_l + pw * i / (n - 1)

    def ny(v):
        return pad_t + nav_h * (1 - (v - nmin) / (nmax - nmin))

    dd_vals = [dd_dict.get(d, 0.0) for d, _ in nav_items]
    dmin = min(dd_vals + [0.0])   # 最深回撤（负）
    if dmin == 0:
        dmin = -1e-9

    def dy(v):
        # 0 在顶，dmin 在底
        return dd_top + dd_h * (v / dmin)

    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" '
             f'preserveAspectRatio="xMidYMid meet" class="svg-chart">']
    # 净值网格
    for frac in (0, 0.5, 1.0):
        gv = nmin + (nmax - nmin) * frac
        gy = ny(gv)
        parts.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width - pad_r}" '
                     f'y2="{gy:.1f}" stroke="#eee"/>')
        parts.append(f'<text x="{pad_l - 6}" y="{gy + 3:.1f}" text-anchor="end" '
                     f'font-size="10" fill="#2b6cb0">{gv:.3f}</text>')
    nav_pts = " ".join(f"{x(i):.1f},{ny(v):.1f}" for i, (_, v) in enumerate(nav_items))
    parts.append(f'<polyline points="{nav_pts}" fill="none" stroke="#2b6cb0" stroke-width="1.8"/>')
    parts.append(f'<text x="{pad_l}" y="{pad_t - 0}" font-size="11" fill="#2b6cb0">净值(左轴)</text>')

    # 回撤填充（红）
    dd_area = f"{pad_l},{dd_top} " + \
        " ".join(f"{x(i):.1f},{dy(v):.1f}" for i, v in enumerate(dd_vals)) + \
        f" {x(n - 1):.1f},{dd_top}"
    parts.append(f'<polygon points="{dd_area}" fill="#e5393533" stroke="#e53935" stroke-width="1"/>')
    parts.append(f'<text x="{width - pad_r + 4}" y="{dd_top + 4}" font-size="10" fill="#e53935">0%</text>')
    parts.append(f'<text x="{width - pad_r + 4}" y="{dd_top + dd_h:.0f}" font-size="10" '
                 f'fill="#e53935">{dmin * 100:.1f}%</text>')
    parts.append(f'<text x="{pad_l}" y="{dd_top - 2}" font-size="11" fill="#e53935">回撤(右轴)</text>')
    parts.append(f'<text x="{pad_l}" y="{height - 6}" font-size="10" fill="#888">{nav_items[0][0]}</text>')
    parts.append(f'<text x="{width - pad_r}" y="{height - 6}" text-anchor="end" '
                 f'font-size="10" fill="#888">{nav_items[-1][0]}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _heatmap_html(monthly: dict) -> str:
    years = monthly.get("years", [])
    matrix = monthly.get("matrix", [])
    if not years:
        return '<div class="chart-empty">（月度数据不足）</div>'
    month_names = ["1月", "2月", "3月", "4月", "5月", "6月",
                   "7月", "8月", "9月", "10月", "11月", "12月"]
    rows = ['<table class="heatmap"><thead><tr><th>年\\月</th>' +
            "".join(f"<th>{m}</th>" for m in month_names) +
            '<th>全年</th></tr></thead><tbody>']
    for y, row in zip(years, matrix):
        cells = [f"<th>{y}</th>"]
        year_prod = 1.0
        has = False
        for v in row:
            if v is None:
                cells.append('<td class="na"></td>')
            else:
                year_prod *= (1.0 + v)
                has = True
                cells.append(f'<td style="background:{_heat_color(v)}">{v * 100:.1f}</td>')
        yr = (year_prod - 1.0) if has else None
        yr_cell = "" if yr is None else f"{yr * 100:.1f}"
        yr_bg = _heat_color(yr) if yr is not None else "#f0f0f0"
        cells.append(f'<td class="year" style="background:{yr_bg}">{yr_cell}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    rows.append("</tbody></table>")
    return "".join(rows)


def _metric_card(label, value, sub=""):
    sub_html = f'<div class="card-sub">{html.escape(sub)}</div>' if sub else ""
    return (f'<div class="card"><div class="card-label">{html.escape(label)}</div>'
            f'<div class="card-value">{html.escape(str(value))}</div>{sub_html}</div>')


def _drawdown_table_html(dd: list) -> str:
    if not dd:
        return '<p class="muted">无回撤区间</p>'
    rows = ['<table class="dd-table"><thead><tr>'
            '<th>#</th><th>峰值日</th><th>谷底日</th><th>恢复日</th>'
            '<th>深度</th><th>回撤天数</th><th>恢复天数</th></tr></thead><tbody>']
    for i, e in enumerate(dd, 1):
        rec = e.get("recover_date") or "未恢复"
        recd = e.get("recovery_days")
        recd = "—" if recd is None else recd
        rows.append(
            f"<tr><td>{i}</td><td>{e.get('peak_date')}</td>"
            f"<td>{e.get('trough_date')}</td><td>{rec}</td>"
            f"<td class='neg'>{_pct(e.get('depth'))}</td>"
            f"<td>{e.get('drawdown_days')}</td><td>{recd}</td></tr>"
        )
    rows.append("</tbody></table>")
    return "".join(rows)


# ---------------------------------------------------------------------------
# HTML 主渲染
# ---------------------------------------------------------------------------
def to_html(t: dict, title: str = "策略绩效 Tearsheet") -> str:
    s = t["summary"]
    ra = t["risk_adjusted"]
    dist = t["distribution"]
    summary_text = build_summary_text(t)

    cards = "".join([
        _metric_card("累计收益", _pct(s["cumulative_return"])),
        _metric_card("年化收益", _pct(s["annualized_return"])),
        _metric_card("年化波动", _pct(s["annualized_vol"])),
        _metric_card("最大回撤", _pct(s["max_drawdown"])),
        _metric_card("夏普比率", _num(ra["sharpe"])),
        _metric_card("索提诺", _num(ra["sortino"])),
        _metric_card("Calmar", _num(ra["calmar"])),
        _metric_card("Omega", _num(ra["omega"])),
        _metric_card("胜率", _pct(s["win_rate"], 1)),
        _metric_card("盈亏比", _num(s["profit_loss_ratio"])),
        _metric_card("偏度", _num(dist["skewness"])),
        _metric_card("超额峰度", _num(dist["kurtosis"])),
        _metric_card("VaR(95%)", _pct(dist["var_95"])),
        _metric_card("CVaR(95%)", _pct(dist["cvar_95"])),
        _metric_card("最优单期", _pct(s["best_period"])),
        _metric_card("最差单期", _pct(s["worst_period"])),
    ])

    vb_html = ""
    vb = t.get("vs_benchmark")
    if vb:
        vb_cards = "".join([
            _metric_card("超额年化", _pct(vb.get("excess_annual"))),
            _metric_card("信息比率", _num(vb.get("information_ratio"))),
            _metric_card("Beta", _num(vb.get("beta"))),
            _metric_card("跟踪误差", _pct(vb.get("tracking_error"))),
            _metric_card("相关性", _num(vb.get("correlation"))),
        ])
        vb_html = (f'<h2>相对基准</h2><div class="cards">{vb_cards}</div>')

    dual = _svg_dual_axis(t.get("nav_curve", {}), t.get("rolling", {}).get("drawdown", {}))
    rs_chart = _svg_line_chart(t.get("rolling", {}).get("sharpe", {}),
                               color="#6a1b9a", zero_line=True, title="滚动夏普")
    heat = _heatmap_html(t.get("monthly_returns", {}))
    dd_table = _drawdown_table_html(t.get("drawdowns", []))

    css = """
    :root{--fg:#1a202c;--muted:#718096;--border:#e2e8f0;--bg:#f7fafc;}
    *{box-sizing:border-box;}
    body{font-family:-apple-system,'PingFang SC','Microsoft YaHei',Helvetica,Arial,sans-serif;
        margin:0;color:var(--fg);background:var(--bg);line-height:1.5;}
    .wrap{max-width:840px;margin:0 auto;padding:24px 20px 60px;}
    h1{font-size:22px;margin:0 0 4px;}
    h2{font-size:16px;margin:28px 0 12px;border-left:4px solid #2b6cb0;padding-left:8px;}
    .meta{color:var(--muted);font-size:13px;margin-bottom:16px;}
    .cards{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;}
    .card{background:#fff;border:1px solid var(--border);border-radius:8px;padding:10px 12px;}
    .card-label{font-size:12px;color:var(--muted);}
    .card-value{font-size:18px;font-weight:600;margin-top:2px;}
    .card-sub{font-size:11px;color:var(--muted);}
    .panel{background:#fff;border:1px solid var(--border);border-radius:8px;padding:14px;margin-top:10px;}
    .svg-chart{display:block;}
    .chart-empty{color:var(--muted);font-size:13px;padding:20px;text-align:center;}
    table{border-collapse:collapse;width:100%;font-size:12px;}
    .heatmap th,.heatmap td{border:1px solid #fff;padding:5px 4px;text-align:center;}
    .heatmap thead th{background:#2b6cb0;color:#fff;}
    .heatmap tbody th{background:#edf2f7;font-weight:600;}
    .heatmap td.na{background:#f0f0f0;}
    .heatmap td.year{font-weight:600;}
    .dd-table th,.dd-table td{border-bottom:1px solid var(--border);padding:6px 8px;text-align:center;}
    .dd-table thead th{background:#edf2f7;}
    .neg{color:#c53030;}
    .muted{color:var(--muted);}
    .summary{background:#fffbeb;border:1px solid #f6e05e;border-radius:8px;padding:14px 16px;
        font-size:14px;margin-top:10px;}
    .disclaimer{margin-top:32px;padding-top:14px;border-top:1px dashed var(--border);
        color:var(--muted);font-size:12px;}
    @media(max-width:640px){.cards{grid-template-columns:repeat(2,1fr);}}
    """

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{css}</style>
</head>
<body>
<div class="wrap">
  <h1>{html.escape(title)}</h1>
  <div class="meta">
    区间 {t.get('start_date')} ~ {t.get('end_date')} ·
    {t['n_periods']} 期 · 年化期数 {t['periods_per_year']} ·
    无风险利率 {_pct(t.get('rf_annual'))} · 数据后端 {t.get('backend', 'n/a')}
  </div>

  <h2>关键指标</h2>
  <div class="cards">{cards}</div>

  {vb_html}

  <h2>净值与回撤</h2>
  <div class="panel">{dual}</div>

  <h2>滚动夏普（窗口 {t.get('rolling_window')} 期）</h2>
  <div class="panel">{rs_chart}</div>

  <h2>月度收益热力图（%）</h2>
  <div class="panel">{heat}</div>

  <h2>Top-N 回撤区间</h2>
  <div class="panel">{dd_table}</div>

  <h2>中文摘要</h2>
  <div class="summary">{html.escape(summary_text)}</div>

  <div class="disclaimer">
    ⚠️ 免责声明：本报告仅供研究参考，不构成投资建议。历史绩效不代表未来表现。
    年化指标依赖 periods_per_year 与序列频率一致，否则夏普等会失真。
  </div>
</div>
</body>
</html>"""
