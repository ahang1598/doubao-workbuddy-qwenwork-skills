"""CLI round trips for the six OOXML types, PDF, Markdown and both XMind generations."""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from lxml import etree as ET

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
from decorators.common import is_aigc_complete
from decorators.ooxml_decorator import OoxmlAigcDecorator, NS, TEXT
from decorators.md_decorator import MdAigcDecorator
from decorators.pdf_decorator import PdfAigcDecorator
from decorators.xmind_decorator import XmindAigcDecorator, CONTENT_NS


def make_office(path):
    extension = path.suffix
    if extension in (".docx", ".dotx"):
        from docx import Document
        document = Document()
        document.add_paragraph("Original Word content")
        document.add_table(rows=1, cols=1).cell(0, 0).text = "Original table"
        document.save(path)
        ordinary, template = "wordprocessingml.document.main+xml", "wordprocessingml.template.main+xml"
    elif extension in (".xlsx", ".xltx"):
        from openpyxl import Workbook
        document = Workbook()
        document.active["B2"] = "Original sheet"
        document.active["F3"] = "=1+1"
        document.active.print_area = "B2:F3"
        document.active.sheet_format.zeroHeight = True
        document.active.row_dimensions[2].hidden = False
        document.create_sheet("Second")["A1"] = "Original second sheet"
        document.template = extension == ".xltx"
        document.save(path)
        ordinary, template = "spreadsheetml.sheet.main+xml", "spreadsheetml.template.main+xml"
    else:
        from pptx import Presentation
        from pptx.util import Inches
        document = Presentation()
        for text in ("Original first slide", "Original second slide"):
            slide = document.slides.add_slide(document.slide_layouts[6])
            slide.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(1)).text = text
        document.save(path)
        ordinary, template = "presentationml.presentation.main+xml", "presentationml.template.main+xml"
    # ISO OOXML templates differ in their main part content type, not extension alone.
    with zipfile.ZipFile(path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    if extension in (".dotx", ".potx"):
        entries["[Content_Types].xml"] = entries["[Content_Types].xml"].replace(ordinary.encode(), template.encode())
    entries["custom/untouched.bin"] = b"unrelated resource\x00\xff"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.comment = b"preserve this archive comment"
        for name, data in entries.items():
            archive.writestr(name, data)


def make_xmind(path, legacy=False, mixed=False):
    sheets = [{"id": "sheet1", "class": "sheet", "title": "Original sheet", "rootTopic": {
        "id": "root1", "class": "topic", "title": "Original root", "branch": "folded",
        "children": {"attached": [{"id": "child1", "class": "topic", "title": "Original child"}]}
    }}]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.comment = b"XMind original comment"
        if not legacy or mixed:
            archive.writestr("content.json", json.dumps(sheets))
            archive.writestr("metadata.json", json.dumps({"creator": {"name": "xmind-generator"}, "dataStructureVersion": "2", "custom": "preserved"}))
            archive.writestr("manifest.json", json.dumps({"file-entries": {"content.json": {}, "metadata.json": {}, "resources/attachment.txt": {}}}))
        if legacy or mixed:
            archive.writestr("content.xml", f'<xmap-content xmlns="{CONTENT_NS}" version="2.0"><sheet id="sheet1"><title>Original sheet</title><topic id="root1" branch="folded"><title>Original root</title><children><topics type="attached"><topic id="child1"><title>Original child</title></topic></topics></children></topic></sheet></xmap-content>')
            archive.writestr("META-INF/manifest.xml", '<manifest xmlns="urn:xmind:xmap:xmlns:manifest:1.0"><file-entry full-path="content.xml" media-type="text/xml"/></manifest>')
            archive.writestr("meta.xml", '<meta xmlns="urn:xmind:xmap:xmlns:meta:2.0"><Creator><Name>XMind</Name></Creator></meta>')
        archive.writestr("resources/attachment.txt", b"attachment must be preserved")


class TextFormatCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def cli(self, path, hidden=False, expected=0):
        args = [sys.executable, str(SCRIPTS / "main.py"), str(path)]
        if hidden:
            args.append("--skip-visible")
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        result = subprocess.run(args, capture_output=True, encoding="utf-8", env=env)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        if expected == 0:
            self.assertIn("AIGC_MARKER_OK:", result.stdout)
        else:
            self.assertIn("AIGC_MARKER_FAILED:", result.stdout + result.stderr)
        return result

    def archive_result(self, path, name=None):
        target = os.environ.get("AIGC_TEST_ARTIFACT_DIR")
        if target:
            destination = Path(target)
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination / (name or path.name))

    def test_all_six_ooxml_extensions_visible_hidden_upgrade_and_repeat(self):
        for extension in (".docx", ".dotx", ".xlsx", ".xltx", ".pptx", ".potx"):
            with self.subTest(extension=extension):
                path = self.root / ("sample" + extension)
                make_office(path)
                with zipfile.ZipFile(path) as archive:
                    content_types = ET.fromstring(archive.read("[Content_Types].xml"))
                    original_types = {item.get("PartName"): item.get("ContentType") for item in content_types}
                    original_names = set(archive.namelist())
                    original_bytes = {name: archive.read(name) for name in original_names}
                self.cli(path, hidden=True)
                metadata = OoxmlAigcDecorator()._get_aigc_data(path)
                self.assertTrue(is_aigc_complete(metadata))
                with zipfile.ZipFile(path) as archive:
                    visible = sum(archive.read(name).decode("utf-8", errors="ignore").count(TEXT) for name in archive.namelist() if name.startswith(("word/", "xl/worksheets/", "ppt/slides/")) and name.endswith(".xml"))
                self.assertEqual(visible, 0)
                self.cli(path)
                self.assertEqual(metadata, OoxmlAigcDecorator()._get_aigc_data(path))
                with zipfile.ZipFile(path) as archive:
                    marked_parts = {name: archive.read(name) for name in archive.namelist()}
                    self.assertEqual(archive.comment, b"preserve this archive comment")
                    self.assertEqual(marked_parts["custom/untouched.bin"], original_bytes["custom/untouched.bin"])
                    resulting_types = {item.get("PartName"): item.get("ContentType") for item in ET.fromstring(marked_parts["[Content_Types].xml"])}
                    for name, type_name in original_types.items():
                        self.assertEqual(resulting_types[name], type_name)
                    self.assertTrue(original_names.issubset(marked_parts))
                self.cli(path)
                with zipfile.ZipFile(path) as archive:
                    self.assertEqual(marked_parts, {name: archive.read(name) for name in archive.namelist()})
                if extension in (".docx", ".dotx"):
                    root = ET.fromstring(marked_parts["word/document.xml"])
                    self.assertEqual(root.xpath("count(//w:t[text()=$text])", namespaces=NS, text=TEXT), 1)
                    self.assertIn("Original Word content", "".join(root.itertext()))
                    self.assertEqual(ET.QName(root.find("w:body", NS)[-1]).localname, "sectPr")
                elif extension in (".xlsx", ".xltx"):
                    from openpyxl import load_workbook
                    workbook = load_workbook(path)
                    self.assertEqual(workbook.template, extension == ".xltx")
                    self.assertEqual(workbook.active["F3"].value, "=1+1")
                    self.assertEqual(workbook.active["A4"].value, TEXT)
                    for sheet in workbook:
                        self.assertEqual(sheet.cell(sheet.max_row, 1).value, TEXT)
                        self.assertIn(TEXT, sheet.oddFooter.right.text)
                        self.assertFalse(sheet.row_dimensions[sheet.max_row].hidden)
                    self.assertEqual(workbook.active.print_area, "'Sheet'!$B$2:$F$3")
                    self.assertEqual(ET.fromstring(marked_parts["xl/worksheets/sheet1.xml"]).find("s:dimension", NS).get("ref"), "A2:F4")
                else:
                    from pptx import Presentation
                    normalized = io.BytesIO()
                    with zipfile.ZipFile(normalized, "w") as archive:
                        for name, data in marked_parts.items():
                            if name == "[Content_Types].xml":
                                data = data.replace(b"presentationml.template.main+xml", b"presentationml.presentation.main+xml")
                            archive.writestr(name, data)
                    normalized.seek(0)
                    presentation = Presentation(normalized)
                    self.assertEqual(len(presentation.slides), 2)
                    texts = [s.text for s in presentation.slides[0].shapes if s.has_text_frame]
                    self.assertEqual(texts.count(TEXT), 1)
                    self.assertIn("Original first slide", texts)
                self.archive_result(path)

    def test_xmind_json_xml_and_mixed_packages(self):
        for variant in ("json", "xml", "mixed"):
            with self.subTest(variant=variant):
                path = self.root / ("sample-" + variant + ".xmind")
                make_xmind(path, legacy=variant == "xml", mixed=variant == "mixed")
                self.cli(path, hidden=True)
                metadata = XmindAigcDecorator()._get_aigc_data(path)
                self.assertTrue(is_aigc_complete(metadata))
                self.cli(path)
                self.assertEqual(metadata, XmindAigcDecorator()._get_aigc_data(path))
                with zipfile.ZipFile(path) as archive:
                    snapshot = {name: archive.read(name) for name in archive.namelist()}
                    self.assertEqual(archive.comment, b"XMind original comment")
                    self.assertIsInstance(json.loads(snapshot["metadata.json"])["AIGC"], str)
                    self.assertEqual(snapshot["resources/attachment.txt"], b"attachment must be preserved")
                    if "content.json" in snapshot:
                        topic = json.loads(snapshot["content.json"])[0]["rootTopic"]
                        self.assertEqual(topic["title"], "Original root")
                        self.assertEqual(topic["children"]["attached"][0]["title"], "Original child")
                        self.assertEqual(sum(t["title"] == TEXT for t in topic["children"]["attached"]), 1)
                        self.assertNotEqual(topic.get("branch"), "folded")
                    if "content.xml" in snapshot:
                        root = ET.fromstring(snapshot["content.xml"])
                        self.assertEqual(root.xpath("count(//*[local-name()='title' and text()=$text])", text=TEXT), 1)
                self.cli(path)
                with zipfile.ZipFile(path) as archive:
                    self.assertEqual(snapshot, {name: archive.read(name) for name in archive.namelist()})
                self.archive_result(path)

    def test_pdf_multi_page_and_rotated_page_visible_hidden_upgrade(self):
        from reportlab.pdfgen import canvas
        from pypdf import PdfReader, PdfWriter
        path = self.root / "sample.pdf"
        pdf = canvas.Canvas(str(path))
        pdf.drawString(72, 720, "Original portrait content")
        pdf.showPage()
        pdf.setPageSize((800, 500))
        pdf.drawString(72, 420, "Original landscape content")
        pdf.save()
        writer = PdfWriter(clone_from=path)
        writer.pages[1].rotate(90)
        writer.add_metadata({"/Title": r"Original (title) \ metadata", "/Producer": "Preserve producer"})
        with open(path, "wb") as output:
            writer.write(output)
        self.cli(path, hidden=True)
        metadata = PdfAigcDecorator()._get_aigc_data(path)
        self.assertTrue(is_aigc_complete(metadata))
        self.assertTrue(all(TEXT not in (page.extract_text() or "") for page in PdfReader(path).pages))
        self.cli(path)
        reader = PdfReader(path)
        self.assertEqual(len(reader.pages), 2)
        self.assertEqual(reader.metadata.title, r"Original (title) \ metadata")
        self.assertEqual(reader.metadata.producer, "Preserve producer")
        self.assertTrue(all(TEXT in page.extract_text() for page in reader.pages))
        self.assertEqual(PdfAigcDecorator()._get_aigc_data(path), metadata)
        snapshot = path.read_bytes()
        self.cli(path)
        self.assertEqual(snapshot, path.read_bytes())
        self.archive_result(path)

    def test_markdown_preserves_frontmatter_and_supports_visible_upgrade(self):
        path = self.root / "sample.md"
        path.write_text('---\ntitle: "Original title"\ntags:\n  - test\n---\n\n# Original content\n', encoding="utf-8")
        self.cli(path, hidden=True)
        metadata = MdAigcDecorator()._get_aigc_data(path)
        self.assertTrue(is_aigc_complete(metadata))
        self.assertNotIn(TEXT, path.read_text(encoding="utf-8"))
        self.cli(path)
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count(TEXT), 1)
        self.assertEqual(text.count("AIGC:"), 1)
        self.assertIn('title: "Original title"', text)
        self.assertIn("tags:\n  - test", text)
        self.assertIn('# Original content', text)
        self.assertEqual(metadata, MdAigcDecorator()._get_aigc_data(path))
        self.cli(path)
        self.assertEqual(text, path.read_text(encoding="utf-8"))
        self.archive_result(path)

    def test_rejects_malformed_package_without_modifying_original(self):
        for extension in (".dotx", ".xltx", ".potx", ".xmind"):
            with self.subTest(extension=extension):
                path = self.root / ("bad" + extension)
                path.write_bytes(b"not a valid document")
                self.cli(path, expected=1)
                self.assertEqual(path.read_bytes(), b"not a valid document")


if __name__ == "__main__":
    unittest.main()