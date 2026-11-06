import os
import tempfile

import pytest
from pypdf import PdfReader
from reportlab.pdfgen import canvas as cvs

from scripts.watermark_cli import build_default_output, main, parse_args


def test_build_default_output():
    assert build_default_output("/path/to/doc.pdf") == "/path/to/doc_watermarked.pdf"


def test_build_default_output_no_dir():
    assert build_default_output("doc.pdf") == "doc_watermarked.pdf"


def test_cli_text_watermark_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        input_pdf = os.path.join(tmp, "input.pdf")
        c = cvs.Canvas(input_pdf, pagesize=(612, 792))
        c.drawString(100, 700, "Page 1")
        c.showPage()
        c.drawString(100, 700, "Page 2")
        c.save()

        output_pdf = os.path.join(tmp, "output.pdf")
        result = main([
            "--input", input_pdf,
            "--output", output_pdf,
            "--type", "text",
            "--text", "TEST",
            "--font-size", "24",
            "--rotate", "0",
            "--opacity", "1.0",
        ])
        assert result == 0
        reader = PdfReader(output_pdf)
        assert len(reader.pages) == 2
        assert os.path.getsize(output_pdf) > os.path.getsize(input_pdf)


def test_cli_missing_input_returns_nonzero():
    result = main(["--input", "missing.pdf", "--type", "text", "--text", "X"])
    assert result == 1


def test_cli_missing_text_returns_nonzero():
    with tempfile.TemporaryDirectory() as tmp:
        input_pdf = os.path.join(tmp, "input.pdf")
        c = cvs.Canvas(input_pdf, pagesize=(612, 792))
        c.drawString(100, 700, "Page 1")
        c.save()
        result = main(["--input", input_pdf, "--type", "text"])
        assert result == 1


def test_cli_default_output():
    with tempfile.TemporaryDirectory() as tmp:
        input_pdf = os.path.join(tmp, "input.pdf")
        c = cvs.Canvas(input_pdf, pagesize=(612, 792))
        c.drawString(100, 700, "Page 1")
        c.save()

        result = main([
            "--input", input_pdf,
            "--type", "text",
            "--text", "WATERMARK",
        ])
        assert result == 0
        expected_output = os.path.join(tmp, "input_watermarked.pdf")
        assert os.path.isfile(expected_output)


def test_cli_text_watermark_page_range():
    with tempfile.TemporaryDirectory() as tmp:
        input_pdf = os.path.join(tmp, "input.pdf")
        from reportlab.pdfgen import canvas as cvs
        c = cvs.Canvas(input_pdf, pagesize=(612, 792))
        for i in range(3):
            c.drawString(100, 700, f"Page {i+1}")
            c.showPage()
        c.save()

        output_pdf = os.path.join(tmp, "output.pdf")
        main([
            "--input", input_pdf,
            "--output", output_pdf,
            "--type", "text",
            "--text", "ONLY_PAGE_2",
            "--pages", "2",
            "--font-size", "24",
            "--rotate", "0",
            "--opacity", "1.0",
        ])
        reader = PdfReader(output_pdf)
        assert len(reader.pages) == 3


def test_cli_image_watermark_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        input_pdf = os.path.join(tmp, "input.pdf")
        from reportlab.pdfgen import canvas as cvs
        from PIL import Image
        c = cvs.Canvas(input_pdf, pagesize=(612, 792))
        c.drawString(100, 700, "Page 1")
        c.showPage()
        c.save()

        img_path = os.path.join(tmp, "logo.png")
        img = Image.new("RGB", (100, 50), color="blue")
        img.save(img_path)

        output_pdf = os.path.join(tmp, "output.pdf")
        main([
            "--input", input_pdf,
            "--output", output_pdf,
            "--type", "image",
            "--image", img_path,
        ])
        reader = PdfReader(output_pdf)
        assert len(reader.pages) == 1


def test_cli_image_watermark_with_opacity_and_scale():
    with tempfile.TemporaryDirectory() as tmp:
        input_pdf = os.path.join(tmp, "input.pdf")
        from reportlab.pdfgen import canvas as cvs
        from PIL import Image
        c = cvs.Canvas(input_pdf, pagesize=(612, 792))
        c.drawString(100, 700, "Page 1")
        c.showPage()
        c.save()

        img_path = os.path.join(tmp, "logo.png")
        img = Image.new("RGB", (200, 100), color="blue")
        img.save(img_path)

        output_pdf = os.path.join(tmp, "output.pdf")
        result = main([
            "--input", input_pdf,
            "--output", output_pdf,
            "--type", "image",
            "--image", img_path,
            "--opacity", "0.5",
            "--scale", "0.2",
        ])
        assert result == 0
        reader = PdfReader(output_pdf)
        assert len(reader.pages) == 1
