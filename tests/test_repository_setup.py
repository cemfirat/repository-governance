"""Offline tests for the safe single-command GitHub repository setup."""
import copy
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import repository_setup as setup


def rule(name, ident, *, checks=("test",), bypass=False, resolution=True, approvals=0):
    filename = ("main-protection-hard-guardrails.json" if name == setup.HARD_NAME
                else "main-protection-merge-gates-base.json")
    value = setup.read_template(filename)
    value.update(id=ident, source_type="Repository", updated_at="2026-10-25T14:00:00Z")
    if bypass:
        value["bypass_actors"] = [
            {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
        ]
    if name == setup.MERGE_NAME:
        pr = next(x["parameters"] for x in value["rules"] if x["type"] == "pull_request")
        ci = next(x["parameters"] for x in value["rules"] if x["type"] == "required_status_checks")
        pr["required_approving_review_count"] = approvals
        pr["required_review_thread_resolution"] = resolution
        ci["required_status_checks"] = [
            {"context": name, "integration_id": 15368} for name in checks
        ]
    return value


class FakeGitHub:
    def __init__(self, *, visibility="private", default="main", rules=(), ci=("test",), app=15368):
        self.name = "cemfirat/example"
        self.visibility = visibility
        self.default = default
        self.rules = {x["id"]: copy.deepcopy(x) for x in rules}
        self.ci = ci
        self.app = app
        self.main_sha = "a" * 40
        self.classic = False
        self.writes = []
        self.next_id = 900

    def get(self, path):
        base = "repos/" + self.name
        if path == "user":
            return {"login": "cemfirat"}
        if path == base:
            return {"default_branch": self.default, "visibility": self.visibility,
                    "archived": False, "disabled": False, "fork": False}
        if path == base + "/branches/main":
            return {"commit": {"sha": self.main_sha},
                    "protected": self.classic or bool(self.rules)}
        if path == base + "/rulesets?per_page=100":
            return [{"id": x["id"], "name": x["name"]} for x in self.rules.values()]
        if path.startswith(base + "/rulesets/"):
            return copy.deepcopy(self.rules[int(path.rsplit("/", 1)[-1])])
        if path == base + "/actions/runs?event=pull_request&per_page=30":
            return {"workflow_runs": [] if self.ci is None else [{
                "id": 555, "head_sha": "b" * 40,
                "event": "pull_request", "conclusion": "success"}]}
        if path == base + "/actions/runs/555/jobs?per_page=100":
            return {"jobs": [{"name": n, "conclusion": "success"} for n in self.ci],
                    "total_count": len(self.ci)}
        if path == base + "/commits/" + "b" * 40 + "/check-runs?per_page=100":
            return {"check_runs": [
                {"name": n, "conclusion": "success", "app": {"id": self.app}}
                for n in self.ci], "total_count": len(self.ci)}
        raise AssertionError("Unexpected read " + path)

    def post(self, path, payload):
        return self.write("POST", path, payload)

    def put(self, path, payload):
        return self.write("PUT", path, payload)

    def write(self, verb, path, payload):
        self.writes.append(verb)
        ident = self.next_id if verb == "POST" else int(path.rsplit("/", 1)[-1])
        if verb == "POST":
            self.next_id += 1
        self.rules[ident] = {
            "id": ident, "source_type": "Repository",
            "updated_at": "2026-10-25T15:00:00Z", **copy.deepcopy(payload)
        }
        return {"id": ident}

    def list_owned_repositories(self, owner):
        return [self.name]


class SafeSetupTests(unittest.TestCase):
    def test_public_and_private_clean_repos_do_not_write(self):
        for visibility in ("public", "private"):
            with self.subTest(visibility=visibility):
                gh = FakeGitHub(visibility=visibility, rules=(
                    rule(setup.HARD_NAME, 1), rule(setup.MERGE_NAME, 2)))
                plan = setup.inspect(gh, gh.name)
                self.assertEqual(plan.visibility, visibility)
                self.assertFalse(plan.blockers)
                self.assertFalse(plan.actions)

    def test_creates_two_rulesets_only_with_real_proven_pr_ci(self):
        gh = FakeGitHub(visibility="public", ci=("test", "lint"))
        plan = setup.inspect(gh, gh.name)
        self.assertFalse(plan.blockers)
        self.assertEqual([x.operation for x in plan.actions], ["POST", "POST"])
        self.assertEqual([x["context"] for x in setup.required_checks(plan.actions[1].payload)],
                         ["test"])
        with redirect_stdout(StringIO()):
            setup.apply_plan(gh, plan, [])
        self.assertEqual(gh.writes, ["POST", "POST"])
        self.assertEqual(gh.rules[901]["bypass_actors"], [])

    def test_no_ci_never_install_dummy_required_test(self):
        gh = FakeGitHub(ci=None)
        plan = setup.inspect(gh, gh.name)
        self.assertTrue(plan.blockers)
        self.assertEqual(plan.actions, [])
        self.assertEqual(gh.writes, [])

    def test_ci_must_come_from_github_actions(self):
        gh = FakeGitHub(ci=("test",), app=1234)
        self.assertTrue(setup.inspect(gh, gh.name).blockers)

    def test_ambiguous_real_ci_requires_explicit_check(self):
        gh = FakeGitHub(ci=("PHP regression", "WordPress regression"))
        self.assertTrue(setup.inspect(gh, gh.name).blockers)
        selected = setup.inspect(gh, gh.name, ["PHP regression", "WordPress regression"])
        self.assertFalse(selected.blockers)
        self.assertEqual(len(setup.required_checks(selected.actions[1].payload)), 2)
        self.assertTrue(setup.inspect(gh, gh.name, ["pretend-green"]).blockers)

    def test_update_preserves_multiple_required_checks(self):
        gh = FakeGitHub(rules=(
            rule(setup.HARD_NAME, 1),
            rule(setup.MERGE_NAME, 2, checks=("php", "wordpress"),
                 bypass=True, resolution=False)))
        plan = setup.inspect(gh, gh.name)
        self.assertFalse(plan.blockers)
        self.assertEqual([x.operation for x in plan.actions], ["PUT"])
        with redirect_stdout(StringIO()):
            setup.apply_plan(gh, plan, [])
        self.assertEqual(gh.writes, ["PUT"])
        self.assertEqual(gh.rules[2]["bypass_actors"], [])
        self.assertEqual([x["context"] for x in setup.required_checks(gh.rules[2])],
                         ["php", "wordpress"])

    def test_existing_merge_without_ci_detects_actual_job(self):
        old = rule(setup.MERGE_NAME, 2)
        old["rules"] = [x for x in old["rules"] if x["type"] != "required_status_checks"]
        gh = FakeGitHub(rules=(rule(setup.HARD_NAME, 1), old), ci=("project-test",))
        plan = setup.inspect(gh, gh.name)
        self.assertFalse(plan.blockers)
        self.assertEqual([x["context"] for x in setup.required_checks(plan.actions[0].payload)],
                         ["project-test"])

    def test_existing_approvals_cannot_be_removed(self):
        gh = FakeGitHub(rules=(rule(setup.MERGE_NAME, 2, approvals=1),))
        self.assertTrue(setup.inspect(gh, gh.name).blockers)
        self.assertEqual(gh.writes, [])

    def test_special_rules_and_non_main_branches_stop(self):
        custom = rule(setup.MERGE_NAME, 2)
        custom["name"] = "other protections"
        self.assertTrue(setup.inspect(FakeGitHub(rules=(custom,)), "cemfirat/example").blockers)
        for branch in ("master", "develop"):
            gh = FakeGitHub(default=branch)
            self.assertTrue(setup.inspect(gh, gh.name).blockers)
        gh = FakeGitHub()
        gh.classic = True
        self.assertTrue(setup.inspect(gh, gh.name).blockers)

    def test_changed_remote_branch_aborts_before_any_write(self):
        gh = FakeGitHub(rules=(rule(setup.MERGE_NAME, 2, bypass=True),))
        plan = setup.inspect(gh, gh.name)
        gh.main_sha = "b" * 40
        with self.assertRaisesRegex(setup.SetupError, "seit der Vorschau"):
            setup.apply_plan(gh, plan, [])
        self.assertEqual(gh.writes, [])

    def test_branch_move_after_first_hard_guard_creation_prevents_second_write(self):
        gh = FakeGitHub(ci=("test",))
        plan = setup.inspect(gh, gh.name)
        old_post = gh.post
        def move_branch_after_first_post(path, payload):
            result = old_post(path, payload)
            gh.main_sha = "f" * 40
            return result
        gh.post = move_branch_after_first_post
        with self.assertRaisesRegex(setup.SetupError, "vor dem Schreiben"):
            setup.apply_plan(gh, plan, [])
        # The new hard guard remains in place, but no merge gate is silently
        # created against an unexpectedly changed branch.
        self.assertEqual(gh.writes, ["POST"])

    def test_preview_and_all_are_read_only(self):
        gh = FakeGitHub()
        with redirect_stdout(StringIO()) as output:
            self.assertEqual(setup.cli([gh.name, "--dry-run"], gh), 0)
            self.assertEqual(setup.cli(["--all", "--owner", "cemfirat"], gh), 0)
        self.assertIn("ausschliesslich lesend", output.getvalue())
        self.assertEqual(gh.writes, [])


class FleetFakeGitHub:
    """Route mock GitHub API calls to independent pretend repositories."""
    def __init__(self, children):
        self.children = {child.name: child for child in children}

    def get(self, path):
        if path == "user":
            return {"login": "cemfirat"}
        for name, child in self.children.items():
            if path == "repos/" + name or path.startswith("repos/" + name + "/"):
                return child.get(path)
        raise AssertionError("Unknown repository GET " + path)

    def post(self, path, payload):
        return self._write("post", path, payload)

    def put(self, path, payload):
        return self._write("put", path, payload)

    def _write(self, verb, path, payload):
        for name, child in self.children.items():
            if path.startswith("repos/" + name + "/"):
                return getattr(child, verb)(path, payload)
        raise AssertionError("Unknown repository write " + path)

    def list_owned_repositories(self, owner):
        assert owner == "cemfirat"
        return sorted(self.children)

    def all_writes(self):
        return {name: list(child.writes) for name, child in self.children.items()}


def sample_fleet():
    safe = FakeGitHub(rules=(
        rule(setup.HARD_NAME, 11),
        rule(setup.MERGE_NAME, 12, bypass=True)))
    safe.name = "cemfirat/a-safe"
    new = FakeGitHub(ci=("test",))
    new.name = "cemfirat/b-new"
    okay = FakeGitHub(rules=(
        rule(setup.HARD_NAME, 13),
        rule(setup.MERGE_NAME, 14)))
    okay.name = "cemfirat/c-okay"
    special = FakeGitHub(default="develop")
    special.name = "cemfirat/d-special"
    return FleetFakeGitHub((safe, new, okay, special))


class SafeBatchTests(unittest.TestCase):
    def test_fleet_preview_selects_only_safe_subset_and_is_read_only(self):
        gh = sample_fleet()
        with redirect_stdout(StringIO()) as out:
            names, plans = setup.preview_safe_batch(gh, "cemfirat")
        self.assertEqual(len(names), 4)
        self.assertEqual([p.name for p in plans], ["cemfirat/a-safe", "cemfirat/b-new"])
        self.assertIn("PRUEFEN", out.getvalue())
        self.assertIn("Pflichtchecks: test", out.getvalue())
        self.assertTrue(all(not actions for actions in gh.all_writes().values()))

    def test_dry_run_never_writes_or_prompts(self):
        gh = sample_fleet()
        with redirect_stdout(StringIO()), patch("builtins.input", side_effect=AssertionError("prompt")):
            result = setup.cli(["--apply-safe-all", "--dry-run"], gh)
        self.assertEqual(result, 0)
        self.assertTrue(all(not actions for actions in gh.all_writes().values()))

    def test_typing_only_ja_does_not_authorize_batch(self):
        gh = sample_fleet()
        with redirect_stdout(StringIO()), patch("sys.stdin.isatty", return_value=True), \
                patch("builtins.input", return_value="ja"):
            result = setup.cli(["--apply-safe-all"], gh)
        self.assertEqual(result, 0)
        self.assertTrue(all(not actions for actions in gh.all_writes().values()))

    def test_explicit_counted_approval_updates_only_two_repositories(self):
        gh = sample_fleet()
        with redirect_stdout(StringIO()) as out, patch("sys.stdin.isatty", return_value=True), \
                patch("builtins.input", return_value="ALLE 2"):
            result = setup.cli(["--apply-safe-all"], gh)
        self.assertEqual(result, 0)
        self.assertEqual(gh.children["cemfirat/a-safe"].writes, ["PUT"])
        self.assertEqual(gh.children["cemfirat/b-new"].writes, ["POST", "POST"])
        self.assertEqual(gh.children["cemfirat/c-okay"].writes, [])
        self.assertEqual(gh.children["cemfirat/d-special"].writes, [])
        self.assertIn("FERTIG: 2", out.getvalue())
        self.assertEqual(gh.children["cemfirat/a-safe"].rules[12]["bypass_actors"], [])
        self.assertEqual(
            setup.required_checks(gh.children["cemfirat/a-safe"].rules[12]),
            [{"context": "test", "integration_id": setup.GITHUB_ACTIONS_APP_ID}],
        )

    def test_non_interactive_always_refuses_writes(self):
        gh = sample_fleet()
        with redirect_stdout(StringIO()) as out, patch("sys.stdin.isatty", return_value=False), \
                patch("builtins.input", side_effect=AssertionError("prompt")):
            result = setup.cli(["--apply-safe-all"], gh)
        self.assertEqual(result, 0)
        self.assertIn("Kein interaktives Terminal", out.getvalue())
        self.assertTrue(all(not actions for actions in gh.all_writes().values()))

    def test_yes_and_other_unsafe_combinations_are_rejected(self):
        for bad in (["--apply-safe-all", "--yes"],
                    ["--apply-safe-all", "--check", "test"],
                    ["--apply-safe-all", "cemfirat/example"],
                    ["--apply-safe-all", "--all"]):
            with self.subTest(bad=bad):
                gh = sample_fleet()
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    result = setup.cli(bad, gh)
                self.assertNotEqual(result, 0)
                self.assertTrue(all(not actions for actions in gh.all_writes().values()))

    def test_fleet_changed_during_confirmation_aborts_all(self):
        gh = sample_fleet()
        old_list = gh.list_owned_repositories
        calls = [0]
        def changed_list(owner):
            calls[0] += 1
            items = old_list(owner)
            if calls[0] == 2:
                return items[:-1]
            return items
        gh.list_owned_repositories = changed_list
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()), \
                patch("sys.stdin.isatty", return_value=True), \
                patch("builtins.input", return_value="ALLE 2"):
            result = setup.cli(["--apply-safe-all"], gh)
        self.assertNotEqual(result, 0)
        self.assertTrue(all(not actions for actions in gh.all_writes().values()))

    def test_first_repo_race_stops_before_any_write(self):
        gh = sample_fleet()
        def race(_prompt):
            gh.children["cemfirat/a-safe"].main_sha = "f" * 40
            return "ALLE 2"
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()), \
                patch("sys.stdin.isatty", return_value=True), \
                patch("builtins.input", side_effect=race):
            result = setup.cli(["--apply-safe-all"], gh)
        self.assertEqual(result, 1)
        self.assertTrue(all(not actions for actions in gh.all_writes().values()))

    def test_later_repo_race_stops_and_retains_only_verified_first(self):
        gh = sample_fleet()
        old_put = gh.children["cemfirat/a-safe"].put
        def move_next_repo_on_first_put(path, payload):
            result = old_put(path, payload)
            gh.children["cemfirat/b-new"].main_sha = "f" * 40
            return result
        gh.children["cemfirat/a-safe"].put = move_next_repo_on_first_put
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()) as error, \
                patch("sys.stdin.isatty", return_value=True), \
                patch("builtins.input", return_value="ALLE 2"):
            result = setup.cli(["--apply-safe-all"], gh)
        self.assertEqual(result, 1)
        self.assertEqual(gh.children["cemfirat/a-safe"].writes, ["PUT"])
        self.assertEqual(gh.children["cemfirat/b-new"].writes, [])
        self.assertIn("Vorher erfolgreich: 1 von 2", error.getvalue())

    def test_all_command_is_still_strictly_read_only(self):
        gh = sample_fleet()
        with redirect_stdout(StringIO()), patch("builtins.input", side_effect=AssertionError("prompt")):
            result = setup.cli(["--all"], gh)
        self.assertEqual(result, 0)
        self.assertTrue(all(not actions for actions in gh.all_writes().values()))


class MultiWorkflowEvidenceFake(FakeGitHub):
    """Three successful workflows on one PR SHA, plus irrelevant old PR evidence."""
    def get(self, path):
        base = "repos/" + self.name
        head = "b" * 40
        if path == base + "/actions/runs?event=pull_request&per_page=30":
            return {"workflow_runs": [
                {"id": 301, "head_sha": head, "event": "pull_request", "conclusion": "success"},
                {"id": 302, "head_sha": head, "event": "pull_request", "conclusion": "success"},
                {"id": 303, "head_sha": head, "event": "pull_request", "conclusion": "success"},
                {"id": 201, "head_sha": "c" * 40, "event": "pull_request", "conclusion": "success"},
            ]}
        known = {
            301: "PHP 8.3 regression",
            302: "Official WordPress Plugin Check",
            303: "WordPress plugin blueprint",
            201: "Outdated unrelated check",
        }
        for run_id, job in known.items():
            if path == base + f"/actions/runs/{run_id}/jobs?per_page=100":
                return {"jobs": [{"name": job, "conclusion": "success"}], "total_count": 1}
        if path == base + "/commits/" + head + "/check-runs?per_page=100":
            return {"check_runs": [
                {"name": name, "conclusion": "success", "app": {"id": 15368}}
                for name in (known[301], known[302], known[303])
            ] + [{"name": "External app", "conclusion": "success", "app": {"id": 999}}],
                    "total_count": 4}
        return super().get(path)


class MultiWorkflowEvidenceTests(unittest.TestCase):
    def test_successful_jobs_from_same_pr_sha_are_aggregated(self):
        gh = MultiWorkflowEvidenceFake()
        wanted = ["Official WordPress Plugin Check",
                  "PHP 8.3 regression", "WordPress plugin blueprint"]
        self.assertEqual(setup.successful_pr_checks(gh, gh.name), wanted)
        plan = setup.inspect(gh, gh.name, requested_checks=wanted)
        self.assertFalse(plan.blockers)
        self.assertEqual([x["context"] for x in setup.required_checks(plan.actions[1].payload)],
                         wanted)

    def test_different_pr_shas_and_external_apps_are_not_mixed(self):
        gh = MultiWorkflowEvidenceFake()
        allowed = setup.successful_pr_checks(gh, gh.name)
        self.assertNotIn("Outdated unrelated check", allowed)
        self.assertNotIn("External app", allowed)
        rejected = setup.inspect(gh, gh.name, requested_checks=["Outdated unrelated check"])
        self.assertTrue(rejected.blockers)
        self.assertEqual(rejected.actions, [])


if __name__ == "__main__":
    unittest.main()
