"""Exercise real publish/registration against an external CLI transport double.

Only the remote transport and local lint subprocess are simulated. The CLI
double implements the documented append/before-slide-id semantics; all files,
locks, pending intents, ACK decisions and registrations are production code.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET


MODULE = Path(os.environ.get('PAGE_INSERTION_MODULE', Path(__file__).parents[1] / 'template' / 'template_publish.py'))
spec = importlib.util.spec_from_file_location('page_insertion_under_test', MODULE)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class CliTransport:
    def __init__(self):
        self.slides = []
        self.writes = []
        self.outcome = 'ack'

    def __call__(self, argv, **kwargs):
        if len(argv) > 1 and Path(argv[1]).name == 'template_lint_all.py':
            return subprocess.CompletedProcess(argv, 0, json.dumps({'ok': True, 'status': 'ready_to_write'}), '')
        if argv[:2] != ['lark-cli', 'slides']:
            raise AssertionError('Unexpected external command: ' + repr(argv))
        if argv[2] == '+xml-get':
            if argv[argv.index('--presentation') + 1] != 'test-deck' or '--json' not in argv:
                raise AssertionError('Missing documented read arguments')
            slides = ''.join('<slide id="' + s['id'] + '"><data>' + str(s['page']) + '</data></slide>'
                             for s in self.slides)
            if '--slide-id' in argv:
                sid = argv[argv.index('--slide-id') + 1]
                slide = next(s for s in self.slides if s['id'] == sid)
                document = {'slide': {'content': '<slide id="' + sid + '"><data>' + str(slide['page']) + '</data></slide>'}}
            else:
                document = {'xml_presentation': {'content': '<presentation id="test-deck">' + slides + '</presentation>'}}
            response = {'ok': True, 'data': {'xml_presentation_id': 'test-deck', **document}}
            return subprocess.CompletedProcess(argv, 0, json.dumps(response), '')
        self.writes.append(list(argv))
        self.assert_arguments(argv)
        payload = ET.fromstring(kwargs['input'])
        number = int(payload.find('data').text)
        before = argv[argv.index('--before-slide-id') + 1] if '--before-slide-id' in argv else None
        if self.outcome == 'lint_reject':
            self.outcome = 'ack'
            response = {'ok': False, 'error': {'code': 4000153, 'message': 'Test server lint rejection'}}
            return subprocess.CompletedProcess(argv, 0, json.dumps(response), '')
        if before is not None and before not in [s['id'] for s in self.slides]:
            return subprocess.CompletedProcess(argv, 0, json.dumps({'ok': False, 'error': {'code': 'missing_anchor'}}), '')
        if argv[2] == '+update-slide':
            sid = argv[argv.index('--slide-id') + 1]
            next(s for s in self.slides if s['id'] == sid)['page'] = number
        else:
            sid = 'sid-' + str(number)
            slide = {'id': sid, 'page': number}
            if before is None:
                self.slides.append(slide)
            else:
                self.slides.insert(next(i for i, s in enumerate(self.slides) if s['id'] == before), slide)
        if self.outcome == 'timeout_after_write':
            self.outcome = 'ack'
            raise subprocess.TimeoutExpired(argv, kwargs['timeout'])
        returned = 'wrong-deck' if self.outcome == 'wrong_deck_ack' else 'test-deck'
        returned_id = 'wrong-slide' if self.outcome == 'wrong_slide_ack' else sid
        self.outcome = 'ack'
        response = {'ok': True, 'identity': 'user', 'data': {
            'xml_presentation_id': returned, 'slide_id': returned_id,
            'revision_id': len(self.writes), 'before_slide_id': before,
            'images_uploaded': 0,
        }}
        return subprocess.CompletedProcess(argv, 0, json.dumps(response), '')

    @staticmethod
    def assert_arguments(argv):
        if argv[2] not in ['+add-slide', '+update-slide']:
            raise AssertionError('Unexpected write command')
        if argv[argv.index('--presentation') + 1] != 'test-deck' or '--json' not in argv:
            raise AssertionError('Missing documented envelope arguments')
        content_flag = '--content' if argv[2] == '+update-slide' else '--slide'
        if argv[argv.index(content_flag) + 1] != '-':
            raise AssertionError('Payload must use stdin')


class InsertionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.transport = CliTransport()

    def publish(self, page, **kwargs):
        xml = self.work / ('page-' + str(page) + '.xml')
        xml.write_text('<slide><data>' + str(page) + '</data></slide>')
        return api.publish(presentation='test-deck', xml=xml, page=page,
                           mode='active_rebuild', work_dir=self.work,
                           link='L4', runner=self.transport, **kwargs)

    def registry(self):
        return json.loads((self.work / 'published-pages.json').read_text())['pages']

    def assert_published(self, page):
        result = self.publish(page)
        self.assertEqual(result['status'], 'published')
        return result

    def test_retry_page_four_goes_before_successful_page_five(self):
        for page in [2, 3, 5, 4]:
            self.assert_published(page)
        self.assertEqual([s['page'] for s in self.transport.slides], [2, 3, 4, 5])
        self.assertIn('--before-slide-id', self.transport.writes[-1])
        self.assertEqual(self.transport.writes[-1][-3:], ['--before-slide-id', 'sid-5', '--json'])
        self.assertEqual([r['page'] for r in self.registry()], [2, 3, 4, 5])

    def test_round_three_retry_sequence_preserves_all_physical_positions(self):
        for page in [1, 2, 3, 5, 4, 6, 8, 10, 12, 13, 14, 7, 11, 9]:
            self.assert_published(page)
        self.assertEqual([s['page'] for s in self.transport.slides],
                         [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
        self.assertEqual([r['page'] for r in self.registry()],
                         [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])

    def test_new_page_uses_nearest_greater_acknowledged_page(self):
        for page in [2, 5, 10, 4]:
            self.assert_published(page)
        command = self.transport.writes[-1]
        self.assertIn('--before-slide-id', command)
        self.assertEqual(command[command.index('--before-slide-id') + 1], 'sid-5')
        self.assertEqual([s['page'] for s in self.transport.slides], [2, 4, 5, 10])

    def test_update_existing_id_keeps_position_and_never_sends_insert_argument(self):
        for page in [2, 3, 5, 4]:
            self.assert_published(page)
        original_ids = [s['id'] for s in self.transport.slides]
        self.assert_published(3)
        self.assertEqual([s['id'] for s in self.transport.slides], original_ids)
        self.assertEqual(self.transport.writes[-1][2], '+update-slide')
        self.assertNotIn('--before-slide-id', self.transport.writes[-1])
        self.assertEqual(len(self.registry()), 4)

    def test_timeout_after_insert_keeps_pending_and_blocks_second_write(self):
        self.assert_published(5)
        self.transport.outcome = 'timeout_after_write'
        result = self.publish(4)
        self.assertEqual(result['status'], 'write_unknown')
        self.assertEqual([r['page'] for r in self.registry()], [5])
        pending = self.work / 'published-pages.pending.json'
        self.assertTrue(pending.exists())
        report = json.loads(Path(result['report_path']).read_text())
        self.assertIn('--before-slide-id', report['write']['command'])
        before = len(self.transport.writes)
        self.assertEqual(self.publish(6)['status'], 'recovery_required')
        self.assertEqual(len(self.transport.writes), before)
        self.assertEqual([s['page'] for s in self.transport.slides], [4, 5])

    def test_wrong_deck_ack_is_unknown_and_not_registered(self):
        self.assert_published(5)
        self.transport.outcome = 'wrong_deck_ack'
        result = self.publish(4)
        self.assertEqual(result['status'], 'write_unknown')
        self.assertEqual([r['page'] for r in self.registry()], [5])
        self.assertTrue((self.work / 'published-pages.pending.json').exists())

    def test_update_ack_for_another_slide_keeps_original_registration_and_pending(self):
        self.assert_published(5)
        self.transport.outcome = 'wrong_slide_ack'
        result = self.publish(5)
        self.assertEqual(result['status'], 'write_unknown')
        self.assertEqual(self.registry()[0]['slide_id'], 'sid-5')
        pending = json.loads((self.work / 'published-pages.pending.json').read_text())
        self.assertEqual(pending['slide_id'], 'sid-5')
        self.assertEqual(pending['operation'], 'update')

    def test_missing_anchor_rejection_does_not_append_or_register_page(self):
        self.assert_published(5)
        self.transport.slides.clear()  # A remote edit removes the insertion anchor.
        result = self.publish(4)
        self.assertEqual(result['status'], 'write_rejected')
        self.assertEqual(self.transport.slides, [])
        self.assertEqual([r['page'] for r in self.registry()], [5])
        self.assertFalse((self.work / 'published-pages.pending.json').exists())

    def test_explicit_wrong_target_still_refuses_without_a_remote_write(self):
        self.assert_published(5)
        before = len(self.transport.writes)
        result = self.publish(5, slide_id='wrong-slide')
        self.assertEqual(result['status'], 'invalid_input')
        self.assertEqual(len(self.transport.writes), before)
        self.assertEqual([s['page'] for s in self.transport.slides], [5])

    def exception_file(self, rejection):
        evidence = self.work / 'reviewed-page.png'
        evidence.write_bytes(b'test-fixture-image')
        definition = self.work / 'exception.json'
        definition.write_text(json.dumps({'rejection_report': rejection['report_path'],
                                         'reason': 'Test fixture: reviewed the rejected page layout.',
                                         'visual_evidence': str(evidence)}))
        return definition

    def test_insert_exception_matches_original_anchor_and_request(self):
        self.assert_published(5)
        self.transport.outcome = 'lint_reject'
        rejected = self.publish(4)
        self.assertEqual(rejected['status'], 'write_rejected')
        result = self.publish(4, exception_file=self.exception_file(rejected))
        self.assertEqual(result['status'], 'published')
        self.assertEqual([s['page'] for s in self.transport.slides], [4, 5])
        self.assertIn('--before-slide-id', self.transport.writes[-1])
        self.assertIn('--no-lint', self.transport.writes[-1])

    def test_insert_exception_refuses_when_another_ack_changes_the_anchor(self):
        self.assert_published(5)
        self.transport.outcome = 'lint_reject'
        rejected = self.publish(2)
        self.assertEqual(rejected['status'], 'write_rejected')
        self.assert_published(3)
        before = len(self.transport.writes)
        result = self.publish(2, exception_file=self.exception_file(rejected))
        self.assertEqual(result['status'], 'invalid_input')
        self.assertEqual(len(self.transport.writes), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
