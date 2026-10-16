"""Measured text, bounded chart canvases and numeric-label utilities."""

from __future__ import annotations

import math
import re
from xml.sax.saxutils import quoteattr

from .._common import (
    _estimate_label_width_px,
    _resolve_font,
    _resolve_palette,
    _xesc,
)
from .._typography import chart_font_sizes
from ._shared import tr


def finite(value, name, *, minimum=None):
    if isinstance(value, (bool, str, bytes)):
        raise TypeError(f"{name} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(number) or (minimum is not None and number < minimum):
        limit = f" >= {minimum}" if minimum is not None else ""
        raise ValueError(f"{name} must be a finite number{limit}")
    return number


class PValue(float):
    """A P value that remembers how the source reported it: ``op`` is '=', '<', '>' or 'ns'."""

    op = "="
    raw = ""


_P_STRING = re.compile(r"\s*(?:[Pp]\s*)?([<>=≤≥])?\s*(0?\.[0-9]+|[01](?:\.[0-9]*)?|[0-9.]+[eE]-?[0-9]+)\s*")


def parse_p(value, name="p"):
    """Number or reported string ('<.05', 'P<0.001', '0.003', 'n.s.') → PValue in [0, 1]."""
    if isinstance(value, PValue):
        return value
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"(?i)n\.?\s*s\.?|not\s+significant|不显著", text):
            p = PValue(1.0)
            p.op, p.raw = "ns", "ns"
            return p
        m = _P_STRING.fullmatch(text)
        if not m:
            raise ValueError(
                f"{name} {value!r}: give a number (0.003) or the reported threshold as a string "
                "('<.05', '<0.001', 'n.s.')"
            )
        op = (m.group(1) or "=").replace("≤", "<").replace("≥", ">")
        number = float(m.group(2))
        raw = m.group(2)
        raw = "0" + raw if raw.startswith(".") else raw
        if not 0 <= number <= 1:
            raise ValueError(f"{name} must be between 0 and 1")
        p = PValue(number * (1 - 1e-9) if op == "<" else number)
        p.op, p.raw = op, raw
        return p
    number = finite(value, name, minimum=0)
    if number > 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return PValue(number)


def p_label(p, digits=".3f", *, spaced=True):
    """'P = 0.003' / 'P < 0.001' / 'P < 0.05' (reported threshold kept) / 'ns'."""
    p = parse_p(p)
    gap = " " if spaced else ""
    if p.op == "ns":
        return "ns"
    if p.op in "<>":
        return f"P{gap}{p.op}{gap}{p.raw}"
    if p < 0.001:
        return f"P{gap}<{gap}0.001"
    return f"P{gap}={gap}{format(float(p), digits)}"


def log_axis_ticks(low, high, *, max_count=7):
    """Readable ticks for a log10 axis on [low, high] (true values, placed at log positions)."""
    from ._academic_rigor import log_ticks

    lo, hi = sorted((float(low), float(high)))
    exps = list(range(math.ceil(math.log10(lo) - 1e-9), math.floor(math.log10(hi) + 1e-9) + 1))
    if len(exps) >= 2:
        return [10.0**e for e in exps[:: max(1, math.ceil(len(exps) / max_count))]]
    return log_ticks(lo, hi, min_count=3, max_count=max_count) or [lo, hi]


def forest_scale(values, midline_value, *, log_x=False, value_domain=None):
    """Fit supplied intervals and the null without expanding to whole decades."""
    from ._academic_rigor import SharedScale, nice_axis
    from ._composition import scale_from

    values = [*values, finite(midline_value, "midline_value")]
    scale = scale_from(values, domain=value_domain, transform="log10" if log_x else "linear")
    if value_domain is not None:
        scale = SharedScale(tuple(finite(v, "value_domain") for v in value_domain), scale.ticks, scale.transform)
    if not log_x:
        return scale
    ticks, low, high = nice_axis(*scale.domain, 5)
    if low > 0 and high / low <= (scale.domain[1] / scale.domain[0]) * 2:
        if value_domain is None:
            return SharedScale((low, high), ticks, "log10")
        return SharedScale(scale.domain, [t for t in ticks if scale.domain[0] <= t <= scale.domain[1]], "log10")
    # Wide ratios retain their fitted bounds. Avoid the previous arbitrary
    # geometric tick labels when fewer than two complete decades are present.
    from ._academic_rigor import log_ticks

    ticks = log_ticks(*scale.domain)
    return SharedScale(scale.domain, ticks or scale.ticks, "log10")


def wrap_lines(value, width, fs, font):
    """Keep Latin words, acronyms and numeric/unit runs whole when they fit."""
    import re
    import unicodedata

    def measure(text):
        return _estimate_label_width_px(text, fs, font_family=font)

    opening = "([{（［｛《〈【「『“‘"
    closing = ")]},.!?:;％%）］｝》〉】」』”’、。，！？：；"

    def long_pieces(token):
        pieces = []
        while token:
            end = 1
            while end <= len(token) and measure(token[:end]) <= width:
                end += 1
            end = max(1, end - 1)
            if end < len(token):
                separator = max((token.rfind(char, 0, end) for char in "/_-–?&:"), default=-1)
                if separator >= max(1, end // 3):
                    end = separator + 1
                while end < len(token) and unicodedata.combining(token[end]):
                    end += 1
                # Keep closing punctuation with a preceding glyph and opening
                # punctuation with a following glyph, including oversized words.
                while end > 1 and ((end < len(token) and token[end] in closing) or token[end - 1] in opening):
                    end -= 1
            pieces.append(token[:end])
            token = token[end:]
        return pieces

    lines = []
    pattern = r"[A-Za-z0-9\u00c0-\u024f\u0300-\u036f\u0370-\u03ff_./%+\-−–=<>≤≥°:#?&]+|\s+|."
    for paragraph in str(value).splitlines() or [""]:
        pending = ""
        tokens = []
        for token in re.findall(pattern, paragraph):
            if tokens and not token.isspace() and (token[0] in closing or tokens[-1][-1] in opening):
                tokens[-1] += token
            else:
                tokens.append(token)
        # A short Latin symbol and the CJK glyph it qualifies read as one word ("p 值", "AUC值"):
        # never break "仅报告 p | 值".
        glued = []
        for token in tokens:
            cjk = (
                unicodedata.east_asian_width(token[0]) in "WF"
                and token[0] not in closing + opening
                and all(ch in closing for ch in token[1:])
            )
            if cjk and glued and _short_symbol(glued[-1]):
                glued[-1] += token
            elif cjk and len(glued) >= 2 and glued[-1].isspace() and _short_symbol(glued[-2]):
                glued[-2:] = [glued[-2] + glued[-1] + token]
            else:
                glued.append(token)
        tokens = glued
        for token in tokens:
            if token.isspace():
                if pending:
                    pending += token
                continue
            if pending.strip() and measure(pending + token) > width:
                lines.append(pending.rstrip())
                pending = ""
            if measure(token) > width:
                pieces = long_pieces(token)
                lines.extend(pieces[:-1])
                pending = pieces[-1]
            else:
                pending += token
        lines.append(pending.rstrip())
    return _rejoin_orphans(lines, width, measure, str(value))


def wrap_axis_title(value, width, fs, font, min_fs=10.0):
    """(lines, font size) for an axis title: break only at spaces / before brackets, never inside a CJK word."""
    import re

    text = str(value or "").strip()
    if not text:
        return [], fs
    chunks = [c for c in re.split(r"\s+|(?=[(（\[［])", text) if c]
    merged = []  # "p 值" / "CI 计算": a short Latin symbol stays with the CJK word after it
    for chunk in chunks:
        if merged and _symbol_cjk_space(merged[-1], chunk) and (merged[-1] + " " + chunk) in text:
            merged[-1] += " " + chunk
        else:
            merged.append(chunk)
    chunks = merged
    floor = max(min_fs, fs * 0.8)
    size = fs
    while True:
        measure = lambda t: _estimate_label_width_px(t, size, font_family=font)
        if all(measure(c) <= width for c in chunks):
            lines, line = [], ""
            for chunk in chunks:
                glue = " " if line and (line + " " + chunk) in text else ""
                if line and measure(line + glue + chunk) > width:
                    lines.append(line)
                    line = chunk
                else:
                    line = line + glue + chunk
            lines.append(line)
            if size <= floor or (len(lines) <= 2 and not any(is_orphan_line(v) for v in lines[1:])):
                return lines, size
        if size <= floor:
            return wrap_lines(text, width, size, font), size
        size = max(floor, size - 0.5)


def is_orphan_line(line):
    """A wrapped line that carries no meaning alone: '(h)', '（ROC-AUC）', '1)', '5'."""
    import re

    text = str(line).strip()
    return bool(text) and (len(text) <= 2 or bool(re.match(r"^[(（\[［][^()（）]*[)）\]］][,，.。;；:：]?$", text)))


def _short_symbol(word):
    """A 1-3 char ASCII symbol (p, pH, AUC) that binds to the CJK word after it."""
    return 0 < len(word) <= 3 and word.isascii() and word.isalnum()


def _symbol_cjk_space(head, tail):
    """True when ``head + " " + tail`` joins a short Latin symbol to the CJK glyph after it ("p 值")."""
    import unicodedata

    return bool(tail) and unicodedata.east_asian_width(tail[0]) in "WF" and _short_symbol(head.split(" ")[-1])


def _rejoin_orphans(lines, width, measure, source=""):
    """Never leave a parenthesized unit or a 1-2 glyph fragment alone on a line."""
    out = []
    for line in lines:
        if out and out[-1].strip() and is_orphan_line(line):
            prev = out[-1]
            # Restore the space the wrap consumed, exactly as the caller wrote it.
            glue = " " if (prev + " " + line) in source else ""
            joined = prev + glue + line
            if measure(joined) <= width:
                out[-1] = joined
                continue
            head, sep, tail = prev.rpartition(" ")
            # "仅报告 p 值": the space between a short symbol and its CJK word is not a break point.
            while sep and _symbol_cjk_space(head, tail):
                head, sep, more = head.rpartition(" ")
                tail = more + " " + tail
            if sep and head.strip() and measure(tail + glue + line) <= width:
                out[-1] = head.rstrip()
                out.append(tail + glue + line)
                continue
            if not glue and len(prev) > 3 and (prev + line) in source and not line.startswith(("(", "（")):
                # One over-long token ("0.775" → "0.77"/"5"): balance the pieces instead.
                cut = (len(prev) + len(line) + 1) // 2
                whole = prev + line
                out[-1] = whole[:cut]
                out.append(whole[cut:])
                continue
        out.append(line)
    return out


def axis_caption(title, unit="", chart_title=None):
    """Axis caption with its unit on the same line, never a bare '(unit)'."""
    title = str(title or "").strip()
    unit = str(unit or "").strip()
    # Already stated: "(h)" in the title, or a multi-glyph unit word ("ROC-AUC") — not 分 inside 得分.
    # "(%，越高越好)" / "(%, higher is better)" already states the unit inside a qualified bracket.
    stated = re.search(r"[(（\[]\s*" + re.escape(unit) + r"\s*[)）\]，,;；、]", title) if unit else None
    if not unit or stated or (len(unit) > 2 and unit in title):
        return title
    if title:
        return f"{title} ({unit})"
    if chart_title and (
        f"({unit})" in str(chart_title)
        or f"（{unit}）" in str(chart_title)
        or (len(unit) > 2 and unit in str(chart_title))
    ):
        return ""
    return unit if len(unit) > 2 else tr("Unit: {unit}", unit=unit)


class ChartLayout:
    """Measured text and a bounded SVG canvas; coordinates use text tops."""

    def __init__(self, width, height, palette, font_family, *, n_items=None):
        self.width = finite(width, "width", minimum=300)
        self.height = finite(height, "height", minimum=260)
        self.pal = _resolve_palette(palette)
        self.font, self.heading = _resolve_font(font_family)
        self.ink = self.pal.get("ink_fg", self.pal["ink"])
        self.font_sizes = chart_font_sizes(self.width, self.height, n_items)
        self.parts = []
        self.text_boxes = []

    def measure(self, text, fs=13, bold=False):
        return _estimate_label_width_px(str(text), fs, bold=bold, font_family=self.font)

    def text(self, text, x, top, *, fs=13, color=None, anchor="start", bold=False, width=None, axis=False):
        font = self.heading if bold else self.font
        if color in (self.pal.get("muted"), self.pal.get("ink6")) and color is not None:
            color = readable_annotation_color(color, self.pal)
        lines = wrap_lines(text, width / (1.05 if bold else 1), fs, font) if width else str(text).splitlines()
        # A unit/fragment that cannot rejoin its line at this size: shrink (to >= 80%, >= 10px) instead of orphaning it.
        size = fs
        while width and len(lines) > 1 and any(is_orphan_line(v) for v in lines[1:]) and size > max(10.0, fs * 0.8):
            size = max(10.0, fs * 0.8, size - 0.5)
            lines = wrap_lines(text, width / (1.05 if bold else 1), size, font)
        if axis and width and len(lines) > 1:
            # Axis titles break at spaces / brackets or shrink — never "比|例" inside a word.
            lines, size = wrap_axis_title(text, width / (1.05 if bold else 1), fs, font)
        fs = size
        for i, line in enumerate(lines):
            y = top + fs * 0.84 + i * fs * 1.35
            w = _estimate_label_width_px(line, fs, bold=bold, font_family=font)
            left = x - (w / 2 if anchor == "middle" else w if anchor == "end" else 0)
            self.text_boxes.append((left, y - fs * 0.84, left + w, y + fs * 0.26, line))
            self.parts.append(
                f'<text x="{x:.2f}" y="{y:.2f}" font-family={quoteattr(font)} '
                f'font-size="{fs:.2f}" fill={quoteattr(color or self.ink)} '
                f'text-anchor="{anchor}" font-weight="{600 if bold else 400}">'
                f"{_xesc(line)}</text>"
            )
        return max(1, len(lines)) * fs * 1.35

    def header(self, title, subtitle, figure_label, margin=28):
        top = margin
        width = self.width - margin * 2
        for value, fs, bold, color, gap in (
            (figure_label, self.font_sizes["figure"], True, self.pal["ink6"], 6),
            (title, self.font_sizes["title"], True, self.ink, 7),
            (subtitle, self.font_sizes["subtitle"], False, self.pal["ink6"], 5),
        ):
            if value:
                top += self.text(value, margin, top, fs=fs, bold=bold, color=color, width=width) + gap
        return top + 15

    def svg(self, description):
        # As with the other chart generators, background is inherited from the slide.
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {self.width:g} {self.height:g}" '
            f"font-family={quoteattr(self.font)} aria-label={quoteattr(description)}>"
            f"{''.join(self.parts)}</svg>"
        )


def number_label(value, *, compact=False):
    """Format exact integer counts without ever converting them through float."""
    if isinstance(value, int):
        plain = f"{value:,}"
        digits = str(abs(value))
        if compact and len(digits) > 6:
            significant = digits.rstrip("0")
            mantissa = significant[0] + ("." + significant[1:] if len(significant) > 1 else "")
            scientific = ("-" if value < 0 else "") + mantissa + f"e{len(digits) - 1}"
            if len(scientific) < len(plain):
                return scientific
        return plain
    if compact:
        return f"{value:.3g}"
    # Scientific measurements remain floats: do not expose their binary
    # representation as a huge integer (e.g. Avogadro's constant).
    if float(value).is_integer() and abs(value) < 1e6:
        return f"{int(value):,}"
    return str(value)


def uniform_value_labels(values, *, cap=2):
    """Value-label texts sharing one decimal count (the series' max, capped at ``cap``): 6 / 5.5 → "6.0" / "5.5"."""
    values = [None if v is None else finite(v, "number") for v in values]

    def places(v):
        text = precise_number(v)
        if "e" in text:
            return cap
        return len(text.split(".", 1)[1]) if "." in text else 0

    present = [v for v in values if v is not None]
    if not present or any(abs(v) >= 1e7 for v in present):
        return [None if v is None else precise_number(v) for v in values]
    decimals = min(cap, max(places(v) for v in present))
    out = []
    for v in values:
        if v is None:
            out.append(None)
            continue
        text = f"{v:.{decimals}f}"
        if v != 0 and float(text) == 0:  # tiny nonzero value: never print it as zero
            text = precise_number(v)
        out.append(text)
    return out


def precise_number(value, *, decimals=None, reference=None):
    """Compact numeric text with at most two ULPs of harmless float noise."""
    value = finite(value, "number")
    if value == 0:
        return f"{0:.{decimals}f}" if decimals is not None else "0"
    tolerance = 2 * math.ulp(value)

    def acceptable(text):
        candidate = float(text)
        if not math.isfinite(candidate) or candidate == 0 or (candidate > 0) != (value > 0):
            return False
        if abs(candidate - value) > tolerance:
            return False
        if reference is not None:
            sign = lambda x: (x > reference) - (x < reference)
            if sign(candidate) != sign(value):
                return False
        return True

    if decimals is not None and abs(value) < 1e7:
        fixed = f"{value:.{decimals}f}"
        if acceptable(fixed):
            return fixed
    for digits in range(1, 18):
        text = format(value, f".{digits}g")
        if acceptable(text):
            if "e" in text and 1e-4 <= abs(value) < 1e7:
                # ".1g" spells 10 as "1e+01"; ordinary magnitudes stay positional.
                from decimal import Decimal

                text = format(Decimal(text), "f")
            return text
    return repr(value)


def forest_estimate_text(row, reference=1.0):
    """Shared numeric annotation for every forest rendering route."""
    values = [row.get(k) for k in ("estimate", "ci_lo", "ci_hi")]
    if row.get("is_subgroup_header") or any(v is None for v in values):
        return ""
    if row.get("_point_only"):
        decimals = 2 if abs(float(values[0])) < 10 else 1
        return precise_number(values[0], decimals=decimals, reference=reference)
    # Ratios (HR/OR ≈ 1) need two decimals; rates and scores (ORR 57.1 %) keep the reported precision.
    decimals = 2 if max(abs(float(v)) for v in values) < 10 else 1
    labels = [precise_number(v, decimals=decimals, reference=reference) for v in values]
    labels = [t[:-2] if decimals == 1 and t.endswith(".0") else t for t in labels]
    parsed = list(map(float, labels))
    sign = lambda x: (x > 0) - (x < 0)
    # Even a two-ULP cleanup must not collapse distinct interval/estimate values.
    if any(sign(parsed[i] - parsed[j]) != sign(values[i] - values[j]) for i in range(3) for j in range(i)):
        labels = [repr(float(v)) for v in values]
    # "−0.28–−0.15" reads as a subtraction; a negative bound needs a comma separator.
    joiner = ", " if any(t.startswith("-") for t in labels[1:]) else "–"
    text = f"{labels[0]} ({labels[1]}{joiner}{labels[2]})"
    return text + " · " + row["_ci_display_label"] if row.get("_ci_display_label") else text


def readable_annotation_color(preferred, palette, minimum=4.5):
    """Choose a legible existing text-role color without modifying the palette."""
    import re

    def rgba(color):
        text = str(color or "").strip()
        if text.startswith("#") and len(text) in (4, 5, 7, 9):
            raw = text[1:]
            if len(raw) in (3, 4):
                raw = "".join(ch * 2 for ch in raw)
            return tuple(int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4)) + (
                (int(raw[6:8], 16) / 255) if len(raw) == 8 else 1.0,
            )
        match = re.fullmatch(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)", text)
        if match:
            r, g, b, a = match.groups()
            return float(r) / 255, float(g) / 255, float(b) / 255, float(a) if a is not None else 1.0
        return {"white": (1, 1, 1, 1), "black": (0, 0, 0, 1)}.get(text.lower())

    background = rgba(palette.get("bg"))
    if background is None or background[3] < 0.999:
        return preferred

    def luminance(rgb):
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
        return sum(v * w for v, w in zip(linear, (0.2126, 0.7152, 0.0722)))

    bg_lum = luminance(background[:3])

    def contrast(color):
        value = rgba(color)
        if value is None:
            return None
        lum = luminance([value[i] * value[3] + background[i] * (1 - value[3]) for i in range(3)])
        return (max(lum, bg_lum) + 0.05) / (min(lum, bg_lum) + 0.05)

    current = contrast(preferred)
    if current is None or current >= minimum:
        return preferred
    candidates = [palette.get("ink_fg"), palette.get("ink"), palette.get("muted"), palette.get("ink6")]
    candidates = [(contrast(color), color) for color in candidates if color is not None]
    candidates = [(ratio, color) for ratio, color in candidates if ratio is not None]
    for ratio, color in candidates:
        if ratio >= minimum:
            return color
    return max(candidates, default=(current, preferred))[1]


def forest_ci_context(rows, header="Estimate (CI)", default_level=None):
    """Copy rows and resolve explicitly stated confidence levels."""
    import re
    import unicodedata

    rows = [dict(row) for row in rows]
    header = tr("Estimate (CI)") if header is None else str(header)
    percent = re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:CI\b|confidence\b|置信区间)", re.I)
    labels, stated_levels = [], []
    numeric_rows = [r for r in rows if not r.get("is_subgroup_header") and r.get("estimate") is not None]
    for row in numeric_rows:
        row.pop("_ci_display_label", None)
        level = row.get("ci_level")
        label = row.get("ci_label")
        if level is None and label is None:
            level = default_level
        if level is not None:
            level = finite(level, "ci_level")
            if not 0 < level < 100:
                raise ValueError("ci_level must be a percentage strictly between 0 and 100 (e.g. 95 or 97.38)")
            row["ci_level"] = level
        if label is not None:
            label = str(label).strip()
            if not label:
                raise ValueError("ci_label must be non-empty when supplied")
            match = re.search(r"(\d+(?:\.\d+)?)\s*%", unicodedata.normalize("NFKC", label))
            if match and level is not None and float(match.group(1)) != level:
                raise ValueError("ci_label contradicts ci_level")
            if match:
                level = float(match.group(1))
                if not 0 < level < 100:
                    raise ValueError("ci_label percentage must be strictly between 0 and 100")
        elif level is not None:
            label = precise_number(level) + "% CI"
        labels.append(label)
        stated_levels.append(level)
    header_level = percent.search(unicodedata.normalize("NFKC", header))
    if header_level and any(level is not None and level != float(header_level.group(1)) for level in stated_levels):
        raise ValueError(
            "right_header_label confidence level conflicts with a row; use a generic CI header for mixed levels"
        )
    known = {label for label in labels if label is not None}
    if not known:
        return rows, header
    uniform = len(known) == 1 and all(label is not None for label in labels)
    if uniform:
        label = next(iter(known))
        if label in header:
            return rows, header
        if not header_level and re.search(r"\bCI\b", header):
            return rows, re.sub(r"\bCI\b", lambda _: label, header, count=1)
    if header == tr("Estimate (CI)"):
        header = tr("Estimate (CI level by row)")
    for row, label in zip(numeric_rows, labels):
        row["_ci_display_label"] = label or "CI"
    return rows, header
