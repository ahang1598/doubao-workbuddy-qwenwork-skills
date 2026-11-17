"""Integration checks. Set SHOT_BROWSER to a Chromium executable if needed."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'runtime' / 'shot.py'


class FixedCanvasTests(unittest.TestCase):
    def render(self, content_height=200, declared_height=240, safe=40, extra='', safe_height=None, width=480):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        source = Path(directory.name) / 'test.html'
        size = f'width:{width}px;height:{declared_height}px;margin:0;padding:0;box-sizing:border-box;'
        actual_safe = safe if safe_height is None else safe_height
        source.write_text(f'<!doctype html><html data-canvas-width="{width}" data-canvas-height="{declared_height}" style="{size}"><head><meta charset="utf-8"></head><body style="{size}"><main style="{size}"><div style="height:{content_height}px;background:#126abc">Test{extra}</div><div data-canvas-bottom-safe-area="{safe}" style="height:{actual_safe}px;background:#ffffff"></div></main></body></html>')
        cmd = [sys.executable, str(SCRIPT), str(source), '--timeout-ms', '1000']
        if os.environ.get('SHOT_BROWSER'):
            cmd += ['--exec-path', os.environ['SHOT_BROWSER']]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def test_exact_canvas_and_natural_height(self):
        from PIL import Image
        code, report = self.render()
        self.assertEqual(code, 0, report)
        self.assertEqual(report['measurement']['natural']['height'], 240)
        image = Image.open(report['screenshot']['path'])
        self.assertEqual(image.size, (480, 240))
        self.assertEqual(image.getpixel((200, 239)), (255, 255, 255))

    def test_overflow_and_missing_safety(self):
        code, report = self.render(content_height=300, safe=0)
        self.assertEqual(code, 1, report)
        codes = {x['code'] for x in report['issues']}
        self.assertIn('CONTENT_OVERFLOW', codes)
        self.assertIn('BOTTOM_SAFE_AREA_INVALID', codes)

    def test_design_selected_safety_height(self):
        for width, safe in [(480, 8), (1600, 24), (480, 72)]:
            with self.subTest(width=width, safe=safe):
                code, report = self.render(width=width, safe=safe, declared_height=200+safe)
                self.assertEqual(code, 0, report)

    def test_safety_declaration_matches_height(self):
        for actual in (24, 48):
            with self.subTest(actual=actual):
                code, report = self.render(safe=40, safe_height=actual, declared_height=200+actual)
                self.assertEqual(code, 1, report)
                self.assertIn('BOTTOM_SAFE_AREA_INVALID', {x['code'] for x in report['issues']})

    def test_safety_declaration_is_positive_integer(self):
        for declared in ('0', '-1', '8.5', 'invalid'):
            with self.subTest(declared=declared):
                code, report = self.render(safe=declared, safe_height=40)
                self.assertEqual(code, 1, report)
                self.assertIn('BOTTOM_SAFE_AREA_INVALID', {x['code'] for x in report['issues']})

    def test_content_cannot_enter_small_safety_area(self):
        code, report = self.render(safe=8, declared_height=208, extra='<span style="position:absolute;top:198px;height:8px">Overlapping</span>')
        self.assertEqual(code, 1, report)
        self.assertIn('BOTTOM_SAFE_AREA_INVALID', {x['code'] for x in report['issues']})

    def test_long_canvas_bottom_is_preserved(self):
        from PIL import Image
        code, report = self.render(content_height=7000, declared_height=7040)
        self.assertEqual(code, 0, report)
        self.assertEqual(len(report['slices']), 3)
        image = Image.open(report['screenshot']['path'])
        self.assertEqual(image.size, (480, 7040))
        self.assertEqual(image.getpixel((200, 6999)), (18, 106, 188))
        self.assertEqual(image.getpixel((200, 7039)), (255, 255, 255))

    def test_broken_local_image_is_reported(self):
        code, report = self.render(extra='<img src="missing.png">')
        self.assertEqual(code, 1, report)
        self.assertTrue(report['measurement']['brokenImages'])
        self.assertIn('IMAGE_SHORTLINK_REQUIRED', {x['code'] for x in report['issues']})

    def test_output_does_not_overwrite_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.html'
            path.write_text('source retained')
            result = subprocess.run([sys.executable, str(SCRIPT), str(path), '-o', str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 3)
            self.assertEqual(path.read_text(), 'source retained')
            self.assertEqual(json.loads(result.stdout)['status'], 'error')


if __name__ == '__main__':
    unittest.main()
