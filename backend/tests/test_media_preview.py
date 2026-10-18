import hashlib
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
import backend.app as api


class PreviewTests(unittest.TestCase):
    def preview(self, content, media_type='Video', digest=None, missing=False, outside=False):
        with tempfile.TemporaryDirectory(dir=api.ROOT) as temp:
            root = Path(temp)
            folder = root/'evidence'/hashlib.sha256(b'CASE-A').hexdigest()[:20]
            folder.mkdir(parents=True)
            path = (root if outside else folder)/'sample.bin'
            path.write_bytes(content)
            row = None if missing else {'stored_path':str(path),'media_type':media_type,'sha256':digest or hashlib.sha256(content).hexdigest()}
            class DB:
                def execute(self, *args):
                    return self
                def fetchone(self):
                    return row
            @contextmanager
            def connect():
                yield DB()
            with patch.object(api,'DATA_ROOT',root), patch.object(api,'connect',connect), patch.object(api,'get_case',return_value={}):
                return api.preview_media('CASE-A','ART-A')

    def test_mp4_signature_and_hash(self):
        response = self.preview(b'\x00\x00\x00\x18ftypisomtest')
        self.assertEqual(response.media_type,'video/mp4')
        self.assertEqual(response.headers['x-content-type-options'],'nosniff')

    def test_html_cannot_be_previewed_as_video(self):
        with self.assertRaises(HTTPException) as error:
            self.preview(b'<html><script>alert(1)</script>')
        self.assertEqual(error.exception.status_code,422)

    def test_integrity_mismatch_blocks_preview(self):
        with self.assertRaises(HTTPException) as error:
            self.preview(b'\x00\x00\x00\x18ftypisomtest',digest='0'*64)
        self.assertEqual(error.exception.status_code,409)

    def test_missing_case_artifact_is_not_served(self):
        with self.assertRaises(HTTPException) as error:
            self.preview(b'anything',missing=True)
        self.assertEqual(error.exception.status_code,404)

    def test_path_outside_case_is_not_served(self):
        with self.assertRaises(HTTPException) as error:
            self.preview(b'anything',outside=True)
        self.assertEqual(error.exception.status_code,404)
