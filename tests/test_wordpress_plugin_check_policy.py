import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "wordpress-plugin-check-policy.py"

spec = importlib.util.spec_from_file_location(
    "wordpress_plugin_check_policy",
    SCRIPT_PATH,
)
policy = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(policy)


def manifest(channel="github-releases", slug="example-plugin"):
    return {
        "schema_version": 1,
        "blueprint": "wordpress-plugin",
        "blueprint_version": "0.2.0",
        "profile": "simple",
        "plugin": {
            "slug": slug,
        },
        "distribution": {
            "channel": channel,
            "updates": "none",
        },
    }


class WordPressPluginCheckPolicyTests(unittest.TestCase):
    def test_external_distribution_excludes_directory_only_policy(self):
        value = policy.resolve_policy(manifest("github-releases"))
        self.assertFalse(value["directory_policy"])
        self.assertNotIn("plugin_repo", value["categories"])
        self.assertEqual(
            ["general", "security", "performance", "accessibility"],
            value["categories"],
        )

    def test_no_distribution_uses_cross_distribution_checks(self):
        value = policy.resolve_policy(manifest("none"))
        self.assertFalse(value["directory_policy"])
        self.assertNotIn("plugin_repo", value["categories"])

    def test_wordpress_org_includes_directory_policy(self):
        value = policy.resolve_policy(manifest("wordpress.org"))
        self.assertTrue(value["directory_policy"])
        self.assertIn("plugin_repo", value["categories"])

    def test_invalid_slug_is_rejected_while_reading_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.json"
            path.write_text(
                json.dumps(manifest(slug="WordPress Bad Slug")),
                encoding="utf-8",
            )
            with self.assertRaises(policy.PolicyError):
                policy.read_manifest(path)

    def test_invalid_distribution_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.json"
            path.write_text(
                json.dumps(manifest(channel="unknown")),
                encoding="utf-8",
            )
            with self.assertRaises(policy.PolicyError):
                policy.read_manifest(path)

    def test_github_output_contains_multiline_categories(self):
        value = policy.resolve_policy(manifest("github-releases"))
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "github-output"
            policy.write_github_output(output, value)
            text = output.read_text(encoding="utf-8")

        self.assertIn("slug=example-plugin\n", text)
        self.assertIn("distribution=github-releases\n", text)
        self.assertIn("directory_policy=false\n", text)
        self.assertIn(
            "general\nsecurity\nperformance\naccessibility\n",
            text,
        )

    def test_composite_action_pins_official_plugin_check_release(self):
        action = (
            ROOT
            / "blueprints"
            / "wordpress-plugin"
            / "plugin-check"
            / "action.yml"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "WordPress/plugin-check-action@"
            "10857da14b6c2246d15402b3e69f777edcf8c12e",
            action,
        )
        self.assertIn("repo-token: \"\"", action)
        self.assertIn(
            "scripts/wordpress-plugin-check-policy.py",
            action,
        )


if __name__ == "__main__":
    unittest.main()
