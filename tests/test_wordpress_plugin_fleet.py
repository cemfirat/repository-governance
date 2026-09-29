import base64
import importlib.util
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "wordpress-plugin-fleet.py"
)
spec = importlib.util.spec_from_file_location(
    "wordpress_plugin_fleet",
    SCRIPT_PATH,
)
fleet = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(fleet)


def inventory():
    return {
        "schema_version": 1,
        "blueprint": "wordpress-plugin",
        "target_blueprint_version": "0.1.0",
        "repositories": [
            {
                "repository": "cemfirat/plugin-a",
                "default_branch": "main",
                "desired_profile": "simple",
                "rollout": "enrolled",
            },
            {
                "repository": "cemfirat/plugin-b",
                "default_branch": "main",
                "desired_profile": "application",
                "rollout": "planned",
            },
        ],
    }


def manifest(version="0.1.0", profile="simple"):
    return {
        "schema_version": 1,
        "blueprint": "wordpress-plugin",
        "blueprint_version": version,
        "profile": profile,
    }


class FleetPlannerTests(unittest.TestCase):
    def test_inventory_validation_rejects_duplicates(self):
        value = inventory()
        value["repositories"].append(dict(value["repositories"][0]))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "inventory.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(fleet.FleetError):
                fleet.load_inventory(path)

    def test_current_manifest_is_current(self):
        entry = inventory()["repositories"][0]
        result = fleet.classify(entry, manifest(), "0.1.0")
        self.assertEqual("current", result["status"])
        self.assertEqual([], result["issues"])

    def test_missing_manifest_is_unenrolled(self):
        entry = inventory()["repositories"][1]
        result = fleet.classify(entry, None, "0.1.0")
        self.assertEqual("unenrolled", result["status"])

    def test_version_drift_is_reported(self):
        entry = inventory()["repositories"][0]
        result = fleet.classify(
            entry,
            manifest(version="0.0.9"),
            "0.1.0",
        )
        self.assertEqual("version-drift", result["status"])

    def test_profile_drift_has_priority(self):
        entry = inventory()["repositories"][1]
        result = fleet.classify(
            entry,
            manifest(version="0.0.9", profile="simple"),
            "0.1.0",
        )
        self.assertEqual("profile-drift", result["status"])
        self.assertEqual(2, len(result["issues"]))

    def test_plan_is_read_only_and_counts_states(self):
        manifests = {
            "cemfirat/plugin-a": manifest(),
            "cemfirat/plugin-b": None,
        }
        calls = []

        def fetcher(repository, branch):
            calls.append((repository, branch))
            return manifests[repository]

        plan = fleet.plan_inventory(inventory(), fetcher)
        self.assertTrue(plan["complete"])
        self.assertEqual(
            {"current": 1, "unenrolled": 1},
            plan["counts"],
        )
        self.assertEqual(
            [
                ("cemfirat/plugin-a", "main"),
                ("cemfirat/plugin-b", "main"),
            ],
            calls,
        )


    def test_fetch_github_manifest_decodes_contents_api_response(self):
        payload = {
            "encoding": "base64",
            "content": base64.b64encode(
                json.dumps(manifest()).encode("utf-8")
            ).decode("ascii"),
        }

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(payload).encode("utf-8")

        with mock.patch.object(
            fleet.urllib.request,
            "urlopen",
            return_value=Response(),
        ) as urlopen:
            value = fleet.fetch_github_manifest(
                "cemfirat/plugin-a",
                "main",
                token="test-token",
            )

        self.assertEqual(manifest(), value)
        request = urlopen.call_args.args[0]
        self.assertEqual(
            "Bearer test-token",
            request.headers["Authorization"],
        )
        self.assertIn(
            "/repos/cemfirat/plugin-a/contents/",
            request.full_url,
        )

    def test_fetch_github_manifest_treats_404_as_unenrolled(self):
        error = urllib.error.HTTPError(
            "https://api.github.com/example",
            404,
            "Not Found",
            hdrs=None,
            fp=None,
        )
        with mock.patch.object(
            fleet.urllib.request,
            "urlopen",
            side_effect=error,
        ):
            value = fleet.fetch_github_manifest(
                "cemfirat/plugin-a",
                "main",
            )

        self.assertIsNone(value)

    def test_unknown_repository_filter_is_rejected(self):
        with self.assertRaises(fleet.FleetError):
            fleet.plan_inventory(
                inventory(),
                lambda repository, branch: None,
                {"cemfirat/unknown"},
            )


if __name__ == "__main__":
    unittest.main()
