import hashlib
import contextlib
import importlib.util
import os
import io
from pathlib import Path
import tempfile
import unittest

import fitz
from PIL import Image

DEFAULT_SOURCE = Path(__file__).parents[1] / 'template' / 'template_reference_assets.py'
SOURCE = Path(os.environ.get('REFERENCE_MODULE', DEFAULT_SOURCE))
spec = importlib.util.spec_from_file_location('overview_candidate', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PdfOverviewTests(unittest.TestCase):
    def render(self, *args, **kwargs):
        operation = getattr(module, 'render_pdf_overview', None)
        self.assertTrue(callable(operation), 'PDF references need a complete visual overview operation')
        return operation(*args, **kwargs)

    def document(self, path, count=3):
        doc = fitz.open()
        for index in range(count):
            page = doc.new_page(width=200, height=100)
            page.draw_rect(fitz.Rect(0, 0, 200, 100), color=None,
                           fill=(1, 0, 0) if index == count - 1 else (0, 0, 1))
            page.insert_text((20, 40), f'PAGE {index+1}', fontsize=18, color=(1, 1, 1))
        doc.save(path)
        doc.close()

    def test_complete_long_reference_and_original_last_page(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / 'reference.pdf'
            self.document(pdf, 87)
            original = pdf.read_bytes()
            result = self.render(pdf, root / 'view')
            self.assertEqual(result['selected_pages'], list(range(1, 88)))
            self.assertEqual([page['page'] for page in result['pages']], list(range(1, 88)))
            self.assertEqual(result['source_pdf']['sha256'], hashlib.sha256(original).hexdigest())
            self.assertEqual(pdf.read_bytes(), original)
            with Image.open(result['pages'][-1]['path']) as image:
                red, green, blue = image.getpixel((image.width-10, image.height-10))
                self.assertGreater(red, 220)
                self.assertLess(green + blue, 40)
            covered = [page for sheet in result['overview']['sheets'] for page in sheet['pages']]
            self.assertEqual(covered, list(range(1, 88)))
            for sheet in result['overview']['sheets']:
                with Image.open(sheet['path']) as image:
                    self.assertLessEqual(max(image.size), 3800)

    def test_rotation_and_original_page_aspect_are_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            doc = fitz.open()
            page = doc.new_page(width=200, height=100)
            page.draw_rect(fitz.Rect(0, 0, 100, 100), color=None, fill=(1, 0, 0))
            page.draw_rect(fitz.Rect(100, 0, 200, 100), color=None, fill=(0, 0, 1))
            page.set_rotation(90)
            pdf = root / 'rotated.pdf'
            doc.save(pdf)
            doc.close()
            result = self.render(pdf, root / 'view')
            with Image.open(result['pages'][0]['path']) as image:
                self.assertAlmostEqual(image.height / image.width, 2, places=2)
                top = image.getpixel((image.width//2, image.height//4))
                bottom = image.getpixel((image.width//2, 3*image.height//4))
                self.assertGreater(top[0], 220)
                self.assertGreater(bottom[2], 220)

    def test_selected_pages_keep_source_numbering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / 'reference.pdf'
            self.document(pdf)
            result = self.render(pdf, root / 'view', pages=[3, 1])
            self.assertEqual(result['selected_pages'], [1, 3])
            self.assertEqual([page['page'] for page in result['pages']], [1, 3])
            self.assertEqual(result['source_pdf']['page_count'], 3)

    def test_overview_cli_preserves_a_separate_asset_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / 'reference.pdf'
            self.document(pdf)
            output = root / 'view'
            output.mkdir()
            inventory = output / 'reference-assets.json'
            inventory.write_text('{"assets":["original-payload"]}')
            original = inventory.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = module.main(['overview', '--pdf', str(pdf), '--output-dir', str(output)])
            self.assertEqual(code, 0)
            self.assertEqual(inventory.read_bytes(), original)
            self.assertTrue((output / 'reference-overview.json').is_file())


if __name__ == '__main__':
    unittest.main()
