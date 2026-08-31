"""The release gate is only worth as much as its assertions.

verify_package.py is what stands between a broken frozen build and a published
installer, and it runs on a tag, where nobody is watching. These tests pin the
two things that would let it pass a broken build silently: a transcript check
that accepts anything, and a manifest that has quietly lost the entries covering
the packaging bugs that actually shipped.
"""

import importlib.util
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "release", "verify_package.py")

_spec = importlib.util.spec_from_file_location("verify_package", SCRIPT)
verify_package = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify_package)


class WordRecallTest(unittest.TestCase):
    def test_exact_match_is_total_recall(self):
        phrase = verify_package.SAMPLE_PHRASE
        self.assertEqual(verify_package.word_recall(phrase, phrase), 1.0)

    def test_recall_ignores_case_punctuation_and_order(self):
        self.assertEqual(
            verify_package.word_recall(
                "the quick brown fox",
                "Fox, brown -- QUICK!",
            ),
            1.0,
        )

    def test_empty_transcript_recovers_nothing(self):
        self.assertEqual(verify_package.word_recall("the quick brown fox", ""), 0.0)

    def test_stop_words_alone_do_not_pass(self):
        # An engine that returns filler must not clear the bar on filler.
        recall = verify_package.word_recall(verify_package.SAMPLE_PHRASE, "the the and a an over")
        self.assertLess(recall, verify_package.MIN_WORD_RECALL)

    def test_partial_transcript_is_scored_proportionally(self):
        # Content words are: quick brown fox jumps lazy dog
        recall = verify_package.word_recall(verify_package.SAMPLE_PHRASE, "quick brown fox")
        self.assertAlmostEqual(recall, 0.5)

    def test_threshold_is_not_trivially_satisfiable(self):
        self.assertGreater(verify_package.MIN_WORD_RECALL, 0.0)


class ParseReportTest(unittest.TestCase):
    def test_report_is_found_among_progress_logging(self):
        stdout = (
            "[whisper-smart] Route: faster-whisper base (mode=auto)\n"
            "[faster-whisper] base preload complete device=cpu compute=int8\n"
            '{"ok": true, "model": "faster-whisper-base.en", "transcript": "hello"}\n'
        )
        report = verify_package._parse_report(stdout)
        self.assertIsNotNone(report)
        self.assertTrue(report["ok"])
        self.assertEqual(report["transcript"], "hello")

    def test_unparseable_output_yields_no_report(self):
        self.assertIsNone(verify_package._parse_report("Traceback (most recent call last):"))

    def test_empty_output_yields_no_report(self):
        self.assertIsNone(verify_package._parse_report(""))

    def test_json_without_an_ok_field_is_not_the_report(self):
        self.assertIsNone(verify_package._parse_report('{"some": "other object"}'))


class SelftestFailureTest(unittest.TestCase):
    """A gate that fails illegibly is a gate someone switches off."""

    def test_missing_executable_is_reported_not_raised(self):
        self.assertEqual(
            verify_package.cmd_selftest(
                os.path.join(REPO_ROOT, "no-such.exe"),
                os.path.abspath(__file__),
                timeout=5,
            ),
            1,
        )

    def test_missing_sample_is_reported_not_raised(self):
        self.assertEqual(
            verify_package.cmd_selftest(
                os.path.abspath(__file__),
                os.path.join(REPO_ROOT, "no-such.wav"),
                timeout=5,
            ),
            1,
        )

    def test_unlaunchable_binary_is_reported_not_raised(self):
        # A real file that Windows cannot start: the shape of a missing DLL or
        # a wrong-architecture build.
        self.assertEqual(
            verify_package.cmd_selftest(
                os.path.abspath(__file__),
                os.path.abspath(__file__),
                timeout=5,
            ),
            1,
        )


class ManifestTest(unittest.TestCase):
    def _build_tree(self, root, skip=()):
        for rel, _why in verify_package.REQUIRED_FILES:
            if rel in skip:
                continue
            path = os.path.join(root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "wb").close()
        # One concrete file per glob family is enough to satisfy the pattern.
        for rel in ("_internal/ggml.dll", "_internal/ggml-cpu-haswell.dll"):
            path = os.path.join(root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "wb").close()

    def test_complete_tree_passes(self):
        import tempfile

        with tempfile.TemporaryDirectory() as root:
            self._build_tree(root)
            self.assertEqual(verify_package.cmd_manifest(root), 0)

    def test_missing_pywebview_bridge_fails(self):
        # The defect that made every dashboard API call return null.
        import tempfile

        with tempfile.TemporaryDirectory() as root:
            self._build_tree(root, skip=("_internal/webview/js/api.js",))
            self.assertEqual(verify_package.cmd_manifest(root), 1)

    def test_missing_offline_model_fails(self):
        import tempfile

        with tempfile.TemporaryDirectory() as root:
            self._build_tree(root, skip=("_internal/models/ggml-base.en.bin",))
            self.assertEqual(verify_package.cmd_manifest(root), 1)

    def test_absent_build_directory_fails(self):
        self.assertEqual(verify_package.cmd_manifest(os.path.join(REPO_ROOT, "no-such-dir")), 1)

    def test_manifest_still_covers_the_bugs_that_shipped(self):
        """Each of these was a real silent failure in a published installer."""
        required = {rel for rel, _why in verify_package.REQUIRED_FILES}
        for rel in (
            "_internal/webview/js/api.js",
            "_internal/whisper_local/ui/dashboard.html",
            "_internal/whisper_local/ui/styles.css",
            "_internal/models/ggml-base.en.bin",
            "_internal/whisper-cli.exe",
        ):
            self.assertIn(rel, required, f"{rel} was dropped from the release gate")


if __name__ == "__main__":
    unittest.main()
