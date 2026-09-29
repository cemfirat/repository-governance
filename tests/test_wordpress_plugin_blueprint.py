import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "wordpress-plugin-blueprint.py"
)
spec = importlib.util.spec_from_file_location(
    "wordpress_plugin_blueprint",
    SCRIPT_PATH,
)
blueprint = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(blueprint)


PLUGIN_PHP = """<?php
/**
 * Plugin Name: Example Plugin
 * Plugin URI: https://github.com/cemfirat/example-plugin
 * Description: A small example plugin used by the blueprint tests.
 * Version: 1.2.3
 * Requires at least: 6.5
 * Requires PHP: 8.0
 * Author: Cem Firat
 * Author URI: https://cemfirat.com/
 * License: GPL-2.0-or-later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Update URI: https://github.com/cemfirat/example-plugin
 * Text Domain: example-plugin
 */
"""

README = """<p align="center">
  <img src="https://raw.githubusercontent.com/cemfirat/repository-governance/main/assets/brand-banner.webp" alt="Cem Firat creative consultancy artwork" width="900" />
</p>

# Example Plugin
"""

README_TXT = """=== Example Plugin ===
Contributors: cemfirat
Tags: example
Requires at least: 6.5
Requires PHP: 8.0
Stable tag: 1.2.3
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Example.
"""

GPL = """GNU GENERAL PUBLIC LICENSE
Version 2, June 1991
test fixture
"""


class BlueprintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.gov = self.root / "governance"
        self.plugin = self.root / "plugin"
        (
            self.gov
            / "blueprints"
            / "wordpress-plugin"
            / "profiles"
        ).mkdir(parents=True)
        (self.gov / "assets").mkdir(parents=True)
        (
            self.gov
            / "blueprints"
            / "wordpress-plugin"
            / "managed"
        ).mkdir(parents=True)
        self.plugin.mkdir()

        profile = {
            "profile": "simple",
            "required_files": [
                ".ccf-wordpress-plugin.json",
                "README.md",
                "readme.txt",
                "CHANGELOG.md",
                "LICENSE",
                "assets/logo.svg",
            ],
            "exact_managed_files": {
                "assets/logo.svg": "assets/logo.svg",
                "LICENSE": (
                    "blueprints/wordpress-plugin/managed/gpl-2.0.txt"
                ),
            },
        }
        (
            self.gov
            / "blueprints"
            / "wordpress-plugin"
            / "profiles"
            / "simple.json"
        ).write_text(json.dumps(profile), encoding="utf-8")
        (self.gov / "assets" / "logo.svg").write_text(
            "<svg>canonical</svg>\n",
            encoding="utf-8",
        )
        (
            self.gov
            / "blueprints"
            / "wordpress-plugin"
            / "managed"
            / "gpl-2.0.txt"
        ).write_text(GPL, encoding="utf-8")

        manifest = {
            "schema_version": 1,
            "blueprint": "wordpress-plugin",
            "blueprint_version": "0.1.0",
            "profile": "simple",
            "plugin": {
                "slug": "example-plugin",
                "name": "Example Plugin",
                "main_file": "example-plugin.php",
                "version": "1.2.3",
                "text_domain": "example-plugin",
                "minimum_wordpress": "6.5",
                "minimum_php": "8.0",
                "author": "Cem Firat",
                "license": "GPL-2.0-or-later",
                "license_header": "GPL-2.0-or-later",
            },
            "distribution": {
                "channel": "github-releases",
                "update_uri": (
                    "https://github.com/cemfirat/example-plugin"
                ),
            },
            "features": {
                "block_plugin": False,
                "playground_preview": False,
            },
        }
        (self.plugin / ".ccf-wordpress-plugin.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
        (self.plugin / "example-plugin.php").write_text(
            PLUGIN_PHP,
            encoding="utf-8",
        )
        (self.plugin / "README.md").write_text(
            README,
            encoding="utf-8",
        )
        (self.plugin / "readme.txt").write_text(
            README_TXT,
            encoding="utf-8",
        )
        (self.plugin / "CHANGELOG.md").write_text(
            "# Changelog\n\n## 1.2.3 - Unreleased\n",
            encoding="utf-8",
        )
        (self.plugin / "LICENSE").write_text(
            GPL,
            encoding="utf-8",
        )
        (self.plugin / "assets").mkdir()
        (self.plugin / "assets" / "logo.svg").write_text(
            "<svg>canonical</svg>\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_plugin_passes(self):
        result = blueprint.audit(self.plugin, self.gov)
        self.assertEqual("clean", result["status"])
        self.assertEqual([], result["issues"])

    def test_managed_file_drift_is_reported(self):
        (self.plugin / "assets" / "logo.svg").write_text(
            "<svg>changed</svg>\n",
            encoding="utf-8",
        )
        result = blueprint.audit(self.plugin, self.gov)
        codes = {issue["code"] for issue in result["issues"]}
        self.assertIn("managed_file_drift", codes)

    def test_header_mismatch_is_reported(self):
        manifest_path = self.plugin / ".ccf-wordpress-plugin.json"
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
        manifest["plugin"]["text_domain"] = "wrong-domain"
        manifest_path.write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        result = blueprint.audit(self.plugin, self.gov)
        codes = {issue["code"] for issue in result["issues"]}
        self.assertIn("plugin_header_mismatch", codes)

    def test_sync_exact_changes_only_exact_managed_files(self):
        original_readme = (
            self.plugin / "README.md"
        ).read_text(encoding="utf-8")
        (self.plugin / "assets" / "logo.svg").write_text(
            "<svg>changed</svg>\n",
            encoding="utf-8",
        )
        (self.plugin / "LICENSE").write_text(
            "changed\n",
            encoding="utf-8",
        )

        plan = blueprint.sync_exact(
            self.plugin,
            self.gov,
            write=False,
        )
        self.assertEqual(
            {"assets/logo.svg", "LICENSE"},
            {item["path"] for item in plan["changes"]},
        )
        self.assertEqual(
            "<svg>changed</svg>\n",
            (self.plugin / "assets" / "logo.svg").read_text(
                encoding="utf-8"
            ),
        )

        applied = blueprint.sync_exact(
            self.plugin,
            self.gov,
            write=True,
        )
        self.assertEqual(2, len(applied["changes"]))
        self.assertEqual(
            "<svg>canonical</svg>\n",
            (self.plugin / "assets" / "logo.svg").read_text(
                encoding="utf-8"
            ),
        )
        self.assertEqual(
            GPL,
            (self.plugin / "LICENSE").read_text(
                encoding="utf-8"
            ),
        )
        self.assertEqual(
            original_readme,
            (self.plugin / "README.md").read_text(
                encoding="utf-8"
            ),
        )

    def test_path_escape_is_rejected(self):
        manifest_path = self.plugin / ".ccf-wordpress-plugin.json"
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
        manifest["plugin"]["main_file"] = "../escape.php"
        manifest_path.write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        with self.assertRaises(blueprint.BlueprintError):
            blueprint.audit(self.plugin, self.gov)


if __name__ == "__main__":
    unittest.main()
