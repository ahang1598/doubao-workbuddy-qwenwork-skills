import importlib.util
from pathlib import Path
import tempfile
import unittest
from PIL import Image

spec = importlib.util.spec_from_file_location('stitch_images', Path(__file__).resolve().parents[1] / 'runtime/stitch-images.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StitchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.first = self.root / 'first.png'
        self.second = self.root / 'second.png'
        Image.new('RGBA', (4, 3), (255, 0, 0, 128)).save(self.first)
        Image.new('RGBA', (4, 5), (0, 0, 255, 255)).save(self.second)

    def test_order_dimensions_alpha_and_source_preservation(self):
        before = [p.read_bytes() for p in (self.first, self.second)]
        result = module.stitch([self.first, self.second], self.root / 'joined.png')
        self.assertEqual((result['width'], result['height']), (4, 8))
        with Image.open(result['output']) as im:
            self.assertEqual(im.getpixel((2, 2)), (255, 0, 0, 128))
            self.assertEqual(im.getpixel((2, 3)), (0, 0, 255, 255))
        self.assertEqual(before, [p.read_bytes() for p in (self.first, self.second)])

    def test_mismatched_width_produces_no_output(self):
        Image.new('RGB', (5, 2)).save(self.second)
        out = self.root / 'joined.png'
        with self.assertRaises(ValueError):
            module.stitch([self.first, self.second], out)
        self.assertFalse(out.exists())

    def test_refuses_existing_output_and_input_overwrite(self):
        before = self.first.read_bytes()
        with self.assertRaises(FileExistsError):
            module.stitch([self.first, self.second], self.first)
        self.assertEqual(self.first.read_bytes(), before)

    def test_missing_input_produces_no_output(self):
        out = self.root / 'joined.png'
        with self.assertRaises(OSError):
            module.stitch([self.first, self.root / 'missing.png'], out)
        self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
