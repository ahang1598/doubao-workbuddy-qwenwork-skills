"""OOXML namespace, package relationship and visible-placement regression cases.

Strict fixtures adapt the schemas and relationship URIs of make_office samples.
They test namespace preservation, rather than claiming full Office validation.
"""
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from lxml import etree as ET

from test_text_formats import make_office
from decorators.common import is_aigc_complete
from decorators.ooxml_decorator import OoxmlAigcDecorator, NS, STRICT_NS, TEXT, dump, xml


def rewrite_package(path, updates=None, removals=()):
    with zipfile.ZipFile(path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist() if name not in removals}
        comment = archive.comment
    entries.update(updates or {})
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.comment = comment
        for name, data in entries.items():
            archive.writestr(name, data)


def make_strict(path):
    make_office(path)
    mapping = {NS[key]: STRICT_NS[key] for key in ("w", "s", "p", "a", "r", "cp", "vt")}
    mapping["http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"] = "http://purl.oclc.org/ooxml/officeDocument/extendedProperties"
    updates = {}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name.endswith((".xml", ".rels")):
                data = archive.read(name)
                for old, new in mapping.items():
                    data = data.replace(old.encode(), new.encode())
                data = data.replace(b"/relationships/custom-properties", b"/relationships/customProperties")
                data = data.replace(b"/relationships/extended-properties", b"/relationships/extendedProperties")
                updates[name] = data
    rewrite_package(path, updates)


class OoxmlEdgeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_six_strict_types_keep_namespace_and_template_content_type(self):
        for extension in (".docx", ".dotx", ".xlsx", ".xltx", ".pptx", ".potx"):
            with self.subTest(extension=extension):
                path = self.root / ("strict" + extension)
                make_strict(path)
                with zipfile.ZipFile(path) as archive:
                    original = {name: archive.read(name) for name in archive.namelist()}
                    original_types = xml(original["[Content_Types].xml"])
                decorator = OoxmlAigcDecorator()
                decorator.decorate(path, "Strict original content", False)
                with zipfile.ZipFile(path) as archive:
                    self.assertEqual(archive.read("custom/untouched.bin"), original["custom/untouched.bin"])
                    for name in original:
                        if name.startswith(("word/", "xl/", "ppt/")):
                            self.assertEqual(archive.read(name), original[name])
                metadata = decorator._get_aigc_data(path)
                self.assertTrue(is_aigc_complete(metadata))
                decorator.decorate(path, "visible upgrade")
                with zipfile.ZipFile(path) as archive:
                    properties = xml(archive.read("docProps/custom.xml"))
                    self.assertEqual(ET.QName(properties).namespace, STRICT_NS["cp"])
                    self.assertEqual(ET.QName(properties[0][0]).namespace, STRICT_NS["vt"])
                    relation = next(r for r in xml(archive.read("_rels/.rels")) if r.get("Type", "").endswith("/customProperties"))
                    self.assertEqual(relation.get("Type"), STRICT_NS["r"] + "/customProperties")
                    current_types = {(ET.QName(p).localname, p.get("PartName") or p.get("Extension")): p.get("ContentType") for p in xml(archive.read("[Content_Types].xml"))}
                    for part in original_types:
                        self.assertEqual(current_types[(ET.QName(part).localname, part.get("PartName") or part.get("Extension"))], part.get("ContentType"))
                    if extension in (".docx", ".dotx"):
                        root = xml(archive.read("word/document.xml"))
                        self.assertEqual(ET.QName(root).namespace, STRICT_NS["w"])
                        labels = root.xpath("//w:t[text()=$text]", namespaces=STRICT_NS, text=TEXT)
                    elif extension in (".xlsx", ".xltx"):
                        root = xml(archive.read("xl/worksheets/sheet1.xml"))
                        self.assertEqual(ET.QName(root).namespace, STRICT_NS["s"])
                        labels = root.xpath("//s:t[text()=$text]", namespaces=STRICT_NS, text=TEXT)
                        self.assertIn(TEXT, root.find("s:headerFooter/s:oddFooter", STRICT_NS).text)
                        self.assertEqual(root.find("s:dimension", STRICT_NS).get("ref"), "A2:F4")
                    else:
                        root = xml(archive.read("ppt/slides/slide1.xml"))
                        self.assertEqual(ET.QName(root).namespace, STRICT_NS["p"])
                        labels = root.xpath("//a:t[text()=$text]", namespaces=STRICT_NS, text=TEXT)
                    self.assertEqual(len(labels), 1)
                    self.assertEqual(decorator._get_aigc_data(path), metadata)
                    marked = {name: archive.read(name) for name in archive.namelist()}
                decorator.decorate(path, "repeat")
                with zipfile.ZipFile(path) as archive:
                    self.assertEqual(marked, {name: archive.read(name) for name in archive.namelist()})
                destination = os.environ.get("AIGC_TEST_OUTPUT")
                if destination:
                    Path(destination).mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, Path(destination) / path.name)

    def test_relocated_custom_properties_preserve_other_properties_in_both_families(self):
        for strict in (False, True):
            with self.subTest(strict=strict):
                path = self.root / (str(strict) + ".docx")
                (make_strict if strict else make_office)(path)
                decorator = OoxmlAigcDecorator()
                decorator.decorate(path, "original", False)
                ns = STRICT_NS if strict else NS
                with zipfile.ZipFile(path) as archive:
                    props = xml(archive.read("docProps/custom.xml"))
                    props.remove(props[0])
                    prop = ET.SubElement(props, "{" + ns["cp"] + "}property", name="UserProperty", pid="2", fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}")
                    ET.SubElement(prop, "{" + ns["vt"] + "}lpwstr").text = "Must survive"
                    rels = xml(archive.read("_rels/.rels"))
                    relation = next(r for r in rels if r.get("Type", "").rsplit("/", 1)[-1] in ("custom-properties", "customProperties"))
                    relation.set("Target", "custom/relocated.xml")
                    types = xml(archive.read("[Content_Types].xml"))
                    next(p for p in types if p.get("PartName") == "/docProps/custom.xml").set("PartName", "/custom/relocated.xml")
                rewrite_package(path, {"custom/relocated.xml": dump(props), "_rels/.rels": dump(rels), "[Content_Types].xml": dump(types)}, ["docProps/custom.xml"])
                decorator.decorate(path, "new original")
                with zipfile.ZipFile(path) as archive:
                    self.assertNotIn("docProps/custom.xml", archive.namelist())
                    props = xml(archive.read("custom/relocated.xml"))
                    self.assertEqual(props.find("cp:property[@name='UserProperty']/vt:lpwstr", ns).text, "Must survive")
                    self.assertEqual(ET.QName(props.find("cp:property[@name='AIGC']", ns)[0]).namespace, ns["vt"])
                    self.assertTrue(is_aigc_complete(decorator._get_aigc_data(path)))
                    self.assertEqual(len(props), 2)

    def test_hidden_first_slide_and_extension_order_in_both_families(self):
        for strict in (False, True):
            with self.subTest(strict=strict):
                path = self.root / (str(strict) + ".pptx")
                (make_strict if strict else make_office)(path)
                ns = STRICT_NS if strict else NS
                with zipfile.ZipFile(path) as archive:
                    first = xml(archive.read("ppt/slides/slide1.xml"))
                    first.set("show", "0")
                    second = xml(archive.read("ppt/slides/slide2.xml"))
                    tree = second.find("p:cSld/p:spTree", ns)
                    ET.SubElement(tree, "{" + ns["p"] + "}extLst")
                hidden_bytes = dump(first)
                rewrite_package(path, {"ppt/slides/slide1.xml": hidden_bytes, "ppt/slides/slide2.xml": dump(second)})
                OoxmlAigcDecorator().decorate(path, "hidden first slide")
                with zipfile.ZipFile(path) as archive:
                    self.assertEqual(archive.read("ppt/slides/slide1.xml"), hidden_bytes)
                    tree = xml(archive.read("ppt/slides/slide2.xml")).find("p:cSld/p:spTree", ns)
                    self.assertEqual([ET.QName(e).localname for e in tree[-2:]], ["sp", "extLst"])
                    self.assertEqual(tree[-2].find("p:txBody/a:p/a:r/a:t", ns).text, TEXT)

    def test_instance_reuse_does_not_change_global_namespace_map(self):
        original = NS.copy()
        decorator = OoxmlAigcDecorator()
        for strict in (True, False):
            path = self.root / (str(strict) + ".docx")
            (make_strict if strict else make_office)(path)
            decorator.decorate(path, "reuse")
            ns = STRICT_NS if strict else NS
            with zipfile.ZipFile(path) as archive:
                self.assertEqual(len(xml(archive.read("word/document.xml")).xpath("//w:t[text()=$text]", namespaces=ns, text=TEXT)), 1)
        self.assertEqual(NS, original)


if __name__ == "__main__":
    unittest.main()
