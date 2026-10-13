import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from resolve_font import load_web_manifest, select_web_family, select_web_face, build_web_font_contract
from web_font_check import validate


class WebFontTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[2]
        self.family = select_web_family(load_web_manifest(), 'douyin-sans')
        self.css = build_web_font_contract(self.family, select_web_face(self.family, 700, 'normal'))['font_face_css']

    def html(self, css):
        return '<html><head><style data-web-fonts>' + css + '</style></head><body></body></html>'

    def test_valid(self):
        self.assertEqual(validate(self.html(self.css)), [])

    def test_invalid(self):
        for html in [self.html(self.css + 'body{color:red}'),
                     self.html(self.css.replace('douyin-sans-bold.ttf', 'unknown.ttf')),
                     self.html(self.css.replace('700', '400')),
                     self.html(self.css + self.css),
                     self.html(self.css).replace('<head>', '<body>').replace('</head>', '</body>'),
                     self.html(self.css).replace('data-web-fonts', ''),
                     self.html(self.css.replace('https://', 'https:// '))]:
            with self.subTest(html=html): self.assertTrue(validate(html))

    def test_missing_weight(self):
        with self.assertRaises(ValueError): select_web_face(self.family, 400, 'normal')

    def test_all_faces(self):
        for family in load_web_manifest()['families']:
            for face in family['faces']:
                self.assertEqual(validate(self.html(build_web_font_contract(family, face)['font_face_css'])), [])

    def test_manifest_matches_published_web_catalog_shape(self):
        families = load_web_manifest()['families']
        faces = [face for family in families for face in family['faces']]
        urls = {face['url'] for face in faces}
        self.assertEqual(len(families), 155)
        self.assertEqual(len(faces), 371)
        self.assertEqual(len(urls), 294)
        self.assertEqual(len({family['id'] for family in families}), len(families))
        self.assertEqual(len({face['id'] for face in faces}), len(faces))
        self.assertTrue(all(
            family['default_face_id'] in {face['id'] for face in family['faces']}
            for family in families
        ))
        self.assertTrue(all(face.get('verified') is True for face in faces))

    def test_canvas_download_urls_are_a_subset_of_web_urls(self):
        canvas_manifest = json.loads((self.root / 'assets/fonts/font-cdn-manifest.json').read_text(encoding='utf-8'))
        canvas_urls = {entry['cdn_url'] for entry in canvas_manifest['files'] if entry.get('verified') is True}
        web_urls = {
            face['url']
            for family in load_web_manifest()['families']
            for face in family['faces']
            if face.get('verified') is True
        }
        self.assertTrue(canvas_urls)
        self.assertTrue(canvas_urls <= web_urls)

    def test_platform_remote_fonts_exist_in_web_manifest(self):
        pool = json.loads((self.root / 'assets/fonts/font-curated-pool.json').read_text(encoding='utf-8'))
        web_families = {family['css_family'] for family in load_web_manifest()['families']}
        system_families = {'PingFang SC', 'Arial', 'Helvetica Neue'}
        platform_families = {font['family'] for font in pool['platform_fonts']}
        self.assertEqual(platform_families - system_families - web_families, set())


if __name__ == '__main__': unittest.main()
