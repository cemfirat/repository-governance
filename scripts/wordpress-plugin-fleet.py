#!/usr/bin/env python3
"""Read-only fleet planner for Cem Firat WordPress plugin blueprint enrollment."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

SCHEMA_VERSION = 1
BLUEPRINT_ID = "wordpress-plugin"
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
PROFILES = {"simple", "application", "block"}
ROLLOUT_STATES = {"planned", "enrolled", "paused"}


class FleetError(Exception):
    """Invalid inventory or incomplete fleet inspection."""


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FleetError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise FleetError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise FleetError(f"Expected a JSON object in {path}")
    return value


def load_inventory(path: Path) -> dict:
    inventory = read_json(path)

    if inventory.get("schema_version") != SCHEMA_VERSION:
        raise FleetError(
            f"Unsupported schema_version {inventory.get('schema_version')!r}; "
            f"expected {SCHEMA_VERSION}"
        )
    if inventory.get("blueprint") != BLUEPRINT_ID:
        raise FleetError(
            f"Unsupported blueprint {inventory.get('blueprint')!r}; "
            f"expected {BLUEPRINT_ID!r}"
        )

    target_version = inventory.get("target_blueprint_version")
    if not isinstance(target_version, str) or not re.fullmatch(
        r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?",
        target_version,
    ):
        raise FleetError("target_blueprint_version must be a semantic version")

    repositories = inventory.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        raise FleetError("repositories must be a non-empty array")

    seen: set[str] = set()
    for index, entry in enumerate(repositories):
        prefix = f"repositories[{index}]"
        if not isinstance(entry, dict):
            raise FleetError(f"{prefix} must be an object")

        repository = entry.get("repository")
        if not isinstance(repository, str) or not REPOSITORY_RE.fullmatch(repository):
            raise FleetError(f"{prefix}.repository must be owner/name")
        if repository.lower() in seen:
            raise FleetError(f"Duplicate repository in inventory: {repository}")
        seen.add(repository.lower())

        branch = entry.get("default_branch")
        if not isinstance(branch, str) or not branch.strip():
            raise FleetError(f"{prefix}.default_branch must be non-empty")

        profile = entry.get("desired_profile")
        if profile not in PROFILES:
            raise FleetError(
                f"{prefix}.desired_profile must be one of {sorted(PROFILES)}"
            )

        rollout = entry.get("rollout")
        if rollout not in ROLLOUT_STATES:
            raise FleetError(
                f"{prefix}.rollout must be one of {sorted(ROLLOUT_STATES)}"
            )

    return inventory


def github_manifest_url(repository: str, branch: str, api_base: str) -> str:
    owner, name = repository.split("/", 1)
    path = urllib.parse.quote(".ccf-wordpress-plugin.json", safe="")
    owner_q = urllib.parse.quote(owner, safe="")
    name_q = urllib.parse.quote(name, safe="")
    query = urllib.parse.urlencode({"ref": branch})
    return (
        f"{api_base.rstrip('/')}/repos/{owner_q}/{name_q}/contents/{path}?{query}"
    )


def fetch_github_manifest(
    repository: str,
    branch: str,
    *,
    token: str | None = None,
    api_base: str = "https://api.github.com",
    timeout: float = 10.0,
) -> dict | None:
    url = github_manifest_url(repository, branch, api_base)
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "cemfirat-wordpress-plugin-fleet-planner",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise FleetError(
            f"GitHub API returned HTTP {exc.code} for {repository}"
        ) from exc
    except urllib.error.URLError as exc:
        raise FleetError(
            f"GitHub API request failed for {repository}: {exc.reason}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise FleetError(
            f"GitHub API returned invalid JSON for {repository}"
        ) from exc

    if not isinstance(payload, dict):
        raise FleetError(f"Unexpected GitHub response for {repository}")

    encoded = payload.get("content")
    encoding = payload.get("encoding")
    if not isinstance(encoded, str) or encoding != "base64":
        raise FleetError(
            f"Unexpected manifest content response for {repository}"
        )

    try:
        raw = base64.b64decode(encoded, validate=False).decode("utf-8")
        manifest = json.loads(raw)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FleetError(
            f"Invalid blueprint manifest in {repository}"
        ) from exc

    if not isinstance(manifest, dict):
        raise FleetError(
            f"Blueprint manifest in {repository} must be a JSON object"
        )
    return manifest


def classify(
    entry: dict,
    manifest: dict | None,
    target_version: str,
) -> dict:
    repository = entry["repository"]
    desired_profile = entry["desired_profile"]

    result = {
        "repository": repository,
        "rollout": entry["rollout"],
        "desired_profile": desired_profile,
        "target_blueprint_version": target_version,
        "status": "",
        "current_profile": None,
        "current_blueprint_version": None,
        "issues": [],
    }

    if manifest is None:
        result["status"] = "unenrolled"
        result["issues"].append("missing .ccf-wordpress-plugin.json")
        return result

    if manifest.get("schema_version") != 1:
        result["status"] = "invalid-manifest"
        result["issues"].append(
            f"unsupported schema_version {manifest.get('schema_version')!r}"
        )
        return result

    if manifest.get("blueprint") != BLUEPRINT_ID:
        result["status"] = "invalid-manifest"
        result["issues"].append(
            f"unexpected blueprint {manifest.get('blueprint')!r}"
        )
        return result

    current_profile = manifest.get("profile")
    current_version = manifest.get("blueprint_version")
    result["current_profile"] = current_profile
    result["current_blueprint_version"] = current_version

    if current_profile not in PROFILES:
        result["status"] = "invalid-manifest"
        result["issues"].append(
            f"invalid profile {current_profile!r}"
        )
        return result

    if not isinstance(current_version, str) or not re.fullmatch(
        r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?",
        current_version,
    ):
        result["status"] = "invalid-manifest"
        result["issues"].append(
            f"invalid blueprint_version {current_version!r}"
        )
        return result

    if current_profile != desired_profile:
        result["issues"].append(
            f"profile is {current_profile}; desired {desired_profile}"
        )

    if current_version != target_version:
        result["issues"].append(
            f"blueprint version is {current_version}; target {target_version}"
        )

    if current_profile != desired_profile:
        result["status"] = "profile-drift"
    elif current_version != target_version:
        result["status"] = "version-drift"
    else:
        result["status"] = "current"

    return result


def plan_inventory(
    inventory: dict,
    fetcher: Callable[[str, str], dict | None],
    repository_filter: set[str] | None = None,
) -> dict:
    target_version = inventory["target_blueprint_version"]
    results: list[dict] = []
    fetch_errors = 0

    for entry in inventory["repositories"]:
        repository = entry["repository"]
        if repository_filter and repository not in repository_filter:
            continue

        try:
            manifest = fetcher(repository, entry["default_branch"])
            result = classify(entry, manifest, target_version)
        except FleetError as exc:
            fetch_errors += 1
            result = {
                "repository": repository,
                "rollout": entry["rollout"],
                "desired_profile": entry["desired_profile"],
                "target_blueprint_version": target_version,
                "status": "fetch-error",
                "current_profile": None,
                "current_blueprint_version": None,
                "issues": [str(exc)],
            }
        results.append(result)

    if repository_filter:
        known = {entry["repository"] for entry in inventory["repositories"]}
        unknown = sorted(repository_filter - known)
        if unknown:
            raise FleetError(
                "Repositories not present in inventory: " + ", ".join(unknown)
            )

    counts: dict[str, int] = {}
    for item in results:
        counts[item["status"]] = counts.get(item["status"], 0) + 1

    return {
        "blueprint": BLUEPRINT_ID,
        "target_blueprint_version": target_version,
        "results": results,
        "counts": dict(sorted(counts.items())),
        "complete": fetch_errors == 0,
    }


def render_text(plan: dict) -> str:
    lines = [
        (
            "WordPress plugin fleet plan "
            f"(target blueprint {plan['target_blueprint_version']})"
        )
    ]
    for item in plan["results"]:
        current = item.get("current_blueprint_version") or "-"
        profile = item.get("current_profile") or "-"
        lines.append(
            f"- {item['repository']}: {item['status']} "
            f"(profile {profile} -> {item['desired_profile']}, "
            f"blueprint {current} -> {item['target_blueprint_version']})"
        )
        for issue in item.get("issues", []):
            lines.append(f"  - {issue}")

    if plan["counts"]:
        summary = ", ".join(
            f"{status}={count}"
            for status, count in plan["counts"].items()
        )
        lines.append(f"Summary: {summary}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory",
        type=Path,
        default=(
            Path(__file__).resolve().parent.parent
            / "blueprints"
            / "wordpress-plugin"
            / "inventory.json"
        ),
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--repository",
        action="append",
        default=[],
        help="Limit the plan to an exact owner/name repository; repeatable.",
    )
    parser.add_argument(
        "--api-base",
        default="https://api.github.com",
        help="GitHub API base URL.",
    )
    parser.add_argument(
        "--token-env",
        default="CCF_FLEET_GITHUB_TOKEN",
        help=(
            "Environment variable containing an optional cross-repository "
            "read token. Public repositories need no token."
        ),
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        inventory = load_inventory(args.inventory.resolve())
        token = os.environ.get(args.token_env) or None

        def fetcher(repository: str, branch: str) -> dict | None:
            return fetch_github_manifest(
                repository,
                branch,
                token=token,
                api_base=args.api_base,
                timeout=args.timeout,
            )

        selected = set(args.repository) if args.repository else None
        plan = plan_inventory(inventory, fetcher, selected)
    except FleetError as exc:
        if args.format == "json":
            print(
                json.dumps(
                    {"status": "error", "error": str(exc)},
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(render_text(plan))

    return 0 if plan["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
