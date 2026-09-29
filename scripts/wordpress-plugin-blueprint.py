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
LICENSE_MODES = ("managed-gpl", "declared")

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


def manifest_license_mode(manifest: dict) -> str:
    plugin = manifest["plugin"]
    mode = plugin.get("license_mode")

    if mode is None:
        if (
            plugin.get("license") == "GPL-2.0-or-later"
            and plugin.get("license_header") == "GPL-2.0-or-later"
        ):
            return "managed-gpl"
        raise BlueprintError(
            "plugin.license_mode is required when licensing is not the managed GPL baseline"
        )

    if mode not in LICENSE_MODES:
        raise BlueprintError(
            f"plugin.license_mode must be one of {LICENSE_MODES}; got {mode!r}"
        )

    if mode == "managed-gpl":
        if plugin.get("license") != "GPL-2.0-or-later":
            raise BlueprintError(
                "managed-gpl requires plugin.license=GPL-2.0-or-later"
            )
        if plugin.get("license_header") != "GPL-2.0-or-later":
            raise BlueprintError(
                "managed-gpl requires plugin.license_header=GPL-2.0-or-later"
            )
    else:
        license_value = plugin.get("license")
        if not isinstance(license_value, str) or not license_value.strip():
            raise BlueprintError(
                "declared license mode requires a non-empty plugin.license"
            )
        header_value = plugin.get("license_header")
        if header_value is not None and (
            not isinstance(header_value, str) or not header_value.strip()
        ):
            raise BlueprintError(
                "plugin.license_header must be null or a non-empty string"
            )

    return mode


def load_manifest(repository_root: Path) -> dict:
    manifest_path = repository_root / ".ccf-wordpress-plugin.json"
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

    required_string_keys = (
        "slug",
        "name",
        "main_file",
        "version",
        "text_domain",
        "minimum_wordpress",
        "minimum_php",
        "author",
        "license",
    )
    missing = [
        key
        for key in required_string_keys
        if not isinstance(plugin.get(key), str) or not plugin.get(key)
    ]
    if "license_header" not in plugin:
        missing.append("license_header")
    if missing:
        raise BlueprintError(
            "Missing plugin manifest fields: " + ", ".join(sorted(set(missing)))
        )

    header_value = plugin.get("license_header")
    if header_value is not None and (
        not isinstance(header_value, str) or not header_value.strip()
    ):
        raise BlueprintError(
            "plugin.license_header must be null or a non-empty string"
        )

    normalize_relpath(plugin.get("root", "."), "plugin.root")
    normalize_relpath(plugin["main_file"], "plugin.main_file")
    manifest_license_mode(manifest)
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


def package_root_for(repository_root: Path, manifest: dict) -> tuple[Path, Path]:
    root_rel = normalize_relpath(
        manifest["plugin"].get("root", "."),
        "plugin.root",
    )
    return repository_root / root_rel, root_rel


def profile_required_files(
    profile: dict,
    package_root_rel: Path,
) -> list[tuple[Path, str]]:
    """Return repository-relative required paths and their scope labels."""

    repository_files = profile.get("repository_required_files")
    package_files = profile.get("package_required_files")

    # Backward compatibility for pre-0.2 profile documents.
    if repository_files is None and package_files is None:
        legacy = profile.get("required_files", [])
        if not isinstance(legacy, list):
            raise BlueprintError("profile.required_files must be an array")
        return [
            (normalize_relpath(rel, "profile.required_files[]"), "repository")
            for rel in legacy
        ]

    if not isinstance(repository_files, list):
        raise BlueprintError(
            "profile.repository_required_files must be an array"
        )
    if not isinstance(package_files, list):
        raise BlueprintError(
            "profile.package_required_files must be an array"
        )

    result: list[tuple[Path, str]] = []
    for rel in repository_files:
        result.append(
            (
                normalize_relpath(
                    rel,
                    "profile.repository_required_files[]",
                ),
                "repository",
            )
        )
    for rel in package_files:
        package_rel = normalize_relpath(
            rel,
            "profile.package_required_files[]",
        )
        result.append((package_root_rel / package_rel, "package"))
    return result


def exact_managed_entries(
    profile: dict,
    manifest: dict,
    package_root_rel: Path,
) -> list[tuple[Path, Path]]:
    """Return repository-relative target paths and governance-relative sources."""

    exact_files = profile.get("exact_managed_files", {})

    # Backward compatibility for pre-0.2 profile documents.
    if isinstance(exact_files, dict):
        return [
            (
                normalize_relpath(target_rel, "exact managed target"),
                normalize_relpath(source_rel, "exact managed source"),
            )
            for target_rel, source_rel in exact_files.items()
        ]

    if not isinstance(exact_files, list):
        raise BlueprintError(
            "profile.exact_managed_files must be an object or array"
        )

    license_mode = manifest_license_mode(manifest)
    result: list[tuple[Path, Path]] = []

    for index, entry in enumerate(exact_files):
        field = f"profile.exact_managed_files[{index}]"
        if not isinstance(entry, dict):
            raise BlueprintError(f"{field} must be an object")

        target_rel = normalize_relpath(
            entry.get("target"),
            f"{field}.target",
        )
        source_rel = normalize_relpath(
            entry.get("source"),
            f"{field}.source",
        )
        scope = entry.get("scope", "repository")
        if scope not in ("repository", "package"):
            raise BlueprintError(
                f"{field}.scope must be repository or package"
            )

        when_license_mode = entry.get("when_license_mode")
        if when_license_mode is not None:
            if when_license_mode not in LICENSE_MODES:
                raise BlueprintError(
                    f"{field}.when_license_mode is invalid"
                )
            if when_license_mode != license_mode:
                continue

        if scope == "package":
            target_rel = package_root_rel / target_rel

        result.append((target_rel, source_rel))

    return result


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


def license_labels_match(expected: str, actual: str | None) -> bool:
    if actual is None:
        return False
    if expected == "GPL-2.0-or-later":
        normalized = re.sub(r"[^a-z0-9]+", "", actual.lower())
        return normalized in {
            "gplv2orlater",
            "gpl2orlater",
            "gpl20orlater",
        }
    return actual.strip() == expected.strip()


def add_issue(
    issues: list[dict], code: str, message: str, path: str | None = None
) -> None:
    item = {"code": code, "message": message}
    if path:
        item["path"] = path
    issues.append(item)


def audit(repository_root: Path, governance_root: Path) -> dict:
    manifest = load_manifest(repository_root)
    profile = load_profile(governance_root, manifest["profile"])
    plugin = manifest["plugin"]
    package_root, package_root_rel = package_root_for(
        repository_root,
        manifest,
    )
    license_mode = manifest_license_mode(manifest)
    issues: list[dict] = []

    for rel_path, scope in profile_required_files(
        profile,
        package_root_rel,
    ):
        if not (repository_root / rel_path).exists():
            display = rel_path.as_posix()
            add_issue(
                issues,
                "missing_required_file",
                f"Required {scope} file is missing: {display}",
                display,
            )

    for target_rel, source_rel in exact_managed_entries(
        profile,
        manifest,
        package_root_rel,
    ):
        target_path = repository_root / target_rel
        source_path = governance_root / source_rel
        display = target_rel.as_posix()
        if not source_path.is_file():
            raise BlueprintError(
                f"Managed source file does not exist: {source_path}"
            )
        if not target_path.is_file():
            add_issue(
                issues,
                "managed_file_missing",
                f"Managed file is missing: {display}",
                display,
            )
        elif target_path.read_bytes() != source_path.read_bytes():
            add_issue(
                issues,
                "managed_file_drift",
                f"Managed file differs from blueprint: {display}",
                display,
            )

    readme_path = repository_root / "README.md"
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
    main_path = package_root / main_rel
    main_display = (package_root_rel / main_rel).as_posix()
    try:
        header = parse_plugin_header(main_path)
    except BlueprintError as exc:
        add_issue(issues, "main_file", str(exc), main_display)
        header = {}

    for manifest_key, header_key in MANIFEST_TO_HEADER.items():
        expected = plugin.get(manifest_key)
        actual = header.get(header_key)
        if actual != expected:
            add_issue(
                issues,
                "plugin_header_mismatch",
                f"{header_key} is {actual!r}; expected {expected!r}",
                main_display,
            )

    if header.get("Description") and len(header["Description"]) > 140:
        add_issue(
            issues,
            "plugin_description_length",
            f"Plugin Description is {len(header['Description'])} characters; keep it at 140 or fewer",
            main_display,
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
                main_display,
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
        raise BlueprintError(
            f"Unsupported distribution.channel: {channel!r}"
        )

    readme_path = package_root / "readme.txt"
    readme_display = (package_root_rel / "readme.txt").as_posix()
    readme_headers = parse_readme_headers(readme_path)
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
                readme_display,
            )

    if not license_labels_match(
        plugin["license"],
        readme_headers.get("License"),
    ):
        add_issue(
            issues,
            "readme_license_mismatch",
            (
                f"readme.txt License is {readme_headers.get('License')!r}; "
                f"expected {plugin['license']!r}"
            ),
            readme_display,
        )

    license_path = package_root / "LICENSE"
    license_display = (package_root_rel / "LICENSE").as_posix()
    if license_mode == "managed-gpl" and license_path.is_file():
        license_text = license_path.read_text(
            encoding="utf-8",
            errors="replace",
        )
        if (
            "GNU GENERAL PUBLIC LICENSE" not in license_text
            or "Version 2, June 1991" not in license_text
        ):
            add_issue(
                issues,
                "license_content",
                "LICENSE does not contain the complete GNU GPL version 2 text",
                license_display,
            )

    changelog_path = repository_root / "CHANGELOG.md"
    if changelog_path.is_file():
        changelog = changelog_path.read_text(encoding="utf-8")
        version_pattern = (
            rf"(?m)^##\s+{re.escape(plugin['version'])}(?:\s|$)"
        )
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
        "package_root": package_root_rel.as_posix(),
        "license_mode": license_mode,
        "status": "clean" if not issues else "drift",
        "issues": issues,
    }


def sync_exact(
    repository_root: Path,
    governance_root: Path,
    write: bool,
) -> dict:
    manifest = load_manifest(repository_root)
    profile = load_profile(governance_root, manifest["profile"])
    _, package_root_rel = package_root_for(repository_root, manifest)

    changes: list[dict] = []
    for target_rel, source_rel in exact_managed_entries(
        profile,
        manifest,
        package_root_rel,
    ):
        target = repository_root / target_rel
        source = governance_root / source_rel
        if not source.is_file():
            raise BlueprintError(
                f"Managed source file does not exist: {source}"
            )
        if target.is_file() and target.read_bytes() == source.read_bytes():
            continue

        target_display = target_rel.as_posix()
        source_display = source_rel.as_posix()
        changes.append(
            {"path": target_display, "source": source_display}
        )
        if write:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

    return {
        "plugin": manifest["plugin"]["slug"],
        "profile": manifest["profile"],
        "package_root": package_root_rel.as_posix(),
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
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    audit_parser = sub.add_parser(
        "audit",
        help="audit one plugin repository checkout",
    )
    audit_parser.add_argument(
        "--plugin-root",
        type=Path,
        required=True,
        help="repository root containing .ccf-wordpress-plugin.json",
    )

    sync_parser = sub.add_parser(
        "sync-exact",
        help="plan or apply exact managed-file updates",
    )
    sync_parser.add_argument(
        "--plugin-root",
        type=Path,
        required=True,
        help="repository root containing .ccf-wordpress-plugin.json",
    )
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
                f"({result['profile']}, blueprint "
                f"{result.get('blueprint_version')}, "
                f"package root {result.get('package_root')})"
            )
        lines = [
            f"{result['plugin']}: {len(result['issues'])} issue(s)"
        ]
        for issue in result["issues"]:
            location = (
                f" [{issue['path']}]"
                if issue.get("path")
                else ""
            )
            lines.append(
                f"- {issue['code']}{location}: {issue['message']}"
            )
        return "\n".join(lines)

    changes = result.get("changes", [])
    action = "updated" if result.get("write") else "would update"
    if not changes:
        return (
            f"{result['plugin']}: exact managed files already match"
        )
    return "\n".join(
        [
            f"{result['plugin']}: {action} "
            f"{len(changes)} exact managed file(s)"
        ]
        + [
            f"- {item['path']} <- {item['source']}"
            for item in changes
        ]
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    governance_root = args.governance_root.resolve()
    repository_root = args.plugin_root.resolve()

    try:
        if args.command == "audit":
            result = audit(repository_root, governance_root)
            exit_code = 0 if result["status"] == "clean" else 1
        else:
            result = sync_exact(
                repository_root,
                governance_root,
                args.write,
            )
            exit_code = 0
    except BlueprintError as exc:
        result = {"status": "error", "error": str(exc)}
        exit_code = 2

    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        if result.get("status") == "error":
            print(
                f"error: {result['error']}",
                file=sys.stderr,
            )
        else:
            print(render_text(result))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
