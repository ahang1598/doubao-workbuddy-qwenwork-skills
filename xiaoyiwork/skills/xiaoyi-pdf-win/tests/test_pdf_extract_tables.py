import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from pdf_extract_tables import extract_tables
from tests._helpers import make_table_pdf, make_text_pdf, temp_pdf


def test_extract_tables_xlsx(tmp_path):
    pdf = temp_pdf(str(tmp_path), make_table_pdf(), "table.pdf")
    out = str(tmp_path / "tables.xlsx")
    result = extract_tables(pdf, out, fmt="xlsx")
    assert result["status"] == "ok"
    assert os.path.exists(out)
    import pandas as pd

    df = pd.read_excel(out)
    assert list(df.columns) == ["Name", "Age", "City"]
    assert list(df.iloc[0].astype(str)) == ["Alice", "30", "Beijing"]


def test_extract_tables_csv(tmp_path):
    pdf = temp_pdf(str(tmp_path), make_table_pdf(), "table.pdf")
    out = str(tmp_path / "tables.csv")
    result = extract_tables(pdf, out, fmt="csv")
    assert result["status"] == "ok"
    assert os.path.exists(out)
    import pandas as pd

    df = pd.read_csv(out)
    assert list(df.columns) == ["Name", "Age", "City"]
    assert list(df.iloc[0].astype(str)) == ["Alice", "30", "Beijing"]


def test_extract_tables_missing_file(tmp_path):
    out = str(tmp_path / "tables.xlsx")
    result = extract_tables(str(tmp_path / "nonexistent.pdf"), out, fmt="xlsx")
    assert result["status"] == "error"


def test_extract_tables_no_tables(tmp_path):
    pdf = temp_pdf(str(tmp_path), make_text_pdf(1, "Hello"), "notext.pdf")
    out = str(tmp_path / "tables.xlsx")
    result = extract_tables(pdf, out, fmt="xlsx")
    assert result["status"] == "ok"
    assert result["tables_found"] == 0
