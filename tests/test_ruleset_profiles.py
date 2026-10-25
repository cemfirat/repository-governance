"""Offline tests for protected public/private GitHub repository setup."""
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def call(script, *args):
    return subprocess.run(["bash", str(ROOT / "scripts" / script), *args],
                          cwd=ROOT, capture_output=True, text=True, check=False)

def payload(stdout):
    a = stdout.split("=== hard guardrails ===", 1)[1]
    hard, merge = a.split("=== merge gates ===", 1)
    return json.loads(hard), json.loads(merge)

class ProfilesTest(unittest.TestCase):
    def test_both_default_profiles_fail_closed(self):
        for profile in ("public", "private"):
            with self.subTest(profile=profile):
                r = call("apply-rulesets.sh", "example/project", "--profile", profile, "--dry-run")
                self.assertEqual(r.returncode, 0, r.stderr)
                hard, merge = payload(r.stdout)
                self.assertEqual(hard["bypass_actors"], [])
                self.assertEqual(merge["bypass_actors"], [])
                pr = next(x["parameters"] for x in merge["rules"] if x["type"] == "pull_request")
                self.assertEqual(pr["required_approving_review_count"], 0)
                self.assertTrue(pr["required_review_thread_resolution"])
                checks = next(x["parameters"] for x in merge["rules"] if x["type"] == "required_status_checks")
                self.assertTrue(checks["strict_required_status_checks_policy"])
                self.assertEqual(checks["required_status_checks"], [{"context":"test","integration_id":15368}])

    def test_custom_checks_override_default_and_deduplicate(self):
        r = call("apply-rulesets.sh", "example/private", "--profile", "private",
                 "--check", "lint", "--check", "validate", "--check", "lint", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        _, m = payload(r.stdout)
        checks = next(x["parameters"]["required_status_checks"] for x in m["rules"] if x["type"]=="required_status_checks")
        self.assertEqual(checks, [{"context":"lint","integration_id":15368},{"context":"validate","integration_id":15368}])

    def test_invalid_options_fail_before_accessing_github(self):
        for opts in (("--dry-run",), ("--profile", "internal", "--dry-run"),
                     ("--profile", "public", "--check", " ", "--dry-run")):
            with self.subTest(opts=opts):
                self.assertNotEqual(call("apply-rulesets.sh", "example/project", *opts).returncode, 0)

    def test_one_command_creation_for_both_profiles_offline(self):
        for profile in ("public", "private"):
            with self.subTest(profile=profile):
                r = call("create-protected-repository.sh", "example/project", "--profile", profile,
                         "--template", "example/language-template", "--check", "unit", "--dry-run")
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn("--"+profile, r.stdout)
                _, m = payload(r.stdout)
                checks = next(x["parameters"]["required_status_checks"] for x in m["rules"] if x["type"]=="required_status_checks")
                self.assertEqual(checks, [{"context":"unit","integration_id":15368}])

    def test_one_command_requires_project_template(self):
        r = call("create-protected-repository.sh", "example/project", "--profile", "public", "--dry-run")
        self.assertNotEqual(r.returncode, 0)

if __name__ == "__main__":
    unittest.main()
