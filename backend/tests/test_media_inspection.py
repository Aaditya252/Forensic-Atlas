import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import backend.app as api
from backend.media_inspection import inspect_file


class InspectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=api.ROOT)
        self.root = Path(self.temp.name)
        self.path = self.root/'sample.wav'
        self.path.write_bytes(b'RIFF'+b'\0'*4+b'WAVE'+b'\0'*20)
        self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()

    def tearDown(self):
        self.temp.cleanup()

    def inspect(self,digest=None):
        return inspect_file(self.path,self.digest if digest is None else digest,allowed_root=self.root,output_dir=self.root)

    def test_digest_mismatch_blocks_parser(self):
        with patch('backend.media_inspection.subprocess.run') as process:
            result = self.inspect('0'*64)
        self.assertEqual(result['status'],'blocked')
        self.assertFalse(result['integrityMatch'])
        process.assert_not_called()

    def test_playlist_signature_never_runs_parser(self):
        self.path.write_text('#EXTM3U\nhttps://example.invalid/media')
        with patch('backend.media_inspection.subprocess.run') as process:
            result = self.inspect(hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(result['status'],'unsupported')
        process.assert_not_called()

    def test_directory_scope_enforced(self):
        with self.assertRaises(ValueError):
            inspect_file(self.path,self.digest,allowed_root=self.root/'another-case',output_dir=self.root)

    def test_missing_dependency_returns_explicit_gap(self):
        with patch('backend.media_inspection.shutil.which',return_value=None):
            result = self.inspect()
        self.assertEqual(result['status'],'dependency_unavailable')
        self.assertEqual(result['streams'],[])
        self.assertFalse(result['detectorRun'])

    def test_parser_failure_never_substitutes_metadata(self):
        with patch('backend.media_inspection.shutil.which',return_value='ffprobe'), patch('backend.media_inspection.subprocess.run') as process:
            process.return_value.returncode = 1
            result = self.inspect()
        self.assertEqual(result['status'],'failed')
        self.assertIsNone(result['durationSeconds'])
