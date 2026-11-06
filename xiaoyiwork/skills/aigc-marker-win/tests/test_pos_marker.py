"""ProcessOn package metadata regression checks."""
import io
import json
from pathlib import Path
import sys
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from decorators.common import get_aigc_signature, is_aigc_complete
from decorators.pos_decorator import metadata_update


class PosMetadataTests(unittest.TestCase):
    def archive(self, meta):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            if meta is not None:
                archive.writestr('meta.json', json.dumps(meta, ensure_ascii=False))
            archive.writestr('resource.bin', b'unchanged')
        return zipfile.ZipFile(buffer)

    def test_missing_metadata_is_created_with_seven_string_fields(self):
        with self.archive(None) as archive:
            result = json.loads(metadata_update(archive, 'synthetic'))
        data = json.loads(result['AIGC'])
        self.assertTrue(is_aigc_complete(data))
        self.assertEqual(len(data), 7)
        self.assertTrue(all(isinstance(value, str) for value in data.values()))

    def test_provenance_and_unrelated_metadata_are_preserved(self):
        identity = json.loads(get_aigc_signature('original'))
        identity['ReservedCode1'] = 'existing-signature'
        for value in (identity, json.dumps(identity)):
            with self.subTest(value=value):
                with self.archive({'version':'5.0', 'vendor':{'key':'keep'}, 'AIGC':value}) as archive:
                    result = json.loads(metadata_update(archive, 'different'))
                self.assertEqual(json.loads(result['AIGC']), identity)
                self.assertEqual(result['version'], '5.0')
                self.assertEqual(result['vendor'], {'key':'keep'})

    def test_invalid_metadata_container_is_rejected(self):
        with self.archive([]) as archive:
            with self.assertRaisesRegex(ValueError, 'must contain an object'):
                metadata_update(archive, 'synthetic')

    def test_duplicate_json_keys_are_rejected(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('meta.json', '{"version":"1","version":"2"}')
        with zipfile.ZipFile(buffer) as archive:
            with self.assertRaisesRegex(ValueError, 'Duplicate ProcessOn JSON key'):
                metadata_update(archive, 'synthetic')


if __name__ == '__main__':
    unittest.main()
