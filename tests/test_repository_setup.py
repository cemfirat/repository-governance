"""Offline tests for the safe single-command GitHub repository setup."""
import copy
import sys
import unittest
from contextlib import redirect_stdout
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

    def test_preview_and_all_are_read_only(self):
        gh = FakeGitHub()
        with redirect_stdout(StringIO()) as output:
            self.assertEqual(setup.cli([gh.name, "--dry-run"], gh), 0)
            self.assertEqual(setup.cli(["--all", "--owner", "cemfirat"], gh), 0)
        self.assertIn("ausschliesslich lesend", output.getvalue())
        self.assertEqual(gh.writes, [])


if __name__ == "__main__":
    unittest.main()
