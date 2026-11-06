import io
import os
import sys
import tempfile
import pytest

# Dependencies are installed by 小艺 Work before the skill runs.
_root = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_root, ".."))
sys.path.insert(0, os.path.join(_root, "..", "scripts"))
from render_body import _image_from_bytes, _normalize_math_expr, _render_math_png, build


def test_normalize_math_expr_supports_common_aliases_and_wrappers():
    assert _normalize_math_expr(
        r"$$x \ge 1, y \le 2, z \ne 0, p \iff q, a \land b \lor c$$"
    ) == (
        r"x \geq 1, y \leq 2, z \neq 0, p \Leftrightarrow q, a \wedge b \vee c"
    )


def test_normalize_math_expr_rejects_python_escape_control_characters():
    broken = "x = " + "\x0c" + "rac{a}{b}"
    with pytest.raises(ValueError, match="raw Python string"):
        _normalize_math_expr(broken)


def test_render_math_png_valid_latex_returns_png_bytes():
    """A simple valid LaTeX expression must render to non-empty PNG bytes."""
    png = _render_math_png(r"E = mc^2")
    assert png is not None
    assert len(png) > 0


def test_render_math_png_strips_wrapped_dollar_signs():
    """If the input already contains $...$, code must not double-wrap into $$...$$."""
    png = _render_math_png(r"$E = mc^2$")
    assert png is not None
    assert len(png) > 0
    # Also verify mixed spacing
    png2 = _render_math_png(r"  $\sum_{i=1}^{n} x_i$  ")
    assert png2 is not None


def test_render_math_png_cjk_does_not_silently_fail():
    """Math expressions containing CJK must not silently return None."""
    png = _render_math_png(r"x = \text{某个值}")
    # After fix: either renders successfully or raises/logs an error.
    # We accept non-None PNG as success.
    assert png is not None


def test_render_math_png_invalid_latex_is_not_silent(caplog):
    """An invalid/unparseable LaTeX expression must produce a visible log."""
    import logging
    with caplog.at_level(logging.WARNING):
        png = _render_math_png(r"\invalidcommand{syntax")
    # After fix: either we get a warning log or the function raises.
    # Current buggy behavior: returns None with zero logging.
    assert png is None or "math" in caplog.text.lower() or "render" in caplog.text.lower()
    assert len(caplog.text) > 0, "Math rendering failures must not be silent"


def test_render_math_png_long_expr_returns_reasonable_image():
    """A long LaTeX expression must still render without excessive compression."""
    long_expr = (
        r"\sum_{i=1}^{n} \left( \frac{a_i + b_i}{c_i} \right) "
        r"= \int_{0}^{1} \frac{x^2 + 1}{\sqrt{x^4 + 1}} \, dx"
    )
    png = _render_math_png(long_expr)
    assert png is not None
    # Minimal sanity check: PNG header magic bytes
    assert png[:4] == b"\x89PNG"

    # A 180-DPI formula is converted to physical PDF points before fitting.
    # It should not be interpreted as hundreds of points merely due to pixels.
    image = _image_from_bytes(png, usable_w=460, max_frac=1.0, source_dpi=180)
    assert image.drawWidth <= 460
    assert 20 < image.drawHeight < 60


def test_render_math_png_ge_alias_renders():
    png = _render_math_png(r"x \ge 0")
    assert png is not None
    assert png[:4] == b"\x89PNG"


def test_render_math_png_cjk_without_text_command_still_renders():
    """Math expressions with raw CJK (not wrapped in \\text{}) must not silently fail.

    This mirrors the real-world path from Markdown: $$x = 某个值$$
    where reformat_parse.py stores the literal text without adding \\text{}.
    """
    png = _render_math_png(r"x = 某个值")
    assert png is not None
    assert png[:4] == b"\x89PNG"


def test_build_math_block_generates_pdf_with_nonzero_size():
    """A content block of type 'math' must produce a PDF page."""
    tokens = {
        "accent": "#3366CC",
        "accent_lt": "#E8F0FE",
        "muted": "#888888",
        "dark": "#222222",
        "body_text": "#333333",
        "font_display_rl": "Times-Bold",
        "font_body_rl": "Helvetica",
        "font_body_b_rl": "Helvetica-Bold",
        "size_h1": 24,
        "size_h2": 18,
        "size_h3": 14,
        "size_body": 10.5,
        "size_caption": 9,
        "size_meta": 8.5,
        "line_gap": 16,
        "para_gap": 10,
        "section_gap": 22,
        "margin_left": 72,
        "margin_right": 72,
        "margin_top": 72,
        "margin_bottom": 72,
        "title": "Math Test",
        "date": "2026-04-14",
        "author": "Tester",
    }
    content = [{"type": "math", "text": r"\int_0^\infty e^{-x^2}\,dx = \frac{\sqrt{\pi}}{2}"}]
    with tempfile.TemporaryDirectory() as tmp:
        out_path = os.path.join(tmp, "math.pdf")
        result = build(tokens, content, out_path)
        assert result["status"] == "ok"
        assert os.path.getsize(out_path) > 0


def test_build_invalid_math_block_fails_instead_of_emitting_source_text():
    tokens = {
        "accent": "#3366CC",
        "accent_lt": "#E8F0FE",
        "muted": "#888888",
        "dark": "#222222",
        "body_text": "#333333",
        "font_display_rl": "Times-Bold",
        "font_body_rl": "Helvetica",
        "font_body_b_rl": "Helvetica-Bold",
        "size_h1": 24,
        "size_h2": 18,
        "size_h3": 14,
        "size_body": 10.5,
        "size_caption": 9,
        "size_meta": 8.5,
        "line_gap": 16,
        "para_gap": 10,
        "section_gap": 22,
        "margin_left": 72,
        "margin_right": 72,
        "margin_top": 72,
        "margin_bottom": 72,
        "title": "Invalid Math Test",
        "date": "2026-09-16",
        "author": "Tester",
    }
    broken_formula = "x = " + "\x0c" + "rac{a}{b}"
    with tempfile.TemporaryDirectory() as tmp:
        out_path = os.path.join(tmp, "invalid-math.pdf")
        with pytest.raises(RuntimeError, match="Math rendering failed"):
            build(tokens, [{"type": "math", "text": broken_formula}], out_path)
