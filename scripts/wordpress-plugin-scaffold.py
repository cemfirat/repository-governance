#!/usr/bin/env python3
"""Create a deterministic WordPress plugin repository baseline from the shared blueprint."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

CHECKOUT_ACTION_SHA = "11d5960a326750d5838078e36cf38b85af677262"
SUPPORTED_SCAFFOLD_PROFILES = ("simple", "application")


class ScaffoldError(Exception):
    """Invalid scaffold request or generated output."""


def default_governance_root() -> Path:
    return Path(__file__).resolve().parent.parent


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ScaffoldError(f"Missing governance file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ScaffoldError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ScaffoldError(f"Expected a JSON object in {path}")
    return value


def load_blueprint_module(governance_root: Path):
    script_path = governance_root / "scripts" / "wordpress-plugin-blueprint.py"
    spec = importlib.util.spec_from_file_location(
        "ccf_wordpress_plugin_blueprint",
        script_path,
    )
    if spec is None or spec.loader is None:
        raise ScaffoldError(f"Cannot load blueprint module: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def current_blueprint_release(governance_root: Path) -> tuple[str, str]:
    inventory = read_json(
        governance_root
        / "blueprints"
        / "wordpress-plugin"
        / "inventory.json"
    )
    version = inventory.get("target_blueprint_version")
    if not isinstance(version, str) or not version:
        raise ScaffoldError("Fleet inventory has no target blueprint version")

    releases = read_json(
        governance_root
        / "blueprints"
        / "wordpress-plugin"
        / "releases.json"
    )
    release_map = releases.get("releases")
    if not isinstance(release_map, dict):
        raise ScaffoldError("Blueprint release metadata is invalid")

    release = release_map.get(version)
    if not isinstance(release, dict):
        raise ScaffoldError(
            f"Target blueprint version {version} has no reviewed release metadata"
        )

    action_sha = release.get("audit_action_sha")
    if not isinstance(action_sha, str) or not re.fullmatch(
        r"[0-9a-f]{40}",
        action_sha,
    ):
        raise ScaffoldError(
            f"Blueprint release {version} has no immutable audit action SHA"
        )
    return version, action_sha


def validate_repository(repository: str | None) -> str | None:
    if repository is None:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ScaffoldError("repository must use owner/name form")
    return repository


def validate_description(description: str) -> str:
    value = description.strip()
    if not value:
        raise ScaffoldError("description must not be empty")
    if len(value) > 140:
        raise ScaffoldError("description must be 140 characters or fewer")
    return value


def validate_distribution(
    channel: str,
    updates: str,
    repository: str | None,
) -> str | None:
    if channel == "github-releases":
        if repository is None:
            raise ScaffoldError(
                "github-releases distribution requires --repository owner/name"
            )
        if updates != "none":
            raise ScaffoldError(
                "new GitHub release scaffolds must start with updates=none; "
                "the scaffold does not invent an updater implementation"
            )
        return f"https://github.com/{repository}"

    if channel == "wordpress.org":
        if updates != "wordpress.org":
            raise ScaffoldError(
                "wordpress.org distribution requires updates=wordpress.org"
            )
        return None

    if channel == "none":
        if updates != "none":
            raise ScaffoldError("distribution=none requires updates=none")
        return None

    raise ScaffoldError(f"Unsupported distribution channel: {channel}")


def ensure_destination_available(destination: Path) -> None:
    if destination.exists():
        if not destination.is_dir():
            raise ScaffoldError(
                f"Destination exists and is not a directory: {destination}"
            )
        if any(destination.iterdir()):
            raise ScaffoldError(
                f"Destination is not empty; refusing to overwrite: {destination}"
            )


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def render_plugin_header(
    *,
    name: str,
    repository: str | None,
    description: str,
    version: str,
    minimum_wordpress: str,
    minimum_php: str,
    author: str,
    author_uri: str,
    license_header: str | None,
    license_uri: str | None,
    update_uri: str | None,
    text_domain: str,
) -> str:
    lines = [
        "<?php",
        "/**",
        f" * Plugin Name: {name}",
    ]
    if repository:
        lines.append(f" * Plugin URI: https://github.com/{repository}")
    lines.extend(
        [
            f" * Description: {description}",
            f" * Version: {version}",
            f" * Requires at least: {minimum_wordpress}",
            f" * Requires PHP: {minimum_php}",
            f" * Author: {author}",
        ]
    )
    if author_uri:
        lines.append(f" * Author URI: {author_uri}")
    if license_header is not None:
        lines.append(f" * License: {license_header}")
    if license_uri:
        lines.append(f" * License URI: {license_uri}")
    if update_uri:
        lines.append(f" * Update URI: {update_uri}")
    lines.extend(
        [
            f" * Text Domain: {text_domain}",
            " */",
            "",
            "if ( ! defined( 'ABSPATH' ) ) {",
            "	exit;",
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def render_readme(
    *,
    name: str,
    description: str,
    author: str,
    license_value: str,
    minimum_wordpress: str,
    minimum_php: str,
    version: str,
    profile: str,
) -> str:
    return f"""<p align="center">
  <img src="https://raw.githubusercontent.com/cemfirat/repository-governance/main/assets/brand-banner.webp" alt="Cem Firat creative consultancy artwork" width="900" />
</p>

# {name}

{description}

**Author:** {author}  
**License:** {license_value}  
**Requirements:** WordPress {minimum_wordpress}+ and PHP {minimum_php}+.

> **Status:** Initial scaffold {version}. Document only behavior that is implemented and verified before release.

## Development

This repository uses the shared Cem Firat WordPress plugin blueprint with the `{profile}` profile.

The generated PHP entry point is intentionally minimal. Add only the architecture required by the plugin itself; the blueprint does not force framework-style folders or classes.

## License

{license_value}.
"""


def render_wordpress_readme(
    *,
    name: str,
    description: str,
    minimum_wordpress: str,
    minimum_php: str,
    version: str,
    license_label: str,
    license_uri: str | None,
) -> str:
    lines = [
        f"=== {name} ===",
        "Contributors: cemfirat",
        f"Requires at least: {minimum_wordpress}",
        f"Requires PHP: {minimum_php}",
        f"Stable tag: {version}",
        f"License: {license_label}",
    ]
    if license_uri:
        lines.append(f"License URI: {license_uri}")
    lines.extend(
        [
            "",
            description,
            "",
            "== Description ==",
            "",
            description,
            "",
            "== Changelog ==",
            "",
            f"= {version} =",
            "* Initial blueprint scaffold.",
            "",
        ]
    )
    return "\n".join(lines)


def render_workflow(action_sha: str) -> str:
    return f"""name: WordPress plugin blueprint

on:
  pull_request:
  push:
    branches:
      - main

permissions:
  contents: read

jobs:
  blueprint:
    name: WordPress plugin blueprint
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      - name: Check out plugin
        uses: actions/checkout@{CHECKOUT_ACTION_SHA} # v4
        with:
          persist-credentials: false

      - name: Audit plugin against pinned blueprint
        uses: cemfirat/repository-governance/blueprints/wordpress-plugin@{action_sha}
        with:
          plugin-root: .
"""


def scaffold_plugin(
    *,
    governance_root: Path,
    destination: Path,
    profile: str,
    slug: str,
    name: str,
    description: str,
    version: str,
    minimum_wordpress: str,
    minimum_php: str,
    author: str,
    author_uri: str,
    package_root: str,
    license_mode: str,
    license_value: str | None,
    license_header: str | None,
    license_uri: str | None,
    distribution: str,
    updates: str,
    repository: str | None,
    text_domain: str | None = None,
    main_file: str | None = None,
    playground_preview: bool = False,
) -> dict:
    governance_root = governance_root.resolve()
    destination = destination.resolve()

    if profile == "block":
        raise ScaffoldError(
            "block profile scaffolding is intentionally delegated to the official "
            "@wordpress/create-block toolchain; create the block plugin first, then "
            "enroll it in this blueprint"
        )
    if profile not in SUPPORTED_SCAFFOLD_PROFILES:
        raise ScaffoldError(
            f"profile must be one of {SUPPORTED_SCAFFOLD_PROFILES} or block"
        )

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ScaffoldError(
            "slug must contain lowercase letters, numbers and single hyphens only"
        )
    text_domain = text_domain or slug
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", text_domain):
        raise ScaffoldError("text domain must be a lowercase WordPress slug")

    description = validate_description(description)
    repository = validate_repository(repository)

    blueprint = load_blueprint_module(governance_root)
    blueprint.load_profile(governance_root, profile)
    package_root_rel = blueprint.normalize_relpath(
        package_root,
        "plugin.root",
    )
    main_file = main_file or f"{slug}.php"
    main_file_rel = blueprint.normalize_relpath(
        main_file,
        "plugin.main_file",
    )
    if main_file_rel.suffix.lower() != ".php":
        raise ScaffoldError("main plugin file must end in .php")

    if license_mode == "managed-gpl":
        if license_value not in (None, "GPL-2.0-or-later"):
            raise ScaffoldError(
                "managed-gpl fixes the license to GPL-2.0-or-later"
            )
        if license_header not in (None, "GPL-2.0-or-later"):
            raise ScaffoldError(
                "managed-gpl fixes the plugin header license to GPL-2.0-or-later"
            )
        license_value = "GPL-2.0-or-later"
        license_header = "GPL-2.0-or-later"
        license_uri = (
            license_uri
            or "https://www.gnu.org/licenses/gpl-2.0.html"
        )
        readme_license = "GPLv2 or later"
    elif license_mode == "declared":
        if not isinstance(license_value, str) or not license_value.strip():
            raise ScaffoldError(
                "declared license mode requires an explicit --license value"
            )
        license_value = license_value.strip()
        if license_header is not None and not license_header.strip():
            raise ScaffoldError(
                "declared --license-header must be non-empty when supplied"
            )
        readme_license = license_value
    else:
        raise ScaffoldError(
            "license mode must be managed-gpl or declared"
        )

    update_uri = validate_distribution(
        distribution,
        updates,
        repository,
    )
    blueprint_version, action_sha = current_blueprint_release(
        governance_root
    )

    manifest = {
        "$schema": (
            "https://raw.githubusercontent.com/cemfirat/"
            "repository-governance/main/blueprints/wordpress-plugin/"
            "manifest.schema.json"
        ),
        "schema_version": 1,
        "blueprint": "wordpress-plugin",
        "blueprint_version": blueprint_version,
        "profile": profile,
        "plugin": {
            "root": package_root_rel.as_posix(),
            "slug": slug,
            "name": name,
            "main_file": main_file_rel.as_posix(),
            "version": version,
            "text_domain": text_domain,
            "minimum_wordpress": minimum_wordpress,
            "minimum_php": minimum_php,
            "author": author,
            "license_mode": license_mode,
            "license": license_value,
            "license_header": license_header,
        },
        "distribution": {
            "channel": distribution,
            "updates": updates,
        },
        "features": {
            "block_plugin": False,
            "playground_preview": bool(playground_preview),
        },
    }
    if update_uri:
        manifest["distribution"]["update_uri"] = update_uri

    ensure_destination_available(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.scaffold-",
            dir=str(destination.parent),
        )
    )

    try:
        package_dir = temp_root / package_root_rel
        package_dir.mkdir(parents=True, exist_ok=True)

        write_text(
            temp_root / ".ccf-wordpress-plugin.json",
            json.dumps(manifest, indent=2) + "\n",
        )
        write_text(
            temp_root / ".gitignore",
            "/dist/\n.DS_Store\n",
        )
        write_text(
            temp_root / "README.md",
            render_readme(
                name=name,
                description=description,
                author=author,
                license_value=license_value,
                minimum_wordpress=minimum_wordpress,
                minimum_php=minimum_php,
                version=version,
                profile=profile,
            ),
        )
        write_text(
            temp_root / "CHANGELOG.md",
            (
                "# Changelog\n\n"
                f"## {version} - Unreleased\n\n"
                "- Initial repository scaffold.\n"
            ),
        )
        write_text(
            package_dir / main_file_rel,
            render_plugin_header(
                name=name,
                repository=repository,
                description=description,
                version=version,
                minimum_wordpress=minimum_wordpress,
                minimum_php=minimum_php,
                author=author,
                author_uri=author_uri,
                license_header=license_header,
                license_uri=license_uri,
                update_uri=update_uri,
                text_domain=text_domain,
            ),
        )
        write_text(
            package_dir / "readme.txt",
            render_wordpress_readme(
                name=name,
                description=description,
                minimum_wordpress=minimum_wordpress,
                minimum_php=minimum_php,
                version=version,
                license_label=readme_license,
                license_uri=license_uri,
            ),
        )

        logo_source = governance_root / "assets" / "logo.svg"
        if not logo_source.is_file():
            raise ScaffoldError(
                f"Missing managed repository logo: {logo_source}"
            )
        (temp_root / "assets").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            logo_source,
            temp_root / "assets" / "logo.svg",
        )

        if license_mode == "managed-gpl":
            license_source = (
                governance_root
                / "blueprints"
                / "wordpress-plugin"
                / "managed"
                / "gpl-2.0.txt"
            )
            if not license_source.is_file():
                raise ScaffoldError(
                    f"Missing managed GPL license: {license_source}"
                )
            shutil.copyfile(
                license_source,
                package_dir / "LICENSE",
            )

        write_text(
            temp_root / ".github" / "workflows" / "blueprint.yml",
            render_workflow(action_sha),
        )

        audit_result = blueprint.audit(temp_root, governance_root)
        if audit_result.get("status") != "clean":
            raise ScaffoldError(
                "generated scaffold failed blueprint audit: "
                + json.dumps(audit_result.get("issues", []), sort_keys=True)
            )

        if destination.exists():
            destination.rmdir()
        os.replace(temp_root, destination)
        temp_root = None

        return {
            "destination": str(destination),
            "profile": profile,
            "plugin": slug,
            "blueprint_version": blueprint_version,
            "audit_action_sha": action_sha,
            "package_root": package_root_rel.as_posix(),
            "license_mode": license_mode,
            "distribution": distribution,
            "updates": updates,
            "audit": audit_result,
        }
    finally:
        if temp_root is not None and temp_root.exists():
            shutil.rmtree(temp_root, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--governance-root",
        type=Path,
        default=default_governance_root(),
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument(
        "--profile",
        choices=("simple", "application", "block"),
        required=True,
    )
    parser.add_argument("--slug", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--minimum-wordpress", default="6.5")
    parser.add_argument("--minimum-php", default="8.0")
    parser.add_argument("--author", default="Cem Firat")
    parser.add_argument("--author-uri", default="https://cemfirat.com/")
    parser.add_argument("--package-root", default=".")
    parser.add_argument(
        "--license-mode",
        choices=("managed-gpl", "declared"),
        required=True,
    )
    parser.add_argument("--license")
    parser.add_argument("--license-header")
    parser.add_argument("--license-uri")
    parser.add_argument(
        "--distribution",
        choices=("github-releases", "wordpress.org", "none"),
        required=True,
    )
    parser.add_argument(
        "--updates",
        choices=("none", "wordpress.org", "github-release-updater"),
        required=True,
    )
    parser.add_argument("--repository")
    parser.add_argument("--text-domain")
    parser.add_argument("--main-file")
    parser.add_argument(
        "--playground-preview",
        action="store_true",
    )
    return parser


def render_text(result: dict) -> str:
    return (
        f"{result['plugin']}: scaffolded {result['profile']} plugin at "
        f"{result['destination']} (blueprint {result['blueprint_version']}, "
        f"audit clean)"
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = scaffold_plugin(
            governance_root=args.governance_root,
            destination=args.destination,
            profile=args.profile,
            slug=args.slug,
            name=args.name,
            description=args.description,
            version=args.version,
            minimum_wordpress=args.minimum_wordpress,
            minimum_php=args.minimum_php,
            author=args.author,
            author_uri=args.author_uri,
            package_root=args.package_root,
            license_mode=args.license_mode,
            license_value=args.license,
            license_header=args.license_header,
            license_uri=args.license_uri,
            distribution=args.distribution,
            updates=args.updates,
            repository=args.repository,
            text_domain=args.text_domain,
            main_file=args.main_file,
            playground_preview=args.playground_preview,
        )
    except (ScaffoldError, Exception) as exc:
        if isinstance(exc, ScaffoldError):
            message = str(exc)
        else:
            message = str(exc)
        if args.format == "json":
            print(json.dumps({"status": "error", "error": message}, indent=2))
        else:
            print(f"error: {message}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(render_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
