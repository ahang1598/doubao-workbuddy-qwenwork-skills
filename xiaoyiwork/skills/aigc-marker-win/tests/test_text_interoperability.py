"""Regression checks for metadata types and HTML marking/migration."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from decorators.common import get_aigc_signature, is_aigc_complete
from decorators.html_decorator import HtmlAigcDecorator, inspect_html

TEXT = "内容由AI生成"


class TextInteroperabilityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "sample.html"
        self.marker = HtmlAigcDecorator()

    def write(self, text):
        self.path.write_text(text, encoding="utf-8")

    def test_generated_metadata_contains_all_seven_string_fields(self):
        data = json.loads(get_aigc_signature("synthetic test"))
        self.assertEqual(set(data), {"Label", "ContentProducer", "ProduceID", "ReservedCode1",
                                     "ContentPropagator", "PropagateID", "ReservedCode2"})
        self.assertTrue(all(isinstance(v, str) for v in data.values()))
        self.assertTrue(is_aigc_complete(data))

    def test_non_string_fields_and_unknown_label_are_not_treated_as_valid(self):
        data = json.loads(get_aigc_signature("synthetic test"))
        for field, value in [("Label", "9"), ("Label", 1), ("ProduceID", []),
                             ("ContentProducer", True), ("PropagateID", "  "), ("ReservedCode2", {})]:
            with self.subTest(field=field, value=value):
                self.assertFalse(is_aigc_complete({**data, field: value}))

    def test_html_implicit_then_visible_upgrade_and_repeat_preserve_content_and_ids(self):
        original = '<!doctype html><html><head><title>Original</title></head><body><p>中文 &amp; content</p></body></html>'
        self.write(original)
        self.marker.decorate(self.path, "synthetic test", False)
        metadata = self.marker._get_aigc_data(self.path)
        self.assertTrue(is_aigc_complete(metadata))
        self.assertNotIn(TEXT, self.path.read_text())
        self.marker.decorate(self.path, "new digest", True)
        self.assertEqual(metadata, self.marker._get_aigc_data(self.path))
        snapshot = self.path.read_bytes()
        self.assertIn(b'content</p>', snapshot)
        self.assertIn('<title>Original</title>', self.path.read_text())
        self.assertEqual(self.path.read_text().count(TEXT), 1)
        self.marker.decorate(self.path, "new digest", True)
        self.assertEqual(snapshot, self.path.read_bytes())

    def test_html_metadata_is_real_json_and_quote_values_roundtrip(self):
        data = json.loads(get_aigc_signature("synthetic test"))
        data["ProduceID"] = 'id-with-"quotes"-&-中文'
        import html
        self.write('<html><head><meta name="AIGC" content="' + html.escape(json.dumps(data), quote=True) + '"></head><body>original</body></html>')
        self.marker.decorate(self.path, "new digest")
        self.assertEqual(self.marker._get_aigc_data(self.path), data)

    def test_label_in_head_script_comment_or_hidden_content_does_not_skip_footer(self):
        for fragment in [f'<title>{TEXT}</title>', f'<script>const text = "{TEXT}";</script>',
                         f'<!--{TEXT}-->', f'<div hidden>{TEXT}</div>', f'<div style="display:none">{TEXT}</div>']:
            with self.subTest(fragment=fragment):
                self.write('<html><head></head><body>' + fragment + '</body></html>')
                self.marker.decorate(self.path, "synthetic test")
                self.assertIn('data-aigc-marker="visible"', self.path.read_text())
                self.assertIn(TEXT, ''.join(inspect_html(self.path.read_text()).text))

    def test_meta_examples_inside_comments_and_scripts_are_preserved(self):
        example = '<meta name="AIGC" content="not-real-metadata">'
        script = '<script>const sample = ' + json.dumps(example) + ';</script>'
        comment = '<!--' + example + '-->'
        self.write('<html><head>' + script + comment + '</head><body>Original</body></html>')
        self.marker.decorate(self.path, "synthetic test")
        text = self.path.read_text()
        self.assertIn(script, text)
        self.assertIn(comment, text)
        self.assertTrue(is_aigc_complete(self.marker._get_aigc_data(self.path)))

    def test_invalid_or_duplicate_actual_metadata_tags_are_repaired(self):
        self.write('<html><head><meta name="AIGC" content="invalid"><meta NAME="aigc" content="invalid"></head><body>Original</body></html>')
        self.marker.decorate(self.path, "synthetic test")
        parsed = inspect_html(self.path.read_text())
        self.assertTrue(is_aigc_complete(parsed.metadata))
        self.assertEqual(len(parsed.meta_positions), 1)

    def test_missing_head_is_created_without_dropping_doctype_or_body(self):
        self.write('<!doctype html><html><body>Original</body></html>')
        self.marker.decorate(self.path, "synthetic test")
        text = self.path.read_text()
        self.assertTrue(text.startswith('<!doctype html>'))
        self.assertLess(text.index('<head>'), text.index('<body>'))
        self.assertIn('Original', text)

    def test_markdown_invalid_numeric_label_is_repaired_as_a_string(self):
        from decorators.md_decorator import MdAigcDecorator
        path = self.path.with_suffix(".md")
        data = json.loads(get_aigc_signature("synthetic test"))
        header = "AIGC:\n" + "\n".join("  " + key + ": " + ("1" if key == "Label" else json.dumps(value)) for key, value in data.items())
        path.write_text("---\n" + header + "\n---\n# Original\n", encoding="utf-8")
        marker = MdAigcDecorator()
        self.assertFalse(is_aigc_complete(marker._get_aigc_data(path)))
        marker.decorate(path, "synthetic test")
        self.assertEqual(marker._get_aigc_data(path)["Label"], "1")
        self.assertIn('# Original', path.read_text())
        self.assertTrue(path.read_text().rstrip().endswith(TEXT))

    def test_html_cli_supports_metadata_only_and_visible_upgrade(self):
        self.write('<html><head></head><body>Original</body></html>')
        for hidden in (True, False):
            result = subprocess.run([sys.executable, '-B', str(SCRIPTS / 'main.py'), str(self.path)] +
                                    (['--skip-visible'] if hidden else []), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('AIGC_MARKER_OK:', result.stdout)
            self.assertTrue(is_aigc_complete(self.marker._get_aigc_data(self.path)))


if __name__ == '__main__':
    unittest.main()
