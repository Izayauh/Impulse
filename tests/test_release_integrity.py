"""Static contracts that keep the Windows release path aligned with Impulse."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def require_match(test_case: unittest.TestCase, pattern: str, text: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    test_case.assertIsNotNone(match, f"Expected pattern not found: {pattern}")
    return match.group(1)


class ReleaseIntegrityTests(unittest.TestCase):
    def test_checked_in_versions_match(self):
        versions = {
            "runtime config": require_match(
                self, r'^APP_VERSION\s*=\s*"([^"]+)"', read("src/whisper_local/config.py")
            ),
            "package metadata": require_match(
                self, r'^version\s*=\s*"([^"]+)"', read("pyproject.toml")
            ),
            "split installer": require_match(
                self, r'^#define MyAppVersion\s+"([^"]+)"', read("scripts/release/installer.iss")
            ),
            "bootstrap installer": require_match(
                self,
                r'^#define MyAppVersion\s+"([^"]+)"',
                read("scripts/release/bootstrap_installer.iss"),
            ),
            "PyInstaller spec": require_match(
                self, r"^APP_VERSION\s*=\s*'([^']+)'", read("scripts/release/build_config.spec")
            ),
        }

        self.assertEqual(
            len(set(versions.values())),
            1,
            "Release versions disagree: "
            + ", ".join(f"{name}={version}" for name, version in versions.items()),
        )

    def test_fresh_machine_qa_looks_for_current_product(self):
        script = read("scripts/qa/fresh-machine-test.ps1")
        self.assertIn("Get-Process -Name 'Impulse'", script)
        self.assertIn("Programs\\Impulse", script)
        self.assertIn("Join-Path $appDir 'Impulse.exe'", script)
        self.assertNotIn("Programs\\WhisperLocal", script)
        self.assertNotIn("Join-Path $appDir 'WhisperLocal.exe'", script)

    def test_local_build_requires_the_same_runtime_shape_as_ci(self):
        script = read("scripts/release/build_installer.ps1")
        self.assertIn("Impulse.ico", script)
        self.assertIn('$model = "ggml-base.en.bin"', script)
        self.assertIn('-Filter "ggml-cpu*.dll"', script)
        self.assertNotIn("Whisper.ico", script)
        self.assertNotIn("ggml-medium.en.bin", script)
        self.assertNotIn("ggml-large-v3.bin", script)

    def test_bootstrap_payload_discovers_runtime_variants(self):
        generator = read("scripts/release/generate_bootstrap_payload.ps1")
        installer = read("scripts/release/bootstrap_installer.iss")
        self.assertIn('-Filter "ggml-cpu*.dll"', generator)
        self.assertIn("_internal\\models\\ggml-base.en.bin", generator)
        self.assertNotIn("ggml-medium.en.bin", generator)
        self.assertNotIn("ggml-large-v3.bin", generator)
        self.assertIn("_internal\\ggml*.dll", installer)

    def test_pull_requests_build_without_publishing_a_release(self):
        workflow = read(".github/workflows/release.yml")
        self.assertIn("pull_request:", workflow)
        self.assertIn("Upload PR installer smoke artifact", workflow)
        self.assertIn("github.event_name != 'pull_request'", workflow)
        self.assertIn("retention-days: 3", workflow)

    def test_public_release_material_uses_current_repository_and_safe_controls(self):
        public_release_files = (
            "README.md",
            "BETA_RELEASE_CHECKLIST.md",
            ".github/RELEASE_INSTRUCTIONS.md",
            ".github/workflows/release.yml",
            "scripts/release/create_release_package.ps1",
        )
        for relative_path in public_release_files:
            with self.subTest(path=relative_path):
                content = read(relative_path)
                self.assertNotIn("github.com/Izayauh/whisper", content)
                self.assertNotIn("WHISPER_DEV_BYPASS_LICENSE", content)


if __name__ == "__main__":
    unittest.main()
