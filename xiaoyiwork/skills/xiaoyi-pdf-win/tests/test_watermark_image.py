import os
import tempfile
from PIL import Image
from pypdf import PdfReader
from scripts.watermark_image import create_image_watermark, _prepare_watermark_image, SUPPORTED_IMAGE_EXTS


def test_create_image_watermark_outputs_pdf():
    with tempfile.TemporaryDirectory() as tmp:
        img_path = os.path.join(tmp, "logo.png")
        out_path = os.path.join(tmp, "watermark.pdf")
        img = Image.new("RGB", (200, 100), color="red")
        img.save(img_path)
        create_image_watermark(out_path, img_path)
        reader = PdfReader(out_path)
        assert len(reader.pages) == 1


def test_unsupported_extension():
    with tempfile.TemporaryDirectory() as tmp:
        gif_path = os.path.join(tmp, "logo.gif")
        out_path = os.path.join(tmp, "watermark.pdf")
        with open(gif_path, "w") as f:
            f.write("")
        try:
            create_image_watermark(out_path, gif_path)
            assert False, "Expected ValueError for unsupported extension"
        except ValueError as e:
            assert "Unsupported image format '.gif'" in str(e)


def test_missing_file():
    with tempfile.TemporaryDirectory() as tmp:
        missing_path = os.path.join(tmp, "nonexistent.png")
        out_path = os.path.join(tmp, "watermark.pdf")
        try:
            create_image_watermark(out_path, missing_path)
            assert False, "Expected FileNotFoundError for missing file"
        except FileNotFoundError as e:
            assert "Image not found" in str(e)


def test_output_pdf_is_a4():
    with tempfile.TemporaryDirectory() as tmp:
        img_path = os.path.join(tmp, "logo.png")
        out_path = os.path.join(tmp, "watermark.pdf")
        img = Image.new("RGB", (200, 100), color="blue")
        img.save(img_path)
        create_image_watermark(out_path, img_path)
        reader = PdfReader(out_path)
        page = reader.pages[0]
        mw, mh = page.mediabox.width, page.mediabox.height
        assert abs(float(mw) - 595.27) < 0.01
        assert abs(float(mh) - 841.89) < 0.01


def test_jpg_input_converted_to_rgba_with_opacity():
    with tempfile.TemporaryDirectory() as tmp:
        img_path = os.path.join(tmp, "logo.jpg")
        out_path = os.path.join(tmp, "watermark.pdf")
        img = Image.new("RGB", (400, 200), color="green")
        img.save(img_path, format="JPEG")
        create_image_watermark(out_path, img_path, opacity=0.5, scale=0.2)
        reader = PdfReader(out_path)
        assert len(reader.pages) == 1


def test_svg_input_requires_cairosvg():
    with tempfile.TemporaryDirectory() as tmp:
        svg_path = os.path.join(tmp, "logo.svg")
        out_path = os.path.join(tmp, "watermark.pdf")
        with open(svg_path, "w") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="red"/></svg>')
        try:
            import cairosvg  # noqa: F401
        except ImportError:
            try:
                create_image_watermark(out_path, svg_path)
                assert False, "Expected RuntimeError when cairosvg is missing"
            except RuntimeError as e:
                assert "SVG support requires cairosvg" in str(e)
        else:
            # cairosvg is available; should succeed
            create_image_watermark(out_path, svg_path, opacity=0.3, scale=0.2)
            reader = PdfReader(out_path)
            assert len(reader.pages) == 1


def test_opacity_clamping_warns():
    with tempfile.TemporaryDirectory() as tmp:
        img_path = os.path.join(tmp, "logo.png")
        out_path = os.path.join(tmp, "watermark.pdf")
        img = Image.new("RGB", (100, 50), color="blue")
        img.save(img_path)
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            create_image_watermark(out_path, img_path, opacity=1.5, scale=0.1)
            assert any("clamped to [0, 1]" in str(warning.message) for warning in w)


def test_scale_clamping_warns():
    with tempfile.TemporaryDirectory() as tmp:
        img_path = os.path.join(tmp, "logo.png")
        out_path = os.path.join(tmp, "watermark.pdf")
        img = Image.new("RGB", (100, 50), color="blue")
        img.save(img_path)
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            create_image_watermark(out_path, img_path, opacity=0.3, scale=2.0)
            assert any("clamped to (0, 1]" in str(warning.message) for warning in w)
