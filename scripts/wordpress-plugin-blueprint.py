#!/usr/bin/env python3
"""Audit and synchronize Cem Firat WordPress plugin blueprint metadata.

This tool intentionally distinguishes between:
- exact managed files, which can be synchronized byte-for-byte;
- validated files, which are plugin-specific and are never overwritten here.

It uses only the Python standard library so the baseline check stays portable.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

SCHEMA_VERSION = 1
BLUEPRINT_ID = "wordpress-plugin"
CANONICAL_BANNER = "https://raw.githubusercontent.com/cemfirat/repository-governance/main/assets/brand-banner.webp"

HEADER_FIELDS = (
    "Plugin Name",
    "Plugin URI",
    "Description",
    "Version",
    "Requires at least",
    "Requires PHP",
    "Author",
    "Author URI",
    "License",
    "License URI",
    "Update URI",
    "Text Domain",
)

MANIFEST_TO_HEADER = {
    "name": "Plugin Name",
    "version": "Version",
    "minimum_wordpress": "Requires at least",
    "minimum_php": "Requires PHP",
    "author": "Author",
    "license_header": "License",
    "text_domain": "Text Domain",
}


class BlueprintError(Exception):
    """Configuration or input error."""


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BlueprintError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BlueprintError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise BlueprintError(f"Expected a JSON object in {path}")
    return data


def normalize_relpath(value: str, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise BlueprintError(f"{field} must be a non-empty relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise BlueprintError(f"{field} must stay inside the repository: {value}")
    return path


def load_manifest(plugin_root: Path) -> dict:
    manifest_path = plugin_root / ".ccf-wordpress-plugin.json"
    manifest = read_json(manifest_path)

    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise BlueprintError(
            f"Unsupported schema_version {manifest.get('schema_version')!r}; expected {SCHEMA_VERSION}"
        )
    if manifest.get("blueprint") != BLUEPRINT_ID:
        raise BlueprintError(
            f"Unsupported blueprint {manifest.get('blueprint')!r}; expected {BLUEPRINT_ID!r}"
        )
    profile = manifest.get("profile")
    if not isinstance(profile, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", profile):
        raise BlueprintError("profile must be a lowercase identifier")

    plugin = manifest.get("plugin")
    if not isinstance(plugin, dict):
        raise BlueprintError("plugin must be an object")

    required_plugin_keys = (
        "slug",
        "name",
        "main_file",
        "version",
        "text_domain",
        "minimum_wordpress",
        "minimum_php",
        "author",
        "license",
        "license_header",
    )
    missing = [
        key
        for key in required_plugin_keys
        if not isinstance(plugin.get(key), str) or not plugin.get(key)
    ]
    if missing:
        raise BlueprintError("Missing plugin manifest fields: " + ", ".join(missing))

    normalize_relpath(plugin["main_file"], "plugin.main_file")
    return manifest


def load_profile(governance_root: Path, profile_name: str) -> dict:
    path = (
        governance_root
        / "blueprints"
        / "wordpress-plugin"
        / "profiles"
        / f"{profile_name}.json"
    )
    profile = read_json(path)
    if profile.get("profile") != profile_name:
        raise BlueprintError(f"Profile id mismatch in {path}")
    return profile


def parse_plugin_header(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")[:8192]
    except FileNotFoundError as exc:
        raise BlueprintError(f"Main plugin file does not exist: {path}") from exc

    found: dict[str, str] = {}
    for field in HEADER_FIELDS:
        match = re.search(
            rf"^[ \t/*#@]*{re.escape(field)}:[ \t]*(.+?)[ \t]*\r?$",
            text,
            re.MULTILINE,
        )
        if match:
            found[field] = match.group(1).strip()
    return found


def parse_readme_headers(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}

    result: dict[str, str] = {}
    title = re.search(r"^===\s*(.+?)\s*===\s*$", text, re.MULTILINE)
    if title:
        result["Plugin Name"] = title.group(1).strip()

    for field in (
        "Requires at least",
        "Requires PHP",
        "Stable tag",
        "License",
        "License URI",
    ):
        match = re.search(
            rf"^{re.escape(field)}:\s*(.+?)\s*$",
            text,
            re.MULTILINE | re.IGNORECASE,
        )
        if match:
            result[field] = match.group(1).strip()
    return result


def add_issue(
    issues: list[dict], code: str, message: str, path: str | None = None
) -> None:
    item = {"code": code, "message": message}
    if path:
        item["path"] = path
    issues.append(item)


def audit(plugin_root: Path, governance_root: Path) -> dict:
    manifest = load_manifest(plugin_root)
    profile = load_profile(governance_root, manifest["profile"])
    plugin = manifest["plugin"]
    issues: list[dict] = []

    required_files = profile.get("required_files", [])
    if not isinstance(required_files, list):
        raise BlueprintError("profile.required_files must be an array")
    for rel in required_files:
        rel_path = normalize_relpath(rel, "profile.required_files[]")
        if not (plugin_root / rel_path).exists():
            add_issue(
                issues,
                "missing_required_file",
                f"Required file is missing: {rel}",
                rel,
            )

    exact_files = profile.get("exact_managed_files", {})
    if not isinstance(exact_files, dict):
        raise BlueprintError("profile.exact_managed_files must be an object")
    for target_rel, source_rel in exact_files.items():
        target_path = plugin_root / normalize_relpath(
            target_rel, "exact managed target"
        )
        source_path = governance_root / normalize_relpath(
            source_rel, "exact managed source"
        )
        if not source_path.is_file():
            raise BlueprintError(f"Managed source file does not exist: {source_path}")
        if not target_path.is_file():
            add_issue(
                issues,
                "managed_file_missing",
                f"Managed file is missing: {target_rel}",
                target_rel,
            )
        elif target_path.read_bytes() != source_path.read_bytes():
            add_issue(
                issues,
                "managed_file_drift",
                f"Managed file differs from blueprint: {target_rel}",
                target_rel,
            )

    readme_path = plugin_root / "README.md"
    if readme_path.is_file():
        readme = readme_path.read_text(encoding="utf-8")
        if CANONICAL_BANNER not in readme:
            add_issue(
                issues,
                "readme_banner",
                "README.md does not use the canonical repository banner",
                "README.md",
            )

    main_rel = normalize_relpath(plugin["main_file"], "plugin.main_file")
    main_path = plugin_root / main_rel
    try:
        header = parse_plugin_header(main_path)
    except BlueprintError as exc:
        add_issue(issues, "main_file", str(exc), plugin["main_file"])
        header = {}

    for manifest_key, header_key in MANIFEST_TO_HEADER.items():
        expected = plugin.get(manifest_key)
        actual = header.get(header_key)
        if actual != expected:
            add_issue(
                issues,
                "plugin_header_mismatch",
                f"{header_key} is {actual!r}; expected {expected!r}",
                plugin["main_file"],
            )

    if header.get("Description") and len(header["Description"]) > 140:
        add_issue(
            issues,
            "plugin_description_length",
            f"Plugin Description is {len(header['Description'])} characters; keep it at 140 or fewer",
            plugin["main_file"],
        )

    distribution = manifest.get("distribution", {})
    if not isinstance(distribution, dict):
        raise BlueprintError("distribution must be an object")
    channel = distribution.get("channel", "none")
    updates = distribution.get("updates")
    supported_updates = ("none", "wordpress.org", "github-release-updater")
    if updates not in supported_updates:
        raise BlueprintError(
            f"Unsupported distribution.updates: {updates!r}"
        )

    if channel == "github-releases":
        if updates not in ("none", "github-release-updater"):
            raise BlueprintError(
                "github-releases supports updates=none or github-release-updater"
            )
        expected_uri = distribution.get("update_uri")
        if not isinstance(expected_uri, str) or not expected_uri:
            raise BlueprintError(
                "distribution.update_uri is required for github-releases"
            )
        if header.get("Update URI") != expected_uri:
            add_issue(
                issues,
                "update_uri_mismatch",
                f"Update URI is {header.get('Update URI')!r}; expected {expected_uri!r}",
                plugin["main_file"],
            )
    elif channel == "wordpress.org":
        if updates != "wordpress.org":
            raise BlueprintError(
                "wordpress.org distribution requires updates=wordpress.org"
            )
    elif channel == "none":
        if updates != "none":
            raise BlueprintError(
                "distribution.channel=none requires updates=none"
            )
    else:
        raise BlueprintError(f"Unsupported distribution.channel: {channel!r}")

    readme_headers = parse_readme_headers(plugin_root / "readme.txt")
    expected_readme = {
        "Plugin Name": plugin["name"],
        "Requires at least": plugin["minimum_wordpress"],
        "Requires PHP": plugin["minimum_php"],
        "Stable tag": plugin["version"],
    }
    for key, expected in expected_readme.items():
        actual = readme_headers.get(key)
        if actual != expected:
            add_issue(
                issues,
                "readme_header_mismatch",
                f"readme.txt {key} is {actual!r}; expected {expected!r}",
                "readme.txt",
            )

    license_path = plugin_root / "LICENSE"
    if license_path.is_file() and plugin["license"] == "GPL-2.0-or-later":
        license_text = license_path.read_text(encoding="utf-8", errors="replace")
        if (
            "GNU GENERAL PUBLIC LICENSE" not in license_text
            or "Version 2, June 1991" not in license_text
        ):
            add_issue(
                issues,
                "license_content",
                "LICENSE does not contain the complete GNU GPL version 2 text",
                "LICENSE",
            )

    changelog_path = plugin_root / "CHANGELOG.md"
    if changelog_path.is_file():
        changelog = changelog_path.read_text(encoding="utf-8")
        version_pattern = rf"(?m)^##\s+{re.escape(plugin['version'])}(?:\s|$)"
        if not re.search(version_pattern, changelog):
            add_issue(
                issues,
                "changelog_version",
                f"CHANGELOG.md has no section for version {plugin['version']}",
                "CHANGELOG.md",
            )

    return {
        "blueprint": BLUEPRINT_ID,
        "schema_version": SCHEMA_VERSION,
        "blueprint_version": manifest.get("blueprint_version"),
        "profile": manifest["profile"],
        "plugin": plugin["slug"],
        "status": "clean" if not issues else "drift",
        "issues": issues,
    }


def sync_exact(plugin_root: Path, governance_root: Path, write: bool) -> dict:
    manifest = load_manifest(plugin_root)
    profile = load_profile(governance_root, manifest["profile"])
    exact_files = profile.get("exact_managed_files", {})
    if not isinstance(exact_files, dict):
        raise BlueprintError("profile.exact_managed_files must be an object")

    changes: list[dict] = []
    for target_rel, source_rel in exact_files.items():
        target = plugin_root / normalize_relpath(
            target_rel, "exact managed target"
        )
        source = governance_root / normalize_relpath(
            source_rel, "exact managed source"
        )
        if not source.is_file():
            raise BlueprintError(f"Managed source file does not exist: {source}")
        if target.is_file() and target.read_bytes() == source.read_bytes():
            continue
        changes.append({"path": target_rel, "source": source_rel})
        if write:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

    return {
        "plugin": manifest["plugin"]["slug"],
        "profile": manifest["profile"],
        "write": write,
        "changes": changes,
    }


def default_governance_root() -> Path:
    return Path(__file__).resolve().parent.parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--governance-root",
        type=Path,
        default=default_governance_root(),
        help="repository-governance checkout (default: inferred from script location)",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")

    sub = parser.add_subparsers(dest="command", required=True)

    audit_parser = sub.add_parser("audit", help="audit one plugin checkout")
    audit_parser.add_argument("--plugin-root", type=Path, required=True)

    sync_parser = sub.add_parser(
        "sync-exact",
        help="plan or apply exact managed-file updates",
    )
    sync_parser.add_argument("--plugin-root", type=Path, required=True)
    sync_parser.add_argument(
        "--write",
        action="store_true",
        help="write exact managed files; without this flag only print the plan",
    )
    return parser


def render_text(result: dict) -> str:
    if "issues" in result:
        if not result["issues"]:
            return (
                f"{result['plugin']}: clean "
                f"({result['profile']}, blueprint {result.get('blueprint_version')})"
            )
        lines = [f"{result['plugin']}: {len(result['issues'])} issue(s)"]
        for issue in result["issues"]:
            location = f" [{issue['path']}]" if issue.get("path") else ""
            lines.append(
                f"- {issue['code']}{location}: {issue['message']}"
            )
        return "\n".join(lines)

    changes = result.get("changes", [])
    action = "updated" if result.get("write") else "would update"
    if not changes:
        return f"{result['plugin']}: exact managed files already match"
    return "\n".join(
        [f"{result['plugin']}: {action} {len(changes)} exact managed file(s)"]
        + [
            f"- {item['path']} <- {item['source']}"
            for item in changes
        ]
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    governance_root = args.governance_root.resolve()
    plugin_root = args.plugin_root.resolve()

    try:
        if args.command == "audit":
            result = audit(plugin_root, governance_root)
            exit_code = 0 if result["status"] == "clean" else 1
        else:
            result = sync_exact(plugin_root, governance_root, args.write)
            exit_code = 0
    except BlueprintError as exc:
        result = {"status": "error", "error": str(exc)}
        exit_code = 2

    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        if result.get("status") == "error":
            print(f"error: {result['error']}", file=sys.stderr)
        else:
            print(render_text(result))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
