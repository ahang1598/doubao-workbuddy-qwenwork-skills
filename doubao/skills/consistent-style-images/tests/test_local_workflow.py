"""Local contract tests; no image API calls or brand assets required."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from profile_utils import BASE_REVIEW, load_profile
from check_batch import validate
from compose_poster import compose


class LocalWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='style-skill-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = {'id': 'test-project', 'status': 'ready',
                        'constraints': {}, 'review_rules': [], 'references': [],
                        'assets': {}, 'fonts': {}}
        self.pp = self.write('profile.json', self.profile)
        _, self.fp = load_profile(self.pp)
        self.batch = {'schema_version': 1, 'brand_profile': 'profile.json',
                      'brand_id': 'test-project', 'profile_fingerprint': self.fp,
                      'stage': 'concept', 'expected_count': 1,
                      'style_lock': {'direction': 'test fixture'},
                      'jobs': [{'id': '01', 'width': 32, 'height': 18,
                                'output': 'test.png', 'copy': {},
                                'content_flags': {'text': False, 'cta': False,
                                                  'logo': False, 'visual': True},
                                'status': 'planned'}]}
        self.layout = {'width': 32, 'height': 18, 'output': 'test.png',
                       'brand_profile': 'profile.json', 'brand_id': 'test-project',
                       'profile_fingerprint': self.fp, 'palette': {}, 'levels': {},
                       'lines': [], 'ctas': []}

    def write(self, name, data):
        path = self.root / name
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def check(self, data=None, plan=True):
        return validate(self.write('batch.json', self.batch if data is None else data), plan)

    def test_minimal_profile(self):
        p, fp = load_profile(self.pp)
        self.assertEqual(p['assets'], {})
        self.assertEqual(len(fp), 64)

    def test_no_text_logo_plan(self):
        self.assertTrue(self.check()['ok'])

    def test_invalid_dimensions(self):
        self.batch['jobs'][0]['width'] = 0
        self.assertFalse(self.check()['ok'])

    def test_stale_fingerprint(self):
        self.batch['profile_fingerprint'] = 'old'
        self.assertFalse(self.check()['ok'])

    def test_profile_change_changes_fingerprint(self):
        self.profile['constraints'] = {'cta_required': True}
        self.write('profile.json', self.profile)
        self.assertNotEqual(load_profile(self.pp)[1], self.fp)

    def test_copy_flags_mismatch(self):
        self.batch['jobs'][0]['copy'] = {'headline': 'Test'}
        self.assertFalse(self.check()['ok'])

    def test_duplicate_job(self):
        self.batch['jobs'].append(copy.deepcopy(self.batch['jobs'][0]))
        self.batch['expected_count'] = 2
        self.assertFalse(self.check()['ok'])

    def test_missing_delivery(self):
        self.assertFalse(self.check(plan=False)['ok'])

    def test_render_and_no_overwrite(self):
        path = self.write('layout.json', self.layout)
        result = compose(path)
        self.assertEqual(result['size'], [32, 18])
        self.assertEqual(result['review_status'], 'pending')
        before = (self.root / 'test.png').read_bytes()
        with self.assertRaises(ValueError):
            compose(path)
        self.assertEqual((self.root / 'test.png').read_bytes(), before)

    def test_render_invalid_dimensions(self):
        self.layout['width'] = 0
        with self.assertRaises(ValueError):
            compose(self.write('layout.json', self.layout))
        self.assertFalse((self.root / 'test.png').exists())

    def test_final_records_and_changed_file(self):
        result = compose(self.write('layout.json', self.layout))
        self.batch.update(stage='final', brief={'copy_status': 'authorized_draft',
                         'spec_status': 'confirmed', 'source': 'synthetic test fixture'})
        job = self.batch['jobs'][0]
        job.update(status='passed', tool='test fixture', actual_size=[32, 18],
                   reviewed_sha256=result['sha256'], brand_review={})
        job['review'] = {k: {'status': 'passed' if applies == 'always' or
                         job['content_flags'].get(applies, False) else 'not_applicable',
                         'evidence': 'Synthetic test only; not a real artwork approval'}
                         for k, applies in BASE_REVIEW.items()}
        self.assertTrue(self.check(plan=False)['ok'])
        (self.root / 'test.png').write_bytes(b'changed invalid image')
        self.assertFalse(self.check(plan=False)['ok'])

    def test_malformed_json_cli(self):
        path = self.root / 'invalid.json'
        path.write_text('{', encoding='utf-8')
        for name in ('check_batch.py', 'compose_poster.py', 'profile_utils.py'):
            with self.subTest(script=name):
                result = subprocess.run([sys.executable, str(SCRIPTS / name), str(path)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 1)
                self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
