"""Security hardening tests for updater."""

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.updater import UpdateChecker


class TestUpdaterSecurity(unittest.TestCase):
    def test_extract_release_hashes_supports_common_formats(self):
        notes = """
        SHA256:
        e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
        WhisperLocalSetup.exe: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
        bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb *WhisperLocalPortable.exe
        """
        hashes = UpdateChecker._extract_release_hashes(notes)
        self.assertEqual(
            hashes.get("whisperlocalsetup.exe"),
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        )
        self.assertEqual(
            hashes.get("whisperlocalportable.exe"),
            "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        )
        self.assertEqual(
            hashes.get("__default__"),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

    def test_verify_installer_requires_hash_and_validates_digest(self):
        checker = UpdateChecker(cache_dir=tempfile.mkdtemp())
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"x" * (1024 * 1024 + 32))
            tmp_path = tmp.name

        try:
            file_hash = hashlib.sha256(Path(tmp_path).read_bytes()).hexdigest()
            self.assertFalse(checker.verify_installer(tmp_path, expected_hash=None))
            self.assertFalse(checker.verify_installer(tmp_path, expected_hash="bad"))
            self.assertTrue(checker.verify_installer(tmp_path, expected_hash=file_hash))
        finally:
            os.remove(tmp_path)

    def test_download_refuses_without_hash_metadata(self):
        checker = UpdateChecker(cache_dir=tempfile.mkdtemp())
        ok, err = checker.download_update(
            "https://example.com/fake-installer.exe",
            os.path.join(tempfile.gettempdir(), "fake-installer.exe"),
            expected_hash=None,
        )
        self.assertFalse(ok)
        self.assertIn("without SHA256 metadata", err or "")


if __name__ == "__main__":
    unittest.main()
