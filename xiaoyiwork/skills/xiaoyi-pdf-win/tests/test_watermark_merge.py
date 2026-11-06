import os
import pytest
from pypdf import PdfWriter
from scripts.watermark_merge import parse_page_ranges, merge_watermark


def test_parse_single_page():
    assert parse_page_ranges("3", 10) == [2]


def test_parse_comma_and_range():
    assert parse_page_ranges("1,3,5-7", 10) == [0, 2, 4, 5, 6]


def test_parse_out_of_bounds_ignored():
    assert parse_page_ranges("8-12", 10) == [7, 8, 9]


def test_parse_all_pages_when_none():
    assert parse_page_ranges(None, 3) == [0, 1, 2]


def test_parse_empty_string_returns_empty():
    assert parse_page_ranges("", 5) == []


def test_parse_invalid_token_single():
    with pytest.raises(ValueError, match="Invalid page range: foo"):
        parse_page_ranges("foo", 5)


def test_parse_invalid_range():
    with pytest.raises(ValueError, match="Invalid page range: 1-bar"):
        parse_page_ranges("1-bar", 5)


@pytest.fixture
def sample_pdfs(tmp_path):
    input_pdf = tmp_path / "input.pdf"
    watermark_pdf = tmp_path / "watermark.pdf"
    output_pdf = tmp_path / "output.pdf"

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    with open(input_pdf, "wb") as f:
        writer.write(f)

    w_writer = PdfWriter()
    w_writer.add_blank_page(width=612, height=792)
    with open(watermark_pdf, "wb") as f:
        w_writer.write(f)

    empty_watermark_pdf = tmp_path / "empty_watermark.pdf"
    empty_writer = PdfWriter()
    with open(empty_watermark_pdf, "wb") as f:
        empty_writer.write(f)

    return str(input_pdf), str(watermark_pdf), str(output_pdf), str(empty_watermark_pdf)


def test_merge_watermark_success(sample_pdfs):
    input_pdf, watermark_pdf, output_pdf, _ = sample_pdfs
    merge_watermark(input_pdf, watermark_pdf, output_pdf)
    assert os.path.exists(output_pdf)


def test_merge_watermark_missing_input(sample_pdfs):
    _, watermark_pdf, output_pdf, _ = sample_pdfs
    with pytest.raises(FileNotFoundError, match="Input PDF not found"):
        merge_watermark("nonexistent.pdf", watermark_pdf, output_pdf)


def test_merge_watermark_missing_watermark(sample_pdfs):
    input_pdf, _, output_pdf, _ = sample_pdfs
    with pytest.raises(FileNotFoundError, match="Watermark PDF not found"):
        merge_watermark(input_pdf, "nonexistent.pdf", output_pdf)


def test_merge_watermark_empty_watermark(sample_pdfs):
    input_pdf, _, output_pdf, empty_watermark_pdf = sample_pdfs
    with pytest.raises(ValueError, match="Watermark PDF has no pages"):
        merge_watermark(input_pdf, empty_watermark_pdf, output_pdf)
