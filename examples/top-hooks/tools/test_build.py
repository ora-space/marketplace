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
        self.assertEqual(10, len({package["identifier"] for package in packages}))
        self.assertEqual(10, len({package["slug"] for package in packages}))

    def test_every_package_names_a_license_and_targets(self) -> None:
        for package in build.load_catalog():
            self.assertTrue(package["license"])
            self.assertTrue(package["license_files"])
            self.assertGreater(package["stars"], 0)
        self.assertEqual(5, len(build.TARGETS))

    def test_npm_and_python_commands_are_normalized(self) -> None:
        package = {"pin_npm_package": "tdd-guard@1.7.0"}
        self.assertEqual(
            "npx --yes tdd-guard@1.7.0",
            build.patched_hook_command("npx tdd-guard@latest", package),
        )
        package = {"python_fallback": True}
        self.assertEqual(
            'python3 "hook.py" || python "hook.py"',
            build.patched_hook_command('python3 "hook.py"', package),
        )

    def test_marketplace_name_is_claude_safe(self) -> None:
        package = build.load_catalog()[0]
        name = build.marketplace_name(package)
        self.assertTrue(name.startswith("orax-top-hooks-"))
        self.assertNotIn(".", name)

    def test_template_rejects_missing_license(self) -> None:
        package = build.load_catalog()[0]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "plugin" / ".claude-plugin").mkdir(parents=True)
            (root / "plugin" / ".claude-plugin" / "plugin.json").write_text(
                '{"name":"tdd-guard","version":"1.0.0"}\n', encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                build.create_template(package, root, root / "template")


if __name__ == "__main__":
    unittest.main()
