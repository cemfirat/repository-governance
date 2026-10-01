import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "wordpress-plugin-pr-orchestrator.py"
)
spec = importlib.util.spec_from_file_location(
    "wordpress_plugin_pr_orchestrator",
    SCRIPT_PATH,
)
orchestrator = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(orchestrator)


OLD_PIN = "618316d349c753bd7527e56183497aefde57f473"
NEW_PIN = "8f3cb9d0ba9bfdb95d5a3510a5293950b523f10a"


def entry(rollout="enrolled"):
    return {
        "repository": "cemfirat/example-plugin",
        "default_branch": "main",
        "desired_profile": "simple",
        "rollout": rollout,
    }


def manifest():
    return {
        "schema_version": 1,
        "blueprint": "wordpress-plugin",
        "blueprint_version": "0.1.0",
        "profile": "simple",
        "plugin": {
            "slug": "example-plugin",
            "name": "Example Plugin",
            "main_file": "example-plugin.php",
            "version": "1.0.0",
            "text_domain": "example-plugin",
            "minimum_wordpress": "6.5",
            "minimum_php": "8.0",
            "author": "Cem Firat",
            "license": "GPL-2.0-or-later",
            "license_header": "GPL-2.0-or-later",
        },
    }


def releases():
    return {
        "blueprint": "wordpress-plugin",
        "releases": {
            "0.2.0": {
                "audit_action_sha": NEW_PIN,
                "supported_from": ["0.1.0"],
            }
        },
    }


def workflow(pin=OLD_PIN):
    return (
        "name: WordPress plugin blueprint\n"
        "jobs:\n"
        "  blueprint:\n"
        "    steps:\n"
        "      - uses: "
        "cemfirat/repository-governance/blueprints/wordpress-plugin@"
        + pin
        + "\n"
    )


class FakeClient:
    def __init__(self, current_manifest, current_workflow):
        self.current_manifest = current_manifest
        self.current_workflow = current_workflow
        self.calls = []
        self.existing_branch = False
        self.staged_files = {}
        self.check_run_values = [
            {
                "name": "Branch CI",
                "status": "completed",
                "conclusion": "success",
            }
        ]
        self.legacy_state = None
        self.legacy_statuses = []

    def branch_exists(self, repository, branch):
        self.calls.append(("branch_exists", repository, branch))
        return self.existing_branch

    def branch_head(self, repository, branch):
        self.calls.append(("branch_head", repository, branch))
        return "a" * 40

    def get_file(self, repository, path, ref):
        self.calls.append(("get_file", repository, path, ref))
        if ref != "main" and (ref, path) in self.staged_files:
            return self.staged_files[(ref, path)], "d" * 40
        if path == orchestrator.MANIFEST_PATH:
            return json.dumps(self.current_manifest, indent=2) + "\n", "b" * 40
        if path == orchestrator.WORKFLOW_PATH:
            return self.current_workflow, "c" * 40
        raise AssertionError(path)

    def create_branch(self, repository, branch, base_sha):
        self.calls.append(("create_branch", repository, branch, base_sha))
        self.existing_branch = True

    def update_file(self, repository, path, content, sha, branch, message):
        self.calls.append(
            ("update_file", repository, path, sha, branch, message)
        )
        self.staged_files[(branch, path)] = content

    def check_runs(self, repository, sha):
        self.calls.append(("check_runs", repository, sha))
        return self.check_run_values

    def combined_status(self, repository, sha):
        self.calls.append(("combined_status", repository, sha))
        return self.legacy_state, self.legacy_statuses

    def create_pull_request(
        self,
        repository,
        title,
        head,
        base_branch,
        body,
    ):
        self.calls.append(
            (
                "create_pull_request",
                repository,
                title,
                head,
                base_branch,
            )
        )
        return "https://github.com/cemfirat/example-plugin/pull/1"


class OrchestratorTests(unittest.TestCase):
    def test_known_migration_builds_allowlisted_change_set(self):
        value = orchestrator.build_change_set(
            entry(),
            manifest(),
            workflow(),
            "0.2.0",
            releases(),
        )

        self.assertEqual("safe-upgrade", value["status"])
        self.assertTrue(value["safe_to_apply"])
        self.assertEqual(
            {
                orchestrator.MANIFEST_PATH,
                orchestrator.WORKFLOW_PATH,
            },
            {item["path"] for item in value["changes"]},
        )

        manifest_change = next(
            item
            for item in value["changes"]
            if item["path"] == orchestrator.MANIFEST_PATH
        )
        updated = json.loads(manifest_change["content"])
        self.assertEqual("0.2.0", updated["blueprint_version"])
        self.assertEqual(".", updated["plugin"]["root"])
        self.assertEqual(
            "managed-gpl",
            updated["plugin"]["license_mode"],
        )

        workflow_change = next(
            item
            for item in value["changes"]
            if item["path"] == orchestrator.WORKFLOW_PATH
        )
        self.assertIn(NEW_PIN, workflow_change["content"])
        self.assertNotIn(OLD_PIN, workflow_change["content"])

    def test_manifest_actions_reject_unallowlisted_path(self):
        with self.assertRaises(orchestrator.OrchestratorError):
            orchestrator.apply_manifest_actions(
                manifest(),
                [
                    {
                        "operation": "set",
                        "path": "plugin.version",
                        "from": "1.0.0",
                        "to": "2.0.0",
                    }
                ],
            )

    def test_workflow_requires_exactly_one_central_pin(self):
        with self.assertRaises(orchestrator.OrchestratorError):
            orchestrator.update_workflow_pin("name: x\n", NEW_PIN)

    def test_paused_repository_is_not_safe(self):
        value = orchestrator.build_change_set(
            entry(rollout="paused"),
            None,
            None,
            "0.2.0",
            releases(),
        )
        self.assertEqual("paused", value["status"])
        self.assertFalse(value["safe_to_apply"])

    def test_apply_stages_branch_without_opening_pr(self):
        current = manifest()
        change_set = orchestrator.build_change_set(
            entry(),
            current,
            workflow(),
            "0.2.0",
            releases(),
        )
        client = FakeClient(current, workflow())

        result = orchestrator.apply_change_set(
            client,
            entry(),
            current,
            workflow(),
            change_set,
        )

        self.assertEqual("branch-ready-for-ci", result["status"])
        self.assertIsNone(result["pull_request"])
        updated_paths = [
            call[2]
            for call in client.calls
            if call[0] == "update_file"
        ]
        self.assertEqual(
            [
                orchestrator.MANIFEST_PATH,
                orchestrator.WORKFLOW_PATH,
            ],
            updated_paths,
        )
        self.assertTrue(
            any(call[0] == "create_branch" for call in client.calls)
        )
        self.assertFalse(
            any(call[0] == "create_pull_request" for call in client.calls)
        )

    def test_open_pr_requires_and_accepts_green_branch_ci(self):
        current = manifest()
        change_set = orchestrator.build_change_set(
            entry(),
            current,
            workflow(),
            "0.2.0",
            releases(),
        )
        client = FakeClient(current, workflow())
        orchestrator.apply_change_set(
            client,
            entry(),
            current,
            workflow(),
            change_set,
        )

        result = orchestrator.open_pull_request_after_green_ci(
            client,
            entry(),
            change_set,
        )

        self.assertEqual("pull-request-created", result["status"])
        self.assertEqual("a" * 40, result["head_sha"])
        self.assertEqual(
            "https://github.com/cemfirat/example-plugin/pull/1",
            result["pull_request"],
        )
        self.assertTrue(
            any(call[0] == "check_runs" for call in client.calls)
        )

    def test_open_pr_refuses_pending_branch_ci(self):
        current = manifest()
        change_set = orchestrator.build_change_set(
            entry(),
            current,
            workflow(),
            "0.2.0",
            releases(),
        )
        client = FakeClient(current, workflow())
        orchestrator.apply_change_set(
            client,
            entry(),
            current,
            workflow(),
            change_set,
        )
        client.check_run_values = [
            {
                "name": "Branch CI",
                "status": "in_progress",
                "conclusion": None,
            }
        ]

        with self.assertRaises(orchestrator.OrchestratorError):
            orchestrator.open_pull_request_after_green_ci(
                client,
                entry(),
                change_set,
            )

        self.assertFalse(
            any(call[0] == "create_pull_request" for call in client.calls)
        )

    def test_apply_refuses_existing_propagation_branch(self):
        current = manifest()
        change_set = orchestrator.build_change_set(
            entry(),
            current,
            workflow(),
            "0.2.0",
            releases(),
        )
        client = FakeClient(current, workflow())
        client.existing_branch = True

        with self.assertRaises(orchestrator.OrchestratorError):
            orchestrator.apply_change_set(
                client,
                entry(),
                current,
                workflow(),
                change_set,
            )

        self.assertFalse(
            any(call[0] == "update_file" for call in client.calls)
        )

    def test_apply_refuses_manifest_changed_after_planning(self):
        planned = manifest()
        live = manifest()
        live["plugin"]["version"] = "1.0.1"
        change_set = orchestrator.build_change_set(
            entry(),
            planned,
            workflow(),
            "0.2.0",
            releases(),
        )
        client = FakeClient(live, workflow())

        with self.assertRaises(orchestrator.OrchestratorError):
            orchestrator.apply_change_set(
                client,
                entry(),
                planned,
                workflow(),
                change_set,
            )

        self.assertFalse(
            any(call[0] == "create_branch" for call in client.calls)
        )

    def test_release_metadata_validation_requires_sha(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "releases.json"
            path.write_text(
                json.dumps(
                    {
                        "blueprint": "wordpress-plugin",
                        "releases": {
                            "0.2.0": {
                                "audit_action_sha": "main",
                                "supported_from": ["0.1.0"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(orchestrator.OrchestratorError):
                orchestrator.load_releases(path)

    def test_cli_parser_requires_repository(self):
        parser = orchestrator.build_parser()
        args = parser.parse_args(
            ["--repository", "cemfirat/example-plugin"]
        )
        self.assertEqual("cemfirat/example-plugin", args.repository)
        self.assertFalse(args.apply)
        self.assertFalse(args.open_pr)


if __name__ == "__main__":
    unittest.main()
