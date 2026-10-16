"""Cached optional FreeType font measurements; no per-text subprocesses."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import shutil
import subprocess
import unicodedata
import re


@dataclass(frozen=True)
class TextMetrics:
    advance: float
    left: float
    top: float
    right: float
    bottom: float
    font_file: str
    ascent: float | None = None
    descent: float | None = None
    x_height: float | None = None


@lru_cache(maxsize=128)
def resolve_font(family, weight="normal", style="normal"):
    try:
        if Path(family).is_file():
            return family, 0
    except OSError:
        return None
    executable = shutil.which("fc-match")
    if not executable:
        return None
    pattern = family.replace('"', "").replace("'", "")
    if weight in ("bold", "bolder", "600", "700", "800", "900"):
        pattern += ":weight=bold"
    if style in ("italic", "oblique"):
        pattern += ":slant=italic"
    try:
        result = subprocess.run(
            [executable, "--format=%{file}\n%{index}\n%{family}", pattern],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        )
        lines = result.stdout.splitlines()
        # fc-match always returns *some* font, even for a nonexistent family.
        # Treating that fallback as exact made Latin labels use unrelated-font
        # metrics while CJK labels from the same family used estimates.
        normalize = lambda name: re.sub(r"[\s_-]+", "", name).casefold()
        requested = {normalize(x.strip(" \"'")) for x in family.split(",")}
        generic = {"sansserif", "serif", "monospace", "systemui", "cursive", "fantasy"}
        matched = {normalize(x) for x in lines[2].split(",")} if len(lines) > 2 else set()
        if not (requested & generic or requested & matched):
            return None
        if lines and Path(lines[0]).is_file():
            return lines[0], int(lines[1] or 0) if len(lines) > 1 else 0
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return None


@lru_cache(maxsize=64)
def _font(file, index):
    try:
        from PIL import ImageFont, features
        from fontTools.ttLib import TTFont, TTLibError
    except ImportError:
        return None
    try:
        font = ImageFont.truetype(file, size=256, index=index)
        with TTFont(file, fontNumber=index & 0xFFFF, lazy=True) as table:
            coverage = frozenset(table.getBestCmap() or ())
        return font, coverage, features.check("raqm")
    except (OSError, ValueError, TTLibError):
        return None


@lru_cache(maxsize=4096)
def measure_text(text, family, size, weight="normal", style="normal"):
    resolved = resolve_font(family or "sans-serif", str(weight), style)
    if not resolved:
        return None
    loaded = _font(*resolved)
    if not loaded:
        return None
    font, coverage, shaping = loaded
    if any(ord(c) not in coverage for c in text if not c.isspace()):
        return None
    # BASIC layout does not shape combining marks or contextual scripts.
    if not shaping and any(unicodedata.combining(c) or unicodedata.bidirectional(c) in ("R", "AL", "AN") for c in text):
        return None
    try:
        scale = float(size) / 256
        left, top, right, bottom = font.getbbox(text, anchor="ls")
        ascent, descent = font.getmetrics()
        x_height = -font.getbbox("x", anchor="ls")[1] * scale if ord("x") in coverage else None
        return TextMetrics(
            font.getlength(text) * scale,
            left * scale,
            top * scale,
            right * scale,
            bottom * scale,
            resolved[0],
            ascent * scale,
            descent * scale,
            x_height,
        )
    except (ValueError, AttributeError):
        return None


def estimate_advance(text, size, weight="normal"):
    """Deterministic fallback in em units, without fonts or subprocesses."""
    total = 0.0
    east_asian_context = any(
        unicodedata.east_asian_width(c) in ("W", "F") and unicodedata.category(c).startswith("L") for c in text
    )
    for c in text:
        if unicodedata.combining(c) or unicodedata.category(c) in ("Mn", "Me", "Cf"):
            continue
        if unicodedata.east_asian_width(c) in ("W", "F"):
            width = 1.0
        elif east_asian_context and c in "—–…":
            width = 1.0
        elif c.isspace():
            width = 0.33
        elif c in "ilI|!.,:;'`":
            width = 0.28
        elif c in "MW@%&":
            width = 0.9
        elif c in "mw":
            width = 0.82
        elif c in "()[]{}":
            width = 0.36
        elif c in "-_/\\":
            width = 0.4
        elif c.isdigit():
            width = 0.6
        elif c.isupper():
            width = 0.7
        elif c in "·×→↑↓←◆◈§":
            width = 0.7
        else:
            width = 0.56
        # Bold Latin advances are often slightly wider; CJK generally remains
        # one em. Do not inflate every CJK character to compensate for fonts.
        if str(weight) in ("bold", "bolder", "600", "700", "800", "900") and width < 1:
            width *= 1.04
        total += width
    return max(0.0, total * float(size))


def lint_floor_width(text, family, size, weight="normal", letter_spacing=0):
    """Width the Slides server lint will estimate for a wrap="false" run."""
    try:
        import sys
        from pathlib import Path

        scripts = str(Path(__file__).resolve().parents[2])
        if scripts not in sys.path:
            sys.path.append(scripts)
        from xml_lint import estimate_text_width
    except ImportError:
        return 0.0
    bold = str(weight) in ("bold", "bolder", "600", "700", "800", "900")
    return float(estimate_text_width(text.rstrip(), size, letter_spacing, bold, family or ""))


def text_advance(text, family, size, weight="normal", style="normal", letter_spacing=0, *, metrics="auto"):
    """Return advance plus inter-character spacing."""
    if metrics not in ("auto", "legacy"):
        raise ValueError("font metrics must be auto or legacy")
    measured = measure_text(text, family or "sans-serif", size, str(weight), style) if metrics == "auto" else None
    advance = measured.advance if measured is not None else estimate_advance(text, size, weight)
    glyphs = sum(not unicodedata.combining(c) and unicodedata.category(c) not in ("Mn", "Me", "Cf") for c in text)
    return max(0.0, advance + max(0, glyphs - 1) * float(letter_spacing))


def baseline_offset(baseline, size, metric=None):
    """Convert a supported SVG baseline to its alphabetic baseline (down +)."""
    if baseline == "central":
        if metric is not None and metric.ascent is not None and metric.descent is not None:
            return (metric.ascent - metric.descent) / 2
        return float(size) * 0.35
    if baseline == "middle":
        if metric is not None and metric.x_height is not None:
            return metric.x_height / 2
        return float(size) * 0.25
    return 0.0
