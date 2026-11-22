#!/usr/bin/env python3
"""Regression test for augment_authors._pdf_text.

Guards against two failure modes that have bitten this pipeline before:
  1. pypdf silently returns "" (e.g. "EOF marker not found") and the PyMuPDF
     fallback was removed/regressed -> affiliations get dropped silently.
  2. _pdf_text returns "" under any normal condition on a valid cached PDF.

Run (from anywhere, needs pypdf + PyMuPDF in the venv):
  python scripts/test_augment_authors.py

Network-free: builds a synthetic PDF with PyMuPDF and forces pypdf to fail.
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    "augment_authors", os.path.join(HERE, "augment_authors.py"))
aug = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(aug)

import fitz
from unittest import mock


MARKER = "RegressionTestAffiliationProbe"
FAKE_PID = "regtest_9999"


def _make_pdf(path):
    """Create a >20KB single-page PDF containing MARKER, via PyMuPDF.

    Lines are drawn individually (insert_text handles one line per call) and
    the PDF is saved WITHOUT compression so the raw content stream stays
    above the 20KB cache gate in _pdf_text (otherwise it would try _curl and
    fail offline)."""
    doc = fitz.open()
    pg = doc.new_page()
    for i in range(400):
        pg.insert_text((50, 50 + i * 12), MARKER * 3, fontsize=10)
    doc.save(path, deflate=False, garbage=0)
    doc.close()


def main():
    cache = aug.PDFCACHE
    os.makedirs(cache, exist_ok=True)
    pdf_path = os.path.join(cache, FAKE_PID + ".pdf")
    _make_pdf(pdf_path)
    try:
        size = os.path.getsize(pdf_path)
        assert size > 20000, f"synthetic PDF too small ({size} B); cache gate skipped"

        # ---- Core regression: pypdf forced to fail MUST fall back to fitz ----
        with mock.patch("pypdf.PdfReader",
                        side_effect=RuntimeError("forced pypdf failure")):
            txt = aug._pdf_text(FAKE_PID, page=0)
        assert txt.strip(), "fitz fallback returned empty when pypdf was forced to fail"
        assert MARKER in txt, "fitz fallback did not recover the expected text"
        print(f"[PASS] pypdf-fail -> fitz fallback ({len(txt)} chars, marker found)")

        # ---- Sanity: normal path returns usable text ----
        txt2 = aug._pdf_text(FAKE_PID, page=0)
        assert txt2.strip(), "normal path returned empty on a valid cached PDF"
        print(f"[PASS] normal path returns text ({len(txt2)} chars)")

        print("[ALL TESTS PASSED]")
        return 0
    finally:
        try:
            os.remove(pdf_path)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
