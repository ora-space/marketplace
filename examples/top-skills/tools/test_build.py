#!/usr/bin/env python3
"""Unit tests for the top-skills catalog and package validation helpers."""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from io import BytesIO
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

    def test_archive_skill_names_reads_direct_skill_directories(self) -> None:
        payload = BytesIO()
        with zipfile.ZipFile(payload, "w") as archive:
            archive.writestr(
                "assets/Review/SKILL.md",
                "---\nname: Review\ndescription: test\n---\n",
            )
            archive.writestr("assets/not-a-skill/README.md", "ignored")
        self.assertEqual({"review"}, build.archive_skill_names(payload.getvalue()))

    def test_archive_skill_names_rejects_nested_skills(self) -> None:
        payload = BytesIO()
        with zipfile.ZipFile(payload, "w") as archive:
            archive.writestr(
                "assets/group/review/SKILL.md",
                "---\nname: review\ndescription: test\n---\n",
            )
        with self.assertRaises(ValueError):
            build.archive_skill_names(payload.getvalue())


if __name__ == "__main__":
    unittest.main()
