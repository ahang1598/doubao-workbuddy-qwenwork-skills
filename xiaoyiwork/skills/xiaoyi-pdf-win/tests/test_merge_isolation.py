import os
import sys
import tempfile

from reportlab.pdfgen import canvas

_root = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_root, "..", "scripts"))

from merge import merge


def _write_pdf(path: str, text: str) -> None:
    pdf = canvas.Canvas(path)
    pdf.drawString(72, 720, text)
    pdf.save()


def test_merge_refuses_output_owned_by_another_job():
    with tempfile.TemporaryDirectory() as tmp:
        cover = os.path.join(tmp, "cover.pdf")
        body = os.path.join(tmp, "body.pdf")
        output = os.path.join(tmp, "result.pdf")
        _write_pdf(cover, "cover")
        _write_pdf(body, "body")
        with open(output + ".xiaoyi-pdf.lock", "w", encoding="ascii") as stream:
            stream.write("123")

        result = merge(cover, body, output)

        assert result["status"] == "error"
        assert "another PDF job" in result["error"]
        assert not os.path.exists(output)


def test_merge_atomically_replaces_output_and_removes_lock():
    with tempfile.TemporaryDirectory() as tmp:
        cover = os.path.join(tmp, "cover.pdf")
        body = os.path.join(tmp, "body.pdf")
        output = os.path.join(tmp, "result.pdf")
        _write_pdf(cover, "cover")
        _write_pdf(body, "body")

        result = merge(cover, body, output, "isolated")

        assert result["status"] == "ok"
        assert os.path.getsize(output) > 0
        assert not os.path.exists(output + ".xiaoyi-pdf.lock")
        assert not [name for name in os.listdir(tmp) if name.endswith(".tmp")]
