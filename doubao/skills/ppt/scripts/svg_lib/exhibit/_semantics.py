"""Chart-semantics guards (business-research chart standard §0.3–0.5): periods are categories, not stack segments;
CAGR only on amounts, within one actual/forecast regime, naming its series; one axis = one unit; side-by-side
magnitude panels share a scale; uneven time gaps are not drawn equidistant; a footnote that says 不可比 forbids
change annotations. Each guard is small and either raises with the right alternative or records an issue."""

from __future__ import annotations

import re

_PERIOD_SEG = re.compile(r"(?:FY|CY)?\s*'?(?:19|20)?\d{2}\s*(?:年度?)?\s*[AEFPB]?(?:年[EF]?|E年)?|"
                         r"(?:FY\s*)?'?\d{2,4}\s*[-/]?\s*(?:Q[1-4]|H[12]|[1-4]Q|[12]H)[AEF]?|(?:Q[1-4]|H[12])\s*'?\d{0,4}|"
                         r"去年|今年|上年|本年|同期|上期|本期", re.I)


def periods_as_segments(names, where):
    """Stack / 100 %-stack / marimekko segments must be components; years or periods go on the category axis."""
    names = [str(n).strip() for n in names]
    if len(names) >= 2 and all(_PERIOD_SEG.fullmatch(n) for n in names):
        raise ValueError(f"{where}：分段 {names[:4]} 是年份/期间——堆叠的分段必须是互斥可加的成分（业务/地区/客户）。"
                         "期间放类别轴：columns(ex, box, [期间…], [(成分, 各期值), …], stack='stack'|'percent')；"
                         "只比较各期规模就用普通柱")


_MULTIPLE = re.compile(r"^\s*(?:x|×|倍)\s*$|\bP/?E\b|\bP/?B\b|\bP/?S\b|PEG|EV\s*/\s*EBITDA|市盈率|市净率|市销率|估值倍数|"
                       r"[（(]\s*(?:x|×|倍)\s*[)）]", re.I)


def is_multiple(*texts):
    """A valuation multiple / ratio (PE, PB, EV/EBITDA, 'x', 倍) — CAGR of a multiple means nothing."""
    return any(t and _MULTIPLE.search(str(t)) for t in texts)


_FCST = re.compile(r"\d\s*[EF]$|[EF]年$|E年$|预测|预计|\bF$", re.I)


def is_forecast(cat):
    return bool(_FCST.search(str(cat).strip()))


def unit_kind(text):
    """'x' multiple, '%' rate, '¥' amount, or None for a label / unit string."""
    t = str(text or "")
    if is_multiple(t):
        return "x"
    if re.search(r"%|％|百分点|\bpp?t?\b|率|占比|份额|yield|margin|ratio", t, re.I):
        return "%"
    if re.search(r"亿|万元|千元|元|美元|\$|USD|RMB|CNY|\bbn\b|\bmn\b|百万|十亿", t, re.I):
        return "¥"
    return None


def mixed_units(labels, where, fix):
    """One value axis carrying two units (PB 'x' next to dividend yield '%') reads as comparable — refuse."""
    kinds = {}
    for lab in labels:
        k = unit_kind(lab)
        if k:
            kinds.setdefault(k, str(lab))
    cur = {}
    for lab in labels:   # 亿元 next to 亿港元 / 美元 / 港元每股: different currencies or per-share on one axis
        t = str(lab or "")
        c = ("港元" if re.search(r"港元|HKD|HK\$", t) else "美元" if re.search(r"美元|USD|US\$|\$", t)
             else "人民币" if re.search(r"人民币|RMB|CNY|亿元|万元", t) else None)
        if c:
            cur.setdefault(c + ("/股" if re.search(r"每股|/股|per share", t) else ""), t)
    if len(cur) >= 2:
        kinds = {**kinds, **{f"币种:{k}": v for k, v in cur.items()}}
    if len(kinds) >= 2:
        shown = "、".join(f"{v}（{k}）" for k, v in kinds.items())
        raise ValueError(f"{where}：同一根数轴混了不同单位：{shown}——位置会被读成可比。{fix}")


_NONCOMP = re.compile(r"不可比|口径不同|口径不一|不做同比|不宜比较|not (?:directly )?comparable|not like[- ]for[- ]like", re.I)


def noncomparable_guard(ex, what):
    """The page footnote says the figures are not comparable: a computed difference / growth on the chart contradicts
    it. Recorded as a chart issue (publish holds the page)."""
    from . import _frame
    said = getattr(_frame, "LAST_NOTES", "") or ""
    m = _NONCOMP.search(said)
    if m and ex is not None:
        from ._table import add_issue
        add_issue(ex, f"脚注写了'{m.group(0)}'，图上却标了{what}——不可比的两者不画差值/增速：删掉该标注，"
                      "改为分面各自标绝对值，或把可比的那部分单独成图")


_CALIBER = re.compile(r"(?:不)?含税[^。；;]{0,30}(?:不)?含税|新口径|旧口径|口径(?:调整|变更|变化|切换|改变)|会计准则(?:变更|调整)|"
                      r"重述|restat(?:ed|ement)|change (?:of|in) (?:basis|definition)", re.I)


def caliber_change_warn(ex, what):
    """The footnote / subtitle declares a caliber change (含税 vs 不含税, 新/旧口径, 口径调整, restated): a CAGR drawn across
    it compounds two definitions. Warning (print + review signal), not a hold — the span may lie on one side of it."""
    from . import _frame
    said = " ".join(str(getattr(_frame, k, "") or "") for k in ("LAST_NOTES", "LAST_SUBTITLE"))
    m = _CALIBER.search(said)
    if not m:
        return None
    from ._page import SIGNALS
    if "跨口径 CAGR" not in SIGNALS:
        SIGNALS.append("跨口径 CAGR")
    print(f"口径提醒：脚注/副标题写了「{m.group(0)}」，{what} 若跨过口径切换点就是两套定义复合——只在同一口径段内算 CAGR"
          "（拆成两段各画一个），或先把旧口径换算成新口径并在脚注写明；整段同口径就忽略")
    return m.group(0)


def _ordinal(cat):
    """(kind, position) on a real time line: whole years, halves, quarters, 'YY/M' months; else None."""
    from ._marks import _half_period, _quarter_period, _year_of
    q = _quarter_period(cat)
    if q:
        return "Q", q[0]
    h = _half_period(cat)
    if h:
        return "H", h[0]
    m = re.fullmatch(r"(?:20)?(\d{2})[/.\-](\d{1,2})(?:[/.\-]\d{1,2})?", str(cat).strip())
    if m and 1 <= int(m.group(2)) <= 12:
        return "M", int(m.group(1)) * 12 + int(m.group(2))
    y = _year_of(cat)
    return ("Y", y) if y is not None else None


def uneven_time(ex, categories, where):
    """Period categories with uneven gaps (2015, 2020, 2023, 2024) drawn at equal spacing: soft warning."""
    if len(categories) < 3:
        return False
    ords = [_ordinal(c) for c in categories]
    if None in ords or len({k for k, _ in ords}) != 1:
        return False
    gaps = [b[1] - a[1] for a, b in zip(ords, ords[1:])]
    if min(gaps) <= 0 or max(gaps) == min(gaps):
        return False
    from ._page import SIGNALS
    SIGNALS.append("时间间隔不等")
    print(f"时间轴提醒（{where}）：类别 {list(map(str, categories))[:6]} 间隔不等（{gaps}），等距画会把跳跃读成匀速——"
          "改用真实时间轴 lines(x=[年份数值…])，或在缺口处断开/标注'间隔 N 年'")
    return True


def share_scale(ex, unit, top, share_y, stack):
    """Side-by-side column panels with the same unit compare magnitudes: they share the value axis by default.
    Returns the ymax to use (None = own scale). A later panel taller than an earlier one records an issue naming the
    common ymax to pass; share_y=False opts out (then the page must state the multiple on the chart)."""
    panel = getattr(ex, "_panel", None)
    if panel is None or share_y is False or stack == "percent" or unit is None:
        return None
    key = str(unit.get("unit") if isinstance(unit, dict) else unit)
    seen = getattr(ex, "_col_scales", None)
    if seen is None:
        seen = ex._col_scales = []
    others = [y for p, u, y in seen if u == key and p != panel]
    seen.append((panel, key, top))
    if not others:
        return None
    prev = max(others)
    if top > prev * 1.02:
        from ._table import add_issue
        add_issue(ex, f"并列面板单位同为 {key}、比较量级却各用各的纵轴（{prev:g} vs {top:g}）——各面板都传 "
                      f"ymax={top:g}（共用纵轴），或 share_y=False 并在图上标出倍数")
        return None
    return prev
