"""Generate and mark one sample per requested text extension; save a result matrix."""
import argparse
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from lxml import etree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))
from test_text_formats import make_office, make_xmind
from test_uof_marker import make_uof_sample
from test_ofd_marker import make_ofd
from decorators.common import is_aigc_complete, parse_aigc_json
from decorators.ooxml_decorator import OoxmlAigcDecorator
from decorators.uof_decorator import UofAigcDecorator, UOF2
from decorators.ofd_decorator import OfdAigcDecorator, OFD_NS
from decorators.pdf_decorator import PdfAigcDecorator
from decorators.md_decorator import MdAigcDecorator
from decorators.xmind_decorator import XmindAigcDecorator
from decorators.html_decorator import HtmlAigcDecorator, inspect_html

TEXT = "内容由AI生成"
EXTENSIONS = ("docx", "pptx", "xlsx", "dotx", "xltx", "potx", "uot", "uott", "uos", "uost", "uop", "uopt", "pdf", "ofd", "md", "xmind", "html", "htm")


def create(path):
    extension = path.suffix[1:]
    if extension in EXTENSIONS[:6]:
        make_office(path)
    elif extension in EXTENSIONS[6:12]:
        make_uof_sample(path, 2)
    elif extension == "pdf":
        from reportlab.pdfgen import canvas
        pdf = canvas.Canvas(str(path))
        for text in ("First original page", "Second original page"):
            pdf.drawString(72, 720, text)
            pdf.showPage()
        pdf.save()
    elif extension == "ofd":
        make_ofd(path)
    elif extension == "md":
        path.write_text("# Original Markdown\n\nText format smoke test.\n", encoding="utf-8")
    elif extension == "xmind":
        make_xmind(path)
    elif extension in ("html", "htm"):
        path.write_text("<!doctype html><html><head><title>Synthetic sample</title></head><body><h1>Original content</h1><p>Public test fixture only.</p></body></html>", encoding="utf-8")


def verify(path):
    extension = path.suffix[1:]
    if extension in EXTENSIONS[:6]:
        metadata = OoxmlAigcDecorator()._get_aigc_data(path)
        with zipfile.ZipFile(path) as archive:
            parts = [archive.read(name) for name in archive.namelist() if name.startswith(("word/", "xl/worksheets/", "ppt/slides/")) and name.endswith(".xml")]
            visible = any(TEXT.encode() in part for part in parts)
    elif extension in EXTENSIONS[6:12]:
        with zipfile.ZipFile(path) as archive:
            root = ET.fromstring(archive.read("_meta/meta.xml"))
            node = next(e for e in root.iter() if e.get("名称_5211") == "AIGC")
            metadata = parse_aigc_json(node.text)
            visible = TEXT.encode() in archive.read("content.xml")
            if extension in ("uop", "uopt"):
                visible = TEXT.encode() in archive.read("graphics.xml") and b"aigc_" in archive.read("content.xml")
    elif extension == "ofd":
        marker = OfdAigcDecorator()
        metadata = marker._get_aigc_data(str(path))
        with zipfile.ZipFile(path) as archive:
            parts = {name: archive.read(name) for name in archive.namelist()}
        document = ET.fromstring(parts["Doc_0/Document.xml"])
        tag = lambda name: "{" + OFD_NS + "}" + name
        marked = marker._marked_media(document.find(tag("CommonData")), "Doc_0", parts)
        pages = [ET.fromstring(data) for name, data in parts.items() if name.endswith("/Content.xml")]
        visible = bool(pages) and all(any(obj.get("ResourceID") in marked for obj in page.iter(tag("ImageObject"))) for page in pages)
    elif extension == "pdf":
        from pypdf import PdfReader
        metadata = PdfAigcDecorator()._get_aigc_data(str(path))
        visible = all(TEXT in (page.extract_text() or "") for page in PdfReader(path).pages)
    elif extension == "md":
        metadata = MdAigcDecorator()._get_aigc_data(str(path))
        visible = path.read_text(encoding="utf-8").rstrip().endswith(TEXT)
    elif extension == "xmind":
        metadata = XmindAigcDecorator()._get_aigc_data(path)
        with zipfile.ZipFile(path) as archive:
            sheets = json.loads(archive.read("content.json"))
        visible = all(any(child["title"] == TEXT for child in sheet["rootTopic"]["children"]["attached"]) for sheet in sheets)
    elif extension in ("html", "htm"):
        metadata = HtmlAigcDecorator()._get_aigc_data(path)
        visible = TEXT in "".join(inspect_html(path.read_text(encoding="utf-8")).text)
    return is_aigc_complete(metadata), visible


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    for extension in EXTENSIONS:
        path = args.output_dir / ("sample." + extension)
        create(path)
        command = [sys.executable, str(HERE.parent / "scripts" / "main.py"), str(path)]
        result = subprocess.run(command, capture_output=True, encoding="utf-8", env=environment)
        metadata, visible = verify(path) if result.returncode == 0 else (False, False)
        success = result.returncode == 0 and "AIGC_MARKER_OK:" in result.stdout and metadata and visible
        rows.append({"extension": extension, "sample": str(path.resolve()), "exit_code": result.returncode, "implicit_metadata": metadata, "visible_mark": visible, "gcmark_explicit_supported": extension in ("docx", "pdf", "md", "html", "htm"), "gcmark_metadata_supported": extension not in ("html", "htm"), "gcmark_result": "not_tested_login_required", "passed": success, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()})
        print(f"{extension}: {'PASS' if success else 'FAIL'}")
    summary = {"validation_scope": "local_structure_and_readback_only", "gcmark_status": "not_tested_login_required", "formats": len(rows), "passed": sum(row["passed"] for row in rows), "results": rows}
    (args.output_dir / "text-format-results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if all(row["passed"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())