#!/usr/bin/env python3
"""
_fonts.py — Cross-platform CJK font resolver for ReportLab.

Motivation
----------
Agents that generate PDFs from Chinese/Japanese/Korean content routinely
fail on font issues:
  1. They pick a core PDF font (Helvetica/Arial/Times) that only covers
     Latin-1, so CJK characters render as blank boxes.
  2. They hard-code a path that does not exist on the current machine.
  3. They register a font but then ask for an italic/bold variant that
     was never registered, crashing with "font not found".
  4. They use a .ttc (TrueType Collection) file but don't pass the
     subfont index, or the subsetter chokes on tables like MERG / COLR
     inside the collection and drops glyphs.

This module solves all four issues:

  * Probes a curated, per-platform priority list of CJK-capable fonts.
  * Prefers modern sans-serif CJK faces (PingFang / Hiragino Sans GB on
     macOS, Microsoft YaHei on Windows, Noto Sans CJK on Linux) for the
     best on-screen rendering, falling back to older but universally
     available faces (Arial Unicode MS, SimHei, WenQuanYi) only when the
     preferred candidates are absent.
  * When only a .ttc is available, registers it with the correct
     ``subfontIndex``.
  * Registers a full font family via ``registerFontFamily`` so that
     bold / italic / bold-italic lookups never raise — missing variants
     silently fall back to the regular face.
  * Returns a diagnostic record so callers can print exactly which font
     was used (or why detection failed).

Usage
-----
    from _fonts import register_cjk_font

    result = register_cjk_font()
    if result.ok:
        body_font = result.family            # e.g. "CJK"
        bold_font = result.bold_family       # e.g. "CJK-Bold" or "CJK"
    else:
        body_font = "Helvetica"              # Latin-only fallback
        print(result.reason)
"""

from __future__ import annotations

import math
import os
import platform
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# reportlab subsetter patch — preserve or inject the ``gasp`` table
# ---------------------------------------------------------------------------
# reportlab's TTFontFile.makeSubset only keeps 13 tables. The ``gasp``
# table (8-16 bytes, tells viewers when to grid-fit vs. anti-alias) is
# stripped. Without it, CJK body text at 10-12pt looks blurry because
# viewers fall back to pure grayscale AA instead of snapping strokes to
# the pixel grid.
#
# Some system fonts (e.g. STHeiti on macOS) never had a gasp table to
# begin with. On macOS this is fine (CoreText ignores gasp), but when
# a PDF generated on macOS is opened on Windows, the absence of gasp
# causes GDI/DirectWrite to skip ClearType — same blurriness problem.
#
# We monkey-patch makeSubset: call the original, then splice ``gasp``
# into the serialized sfnt binary. If the original font had gasp, we
# preserve it; if not, we inject a safe universal default.
# ---------------------------------------------------------------------------

def _splice_tables(font_data: bytes, extra: dict) -> bytes:
    """Splice extra tables into a serialized TrueType (sfnt) font binary."""
    if len(font_data) < 12:
        return font_data

    num_tables = struct.unpack('>H', font_data[4:6])[0]
    old_dir_end = 12 + num_tables * 16

    # Parse existing directory
    existing_tags = set()
    dir_entries = []
    for i in range(num_tables):
        off = 12 + i * 16
        tag_b = font_data[off:off + 4]
        cs, toff, tlen = struct.unpack('>III', font_data[off + 4:off + 16])
        existing_tags.add(tag_b)
        dir_entries.append([tag_b, cs, toff, tlen])

    to_add = {k: v for k, v in extra.items()
              if k.encode('ascii').ljust(4)[:4] not in existing_tags}
    if not to_add:
        return font_data

    new_num = num_tables + len(to_add)
    new_dir_end = 12 + new_num * 16
    shift = new_dir_end - old_dir_end

    # Shift existing table offsets
    for e in dir_entries:
        e[2] += shift

    # Append new table data after existing data
    table_data = font_data[old_dir_end:]
    append_off = new_dir_end + len(table_data)
    appended = b''
    for tag_str, data in to_add.items():
        tag_b = tag_str.encode('ascii')[:4].ljust(4, b' ')
        padded = data + b'\x00' * ((4 - len(data) % 4) % 4)
        cs = 0
        for j in range(0, len(padded), 4):
            cs = (cs + struct.unpack('>I', padded[j:j + 4])[0]) & 0xFFFFFFFF
        dir_entries.append([tag_b, cs, append_off, len(data)])
        appended += padded
        append_off += len(padded)

    dir_entries.sort(key=lambda e: e[0])

    # Recompute sfnt header
    sr = (2 ** int(math.log2(new_num))) * 16
    es = int(math.log2(sr // 16))
    rs = new_num * 16 - sr
    header = font_data[:4] + struct.pack('>HHHH', new_num, sr, es, rs)

    dir_bytes = b''.join(
        e[0] + struct.pack('>III', e[1], e[2], e[3]) for e in dir_entries
    )
    return header + dir_bytes + table_data + appended


def _build_default_gasp() -> bytes:
    """Build a minimal gasp table: enable grid-fit + AA at all sizes.

    Format: version(u16) + numRanges(u16) + [rangeMaxPPEM(u16) + behavior(u16)]
    Behavior 0x000F = GRIDFIT | DOGRAY | SYMMETRIC_GRIDFIT | SYMMETRIC_SMOOTHING
    — the safest universal default that tells every renderer (GDI, DirectWrite,
    FreeType) to enable all available hinting and smoothing.
    """
    return struct.pack('>HH HH', 0, 1, 0xFFFF, 0x000F)


def _patch_subsetter() -> None:
    """Monkey-patch reportlab to preserve or inject gasp in font subsets.

    If the original font has a gasp table, splice it into the subset
    (reportlab's default makeSubset strips it).  If the original font
    lacks gasp entirely (e.g. STHeiti), inject a safe default so that
    Windows GDI/DirectWrite renderers still enable ClearType.
    """
    try:
        from reportlab.pdfbase import ttfonts
    except ImportError:
        return
    if getattr(_patch_subsetter, '_done', False):
        return

    _orig = ttfonts.TTFontFile.makeSubset

    def _makeSubset_keep_gasp(self, subset):
        result = _orig(self, subset)
        extra = {}
        for tag in ('gasp',):
            try:
                extra[tag] = self.get_table(tag)
            except (KeyError, RuntimeError):
                # Original font has no gasp — inject a safe default
                extra[tag] = _build_default_gasp()
        return _splice_tables(result, extra) if extra else result

    ttfonts.TTFontFile.makeSubset = _makeSubset_keep_gasp
    _patch_subsetter._done = True


# (path, subfont_index, display_label)
# Priority: modern sans-serif CJK faces first for best on-screen rendering,
# then legacy faces as fallback.  All original paths are kept — only the
# order changed — so machines that relied on a lower-priority font will
# still find it; they just won't be the first pick anymore.
CANDIDATES = {
    "Darwin": [
        # --- Best available sans-serif for reportlab ---
        # STHeiti Medium — TrueType outlines, reliable across macOS 10.6+.
        # Precursor to PingFang with clean CJK glyphs.  This is the best
        # font reportlab can actually use on modern macOS because:
        #   - Hiragino Sans GB uses PostScript/CFF outlines → TTFont rejects
        #   - PingFang.ttc moved to PrivateFrameworks on macOS 13+ and its
        #     new PingFangUI.ttc lacks a loca table → TTFont rejects
        # STHeiti is the highest-quality TrueType-outline CJK font that
        # still ships at a stable public path.
        ("/System/Library/Fonts/STHeiti Medium.ttc", 0, "STHeiti Medium"),
        ("/System/Library/Fonts/STHeiti Light.ttc", 0, "STHeiti Light"),
        # --- Try Hiragino / PingFang anyway for older macOS where they
        # still had TrueType outlines or sat at public paths ---
        ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0, "Hiragino Sans GB"),
        ("/System/Library/Fonts/PingFang.ttc", 0, "PingFang SC"),
        ("/System/Library/Fonts/Supplemental/PingFang.ttc", 0, "PingFang SC"),
        # --- Wide-coverage fallback (single .ttf, no subsetting surprises,
        # but dated 2000-era CJK glyph design — looks mechanical) ---
        ("/Library/Fonts/Arial Unicode.ttf", 0, "Arial Unicode MS"),
        ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 0, "Arial Unicode MS"),
        # --- Serif fallback ---
        ("/System/Library/Fonts/Supplemental/Songti.ttc", 0, "Songti SC"),
    ],
    "Windows": [
        # --- Microsoft YaHei — default CJK sans-serif since Vista,
        # highest quality screen-rendering with DirectWrite hinting.
        # Try .ttc first (Win8+), then .ttf (Vista/Win7). ---
        ("C:/Windows/Fonts/msyh.ttc", 0, "Microsoft YaHei"),
        ("C:/Windows/Fonts/msyh.ttf", 0, "Microsoft YaHei"),
        ("C:/Windows/Fonts/msyhl.ttf", 0, "Microsoft YaHei Light"),
        # --- SimHei — universal bold sans, present on every Chinese Windows.
        # Mechanical glyph design but extremely stable. ---
        ("C:/Windows/Fonts/simhei.ttf", 0, "SimHei"),
        # --- Serif / CJK fallback ---
        ("C:/Windows/Fonts/simsun.ttc", 0, "SimSun"),
        # --- JPN / KOR / TC coverage ---
        ("C:/Windows/Fonts/msjh.ttc", 0, "Microsoft JhengHei"),
        ("C:/Windows/Fonts/YuGothR.ttc", 0, "Yu Gothic"),
        ("C:/Windows/Fonts/malgun.ttf", 0, "Malgun Gothic"),
        # --- Stylistic faces (仿宋/楷体) — only if nothing else matched ---
        ("C:/Windows/Fonts/simfang.ttf", 0, "FangSong"),
        ("C:/Windows/Fonts/simkai.ttf", 0, "KaiTi"),
    ],
    "Linux": [
        # Noto CJK single-face files (preferred — OTF, no subsetting issues)
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf", 0, "Noto Sans CJK"),
        ("/usr/share/fonts/opentype/noto/NotoSansSC-Regular.otf", 0, "Noto Sans SC"),
        ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 0, "Noto Sans CJK"),
        # WenQuanYi fallback
        ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 0, "WenQuanYi Micro Hei"),
        ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 0, "WenQuanYi Zen Hei"),
        # Arphic
        ("/usr/share/fonts/truetype/arphic/uming.ttc", 0, "AR PL UMing"),
        ("/usr/share/fonts/truetype/arphic/ukai.ttc", 0, "AR PL UKai"),
        # Droid (older Android/Debian)
        ("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", 0, "Droid Sans Fallback"),
    ],
}


# Bold sibling candidates: when a regular face is found, look for a
# bold face in the same directory. Keys are the regular filename (lower-
# case basename), values are ordered lists of bold candidate basenames.
# Bold sibling candidates per regular-font basename.
#
# Each value is a list of (sibling_basename, subfont_index) tuples tried
# in order until one registers successfully. Multiple tuples for the same
# file are used when the subfont index for a heavy weight is known to
# shift across OS versions — PingFang.ttc is the canonical example (its
# Semibold has sat at index 3, 4, and 5 on different macOS releases).
#
# An empty list means "no bold variant available" (e.g. STHeiti Medium is
# itself the bold face; SimHei is already heavy).
BOLD_SIBLINGS = {
    # macOS
    "hiragino sans gb.ttc": [("Hiragino Sans GB.ttc", 1)],  # subfont 1 = W6
    "stheiti medium.ttc": [],
    "stheiti light.ttc": [("STHeiti Medium.ttc", 0)],
    # PingFang: try the heaviest reasonable subfont first. macOS 12/13/14
    # all have Semibold somewhere in 3..5; we prefer Semibold over Medium,
    # and Medium over nothing, so the order is 5 → 4 → 3.
    "pingfang.ttc": [
        ("PingFang.ttc", 5),
        ("PingFang.ttc", 4),
        ("PingFang.ttc", 3),
    ],
    # Windows
    "simhei.ttf": [],  # SimHei is already a "bold" style
    "simfang.ttf": [],
    "simkai.ttf": [],
    "msyh.ttf": [("msyhbd.ttf", 0)],
    "msyh.ttc": [("msyhbd.ttc", 0)],
    "simsun.ttc": [],
    # Linux
    "notosanscjk-regular.otf": [("NotoSansCJK-Bold.otf", 0)],
    "notosanscjk-regular.ttc": [("NotoSansCJK-Bold.ttc", 0)],
    "notosanssc-regular.otf": [("NotoSansSC-Bold.otf", 0)],
}


@dataclass
class FontResult:
    ok: bool
    family: Optional[str] = None        # e.g. "CJK"
    bold_family: Optional[str] = None   # e.g. "CJK-Bold" or falls back to family
    path: Optional[str] = None
    label: Optional[str] = None
    reason: Optional[str] = None


def _system() -> str:
    s = platform.system()
    return s if s in CANDIDATES else "Linux"


def _iter_candidates() -> List[Tuple[str, int, str]]:
    """Return platform candidates with $FONT_OVERRIDE env var injected first."""
    out: List[Tuple[str, int, str]] = []
    override = os.environ.get("WUKONG_CJK_FONT")
    if override and Path(override).exists():
        out.append((override, 0, Path(override).stem))
    out.extend(CANDIDATES[_system()])
    return out


def _try_register_face(name: str, path: str, subfont: int) -> bool:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont, TTFError

    # Skip if already registered
    try:
        pdfmetrics.getFont(name)
        return True
    except KeyError:
        pass

    try:
        pdfmetrics.registerFont(TTFont(name, path, subfontIndex=subfont))
        return True
    except TTFError as e:
        print(f"[_fonts] skip {path}#{subfont}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[_fonts] skip {path}#{subfont}: {type(e).__name__}: {e}",
              file=sys.stderr)
        return False


def _find_bold_sibling_candidates(regular_path: Path) -> List[Tuple[Path, int]]:
    """Return *existing* bold sibling candidates for *regular_path*.

    Each entry is ``(path, subfont_index)``. The list preserves the
    priority order declared in :data:`BOLD_SIBLINGS`; the caller tries
    them sequentially and stops at the first one that registers.
    """
    key = regular_path.name.lower()
    out: List[Tuple[Path, int]] = []
    for sibling_name, subfont in BOLD_SIBLINGS.get(key, []):
        p = regular_path.parent / sibling_name
        if p.exists():
            out.append((p, subfont))
    return out


def register_cjk_font(family: str = "CJK") -> FontResult:
    """Register a CJK-capable font family with ReportLab.

    Returns a :class:`FontResult`. On success, ``result.family`` is the
    name you pass as ``fontName=`` in a ParagraphStyle; ``result.bold_family``
    is the bold variant (falls back to ``family`` if no bold face found).
    Italic and bold-italic are always mapped to regular / bold, so you
    can freely use ``<i>`` / ``<b>`` markup in Paragraph text without
    triggering "font not registered" errors.
    """
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.pdfmetrics import registerFontFamily
    except ImportError:
        return FontResult(ok=False, reason="reportlab not installed")

    # Ensure gasp table is preserved in subsets before any font is
    # registered — the patch is idempotent so multiple calls are safe.
    _patch_subsetter()

    tried: List[str] = []
    for path_str, subfont, label in _iter_candidates():
        p = Path(path_str)
        if not p.exists():
            continue
        tried.append(path_str)
        if not _try_register_face(family, str(p), subfont):
            continue

        # Regular face registered. Try bold sibling candidates in the
        # order declared in BOLD_SIBLINGS — priority matters for fonts
        # like PingFang where we prefer Semibold > Medium > Regular.
        bold_name = family  # default: bold ⇒ regular
        candidate_name = f"{family}-Bold"
        for bold_path, bold_subfont in _find_bold_sibling_candidates(p):
            if _try_register_face(candidate_name, str(bold_path), bold_subfont):
                bold_name = candidate_name
                break

        # Map all 4 family variants — italic/bold-italic fall back safely
        try:
            registerFontFamily(
                family,
                normal=family,
                bold=bold_name,
                italic=family,
                boldItalic=bold_name,
            )
        except Exception as e:
            print(f"[_fonts] registerFontFamily warning: {e}", file=sys.stderr)

        return FontResult(
            ok=True,
            family=family,
            bold_family=bold_name,
            path=str(p),
            label=label,
        )

    # Last-ditch fallback: reportlab ships a handful of Adobe CID fonts
    # that embed a CJK encoding without needing a .ttf/.ttc file at all.
    # Coverage is Simplified Chinese only (plus basic punctuation) and
    # bold is not available, but it's better than a broken PDF on hosts
    # where every file-based candidate had PostScript outlines inside a
    # .ttc collection (the classic "Arial Unicode removed on macOS 13+"
    # scenario). We only reach this branch when every curated path
    # above has failed or was absent.
    try:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.pdfbase.pdfmetrics import registerFont

        registerFont(UnicodeCIDFont("STSong-Light"))
        # NOTE: ``registerFontFamily`` only creates an alias lookup for
        # ``<b>`` / ``<i>`` inside Paragraph markup — it does NOT create a
        # new typeface under *family*, so ``canvas.setFont(family, ...)``
        # would fail with a KeyError. We therefore return the raw PS name
        # (``STSong-Light``) as the family, and register the family so
        # Paragraph-level bold/italic lookups still work.
        try:
            registerFontFamily(
                "STSong-Light",
                normal="STSong-Light",
                bold="STSong-Light",
                italic="STSong-Light",
                boldItalic="STSong-Light",
            )
        except Exception as e:
            print(f"[_fonts] CID registerFontFamily warning: {e}", file=sys.stderr)
        return FontResult(
            ok=True,
            family="STSong-Light",
            bold_family="STSong-Light",
            path="(builtin UnicodeCIDFont)",
            label="STSong-Light (Adobe CID, SC only)",
            reason="no TTF/TTC candidates matched; using built-in CID fallback",
        )
    except Exception as e:
        print(f"[_fonts] CID fallback failed: {type(e).__name__}: {e}", file=sys.stderr)

    reason = (
        f"No CJK font found on {_system()}. Tried: {tried or '(none existed)'}. "
        "Set WUKONG_CJK_FONT=/path/to/your/font.ttf to override."
    )
    return FontResult(ok=False, reason=reason)


def contains_cjk(text: str) -> bool:
    """Return True if *text* contains any CJK Unified character."""
    for ch in text:
        o = ord(ch)
        if (
            0x3000 <= o <= 0x303F       # CJK symbols and punctuation
            or 0x3040 <= o <= 0x309F    # Hiragana
            or 0x30A0 <= o <= 0x30FF    # Katakana
            or 0x3400 <= o <= 0x4DBF    # CJK Unified Ideographs Ext A
            or 0x4E00 <= o <= 0x9FFF    # CJK Unified Ideographs
            or 0xAC00 <= o <= 0xD7AF    # Hangul syllables
            or 0xF900 <= o <= 0xFAFF    # CJK Compat Ideographs
            or 0xFF00 <= o <= 0xFFEF    # Halfwidth / fullwidth forms
        ):
            return True
    return False


if __name__ == "__main__":
    # Self-test: report what would happen on this machine.
    res = register_cjk_font()
    if res.ok:
        print(f"OK   family={res.family} bold={res.bold_family}")
        print(f"     path={res.path}")
        print(f"     label={res.label}")
    else:
        print(f"FAIL {res.reason}")
        sys.exit(1)
