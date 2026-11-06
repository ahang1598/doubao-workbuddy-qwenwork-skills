"""Verify serialized storage independently against the user's text guide."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from lxml import etree as E

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
sys.path.insert(0, str(ROOT/'tests'))
from decorators.common import get_aigc_signature
from decorators.text_metadata import inspect_text_metadata, GUIDE_EXTENSIONS
from decorators.uof_decorator import UOF2, UOF3
from run_text_format_smoke import create
from test_uof_marker import make_uof_sample, EXTENSIONS
import main


def replace_parts(path, updates):
    with zipfile.ZipFile(path) as z:
        entries = {i.filename: z.read(i) for i in z.infolist()}
        comment = z.comment
    entries.update(updates)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.comment = comment
        for name, value in entries.items(): z.writestr(name, value)


def make_pos(path):
    # Script fixture based on public ProcessOn native editor definitions, not an editor export.
    if path.suffix.lower() == '.posm':
        diagram = {'id': 'root', 'root': True, 'title': 'AIGC标识回归样例',
                   'structure': 'mind_free', 'theme': 'default', 'showWatermark': False,
                   'watermark': '', 'children': [{'id': 'topic1', 'parent': 'root',
                     'title': '原有内容保持不变', 'children': []}]}
    else:
        diagram = {'page': {'width': 800, 'height': 600, 'backgroundColor': '255,255,255'},
                   'elements': {'original': {'id': 'original', 'name': 'text',
                     'props': {'x': 60, 'y': 80, 'w': 260, 'h': 50, 'zindex': 1, 'angle': 0},
                     'textBlock': [{'position': {'x': 0, 'y': 0, 'w': 'w', 'h': 'h'},
                                    'text': '原有内容保持不变'}],
                     'title': '文本', 'category': 'basic', 'group': '', 'parent': '',
                     'children': [], 'locked': False, 'link': '', 'theme': {},
                     'shapeStyle': {'alpha': 1}, 'fontStyle': {'size': 16, 'color': '0,0,0'},
                     'fillStyle': {}, 'lineStyle': {}, 'dataAttributes': [],
                     'attribute': {'visible': True, 'rotatable': True, 'container': False,
                                   'collapsable': False, 'collapsed': False, 'linkable': True},
                     'resizeDir': ['tl','tr','br','bl','l','t','r','b'],
                     'path': [{'lineStyle': {'lineWidth': 0}, 'fillStyle': {'type': 'none'},
                               'actions': [{'action':'move','x':'0','y':'0'},
                                           {'action':'line','x':'w','y':'0'},
                                           {'action':'line','x':'w','y':'h'},
                                           {'action':'line','x':'0','y':'h'}, {'action':'close'}]}],
                     'anchors': [{'x':'w/2','y':'0'}, {'x':'w/2','y':'h'},
                                 {'x':'0','y':'h/2'}, {'x':'w','y':'h/2'}]}}}
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.comment = b'preserve comment'
        z.writestr('meta.json', json.dumps({'version':'5.0', 'vendor':{'keep':True}}))
        z.writestr('content.json', json.dumps({'diagram': diagram}, ensure_ascii=False))
        z.writestr('resources/original.bin', b'original\x00\xff')


class TextGuideTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def cli(self, path, *args, code=0):
        result = subprocess.run([sys.executable, str(ROOT/'scripts/main.py'), str(path), *args],
            capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def test_all_eighteen_guide_extensions_exact_storage_and_read_only_verification(self):
        for ext in sorted(GUIDE_EXTENSIONS):
            with self.subTest(ext=ext):
                path = self.folder/('sample'+ext)
                make_pos(path) if ext in ('.posm','.posf') else create(path)
                self.cli(path, '--skip-visible')
                before = path.read_bytes()
                result = inspect_text_metadata(path)
                self.assertTrue(result['guide_storage_verified'])
                self.assertEqual(set(result['metadata']), {'Label','ContentProducer','ProduceID','ReservedCode1','ContentPropagator','PropagateID','ReservedCode2'})
                self.assertTrue(all(isinstance(v,str) for v in result['metadata'].values()))
                self.assertIn('AIGC_METADATA_VERIFIED:', self.cli(path, '--verify').stdout)
                self.assertEqual(before, path.read_bytes())

    def test_pos_metadata_preserves_all_content_and_repeat_bytes(self):
        for ext in ('.posm','.posf'):
            path = self.folder/('diagram'+ext)
            make_pos(path)
            identity = json.loads(get_aigc_signature('old'))
            identity.pop('ReservedCode2')
            replace_parts(path, {'meta.json':json.dumps({'version':'5.0','AIGC':identity}).encode()})
            with zipfile.ZipFile(path) as z:
                contents = {n:z.read(n) for n in z.namelist() if n!='meta.json'}
            self.cli(path, '--skip-visible')
            result = inspect_text_metadata(path)
            self.assertEqual(result['metadata']['ProduceID'], identity['ProduceID'])
            self.assertEqual(result['metadata']['ReservedCode2'], '')
            with zipfile.ZipFile(path) as z:
                self.assertEqual(z.comment, b'preserve comment')
                self.assertEqual(contents, {n:z.read(n) for n in contents})
                self.assertIsInstance(json.loads(z.read('meta.json'))['AIGC'], str)
            before=path.read_bytes()
            self.cli(path,'--skip-visible')
            self.assertEqual(before,path.read_bytes())
            self.cli(path)
            self.assertNotEqual(before,path.read_bytes())
            from decorators.pos_decorator import inspect_pos_visible
            self.assertTrue(inspect_pos_visible(path)['visible_storage_verified'])
            self.assertEqual(inspect_text_metadata(path)['metadata']['ProduceID'], identity['ProduceID'])
            before=path.read_bytes();self.cli(path)
            self.assertEqual(before,path.read_bytes())

    def test_native_2021_uof_packages_all_six_kinds(self):
        for ext in EXTENSIONS:
            with self.subTest(ext=ext):
                path = make_uof_sample(self.folder/('uof3'+ext))
                with zipfile.ZipFile(path) as z:
                    parts = {n:z.read(n) for n in z.namelist()}
                for name, data in parts.items():
                    if name.endswith('.xml'):
                        for key, ns in UOF2.items(): data = data.replace(ns.encode(), UOF3[key].encode())
                        parts[name] = data
                replace_parts(path, parts)
                self.cli(path)
                result=inspect_text_metadata(path)
                self.assertTrue(result['guide_storage_verified'])
                with zipfile.ZipFile(path) as z:
                    meta=E.fromstring(z.read('_meta/meta.xml'))
                    self.assertEqual(E.QName(meta).namespace, 'http://www.nits.org.cn/uof3/zh-cn/2021/metadata')
                    self.assertEqual(z.read('data/original.bin'), b'original bytes\x00\xff')
                    self.assertIn(b'2021', z.read('content.xml'))
                snapshot=path.read_bytes(); self.cli(path)
                self.assertEqual(snapshot,path.read_bytes())

    def test_ooxml_wrong_storage_type_is_repaired_and_identity_preserved(self):
        path=self.folder/'repair.docx';create(path);self.cli(path,'--skip-visible')
        with zipfile.ZipFile(path) as z: root=E.fromstring(z.read('docProps/custom.xml'))
        prop=next(p for p in root if p.get('name')=='AIGC')
        old=json.loads(prop[0].text);old.pop('ReservedCode2')
        prop[0].tag=prop[0].tag.replace('lpwstr','lpstr');prop[0].text=json.dumps({'AIGC':old})
        replace_parts(path,{'docProps/custom.xml':E.tostring(root)})
        self.cli(path,'--skip-visible')
        self.assertEqual(inspect_text_metadata(path)['metadata']['ProduceID'],old['ProduceID'])

    def test_conflicting_office_provenance_fails_without_modifying_source(self):
        path=self.folder/'conflict.docx';create(path);self.cli(path,'--skip-visible')
        with zipfile.ZipFile(path) as z: root=E.fromstring(z.read('docProps/custom.xml'))
        prop=next(p for p in root if p.get('name')=='AIGC')
        duplicate=E.fromstring(E.tostring(prop));duplicate.set('pid','999')
        data=json.loads(duplicate[0].text);data['ProduceID']='conflicting-id';duplicate[0].text=json.dumps(data)
        root.append(duplicate);replace_parts(path,{'docProps/custom.xml':E.tostring(root)})
        before=path.read_bytes();self.cli(path,'--skip-visible',code=1)
        self.assertEqual(before,path.read_bytes())

    def test_pdf_exact_key_and_missing_reserved_fields(self):
        from pypdf import PdfReader,PdfWriter
        path=self.folder/'metadata.pdf';create(path)
        writer=PdfWriter(clone_from=path)
        writer.add_metadata({'/OtherAIGC':get_aigc_signature('wrong-key')})
        with path.open('wb') as f:writer.write(f)
        self.cli(path,'--skip-visible')
        self.assertIn('/AIGC',PdfReader(path).metadata)
        self.assertTrue(inspect_text_metadata(path)['guide_storage_verified'])

    def test_xmind_object_record_is_migrated_to_string_without_changing_identity(self):
        path=self.folder/'object.xmind';create(path)
        old=json.loads(get_aigc_signature('original'));old.pop('ReservedCode1')
        replace_parts(path,{'metadata.json':json.dumps({'AIGC':old,'custom':'keep'}).encode()})
        self.cli(path,'--skip-visible')
        self.assertEqual(inspect_text_metadata(path)['metadata']['ProduceID'],old['ProduceID'])
        with zipfile.ZipFile(path) as z:self.assertEqual(json.loads(z.read('metadata.json'))['custom'],'keep')

    def test_failed_post_write_verification_preserves_source(self):
        path=self.folder/'atomic.md';create(path);before=path.read_bytes()
        with patch('decorators.text_metadata.inspect_text_metadata',side_effect=ValueError('failed readback')):
            with self.assertRaisesRegex(ValueError,'failed readback'):main.add_aigc_mark(str(path))
        self.assertEqual(before,path.read_bytes())
        self.assertEqual(list(self.folder.glob('.aigc-*')),[])

    def test_version_and_legacy_uof_are_not_misreported_as_guide_compliance(self):
        r=subprocess.run([sys.executable,str(ROOT/'scripts/main.py'),'--version'],capture_output=True,text=True)
        self.assertEqual(r.returncode,0);self.assertIn((ROOT/'VERSION').read_text().strip(),r.stdout)
        path=make_uof_sample(self.folder/'legacy.uot',1)
        self.assertIn('AIGC_GUIDE_NOT_COVERED:',self.cli(path).stdout)
        self.cli(path,'--verify',code=3)


if __name__=='__main__':unittest.main()
