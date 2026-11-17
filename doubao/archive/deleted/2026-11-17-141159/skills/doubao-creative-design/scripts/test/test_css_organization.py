"""Browser regressions for CSS organization and retained size/resource checks."""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from shot import run, chromium_executable


class CssOrganizationTests(unittest.TestCase):
    def render(self, css='', sizes=True):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'site.css').write_text('html,body,main{margin:0;padding:0;box-sizing:border-box}p{margin:0}.copy{color:blue}main::before{content:""}' + css)
            size = 'width:240px;height:300px;' if sizes else ''
            source = folder / 'test.html'
            source.write_text('<!doctype html><html data-canvas-width="240" data-canvas-height="300" style="' + size + '"><head><meta charset="utf-8"><link rel="stylesheet" href="site.css"><style>.copy{font-size:20px}</style><style>p{line-height:24px}</style></head><body style="' + size + '"><main style="' + size + '"><section style="height:276px"><p class="copy">Test</p></section><div data-canvas-bottom-safe-area="24" style="height:24px;width:240px"></div></main></body></html>')
            return run(SimpleNamespace(html_file=str(source), output=str(folder / 'preview.png'), exec_path=chromium_executable(), timeout_ms=3000, slice_height=3200))

    def test_multiple_blocks_external_css_and_pseudo_elements(self):
        self.assertEqual(self.render()['issues'], [])

    def test_stylesheet_sizes_do_not_replace_inline_sizes(self):
        issues = self.render('html,body,main{width:240px;height:300px}', sizes=False)['issues']
        self.assertIn('INLINE_CANVAS_SIZE', {i['code'] for i in issues})

    def test_external_font_source_is_still_checked(self):
        issues = self.render('@font-face{font-family:Unknown;src:local(Arial)}')['issues']
        self.assertIn('WEB_FONT_CONTRACT_INVALID', {i['code'] for i in issues})

    def test_external_pseudo_image_is_still_checked(self):
        issues = self.render('main::after{content:url("data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")}')['issues']
        self.assertIn('IMAGE_SHORTLINK_REQUIRED', {i['code'] for i in issues})


if __name__ == '__main__':
    unittest.main()
