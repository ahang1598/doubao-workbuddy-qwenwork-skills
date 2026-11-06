import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from pdf_decrypt import decrypt
from tests._helpers import make_text_pdf, temp_pdf
from pypdf import PdfReader, PdfWriter


def _make_encrypted(pdf_path: str, password: str) -> str:
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    enc_path = pdf_path.replace(".pdf", "_enc.pdf")
    with open(enc_path, "wb") as f:
        writer.write(f)
    return enc_path


def test_decrypt_pdf(tmp_path):
    pdf = temp_pdf(str(tmp_path), make_text_pdf(2), "doc.pdf")
    enc = _make_encrypted(pdf, "secret")
    out = str(tmp_path / "decrypted.pdf")
    result = decrypt(enc, out, "secret")
    assert result["status"] == "ok"
    reader = PdfReader(out)
    assert not reader.is_encrypted
    assert len(reader.pages) == 2


def test_decrypt_wrong_password(tmp_path):
    pdf = temp_pdf(str(tmp_path), make_text_pdf(1), "doc.pdf")
    enc = _make_encrypted(pdf, "secret")
    out = str(tmp_path / "decrypted.pdf")
    result = decrypt(enc, out, "wrong")
    assert result["status"] == "error"


def test_decrypt_missing_file(tmp_path):
    result = decrypt("nonexistent.pdf", str(tmp_path / "out.pdf"), "secret")
    assert result["status"] == "error"
