import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from pypdf import PdfReader
from pdf_split import split
from tests._helpers import make_text_pdf, temp_pdf


def test_split_by_page(tmp_path):
    pdf = temp_pdf(str(tmp_path), make_text_pdf(3), "doc.pdf")
    outdir = str(tmp_path / "out")
    result = split(pdf, outdir)
    assert result["status"] == "ok"
    assert result["files_created"] == 3
    assert os.path.isdir(outdir)
    files = [f for f in os.listdir(outdir) if f.endswith(".pdf")]
    assert len(files) == 3
    assert "doc_page1.pdf" in files
    assert "doc_page2.pdf" in files
    assert "doc_page3.pdf" in files


def test_split_by_ranges(tmp_path):
    pdf = temp_pdf(str(tmp_path), make_text_pdf(5), "doc.pdf")
    outdir = str(tmp_path / "out2")
    result = split(pdf, outdir, ranges_str="1-2,4")
    assert result["status"] == "ok"
    assert result["files_created"] == 2
    files = sorted([f for f in os.listdir(outdir) if f.endswith(".pdf")])
    assert len(files) == 2
    assert "doc_part1_pages1-2.pdf" in files
    assert "doc_part2_pages4-4.pdf" in files


def test_split_range_invalid_input(tmp_path):
    pdf = temp_pdf(str(tmp_path), make_text_pdf(3), "doc.pdf")
    outdir = str(tmp_path / "out3")
    result = split(pdf, outdir, ranges_str="abc")
    assert result["status"] == "error"


def test_split_pages_content(tmp_path):
    pdf = temp_pdf(str(tmp_path), make_text_pdf(3), "doc.pdf")
    outdir = str(tmp_path / "out4")
    result = split(pdf, outdir, ranges_str="2")
    assert result["status"] == "ok"
    assert result["files_created"] == 1
    files = [f for f in os.listdir(outdir) if f.endswith(".pdf")]
    assert len(files) == 1
    reader = PdfReader(os.path.join(outdir, files[0]))
    assert len(reader.pages) == 1


def test_split_clamped_range(tmp_path):
    pdf = temp_pdf(str(tmp_path), make_text_pdf(3), "doc.pdf")
    outdir = str(tmp_path / "out5")
    result = split(pdf, outdir, ranges_str="2-5")
    assert result["status"] == "ok"
    assert result["files_created"] == 1
    files = [f for f in os.listdir(outdir) if f.endswith(".pdf")]
    assert files == ["doc_part1_pages2-3.pdf"]
    assert result["warnings"]
    assert any("clamped" in w.lower() for w in result["warnings"])


def test_split_skipped_range(tmp_path):
    pdf = temp_pdf(str(tmp_path), make_text_pdf(2), "doc.pdf")
    outdir = str(tmp_path / "out6")
    result = split(pdf, outdir, ranges_str="5")
    assert result["status"] == "ok"
    assert result["files_created"] == 0
    assert result["warnings"]
    assert any("skipped" in w.lower() for w in result["warnings"])
