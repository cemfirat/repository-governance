#!/usr/bin/env python3
"""Read-only upgrade proposal planner for the Cem Firat WordPress plugin fleet.

The planner turns fleet/version drift into an explicit proposal. It never writes
another repository. Only migrations encoded in this file may be classified as
safe; unknown migrations always require manual review.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FLEET_SCRIPT = SCRIPT_DIR / "wordpress-plugin-fleet.py"

spec = importlib.util.spec_from_file_location(
    "wordpress_plugin_fleet",
    FLEET_SCRIPT,
)
fleet = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(fleet)


def _set_action(path: str, old, new) -> dict:
    return {
        "operation": "set",
        "path": path,
        "from": old,
        "to": new,
    }


def _migration_010_to_020(manifest: dict) -> tuple[list[dict], list[str], bool]:
    """Describe the known 0.1.0 -> 0.2.0 manifest migration."""

    actions = [
        _set_action(
            "blueprint_version",
            manifest.get("blueprint_version"),
            "0.2.0",
        )
    ]
    notes: list[str] = []
    safe = True

    plugin = manifest.get("plugin")
    if not isinstance(plugin, dict):
        return actions, ["plugin manifest section is missing or invalid"], False

    if "root" not in plugin:
        actions.append(_set_action("plugin.root", None, "."))

    if "license_mode" not in plugin:
        if (
            plugin.get("license") == "GPL-2.0-or-later"
            and plugin.get("license_header") == "GPL-2.0-or-later"
        ):
            actions.append(
                _set_action("plugin.license_mode", None, "managed-gpl")
            )
        else:
            safe = False
            notes.append(
                "license_mode cannot be inferred safely from the existing "
                "license fields"
            )

    return actions, notes, safe


MIGRATIONS = {
    ("0.1.0", "0.2.0"): _migration_010_to_020,
}


def propose(entry: dict, manifest: dict | None, target_version: str) -> dict:
    result = {
        "repository": entry["repository"],
        "rollout": entry["rollout"],
        "desired_profile": entry["desired_profile"],
        "target_blueprint_version": target_version,
        "status": "",
        "safe_to_apply": False,
        "actions": [],
        "notes": [],
    }

    if entry["rollout"] == "paused":
        result["status"] = "paused"
        result["notes"].append(
            "rollout is explicitly paused in the fleet inventory"
        )
        return result

    if manifest is None:
        result["status"] = "manual-enrollment"
        result["notes"].append(
            "repository has no .ccf-wordpress-plugin.json manifest"
        )
        return result

    classified = fleet.classify(entry, manifest, target_version)
    status = classified["status"]

    if status == "current":
        result["status"] = "current"
        result["safe_to_apply"] = True
        return result

    if status in ("invalid-manifest", "profile-drift"):
        result["status"] = "manual-review"
        result["notes"].extend(classified.get("issues", []))
        return result

    if status != "version-drift":
        result["status"] = "manual-review"
        result["notes"].extend(classified.get("issues", []))
        return result

    current = manifest.get("blueprint_version")
    migration = MIGRATIONS.get((current, target_version))
    if migration is None:
        result["status"] = "manual-review"
        result["notes"].append(
            f"no reviewed migration exists for {current} -> {target_version}"
        )
        return result

    actions, notes, safe = migration(manifest)
    result["actions"] = actions
    result["notes"].extend(notes)
    result["safe_to_apply"] = safe
    result["status"] = "safe-upgrade" if safe else "manual-review"
    return result


def plan(
    inventory: dict,
    fetcher,
    repository_filter: set[str] | None = None,
) -> dict:
    target = inventory["target_blueprint_version"]
    results: list[dict] = []
    fetch_errors = 0

    if repository_filter:
        known = {item["repository"] for item in inventory["repositories"]}
        unknown = sorted(repository_filter - known)
        if unknown:
            raise fleet.FleetError(
                "Repositories not present in inventory: " + ", ".join(unknown)
            )

    for entry in inventory["repositories"]:
        repository = entry["repository"]
        if repository_filter and repository not in repository_filter:
            continue

        if entry["rollout"] == "paused":
            results.append(propose(entry, None, target))
            continue

        try:
            manifest = fetcher(repository, entry["default_branch"])
            results.append(propose(entry, manifest, target))
        except fleet.FleetError as exc:
            fetch_errors += 1
            results.append(
                {
                    "repository": repository,
                    "rollout": entry["rollout"],
                    "desired_profile": entry["desired_profile"],
                    "target_blueprint_version": target,
                    "status": "fetch-error",
                    "safe_to_apply": False,
                    "actions": [],
                    "notes": [str(exc)],
                }
            )

    counts: dict[str, int] = {}
    for item in results:
        counts[item["status"]] = counts.get(item["status"], 0) + 1

    return {
        "blueprint": fleet.BLUEPRINT_ID,
        "target_blueprint_version": target,
        "mode": "read-only",
        "results": results,
        "counts": dict(sorted(counts.items())),
        "complete": fetch_errors == 0,
    }


def render_text(value: dict) -> str:
    lines = [
        "WordPress plugin blueprint upgrade proposals "
        f"(target {value['target_blueprint_version']}, read-only)"
    ]
    for item in value["results"]:
        lines.append(
            f"- {item['repository']}: {item['status']} "
            f"(safe={str(item['safe_to_apply']).lower()})"
        )
        for action in item["actions"]:
            lines.append(
                f"  - {action['operation']} {action['path']}: "
                f"{action['from']!r} -> {action['to']!r}"
            )
        for note in item["notes"]:
            lines.append(f"  - note: {note}")
    if value["counts"]:
        lines.append(
            "Summary: "
            + ", ".join(
                f"{name}={count}"
                for name, count in value["counts"].items()
            )
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory",
        type=Path,
        default=(
            SCRIPT_DIR.parent
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
        help="Limit proposals to an exact owner/name repository; repeatable.",
    )
    parser.add_argument(
        "--api-base",
        default="https://api.github.com",
        help="GitHub API base URL.",
    )
    parser.add_argument(
        "--token-env",
        default="CCF_FLEET_GITHUB_TOKEN",
        help="Optional environment variable containing a read-only token.",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        inventory = fleet.load_inventory(args.inventory.resolve())
        token = os.environ.get(args.token_env) or None

        def fetcher(repository: str, branch: str):
            return fleet.fetch_github_manifest(
                repository,
                branch,
                token=token,
                api_base=args.api_base,
                timeout=args.timeout,
            )

        selected = set(args.repository) if args.repository else None
        value = plan(inventory, fetcher, selected)
    except fleet.FleetError as exc:
        if args.format == "json":
            print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(value, indent=2, sort_keys=True))
    else:
        print(render_text(value))

    return 0 if value["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
