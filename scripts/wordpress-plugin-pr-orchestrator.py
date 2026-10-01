#!/usr/bin/env python3
"""Guarded cross-repository PR orchestrator for WordPress blueprint upgrades.

Dry-run is the default. Write mode is intentionally narrow:
- exactly one target repository;
- only a fleet repository not marked paused;
- only proposals classified safe-upgrade;
- only the blueprint manifest and blueprint audit workflow may be changed;
- --apply creates the propagation branch and stages the reviewed changes only;
- --open-pr refuses to open a pull request until branch CI is fully green;
- the tool never merges a pull request.
"""

from __future__ import annotations

import argparse
import base64
import copy
import importlib.util
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

def _load_module(name: str, filename: str):
    path = SCRIPT_DIR / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module

fleet = _load_module("wordpress_plugin_fleet", "wordpress-plugin-fleet.py")
planner = _load_module(
    "wordpress_plugin_upgrade_plan",
    "wordpress-plugin-upgrade-plan.py",
)

MANIFEST_PATH = ".ccf-wordpress-plugin.json"
WORKFLOW_PATH = ".github/workflows/blueprint.yml"
ALLOWED_MANIFEST_PATHS = {
    "blueprint_version",
    "plugin.root",
    "plugin.license_mode",
}
ACTION_USE_RE = re.compile(
    r"(uses:\s*cemfirat/repository-governance/blueprints/wordpress-plugin@)"
    r"([0-9a-f]{40})"
)


class OrchestratorError(Exception):
    """Safety, configuration, or GitHub API error."""


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OrchestratorError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise OrchestratorError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise OrchestratorError(f"Expected JSON object in {path}")
    return value


def load_releases(path: Path) -> dict:
    data = read_json(path)
    if data.get("blueprint") != fleet.BLUEPRINT_ID:
        raise OrchestratorError("release metadata blueprint id mismatch")
    releases = data.get("releases")
    if not isinstance(releases, dict) or not releases:
        raise OrchestratorError("release metadata must contain releases")
    for version, meta in releases.items():
        if not isinstance(meta, dict):
            raise OrchestratorError(f"release {version} must be an object")
        sha = meta.get("audit_action_sha")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise OrchestratorError(
                f"release {version} has invalid audit_action_sha"
            )
        supported = meta.get("supported_from")
        if not isinstance(supported, list):
            raise OrchestratorError(
                f"release {version} supported_from must be an array"
            )
    return data


def find_inventory_entry(inventory: dict, repository: str) -> dict:
    matches = [
        entry
        for entry in inventory["repositories"]
        if entry["repository"] == repository
    ]
    if not matches:
        raise OrchestratorError(
            f"Repository not present in fleet inventory: {repository}"
        )
    if len(matches) != 1:
        raise OrchestratorError(
            f"Repository appears more than once in fleet inventory: {repository}"
        )
    return matches[0]


def get_nested(value: dict, path: str):
    current = value
    parts = path.split(".")
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def set_nested(value: dict, path: str, new_value) -> None:
    current = value
    parts = path.split(".")
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            raise OrchestratorError(
                f"Cannot set {path}: parent {part} is not an object"
            )
        current = child
    current[parts[-1]] = new_value


def apply_manifest_actions(manifest: dict, actions: list[dict]) -> dict:
    updated = copy.deepcopy(manifest)
    for action in actions:
        if action.get("operation") != "set":
            raise OrchestratorError(
                f"Unsupported proposal operation: {action.get('operation')!r}"
            )
        path = action.get("path")
        if path not in ALLOWED_MANIFEST_PATHS:
            raise OrchestratorError(
                f"Proposal attempts non-allow-listed manifest path: {path!r}"
            )
        actual = get_nested(updated, path)
        expected = action.get("from")
        if actual != expected:
            raise OrchestratorError(
                f"Manifest drift at {path}: found {actual!r}, "
                f"proposal expected {expected!r}"
            )
        set_nested(updated, path, action.get("to"))
    return updated


def update_workflow_pin(text: str, target_sha: str) -> str:
    matches = list(ACTION_USE_RE.finditer(text))
    if len(matches) != 1:
        raise OrchestratorError(
            "blueprint workflow must contain exactly one pinned central action"
        )
    current_sha = matches[0].group(2)
    if current_sha == target_sha:
        return text
    return ACTION_USE_RE.sub(
        lambda match: match.group(1) + target_sha,
        text,
        count=1,
    )


def build_change_set(
    entry: dict,
    manifest: dict | None,
    workflow_text: str | None,
    target_version: str,
    release_metadata: dict,
) -> dict:
    proposal = planner.propose(entry, manifest, target_version)
    result = {
        "repository": entry["repository"],
        "status": proposal["status"],
        "safe_to_apply": False,
        "target_blueprint_version": target_version,
        "changes": [],
        "notes": list(proposal.get("notes", [])),
    }

    if proposal["status"] == "current":
        result["safe_to_apply"] = True
        return result

    if proposal["status"] != "safe-upgrade" or not proposal["safe_to_apply"]:
        return result

    assert manifest is not None
    current_version = manifest.get("blueprint_version")
    release = release_metadata["releases"].get(target_version)
    if not isinstance(release, dict):
        result["status"] = "manual-review"
        result["notes"].append(
            f"no release metadata exists for {target_version}"
        )
        return result
    if current_version not in release.get("supported_from", []):
        result["status"] = "manual-review"
        result["notes"].append(
            f"release {target_version} does not list {current_version} "
            "as a supported migration source"
        )
        return result
    if workflow_text is None:
        result["status"] = "manual-review"
        result["notes"].append(
            f"required workflow is missing: {WORKFLOW_PATH}"
        )
        return result

    try:
        updated_manifest = apply_manifest_actions(
            manifest,
            proposal["actions"],
        )
        updated_workflow = update_workflow_pin(
            workflow_text,
            release["audit_action_sha"],
        )
    except OrchestratorError as exc:
        result["status"] = "manual-review"
        result["notes"].append(str(exc))
        return result

    manifest_text = json.dumps(updated_manifest, indent=2) + "\n"
    original_manifest_text = json.dumps(manifest, indent=2) + "\n"
    if manifest_text != original_manifest_text:
        result["changes"].append(
            {
                "path": MANIFEST_PATH,
                "kind": "manifest",
                "content": manifest_text,
            }
        )

    if updated_workflow != workflow_text:
        result["changes"].append(
            {
                "path": WORKFLOW_PATH,
                "kind": "workflow-pin",
                "content": updated_workflow,
            }
        )

    result["safe_to_apply"] = True
    result["status"] = "safe-upgrade"
    return result


class GitHubClient:
    def __init__(
        self,
        token: str | None,
        api_base: str = "https://api.github.com",
        timeout: float = 15.0,
    ):
        self.token = token
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        *,
        allow_404: bool = False,
    ):
        url = self.api_base + path
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "cemfirat-wordpress-blueprint-orchestrator",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            if allow_404 and exc.code == 404:
                return None
            try:
                detail = exc.read().decode("utf-8", errors="replace")
            except Exception:
                detail = ""
            raise OrchestratorError(
                f"GitHub API HTTP {exc.code} for {method} {path}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise OrchestratorError(
                f"GitHub API request failed for {method} {path}: {exc.reason}"
            ) from exc
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise OrchestratorError(
                f"GitHub API returned invalid JSON for {method} {path}"
            ) from exc

    @staticmethod
    def _repo_path(repository: str) -> str:
        owner, name = repository.split("/", 1)
        return (
            "/repos/"
            + urllib.parse.quote(owner, safe="")
            + "/"
            + urllib.parse.quote(name, safe="")
        )

    def branch_head(self, repository: str, branch: str) -> str:
        base = self._repo_path(repository)
        encoded = urllib.parse.quote(f"heads/{branch}", safe="/")
        value = self._request("GET", f"{base}/git/ref/{encoded}")
        try:
            sha = value["object"]["sha"]
        except (KeyError, TypeError) as exc:
            raise OrchestratorError(
                f"Unexpected branch response for {repository}:{branch}"
            ) from exc
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise OrchestratorError("GitHub returned an invalid branch SHA")
        return sha

    def branch_exists(self, repository: str, branch: str) -> bool:
        base = self._repo_path(repository)
        encoded = urllib.parse.quote(f"heads/{branch}", safe="/")
        return (
            self._request(
                "GET",
                f"{base}/git/ref/{encoded}",
                allow_404=True,
            )
            is not None
        )

    def get_file(
        self,
        repository: str,
        path: str,
        ref: str,
    ) -> tuple[str, str]:
        base = self._repo_path(repository)
        encoded = urllib.parse.quote(path, safe="/")
        query = urllib.parse.urlencode({"ref": ref})
        value = self._request(
            "GET",
            f"{base}/contents/{encoded}?{query}",
            allow_404=True,
        )
        if value is None:
            raise OrchestratorError(
                f"Required file is missing in {repository}: {path}"
            )
        try:
            sha = value["sha"]
            encoding = value["encoding"]
            raw = value["content"]
        except (KeyError, TypeError) as exc:
            raise OrchestratorError(
                f"Unexpected contents response for {repository}:{path}"
            ) from exc
        if encoding != "base64":
            raise OrchestratorError(
                f"Unexpected content encoding for {repository}:{path}"
            )
        try:
            text = base64.b64decode(raw).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise OrchestratorError(
                f"Could not decode {repository}:{path}"
            ) from exc
        return text, sha

    def create_branch(
        self,
        repository: str,
        branch: str,
        base_sha: str,
    ) -> None:
        base = self._repo_path(repository)
        self._request(
            "POST",
            f"{base}/git/refs",
            {"ref": f"refs/heads/{branch}", "sha": base_sha},
        )

    def update_file(
        self,
        repository: str,
        path: str,
        content: str,
        sha: str,
        branch: str,
        message: str,
    ) -> None:
        base = self._repo_path(repository)
        encoded = urllib.parse.quote(path, safe="/")
        self._request(
            "PUT",
            f"{base}/contents/{encoded}",
            {
                "message": message,
                "content": base64.b64encode(
                    content.encode("utf-8")
                ).decode("ascii"),
                "sha": sha,
                "branch": branch,
            },
        )

    def check_runs(self, repository: str, sha: str) -> list[dict]:
        base = self._repo_path(repository)
        value = self._request(
            "GET",
            f"{base}/commits/{urllib.parse.quote(sha, safe='')}/check-runs?per_page=100",
        )
        runs = value.get("check_runs") if isinstance(value, dict) else None
        if not isinstance(runs, list):
            raise OrchestratorError("GitHub returned invalid check-runs data")
        return runs

    def combined_status(self, repository: str, sha: str) -> tuple[str | None, list[dict]]:
        base = self._repo_path(repository)
        value = self._request(
            "GET",
            f"{base}/commits/{urllib.parse.quote(sha, safe='')}/status?per_page=100",
        )
        if not isinstance(value, dict):
            raise OrchestratorError("GitHub returned invalid commit-status data")
        statuses = value.get("statuses", [])
        state = value.get("state")
        if not isinstance(statuses, list):
            raise OrchestratorError("GitHub returned invalid legacy status list")
        if state is not None and not isinstance(state, str):
            raise OrchestratorError("GitHub returned invalid combined status state")
        return state, statuses

    def create_pull_request(
        self,
        repository: str,
        title: str,
        head: str,
        base_branch: str,
        body: str,
    ) -> str:
        base = self._repo_path(repository)
        value = self._request(
            "POST",
            f"{base}/pulls",
            {
                "title": title,
                "head": head,
                "base": base_branch,
                "body": body,
                "maintainer_can_modify": True,
            },
        )
        url = value.get("html_url") if isinstance(value, dict) else None
        if not isinstance(url, str) or not url:
            raise OrchestratorError("GitHub did not return a pull request URL")
        return url


def branch_name_for(target_version: str) -> str:
    safe = target_version.replace(".", "-").replace("+", "-").replace("_", "-")
    return f"chore/wordpress-blueprint-{safe}"


def apply_change_set(
    client,
    entry: dict,
    manifest: dict,
    workflow_text: str,
    change_set: dict,
) -> dict:
    if change_set["status"] != "safe-upgrade":
        raise OrchestratorError(
            f"Refusing write for status {change_set['status']}"
        )
    if not change_set["safe_to_apply"]:
        raise OrchestratorError("Proposal is not marked safe_to_apply")
    if entry["rollout"] == "paused":
        raise OrchestratorError("Refusing write to a paused repository")
    if not change_set["changes"]:
        return {
            "repository": entry["repository"],
            "status": "no-change",
            "pull_request": None,
        }

    target_version = change_set["target_blueprint_version"]
    branch = branch_name_for(target_version)
    repository = entry["repository"]
    base_branch = entry["default_branch"]

    if client.branch_exists(repository, branch):
        raise OrchestratorError(
            f"Propagation branch already exists: {repository}:{branch}"
        )

    base_sha = client.branch_head(repository, base_branch)
    _, manifest_sha = client.get_file(
        repository,
        MANIFEST_PATH,
        base_branch,
    )
    _, workflow_sha = client.get_file(
        repository,
        WORKFLOW_PATH,
        base_branch,
    )

    # Re-check that the manifest used for planning is still the live manifest.
    live_manifest_text, _ = client.get_file(
        repository,
        MANIFEST_PATH,
        base_branch,
    )
    try:
        live_manifest = json.loads(live_manifest_text)
    except json.JSONDecodeError as exc:
        raise OrchestratorError("Live manifest became invalid JSON") from exc
    if live_manifest != manifest:
        raise OrchestratorError(
            "Target manifest changed after planning; regenerate proposal"
        )

    client.create_branch(repository, branch, base_sha)

    sha_by_path = {
        MANIFEST_PATH: manifest_sha,
        WORKFLOW_PATH: workflow_sha,
    }
    allowed_paths = {MANIFEST_PATH, WORKFLOW_PATH}

    for change in change_set["changes"]:
        path = change["path"]
        if path not in allowed_paths:
            raise OrchestratorError(
                f"Refusing non-allow-listed target path: {path}"
            )
        message = (
            "chore: upgrade WordPress blueprint to "
            f"{target_version}"
        )
        client.update_file(
            repository,
            path,
            change["content"],
            sha_by_path[path],
            branch,
            message,
        )

    return {
        "repository": repository,
        "status": "branch-ready-for-ci",
        "branch": branch,
        "base_sha": base_sha,
        "pull_request": None,
    }


def assert_green_branch_ci(client, repository: str, branch: str) -> str:
    head_sha = client.branch_head(repository, branch)
    check_runs = client.check_runs(repository, head_sha)
    combined_state, statuses = client.combined_status(repository, head_sha)

    if not check_runs and not statuses:
        raise OrchestratorError(
            "Refusing PR creation: no CI/status checks exist for the branch HEAD"
        )

    incomplete = [
        run.get("name", "<unnamed>")
        for run in check_runs
        if run.get("status") != "completed"
    ]
    if incomplete:
        raise OrchestratorError(
            "Refusing PR creation: branch CI is still running: "
            + ", ".join(sorted(incomplete))
        )

    accepted = {"success", "neutral", "skipped"}
    failed = [
        f"{run.get('name', '<unnamed>')}={run.get('conclusion')}"
        for run in check_runs
        if run.get("conclusion") not in accepted
    ]
    if failed:
        raise OrchestratorError(
            "Refusing PR creation: branch CI is not green: "
            + ", ".join(sorted(failed))
        )

    if statuses and combined_state != "success":
        raise OrchestratorError(
            "Refusing PR creation: legacy commit status is "
            f"{combined_state!r}, not 'success'"
        )

    return head_sha


def open_pull_request_after_green_ci(
    client,
    entry: dict,
    change_set: dict,
) -> dict:
    if change_set["status"] != "safe-upgrade":
        raise OrchestratorError(
            f"Refusing PR creation for status {change_set['status']}"
        )
    if not change_set["safe_to_apply"]:
        raise OrchestratorError("Proposal is not marked safe_to_apply")
    if entry["rollout"] == "paused":
        raise OrchestratorError("Refusing PR creation for a paused repository")
    if not change_set["changes"]:
        return {
            "repository": entry["repository"],
            "status": "no-change",
            "pull_request": None,
        }

    target_version = change_set["target_blueprint_version"]
    branch = branch_name_for(target_version)
    repository = entry["repository"]
    base_branch = entry["default_branch"]

    if not client.branch_exists(repository, branch):
        raise OrchestratorError(
            f"Propagation branch does not exist: {repository}:{branch}; "
            "run --apply first"
        )

    for change in change_set["changes"]:
        live_content, _ = client.get_file(
            repository,
            change["path"],
            branch,
        )
        if live_content != change["content"]:
            raise OrchestratorError(
                f"Propagation branch drift at {change['path']}; "
                "regenerate and restage the proposal"
            )

    head_sha = assert_green_branch_ci(client, repository, branch)
    pr_url = client.create_pull_request(
        repository,
        f"chore: upgrade WordPress blueprint to {target_version}",
        branch,
        base_branch,
        (
            "Automated blueprint upgrade proposal.\n\n"
            f"Target blueprint: `{target_version}`\n"
            f"Verified green branch HEAD: `{head_sha}`\n\n"
            "Safety boundaries:\n"
            "- generated from an explicitly safe migration\n"
            "- changes only blueprint control files\n"
            "- branch CI was fully green before this PR was opened\n"
            "- does not modify plugin feature code\n"
            "- does not merge automatically\n"
            "- target repository PR CI/review remains authoritative\n"
        ),
    )
    return {
        "repository": repository,
        "status": "pull-request-created",
        "branch": branch,
        "head_sha": head_sha,
        "pull_request": pr_url,
    }


def render_change_set(value: dict) -> str:
    lines = [
        f"{value['repository']}: {value['status']} "
        f"(safe={str(value['safe_to_apply']).lower()})"
    ]
    for change in value.get("changes", []):
        lines.append(f"- would update {change['path']}")
    for note in value.get("notes", []):
        lines.append(f"- note: {note}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    root = SCRIPT_DIR.parent
    parser.add_argument("--repository", required=True)
    parser.add_argument(
        "--inventory",
        type=Path,
        default=root
        / "blueprints"
        / "wordpress-plugin"
        / "inventory.json",
    )
    parser.add_argument(
        "--releases",
        type=Path,
        default=root
        / "blueprints"
        / "wordpress-plugin"
        / "releases.json",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Create and update the propagation branch, but do not open a PR.",
    )
    mode.add_argument(
        "--open-pr",
        action="store_true",
        help="Open the PR only after the staged branch CI is fully green.",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--read-token-env",
        default="CCF_FLEET_GITHUB_TOKEN",
    )
    parser.add_argument(
        "--write-token-env",
        default="CCF_BLUEPRINT_GITHUB_WRITE_TOKEN",
    )
    parser.add_argument(
        "--api-base",
        default="https://api.github.com",
    )
    parser.add_argument("--timeout", type=float, default=15.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        inventory = fleet.load_inventory(args.inventory.resolve())
        releases = load_releases(args.releases.resolve())
        entry = find_inventory_entry(inventory, args.repository)
        if entry["rollout"] == "paused":
            value = build_change_set(
                entry,
                None,
                None,
                inventory["target_blueprint_version"],
                releases,
            )
            if args.apply or args.open_pr:
                raise OrchestratorError(
                    "Write/PR mode is forbidden for paused repositories"
                )
        else:
            read_token = os.environ.get(args.read_token_env) or None
            reader = GitHubClient(
                read_token,
                api_base=args.api_base,
                timeout=args.timeout,
            )
            manifest_text, _ = reader.get_file(
                args.repository,
                MANIFEST_PATH,
                entry["default_branch"],
            )
            try:
                manifest = json.loads(manifest_text)
            except json.JSONDecodeError as exc:
                raise OrchestratorError(
                    "Target blueprint manifest is invalid JSON"
                ) from exc
            workflow_text, _ = reader.get_file(
                args.repository,
                WORKFLOW_PATH,
                entry["default_branch"],
            )
            value = build_change_set(
                entry,
                manifest,
                workflow_text,
                inventory["target_blueprint_version"],
                releases,
            )

            if args.apply or args.open_pr:
                write_token = os.environ.get(args.write_token_env)
                if not write_token:
                    mode_name = "--apply" if args.apply else "--open-pr"
                    raise OrchestratorError(
                        f"{mode_name} requires explicit token in "
                        f"{args.write_token_env}"
                    )
                writer = GitHubClient(
                    write_token,
                    api_base=args.api_base,
                    timeout=args.timeout,
                )
                if args.apply:
                    value = apply_change_set(
                        writer,
                        entry,
                        manifest,
                        workflow_text,
                        value,
                    )
                else:
                    value = open_pull_request_after_green_ci(
                        writer,
                        entry,
                        value,
                    )
    except (fleet.FleetError, OrchestratorError) as exc:
        if args.format == "json":
            print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(value, indent=2, sort_keys=True))
    else:
        if "safe_to_apply" in value:
            print(render_change_set(value))
        else:
            print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
