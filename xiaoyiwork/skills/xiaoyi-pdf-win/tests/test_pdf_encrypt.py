import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from pdf_encrypt import encrypt
from tests._helpers import make_text_pdf, temp_pdf
from pypdf import PdfReader


def test_encrypt_pdf(tmp_path):
    pdf = temp_pdf(str(tmp_path), make_text_pdf(1), "doc.pdf")
    out = str(tmp_path / "encrypted.pdf")
    result = encrypt(pdf, out, "secret")
    assert result["status"] == "ok"
    assert os.path.exists(out)
    reader = PdfReader(out)
    assert reader.is_encrypted


def test_encrypt_missing_file(tmp_path):
    result = encrypt("nonexistent.pdf", str(tmp_path / "out.pdf"), "secret")
    assert result["status"] == "error"


def test_encrypt_can_be_decrypted(tmp_path):
    pdf = temp_pdf(str(tmp_path), make_text_pdf(3), "doc.pdf")
    out = str(tmp_path / "encrypted.pdf")
    result = encrypt(pdf, out, "secret")
    assert result["status"] == "ok"
    reader = PdfReader(out)
    assert reader.is_encrypted
    reader.decrypt("secret")
    assert len(reader.pages) == 3
