import os
import tempfile
from unittest.mock import patch
import pytest
from pypdf import PdfReader
from scripts.watermark_text import (
    has_cjk,
    resolve_font_path,
    hex_to_rgb,
    create_text_watermark,
)


def test_has_cjk_true():
    assert has_cjk("机密文件") is True


def test_has_cjk_false():
    assert has_cjk("Secret") is False


def test_resolve_font_path_explicit_existing():
    with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as f:
        tmp_path = f.name
    try:
        assert resolve_font_path(tmp_path) == tmp_path
    finally:
        os.unlink(tmp_path)


def test_resolve_font_path_explicit_missing():
    with pytest.raises(FileNotFoundError, match="Font file not found"):
        resolve_font_path("/nonexistent/for_test_only.ttf")


def test_resolve_font_path_english_fallback():
    assert resolve_font_path(None, "Hello") is None


def test_resolve_font_path_cjk_missing():
    with patch("scripts.watermark_text.FONT_CANDIDATES", {}):
        with pytest.raises(RuntimeError, match="CJK font required"):
            resolve_font_path(None, "中文")


@pytest.mark.parametrize(
    "hex_str,expected",
    [
        ("#FF0000", (1.0, 0.0, 0.0)),
        ("FF0000", (1.0, 0.0, 0.0)),
        ("#F00", (1.0, 0.0, 0.0)),
        ("F00", (1.0, 0.0, 0.0)),
        ("#00FF00", (0.0, 1.0, 0.0)),
        ("#0000FF", (0.0, 0.0, 1.0)),
        ("#888888", (0.5333333333333333, 0.5333333333333333, 0.5333333333333333)),
    ],
)
def test_hex_to_rgb_valid(hex_str, expected):
    assert hex_to_rgb(hex_str) == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize(
    "hex_str",
    [
        "#GG0000",
        "#FF00",
        "#FF00000",
        "not_a_color",
        "",
        "#",
        "#12G",
    ],
)
def test_hex_to_rgb_invalid(hex_str):
    with pytest.raises(ValueError, match="Invalid color hex"):
        hex_to_rgb(hex_str)


def test_create_text_watermark_outputs_pdf():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "watermark.pdf")
        create_text_watermark(
            path, "SECRET", font_size=36, rotate=30, opacity=0.5, color="#FF0000"
        )
        reader = PdfReader(path)
        assert len(reader.pages) == 1


def _find_real_font():
    # 本技能只跑在 Windows：只探测 Windows 自带字体，别再列我们不发布的 Linux/macOS 字体
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\times.ttf",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def test_create_text_watermark_cjk():
    real_font = _find_real_font()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "watermark_cjk.pdf")
        with patch("scripts.watermark_text.FONT_CANDIDATES", {}):
            with pytest.raises(RuntimeError, match="CJK font required"):
                create_text_watermark(path, "机密文件")
        if real_font is None:
            pytest.skip("No real system font available for explicit font test")
        create_text_watermark(path, "机密文件", font_path=real_font)
        reader = PdfReader(path)
        assert len(reader.pages) == 1


def test_multiple_calls_different_fonts():
    real_font = _find_real_font()
    with tempfile.TemporaryDirectory() as tmp:
        path1 = os.path.join(tmp, "wm1.pdf")
        path2 = os.path.join(tmp, "wm2.pdf")
        if real_font is None:
            pytest.skip("No real system font available for multiple calls test")
        create_text_watermark(path1, "Hello", font_path=real_font)
        create_text_watermark(path2, "World")
        assert len(PdfReader(path1).pages) == 1
        assert len(PdfReader(path2).pages) == 1
