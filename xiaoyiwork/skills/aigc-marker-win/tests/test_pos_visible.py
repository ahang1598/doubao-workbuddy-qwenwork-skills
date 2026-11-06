"""POSM/POSF visible canvas marking and preservation regressions."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
sys.path.insert(0, str(ROOT/'tests'))
from decorators.pos_decorator import PosAigcDecorator, inspect_pos_visible, read_pos_metadata
from decorators.pos_visible import MARKER_ID, VISIBLE_TEXT
from test_text_guide import make_pos, replace_parts
import main


class PosVisibleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def sample(self, ext):
        path = self.folder/('sample'+ext)
        make_pos(path)
        return path

    def read(self, path):
        with zipfile.ZipFile(path) as z:
            return json.loads(z.read('content.json'))

    def write(self, path, data):
        replace_parts(path, {'content.json': json.dumps(data, ensure_ascii=False).encode()})

    def test_native_watermark_and_actual_text_on_both_formats_with_repeat_stability(self):
        for ext in ('.posm', '.posf'):
            with self.subTest(ext=ext):
                path = self.sample(ext)
                old = self.read(path)['diagram']
                main.add_aigc_mark(str(path))
                result = inspect_pos_visible(path)
                self.assertEqual(result['canvas_count'], 1)
                canvas = self.read(path)['diagram']
                target = canvas if ext == '.posm' else canvas['page']
                self.assertEqual(target['watermark'], VISIBLE_TEXT)
                self.assertIs(target['showWatermark'], True)
                if ext == '.posm':
                    self.assertEqual(canvas['children'][:-1], old['children'])
                    self.assertEqual(canvas['title'], old['title'])
                    self.assertEqual(canvas['children'][-1]['title'], VISIBLE_TEXT)
                else:
                    self.assertEqual(canvas['elements']['original'], old['elements']['original'])
                    label = canvas['elements'][MARKER_ID]
                    self.assertGreater(label['props']['y'], 130)
                    self.assertEqual(label['textBlock'][0]['text'], VISIBLE_TEXT)
                    self.assertIs(label['attribute']['visible'], True)
                    self.assertEqual(label['fontStyle']['color'], '0,0,0')
                with zipfile.ZipFile(path) as z:
                    self.assertEqual(z.read('resources/original.bin'), b'original\x00\xff')
                    self.assertEqual(z.comment, b'preserve comment')
                    self.assertEqual(json.loads(z.read('meta.json'))['vendor'], {'keep': True})
                before = path.read_bytes()
                main.add_aigc_mark(str(path))
                self.assertEqual(before, path.read_bytes())

    def test_metadata_only_upgrade_preserves_existing_provenance(self):
        for ext in ('.posm', '.posf'):
            path = self.sample(ext)
            original = self.read(path)
            main.add_aigc_mark(str(path), False)
            self.assertEqual(self.read(path), original)
            identity = read_pos_metadata(path)
            main.add_aigc_mark(str(path))
            self.assertEqual(read_pos_metadata(path), identity)
            inspect_pos_visible(path)

    def test_multiple_canvases_and_serialized_definition_wrappers(self):
        for ext in ('.posm', '.posf'):
            path = self.sample(ext)
            diagram = self.read(path)['diagram']
            self.write(path, {'canvases': [{'def': json.dumps(diagram)}, {'definition': copy.deepcopy(diagram)}]})
            main.add_aigc_mark(str(path))
            self.assertEqual(inspect_pos_visible(path)['canvas_count'], 2)
            self.assertIsInstance(self.read(path)['canvases'][0]['def'], str)
            before = path.read_bytes(); main.add_aigc_mark(str(path))
            self.assertEqual(before, path.read_bytes())

    def test_separate_canvas_members_are_all_marked_and_resources_ignored(self):
        path = self.sample('.posm')
        diagram = self.read(path)['diagram']
        replace_parts(path, {'canvases/second.json': json.dumps(diagram).encode(),
                             'resources/template.json': json.dumps(diagram).encode()})
        main.add_aigc_mark(str(path))
        self.assertEqual(inspect_pos_visible(path)['canvas_count'], 2)
        with zipfile.ZipFile(path) as z:
            self.assertEqual(json.loads(z.read('resources/template.json')), diagram)

    def test_existing_custom_watermarks_and_folded_branches_are_preserved(self):
        for ext in ('.posm', '.posf'):
            path = self.sample(ext)
            data = self.read(path); canvas = data['diagram']
            target = canvas if ext == '.posm' else canvas['page']
            target.update({'watermark': '原有公司水印', 'showWatermark': False})
            if ext == '.posm': canvas.update({'fold': True, 'hideSelf': True})
            self.write(path, data)
            main.add_aigc_mark(str(path))
            canvas = self.read(path)['diagram']; target = canvas if ext == '.posm' else canvas['page']
            self.assertEqual(target['watermark'], '原有公司水印 | '+VISIBLE_TEXT)
            if ext == '.posm':
                self.assertIs(canvas['fold'], True); self.assertIs(canvas['hideSelf'], True)
            inspect_pos_visible(path)

    def test_flow_label_outside_original_content_expands_small_page(self):
        path = self.sample('.posf'); data = self.read(path)
        data['diagram']['elements']['original']['props']['y'] = 1500
        self.write(path, data); main.add_aigc_mark(str(path))
        canvas = self.read(path)['diagram']; props = canvas['elements'][MARKER_ID]['props']
        self.assertGreater(props['y'], 1550)
        self.assertGreaterEqual(canvas['page']['height'], props['y']+props['h'])

    def test_unknown_canvas_and_mixed_collections_fail_atomically(self):
        for ext in ('.posm', '.posf'):
            for mixed in (False, True):
                path = self.sample(ext); diagram = self.read(path)['diagram']
                self.write(path, {'canvases': [diagram, {'unknown': True}]} if mixed else {'opaque': True})
                before = path.read_bytes()
                with self.assertRaisesRegex(ValueError, 'nrecognized|supported'):
                    main.add_aigc_mark(str(path))
                self.assertEqual(before, path.read_bytes())
                self.assertEqual(list(self.folder.glob('.aigc-*')), [])
                main.add_aigc_mark(str(path), False)
                self.assertIsNotNone(read_pos_metadata(path))

    def test_reserved_id_collisions_fail_without_overwriting_original(self):
        for ext in ('.posm', '.posf'):
            path = self.sample(ext); data = self.read(path); canvas = data['diagram']
            if ext == '.posm': canvas['children'].append({'id': MARKER_ID, 'title': '原有用户节点'})
            else: canvas['elements'][MARKER_ID] = {'name': 'process', 'textBlock': []}
            self.write(path, data); before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'already used'): main.add_aigc_mark(str(path))
            self.assertEqual(before, path.read_bytes())

    def test_extension_and_canvas_type_mismatch_fails_atomically(self):
        mind = self.sample('.posm'); flow = self.sample('.posf')
        self.write(flow, self.read(mind)); before = flow.read_bytes()
        with self.assertRaisesRegex(ValueError, 'does not match'): main.add_aigc_mark(str(flow))
        self.assertEqual(before, flow.read_bytes())

    def test_top_level_canvas_arrays_and_empty_flow_canvases(self):
        for ext in ('.posm', '.posf'):
            path = self.sample(ext); canvas = self.read(path)['diagram']
            if ext == '.posf': canvas['elements'] = {}
            self.write(path, [canvas, copy.deepcopy(canvas)])
            main.add_aigc_mark(str(path))
            self.assertEqual(inspect_pos_visible(path)['canvas_count'], 2)

    def test_unknown_primary_encoding_does_not_allow_partial_success(self):
        path = self.sample('.posm')
        diagram = self.read(path)['diagram']
        replace_parts(path, {'content.json': b'unknown-binary-format',
                             'canvases/second.json': json.dumps(diagram).encode()})
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'encoding'): main.add_aigc_mark(str(path))
        self.assertEqual(before, path.read_bytes())

    def test_readonly_check_detects_disabled_native_watermark(self):
        path = self.sample('.posf'); main.add_aigc_mark(str(path))
        data = self.read(path); data['diagram']['page']['showWatermark'] = False
        self.write(path, data); before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'missing or disabled'): inspect_pos_visible(path)
        self.assertEqual(before, path.read_bytes())
        main.add_aigc_mark(str(path)); inspect_pos_visible(path)


if __name__ == '__main__': unittest.main()
