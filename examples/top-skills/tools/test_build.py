#!/usr/bin/env python3
"""Unit tests for the top-skills catalog and package validation helpers."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build


class CatalogTests(unittest.TestCase):
    def test_catalog_has_ten_unique_packages(self) -> None:
        packages = build.load_catalog()
        self.assertEqual(10, len(packages))
        self.assertEqual(10, len({item["identifier"] for item in packages}))
        self.assertEqual(10, len({item["repository"] for item in packages}))

    def test_skill_name_must_extend_to_the_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "SKILL.md"
            path.write_text("---\nname: wrong\ndescription: test\n---\n", encoding="utf-8")
            self.assertEqual("wrong", build.read_frontmatter_name(path))

    def test_symlinks_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "target").write_text("x", encoding="utf-8")
            (root / "link").symlink_to(root / "target")
            with self.assertRaises(ValueError):
                build.validate_tree(root)


if __name__ == "__main__":
    unittest.main()
