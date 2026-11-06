import os
import sys
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from pdf_merge import merge
from tests._helpers import make_text_pdf, temp_pdf

def test_merge_two_pdfs(tmp_path):
    pdf1 = temp_pdf(str(tmp_path), make_text_pdf(2, "A"), "a.pdf")
    pdf2 = temp_pdf(str(tmp_path), make_text_pdf(3, "B"), "b.pdf")
    out = str(tmp_path / "merged.pdf")
    result = merge([pdf1, pdf2], out)
    assert result["status"] == "ok"
    assert result["total_pages"] == 5
    assert result["input_count"] == 2
    assert os.path.exists(out)


def test_merge_missing_file(tmp_path):
    out = str(tmp_path / "out.pdf")
    result = merge(["nonexistent.pdf"], out)
    assert result["status"] == "error"
