"""The 1.0.5-beta.7 WhisperLocal -> Impulse rename must carry existing user data forward."""

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import importlib

config = importlib.import_module("whisper_local.config")


class DataDirMigrationTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.appdata = self._tmp.name
        self.legacy = os.path.join(self.appdata, "WhisperLocal")
        self.current = os.path.join(self.appdata, "Impulse")
        patcher = mock.patch.dict(os.environ, {"LOCALAPPDATA": self.appdata})
        patcher.start()
        self.addCleanup(patcher.stop)
        frozen = mock.patch.object(config, "is_frozen", return_value=True)
        frozen.start()
        self.addCleanup(frozen.stop)
        self.addCleanup(self._tmp.cleanup)

    def _seed_legacy(self):
        os.makedirs(os.path.join(self.legacy, "state"), exist_ok=True)
        with open(os.path.join(self.legacy, "state", "license.json"), "w") as f:
            f.write('{"active": true}')

    def test_legacy_data_is_adopted(self):
        """An existing WhisperLocal install keeps its license after the rename."""
        self._seed_legacy()

        resolved = config.get_user_data_dir()

        self.assertEqual(resolved, self.current)
        self.assertTrue(os.path.exists(os.path.join(self.current, "state", "license.json")))
        self.assertFalse(os.path.isdir(self.legacy))

    def test_fresh_install_creates_impulse_dir(self):
        resolved = config.get_user_data_dir()

        self.assertEqual(resolved, self.current)
        for rel in ("logs", "audio", "transcripts", "state"):
            self.assertTrue(os.path.isdir(os.path.join(self.current, rel)))

    def test_existing_impulse_dir_wins_over_legacy(self):
        """Once migrated, a stale legacy dir must never clobber real data."""
        self._seed_legacy()
        os.makedirs(os.path.join(self.current, "state"), exist_ok=True)
        with open(os.path.join(self.current, "state", "license.json"), "w") as f:
            f.write('{"active": "current"}')

        resolved = config.get_user_data_dir()

        self.assertEqual(resolved, self.current)
        with open(os.path.join(self.current, "state", "license.json")) as f:
            self.assertIn("current", f.read())
        self.assertTrue(os.path.isdir(self.legacy))

    def test_migration_failure_falls_back_to_legacy(self):
        """If the rename is blocked, keep using the old dir rather than losing the license."""
        self._seed_legacy()

        with mock.patch("os.rename", side_effect=OSError("locked")):
            resolved = config.get_user_data_dir()

        self.assertEqual(resolved, self.legacy)
        self.assertTrue(os.path.exists(os.path.join(self.legacy, "state", "license.json")))


if __name__ == "__main__":
    unittest.main()
