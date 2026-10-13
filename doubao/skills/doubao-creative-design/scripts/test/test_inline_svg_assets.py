#!/usr/bin/env python3
"""Contract tests for the portable SVG assembly step."""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote

SCRIPT = Path(__file__).resolve().parents[1] / 'runtime/inline-svg-assets.py'
spec = importlib.util.spec_from_file_location('svg_assets', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SVG = '<svg xmlns="http://www.w3.org/2000/svg"><filter id="n"/><path fill="#abc" filter="url(#n)" d="M0 0h2v2z"/></svg>'


class InlineAssetsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='svg package ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.assets = self.root / 'assets'
        (self.assets / 'svg').mkdir(parents=True)
        (self.assets / 'svg/paper.svg').write_text(SVG)

    def test_css_html_and_escaped_inline_style_share_asset(self):
        source = '<img src="asset:svg/paper.svg"><b style="background:url(&quot;asset:svg/paper.svg&quot;)"></b>'
        out, stats = module.inline_assets(source, self.assets)
        self.assertNotIn('asset:', out)
        self.assertEqual(stats, {'references': 2, 'unique_assets': 1, 'inline_svgs': 0})
        uri = out.split('src="')[1].split('"')[0]
        self.assertEqual(unquote(uri.split(',', 1)[1]), SVG)
        self.assertIn('%23abc', out)

    def test_reprocessing_final_output_is_idempotent(self):
        out, _ = module.inline_assets('url("asset:svg/paper.svg")', self.assets)
        second, stats = module.inline_assets(out, self.assets)
        self.assertEqual(out, second)
        self.assertEqual(stats['references'], 0)

    def test_rejects_missing_malformed_and_non_svg(self):
        for ref in ['svg/missing.svg', '../secret.svg', '/tmp/file.svg', 'svg/paper.svg?x=1', 'svg/paper.xml']:
            with self.subTest(ref=ref), self.assertRaises((ValueError, OSError)):
                module.inline_assets(f'url("asset:{ref}")', self.assets)
        (self.assets / 'svg/bad.svg').write_text('<html/>')
        with self.assertRaises(ValueError):
            module.inline_assets('asset:svg/bad.svg', self.assets)

    def test_rejects_symlink_outside_package(self):
        outside = self.root / 'outside.svg'
        outside.write_text(SVG)
        (self.assets / 'svg/escape.svg').symlink_to(outside)
        with self.assertRaises(ValueError):
            module.inline_assets('asset:svg/escape.svg', self.assets)

    def test_rejects_external_svg_dependencies(self):
        for content in ['<image href="https://example.com/x.png"/>', '<style>rect{fill:url(https://example.com/x.svg)}</style>', '<style>@import "remote.css";</style>']:
            (self.assets / 'svg/external.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg">'+content+'</svg>')
            with self.subTest(content=content), self.assertRaises(ValueError):
                module.inline_assets('asset:svg/external.svg', self.assets)

    def test_cli_relocated_package_and_failure_preserves_output(self):
        scripts = self.root / 'scripts/runtime'
        scripts.mkdir(parents=True)
        relocated = scripts / SCRIPT.name
        relocated.write_bytes(SCRIPT.read_bytes())
        source, output = self.root / 'draft.html', self.root / 'final.html'
        source.write_text('<img src="asset:svg/paper.svg">')
        run = lambda *extra: subprocess.run([sys.executable, str(relocated), '--input', str(source), '--output', str(output), *extra], cwd='/', capture_output=True, text=True)
        first = run()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertNotIn('data:image', first.stdout)
        expected = output.read_bytes()
        self.assertNotEqual(run().returncode, 0)
        source.write_text('<img src="asset:svg/missing.svg">')
        self.assertNotEqual(run('--force').returncode, 0)
        self.assertEqual(output.read_bytes(), expected)

    def test_cli_refuses_to_overwrite_input(self):
        source = self.root / 'draft.html'
        source.write_text('asset:svg/paper.svg')
        result = subprocess.run([sys.executable, str(SCRIPT), '--input', str(source), '--output', str(source), '--force'], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(source.read_text(), 'asset:svg/paper.svg')


    def test_inline_dom_keeps_text_and_scopes_duplicate_instances(self):
        import xml.etree.ElementTree as ET
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><defs><path id="abc" d="M0 10Q50 0 100 10"/></defs><text fill="#abc"><textPath href="#abc">文字 &amp; 标题</textPath></text></svg>'
        (self.assets / 'svg/arc.svg').write_text(svg)
        source = '<!-- svg-inline:svg/arc.svg --><!-- svg-inline:svg/arc.svg -->'
        out, summary = module.inline_assets(source, self.assets)
        root = ET.fromstring('<root>'+out+'</root>')
        ids = [n.get('id') for n in root.iter() if n.get('id')]
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(set(ids)), 2)
        paths = root.findall('.//{http://www.w3.org/2000/svg}textPath')
        self.assertEqual([n.get('href') for n in paths], ['#'+x for x in ids])
        self.assertEqual([n.text for n in paths], ['文字 & 标题']*2)
        self.assertEqual(root.find('.//{http://www.w3.org/2000/svg}text').get('fill'), '#abc')
        self.assertEqual(summary['inline_svgs'], 2)
        self.assertEqual(summary['unique_assets'], 1)
        self.assertNotIn('data:image', out)

    def test_inline_dom_rejects_unresolved_or_external_assets(self):
        with self.assertRaises(ValueError):
            module.inline_assets('<!-- svg-inline: -->', self.assets)
        (self.assets / 'svg/network.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.com/a.png"/></svg>')
        with self.assertRaises(ValueError):
            module.inline_assets('<!-- svg-inline:svg/network.svg -->', self.assets)

    def test_arc_generator_escapes_text_and_validates_geometry(self):
        import xml.etree.ElementTree as ET
        arc_spec = importlib.util.spec_from_file_location('arc', SCRIPT.with_name('make-text-arc.py'))
        arc = importlib.util.module_from_spec(arc_spec)
        arc_spec.loader.exec_module(arc)
        root = ET.fromstring(arc.build('A & <中文>', rise=30))
        self.assertEqual(root.find('.//{http://www.w3.org/2000/svg}textPath').text, 'A & <中文>')
        self.assertEqual(root.find('.//{http://www.w3.org/2000/svg}path').get('d'), 'M24 100Q160 40 296 100')
        for options in [{'rise':100}, {'width':0}, {'inset':160}, {'rise':float('nan')}]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                arc.build('标题', **options)


if __name__ == '__main__':
    unittest.main()
