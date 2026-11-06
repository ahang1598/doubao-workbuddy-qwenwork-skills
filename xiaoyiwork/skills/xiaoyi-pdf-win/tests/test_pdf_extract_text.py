import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from pdf_extract_text import extract_text
from tests._helpers import make_text_pdf, temp_pdf


def test_extract_text(tmp_path):
    pdf = temp_pdf(str(tmp_path), make_text_pdf(2, "Line"), "doc.pdf")
    out = str(tmp_path / "text.txt")
    result = extract_text(pdf, out)
    assert result["status"] == "ok"
    assert result["pages"] == 2
    with open(out, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Line 1" in content
    assert "Line 2" in content


def test_extract_text_missing_file(tmp_path):
    result = extract_text("nonexistent.pdf", str(tmp_path / "out.txt"))
    assert result["status"] == "error"
