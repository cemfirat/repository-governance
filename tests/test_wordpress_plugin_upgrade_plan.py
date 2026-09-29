import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "wordpress-plugin-upgrade-plan.py"
)
spec = importlib.util.spec_from_file_location(
    "wordpress_plugin_upgrade_plan",
    SCRIPT_PATH,
)
planner = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(planner)


def entry(
    repository="cemfirat/example-plugin",
    profile="simple",
    rollout="enrolled",
):
    return {
        "repository": repository,
        "default_branch": "main",
        "desired_profile": profile,
        "rollout": rollout,
    }


def manifest(
    version="0.1.0",
    profile="simple",
    license_name="GPL-2.0-or-later",
    license_header="GPL-2.0-or-later",
):
    return {
        "schema_version": 1,
        "blueprint": "wordpress-plugin",
        "blueprint_version": version,
        "profile": profile,
        "plugin": {
            "slug": "example-plugin",
            "name": "Example Plugin",
            "main_file": "example-plugin.php",
            "version": "1.0.0",
            "text_domain": "example-plugin",
            "minimum_wordpress": "6.5",
            "minimum_php": "8.0",
            "author": "Cem Firat",
            "license": license_name,
            "license_header": license_header,
        },
    }


class UpgradePlannerTests(unittest.TestCase):
    def test_current_plugin_needs_no_change(self):
        value = manifest(version="0.2.0")
        value["plugin"]["root"] = "."
        value["plugin"]["license_mode"] = "managed-gpl"

        result = planner.propose(entry(), value, "0.2.0")

        self.assertEqual("current", result["status"])
        self.assertTrue(result["safe_to_apply"])
        self.assertEqual([], result["actions"])

    def test_known_gpl_migration_is_safe(self):
        result = planner.propose(entry(), manifest(), "0.2.0")

        self.assertEqual("safe-upgrade", result["status"])
        self.assertTrue(result["safe_to_apply"])
        self.assertEqual(
            {
                "blueprint_version",
                "plugin.root",
                "plugin.license_mode",
            },
            {item["path"] for item in result["actions"]},
        )

    def test_non_gpl_license_is_not_inferred(self):
        value = manifest(
            license_name="Proprietary / private project",
            license_header=None,
        )

        result = planner.propose(entry(), value, "0.2.0")

        self.assertEqual("manual-review", result["status"])
        self.assertFalse(result["safe_to_apply"])
        self.assertTrue(
            any("license_mode" in note for note in result["notes"])
        )

    def test_paused_repository_is_not_fetched(self):
        inventory = {
            "schema_version": 1,
            "blueprint": "wordpress-plugin",
            "target_blueprint_version": "0.2.0",
            "repositories": [entry(rollout="paused")],
        }
        calls = []

        def fetcher(repository, branch):
            calls.append((repository, branch))
            return manifest()

        result = planner.plan(inventory, fetcher)

        self.assertEqual([], calls)
        self.assertEqual("paused", result["results"][0]["status"])
        self.assertFalse(result["results"][0]["safe_to_apply"])

    def test_unenrolled_repository_requires_manual_enrollment(self):
        result = planner.propose(entry(rollout="planned"), None, "0.2.0")

        self.assertEqual("manual-enrollment", result["status"])
        self.assertFalse(result["safe_to_apply"])

    def test_profile_drift_requires_manual_review(self):
        result = planner.propose(
            entry(profile="application"),
            manifest(profile="simple"),
            "0.2.0",
        )

        self.assertEqual("manual-review", result["status"])
        self.assertFalse(result["safe_to_apply"])

    def test_unknown_migration_requires_manual_review(self):
        result = planner.propose(
            entry(),
            manifest(version="0.2.0"),
            "0.3.0",
        )

        self.assertEqual("manual-review", result["status"])
        self.assertFalse(result["safe_to_apply"])
        self.assertTrue(
            any("no reviewed migration" in note for note in result["notes"])
        )

    def test_repository_filter_rejects_unknown_repository(self):
        inventory = {
            "schema_version": 1,
            "blueprint": "wordpress-plugin",
            "target_blueprint_version": "0.2.0",
            "repositories": [entry()],
        }

        with self.assertRaises(planner.fleet.FleetError):
            planner.plan(
                inventory,
                lambda repository, branch: manifest(),
                {"cemfirat/unknown"},
            )

    def test_cli_parser_builds(self):
        parser = planner.build_parser()
        args = parser.parse_args(
            ["--repository", "cemfirat/example-plugin", "--format", "json"]
        )
        self.assertEqual(["cemfirat/example-plugin"], args.repository)
        self.assertEqual("json", args.format)


if __name__ == "__main__":
    unittest.main()
