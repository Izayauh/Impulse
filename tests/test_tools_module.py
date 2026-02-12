"""Tests for deterministic tools module."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from tools import get_active_context, read_project_file


class TestToolsModule(unittest.TestCase):
    def test_get_active_context_placeholder(self):
        value = get_active_context()
        self.assertIsInstance(value, str)
        self.assertTrue(len(value) > 0)

    def test_read_project_file_reads_readme(self):
        content = read_project_file("README.md")
        self.assertIsInstance(content, str)
        self.assertGreater(len(content), 0)

    def test_read_project_file_blocks_traversal(self):
        with self.assertRaises(ValueError):
            read_project_file("..\\..\\Windows\\system.ini")


if __name__ == "__main__":
    unittest.main()
