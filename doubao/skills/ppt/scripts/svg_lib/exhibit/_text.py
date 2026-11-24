"""Text measurement and wrapping from the embedded metrics table (no runtime font dependency)."""

from __future__ import annotations

from . import _metrics as M

_TABLES = {"regular": M.REGULAR, "bold": M.BOLD, "italic": M.ITALIC, "serif": M.SERIF}

# Chinese line-break rules: these never start a line / never end a line.
_NO_START = set("，。、；：？！）】》」』”’%‰·…,.;:?!)]}") | {"　"}
_UNITS = set("亿万千百元倍个家年月日天岁人次项条台辆吨米%‰")
_NO_END = set("（【《「『“‘([{$￥")


def is_cjk(ch: str) -> bool:
    return ord(ch) > 0x2E80


def has_cjk(s: str) -> bool:
    return any(is_cjk(c) for c in str(s))


def tw(s, size: float, bold: bool = False, italic: bool = False, serif: bool = False) -> float:
    """Advance width of `s` at font-size `size` (pt == px on a 960x540 slide)."""
    key = "serif" if serif else ("bold" if bold else ("italic" if italic else "regular"))
    table, fb = _TABLES[key], M.FALLBACK[key]
    w = 0.0
    for ch in str(s):
        if is_cjk(ch):
            w += M.CJK
        else:
            w += table.get(ch, fb)
    return w * size


def wrap(s: str, size: float, width: float, bold: bool = False) -> list[str]:
    """Greedy wrap: CJK breaks anywhere, Latin words stay whole, CJK punctuation never starts a line."""
    tokens, buf = [], ""
    for ch in str(s):
        if is_cjk(ch) or ch == " ":
            if buf:
                tokens.append(buf)
                buf = ""
            tokens.append(ch)
        else:
            buf += ch
    if buf:
        tokens.append(buf)
    lines, cur = [], ""
    for t in tokens:
        if tw(cur + t, size, bold) > width and cur.strip():
            if t[0] in _NO_START or (t[0] in _UNITS and cur.rstrip() and (cur.rstrip()[-1].isdigit())):
                cur += t
                continue
            if cur and cur[-1] in _NO_END:
                lines.append(cur[:-1].rstrip())
                cur = cur[-1] + t
                continue
            lines.append(cur.rstrip())
            cur = t.lstrip()
        else:
            cur += t
    if cur.strip():
        lines.append(cur.rstrip())
    return lines or [""]


def fmt(v, nd=None) -> str:
    """Compact number: integers without decimals, else one decimal; thousands separators. |v| < 1 keeps two
    decimals (0.08 / 0.12 stay apart instead of both reading 0.1; trailing zero dropped: 0.5), smaller values two
    significant digits (0.0034)."""
    if v is None:
        return ""
    if nd is None:
        if 0 < abs(v) < 1 and not float(v).is_integer():
            import math
            nd = max(2, 1 - math.floor(math.log10(abs(v))))
            s = f"{v:,.{nd}f}"
            return s.rstrip("0").rstrip(".") if s.endswith("0") else s
        nd = 0 if abs(v) >= 100 or float(v).is_integer() else 1
    s = f"{v:,.{nd}f}"
    if "." in s and s.split(".")[1].strip("0") == "":   # integers never carry ".0" ("1,600.0", "3.0pt")
        s = s.split(".")[0]
    return "0" if s in ("-0", "−0") else s
