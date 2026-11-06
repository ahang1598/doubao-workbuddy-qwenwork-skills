import io
import os
import tempfile
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors


def _write_pdf_bytes(writer: PdfWriter) -> bytes:
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()


def make_text_pdf(num_pages: int = 3, text_prefix: str = "Page") -> bytes:
    """Return a PDF with the given number of pages, each containing a text string."""
    if num_pages < 1:
        raise ValueError("num_pages must be >= 1")
    writer = PdfWriter()
    for i in range(1, num_pages + 1):
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        c.drawString(100, 700, f"{text_prefix} {i}")
        c.showPage()
        c.save()
        buf.seek(0)
        reader = PdfReader(buf)
        writer.add_page(reader.pages[0])
    return _write_pdf_bytes(writer)


def make_table_pdf() -> bytes:
    """Return a single-page PDF containing a simple table."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    data = [
        ["Name", "Age", "City"],
        ["Alice", "30", "Beijing"],
        ["Bob", "25", "Shanghai"],
    ]
    table = Table(data)
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ]))
    doc.build([table])
    buf.seek(0)
    return buf.read()


def temp_pdf(tmpdir: str | os.PathLike[str], content_bytes: bytes, filename: str = "input.pdf") -> str:
    """Write ``content_bytes`` to ``tmpdir / filename`` and return the full path."""
    path = os.path.join(tmpdir, filename)
    with open(path, "wb") as f:
        f.write(content_bytes)
    return path
