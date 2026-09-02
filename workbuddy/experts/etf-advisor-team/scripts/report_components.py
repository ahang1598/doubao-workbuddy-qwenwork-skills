# -*- coding: utf-8 -*-
"""report_components.py — 结构化数据组件库（v26）

把 forecast.json 等结构化数据**用代码直接从 JSON 渲染为 HTML 块**，通过占位符在
markdown 出数据处定位入槽（杜绝 LLM 手敲数字漂移；单一可信源 SSOT = forecast.json）：

    [[table:KEY]]   表格组件（利润表 income_statement / 现金流量表 cash_flow /
                    三表预测 three_statement / 与卖方一致预期对比 vs_consensus /
                    DCF 三阶段假设披露 dcf …）
    [[card:KEY]]    卡片组件（卖方一致预期速览 consensus …）
    [[matrix:KEY]]  矩阵组件（六面方向矩阵 …）        ← 预留扩展

注入入口 :func:`inject_data_components` 在 markdown→html 之后、表格自动编号
（number_tables）之前调用：渲染出的 `<table>` 会被 number_tables 自动包成
`<figure class="table-figure" id="tab-N">` 并编号"表 N"，与正文手写表统一。

设计原则：
  * 渲染器**只读 JSON、不改 JSON**——上游数据若有误（如折旧计算 bug），组件会
    如实呈现，由 forecast_engine 端修正，而非在渲染端"美化掩盖"。
  * 未知组件 / 无数据 → 整段删除占位符，**不把 `[[table:xxx]]` 字面量泄漏到页面**。
  * 每个组件 = 一个 `render_<key>(data) -> str|None` 函数（返回 None 表示数据缺失）。
"""
import re
import html as _html

# ── 占位符 token：[[table:KEY]] / [[card:KEY]] / [[matrix:KEY]]（兼容外层 <p> 包裹与全角冒号）
#    与图表占位符 [[chart:KEY]]/[[图:KEY]] 命名空间互不重叠（kind ∈ table/card/matrix）。
_DATA_COMPONENT_RE = re.compile(
    r"(?:<p>\s*)?\[\[\s*(table|card|matrix)\s*[:：]\s*([A-Za-z_][\w\-]*)\s*\]\](?:\s*</p>)?",
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════════════
#  格式化原语
# ═══════════════════════════════════════════════════════════════════
def _esc(s) -> str:
    return _html.escape(str(s), quote=True)


def _g(d, *path, default=None):
    """安全多级取值：_g(data, 'L4', 'base', 'year_1')。"""
    cur = d
    for k in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def _num(v, nd=1):
    """数值 → 千分位字符串；None/空/非数 → '—'。"""
    if v is None or v == "":
        return "—"
    try:
        return f"{float(v):,.{nd}f}"
    except (TypeError, ValueError):
        return _esc(v)


def _pct(v, nd=1, sign=False):
    if v is None or v == "":
        return "—"
    try:
        f = float(v)
        return f"{f:+.{nd}f}%" if sign else f"{f:.{nd}f}%"
    except (TypeError, ValueError):
        return _esc(v)


# 组件表统一样式（仅注入一次；放在首个组件 HTML 前由 inject 负责去重）
_COMP_CSS = (
    "<style>"
    ".fc-comp{width:100%;border-collapse:collapse;margin:6px 0;font-size:13px}"
    ".fc-comp caption{caption-side:top;text-align:left;font-weight:700;color:#1f2733;"
    "padding:2px 0 8px;font-size:13.5px}"
    ".fc-comp caption .fc-sub{display:block;font-weight:400;color:#8a93a0;font-size:11.5px;margin-top:2px}"
    ".fc-comp th,.fc-comp td{border:1px solid #e2e6ea;padding:6px 10px;text-align:right}"
    ".fc-comp thead th{background:#f3f5f7;color:#33404f;text-align:right;font-weight:600}"
    ".fc-comp thead th:first-child,.fc-comp tbody th{text-align:left;font-weight:500;color:#33404f;background:#fafbfc}"
    ".fc-comp tr.row-strong td,.fc-comp tr.row-strong th{font-weight:700;background:#fbf2f0;color:#1f2733}"
    ".fc-comp tr.row-sub th{padding-left:20px;color:#5a6573;font-weight:400}"
    ".fc-comp .dev-neg{color:#c0392b}.fc-comp .dev-pos{color:#1e8449}"
    # 卡片组件（[[card:KEY]]）样式
    ".fc-card{border:1px solid #e2e6ea;border-radius:8px;padding:12px 16px;margin:10px 0;background:#fafbfc}"
    ".fc-card-title{font-weight:700;color:#1f2733;font-size:14px;margin-bottom:10px;"
    "border-left:3px solid #d84033;padding-left:8px}"
    ".fc-card-title .fc-card-sub{display:block;font-weight:400;color:#8a93a0;font-size:11px;"
    "margin-top:2px;border:0;padding:0}"
    ".fc-card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px 16px}"
    ".fc-card-item{display:flex;flex-direction:column;padding:4px 0}"
    ".fc-card-k{color:#8a93a0;font-size:11.5px}"
    ".fc-card-v{color:#1f2733;font-size:14px;font-weight:600}"
    "</style>"
)


def _table(caption, sub, head, rows) -> str:
    """构造一张组件表：
      caption: 主标题（不含"表 N"，编号由 number_tables 统一分配为 figcaption）
      sub:     副标题（单位 / 数据来源），可为 None
      head:    表头单元格列表（首列为行项名占位）
      rows:    [(label, [cells...], css_class_or_None), ...]
    返回完整 <table>（含内部 <caption>），整体会被 number_tables 包 figure 并编号。
    """
    sub_html = f'<span class="fc-sub">{_esc(sub)}</span>' if sub else ""
    th = "".join(f"<th>{_esc(h)}</th>" for h in head)
    body = []
    for label, cells, cls in rows:
        c = f' class="{cls}"' if cls else ""
        tds = "".join(f"<td>{c2}</td>" for c2 in cells)
        body.append(f'<tr{c}><th scope="row">{_esc(label)}</th>{tds}</tr>')
    return (
        f'<table class="fc-comp"><caption>{_esc(caption)}{sub_html}</caption>'
        f'<thead><tr>{th}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table>'
    )


# ═══════════════════════════════════════════════════════════════════
#  组件：利润表预测（L4 + base_year）
# ═══════════════════════════════════════════════════════════════════
def render_income_statement(data, scenario: str = "base") -> str:
    """利润表预测：基期实际(2025A) + L4[scenario] 三年(2026E/2027E/2028E)。

    数据全部来自 forecast.json 的 L4[scenario].year_1/2/3 与 base_year，
    与正文手敲不同——此处零漂移。
    """
    L4 = _g(data, "L4", scenario, default={})
    yrs = [L4.get("year_1"), L4.get("year_2"), L4.get("year_3")]
    yrs = [y for y in yrs if isinstance(y, dict)]
    if not yrs:
        return None

    by = _g(data, "base_year", default={})
    base_period = str(_g(by, "base_year_period", default="") or "")
    base_label = (base_period[:4] + "A") if base_period[:4].isdigit() else "基期A"
    year_heads = [f'{y.get("year_label", "")}E' for y in yrs]
    head = ["利润表（亿元）", base_label] + year_heads
    sc_cn = {"base": "Base 中性", "bull": "Bull 乐观", "bear": "Bear 悲观"}.get(scenario, scenario)

    def col(getter, base_val, nd=1, fn=_num):
        return [fn(base_val, nd)] + [fn(getter(y), nd) for y in yrs]

    rows = [
        ("营业收入", col(lambda y: y.get("revenue_yi"),
                     _g(by, "base_year_revenue_yi")), None),
        ("　同比增速", [_pct(None)] + [_pct(y.get("revenue_growth_pct"), 1, sign=True) for y in yrs], "row-sub"),
        ("营业成本", [_num(None)] + [_num((y.get("revenue_yi") or 0) - (y.get("gross_profit_yi") or 0)
                                       if y.get("gross_profit_yi") is not None else None) for y in yrs], None),
        ("毛利润", [_num(None)] + [_num(y.get("gross_profit_yi")) for y in yrs], None),
        ("　毛利率", col(lambda y: y.get("gross_margin_pct"),
                     _g(by, "base_year_gross_margin_pct"), 1, _pct), "row-sub"),
        ("销售费用", [_num(None)] + [_num(y.get("sales_exp_yi")) for y in yrs], None),
        ("管理费用", [_num(None)] + [_num(y.get("mgmt_exp_yi")) for y in yrs], None),
        ("研发费用", [_num(None)] + [_num(y.get("rd_exp_yi")) for y in yrs], None),
        ("财务费用", [_num(None)] + [_num(y.get("fin_exp_yi")) for y in yrs], None),
        ("营业利润", [_num(None)] + [_num(y.get("op_profit_yi")) for y in yrs], None),
        ("归母净利润", col(lambda y: y.get("net_profit_parent_yi"),
                      _g(by, "base_year_net_profit_yi")), "row-strong"),
        ("EPS（元）", col(lambda y: y.get("eps"),
                       _g(by, "base_year_eps"), 2), None),
    ]
    return _table(
        "利润表预测",
        f"{sc_cn}情景 · 单位：亿元 · 来源：forecast.json（historical→assumptions→forecast 三件套）",
        head, rows,
    )


# ═══════════════════════════════════════════════════════════════════
#  组件：现金流量表预测（L5_three_statement，简化间接法）
# ═══════════════════════════════════════════════════════════════════
def render_cash_flow(data, scenario: str = "base") -> str:
    """现金流量表预测（简化间接法）：L5_three_statement[scenario] 三年。

    CFO = 净利润 + 折旧摊销 − Δ应收 − Δ存货 + Δ应付；FCF = CFO − CAPEX。
    """
    ts = _g(data, "L5_three_statement", scenario, default={})
    yrs = [ts.get("year_1"), ts.get("year_2"), ts.get("year_3")]
    yrs = [y for y in yrs if isinstance(y, dict)]
    if not yrs:
        return None

    head = ["现金流量表（亿元）"] + [f'{y.get("year_label", "")}E' for y in yrs]
    sc_cn = {"base": "Base 中性", "bull": "Bull 乐观", "bear": "Bear 悲观"}.get(scenario, scenario)

    def r(key, nd=1):
        return [_num(y.get(key), nd) for y in yrs]

    rows = [
        ("归母净利润", r("net_profit_parent_yi"), None),
        ("（＋）折旧摊销", r("depreciation_yi"), "row-sub"),
        ("（－）应收账款增加", r("delta_ar_yi"), "row-sub"),
        ("（－）存货增加", r("delta_inventory_yi"), "row-sub"),
        ("（＋）应付账款增加", r("delta_ap_yi"), "row-sub"),
        ("经营活动现金流（CFO）", r("cfo_yi"), "row-strong"),
        ("（－）资本开支（CAPEX）", r("capex_yi"), "row-sub"),
        ("自由现金流（FCF）", r("fcf_yi"), "row-strong"),
        ("CFO/归母净利（倍）", r("cfo_to_net_profit", 2), None),
        ("现金转换周期（天）", r("ccc_days", 0), None),
    ]
    return _table(
        "现金流量表预测",
        f"{sc_cn}情景 · 简化间接法 CFO=净利+折旧−Δ应收−Δ存货+Δ应付，FCF=CFO−CAPEX · 来源：forecast.json",
        head, rows,
    )


# ═══════════════════════════════════════════════════════════════════
#  组件：三表预测（利润表 + 现金流量表）
# ═══════════════════════════════════════════════════════════════════
def render_three_statement(data, scenario: str = "base") -> str:
    """三表预测组件：利润表(L4) + 现金流量表(L5_three_statement)，同一情景逐年。"""
    parts = [p for p in (render_income_statement(data, scenario),
                         render_cash_flow(data, scenario)) if p]
    return "\n".join(parts) if parts else None


# ═══════════════════════════════════════════════════════════════════
#  组件：与卖方一致预期对比（L4[scenario] × market_consensus）
# ═══════════════════════════════════════════════════════════════════
def _dev_cell(ours, cons):
    """偏差单元格：(本报告−一致)/一致，带正负色标；任一缺失 → '—'。"""
    try:
        o, c = float(ours), float(cons)
    except (TypeError, ValueError):
        return "—", None
    if c == 0:
        return "—", None
    d = (o - c) / c * 100.0
    cls = "dev-neg" if d < 0 else ("dev-pos" if d > 0 else None)
    return f"{d:+.1f}%", cls


def render_vs_consensus(data, scenario: str = "base") -> str:
    """与卖方一致预期对比表：本报告 L4[scenario] 的营收/EPS vs market_consensus 中位。

    彻底取代正文手敲对比表（历史上 726/1100 等漂移即源于此），数字全部 JSON 派生。
    偏差列在渲染端实时计算 (本报告−一致)/一致，杜绝手算误差。
    """
    L4 = _g(data, "L4", scenario, default={})
    mc = _g(data, "market_consensus", default={})
    y1 = L4.get("year_1") or {}
    y2 = L4.get("year_2") or {}
    if not mc or (not y1 and not y2):
        return None

    sc_cn = {"base": "Base 中性", "bull": "Bull 乐观", "bear": "Bear 悲观"}.get(scenario, scenario)

    # (行项, 本报告值, 一致预期值, 小数位)
    specs = [
        ("2026E 营业收入（亿）", y1.get("revenue_yi"), _g(mc, "revenue_2026e", "median"), 1),
        ("2026E EPS（元）", y1.get("eps"), _g(mc, "eps_2026e", "median"), 2),
        ("2027E 营业收入（亿）", y2.get("revenue_yi"), _g(mc, "revenue_2027e", "median"), 1),
        ("2027E EPS（元）", y2.get("eps"), _g(mc, "eps_2027e", "median"), 2),
    ]
    rows = []
    for label, ours, cons, nd in specs:
        dev_txt, dev_cls = _dev_cell(ours, cons)
        cells = [
            _num(ours, nd),
            _num(cons, nd),
            (f'<span class="{dev_cls}">{dev_txt}</span>' if dev_cls else dev_txt),
        ]
        rows.append((label, cells, None))

    head = ["指标", f"本报告（{sc_cn}）", "卖方一致预期（中位）", "偏差"]
    return _table(
        "与卖方一致预期对比",
        "本报告来自 forecast.json（L4 三表预测）× 卖方一致预期来自 market_consensus（consensus.json 中位数）· 偏差=（本报告−一致）/一致",
        head, rows,
    )


# ═══════════════════════════════════════════════════════════════════
#  组件：卖方一致预期速览卡（market_consensus）
# ═══════════════════════════════════════════════════════════════════
def render_consensus_card(data) -> str:
    """卖方一致预期速览卡：覆盖机构数 / 评级分布 / 2026E·2027E EPS·营收中位。

    纯展示 market_consensus，零口径分歧。
    """
    mc = _g(data, "market_consensus", default={})
    if not mc:
        return None
    rec = _g(mc, "analyst_recommendation", default={})
    buy = _g(rec, "buy_count")
    hold = _g(rec, "hold_count")
    eps26 = _g(mc, "eps_2026e", default={})
    rev26 = _g(mc, "revenue_2026e", "median")
    eps27 = _g(mc, "eps_2027e", "median")
    rev27 = _g(mc, "revenue_2027e", "median")
    bc = _g(eps26, "broker_count")

    items = []
    if bc is not None:
        items.append(("覆盖机构", f"{_num(bc, 0)} 家"))
    if buy is not None or hold is not None:
        items.append(("评级分布", f"买入 {_num(buy, 0)} / 增持·持有 {_num(hold, 0)}"))
    if eps26.get("median") is not None:
        lo, hi = eps26.get("low"), eps26.get("high")
        rng = f"（{_num(lo, 2)}–{_num(hi, 2)}）" if lo is not None and hi is not None else ""
        items.append(("2026E EPS 中位", f"{_num(eps26.get('median'), 2)} 元{rng}"))
    if rev26 is not None:
        items.append(("2026E 营收中位", f"{_num(rev26, 1)} 亿"))
    if eps27 is not None:
        items.append(("2027E EPS 中位", f"{_num(eps27, 2)} 元"))
    if rev27 is not None:
        items.append(("2027E 营收中位", f"{_num(rev27, 1)} 亿"))
    if not items:
        return None

    cells = "".join(
        f'<div class="fc-card-item"><span class="fc-card-k">{_esc(k)}</span>'
        f'<span class="fc-card-v">{_esc(v)}</span></div>'
        for k, v in items
    )
    return (
        '<div class="fc-card"><div class="fc-card-title">卖方一致预期速览'
        '<span class="fc-card-sub">来源：market_consensus（consensus.json，仅作锚定参考，非本报告观点）</span>'
        f'</div><div class="fc-card-grid">{cells}</div></div>'
    )


# ═══════════════════════════════════════════════════════════════════
#  组件：DCF 假设披露 + 分阶段拆解（valuation.dcf 三档）
# ═══════════════════════════════════════════════════════════════════
def render_dcf_disclosure(data) -> str:
    """三阶段 DCF 假设透明披露表：bull/base/bear 三档并列。

    上半部「输入假设」让用户一眼核对合理性（显式期/衰减期/FCF 转化率/WACC/永续 g/
    衰减区间增速/股本）；下半部「分阶段结果」拆出 显式期现值 + 衰减期现值 + 永续期现值
    → 股权价值 → 每股价值。所有数字均来自 forecast.json["valuation"]["dcf"]，零手敲。

    若某档 FCF 转化率为引擎默认（yaml 未研判），在该值后标注「⚠默认」提醒补研判。
    """
    dcf = _g(data, "valuation", "dcf", default={})
    if not dcf:
        return None
    cols = ["bull", "base", "bear"]
    col_cn = {"bull": "Bull 乐观", "base": "Base 中性", "bear": "Bear 悲观"}
    # 至少 base 档要有结果
    if dcf.get("base", {}).get("dcf_per_share") is None and \
       all(dcf.get(s, {}).get("dcf_per_share") is None for s in cols):
        return None

    def cell(scenario, key, nd=1, fn=_num, pct=False, fcf_flag=False):
        d = dcf.get(scenario, {})
        v = d.get(key)
        if v is None:
            return "—"
        if pct:
            txt = _pct(v, nd, sign=False)
        else:
            txt = fn(v, nd)
        if fcf_flag and d.get("fcf_to_np_source") == "engine_default":
            txt = f'{txt}<span class="dev-neg"> ⚠默认</span>'
        return txt

    # (行项, key, 小数位, 是否百分比, 是否FCF标注, css)
    assum_rows = [
        ("显式预测期（年）", "explicit_years", 0, False, False, "row-sub"),
        ("增长衰减期（年）", "fade_years", 0, False, False, "row-sub"),
        ("FCF/归母净利 转化率", "fcf_to_np_ratio", 2, False, True, "row-sub"),
        ("WACC（%）", "wacc_pct", 2, True, False, "row-sub"),
        ("永续增长率 g（%）", "terminal_growth_pct", 2, True, False, "row-sub"),
        ("衰减期起始增速（%）", "stage2_growth_start_pct", 1, True, False, "row-sub"),
        ("衰减期末增速（%）", "stage2_growth_end_pct", 1, True, False, "row-sub"),
        ("基准股本（亿股）", "share_count_base_yi", 2, False, False, "row-sub"),
    ]
    result_rows = [
        ("显式期现值（亿）", "pv_stage1_yi", 1, False, False, None),
        ("衰减期现值（亿）", "pv_stage2_yi", 1, False, False, None),
        ("永续期现值（亿）", "terminal_pv_yi", 1, False, False, None),
        ("股权价值合计（亿）", "equity_value_yi", 1, False, False, None),
        ("每股价值（元）", "dcf_per_share", 2, False, False, "row-strong"),
    ]

    rows = []
    # 分隔小标题行（用 row-sub 风格的伪表头，借 label 列）
    for label, key, nd, pct, fcf_flag, cls in assum_rows:
        cells = [cell(s, key, nd, _num, pct, fcf_flag) for s in cols]
        rows.append((label, cells, cls))
    for label, key, nd, pct, fcf_flag, cls in result_rows:
        cells = [cell(s, key, nd, _num, pct, fcf_flag) for s in cols]
        rows.append((label, cells, cls))

    head = ["DCF 三阶段（输入假设 / 分阶段结果）"] + [col_cn[s] for s in cols]
    return _table(
        "DCF 三阶段估值：假设披露与分阶段拆解",
        "结构=显式期(L4 逐年净利×转化率折现)+衰减期(增速线性回落至永续)+永续期(Gordon) · "
        "全部假设来自 assumptions.yaml(valuation_inputs) 经 LLM 研判 · 数值来源 forecast.json · "
        "「⚠默认」表示该档 FCF 转化率未研判、用了引擎默认值需复核",
        head, rows,
    )


# ═══════════════════════════════════════════════════════════════════
#  组件注册表 & 注入入口
# ═══════════════════════════════════════════════════════════════════
#: (kind, key) -> render_fn(data) -> str|None
_RENDERERS = {
    ("table", "three_statement"): render_three_statement,
    ("table", "income_statement"): render_income_statement,
    ("table", "is"): render_income_statement,            # 别名
    ("table", "cash_flow"): render_cash_flow,
    ("table", "cashflow"): render_cash_flow,             # 别名
    ("table", "vs_consensus"): render_vs_consensus,
    ("table", "consensus"): render_vs_consensus,         # 别名
    ("card", "consensus"): render_consensus_card,
    ("table", "dcf"): render_dcf_disclosure,
    ("table", "dcf_disclosure"): render_dcf_disclosure,  # 别名
    ("table", "dcf_assumptions"): render_dcf_disclosure, # 别名
}


def inject_data_components(html: str, forecast_data: dict, id_prefix: str = "") -> str:
    """扫描 `[[table:KEY]]` / `[[card:KEY]]` / `[[matrix:KEY]]` 占位符，用代码从
    forecast_data 渲染对应 HTML 块整段替换之。

    调用时机：markdown→html 之后、number_tables 之前（这样渲染出的表会被自动编号）。
    未知组件 / 无数据 / 渲染异常 → 整段删除占位符（不泄漏 `[[...]]` 字面量）。
    多个组件复用同一份 `<style>`：仅在首个成功渲染前注入一次。
    """
    if not html:
        return html
    state = {"css_done": False}

    def _repl(m):
        kind, key = m.group(1).lower(), m.group(2).lower()
        fn = _RENDERERS.get((kind, key))
        if fn is None or not forecast_data:
            return ""  # 未知组件 / 无数据 → 删除占位符
        try:
            out = fn(forecast_data)
        except Exception:
            out = None
        if not out:
            return ""
        if not state["css_done"]:
            state["css_done"] = True
            return _COMP_CSS + out
        return out

    return _DATA_COMPONENT_RE.sub(_repl, html)
