"""Derived numbers for business-review decks: each metric is defined once in data_common.py and every page computes
the same achievement / gap / growth from it, so no hand-written percentage drifts between pages.

A metric is a dict: name, unit, actual, and optionally target, ly (same period last year), prev (last period),
series {period: value}, higher_better (default True), src, pages, chart.
"""

from __future__ import annotations


def _num(m, k):
    v = m.get(k)
    return None if v is None else float(v)


RATE_UNITS = ("%", "pct", "pp", "pt", "ppt", "pts", "个百分点", "百分点")


def _is_rate(m):
    return str(m.get("unit", "")).strip() in RATE_UNITS


def is_rate_unit(unit):
    """True for a known rate unit (%, pt, pp …), or a metric dict with one: changes are in pt, never % of a %."""
    if isinstance(unit, dict):
        unit = unit.get("unit")
    return unit is not None and str(unit).strip() in RATE_UNITS


FLAT = "持平"   # a change that rounds to zero: never "−0%" / "+0.0pt"


def _trim0(s):
    """'3.0' → '3', '1,600.00' → '1,600'; '3.50' stays (only an all-zero fraction is dropped)."""
    if "." in s and s.split(".")[1].strip("0") == "":
        return s.split(".")[0]
    return s


def pt_text(d, zh=True):
    """Signed point change, one decimal at most: +13.7pt / −0.4pt / +15pt; rounds to 0 → '持平' ('Flat' if zh=False)."""
    s_ = f"{round(abs(d), 1):.1f}".rstrip("0").rstrip(".")
    if s_ in ("", "0"):
        return FLAT if zh else "Flat"
    return ("+" if d > 0 else "−") + s_ + "pt"


_NUM_FIELDS = ("actual", "target", "ly", "prev")
_IDENTITY_FIELDS = ("unit", "period", "actual_period", "target_period", "ly_period", "prev_period", "frequency",
                    "denominator", "definition", "basis", "entity", "currency", "geography", "status", "higher_better")


def _differs(a, b, tol):
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return False
    return abs(a - b) > tol * max(abs(a), abs(b)) and abs(a - b) > 1e-9


def merge_metrics(*dicts, tol=0.005):
    """Merge the METRICS dicts of several research directions — use instead of {**M_R1, **M_R2}, which silently keeps
    the last value when two directions report the same metric differently (one 口径 overwrites the other and every
    derived number — bridge steps, Δpt, colours — follows the wrong one). Same key with actual / target / ly / prev or
    a shared series period differing by > tol (0.5 %) raises ValueError listing both values and their src. Explicit
    metric identities must agree even when the numbers match; missing metadata remains optional. Compatible series
    periods are combined without mutating research inputs."""
    out, origin, clashes = {}, {}, []
    for i, d in enumerate(dicts):
        for k, m in (d or {}).items():
            if k not in out:
                out[k], origin[k] = dict(m) if isinstance(m, dict) else m, i
                if isinstance(m, dict) and isinstance(m.get("series"), dict):
                    out[k]["series"] = dict(m["series"])
                continue
            a = out[k]
            if not (isinstance(a, dict) and isinstance(m, dict)):
                if _differs(a, m, tol):
                    clashes.append(f"{k}: {a}（第 {origin[k] + 1} 个）vs {m}（第 {i + 1} 个）")
                continue
            src = lambda x, j: x.get("src") or f"第 {j + 1} 个 dict"
            for identity_field in _IDENTITY_FIELDS:
                left_value, right_value = a.get(identity_field), m.get(identity_field)
                if isinstance(left_value, str):
                    left_value = left_value.strip()
                if isinstance(right_value, str):
                    right_value = right_value.strip()
                if left_value is not None and right_value is not None and left_value != right_value:
                    clashes.append(f"{k}.{identity_field}: {a[identity_field]}（{src(a, origin[k])}）vs "
                                   f"{m[identity_field]}（{src(m, i)}）")
            for f_ in _NUM_FIELDS:
                if a.get(f_) is not None and m.get(f_) is not None and _differs(a[f_], m[f_], tol):
                    clashes.append(f"{k}.{f_}: {a[f_]}（{src(a, origin[k])}）vs {m[f_]}（{src(m, i)}）")
            sa, sm = a.get("series"), m.get("series")
            if isinstance(sa, dict) and isinstance(sm, dict):
                for per in sa.keys() & sm.keys():
                    if _differs(sa[per], sm[per], tol):
                        clashes.append(f"{k}.series[{per}]: {sa[per]}（{src(a, origin[k])}）vs {sm[per]}（{src(m, i)}）")
                a["series"] = {**sm, **sa}
            for f_, v in m.items():
                if a.get(f_) is None and v is not None:
                    a[f_] = dict(v) if f_ == "series" and isinstance(v, dict) else v
    if clashes:
        raise ValueError(f"merge_metrics：同一指标口径冲突或数值相差 >{tol:.1%}——" + "；".join(clashes[:6])
                         + "。在 plan.py 里选定一个口径（改掉另一方向的值，或换一个键名并在 name 里注明口径），再合并；"
                         "不要用 {**A, **B} 静默覆盖")
    return out


def vs_target(m):
    """Achievement vs target: {"rate": actual/target·100, "gap": actual − target, "ok": bool}; None without a target.
    For % metrics the gap is in pt; lower-is-better metrics (cost rate, NPL) are ok when actual ≤ target."""
    a, t = _num(m, "actual"), _num(m, "target")
    if a is None or t is None:
        return None
    better = m.get("higher_better", True)
    return {"rate": a / t * 100 if t else None, "gap": a - t, "ok": (a >= t) if better else (a <= t)}


def yoy(m, base="ly"):
    """Change vs last year (base="ly") or last period (base="prev"): {"pct": relative %, "diff": absolute change}.
    For % metrics read "diff" (pt)."""
    a, b = _num(m, "actual"), _num(m, base)
    if a is None or b is None:
        return None
    return {"pct": (a - b) / abs(b) * 100 if b else None, "diff": a - b}


def status(m, warn=0.98):
    """Traffic light vs target: "green" (met), "amber" (within 2% of target), "red" (worse), None (no target)."""
    v = vs_target(m)
    if v is None:
        return None
    if v["ok"]:
        return "green"
    a, t = _num(m, "actual"), _num(m, "target")
    close = (a >= t * warn) if m.get("higher_better", True) else (a <= t * (2 - warn))
    return "amber" if close else "red"


def fmt_delta(m, base="ly", digits=1, zh=True):
    """'+43.0%' / '−1.2pt' label of the change vs ly / prev, or the gap to target (base="target", in the metric's
    unit). % metrics always show pt. A rounded zero reads '持平' ('Flat' if zh=False)."""
    if base == "target":
        v = vs_target(m)
        d, rel = (None, None) if v is None else (v["gap"], None)
    else:
        v = yoy(m, base)
        d, rel = (None, None) if v is None else (v["diff"], v["pct"])
    if d is None:
        return ""
    sign = "+" if d > 0 else ("−" if d < 0 else "±")

    def out(body, unit):   # integers without ".0"; a change that rounds to zero reads "持平", never "−0%"
        body = _trim0(body)
        return (FLAT if zh else "Flat") if body.replace(",", "").strip("0.") == "" else f"{sign}{body}{unit}"
    if _is_rate(m):
        level = abs(_num(m, "actual") or 0)
        if level < 5 or abs(d) < 0.5 * 10 ** -digits:   # NIM 1.63 vs 1.58, NPL 1.46: banks read these in bp
            return out(f"{abs(d) * 100:.0f}", "bp")
        return out(f"{abs(d):.{digits}f}", "pt")
    if rel is None:   # gap in the metric's unit, at the precision data_common.py writes it (3428 vs 3300 → +128)
        raw = str(m.get("actual"))
        nd = len(raw.split(".")[1]) if "." in raw and isinstance(m.get("actual"), float) else 0
        return out(f"{abs(d):,.{nd}f}", m.get("unit", ""))
    return out(f"{abs(rel):.{digits}f}", "%")


def metric_rows(metrics, keys=None, zh=True):
    """Rows for a row_table KPI scorecard: label, unit, actual, target, ly, rate, gap, yoy_pct, yoy_diff, status,
    delta ('+43.0%' vs ly; % metrics in pt), vs_t (gap to target), higher_better (Variance colours by it).
    zh=False localizes rounded-zero deltas to 'Flat'; the default remains '持平'."""
    out = []
    for k in keys or list(metrics):
        m = metrics[k]
        v, g = vs_target(m) or {}, yoy(m) or {}
        out.append(dict(key=k, label=m.get("name", k), unit=m.get("unit", ""), actual=_num(m, "actual"),
                        actual_s=fmt_value(m), target_s=fmt_value(m, m.get("target")) if m.get("target") is not None else "—",
                        target=_num(m, "target"), ly=_num(m, "ly"), rate=v.get("rate"), gap=v.get("gap"),
                        yoy_pct=g.get("pct"), yoy_diff=g.get("diff"), status=status(m),
                        delta=fmt_delta(m, zh=zh), vs_t=fmt_delta(m, "target", zh=zh),
                        higher_better=(bool(m["higher_better"]) if "higher_better" in m else None)))
    return out


def fmt_value(m, v=None):
    """The metric's value as written in data_common.py precision: 1.63 → '1.63', 216.8 → '216.8', 31048 → '31,048'."""
    v = m.get("actual") if v is None else v
    if v is None:
        return "—"
    raw = str(m.get("actual"))
    nd = len(raw.split(".")[1]) if "." in raw and isinstance(m.get("actual"), float) else 0
    return f"{float(v):,.{nd}f}"


def _n(v, digits=2):
    """Plain number for formula text: thousands separators, no trailing zeros (3.850 → 3.85, 12.0 → 12)."""
    s = f"{float(v):,.{digits}f}"
    return (s.rstrip("0").rstrip(".") if "." in s else s).replace("-", "−")


def gap_vs_baseline(target, actual_ytd, ly_remaining, ytd_growth, digits=2):
    """Gap after the business-as-usual baseline (a stated remaining-period gap often ignores that last year's
    remaining period alone, grown at the YTD rate, already covers the target). baseline_remaining = ly_remaining × (1 + ytd_growth)
    (ytd_growth as a fraction: 0.123 = +12.3 %); gap = target − actual_ytd − baseline_remaining. covered=True
    (gap ≤ 0): the revenue target is met on trend — move the page's gap to profit. need_yoy: the growth the remaining
    period needs vs last year (title it "同比需 +x%", not 环比). formula_text goes on the page as the derivation."""
    t, a, ly, g = float(target), float(actual_ytd), float(ly_remaining), float(ytd_growth)
    base = ly * (1 + g)
    gap = t - a - base
    need = (t - a) / ly - 1 if ly else None
    return dict(baseline_remaining=base, gap=gap, covered=gap <= 0, need_yoy=need,
                formula_text=f"目标 {_n(t, digits)} − 已实现 {_n(a, digits)} − 基线 {_n(base, digits)} = 缺口 {_n(gap, digits)}")


def remaining_risk(base_remaining, shock, digits=2):
    """Risk amount on the remaining-period base (a shock amount without its base is unverifiable): amount = base × shock
    (shock as a fraction, or a day count with base = balance ÷ turnover days). Returns dict(amount, formula_text)."""
    b, s_ = float(base_remaining), float(shock)
    amt = b * s_
    return dict(amount=amt, formula_text=f"剩余期基数 {_n(b, digits)} × 冲击 {_n(s_, 4)} = {_n(amt, digits)}")


def on_page(metrics, page):
    """Metric keys whose data_common.py entry lists this page in pages=[…] (a hint, not a contract)."""
    return [k for k, m in metrics.items() if page in (m.get("pages") or [])]


def check_mix(parts, total, tol=0.5, name="比率"):
    """Weighted-ratio reconciliation: parts = [(weight, rate), …] (e.g. (category revenue, gross margin %),
    (channel sign-ups, activation %)); total = the overall rate shown elsewhere. Raises ValueError when
    Σ(weight × rate) / Σ weight differs from total by more than tol points (same unit as the rates). Returns the
    weighted average. Use in plan.py: check_mix([(rev_fresh, 19.6), (rev_food, 17.8)], 23.5, name="毛利率")."""
    pairs = [(float(w), float(r)) for w, r in parts if w is not None and r is not None]
    wsum = sum(w for w, _ in pairs)
    if not pairs or wsum <= 0:
        raise ValueError(f"check_mix（{name}）：parts 需要至少一项正权重 (weight, rate)")
    avg = sum(w * r for w, r in pairs) / wsum
    if abs(avg - float(total)) > tol:
        detail = "、".join(f"{w:g}×{r:g}" for w, r in pairs[:6])
        gap = f"{avg - float(total):+.2f}".replace("-", "−")
        raise ValueError(f"check_mix：分项{name}加权平均 {avg:.2f} 与整体 {float(total):g} 相差 {gap}pt"
                         f"（> {tol}pt；分项 {detail}）——分项和整体口径不一致：核对权重（收入/人数）与各分项{name}，"
                         "或补上漏掉的分项后再出图；不要只改整体数")
    return avg


def ratio(num, den, pct=True, name="比率"):
    """A rate computed from its parts — write ratio(paid, signups) instead of typing the rate (a typed
    rate can match neither pair of source figures). pct=True returns percent (×100), False a fraction.
    Raises ValueError on a missing or zero denominator."""
    if num is None or den is None or not float(den):
        raise ValueError(f"ratio（{name}）：分子/分母缺失或分母为 0（{num!r} / {den!r}）——从 METRICS 取两个字段现算")
    r = float(num) / float(den)
    return r * 100 if pct else r


def check_stock(begin, adds, churn, end, tol=0.5, name=""):
    """Stock identity begin + adds − churn = end (users, members, stores, headcount; churn as a positive number).
    Raises ValueError when the residual exceeds tol % of end (net adds otherwise imply a churn rate that
    contradicts the one used on other pages). Returns the implied churn rate churn / begin as a fraction — feed
    that one number to every page (churn rate, LTV, net adds) instead of a typed rate."""
    b, a, c, e = (float(x) for x in (begin, adds, churn, end))
    gap = b + a - c - e
    if abs(gap) > tol / 100 * max(abs(e), 1e-9):
        tag = f"（{name}）" if name else ""
        raise ValueError(f"check_stock{tag}：期初 {b:g} + 新增 {a:g} − 流失 {c:g} = {b + a - c:g}，与期末 {e:g} 相差 "
                         f"{gap:+g}（> {tol:g}%）——存量恒等式不闭合：流失率、净增、LTV 只能来自同一组字段，"
                         "改数据源而不是改某一页的数")
    if not b:
        raise ValueError(f"check_stock（{name}）：期初为 0，算不出流失率")
    return c / b


import re as _re

_REF_WORDS = _re.compile(r"去年|上年|同期|上期|上月|上季|前一?年|基期|预算|目标|计划|对照|\b(?:PY|LY|PL|BU|FC|prior|last year|budget|"
                         r"target|plan|prev(?:ious)?|ref|baseline)\b", _re.I)
_AC_WORDS = _re.compile(r"实际|本期|今年|本年|当期|\b(?:AC|actual|current|now|cur)\b", _re.I)
_PERIOD_KEY = _re.compile(r"((?:19|20)\d{2})\s*(?:年)?\s*(?:([HQ])([1-4])|([1-4])([HQ]))?", _re.I)


def _role(*texts):
    """'ref' / 'ac' / None for a series from its name / field key."""
    for t in texts:
        if not isinstance(t, str) or not t.strip():
            continue
        ref, ac = bool(_REF_WORDS.search(t)), bool(_AC_WORDS.search(t))
        if ref != ac:
            return "ref" if ref else "ac"
    return None


def _period(t):
    m = _PERIOD_KEY.search(str(t or ""))
    if not m:
        return None
    sub = (m.group(2) or m.group(5) or "").upper()
    n = int(m.group(3) or m.group(4) or 0)
    return (int(m.group(1)), {"H": n * 2, "Q": n}.get(sub, 0) if sub else 0, sub)


def ac_minus_ref_order(a, b):
    """Which way a two-series difference must be taken so its sign is AC − reference.
    a, b: names (or tuples of name + field key) of the first / second series. Returns +1 when b is the actual
    (difference = b − a), −1 when a is (difference = a − b), 0 when the names do not tell (keep b − a).
    Reference words: 去年 / 同期 / 预算 / 目标 / PY / PL / plan …; actual words: 实际 / 本期 / AC / now … — only a pair
    with one of each decides; otherwise the later of two periods of the same kind (2025H1 vs 2024H1) is the actual."""
    ta = a if isinstance(a, (tuple, list)) else (a,)
    tb = b if isinstance(b, (tuple, list)) else (b,)
    ra, rb = _role(*ta), _role(*tb)
    if (ra, rb) == ("ref", "ac"):   # both sides must be identified: ("now", "现状") vs ("fut", "2028") stays b − a
        return 1
    if (ra, rb) == ("ac", "ref"):
        return -1
    pa, pb = _period(ta[0]), _period(tb[0])
    if pa and pb and pa[2] == pb[2] and pa[:2] != pb[:2]:
        return 1 if pb[:2] > pa[:2] else -1
    return 0
