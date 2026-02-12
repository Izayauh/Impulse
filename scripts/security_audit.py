"""
Security audit script for WhisperLocal.

This script performs automated static checks across the Python codebase:
- Unsafe subprocess usage (shell=True)
- Dangerous execution primitives (eval/exec/os.system)
- Hardcoded secrets
- Basic input/path validation controls
- Network call surface review

Run with: python scripts/security_audit.py
"""

from __future__ import annotations

import re
import sys
import ast
from pathlib import Path


# Fix Windows console encoding for Unicode characters.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        import codecs

        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")


class SecurityAuditor:
    """Automated security audit for WhisperLocal."""

    EXCLUDED_DIRS = {
        ".git",
        ".venv",
        ".vs",
        ".vscode",
        "__pycache__",
        "docs",
        "output",
        "runtime",
        "tmp",
        "tests",
        "whisper.cpp",
    }

    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.self_script_path = Path(__file__).resolve()
        self.scan_roots = [
            self.project_root / "src",
            self.project_root / "scripts",
            self.project_root / "main.py",
            self.project_root / "gui_host.py",
            self.project_root / "post_processor.py",
        ]
        self.files = self._discover_python_files()
        self.contents = self._load_contents()
        self.passed: list[str] = []
        self.failed: list[str] = []
        self.warnings: list[str] = []

    def _discover_python_files(self) -> list[Path]:
        discovered: set[Path] = set()
        for root in self.scan_roots:
            if not root.exists():
                continue
            if root.is_file() and root.suffix == ".py":
                resolved = root.resolve()
                if resolved != self.self_script_path:
                    discovered.add(resolved)
                continue

            for path in root.rglob("*.py"):
                if any(part in self.EXCLUDED_DIRS for part in path.parts):
                    continue
                resolved = path.resolve()
                if resolved == self.self_script_path:
                    continue
                discovered.add(resolved)

        return sorted(discovered)

    def _load_contents(self) -> dict[Path, str]:
        contents: dict[Path, str] = {}
        for path in self.files:
            try:
                contents[path] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                self.warnings.append(f"Could not read {path}: {exc}")
        return contents

    @staticmethod
    def _line_number(content: str, index: int) -> int:
        return content[:index].count("\n") + 1

    @staticmethod
    def _is_noise_secret_line(line: str) -> bool:
        upper = line.upper()
        return (
            line.strip().startswith("#")
            or "EXAMPLE" in upper
            or "PLACEHOLDER" in upper
            or "DUMMY" in upper
            or "TEST" in upper
        )

    def _parse_ast(self, path: Path, content: str) -> ast.AST | None:
        try:
            return ast.parse(content, filename=str(path))
        except SyntaxError as exc:
            self.warnings.append(f"Could not parse AST for {path}: {exc}")
            return None

    def check_subprocess_calls(self):
        """Check for unsafe subprocess usage."""
        print("\nChecking subprocess calls...")

        shell_true_hits: list[str] = []
        dangerous_exec_hits: list[str] = []
        has_safe_subprocess_pattern = False

        for path, content in self.contents.items():
            tree = self._parse_ast(path, content)
            if tree is None:
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue

                func = node.func
                if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    if func.value.id == "subprocess" and func.attr in {
                        "run",
                        "Popen",
                        "call",
                        "check_call",
                        "check_output",
                    }:
                        if node.args and isinstance(node.args[0], (ast.List, ast.Tuple)):
                            has_safe_subprocess_pattern = True
                        for kw in node.keywords or []:
                            if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                shell_true_hits.append(
                                    f"{path}:{getattr(node, 'lineno', '?')}: subprocess.{func.attr}(..., shell=True)"
                                )
                    if func.value.id == "os" and func.attr == "system":
                        # os.system is checked in check_command_injection.
                        pass
                elif isinstance(func, ast.Name) and func.id in {"eval", "exec"}:
                    dangerous_exec_hits.append(
                        f"{path}:{getattr(node, 'lineno', '?')}: {func.id}(...)"
                    )

        if shell_true_hits:
            print("  FAIL: Found shell=True in subprocess calls")
            for hit in shell_true_hits[:10]:
                print(f"    {hit}")
            self.failed.append("Unsafe subprocess: shell=True found")
        else:
            print("  PASS: No shell=True in subprocess calls")

        if dangerous_exec_hits:
            print("  FAIL: Found eval() or exec() calls")
            for hit in dangerous_exec_hits[:10]:
                print(f"    {hit}")
            self.failed.append("Dangerous functions: eval() or exec() found")
        else:
            print("  PASS: No eval() or exec() calls found")

        if has_safe_subprocess_pattern:
            print("  PASS: list-based subprocess command patterns detected")
        else:
            print("  WARN: No evidence of list-based subprocess calls")
            self.warnings.append("Consider list-based subprocess arguments throughout")

        if not shell_true_hits and not dangerous_exec_hits:
            self.passed.append("Subprocess security checks")

    def check_input_validation(self):
        """Check for high-level input validation safeguards."""
        print("\nChecking input validation...")

        corpus = "\n".join(self.contents.values())
        all_checks_passed = True

        if "MAX_TRANSCRIPT_SIZE_BYTES" in corpus or "MAX_TRANSCRIPT_BYTES" in corpus:
            print("  PASS: Transcript size limit defined")
        else:
            print("  FAIL: No transcript size limit found")
            self.failed.append("Missing transcript size limit")
            all_checks_passed = False

        if "MAX_TRANSCRIPT_LINE_COUNT" in corpus or "MAX_TRANSCRIPT_LINES" in corpus:
            print("  PASS: Transcript line count limit defined")
        else:
            print("  FAIL: No transcript line count limit found")
            self.failed.append("Missing transcript line count limit")
            all_checks_passed = False

        if "sanitize_transcript" in corpus:
            print("  PASS: Input sanitization function exists")
        else:
            print("  FAIL: No input sanitization function found")
            self.failed.append("Missing input sanitization function")
            all_checks_passed = False

        if "os.path.abspath" in corpus and "os.path.normpath" in corpus:
            print("  PASS: Path normalization detected")
        else:
            print("  WARN: Limited path normalization detected")
            self.warnings.append("Consider using os.path.abspath + normpath for all external paths")

        if all_checks_passed:
            self.passed.append("Input validation checks")

    def check_hardcoded_secrets(self):
        """Check for obvious hardcoded credentials."""
        print("\nChecking for hardcoded secrets...")

        patterns = [
            (re.compile(r'password\s*=\s*["\'][^"\']+["\']', re.IGNORECASE), "password"),
            (re.compile(r'api[_-]?key\s*=\s*["\'][^"\']+["\']', re.IGNORECASE), "API key"),
            (re.compile(r'secret\s*=\s*["\'][^"\']+["\']', re.IGNORECASE), "secret"),
            (re.compile(r'token\s*=\s*["\'][^"\']+["\']', re.IGNORECASE), "token"),
            (re.compile(r'auth\s*=\s*["\'][^"\']+["\']', re.IGNORECASE), "auth credential"),
        ]

        findings: list[str] = []
        for path, content in self.contents.items():
            lines = content.splitlines()
            for regex, name in patterns:
                for match in regex.finditer(content):
                    line_no = self._line_number(content, match.start())
                    line = lines[line_no - 1].strip()
                    if self._is_noise_secret_line(line):
                        continue
                    findings.append(f"{path}:{line_no}: potential hardcoded {name}: {line[:120]}")

        if findings:
            print("  FAIL: Potential hardcoded secrets detected")
            for item in findings[:10]:
                print(f"    {item}")
            self.failed.append("Potential hardcoded secrets found")
        else:
            print("  PASS: No hardcoded secrets found")
            self.passed.append("No hardcoded secrets")

    def check_file_permissions(self):
        """Check for baseline file I/O resilience and data-directory usage."""
        print("\nChecking file permission handling...")

        corpus = "\n".join(self.contents.values())

        if "except (IOError, OSError)" in corpus or "except OSError" in corpus:
            print("  PASS: File operations include explicit error handling")
        else:
            print("  WARN: File error handling patterns were not found globally")
            self.warnings.append("Ensure file operations consistently use try/except")

        if "get_user_data_dir" in corpus:
            print("  PASS: User data directory separation detected")
        else:
            print("  WARN: No clear user data directory abstraction found")
            self.warnings.append("Consider centralized user-data directory handling")

        self.passed.append("File permission handling")

    def check_command_injection(self):
        """Check for command-injection-sensitive call patterns."""
        print("\nChecking for command injection vulnerabilities...")

        os_system_hits: list[str] = []
        subprocess_format_warnings: list[str] = []

        for path, content in self.contents.items():
            tree = self._parse_ast(path, content)
            if tree is not None:
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    func = node.func
                    if (
                        isinstance(func, ast.Attribute)
                        and isinstance(func.value, ast.Name)
                        and func.value.id == "os"
                        and func.attr == "system"
                    ):
                        os_system_hits.append(
                            f"{path}:{getattr(node, 'lineno', '?')}: os.system(...)"
                        )

            lines = content.splitlines()
            for idx, line in enumerate(lines, 1):
                stripped = line.strip()
                if "subprocess" in stripped and any(tok in stripped for tok in [".format(", " f\"", " f'"]):
                    subprocess_format_warnings.append(f"{path}:{idx}: {stripped[:140]}")

        if os_system_hits:
            print("  FAIL: os.system() usage found")
            for hit in os_system_hits[:10]:
                print(f"    {hit}")
            self.failed.append("Unsafe os.system() usage")
        else:
            print("  PASS: No os.system() usage found")

        if subprocess_format_warnings:
            print("  WARN: String formatting found on subprocess-related lines")
            for hit in subprocess_format_warnings[:10]:
                print(f"    {hit}")
            self.warnings.append("Review subprocess string formatting for input safety")
        else:
            print("  PASS: No obvious subprocess string-formatting injection patterns")

        if not os_system_hits:
            self.passed.append("Command injection checks")

    def check_network_connections(self):
        """Review network usage surface (informational/privacy)."""
        print("\nChecking for network connections (privacy review)...")

        indicators = [
            ("requests.", "HTTP requests library"),
            ("urllib.request", "URL request calls"),
            ("http.client", "HTTP client"),
            ("socket.connect", "socket connections"),
            ("telemetry", "telemetry references"),
        ]

        matches: list[str] = []
        for path, content in self.contents.items():
            lines = content.splitlines()
            for idx, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for token, label in indicators:
                    if token in stripped:
                        matches.append(f"{path}:{idx}: {label}: {stripped[:120]}")

        if matches:
            print("  WARN: Network-related code paths detected")
            for item in matches[:10]:
                print(f"    {item}")
            self.warnings.append(
                "Network call sites found (expected for updater/local LLM in this project)"
            )
        else:
            print("  PASS: No network-related code paths found")
            self.passed.append("Privacy: No network connections")

    def print_summary(self):
        """Print audit summary."""
        print("\n" + "=" * 70)
        print("SECURITY AUDIT SUMMARY")
        print("=" * 70)
        print(f"Scanned Python files: {len(self.files)}")

        if self.passed:
            print(f"\nPASSED ({len(self.passed)}):")
            for item in self.passed:
                print(f"  - {item}")

        if self.warnings:
            print(f"\nWARNINGS ({len(self.warnings)}):")
            for item in self.warnings:
                print(f"  - {item}")

        if self.failed:
            print(f"\nFAILED ({len(self.failed)}):")
            for item in self.failed:
                print(f"  - {item}")

        print("\n" + "=" * 70)

        if not self.failed:
            print("SECURITY AUDIT PASSED")
            if self.warnings:
                print(f"({len(self.warnings)} warning(s) to review)")
            return 0

        print("SECURITY AUDIT FAILED")
        print(f"{len(self.failed)} critical issue(s) found")
        return 1

    def run_audit(self):
        """Run all security checks."""
        print("=" * 70)
        print("WhisperLocal Security Audit")
        print("=" * 70)
        print(f"Project root: {self.project_root}")

        self.check_subprocess_calls()
        self.check_input_validation()
        self.check_hardcoded_secrets()
        self.check_file_permissions()
        self.check_command_injection()
        self.check_network_connections()

        return self.print_summary()


def main():
    """Main entry point."""
    auditor = SecurityAuditor()
    return auditor.run_audit()


if __name__ == "__main__":
    sys.exit(main())
