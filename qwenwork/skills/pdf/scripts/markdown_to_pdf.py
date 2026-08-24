#!/usr/bin/env python3
"""
markdown_to_pdf.py — Markdown to PDF Converter

Two rendering engines:
  - **reportlab** (default): pure Python, zero system deps, fast, lightweight.
    Best for simple documents. Emoji and advanced CSS are NOT supported.
  - **playwright**: renders Markdown as styled HTML in headless Chromium,
    then "prints" to PDF. Full emoji, CSS, GitHub-style code blocks, and
    pixel-perfect typography. Requires ``playwright`` + Chromium binary.

The engine is selected via ``--engine`` (reportlab | playwright | auto).
``auto`` (default) checks for emoji / complex formatting in the source and
uses Playwright when available; falls back to ReportLab otherwise.

Supported Markdown features (both engines):
    - headings (h1–h6), paragraphs, emphasis/strong, inline code
    - fenced code blocks with syntax highlighting
    - ordered / unordered / nested lists
    - blockquotes
    - tables (GFM)
    - horizontal rules
    - hyperlinks
    - images (local file paths and remote URLs)

Usage:
    python scripts/markdown_to_pdf.py README.md --output readme.pdf
    python scripts/markdown_to_pdf.py report.md --output report.pdf --engine playwright
    python scripts/markdown_to_pdf.py report.md --output report.pdf --theme professional
    python scripts/markdown_to_pdf.py doc.md --output doc.pdf --page-size a4

Requirements:
    reportlab engine: markdown-it-py, reportlab, pygments, pillow
    playwright engine: markdown-it-py, playwright (+ Chromium via playwright install)
"""

from __future__ import annotations

import argparse
import html as html_lib
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

# Make _fonts importable regardless of cwd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fonts import FontResult, contains_cjk, register_cjk_font  # noqa: E402


# Set by convert_markdown_to_pdf before token walking. Inline <code> and
# fenced code block content use this face so that CJK comments inside
# code blocks render correctly. Defaults to Courier (Latin-only).
_CODE_FACE: str = "Courier"


THEMES = {
    "default": {
        "body_font": "Times-Roman",
        "body_size": 11,
        "leading": 15,
        "h1_color": "#1a1a2e",
        "h2_color": "#16213e",
        "link_color": "#0f3460",
        "code_bg": "#f4f4f4",
    },
    "professional": {
        "body_font": "Helvetica",
        "body_size": 10.5,
        "leading": 15,
        "h1_color": "#003366",
        "h2_color": "#003366",
        "link_color": "#003366",
        "code_bg": "#eef2f7",
    },
    "minimal": {
        "body_font": "Courier",
        "body_size": 10,
        "leading": 13,
        "h1_color": "#111111",
        "h2_color": "#111111",
        "link_color": "#333333",
        "code_bg": "#f0f0f0",
    },
}


class MissingDependency(RuntimeError):
    """Raised when a required Python dependency is missing.

    Raising (instead of sys.exit) keeps the module usable as a library
    from tests or batch scripts — the CLI main() catches this and exits.
    """


def _import_deps():
    try:
        from markdown_it import MarkdownIt  # noqa: F401
    except ImportError as e:
        raise MissingDependency("markdown-it-py not installed") from e
    try:
        import reportlab  # noqa: F401
    except ImportError as e:
        raise MissingDependency("reportlab not installed") from e


def _inline_to_rl(tokens) -> str:
    """Render markdown-it inline token stream to ReportLab Paragraph markup.

    ReportLab Paragraph supports: <b>, <i>, <u>, <font>, <br/>, <a href="">,
    <sub>, <super>. We convert inline MD tokens accordingly and escape text.
    Image tokens become a bracketed fallback here because Paragraph markup
    cannot embed images inline; block-level images are handled separately
    by _extract_block_image().
    """
    out: List[str] = []
    for t in tokens:
        ttype = t.type
        if ttype == "text":
            out.append(html_lib.escape(t.content))
        elif ttype == "softbreak" or ttype == "hardbreak":
            out.append("<br/>")
        elif ttype == "code_inline":
            txt = html_lib.escape(t.content)
            out.append(
                f'<font face="{_CODE_FACE}" backColor="#f0f0f0">{txt}</font>'
            )
        elif ttype == "strong_open":
            out.append("<b>")
        elif ttype == "strong_close":
            out.append("</b>")
        elif ttype == "em_open":
            out.append("<i>")
        elif ttype == "em_close":
            out.append("</i>")
        elif ttype == "s_open":
            out.append("<strike>")
        elif ttype == "s_close":
            out.append("</strike>")
        elif ttype == "link_open":
            href = dict(t.attrs or {}).get("href", "")
            out.append(f'<a href="{html_lib.escape(href)}" color="#0f3460">')
        elif ttype == "link_close":
            out.append("</a>")
        elif ttype == "image":
            alt = html_lib.escape(t.content or "image")
            out.append(f"[{alt}]")
        elif ttype == "html_inline":
            # best effort: strip raw HTML to avoid breaking the paragraph
            out.append(html_lib.escape(t.content))
    return "".join(out)


class _OutlineParagraph:
    """Factory for a Paragraph subclass that registers a PDF bookmark
    and outline entry at draw time.

    We can't subclass Paragraph at import time because reportlab isn't
    guaranteed to be importable yet (the module may be run without its
    generator deps installed — e.g. by tests that only touch the CLI
    argument parsing). This helper defers the subclass construction
    until the first heading is actually rendered.

    Each heading gets a unique bookmark key based on id(self); using the
    label text would collide when the same heading appears twice.
    """

    _klass = None

    @classmethod
    def new(cls, label_text: str, style, level: int):
        if cls._klass is None:
            from reportlab.platypus import Paragraph

            class _P(Paragraph):
                def __init__(self, text, s, outline_label, outline_level):
                    Paragraph.__init__(self, text, s)
                    self._outline_label = outline_label
                    self._outline_level = outline_level

                def draw(self):
                    key = f"h-{id(self)}"
                    try:
                        self.canv.bookmarkPage(key)
                        # reportlab outline level is 0-indexed: H1 → 0.
                        self.canv.addOutlineEntry(
                            self._outline_label,
                            key,
                            level=self._outline_level,
                            closed=False,
                        )
                    except Exception:
                        # A broken outline must never break rendering —
                        # skip silently and fall through to the normal
                        # Paragraph draw path.
                        pass
                    Paragraph.draw(self)

            cls._klass = _P

        # Heading text has already been converted to Paragraph markup
        # (``<b>``, ``<font>``, etc.); strip those tags for the outline
        # label since the outline panel is plain text.
        import re as _re
        clean_label = _re.sub(r"<[^>]+>", "", label_text).strip() or "(untitled)"
        return cls._klass(label_text, style, clean_label, level)


def _extract_block_image(inline_token) -> Optional[dict]:
    """If a paragraph's inline token contains a single image (plus optional
    whitespace), return its src/alt so the caller can emit an RLImage
    flowable instead of a Paragraph. Otherwise return None.
    """
    children = inline_token.children or []
    image = None
    for c in children:
        if c.type == "image":
            if image is not None:
                return None  # multiple images → keep as paragraph text
            image = c
        elif c.type == "text" and not c.content.strip():
            continue
        elif c.type in ("softbreak", "hardbreak"):
            continue
        else:
            return None  # any other content → not a pure image paragraph
    if image is None:
        return None
    attrs = dict(image.attrs or {})
    return {
        "src": attrs.get("src", ""),
        "alt": image.content or attrs.get("alt", ""),
    }


def _download_image(url: str, timeout: int = 30) -> Optional[str]:
    """Download a remote image to a temporary file. Returns the path or None."""
    import urllib.request
    import urllib.error

    try:
        from urllib.parse import urlparse
        url_path = urlparse(url).path
        suffix = Path(url_path).suffix.lower()
        if suffix not in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"):
            suffix = ".png"
        tmp = Path(tempfile.mkdtemp()) / f"dl_img{suffix}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            tmp.write_bytes(resp.read())
        if tmp.stat().st_size == 0:
            return None
        return str(tmp)
    except Exception as e:
        print(f"[markdown_to_pdf] image download failed: {url}: {e}",
              file=sys.stderr)
        return None


def _make_image_flowable(
    src: str,
    alt: str,
    base_dir: Path,
    max_width_pt: float,
    max_height_pt: Optional[float] = None,
):
    """Build an RLImage flowable preserving aspect ratio, or None on failure.

    Supports both local file paths and remote URLs (http/https). Remote
    images are downloaded to a temporary file first. ``data:`` URIs are
    still skipped (too large to be practical in PDF generation).
    """
    from reportlab.platypus import Image as RLImage, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet

    if not src:
        return None

    img_path: Optional[str] = None

    if src.startswith(("http://", "https://")):
        img_path = _download_image(src)
        if img_path is None:
            return None
    elif src.startswith("data:"):
        return None
    else:
        p = Path(src)
        if not p.is_absolute():
            p = (base_dir / p).resolve()
        if not p.exists():
            return None
        img_path = str(p)

    try:
        from PIL import Image as PILImage
        with PILImage.open(img_path) as im:
            w, h = im.size
        if w <= 0 or h <= 0:
            return None
        ratio = h / w
        display_w = min(float(max_width_pt), float(w))
        display_h = display_w * ratio
        # Cap height so a tall image can't exceed the page frame.
        if max_height_pt is not None and display_h > max_height_pt:
            display_h = float(max_height_pt)
            display_w = display_h / ratio
        return RLImage(img_path, width=display_w, height=display_h)
    except Exception as e:
        print(f"[markdown_to_pdf] image failed: {img_path}: {e}", file=sys.stderr)
        return None


# Pygments token → color mapping. Prefix matching is used at lookup
# time so subtypes (Token.Keyword.Constant, Token.Literal.String.Double,
# etc.) fall through to the nearest ancestor entry.
_PYGMENTS_COLORS = [
    ("Token.Keyword",                "#0000aa"),
    ("Token.Name.Function",          "#005fa0"),
    ("Token.Name.Class",             "#005fa0"),
    ("Token.Name.Builtin",           "#005fa0"),
    ("Token.Name.Decorator",         "#aa6600"),
    ("Token.Name.Namespace",         "#005fa0"),
    ("Token.Name.Attribute",         "#005fa0"),
    ("Token.Name.Tag",               "#aa0000"),
    ("Token.Literal.String",         "#aa5500"),
    ("Token.Literal.Number",         "#666666"),
    ("Token.Comment",                "#888888"),
    ("Token.Operator.Word",          "#0000aa"),
    ("Token.Operator",               "#111111"),
    ("Token.Punctuation",            "#555555"),
]


def _color_for_token(tok_str: str) -> Optional[str]:
    # Longest-prefix-first lookup.
    best: Optional[str] = None
    best_len = -1
    for prefix, color in _PYGMENTS_COLORS:
        if tok_str == prefix or tok_str.startswith(prefix + "."):
            if len(prefix) > best_len:
                best = color
                best_len = len(prefix)
    return best


def _highlight_code(code: str, lang: str) -> str:
    """Return ReportLab XPreformatted-safe, pygments-colored markup.

    Unlike the previous implementation, this returns text with real
    ``\\n`` line breaks (NOT ``<br/>``) because XPreformatted treats
    newlines as hard line breaks AND lets reportlab split the flowable
    across pages. Inline markup (``<font color=...>``) is preserved.
    """
    try:
        from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
    except ImportError:
        return html_lib.escape(code)

    lexer = None
    if lang:
        try:
            lexer = get_lexer_by_name(lang)
        except Exception:
            lexer = None
    if lexer is None:
        try:
            lexer = guess_lexer(code)
        except Exception:
            lexer = TextLexer()

    pieces: List[str] = []
    for tok, val in lexer.get_tokens(code):
        if not val:
            continue
        esc = html_lib.escape(val)  # keep real newlines for XPreformatted
        color = _color_for_token(str(tok))
        if color:
            pieces.append(f'<font color="{color}">{esc}</font>')
        else:
            pieces.append(esc)
    return "".join(pieces).rstrip("\n")


def _tokens_to_flowables(tokens, styles, theme, ctx):
    from reportlab.platypus import (
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        HRFlowable,
        ListFlowable,
        ListItem,
        XPreformatted,
    )
    from reportlab.lib import colors

    flow = []
    i = 0
    n = len(tokens)

    while i < n:
        t = tokens[i]
        tt = t.type

        if tt == "heading_open":
            level = int(t.tag[1])
            inline = tokens[i + 1]
            content = _inline_to_rl(inline.children or [])
            style_name = f"H{min(level, 4)}"
            flow.append(Spacer(1, 6))
            # H1-H3 become outline entries so PDF readers show a
            # navigable tree; H4+ fall back to plain paragraphs because
            # outline trees deeper than 3 levels become noisy.
            if level <= 3:
                flow.append(
                    _OutlineParagraph.new(content, styles[style_name], level - 1)
                )
            else:
                flow.append(Paragraph(content, styles[style_name]))
            flow.append(Spacer(1, 4))
            i += 3
            continue

        if tt == "paragraph_open":
            inline = tokens[i + 1]
            # If the paragraph is just an image, emit RLImage flowable.
            img = _extract_block_image(inline)
            if img is not None:
                rl_img = _make_image_flowable(
                    img["src"],
                    img["alt"],
                    ctx["base_dir"],
                    ctx["max_width"],
                    ctx.get("max_height"),
                )
                if rl_img is not None:
                    flow.append(rl_img)
                    flow.append(Spacer(1, 4))
                else:
                    # Missing/remote image → fall back to bracketed alt text.
                    alt = html_lib.escape(img["alt"] or img["src"] or "image")
                    flow.append(Paragraph(f"[{alt}]", styles["Body"]))
            else:
                content = _inline_to_rl(inline.children or [])
                if content.strip():
                    flow.append(Paragraph(content, styles["Body"]))
            i += 3
            continue

        if tt in ("fence", "code_block"):
            parts = (t.info or "").strip().split()
            lang = parts[0] if parts else ""
            marked = _highlight_code(t.content.rstrip("\n"), lang)
            # XPreformatted is splittable across pages AND supports our
            # <font color=...> inline markup. No single-cell Table wrapper
            # (that made the block unsplittable and overflowed tall code).
            pre = XPreformatted(marked, styles["Code"])
            flow.append(pre)
            flow.append(Spacer(1, 6))
            i += 1
            continue

        if tt == "hr":
            flow.append(Spacer(1, 4))
            flow.append(HRFlowable(width="100%", thickness=0.5,
                                   color=colors.HexColor("#cccccc")))
            flow.append(Spacer(1, 4))
            i += 1
            continue

        if tt == "blockquote_open":
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                if tokens[j].type == "blockquote_open":
                    depth += 1
                elif tokens[j].type == "blockquote_close":
                    depth -= 1
                j += 1
            inner = _tokens_to_flowables(tokens[i + 1:j - 1], styles, theme, ctx)
            tbl = Table([[inner]], colWidths=[ctx["max_width"]])
            tbl.setStyle(
                TableStyle([
                    ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor("#999999")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafafa")),
                ])
            )
            flow.append(tbl)
            flow.append(Spacer(1, 4))
            i = j
            continue

        if tt in ("bullet_list_open", "ordered_list_open"):
            ordered = tt == "ordered_list_open"
            depth = 1
            j = i + 1
            close_name = "ordered_list_close" if ordered else "bullet_list_close"
            open_name = tt
            while j < n and depth > 0:
                if tokens[j].type == open_name:
                    depth += 1
                elif tokens[j].type == close_name:
                    depth -= 1
                j += 1
            items = _collect_list_items(tokens[i + 1:j - 1], styles, theme, ctx)
            flow.append(
                ListFlowable(
                    [ListItem(x, leftIndent=14) for x in items],
                    bulletType="1" if ordered else "bullet",
                    start="1" if ordered else "circle",
                    leftIndent=14,
                )
            )
            flow.append(Spacer(1, 4))
            i = j
            continue

        if tt == "table_open":
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                if tokens[j].type == "table_open":
                    depth += 1
                elif tokens[j].type == "table_close":
                    depth -= 1
                j += 1
            rows, ncols = _collect_table_rows(tokens[i + 1:j - 1], styles)
            if rows and ncols > 0:
                col_w = ctx["max_width"] / ncols
                tbl = Table(rows, repeatRows=1, colWidths=[col_w] * ncols)
                tbl.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ])
                )
                flow.append(tbl)
                flow.append(Spacer(1, 6))
            i = j
            continue

        i += 1

    return flow


def _collect_list_items(tokens, styles, theme, ctx):
    """Extract a list item's flowables from a flat token slice."""
    items = []
    i = 0
    n = len(tokens)
    while i < n:
        t = tokens[i]
        if t.type == "list_item_open":
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                if tokens[j].type == "list_item_open":
                    depth += 1
                elif tokens[j].type == "list_item_close":
                    depth -= 1
                j += 1
            items.append(_tokens_to_flowables(tokens[i + 1:j - 1], styles, theme, ctx))
            i = j
            continue
        i += 1
    return items


def _collect_table_rows(tokens, styles):
    """Return (rows, num_cols). Each row is a list of Paragraphs; header
    cells use the bold TableHeader style so the first row is visibly
    bolder than body rows.

    markdown-it drops cell tokens (th_open/td_open) around the inline
    content; we track the most recent cell-open type to decide which
    ParagraphStyle to apply.
    """
    from reportlab.platypus import Paragraph

    rows: List[List] = []
    current_row: List = []
    current_cell_is_header = False
    in_row = False
    num_cols = 0
    for t in tokens:
        if t.type == "tr_open":
            in_row = True
            current_row = []
        elif t.type == "tr_close":
            if in_row and current_row:
                rows.append(current_row)
                if len(current_row) > num_cols:
                    num_cols = len(current_row)
            in_row = False
        elif t.type == "th_open":
            current_cell_is_header = True
        elif t.type == "td_open":
            current_cell_is_header = False
        elif t.type == "inline":
            content = _inline_to_rl(t.children or [])
            style = styles["TableHeader"] if current_cell_is_header else styles["TableCell"]
            current_row.append(Paragraph(content, style))
    return rows, num_cols


_LATIN_BOLD = {
    "Helvetica": "Helvetica-Bold",
    "Courier": "Courier-Bold",
    "Times-Roman": "Times-Bold",
}


def _build_styles(theme, cjk: FontResult):
    """Build ReportLab paragraph styles.

    When *cjk.ok* is True, the CJK-capable font family is used for body,
    heading, table, and code text so that Chinese/Japanese/Korean
    characters render correctly on any platform. Latin-only fonts are
    only used as a fallback when no CJK font is available.
    """
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    base = getSampleStyleSheet()
    body_size = theme["body_size"]
    leading = theme["leading"]

    if cjk.ok:
        body_font = cjk.family
        bold_font = cjk.bold_family or cjk.family
        code_font = cjk.family  # CJK comments in code blocks render safely
    else:
        body_font = theme["body_font"]
        bold_font = _LATIN_BOLD.get(body_font, "Helvetica-Bold")
        code_font = "Courier"

    styles = {
        "Body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName=body_font,
            fontSize=body_size,
            leading=leading,
            spaceAfter=6,
            textColor=colors.HexColor("#222222"),
        ),
        "H1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName=bold_font,
            fontSize=22,
            leading=26,
            spaceBefore=10,
            spaceAfter=6,
            textColor=colors.HexColor(theme["h1_color"]),
        ),
        "H2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName=bold_font,
            fontSize=16,
            leading=20,
            spaceBefore=8,
            spaceAfter=4,
            textColor=colors.HexColor(theme["h2_color"]),
        ),
        "H3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontName=bold_font,
            fontSize=13,
            leading=16,
            spaceBefore=6,
            spaceAfter=3,
            textColor=colors.HexColor(theme["h2_color"]),
        ),
        "H4": ParagraphStyle(
            "H4",
            parent=base["Heading4"],
            fontName=bold_font,
            fontSize=11,
            leading=14,
            spaceBefore=4,
            spaceAfter=2,
            textColor=colors.HexColor(theme["h2_color"]),
        ),
        "Code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName=code_font,
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#222222"),
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=base["BodyText"],
            fontName=body_font,
            fontSize=body_size - 1,
            leading=leading - 2,
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            parent=base["BodyText"],
            fontName=bold_font,
            fontSize=body_size - 1,
            leading=leading - 2,
        ),
    }
    return styles


def _make_numbered_canvas(body_font: str):
    """Build a reportlab Canvas subclass that draws ``Page X / Y`` footers
    and finalizes the PDF outline tree on save.

    Why a subclass instead of ``onLaterPages`` callbacks
    ---------------------------------------------------
    reportlab's standard onPage callback only knows the *current* page
    number — it can't draw "Page 3 / 7" because the total isn't known
    until ``doc.build()`` finishes. The canonical workaround is the
    ``NumberedCanvas`` pattern: buffer each page's state in ``showPage``,
    then draw all footers in ``save`` when the total is finally known.

    We also call ``showOutline()`` here so the PDF outline panel pops
    open automatically in readers like Preview / Acrobat.
    """
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            # Stash the current page's drawing state. reportlab internals
            # use the instance ``__dict__`` as the page buffer, so a
            # shallow copy captures everything we need to replay later.
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self._draw_footer(total)
                canvas.Canvas.showPage(self)
            # Auto-open the outline tree when the reader supports it.
            try:
                self.showOutline()
            except Exception:
                pass
            canvas.Canvas.save(self)

        def _draw_footer(self, total_pages: int):
            page_num = self._pageNumber
            page_w, page_h = self._pagesize if hasattr(self, "_pagesize") else A4
            label = f"Page {page_num} / {total_pages}"
            self.saveState()
            try:
                # 9pt is small enough to feel like chrome, not content.
                # Use the body font so CJK filenames / titles wouldn't
                # break if we ever extend the footer to show them.
                self.setFont(body_font, 9)
                self.setFillGray(0.5)
                # 10mm from the bottom edge, right-aligned to the page
                # (not the frame) so the footer lines up regardless of
                # the user's --margin.
                self.drawRightString(page_w - 15 * 2.8346, 10 * 2.8346, label)
            finally:
                self.restoreState()

    return NumberedCanvas


# ---------------------------------------------------------------------------
# Playwright engine — high-fidelity rendering via headless Chromium
# ---------------------------------------------------------------------------

import re as _re

_EMOJI_PATTERN = _re.compile(
    "[\U0001F300-\U0001F9FF"   # Misc Symbols, Emoticons, Supplemental
    "\U00002702-\U000027B0"    # Dingbats
    "\U0000FE00-\U0000FE0F"    # Variation Selectors
    "\U0000200D"               # Zero Width Joiner
    "\U00002600-\U000026FF"    # Misc Symbols
    "\U00002B50-\U00002B55"    # Stars
    "\U000023CF-\U000023FA"    # Symbols
    "\U0001FA00-\U0001FA6F"    # Chess, extended-A
    "\U0001FA70-\U0001FAFF"    # Symbols extended-A
    "]"
)


def _contains_emoji(text: str) -> bool:
    """Return True if *text* contains any emoji character."""
    return bool(_EMOJI_PATTERN.search(text))


def _playwright_available() -> bool:
    """Return True if playwright is importable AND a Chromium binary is present.

    A bare ``import playwright`` succeeds even when Chromium hasn't been
    installed via ``playwright install chromium``.  We probe the actual
    executable path so that ``auto`` mode won't pick Playwright only to
    crash at launch time.  If the private API we rely on changes, we
    optimistically return True and let the try/except in
    ``convert_markdown_to_pdf`` handle any runtime failure.
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return False
    # Check that the Chromium executable actually exists on disk.
    try:
        from playwright._impl._driver import compute_driver_executable  # type: ignore
        driver_exe, browser_env = compute_driver_executable()
        import subprocess
        result = subprocess.run(
            [str(driver_exe), "print-browsers-json"],
            capture_output=True, timeout=5, env={**__import__("os").environ, **browser_env},
        )
        if result.returncode == 0:
            import json
            for entry in json.loads(result.stdout):
                if entry.get("name") == "chromium":
                    exe = Path(entry.get("executablePath", ""))
                    return exe.is_file()
        # Could not parse — assume available; runtime try/except will catch.
        return True
    except Exception:
        # Private API changed or subprocess failed — be optimistic.
        return True


# Compact GitHub-flavored CSS embedded directly into the HTML page.
_GITHUB_CSS = """\
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial,
    sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
  font-size: 14px; line-height: 1.6; color: #24292e;
  max-width: 800px; margin: 0 auto; padding: 20px 32px;
}
h1 { font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: .3em; }
h2 { font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: .3em; }
h3 { font-size: 1.25em; }
h4 { font-size: 1em; }
code {
  background: #f6f8fa; padding: 0.2em 0.4em; border-radius: 3px;
  font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
  font-size: 85%;
}
pre {
  background: #f6f8fa; padding: 16px; border-radius: 6px; overflow-x: auto;
  line-height: 1.45;
}
pre code { background: none; padding: 0; font-size: 100%; }
blockquote {
  border-left: 4px solid #dfe2e5; padding: 0 1em; color: #6a737d; margin: 0 0 16px;
}
table { border-collapse: collapse; width: 100%; margin-bottom: 16px; }
th, td { border: 1px solid #dfe2e5; padding: 6px 13px; }
th { background: #f6f8fa; font-weight: 600; }
tr:nth-child(2n) { background: #f6f8fa; }
img { max-width: 100%; height: auto; }
a { color: #0366d6; text-decoration: none; }
hr { border: none; border-top: 1px solid #eaecef; margin: 24px 0; }
mark, .highlight { background: #fff3cd; padding: 0.1em 0.3em; border-radius: 2px; }
"""


def _convert_via_playwright(
    md_path: Path,
    output_path: Path,
    page_size: str,
    margin: str,
) -> None:
    """Render Markdown to PDF via markdown-it → HTML → Playwright Chromium.

    This path produces pixel-perfect output with full emoji, CSS, and
    typography support — at the cost of requiring Chromium (~300 MB).
    """
    from markdown_it import MarkdownIt
    from playwright.sync_api import sync_playwright

    md_text = md_path.read_text(encoding="utf-8")
    base_dir = md_path.resolve().parent

    md = MarkdownIt(
        "commonmark", {"html": True, "linkify": True, "typographer": True}
    ).enable(["table", "strikethrough"])
    html_body = md.render(md_text)

    # Resolve relative image paths to absolute file:// URIs so Chromium
    # can load them from disk.
    def _resolve_img(match):
        src = match.group(1)
        if src.startswith(("http://", "https://", "data:", "file://")):
            return match.group(0)
        abs_path = (base_dir / src).resolve()
        if abs_path.exists():
            return f'src="file://{abs_path}"'
        return match.group(0)

    html_body = _re.sub(r'src="([^"]*)"', _resolve_img, html_body)

    full_html = (
        "<!DOCTYPE html>\n<html><head>\n"
        '<meta charset="utf-8">\n'
        f"<style>{_GITHUB_CSS}</style>\n"
        f"</head><body>\n{html_body}\n</body></html>"
    )

    # Write temp HTML next to the MD so relative resources resolve.
    tmp_html = base_dir / f".{md_path.stem}.tmp.html"
    tmp_html.write_text(full_html, encoding="utf-8")

    # Page size mapping for Chromium.
    size_map = {
        "a4": {"width": "210mm", "height": "297mm"},
        "a3": {"width": "297mm", "height": "420mm"},
        "letter": {"width": "8.5in", "height": "11in"},
        "legal": {"width": "8.5in", "height": "14in"},
    }
    page_dims = size_map.get(page_size.lower(), size_map["a4"])

    # Parse margin string for Playwright (accepts CSS units directly).
    margin_css = margin.strip()
    if not any(margin_css.endswith(u) for u in ("mm", "in", "px", "cm")):
        margin_css += "mm"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"file://{tmp_html.resolve()}", wait_until="networkidle")
            page.pdf(
                path=str(output_path),
                format=None,
                width=page_dims["width"],
                height=page_dims["height"],
                margin={
                    "top": margin_css,
                    "right": margin_css,
                    "bottom": margin_css,
                    "left": margin_css,
                },
                print_background=True,
            )
            browser.close()
    finally:
        try:
            tmp_html.unlink()
        except OSError:
            pass


def _parse_margin(margin: str):
    from reportlab.lib.units import mm
    m = margin.strip().lower()
    if m.endswith("mm"):
        return float(m[:-2]) * mm
    if m.endswith("in"):
        return float(m[:-2]) * 72
    try:
        return float(m) * mm
    except ValueError:
        return 20 * mm


def convert_markdown_to_pdf(
    md_path: Path,
    output_path: Path,
    theme: str,
    page_size: str,
    margin: str,
    engine: str = "auto",
    title: Optional[str] = None,
    page_numbers: bool = True,
) -> None:
    md_text = md_path.read_text(encoding="utf-8")

    # --- Engine selection ---------------------------------------------------
    # "auto": use Playwright when the source contains emoji (which ReportLab
    # cannot render) and Playwright is available; otherwise fall back to
    # ReportLab. Explicit "playwright" / "reportlab" bypasses auto-detection.
    use_playwright = False
    if engine in ("playwright", "auto"):
        has_emoji = _contains_emoji(md_text)
        pw_ok = _playwright_available()
        if engine == "playwright":
            if pw_ok:
                use_playwright = True
            else:
                print("  [playwright] Playwright not available, falling back to ReportLab. "
                      "Emoji may not render correctly.",
                      file=sys.stderr)
        elif engine == "auto" and has_emoji and pw_ok:
            use_playwright = True
            print("  [auto] Emoji detected → using Playwright engine for full fidelity.",
                  file=sys.stderr)
    # engine == "reportlab" → use_playwright stays False

    if use_playwright:
        try:
            _convert_via_playwright(md_path, output_path, page_size, margin)
            return
        except Exception as exc:
            print(f"  [playwright] Rendering failed ({exc}), falling back to ReportLab.",
                  file=sys.stderr)
            # Fall through to ReportLab path below.

    # --- ReportLab path (original) ------------------------------------------
    _import_deps()

    from markdown_it import MarkdownIt
    from reportlab.platypus import SimpleDocTemplate
    from reportlab.lib.pagesizes import A4, A3, LETTER, LEGAL

    # Register a CJK font whenever the source contains CJK characters.
    cjk_result = FontResult(ok=False)
    if contains_cjk(md_text):
        cjk_result = register_cjk_font()
        if cjk_result.ok:
            print(
                f"CJK font registered: {cjk_result.label} ({cjk_result.path})",
                file=sys.stderr,
            )
        else:
            print(
                f"WARNING: {cjk_result.reason}\n"
                "         CJK characters will render as empty boxes. "
                "Install a CJK font (e.g. Noto Sans CJK) and retry.",
                file=sys.stderr,
            )

    theme_conf = THEMES.get(theme, THEMES["default"])
    styles = _build_styles(theme_conf, cjk_result)

    # Make inline <code> / fenced blocks use the same font family the
    # "Code" style points at (avoids boxing CJK comments in Courier).
    global _CODE_FACE
    _CODE_FACE = styles["Code"].fontName

    page_map = {"a4": A4, "a3": A3, "letter": LETTER, "legal": LEGAL}
    pagesize = page_map.get(page_size.lower(), A4)
    m_val = _parse_margin(margin)
    max_width = pagesize[0] - 2 * m_val
    # Slightly under the usable frame height — reportlab's frame reserves a
    # few points for internal padding, and a trailing Spacer+Paragraph needs
    # room too. 95% empirically avoids "flowable too large" on tall images.
    max_height = (pagesize[1] - 2 * m_val) * 0.95

    ctx = {
        "base_dir": md_path.resolve().parent,
        "max_width": max_width,
        "max_height": max_height,
    }

    md = MarkdownIt(
        "commonmark", {"html": False, "linkify": True, "typographer": True}
    ).enable(["table", "strikethrough"])
    tokens = md.parse(md_text)
    flow = _tokens_to_flowables(tokens, styles, theme_conf, ctx)

    # Atomic write: render to a sibling temp file first, rename on success.
    # This prevents half-written PDFs from being mistaken for a completed
    # output if reportlab raises midway through doc.build().
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(
        prefix=output_path.stem + ".", suffix=".pdf.tmp", dir=str(output_path.parent)
    )
    import os as _os
    _os.close(tmp_fd)
    tmp_path = Path(tmp_name)
    try:
        doc = SimpleDocTemplate(
            str(tmp_path),
            pagesize=pagesize,
            leftMargin=m_val,
            rightMargin=m_val,
            topMargin=m_val,
            bottomMargin=m_val,
            title=title or md_path.stem,
        )
        # Body font = the style that will be used for footer chrome.
        # Derived from the resolved CJK family when present, otherwise
        # the theme's Latin body font. Must be something already
        # registered by _build_styles above.
        footer_font = (
            cjk_result.family if cjk_result.ok else theme_conf["body_font"]
        )
        if page_numbers:
            numbered_canvas = _make_numbered_canvas(footer_font)
            doc.build(flow, canvasmaker=numbered_canvas)
        else:
            doc.build(flow)
        tmp_path.replace(output_path)
    except Exception:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Markdown to PDF (ReportLab or Playwright engine).",
        epilog=(
            "Examples:\n"
            "  python scripts/markdown_to_pdf.py report.md --output report.pdf\n"
            "  python scripts/markdown_to_pdf.py report.md --output report.pdf --engine playwright\n"
            "  python scripts/markdown_to_pdf.py --file report.md --output report.pdf \\\n"
            "      --theme professional --page-size a4 --margin 20mm\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # Accept the input file either as a positional argument OR via --file,
    # to match html_to_pdf.py's style. Agents routinely confuse the two;
    # supporting both eliminates a whole class of usage failures.
    parser.add_argument(
        "md_file",
        nargs="?",
        help="Input Markdown file (positional form)",
    )
    parser.add_argument(
        "--file",
        dest="md_file_flag",
        help="Input Markdown file (flag form, alias of positional)",
    )
    parser.add_argument("--output", "-o", required=True, help="Output PDF path")
    parser.add_argument("--title", help="PDF metadata title (default: input filename)")
    parser.add_argument(
        "--no-page-numbers",
        action="store_true",
        help="Do not draw page-number footers",
    )
    parser.add_argument(
        "--theme",
        choices=list(THEMES.keys()),
        default="default",
        help="Visual theme (default: default)",
    )
    parser.add_argument(
        "--toc",
        action="store_true",
        help="(reserved) Include table of contents — no-op in reportlab backend",
    )
    parser.add_argument(
        "--page-size",
        default="a4",
        choices=["a4", "letter", "a3", "legal"],
        help="Page size (default: a4)",
    )
    parser.add_argument("--margin", default="20mm", help="Page margin (default: 20mm)")
    parser.add_argument(
        "--engine",
        choices=["auto", "reportlab", "playwright"],
        default="auto",
        help="Rendering engine (default: auto). "
             "'auto' uses Playwright when emoji is detected and Playwright is available, "
             "otherwise falls back to ReportLab. "
             "'playwright' forces Chromium rendering (best for emoji, CSS, complex styling). "
             "'reportlab' forces pure-Python rendering (fastest, zero system deps).",
    )
    args = parser.parse_args()

    # Resolve the input file from either positional or --file.
    md_file = args.md_file or args.md_file_flag
    if not md_file:
        parser.error(
            "input Markdown file is required — pass it as a positional "
            "argument (e.g. `markdown_to_pdf.py report.md --output x.pdf`) "
            "or via `--file report.md`"
        )
    if args.md_file and args.md_file_flag and args.md_file != args.md_file_flag:
        parser.error(
            "conflicting inputs: positional and --file point to different files"
        )
    md_path = Path(md_file)
    if not md_path.exists():
        print(f"Error: file not found: {md_path}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Converting {md_path.name} → PDF (theme: {args.theme}, engine: {args.engine})…")
    try:
        convert_markdown_to_pdf(
            md_path, output_path, args.theme, args.page_size, args.margin,
            engine=args.engine,
            title=args.title,
            page_numbers=not args.no_page_numbers,
        )
    except MissingDependency as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"PDF created → {output_path}")


if __name__ == "__main__":
    main()
