#!/usr/bin/env python3
"""
cover.py — Generate cover.pdf directly from tokens.json using reportlab.

Usage:
    python3 cover.py --tokens tokens.json --out cover.pdf

Reads tokens.json["cover_pattern"] and renders the matching cover pattern.
No HTML, no external rendering engine — pure Python.

Exit codes: 0 success, 1 bad args/missing file, 3 render error
"""

import argparse
import importlib.util
import json
import os
import sys


def ensure_deps():
    missing = [p for p in ("reportlab",) if importlib.util.find_spec(p) is None]
    if missing:
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install",
             "--break-system-packages", "-q"] + missing
        )

ensure_deps()

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# A4 in points: 595.27 x 841.89
# Design space: 794 x 1123 px ≈ A4
SCALE_X = A4[0] / 794.0
SCALE_Y = A4[1] / 1123.0


def _scale(x, y):
    """Convert design coordinates (794x1123) to PDF points."""
    return x * SCALE_X, A4[1] - y * SCALE_Y  # flip Y




def _hex(color_str, default="#000000"):
    """Parse hex color string to reportlab Color."""
    if not color_str:
        return HexColor(default)
    if isinstance(color_str, Color):
        return color_str
    color_str = str(color_str).lstrip("#")
    if len(color_str) == 6:
        return HexColor("#" + color_str)
    return HexColor(default)


def _hex_with_alpha(color_str, alpha=1.0):
    """Parse hex color with alpha channel."""
    base = _hex(color_str)
    return Color(base.red, base.green, base.blue, alpha)


class CoverRenderer:
    """Render cover PDF directly with reportlab Canvas."""

    def __init__(self, tokens: dict, out_path: str):
        self.t = tokens
        self.out = out_path
        self.c = canvas.Canvas(out_path, pagesize=A4)
        self.c.setTitle(tokens.get("title", "Cover"))
        self.c.setAuthor(tokens.get("author", ""))
        self.W = A4[0]
        self.H = A4[1]
        # Font mapping — auto-detect CJK and use CID fonts
        self._init_fonts(tokens)

    def _init_fonts(self, tokens: dict):
        """Register fonts: CJK TrueType (preferred) → CID fallback (preset compat)."""
        from reportlab.pdfbase.ttfonts import TTFont

        # ── CJK TrueType: try system fonts for crisp large-size rendering ──
        cjk_ttf_candidates = [
            "C:/Windows/Fonts/msyh.ttc",                   # 微软雅黑
            "C:/Windows/Fonts/msyhbd.ttc",                 # 微软雅黑 Bold
            "C:/Windows/Fonts/simsun.ttc",                 # 宋体
            "C:/Windows/Fonts/simhei.ttf",                 # 黑体
            "/System/Library/Fonts/PingFang.ttc",          # macOS
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        ]
        self.font_cjk_ttf = None
        for path in cjk_ttf_candidates:
            if os.path.exists(path):
                try:
                    name = "cjk_" + os.path.splitext(os.path.basename(path))[0]
                    pdfmetrics.registerFont(TTFont(name, path, subfontIndex=0))
                    self.font_cjk_ttf = name
                    break
                except Exception:
                    continue

        # ── CID fallback: works for both preset patterns and custom layouts ──
        cjk_name = tokens.get("font_cjk_rl", "STSong-Light")
        try:
            pdfmetrics.registerFont(UnicodeCIDFont(cjk_name))
            self.font_display = cjk_name
            self.font_body    = cjk_name
        except Exception:
            self.font_display = "Times-Bold"
            self.font_body    = "Helvetica"

    def _font_for(self, font_type: str, text: str = "") -> str:
        """Pick best font: TTF for all text when available, CID fallback otherwise."""
        if self.font_cjk_ttf:
            return self.font_cjk_ttf
        return self.font_display if font_type == "display" else self.font_body

    def finish(self):
        self.c.save()

    # ── helpers ───────────────────────────────────────────────────────────

    def _bg(self, color):
        """Fill entire page background."""
        self.c.setFillColor(_hex(color))
        self.c.rect(0, 0, self.W, self.H, fill=1, stroke=0)

    def _rect(self, x, y, w, h, color, alpha=1.0):
        """Draw filled rectangle."""
        px, py = _scale(x, y + h)
        self.c.setFillColor(_hex_with_alpha(color, alpha))
        self.c.rect(px, py, w * SCALE_X, h * SCALE_Y, fill=1, stroke=0)

    def _line(self, x1, y1, x2, y2, color, width=1.0, alpha=1.0):
        """Draw line."""
        px1, py1 = _scale(x1, y1)
        px2, py2 = _scale(x2, y2)
        self.c.setStrokeColor(_hex_with_alpha(color, alpha))
        self.c.setLineWidth(width * SCALE_X)
        self.c.line(px1, py1, px2, py2)

    def _text(self, x, y, text, font, size, color, alpha=1.0, anchor="start"):
        """Draw text."""
        px, py = _scale(x, y)
        self.c.setFont(font, size * SCALE_Y)
        self.c.setFillColor(_hex_with_alpha(color, alpha))
        if anchor == "middle":
            self.c.drawCentredString(px, py, text)
        elif anchor == "end":
            self.c.drawRightString(px, py, text)
        else:
            self.c.drawString(px, py, text)

    def _wrap_text(self, x, y, text, font, size, color, max_width,
                   line_height=None, alpha=1.0, align="start"):
        """Draw wrapped text block (word-based for Latin, char-based for CJK)."""
        if line_height is None:
            line_height = size * 1.4
        px, py = _scale(x, y)
        font_size = size * SCALE_Y
        self.c.setFont(font, font_size)
        self.c.setFillColor(_hex_with_alpha(color, alpha))
        max_w = max_width * SCALE_X

        lines = []
        current = ""

        if any(ord(c) > 0x7f for c in text):
            # CJK: wrap by character, treating \n as line break
            for ch in text:
                if ch == '\n':
                    lines.append(current)
                    current = ""
                    continue
                test = current + ch
                if self.c.stringWidth(test, font, font_size) <= max_w:
                    current = test
                else:
                    if current:
                        lines.append(current)
                    current = ch
        else:
            # Latin: wrap by word
            words = text.split()
            for word in words:
                test = current + (" " if current else "") + word
                if self.c.stringWidth(test, font, font_size) <= max_w:
                    current = test
                else:
                    if current:
                        lines.append(current)
                    current = word

        if current:
            lines.append(current)

        for i, line in enumerate(lines):
            ly = py - i * line_height * SCALE_Y
            if align == "middle":
                self.c.drawCentredString(px, ly, line)
            elif align == "end":
                self.c.drawRightString(px, ly, line)
            else:
                self.c.drawString(px, ly, line)
        return y + len(lines) * line_height

    def _dot_grid(self, x0, y0, cols, rows, gap, r, color, alpha):
        """Draw dot grid pattern."""
        self.c.setFillColor(_hex_with_alpha(color, alpha))
        for row in range(rows):
            for col in range(cols):
                cx = x0 + col * gap
                cy = y0 + row * gap
                px, py = _scale(cx, cy)
                self.c.circle(px, py, r * SCALE_X, fill=1, stroke=0)

    def _resolve_template_vars(self, elements):
        """Replace {token_key} in all element string values with token values.
        Strip unresolved {…} patterns to avoid garbled display."""
        import re
        self._unresolved = set()

        def _sub(v):
            if not isinstance(v, str):
                return v
            s = v
            for tk, tv in self.t.items():
                if isinstance(tv, (str, int, float)):
                    s = s.replace("{" + tk + "}", str(tv))
            leftover = re.findall(r'\{(\w+)\}', s)
            if leftover:
                self._unresolved.update(leftover)
                s = re.sub(r'\s*\{\w+\}\s*', ' ', s).strip()
            return s

        resolved = []
        for el in elements:
            new_el = {}
            for key, value in el.items():
                if isinstance(value, str):
                    new_el[key] = _sub(value)
                elif isinstance(value, list) and value and isinstance(value[0], list):
                    # Nested lists (e.g., polygon points)
                    new_el[key] = [[_sub(v) for v in pt] for pt in value]
                elif isinstance(value, list):
                    new_el[key] = [_sub(v) for v in value]
                else:
                    new_el[key] = value
            resolved.append(new_el)
        return resolved

    def _draw_polygon(self, points, color, alpha=1.0):
        """Draw filled polygon from list of [x, y] points (design space)."""
        self.c.setFillColor(_hex_with_alpha(color, alpha))
        path = self.c.beginPath()
        px, py = _scale(float(points[0][0]), float(points[0][1]))
        path.moveTo(px, py)
        for pt in points[1:]:
            px, py = _scale(float(pt[0]), float(pt[1]))
            path.lineTo(px, py)
        path.close()
        self.c.drawPath(path, fill=1, stroke=0)

    def _draw_bracket(self, bx, by, bw, bh, color, width=2.0):
        """Draw corner brackets with arm length auto-determined."""
        self.c.setStrokeColor(_hex(color))
        self.c.setLineWidth(width * SCALE_X)
        arm = min(28, bw * 0.15, bh * 0.3)
        # Top-left
        px, py = _scale(bx, by)
        self.c.line(px, py, px, py - bh * SCALE_Y)
        self.c.line(px, py, px + arm * SCALE_X, py)
        # Top-right
        px2, py2 = _scale(bx + bw, by)
        self.c.line(px2, py2, px2, py2 - arm * SCALE_Y)
        self.c.line(px2, py2, px2 - arm * SCALE_X, py2)
        # Bottom-left
        px3, py3 = _scale(bx, by - bh)
        self.c.line(px3, py3, px3 + arm * SCALE_X, py3)

    def _from_layout(self):
        """Render cover from AI-generated layout_params."""
        params = self.t.get("layout_params", {})
        elements = params.get("elements", [])
        elements = self._resolve_template_vars(elements)

        for el in elements:
            el_type = el.get("type")
            if el_type == "rect":
                self._rect(el["x"], el["y"], el["w"], el["h"],
                          el["color"], el.get("opacity", 1.0))
            elif el_type == "line":
                self._line(el["x1"], el["y1"], el["x2"], el["y2"],
                          el["color"], el.get("width", 1.0), el.get("opacity", 1.0))
            elif el_type == "text":
                text_content = el.get("text", "")
                self._text(el["x"], el["y"], text_content,
                          self._font_for("display" if el.get("font") == "display" else "body", text_content),
                          el["size"], el["color"], el.get("opacity", 1.0),
                          el.get("align", "start"))
            elif el_type == "text_block":
                text_content = el.get("text", "")
                self._wrap_text(el["x"], el["y"], text_content,
                               self._font_for("display" if el.get("font") == "display" else "body", text_content),
                               el["size"], el["color"], el["max_w"],
                               el.get("line_h"), el.get("opacity", 1.0),
                               el.get("align", "start"))
            elif el_type == "dot_grid":
                self._dot_grid(el["x"], el["y"], el["cols"], el["rows"],
                              el["gap"], el["r"], el["color"], el.get("opacity", 1.0))
            elif el_type == "polygon":
                self._draw_polygon(el["points"], el["color"], el.get("opacity", 1.0))
            elif el_type == "bracket":
                self._draw_bracket(el["x"], el["y"], el["w"], el["h"],
                                  el["color"], el.get("width", 2.0))

    # ── Pattern implementations ──────────────────────────────────────────

    def _fullbleed(self):
        t = self.t
        bg = t.get("cover_bg", "#F6F7F9")
        accent = t["accent"]
        text_l = t.get("text_light", "#000000")
        muted = t.get("muted", "#9CA3AF")
        dark = t.get("dark", "#000000")
        M = 80  # consistent margin
        self._bg(bg)
        # Top vignette — subtle darkening
        self._rect(0, 0, 794, 1123 * 0.42, dark, 0.08)
        # Right accent bars (layered depth)
        self._rect(794 - 140, 0, 140, 6, accent)
        self._rect(794 - 320, 0, 180, 3, accent, 0.35)
        # Vertical accent rail (left)
        self._rect(M - 32, 1123 * 0.24, 2.5, 1123 * 0.46, accent, 0.3)
        # Dot grid — right decorative field
        self._dot_grid(610, 60, 7, 14, 24, 1.6, accent, 0.05)
        # Label
        label_parts = [t.get('doc_type', 'Document').upper()]
        if t.get('date'):
            label_parts.append(t.get('date'))
        self._text(M, 1123 * 0.24, "  ·  ".join(label_parts), self.font_body, 10, accent, 0.75)
        # Title
        self._wrap_text(M, 1123 * 0.31, t["title"], self.font_display, 56,
                       text_l, 794 - M * 2, 56 * 1.12)
        # Accent rule
        self._line(M, 1123 * 0.49, M + 380, 1123 * 0.49, accent, 2.5)
        # Subtitle
        if t.get("subtitle"):
            self._wrap_text(M, 1123 * 0.54, t["subtitle"], self.font_body, 12.5,
                          muted, 500, 12.5 * 1.7)
        # Footer — thin rule + meta
        footer_y = 1123 - 56
        self._line(M, footer_y, 794 - M, footer_y, accent, 0.6, 0.18)
        self._text(M, 1123 - 36, t.get("author", "") or "", self.font_body, 10, muted, 0.7)
        self._text(794 - M, 1123 - 36, t.get("date", "") or "", self.font_body, 10, muted, 0.6, anchor="end")

    def _split(self):
        t = self.t
        bg = t.get("cover_bg", "#F6F7F9")
        accent = t["accent"]
        text_l = t.get("text_light", "#000000")
        muted = t.get("muted", "#9CA3AF")
        page_bg = t.get("page_bg", "#FAFAF8")
        dark = t.get("dark", "#111111")
        panel_w = 302  # ~38% golden-section panel
        M = 48
        self._bg(page_bg)
        # Left panel
        self._rect(0, 0, panel_w, 1123, bg)
        self._rect(0, 0, panel_w, 5, accent)
        # Divider line
        self._rect(panel_w - 1, 0, 2.5, 1123, accent)
        # Right side dot grid — subtle
        self._dot_grid(panel_w + 60, 80, 6, 12, 28, 1.4, muted, 0.12)
        # Title on left
        self._wrap_text(M, 1123 * 0.28, t["title"], self.font_display, 40,
                       text_l, panel_w - M * 2)
        # Rule
        rule_len = panel_w * 0.5
        self._line(M, 1123 * 0.44, M + rule_len, 1123 * 0.44, accent, 2)
        # Subtitle
        if t.get("subtitle"):
            self._wrap_text(M, 1123 * 0.49, t["subtitle"], self.font_body, 11.5,
                          muted, panel_w - M * 2, 11.5 * 1.7)
        # Author + date on left
        meta_y = 1123 * 0.72
        self._text(M, meta_y, t.get("author", "") or "", self.font_body, 12, text_l)
        if t.get("date"):
            self._text(M, meta_y + 20, t["date"], self.font_body, 10, muted)
        # Right side: doc type label
        rx = panel_w + 64
        self._text(794 - M, 1123 - 72, t.get("doc_type", "").upper(),
                  self.font_body, 9.5, muted, anchor="end")
        # Right side: accent bottom bar
        self._rect(rx, 1123 * 0.84, 140, 3, accent, 0.25)

    def _typographic(self):
        t = self.t
        accent = t["accent"]
        dark = t.get("dark", "#000000")
        muted = t.get("muted", "#888888")
        self._bg(t.get("page_bg", "#FAFAF8"))
        M = 80
        # Title — first word accent + stack rest on next line
        words = t["title"].split()
        first = words[0] if words else ""
        rest = " ".join(words[1:]) if len(words) > 1 else ""
        title_sz = 74
        line_h = title_sz * 1.05
        self._text(M, 1123 * 0.33, first, self.font_display, title_sz, accent)
        if rest:
            self._wrap_text(M, 1123 * 0.33 + line_h, rest, self.font_display,
                           title_sz, dark, 794 - M * 2, line_h)
        # Thick rule across page
        self._line(M, 1123 * 0.56, 794 - M, 1123 * 0.56, accent, 1.8, 0.4)
        # Meta: author left / date right
        self._text(M, 1123 * 0.62, t.get("author", "") or "", self.font_body, 14, dark)
        self._text(794 - M, 1123 * 0.62, t.get("date", "") or "", self.font_body, 12, muted, anchor="end")
        # Subtitle
        if t.get("subtitle"):
            self._wrap_text(M, 1123 * 0.69, t["subtitle"], self.font_body, 13, muted, 520, 13 * 1.7)
        # Bottom accent dot
        self._rect(M, 1123 * 0.84, 4, 4, accent, 0.3)

    def _atmospheric(self):
        t = self.t
        bg = t.get("cover_bg", "#F6F7F9")
        accent = t["accent"]
        text_l = t.get("text_light", "#000000")
        muted = t.get("muted", "#9CA3AF")
        dark = t.get("dark", "#000000")
        M = 80
        self._bg(bg)
        # Bottom vignette — darkness fading up
        self._rect(0, 1123 * 0.72, 794, 1123 * 0.28, dark, 0.2)
        # Accent anchor bar — top
        self._rect(0, 0, 240, 3.5, accent)
        # Dot grid — full-page atmospheric
        self._dot_grid(60, 100, 15, 20, 22, 1.4, accent, 0.04)
        # Label
        label_parts = [t.get('doc_type', '').upper()]
        if t.get('date'):
            label_parts.append(t.get('date'))
        self._text(M, 1123 * 0.25, "  ·  ".join(label_parts), self.font_body, 10, accent, 0.7)
        # Title
        self._wrap_text(M, 1123 * 0.33, t["title"], self.font_display, 52,
                       text_l, 794 - M * 2, 52 * 1.08)
        # Short accent rule
        self._line(M, 1123 * 0.54, M + 60, 1123 * 0.54, accent, 2.5)
        # Subtitle
        if t.get("subtitle"):
            self._wrap_text(M, 1123 * 0.61, t["subtitle"], self.font_body, 13, muted, 480, 13 * 1.6)
        # Footer
        self._text(M, 1123 - 56, t.get("author", "") or "", self.font_body, 11, text_l, 0.55)
        self._text(794 - M, 1123 - 56, t.get("date", "") or "", self.font_body, 10.5, muted, anchor="end")

    def _minimal(self):
        t = self.t
        accent = t["accent"]
        dark = t.get("dark", "#000000")
        muted = t.get("muted", "#999999")
        self._bg(t.get("page_bg", "#FAFAF8"))
        M = 80
        # Accent sidebar — 10px wide, stronger presence
        self._rect(0, 0, 10, 1123, accent)
        # Content area offset from sidebar
        cx = M
        # Eyebrow label
        self._text(cx, 1123 * 0.26, t.get("doc_type", "").upper(),
                  self.font_body, 10, accent, 0.8)
        # Title
        self._wrap_text(cx, 1123 * 0.34, t["title"], self.font_display, 68,
                       dark, 794 - cx - M)
        # Thin rule
        self._line(cx, 1123 * 0.57, cx + 64, 1123 * 0.57, dark, 1.2, 0.15)
        # Subtitle
        if t.get("subtitle"):
            self._wrap_text(cx, 1123 * 0.63, t["subtitle"], self.font_body, 13,
                          muted, 500, 13 * 1.7)
        # Meta
        meta_parts = []
        if t.get("author"):
            meta_parts.append(t["author"])
        if t.get("date"):
            meta_parts.append(t["date"])
        self._text(cx, 1123 * 0.84, "  ·  ".join(meta_parts), self.font_body, 10.5, muted)

    def _stripe(self):
        t = self.t
        accent = t["accent"]
        dark = t.get("cover_bg", "#0A0D12")
        light = t.get("page_bg", "#FAFAF8")
        text_l = t.get("text_light", "#FFFFFF")
        muted = t.get("muted", "#888888")
        # Three bands — golden-section proportions
        top_h = 180
        mid_h = 490
        bot_h = 1123 - top_h - mid_h
        M = 80
        # Bands
        self._rect(0, 0, 794, top_h, accent)          # top: accent
        self._rect(0, top_h, 794, mid_h, dark)         # mid: dark
        self._rect(0, top_h + mid_h, 794, bot_h, light) # bot: light
        # Separators
        self._line(0, top_h, 794, top_h, text_l, 1, 0.15)
        self._line(0, top_h + mid_h, 794, top_h + mid_h, accent, 2)
        # Top: eyebrow
        self._text(M, top_h - 36, t.get("doc_type", "").upper(),
                  self.font_body, 11, dark, 0.7)
        # Mid: title
        self._wrap_text(M, top_h + mid_h * 0.32, t["title"], self.font_display, 58,
                       text_l, 794 - M * 2, 58 * 1.06)
        # Mid: short accent line under title block
        title_bottom = top_h + mid_h * 0.54
        self._line(M, title_bottom, M + 100, title_bottom, accent, 3)
        # Bottom: meta
        by = top_h + mid_h + 72
        self._text(M, by, t.get("author", "") or "", self.font_body, 14, dark)
        if t.get("date"):
            self._text(M, by + 24, t["date"], self.font_body, 11.5, muted)
        if t.get("subtitle"):
            self._wrap_text(M, by + 60, t["subtitle"], self.font_body, 12.5, muted, 560, 12.5 * 1.6)

    def _diagonal(self):
        t = self.t
        dark_bg = t.get("cover_bg", "#000000")
        light_bg = t.get("page_bg", "#FAFCFF")
        accent = t["accent"]
        text_l = t.get("text_light", "#FFFFFF")
        text_d = t.get("dark", "#000000")
        muted = t.get("muted", "#7A8A99")
        M = 80
        self._bg(light_bg)
        # Diagonal polygon — more dramatic cut
        cut_y = 580
        cut_x = 794
        self.c.setFillColor(_hex(dark_bg))
        path = self.c.beginPath()
        px, py = _scale(0, 0)
        path.moveTo(px, py)
        px, py = _scale(cut_x, 0)
        path.lineTo(px, py)
        px, py = _scale(cut_x, cut_y)
        path.lineTo(px, py)
        px, py = _scale(0, cut_y + 220)
        path.lineTo(px, py)
        path.close()
        self.c.drawPath(path, fill=1, stroke=0)
        # Accent diagonal edge
        self._line(0, cut_y + 220, 794, cut_y, accent, 2.5)
        # Eyebrow
        label_parts = [t.get('doc_type', '').upper()]
        if t.get('date'):
            label_parts.append(t.get('date'))
        self._text(M, 160, "  ·  ".join(label_parts), self.font_body, 10, accent, 0.75)
        # Title — on dark side
        self._wrap_text(M, 220, t["title"], self.font_display, 54, text_l, 560, 54 * 1.1)
        # Accent rule on dark side
        self._line(M, cut_y - 60, M + 64, cut_y - 60, accent, 3)
        # Author — on light side
        self._text(M, 1123 - 72, t.get("author", "") or "", self.font_body, 13, text_d)
        # Subtitle on light side
        if t.get("subtitle"):
            self._wrap_text(M, 1123 - 44, t["subtitle"], self.font_body, 11, muted, 500)

    def _frame(self):
        t = self.t
        bg = t.get("cover_bg", "#FAF8F3")
        accent = t["accent"]
        dark = t.get("dark", "#2A1A0A")
        muted = t.get("muted", "#9A8A78")
        self._bg(bg)
        pad = 36
        inner_pad = pad + 24
        # Outer frame — subtle
        self.c.setStrokeColor(_hex_with_alpha(dark, 0.25))
        self.c.setLineWidth(1.5 * SCALE_X)
        ppx, ppy = _scale(pad, pad)
        self.c.rect(ppx, ppy, (794 - 2*pad) * SCALE_X, (1123 - 2*pad) * SCALE_Y, fill=0, stroke=1)
        # Top accent strip above frame
        self._rect(inner_pad, pad + 12, 794 - 2*inner_pad, 3, accent)
        # Bottom accent strip
        self._rect(inner_pad, 1123 - pad - 15, 794 - 2*inner_pad, 3, accent)
        # Corner ornaments — more elegant
        corner_sz = 10
        for cx, cy in [(pad-5, pad-5), (794-pad-5, pad-5),
                       (pad-5, 1123-pad-5), (794-pad-5, 1123-pad-5)]:
            self._rect(cx, cy, corner_sz, corner_sz, accent, 0.55)
        # Content area — centered
        cx = 794 / 2
        # Eyebrow
        self._text(cx, 1123 * 0.28, t.get("doc_type", "").upper(),
                  self.font_body, 9, accent, anchor="middle")
        # Short rule
        self._line(cx - 36, 1123 * 0.34, cx + 36, 1123 * 0.34, dark, 1, 0.2)
        # Title — centered
        self._wrap_text(cx, 1123 * 0.40, t["title"], self.font_display, 48,
                       dark, 540, 48 * 1.22)
        # Accent rule under title
        self._line(cx - 24, 1123 * 0.63, cx + 24, 1123 * 0.63, accent, 2)
        # Subtitle
        if t.get("subtitle"):
            self._wrap_text(cx, 1123 * 0.69, t["subtitle"], self.font_body, 13,
                          muted, 440, 13 * 1.6)
        # Meta centered at bottom
        meta_parts = []
        if t.get("author"):
            meta_parts.append(t["author"])
        if t.get("date"):
            meta_parts.append(t["date"])
        self._text(cx, 1123 * 0.86, "  ·  ".join(meta_parts), self.font_body, 10.5,
                  muted, anchor="middle")

    def _editorial(self):
        t = self.t
        bg = t.get("cover_bg", "#FFFFFF")
        accent = t["accent"]
        dark = t.get("dark", "#000000")
        muted = t.get("muted", "#777777")
        is_dark = bg.startswith("#0") or bg.startswith("#1") or bg.startswith("#2")
        body_color = t.get("text_light", "#FFFFFF") if is_dark else dark
        M = 80
        self._bg(bg)
        # Ghost letter — larger, lower opacity
        ghost = t["title"][0].upper() if t["title"] else "A"
        self._text(794 - 80, 260, ghost, self.font_display, 660, body_color, 0.04, anchor="end")
        # Top accent bar
        self._rect(0, 0, 794, 6, accent)
        # Category
        self._text(M, 48, t.get("doc_type", "").upper(), self.font_body, 10, accent, 0.8)
        # Title
        self._wrap_text(M, 1123 * 0.34, t["title"].upper(), self.font_display, 76,
                       body_color, 794 - M * 2, 76 * 0.92)
        # Subtitle
        if t.get("subtitle"):
            self._wrap_text(M, 1123 * 0.62, t["subtitle"], self.font_body, 14, muted, 540, 14 * 1.6)
        # Footer rule
        self._line(M, 1123 - 76, 794 - M, 1123 - 76, body_color, 0.8, 0.12)
        # Footer
        self._text(M, 1123 - 48, t.get("author", "") or "", self.font_body, 11, muted)
        self._text(794 - M, 1123 - 48, t.get("date", "") or "", self.font_body, 10, muted, anchor="end")

    def _magazine(self):
        t = self.t
        bg = t.get("cover_bg", "#F2F0EC")
        accent = t["accent"]
        dark = t.get("dark", "#000000")
        muted = t.get("muted", "#888888")
        self._bg(bg)
        cx = 794 / 2
        # Org name
        org = t.get("doc_type", "").upper()
        self._text(cx, 1123 * 0.17, org, self.font_body, 10, dark, 0.6, anchor="middle")
        # Org rule
        self._line(cx - 32, 1123 * 0.21, cx + 32, 1123 * 0.21, accent, 2.5)
        # Title — bigger, more generous tracking via line height
        self._wrap_text(cx, 1123 * 0.28, t["title"], self.font_display, 54,
                       dark, 560, 54 * 1.12)
        # Title rule
        self._line(cx - 24, 1123 * 0.53, cx + 24, 1123 * 0.53, accent, 2.5)
        # Subtitle
        if t.get("subtitle"):
            self._wrap_text(cx, 1123 * 0.59, t["subtitle"], self.font_body, 14, muted, 460, 14 * 1.6)
        # Author (accent colored for impact)
        self._text(cx, 1123 * 0.78, t.get("author", "") or "", self.font_display, 18, accent, anchor="middle")
        # Rule under author
        self._line(cx - 40, 1123 * 0.81, cx + 40, 1123 * 0.81, dark, 1, 0.15)
        # Date
        self._text(cx, 1123 * 0.84, t.get("date", "") or "", self.font_body, 11, muted, anchor="middle")

    def _darkroom(self):
        t = self.t
        bg = t.get("cover_bg", "#F6F7F9")
        accent = t["accent"]
        text_l = t.get("text_light", "#000000")
        muted = t.get("muted", "#9CA3AF")
        self._bg(bg)
        cx = 794 / 2
        # Org name
        org = t.get("doc_type", "").upper()
        self._text(cx, 1123 * 0.17, org, self.font_body, 10, text_l, 0.5, anchor="middle")
        # Org rule
        self._line(cx - 32, 1123 * 0.21, cx + 32, 1123 * 0.21, text_l, 2, 0.3)
        # Title
        self._wrap_text(cx, 1123 * 0.28, t["title"], self.font_display, 54,
                       text_l, 560, 54 * 1.12)
        # Title rule
        self._line(cx - 24, 1123 * 0.53, cx + 24, 1123 * 0.53, text_l, 2.5, 0.3)
        # Subtitle
        if t.get("subtitle"):
            self._wrap_text(cx, 1123 * 0.59, t["subtitle"], self.font_body, 14, muted, 460, 14 * 1.6)
        # Author
        self._text(cx, 1123 * 0.78, t.get("author", "") or "", self.font_display, 18, text_l, anchor="middle")
        # Rule under author
        self._line(cx - 40, 1123 * 0.81, cx + 40, 1123 * 0.81, text_l, 1, 0.15)
        # Date
        self._text(cx, 1123 * 0.84, t.get("date", "") or "", self.font_body, 11, muted, anchor="middle")

    def _terminal(self):
        t = self.t
        bg = t.get("cover_bg", "#F6F7F9")
        accent = t["accent"]
        text_l = t.get("text_light", "#000000")
        muted = t.get("muted", "#9CA3AF")
        M = 80
        self._bg(bg)
        # Grid overlay — more subtle, larger cells
        self.c.setStrokeColor(_hex_with_alpha(accent, 0.05))
        self.c.setLineWidth(0.5 * SCALE_X)
        cell = 56
        for y in range(0, 1124, cell):
            px1, py1 = _scale(0, y)
            px2, py2 = _scale(794, y)
            self.c.line(px1, py1, px2, py2)
        for x in range(0, 795, cell):
            px1, py1 = _scale(x, 0)
            px2, py2 = _scale(x, 1123)
            self.c.line(px1, py1, px2, py2)
        # Status bar (top)
        self._rect(0, 0, 794, 36, accent, 0.08)
        # Status indicators
        self._rect(M - 40, 12, 8, 8, accent)
        label = f"SYSTEM_REPORT  //  {t.get('date', '')}"
        self._text(M, 12 + 6, label, self.font_body, 10, accent)
        # Bracket frame — simplified, cleaner
        bracket_x = M
        bracket_y = 320
        bracket_w = 794 - M * 2
        bracket_h = 260
        self.c.setStrokeColor(_hex(accent))
        self.c.setLineWidth(2.2 * SCALE_X)
        px, py = _scale(bracket_x, bracket_y)
        # Top-left corner
        self.c.line(px, py, px, py - bracket_h * SCALE_Y)
        self.c.line(px, py, px + 28 * SCALE_X, py)
        # Top-right
        px2, py2 = _scale(bracket_x + bracket_w, bracket_y)
        self.c.line(px2, py2, px2, py2 - 28 * SCALE_Y)
        self.c.line(px2, py2, px2 - 28 * SCALE_X, py2)
        # Bottom-left
        px3, py3 = _scale(bracket_x, bracket_y - bracket_h)
        self.c.line(px3, py3, px3 + 28 * SCALE_X, py3)
        # Title inside bracket
        self._wrap_text(bracket_x + 24, bracket_y + 52, t["title"].upper(),
                       self.font_body, 44, text_l, bracket_w - 48, 44 * 1.08)
        # Subtitle with > prefix
        if t.get("subtitle"):
            self._text(bracket_x + 24, bracket_y + 52 + 44 * 1.5,
                      f'> {t["subtitle"]}', self.font_body, 13, accent)
        # Info block (right aligned below bracket)
        info_x = bracket_x
        info_y = bracket_y - bracket_h - 100
        self._text(info_x, info_y, "AUTHOR_ID", self.font_body, 8, muted)
        self._text(info_x, info_y + 20, t.get("author", "") or "", self.font_body, 14, text_l)
        self._text(info_x, info_y + 42, t.get("doc_type", "").upper(),
                  self.font_body, 10, accent)
        # Bottom status bar
        bar_y = 36
        self._rect(0, 1123 - bar_y, 794, bar_y, accent, 0.1)
        self._text(M, 1123 - bar_y + 12, "Ln 1, Col 1", self.font_body, 9, muted, 0.7)
        self._text(794 / 2, 1123 - bar_y + 12, "UTF-8  |  COVER.PY v3", self.font_body, 9, muted, 0.7, anchor="middle")
        self._text(794 - M, 1123 - bar_y + 12, "GENERATED_AUTOMATICALLY",
                  self.font_body, 9, muted, 0.7, anchor="end")

    def _poster(self):
        t = self.t
        bg = t.get("cover_bg", "#FFFFFF")
        accent = t["accent"]
        dark = t.get("dark", "#000000")
        muted = t.get("muted", "#888888")
        self._bg(bg)
        M = 76  # inner margin from sidebar
        # Sidebar — wider for more impact
        sidebar_w = 48
        self._rect(0, 0, sidebar_w, 1123, accent)
        content_x = sidebar_w + M
        # Title — large, condensed feel
        self._wrap_text(content_x, 96, t["title"].upper(), self.font_display, 88,
                       dark, 794 - content_x - M, 88 * 0.90)
        # Subtitle under title
        if t.get("subtitle"):
            self._text(content_x, 96 + 88 * 1.2 + 16, t["subtitle"],
                      self.font_body, 12.5, muted)
        # Bold rule
        self._line(content_x, 96 + 88 * 1.2 + 48, content_x + 72, 96 + 88 * 1.2 + 48, dark, 2.5)
        # Meta stack
        meta_y = 96 + 88 * 1.2 + 90
        if t.get("author"):
            self._text(content_x, meta_y, t["author"], self.font_body, 13, dark)
            meta_y += 24
        if t.get("date"):
            self._text(content_x, meta_y, t["date"], self.font_body, 11, muted)
        # Icon block (right side) — simplified geometric mark
        icon_x = 794 - M - 56
        icon_y = 400
        icon_sz = 56
        self._rect(icon_x, icon_y, icon_sz, icon_sz, accent)
        lx = icon_x + 14
        self._line(lx, icon_y + 18, icon_x + icon_sz - 14, icon_y + 18, bg, 2.5)
        self._line(lx, icon_y + 30, icon_x + icon_sz - 20, icon_y + 30, bg, 2.5)
        self._line(lx, icon_y + 42, icon_x + icon_sz - 14, icon_y + 42, bg, 2.5)

    def render(self):
        # ── AI-generated layout takes priority ──
        if self.t.get("layout_params"):
            self._from_layout()
            self.finish()
            return

        pattern = self.t.get("cover_pattern", "fullbleed")
        dispatch = {
            "fullbleed": self._fullbleed,
            "split": self._split,
            "typographic": self._typographic,
            "atmospheric": self._atmospheric,
            "minimal": self._minimal,
            "stripe": self._stripe,
            "diagonal": self._diagonal,
            "frame": self._frame,
            "editorial": self._editorial,
            "magazine": self._magazine,
            "darkroom": self._darkroom,
            "terminal": self._terminal,
            "poster": self._poster,
        }
        fn = dispatch.get(pattern, self._fullbleed)
        fn()
        self.finish()


# ── CLI ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Render cover PDF from tokens.json")
    parser.add_argument("--tokens", default="tokens.json")
    parser.add_argument("--out", default="cover.pdf")
    parser.add_argument("--subtitle", default="", help="Optional subtitle override")
    parser.add_argument("--abstract", default="", help="Optional abstract text (resolves {abstract})")
    parser.add_argument("--version", default="", help="Optional version string (resolves {version})")
    args = parser.parse_args()

    try:
        with open(args.tokens, encoding="utf-8") as f:
            tokens = json.load(f)
    except FileNotFoundError:
        print(json.dumps({"status": "error", "error": f"tokens file not found: {args.tokens}"}),
              file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "error": f"invalid JSON: {e}"}), file=sys.stderr)
        sys.exit(1)

    if args.subtitle:
        tokens["subtitle"] = args.subtitle
    if args.abstract:
        tokens["abstract"] = args.abstract
    if args.version:
        tokens["version"] = args.version

    try:
        renderer = CoverRenderer(tokens, args.out)
        renderer.render()
        size_kb = os.path.getsize(args.out) // 1024
        print(json.dumps({
            "status": "ok",
            "out": args.out,
            "pattern": tokens.get("cover_pattern"),
            "size_kb": size_kb,
        }))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}), file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
