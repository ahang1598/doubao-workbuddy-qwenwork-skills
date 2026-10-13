import contextlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
import resolve_font as resolver
import web_font_check as checker


class WebFontFailureTests(unittest.TestCase):
    def resolve(self, ready=False, check=False):
        args = SimpleNamespace(fetch=False, register_package=None, cache_root=None,
            allow_license_risk=False, weight=700, query='douyin-sans', style='normal',
            check_cdn=check, require_ready=ready, text='邀请函')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = resolver.resolve_html(args)
        return code, json.loads(out.getvalue())

    def test_unchecked_is_not_network_ready(self):
        with patch.object(resolver, 'probe_entry') as probe:
            code, result = self.resolve()
        probe.assert_not_called()
        self.assertEqual(code, 0)
        self.assertEqual(result['package_status'], 'cdn_listed_not_rechecked')
        self.assertEqual(result['coverage_status'], 'not_checked')

    def test_require_ready_probes_and_reports_failure(self):
        for reply in [False, True, 'timeout']:
            with self.subTest(reply=reply):
                kwargs = {'side_effect': TimeoutError('timeout')} if reply == 'timeout' else {'return_value': {'verified': reply}}
                with patch.object(resolver, 'probe_entry', **kwargs) as probe:
                    code, result = self.resolve(ready=True)
                probe.assert_called_once()
                self.assertEqual(code, 0 if reply is True else 4)
                self.assertEqual(result['package_status'], 'cdn_ready' if reply is True else 'cdn_check_failed')

    def test_manifest_failures_are_reported(self):
        for error in [ValueError('invalid manifest'), OSError('missing file')]:
            with patch.object(checker, 'load_web_manifest', side_effect=error):
                self.assertTrue(checker.validate('<html></html>'))

    def test_unverified_face_does_not_crash_or_pass(self):
        with patch.object(checker, 'load_web_manifest', return_value={'families': [{'faces': [{'verified': False}]}]}):
            self.assertTrue(checker.validate('<html></html>'))

    def test_invalid_css_metadata_is_rejected(self):
        family = resolver.select_web_family(resolver.load_web_manifest(), 'douyin-sans')
        face = resolver.select_web_face(family, 700, 'normal')
        for field, value in [('weight', 'bold; color:red'), ('style', 'normal; color:red'), ('weight_range', {'min':900,'max':100})]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                resolver.build_web_font_contract(family, dict(face, **{field:value}))

if __name__ == '__main__':
    unittest.main()
