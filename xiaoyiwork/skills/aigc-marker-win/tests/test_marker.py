import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from decorators.docx_decorator import DocxAigcDecorator
from decorators.excel_decorator import ExcelAigcDecorator
from decorators.html_decorator import HtmlAigcDecorator
from decorators.md_decorator import MdAigcDecorator
from decorators.pdf_decorator import PdfAigcDecorator
from decorators.ppt_decorator import PptAigcDecorator


class MarkerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_markdown_and_html_are_rewritten_without_trailing_bytes(self):
        md_path = self.root / "sample.md"
        md_path.write_text("# Title\n" + "x" * 500, encoding="utf-8")
        MdAigcDecorator().decorate(str(md_path), "digest", add_visible_mark=False)
        md_text = md_path.read_text(encoding="utf-8")
        self.assertTrue(md_text.startswith("---\nAIGC:"))
        self.assertNotIn("内容由AI生成", md_text)

        html_path = self.root / "sample.html"
        html_path.write_text("<html><body>short</body></html>" + "z" * 500, encoding="utf-8")
        HtmlAigcDecorator().decorate(str(html_path), "digest", add_visible_mark=True)
        html_text = html_path.read_text(encoding="utf-8")
        self.assertIn("内容由AI生成", html_text)
        HtmlAigcDecorator().decorate(str(html_path), "digest", add_visible_mark=True)
        self.assertEqual(html_path.read_text(encoding="utf-8").count("内容由AI生成"), 1)

    def test_office_and_pdf_implicit_markers(self):
        from docx import Document
        from openpyxl import Workbook
        from pptx import Presentation
        from reportlab.pdfgen import canvas

        docx_path = self.root / "sample.docx"
        doc = Document()
        doc.add_paragraph("hello")
        doc.save(docx_path)
        docx_marker = DocxAigcDecorator()
        docx_marker.decorate(str(docx_path), "digest", add_visible_mark=False)
        self.assertIsNotNone(docx_marker._get_aigc_data(str(docx_path)))

        xlsx_path = self.root / "sample.xlsx"
        workbook = Workbook()
        workbook.active["A1"] = "hello"
        workbook.save(xlsx_path)
        xlsx_marker = ExcelAigcDecorator()
        xlsx_marker.decorate(str(xlsx_path), "digest", add_visible_mark=False)
        self.assertIsNotNone(xlsx_marker._get_aigc_data(str(xlsx_path)))

        pptx_path = self.root / "sample.pptx"
        presentation = Presentation()
        presentation.slides.add_slide(presentation.slide_layouts[6])
        presentation.save(pptx_path)
        pptx_marker = PptAigcDecorator()
        pptx_marker.decorate(str(pptx_path), "digest", add_visible_mark=False)
        self.assertIsNotNone(pptx_marker._get_aigc_data(str(pptx_path)))

        pdf_path = self.root / "sample.pdf"
        pdf = canvas.Canvas(str(pdf_path))
        pdf.drawString(72, 720, "hello")
        pdf.save()
        pdf_marker = PdfAigcDecorator()
        pdf_marker.decorate(str(pdf_path), "digest", add_visible_mark=False)
        self.assertIsNotNone(pdf_marker._get_aigc_data(str(pdf_path)))
        self.assertGreater(os.path.getsize(pdf_path), 0)

    def test_cli_reports_machine_readable_success(self):
        md_path = self.root / "cli.md"
        md_path.write_text("# CLI", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "main.py"), str(md_path), "--skip-visible"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AIGC_MARKER_OK:", result.stdout)

    def test_pdf_cli_does_not_import_docx_dependency(self):
        """A missing dependency for another format must not block PDF marking."""
        from reportlab.pdfgen import canvas

        pdf_path = self.root / "lazy-import.pdf"
        pdf = canvas.Canvas(str(pdf_path))
        pdf.drawString(72, 720, "lazy import")
        pdf.save()

        blocker_dir = self.root / "blocked-dependencies"
        blocker_dir.mkdir()
        (blocker_dir / "docx.py").write_text(
            'raise ModuleNotFoundError("blocked docx dependency")\n',
            encoding="utf-8",
        )
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = os.pathsep.join(
            part for part in (str(blocker_dir), existing_pythonpath) if part
        )
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "main.py"), str(pdf_path), "--skip-visible"],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AIGC_MARKER_OK:", result.stdout)
        self.assertNotIn("docx", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
