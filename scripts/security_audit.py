"""
Security audit script for WhisperLocal.

This script performs automated security checks on the codebase:
- Checks for unsafe subprocess usage
- Validates input sanitization
- Checks for hardcoded secrets
- Validates file permission handling
- Checks for command injection vulnerabilities

Run with: python scripts/security_audit.py
"""

import subprocess
import re
import sys
import os
from pathlib import Path

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


class SecurityAuditor:
    """Automated security audit for WhisperLocal."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.main_file = self.project_root / "flow_local_dictation.py"
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def check_subprocess_calls(self):
        """Check for unsafe subprocess usage."""
        print("\n🔍 Checking subprocess calls...")
        
        with open(self.main_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
        
        issues_found = False
        
        # Check for shell=True
        if 'shell=True' in content:
            print("  ❌ FAIL: Found shell=True in subprocess calls")
            print("     This can lead to command injection vulnerabilities")
            for i, line in enumerate(lines, 1):
                if 'shell=True' in line:
                    print(f"     Line {i}: {line.strip()}")
            self.failed.append("Unsafe subprocess: shell=True found")
            issues_found = True
        else:
            print("  ✅ PASS: No shell=True in subprocess calls")
        
        # Check for eval/exec
        eval_pattern = re.compile(r'\beval\s*\(')
        exec_pattern = re.compile(r'\bexec\s*\(')
        
        if eval_pattern.search(content) or exec_pattern.search(content):
            print("  ❌ FAIL: Found eval() or exec() calls")
            print("     These functions execute arbitrary code and are dangerous")
            for i, line in enumerate(lines, 1):
                if eval_pattern.search(line) or exec_pattern.search(line):
                    print(f"     Line {i}: {line.strip()}")
            self.failed.append("Dangerous functions: eval() or exec() found")
            issues_found = True
        else:
            print("  ✅ PASS: No eval() or exec() calls found")
        
        # Check for proper command building (using shlex or list)
        if 'shlex.quote' in content or 'subprocess.run([' in content:
            print("  ✅ PASS: Proper command building detected (shlex or list args)")
        else:
            print("  ⚠️  WARN: No evidence of shlex.quote or list-based subprocess calls")
            self.warnings.append("Consider using shlex.quote() for subprocess arguments")
        
        if not issues_found:
            self.passed.append("Subprocess security checks")
        
        return not issues_found
    
    def check_input_validation(self):
        """Check for input validation and size limits."""
        print("\n🔍 Checking input validation...")
        
        with open(self.main_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        all_checks_passed = True
        
        # Check for transcript size limit
        if 'MAX_TRANSCRIPT_SIZE_BYTES' in content or 'MAX_TRANSCRIPT_BYTES' in content:
            print("  ✅ PASS: Transcript size limit defined")
        else:
            print("  ❌ FAIL: No transcript size limit found")
            self.failed.append("Missing transcript size limit")
            all_checks_passed = False
        
        # Check for line count limit
        if 'MAX_TRANSCRIPT_LINE_COUNT' in content or 'MAX_TRANSCRIPT_LINES' in content:
            print("  ✅ PASS: Transcript line count limit defined")
        else:
            print("  ❌ FAIL: No line count limit found")
            self.failed.append("Missing line count limit")
            all_checks_passed = False
        
        # Check for input sanitization function
        if 'sanitize_transcript' in content:
            print("  ✅ PASS: Input sanitization function exists")
        else:
            print("  ❌ FAIL: No input sanitization function found")
            self.failed.append("Missing input sanitization")
            all_checks_passed = False
        
        # Check for path validation
        if 'os.path.abspath' in content and 'os.path.normpath' in content:
            print("  ✅ PASS: Path normalization detected")
        else:
            print("  ⚠️  WARN: Limited path normalization detected")
            self.warnings.append("Consider using os.path.abspath and normpath for all paths")
        
        if all_checks_passed:
            self.passed.append("Input validation checks")
        
        return all_checks_passed
    
    def check_hardcoded_secrets(self):
        """Check for hardcoded secrets and credentials."""
        print("\n🔍 Checking for hardcoded secrets...")
        
        with open(self.main_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
        
        # Patterns to check
        patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', 'password'),
            (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', 'API key'),
            (r'secret\s*=\s*["\'][^"\']+["\']', 'secret'),
            (r'token\s*=\s*["\'][^"\']+["\']', 'token'),
            (r'auth\s*=\s*["\'][^"\']+["\']', 'auth credential'),
        ]
        
        found_issues = False
        
        for pattern, name in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                # Find line number
                line_num = content[:match.start()].count('\n') + 1
                line_content = lines[line_num - 1].strip()
                
                # Ignore comments and obvious constants
                if not line_content.startswith('#') and 'EXAMPLE' not in line_content.upper():
                    print(f"  ❌ FAIL: Potential hardcoded {name}")
                    print(f"     Line {line_num}: {line_content[:80]}")
                    self.failed.append(f"Potential hardcoded {name}")
                    found_issues = True
        
        if not found_issues:
            print("  ✅ PASS: No hardcoded secrets found")
            self.passed.append("No hardcoded secrets")
        
        return not found_issues
    
    def check_file_permissions(self):
        """Check for proper file permission handling."""
        print("\n🔍 Checking file permission handling...")
        
        with open(self.main_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        all_checks_passed = True
        
        # Check for try-except around file operations
        file_ops = ['open(', 'with open(', 'os.remove(', 'shutil.']
        has_proper_handling = all(
            any(f'{op}' in line and ('try:' in content[max(0, content.find(line) - 200):content.find(line)] or 
                                      'except' in content[content.find(line):content.find(line) + 200])
                for line in content.splitlines() if op in line)
            for op in file_ops if op in content
        )
        
        if has_proper_handling or 'except (IOError, OSError)' in content:
            print("  ✅ PASS: File operations have error handling")
        else:
            print("  ⚠️  WARN: Some file operations may lack error handling")
            self.warnings.append("Ensure all file operations have try-except blocks")
        
        # Check for user data directory separation
        if 'get_user_data_dir' in content:
            print("  ✅ PASS: User data directory separation implemented")
        else:
            print("  ⚠️  WARN: No clear user data directory separation")
            self.warnings.append("Consider separating user data from application files")
        
        if all_checks_passed:
            self.passed.append("File permission handling")
        
        return True
    
    def check_command_injection(self):
        """Check for command injection vulnerabilities."""
        print("\n🔍 Checking for command injection vulnerabilities...")
        
        with open(self.main_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
        
        issues_found = False
        
        # Check for string formatting in subprocess calls
        subprocess_lines = [
            (i + 1, line) for i, line in enumerate(lines) 
            if 'subprocess' in line and any(op in line for op in ['%', '.format', 'f"', "f'"])
        ]
        
        if subprocess_lines:
            print("  ⚠️  WARN: String formatting found near subprocess calls")
            print("     Ensure user input is properly sanitized")
            for line_num, line in subprocess_lines[:3]:  # Show first 3
                print(f"     Line {line_num}: {line.strip()[:80]}")
            self.warnings.append("String formatting in subprocess calls - review for safety")
        else:
            print("  ✅ PASS: No obvious string formatting in subprocess calls")
        
        # Check for os.system usage
        if 'os.system(' in content:
            print("  ❌ FAIL: os.system() usage found")
            print("     This is vulnerable to command injection")
            for i, line in enumerate(lines, 1):
                if 'os.system(' in line:
                    print(f"     Line {i}: {line.strip()}")
            self.failed.append("Unsafe os.system() usage")
            issues_found = True
        else:
            print("  ✅ PASS: No os.system() usage found")
        
        if not issues_found:
            self.passed.append("Command injection checks")
        
        return not issues_found
    
    def check_network_connections(self):
        """Check for network connections (should be none for privacy)."""
        print("\n🔍 Checking for network connections (privacy check)...")
        
        with open(self.main_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
        
        # Patterns that might indicate network activity
        network_patterns = [
            ('requests.', 'HTTP requests library'),
            ('urllib.request', 'URL requests'),
            ('http.client', 'HTTP client'),
            ('socket.connect', 'Socket connections'),
            ('telemetry', 'Telemetry'),
        ]
        
        found_network = False
        
        for pattern, description in network_patterns:
            if pattern in content:
                # Check if it's in a comment
                for i, line in enumerate(lines, 1):
                    if pattern in line and not line.strip().startswith('#'):
                        print(f"  ⚠️  WARN: Found {description}")
                        print(f"     Line {i}: {line.strip()[:80]}")
                        self.warnings.append(f"Network activity detected: {description}")
                        found_network = True
        
        if not found_network:
            print("  ✅ PASS: No network connections found (privacy preserved)")
            self.passed.append("Privacy: No network connections")
        
        return True
    
    def print_summary(self):
        """Print audit summary."""
        print("\n" + "=" * 70)
        print("SECURITY AUDIT SUMMARY")
        print("=" * 70)
        
        if self.passed:
            print(f"\n✅ PASSED ({len(self.passed)}):")
            for item in self.passed:
                print(f"   • {item}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for item in self.warnings:
                print(f"   • {item}")
        
        if self.failed:
            print(f"\n❌ FAILED ({len(self.failed)}):")
            for item in self.failed:
                print(f"   • {item}")
        
        print("\n" + "=" * 70)
        
        if not self.failed:
            print("✅ SECURITY AUDIT PASSED")
            if self.warnings:
                print(f"   ({len(self.warnings)} warnings to review)")
            return 0
        else:
            print("❌ SECURITY AUDIT FAILED")
            print(f"   {len(self.failed)} critical issue(s) found")
            return 1
    
    def run_audit(self):
        """Run all security checks."""
        print("=" * 70)
        print("WhisperLocal Security Audit")
        print("=" * 70)
        print(f"Auditing: {self.main_file}")
        
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


if __name__ == '__main__':
    sys.exit(main())

