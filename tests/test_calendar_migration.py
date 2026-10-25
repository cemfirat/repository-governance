"""Offline tests for the explicitly authorised legacy Calendar Booking migration."""
import copy
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import migrate_calendar_booking as migration
from repository_setup import SetupError, safe_payload


def legacy_ruleset():
    checks = [{"context": name, "integration_id": 15368}
              for name in sorted(migration.EXPECTED_CHECKS)]
    return {
        "id": migration.RULESET_ID,
        "source_type": "Repository",
        "updated_at": "2026-10-25T15:00:00Z",
        "name": migration.RULESET_NAME,
        "target": "branch",
        "enforcement": "active",
        "bypass_actors": [copy.deepcopy(migration.EXPECTED_BYPASS)],
        "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {"type": "pull_request", "parameters": {
                "required_approving_review_count": 0,
                "dismiss_stale_reviews_on_push": False,
                "required_reviewers": [],
                "require_code_owner_review": False,
                "require_last_push_approval": False,
                "required_review_thread_resolution": False,
                "require_extra_approval_for_unattributed_changes": True,
                "allowed_merge_methods": ["merge", "squash", "rebase"]}},
            {"type": "required_status_checks", "parameters": {
                "strict_required_status_checks_policy": True,
                "do_not_enforce_on_create": False,
                "required_status_checks": checks}}
        ],
    }


class FakeCalendarGitHub:
    def __init__(self):
        self.rule = legacy_ruleset()
        self.sha = "a" * 40
        self.writes = []
        self.visibility = "public"
        self.repo = migration.REPO

    def get(self, path):
        base = "repos/" + self.repo
        if path == base:
            return {"visibility": self.visibility, "default_branch": "main",
                    "archived": False, "disabled": False, "fork": False}
        if path == base + "/branches/main":
            return {"commit": {"sha": self.sha}}
        if path == base + "/rulesets?per_page=100":
            return [{"id": migration.RULESET_ID, "name": migration.RULESET_NAME}]
        if path == base + f"/rulesets/{migration.RULESET_ID}":
            return copy.deepcopy(self.rule)
        raise AssertionError("Unexpected GET " + path)

    def put(self, path, payload):
        self.writes.append((path, copy.deepcopy(payload)))
        self.rule.update(copy.deepcopy(payload))
        self.rule["updated_at"] = "2026-10-25T16:00:00Z"
        return {"id": migration.RULESET_ID}


class CalendarMigrationTests(unittest.TestCase):
    def test_plan_is_read_only_and_preserves_exact_eleven_checks(self):
        gh = FakeCalendarGitHub()
        before = copy.deepcopy(gh.rule)
        plan = migration.migrate_plan(gh)
        self.assertEqual(gh.rule, before)
        self.assertEqual(len(plan.checks), 11)
        self.assertEqual(plan.after["bypass_actors"], [])
        orig_pr = before["rules"][2]["parameters"]
        new_pr = plan.after["rules"][2]["parameters"]
        for key, val in orig_pr.items():
            self.assertEqual(new_pr[key], True if key == "required_review_thread_resolution" else val)
        self.assertEqual(plan.after["rules"][3], before["rules"][3])
        self.assertEqual(gh.writes, [])

    def test_exact_authorization_updates_only_original_ruleset(self):
        gh = FakeCalendarGitHub()
        with redirect_stdout(StringIO()) as output, patch("sys.stdin.isatty", return_value=True), \
                patch("builtins.input", return_value="KALENDER"):
            result = migration.cli([], gh)
        self.assertEqual(result, 0)
        self.assertEqual(len(gh.writes), 1)
        self.assertTrue(gh.writes[0][0].endswith("/rulesets/23837020"))
        self.assertIn("alle elf CI-Checks erhalten", output.getvalue())
        self.assertEqual(safe_payload(gh.rule)["bypass_actors"], [])
        self.assertEqual(len(gh.rule["rules"][3]["parameters"]["required_status_checks"]), 11)
        self.assertTrue(gh.rule["rules"][2]["parameters"]["required_review_thread_resolution"])

    def test_dry_run_never_writes_or_prompts(self):
        gh = FakeCalendarGitHub()
        with redirect_stdout(StringIO()), patch("builtins.input", side_effect=AssertionError("prompt")):
            self.assertEqual(migration.cli(["--dry-run"], gh), 0)
        self.assertEqual(gh.writes, [])

    def test_noninteractive_and_wrong_code_do_not_write(self):
        for tty, answer in ((False, "KALENDER"), (True, "ja")):
            with self.subTest(tty=tty):
                gh = FakeCalendarGitHub()
                with redirect_stdout(StringIO()), patch("sys.stdin.isatty", return_value=tty), \
                        patch("builtins.input", return_value=answer):
                    self.assertEqual(migration.cli([], gh), 0)
                self.assertEqual(gh.writes, [])

    def test_unexpected_ci_and_bypass_reject_without_writes(self):
        for mutation in ("checks", "bypass", "approval", "types", "visibility"):
            with self.subTest(mutation=mutation):
                gh = FakeCalendarGitHub()
                if mutation == "checks":
                    gh.rule["rules"][3]["parameters"]["required_status_checks"].pop()
                elif mutation == "bypass":
                    gh.rule["bypass_actors"].append({
                        "actor_id": 2, "actor_type": "RepositoryRole", "bypass_mode": "always"})
                elif mutation == "approval":
                    gh.rule["rules"][2]["parameters"]["required_approving_review_count"] = 1
                elif mutation == "types":
                    gh.rule["rules"].append({"type": "creation"})
                else:
                    gh.visibility = "private"
                with self.assertRaises(SetupError):
                    migration.migrate_plan(gh)
                self.assertEqual(gh.writes, [])

    def test_ruleset_or_main_changed_since_preview_aborts(self):
        for mutation in ("sha", "updated_at"):
            with self.subTest(mutation=mutation):
                gh = FakeCalendarGitHub()
                plan = migration.migrate_plan(gh)
                if mutation == "sha":
                    gh.sha = "b" * 40
                else:
                    gh.rule["updated_at"] = "2026-10-25T17:00:00Z"
                with self.assertRaisesRegex(SetupError, "seit der Vorschau"):
                    migration.save_calendar_plan(gh, plan)
                self.assertEqual(gh.writes, [])

    def test_idempotent_when_already_secured(self):
        gh = FakeCalendarGitHub()
        plan = migration.migrate_plan(gh)
        gh.rule.update(copy.deepcopy(plan.after))
        with redirect_stdout(StringIO()) as output:
            self.assertEqual(migration.cli([], gh), 0)
        self.assertIn("Kein Handlungsbedarf", output.getvalue())
        self.assertEqual(gh.writes, [])


if __name__ == "__main__":
    unittest.main()
