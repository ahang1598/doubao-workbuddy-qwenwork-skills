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
    def render(self, content_height=200, declared_height=240, safe=40, extra=''):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        source = Path(directory.name) / 'test.html'
        size = f'width:480px;height:{declared_height}px;margin:0;padding:0;box-sizing:border-box;'
        source.write_text(f'<!doctype html><html data-canvas-width="480" data-canvas-height="{declared_height}" style="{size}"><head><meta charset="utf-8"></head><body style="{size}"><main style="{size}"><div style="height:{content_height}px;background:#126abc">Test{extra}</div><div data-canvas-bottom-safe-area="{safe}" style="height:{safe}px;background:#ffffff"></div></main></body></html>')
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

    def test_overflow_still_detected(self):
        code, report = self.render(content_height=300, safe=0)
        self.assertEqual(code, 1, report)
        codes = {x['code'] for x in report['issues']}
        self.assertIn('CONTENT_OVERFLOW', codes)
        self.assertNotIn('BOTTOM_SAFE_AREA_INVALID', codes)

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
