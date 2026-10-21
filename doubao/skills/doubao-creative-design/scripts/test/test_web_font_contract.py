import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

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

    def test_equivalent_font_declaration_order_and_quotes(self):
        head, body = self.css.split('{', 1)
        declarations = [s.strip() for s in body.rsplit('}', 1)[0].split(';') if s.strip()]
        reordered = head + '{' + ';'.join(reversed(declarations)) + ';}'
        for css in [reordered, reordered.replace('"', "'")]:
            with self.subTest(css=css):
                self.assertEqual(validate(self.html(css)), [])

    def test_invalid(self):
        for html in [self.html(self.css.replace('douyin-sans-bold.ttf', 'unknown.ttf')),
                     self.html(self.css.replace('700', '400')),
                     self.html(self.css.replace('https://', 'https:// '))]:
            with self.subTest(html=html): self.assertTrue(validate(html))

    def test_style_organization_is_optional(self):
        for html in [self.html(self.css + 'body{color:red}'),
                     self.html(self.css + self.css),
                     self.html(self.css).replace('<head>', '<body>').replace('</head>', '</body>'),
                     self.html(self.css).replace('data-web-fonts', ''),
                     self.html(self.css).replace('</head>', '<style>p{color:blue}</style></head>'),
                     '<html><head><link rel="stylesheet" href="https://example.com/site.css"></head><body></body></html>',
                     self.html(self.css).replace('</style>', '</style><style>' + self.css + '</style>')]:
            with self.subTest(html=html): self.assertEqual(validate(html), [])

    def test_unclosed_style_remains_invalid(self):
        self.assertTrue(validate('<html><head><style>' + self.css))

    def test_comments_are_not_font_rules(self):
        self.assertEqual(validate(self.html('/* @font-face {src:url(old.woff)} */')), [])

    def test_uppercase_font_rule_is_checked(self):
        self.assertTrue(validate(self.html('@FONT-FACE {font-family:Unknown;src:local(Arial)}')))

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


@unittest.skipUnless(os.environ.get('SHOT_TEST_CHROMIUM'), 'Set SHOT_TEST_CHROMIUM for browser regression tests')
class ShotStyleTests(unittest.TestCase):
    def test_embedded_external_font_decisions_match(self):
        from playwright.sync_api import sync_playwright
        from web_font_check import validate_loaded
        family = select_web_family(load_web_manifest(), 'douyin-sans')
        css = build_web_font_contract(family, select_web_face(family, 700, 'normal'))['font_face_css']
        head, body = css.split('{', 1)
        reordered = head + '{' + ';'.join(reversed([s.strip() for s in body.rstrip().rstrip('}').split(';') if s.strip()])) + ';}'
        cases = [(reordered, True), (reordered.replace('"', "'"), True),
                 ('@media all{' + css + '}', True),
                 (css.replace('700', 'bold'), True),
                 (css.replace('font-display: swap', 'font-display: block'), True),
                 (css.replace('700', '400'), False),
                 (css.replace('font-style: normal', 'font-style: italic'), False),
                 (css.replace('douyin-sans-bold.ttf', 'unknown.ttf'), False),
                 (css.replace('https://', 'https:// '), False),
                 (css.replace('src:', 'src: local(Arial),'), False)]
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ['SHOT_TEST_CHROMIUM'])
            try:
                page = browser.new_page()
                for candidate, expected in cases:
                    with self.subTest(css=candidate):
                        page.set_content('<html><head></head><body>Test</body></html>')
                        external = validate_loaded(page, {'https://example.com/fonts.css': candidate})
                        embedded = validate('<html><style>' + candidate + '</style></html>')
                        self.assertEqual(not embedded, expected)
                        self.assertEqual(not external, expected)
                        page.set_content('<html><style>' + candidate + '</style></html>')
                        self.assertEqual(not validate_loaded(page, {}), expected)
            finally:
                browser.close()

    def render(self, content='', root_height=300, css='', inline_sizes=True, imported_css='', canvas_height='300'):
        from shot import run
        with tempfile.TemporaryDirectory(prefix='shot-style-test-') as directory:
            folder = Path(directory)
            # Test fixtures are generated locally; no external resources are needed.
            (folder / 'imported.css').write_text(imported_css, encoding='utf-8')
            (folder / 'styles.css').write_text('@import url("imported.css");body{margin:0}p{margin:0;color:blue}' + css, encoding='utf-8')
            source = folder / 'test.html'
            source.write_text(
                '<!doctype html><html data-canvas-width="240" data-canvas-height="300" style="width:240px;height:300px">'
                '<head><meta charset="utf-8"><link rel="stylesheet" href="styles.css"><style>.copy{font-size:20px}</style></head>'
                '<body style="width:240px;height:300px"><main style="width:240px;height:' + str(root_height) + 'px">'
                '<p class="copy">Test</p>' + content + '</main></body></html>', encoding='utf-8')
            if not inline_sizes:
                source.write_text(source.read_text().replace('width:240px;height:300px', ''), encoding='utf-8')
            if canvas_height != '300':
                source.write_text(source.read_text().replace('data-canvas-height="300"', 'data-canvas-height="' + canvas_height + '"'), encoding='utf-8')
            return run(SimpleNamespace(html_file=str(source), output=str(folder / 'out.png'),
                                       exec_path=os.environ['SHOT_TEST_CHROMIUM'], timeout_ms=3000, slice_height=3200))

    def test_no_required_markers_box_sizing_or_footer_node(self):
        report = self.render()
        self.assertEqual(report['issues'], [])
        self.assertEqual((report['screenshot']['width'], report['screenshot']['height']), (240, 300))

    def test_optional_footer_marker_does_not_require_minimum(self):
        self.assertEqual(self.render('<div data-canvas-bottom-safe-area="1" style="height:1px"></div>')['issues'], [])

    def test_size_mismatch_still_detected(self):
        self.assertIn('ROOT_SIZE_MISMATCH', {i['code'] for i in self.render(root_height=290)['issues']})

    def test_real_overflow_still_detected(self):
        report = self.render('<div style="height:400px">Overflow</div>')
        self.assertIn('CONTENT_OVERFLOW', {i['code'] for i in report['issues']})

    def test_root_sizes_must_be_inline(self):
        report = self.render(css='html,body,main{width:240px;height:300px}', inline_sizes=False)
        self.assertIn('INLINE_CANVAS_SIZE', {i['code'] for i in report['issues']})

    def test_external_css_image_url_checked(self):
        report = self.render(css='main{background-image:url("data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")}')
        self.assertIn('IMAGE_SHORTLINK_REQUIRED', {i['code'] for i in report['issues']})

    def test_external_font_source_checked(self):
        report = self.render(css='@font-face{font-family:Unknown;src:local(Arial)}')
        self.assertIn('WEB_FONT_CONTRACT_INVALID', {i['code'] for i in report['issues']})

    def test_imported_font_source_checked(self):
        report = self.render(imported_css='@FONT-FACE{font-family:Unknown;src:local(Arial)}')
        self.assertIn('WEB_FONT_CONTRACT_INVALID', {i['code'] for i in report['issues']})

    def test_manifest_fonts_allowed_in_external_css(self):
        css='\n'.join(build_web_font_contract(f, face)['font_face_css']
                      for f in load_web_manifest()['families'] for face in f['faces'])
        self.assertEqual(self.render(imported_css=css)['issues'], [])

    def test_reordered_font_allowed_through_actual_import(self):
        family = select_web_family(load_web_manifest(), 'douyin-sans')
        css = build_web_font_contract(family, select_web_face(family, 700, 'normal'))['font_face_css']
        head, body = css.split('{', 1)
        reordered = head + '{' + ';'.join(reversed([s.strip() for s in body.rstrip().rstrip('}').split(';') if s.strip()])) + ';}'
        self.assertEqual(self.render(imported_css=reordered)['issues'], [])

    def test_pseudo_element_image_checked(self):
        report = self.render(css='main::before{content:"";background-image:url("data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")}')
        self.assertIn('IMAGE_SHORTLINK_REQUIRED', {i['code'] for i in report['issues']})

    def test_invalid_dimensions_are_source_error(self):
        report = self.render(canvas_height='300px')
        self.assertEqual(report['status'], 'needs_review')
        self.assertIn('CANVAS_ATTRIBUTES', {i['code'] for i in report['issues']})


if __name__ == '__main__': unittest.main()
