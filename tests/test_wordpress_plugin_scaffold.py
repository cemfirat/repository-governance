import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "wordpress-plugin-scaffold.py"

spec = importlib.util.spec_from_file_location(
    "wordpress_plugin_scaffold",
    SCRIPT_PATH,
)
scaffold = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(scaffold)


class WordPressPluginScaffoldTests(unittest.TestCase):
    def base_args(self, destination):
        return {
            "governance_root": ROOT,
            "destination": destination,
            "profile": "simple",
            "slug": "example-plugin",
            "name": "Example Plugin",
            "description": "Adds a focused example capability to WordPress.",
            "version": "0.1.0",
            "minimum_wordpress": "6.5",
            "minimum_php": "8.0",
            "author": "Cem Firat",
            "author_uri": "https://cemfirat.com/",
            "package_root": ".",
            "license_mode": "managed-gpl",
            "license_value": None,
            "license_header": None,
            "license_uri": None,
            "distribution": "github-releases",
            "updates": "none",
            "repository": "cemfirat/example-plugin",
            "text_domain": None,
            "main_file": None,
            "playground_preview": False,
        }

    def test_simple_managed_gpl_scaffold_audits_clean(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "example-plugin"
            result = scaffold.scaffold_plugin(
                **self.base_args(destination)
            )

            self.assertEqual("clean", result["audit"]["status"])
            self.assertEqual("simple", result["profile"])
            self.assertTrue(
                (destination / ".ccf-wordpress-plugin.json").is_file()
            )
            self.assertTrue(
                (destination / "example-plugin.php").is_file()
            )
            self.assertTrue((destination / "LICENSE").is_file())
            self.assertTrue(
                (destination / "assets" / "logo.svg").is_file()
            )

            manifest = json.loads(
                (
                    destination / ".ccf-wordpress-plugin.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual("0.2.0", manifest["blueprint_version"])
            self.assertEqual(
                "managed-gpl",
                manifest["plugin"]["license_mode"],
            )

            releases = json.loads(
                (
                    ROOT
                    / "blueprints"
                    / "wordpress-plugin"
                    / "releases.json"
                ).read_text(encoding="utf-8")
            )
            action_sha = releases["releases"]["0.2.0"][
                "audit_action_sha"
            ]
            workflow = (
                destination
                / ".github"
                / "workflows"
                / "blueprint.yml"
            ).read_text(encoding="utf-8")
            self.assertIn(
                f"repository-governance/blueprints/wordpress-plugin@{action_sha}",
                workflow,
            )
            self.assertIn("on:\n  pull_request:\n  push:\n", workflow)
            self.assertNotIn("branches:", workflow)

    def test_nested_application_declared_license_audits_clean(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "nested-plugin"
            args = self.base_args(destination)
            args.update(
                {
                    "profile": "application",
                    "slug": "nested-plugin",
                    "name": "Nested Plugin",
                    "description": (
                        "Provides a larger WordPress integration from a "
                        "nested package directory."
                    ),
                    "package_root": "wordpress",
                    "license_mode": "declared",
                    "license_value": "Proprietary / private project",
                    "distribution": "none",
                    "updates": "none",
                    "repository": None,
                }
            )

            result = scaffold.scaffold_plugin(**args)

            self.assertEqual("clean", result["audit"]["status"])
            self.assertEqual("wordpress", result["package_root"])
            self.assertTrue(
                (
                    destination
                    / "wordpress"
                    / "nested-plugin.php"
                ).is_file()
            )
            self.assertTrue(
                (
                    destination
                    / "wordpress"
                    / "readme.txt"
                ).is_file()
            )
            self.assertFalse(
                (destination / "wordpress" / "LICENSE").exists()
            )

            manifest = json.loads(
                (
                    destination / ".ccf-wordpress-plugin.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                "declared",
                manifest["plugin"]["license_mode"],
            )
            self.assertIsNone(
                manifest["plugin"]["license_header"]
            )

    def test_non_empty_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "existing"
            destination.mkdir()
            sentinel = destination / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")

            with self.assertRaises(scaffold.ScaffoldError):
                scaffold.scaffold_plugin(
                    **self.base_args(destination)
                )

            self.assertEqual(
                "keep",
                sentinel.read_text(encoding="utf-8"),
            )

    def test_block_profile_refuses_custom_scaffold(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "block-plugin"
            args = self.base_args(destination)
            args["profile"] = "block"

            with self.assertRaises(scaffold.ScaffoldError):
                scaffold.scaffold_plugin(**args)

            self.assertFalse(destination.exists())

    def test_github_release_updater_is_not_invented(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "example-plugin"
            args = self.base_args(destination)
            args["updates"] = "github-release-updater"

            with self.assertRaises(scaffold.ScaffoldError):
                scaffold.scaffold_plugin(**args)

            self.assertFalse(destination.exists())

    def test_github_distribution_requires_repository(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "example-plugin"
            args = self.base_args(destination)
            args["repository"] = None

            with self.assertRaises(scaffold.ScaffoldError):
                scaffold.scaffold_plugin(**args)

    def test_cli_main_creates_clean_scaffold(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "cli-plugin"
            exit_code = scaffold.main(
                [
                    "--governance-root",
                    str(ROOT),
                    "--destination",
                    str(destination),
                    "--profile",
                    "simple",
                    "--slug",
                    "cli-plugin",
                    "--name",
                    "CLI Plugin",
                    "--description",
                    "Adds a small capability generated through the CLI.",
                    "--license-mode",
                    "managed-gpl",
                    "--distribution",
                    "github-releases",
                    "--updates",
                    "none",
                    "--repository",
                    "cemfirat/cli-plugin",
                ]
            )

            self.assertEqual(0, exit_code)
            self.assertTrue(
                (destination / ".ccf-wordpress-plugin.json").is_file()
            )


if __name__ == "__main__":
    unittest.main()
