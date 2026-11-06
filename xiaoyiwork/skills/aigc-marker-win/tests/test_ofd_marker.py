import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from decorators.common import is_aigc_complete
from decorators.ofd_decorator import OfdAigcDecorator, OFD_NS, PNG_MARK_KEY, VISIBLE_TEXT

NS = {"ofd": OFD_NS}


def make_ofd(path, boxes=((0, 0, 210, 297), (0, 0, 297, 210)), absolute=False):
    """Build a real OFD package with referenced fonts and visible body text."""
    page_refs, pages = [], {}
    for index, box in enumerate(boxes):
        loc = f"Pages/Page_{index}/Content.xml"
        reference = f"/Doc_0/{loc}" if absolute else loc
        page_refs.append(f'<ofd:Page ID="{index * 3 + 1}" BaseLoc="{reference}"/>')
        area = '' if index == 0 else f'<ofd:Area><ofd:PhysicalBox>{" ".join(map(str,box))}</ofd:PhysicalBox></ofd:Area>'
        pages[f"Doc_0/{loc}"] = f'''<ofd:Page xmlns:ofd="{OFD_NS}">{area}<ofd:Content>
        <ofd:Layer ID="{index * 3 + 3}" Type="Body"><ofd:TextObject ID="{500 + index * 200}" Font="2" Size="5" Boundary="20 20 100 10">
        <ofd:FillColor Value="0 0 0"/><ofd:TextCode X="0" Y="5" DeltaX="g 8 3">OFD sample</ofd:TextCode>
        </ofd:TextObject></ofd:Layer></ofd:Content></ofd:Page>'''.encode()
    entry = f'''<ofd:OFD xmlns:ofd="{OFD_NS}" Version="1.0" DocType="OFD"><ofd:DocBody><ofd:DocInfo>
    <ofd:DocID>fbde79767233487397f358b960bf048c</ofd:DocID><ofd:Title>Marker test</ofd:Title><ofd:Creator>test fixture</ofd:Creator>
    <ofd:CustomDatas><ofd:CustomData Name="Original">retain</ofd:CustomData></ofd:CustomDatas>
    </ofd:DocInfo><ofd:DocRoot>Doc_0/Document.xml</ofd:DocRoot></ofd:DocBody></ofd:OFD>'''.encode()
    document = f'''<ofd:Document xmlns:ofd="{OFD_NS}"><ofd:CommonData><ofd:MaxUnitID>10</ofd:MaxUnitID>
    <ofd:PageArea><ofd:PhysicalBox>{" ".join(map(str, boxes[0]))}</ofd:PhysicalBox></ofd:PageArea>
    <ofd:PublicRes>PublicRes.xml</ofd:PublicRes></ofd:CommonData><ofd:Pages>{"".join(page_refs)}</ofd:Pages></ofd:Document>'''.encode()
    fonts = f'<ofd:Res xmlns:ofd="{OFD_NS}" BaseLoc="Res"><ofd:Fonts><ofd:Font ID="2" FontName="Arial" FamilyName="Arial"/></ofd:Fonts></ofd:Res>'.encode()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as target:
        target.comment = b"original archive comment"
        target.writestr("OFD.xml", entry)
        target.writestr("Doc_0/Document.xml", document)
        target.writestr("Doc_0/PublicRes.xml", fonts)
        for name, data in pages.items():
            target.writestr(name, data)
        target.writestr("Unrelated/opaque.bin", b"retain\x00\xff")


def read_parts(path):
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


class OfdMarkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "sample.ofd"
        self.marker = OfdAigcDecorator()
        self.font = Path(os.environ.get("CLAW_AIGC_FONT_PATH") or (Path(__file__).resolve().parents[3] / "fonts" / "HarmonyOS_Sans_SC.ttf"))
        self.env = patch.dict(os.environ, {"CLAW_AIGC_FONT_PATH": str(self.font)})
        self.env.start()
        make_ofd(self.path)

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_metadata_uses_docinfo_customdata_and_preserves_parts(self):
        before = read_parts(self.path)
        self.marker.decorate(str(self.path), "digest", False)
        after = read_parts(self.path)
        self.assertTrue(is_aigc_complete(self.marker._get_aigc_data(str(self.path))))
        root = ET.fromstring(after["OFD.xml"])
        original = root.find("ofd:DocBody/ofd:DocInfo/ofd:CustomDatas/ofd:CustomData[@Name='Original']", NS)
        self.assertEqual(original.text, "retain")
        guide_property = root.find("ofd:DocBody/ofd:DocInfo/ofd:CustomDatas/ofd:CustomData[@name='AIGC']", NS)
        self.assertIsNotNone(guide_property)
        self.assertEqual(guide_property.get("Name"), "AIGC")
        self.assertTrue(is_aigc_complete(json.loads(guide_property.text)))
        self.assertEqual({k:v for k,v in after.items() if k != 'OFD.xml'}, {k:v for k,v in before.items() if k != 'OFD.xml'})
        with zipfile.ZipFile(self.path) as archive:
            self.assertEqual(archive.comment, b"original archive comment")
        marked = self.path.read_bytes()
        self.marker.decorate(str(self.path), "new digest", False)
        self.assertEqual(self.path.read_bytes(), marked)

    def test_legacy_name_variants_upgrade_without_changing_provenance(self):
        for legacy_attribute in ("Name", "name"):
            with self.subTest(attribute=legacy_attribute):
                make_ofd(self.path)
                self.marker.decorate(str(self.path), "original digest", False)
                original_signature = self.marker._get_aigc_data(str(self.path))
                parts = read_parts(self.path)
                root = ET.fromstring(parts["OFD.xml"])
                prop = root.find("ofd:DocBody/ofd:DocInfo/ofd:CustomDatas/ofd:CustomData[@Name='AIGC']", NS)
                del prop.attrib["name" if legacy_attribute == "Name" else "Name"]
                parts["OFD.xml"] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                with zipfile.ZipFile(self.path, "w", zipfile.ZIP_DEFLATED) as archive:
                    for name, data in parts.items():
                        archive.writestr(name, data)
                self.marker.decorate(str(self.path), "different digest", False)
                self.assertEqual(self.marker._get_aigc_data(str(self.path)), original_signature)
                prop = ET.fromstring(read_parts(self.path)["OFD.xml"]).find(
                    "ofd:DocBody/ofd:DocInfo/ofd:CustomDatas/ofd:CustomData[@name='AIGC']", NS)
                self.assertEqual(prop.get("Name"), "AIGC")
                marked = self.path.read_bytes()
                self.marker.decorate(str(self.path), "different again", False)
                self.assertEqual(self.path.read_bytes(), marked)

    def test_conflicting_property_names_fail_without_changing_file(self):
        self.marker.decorate(str(self.path), "original digest", False)
        parts = read_parts(self.path)
        root = ET.fromstring(parts["OFD.xml"])
        prop = root.find("ofd:DocBody/ofd:DocInfo/ofd:CustomDatas/ofd:CustomData[@Name='AIGC']", NS)
        prop.set("name", "Unrelated")
        parts["OFD.xml"] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        with zipfile.ZipFile(self.path, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in parts.items():
                archive.writestr(name, data)
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "Conflicting OFD AIGC"):
            self.marker.decorate(str(self.path), "new digest", False)
        self.assertEqual(before, self.path.read_bytes())

    def test_visible_marks_are_referenced_on_all_pages_and_ids_unique(self):
        from PIL import Image
        self.marker.decorate(str(self.path), "digest")
        parts = read_parts(self.path)
        document = ET.fromstring(parts["Doc_0/Document.xml"])
        refs = document.findall("ofd:CommonData/ofd:DocumentRes", NS)
        self.assertEqual(len(refs), 1)
        resource = ET.fromstring(parts["Doc_0/" + refs[0].text])
        media = resource.find("ofd:MultiMedias/ofd:MultiMedia", NS)
        image_path = "Doc_0/" + resource.get("BaseLoc") + "/" + media.find("ofd:MediaFile", NS).text
        with Image.open(io.BytesIO(parts[image_path])) as image:
            self.assertEqual(image.info[PNG_MARK_KEY], VISIBLE_TEXT)
            self.assertGreater(sum(1 for x in range(image.width) for y in range(image.height) if image.getpixel((x,y))[:3] == (0,0,0)), 100)
        for index, box in enumerate(((0,0,210,297), (0,0,297,210))):
            page = ET.fromstring(parts[f"Doc_0/Pages/Page_{index}/Content.xml"])
            layer = page.findall("ofd:Content/ofd:Layer", NS)[-1]
            self.assertEqual(layer.get("Type"), "Foreground")
            obj = layer.find("ofd:ImageObject", NS)
            self.assertEqual(obj.get("ResourceID"), media.get("ID"))
            x,y,width,height = map(float, obj.get("Boundary").split())
            self.assertGreaterEqual(x,box[0]); self.assertGreaterEqual(y,box[1])
            self.assertLessEqual(x+width, box[0]+box[2]); self.assertLessEqual(y+height, box[1]+box[3])
            self.assertEqual(list(map(float,obj.get("CTM").split())), [width,0,0,height,0,0])
        ids = [e.get("ID") for name,data in parts.items() if name.endswith('.xml') for e in ET.fromstring(data).iter() if e.get("ID")]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(int(document.find("ofd:CommonData/ofd:MaxUnitID",NS).text), max(map(int,ids)))
        self.assertEqual(parts["Unrelated/opaque.bin"], b"retain\x00\xff")
        marked = self.path.read_bytes()
        self.marker.decorate(str(self.path), "digest")
        self.assertEqual(self.path.read_bytes(), marked)

    def test_skip_visible_can_be_followed_by_visible_mark(self):
        self.marker.decorate(str(self.path), "digest", False)
        signature = self.marker._get_aigc_data(str(self.path))
        self.marker.decorate(str(self.path), "other digest", True)
        self.assertEqual(self.marker._get_aigc_data(str(self.path)), signature)
        for name,data in read_parts(self.path).items():
            if name.endswith('/Content.xml'):
                self.assertIsNotNone(ET.fromstring(data).find("ofd:Content/ofd:Layer/ofd:ImageObject",NS))

    def test_absolute_paths_nonzero_page_origins_and_small_pages(self):
        make_ofd(self.path, boxes=((5,7,20,30),(2,3,12,10)), absolute=True)
        self.marker.decorate(str(self.path), "digest")
        for index,box in enumerate(((5,7,20,30),(2,3,12,10))):
            page = ET.fromstring(read_parts(self.path)[f"Doc_0/Pages/Page_{index}/Content.xml"])
            obj = page.find("ofd:Content/ofd:Layer/ofd:ImageObject",NS)
            x,y,w,h = map(float,obj.get('Boundary').split())
            self.assertGreaterEqual(x,box[0]); self.assertGreaterEqual(y,box[1])
            self.assertLessEqual(x+w,box[0]+box[2]); self.assertLessEqual(y+h,box[1]+box[3])

    def test_missing_font_keeps_source_and_cleans_temp_files(self):
        before = self.path.read_bytes()
        with patch("fonts.get_font_path", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "font.*not found"):
                self.marker.decorate(str(self.path), "digest")
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(list(self.path.parent.glob('.aigc-*')), [])

    def test_failed_atomic_replace_keeps_source_and_cleans_temp_files(self):
        before = self.path.read_bytes()
        with patch("decorators.ofd_decorator.os.replace", side_effect=OSError("test locked file")):
            with self.assertRaisesRegex(RuntimeError,"test locked file"):
                self.marker.decorate(str(self.path), "digest")
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(list(self.path.parent.glob('.aigc-*')), [])

    def test_invalid_page_and_archive_fail_without_rewriting(self):
        make_ofd(self.path, boxes=((0,0,-1,297),))
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError,"invalid PhysicalBox"):
            self.marker.decorate(str(self.path),"digest")
        self.assertEqual(self.path.read_bytes(),before)
        self.path.write_bytes(b'not an OFD archive')
        with self.assertRaises(RuntimeError):
            self.marker.decorate(str(self.path),"digest")
        self.assertEqual(self.path.read_bytes(),b'not an OFD archive')


    def test_adds_watermark_to_new_page_after_prior_marking(self):
        self.marker.decorate(str(self.path), "digest")
        parts = read_parts(self.path)
        document = ET.fromstring(parts["Doc_0/Document.xml"])
        pages = document.find("ofd:Pages",NS)
        ET.SubElement(pages, f"{{{OFD_NS}}}Page", ID="800", BaseLoc="Pages/Page_2/Content.xml")
        parts["Doc_0/Document.xml"] = ET.tostring(document)
        parts["Doc_0/Pages/Page_2/Content.xml"] = f'<ofd:Page xmlns:ofd="{OFD_NS}"><ofd:Content><ofd:Layer ID="801" Type="Body"/></ofd:Content></ofd:Page>'.encode()
        with zipfile.ZipFile(self.path,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,data in parts.items():
                archive.writestr(name,data)
        self.marker.decorate(str(self.path), "other digest")
        after = read_parts(self.path)
        for name in ('Doc_0/Pages/Page_0/Content.xml','Doc_0/Pages/Page_1/Content.xml'):
            self.assertEqual(after[name],parts[name])
        page = ET.fromstring(after["Doc_0/Pages/Page_2/Content.xml"])
        self.assertEqual(len(page.findall("ofd:Content/ofd:Layer/ofd:ImageObject",NS)),1)
        self.assertGreater(int(ET.fromstring(after["Doc_0/Document.xml"]).find("ofd:CommonData/ofd:MaxUnitID",NS).text),801)

    def test_all_document_bodies_receive_both_marks(self):
        from copy import deepcopy
        parts = read_parts(self.path)
        root = ET.fromstring(parts['OFD.xml'])
        second = deepcopy(root.find('ofd:DocBody',NS))
        second.find('ofd:DocInfo/ofd:DocID',NS).text='ebde79767233487397f358b960bf048c'
        second.find('ofd:DocRoot',NS).text='Doc_1/Document.xml'
        root.append(second)
        parts['OFD.xml']=ET.tostring(root)
        parts.update({name.replace('Doc_0/','Doc_1/',1):data for name,data in list(parts.items()) if name.startswith('Doc_0/')})
        with zipfile.ZipFile(self.path,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,data in parts.items():
                archive.writestr(name,data)
        self.marker.decorate(str(self.path), 'digest')
        after = read_parts(self.path)
        root = ET.fromstring(after['OFD.xml'])
        self.assertEqual(len(root.findall("ofd:DocBody/ofd:DocInfo/ofd:CustomDatas/ofd:CustomData[@Name='AIGC']",NS)),2)
        visible_ids=[]
        for name,data in after.items():
            if name.endswith('/Content.xml'):
                obj=ET.fromstring(data).find('ofd:Content/ofd:Layer/ofd:ImageObject',NS)
                self.assertIsNotNone(obj)
                visible_ids.append(obj.get('ID'))
        self.assertEqual(len(visible_ids),len(set(visible_ids)))
        marked=self.path.read_bytes()
        self.marker.decorate(str(self.path), 'digest')
        self.assertEqual(self.path.read_bytes(),marked)



    def test_cli_skip_visible_full_repeat_and_export_artifact(self):
        results=[]
        env=os.environ.copy()
        env['PYTHONIOENCODING']='utf-8'
        for stage,options in [('implicit',['--skip-visible']),('visible',[]),('repeat',[])]:
            before=self.path.read_bytes()
            result=subprocess.run([sys.executable,str(SCRIPTS/'main.py'),str(self.path),*options],
                                  capture_output=True,text=True,encoding='utf-8',check=False,env=env)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('AIGC_MARKER_OK:',result.stdout)
            self.assertTrue(is_aigc_complete(self.marker._get_aigc_data(str(self.path))))
            for name,data in read_parts(self.path).items():
                if name.endswith('/Content.xml'):
                    visible=ET.fromstring(data).find('ofd:Content/ofd:Layer/ofd:ImageObject',NS)
                    self.assertEqual(visible is not None,stage != 'implicit')
            if stage == 'repeat':
                self.assertEqual(self.path.read_bytes(),before)
            results.append({'format':'ofd','stage':stage,'returncode':result.returncode,'stdout':result.stdout})
        artifact_dir=os.environ.get('AIGC_TEST_ARTIFACT_DIR')
        if artifact_dir:
            directory=Path(artifact_dir)
            directory.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(self.path,directory/'sample.ofd')
            (directory/'ofd-cli-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__ == "__main__":
    unittest.main()
