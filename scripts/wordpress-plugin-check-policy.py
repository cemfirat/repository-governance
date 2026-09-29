#!/usr/bin/env python3
"""Resolve distribution-aware WordPress Plugin Check policy from a blueprint manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EXTERNAL_CATEGORIES = (
    "general",
    "security",
    "performance",
    "accessibility",
)
WORDPRESS_ORG_CATEGORIES = (
    "general",
    "plugin_repo",
    "security",
    "performance",
    "accessibility",
)


class PolicyError(Exception):
    """Invalid plugin-check policy input."""


def read_manifest(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PolicyError(f"Missing blueprint manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PolicyError(f"Invalid blueprint manifest JSON: {exc}") from exc

    if not isinstance(value, dict):
        raise PolicyError("Blueprint manifest must be a JSON object")
    if value.get("blueprint") != "wordpress-plugin":
        raise PolicyError("Manifest is not a wordpress-plugin blueprint manifest")

    plugin = value.get("plugin")
    if not isinstance(plugin, dict):
        raise PolicyError("Manifest plugin section is missing")

    slug = plugin.get("slug")
    if not isinstance(slug, str) or not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*",
        slug,
    ):
        raise PolicyError(f"Invalid plugin.slug: {slug!r}")

    distribution = value.get("distribution")
    if not isinstance(distribution, dict):
        raise PolicyError("Manifest distribution section is missing")

    channel = distribution.get("channel")
    if channel not in ("github-releases", "wordpress.org", "none"):
        raise PolicyError(f"Unsupported distribution channel: {channel!r}")

    return value


def resolve_policy(manifest: dict) -> dict:
    slug = manifest["plugin"]["slug"]
    channel = manifest["distribution"]["channel"]

    if channel == "wordpress.org":
        categories = WORDPRESS_ORG_CATEGORIES
        directory_policy = True
    else:
        categories = EXTERNAL_CATEGORIES
        directory_policy = False

    return {
        "slug": slug,
        "distribution": channel,
        "directory_policy": directory_policy,
        "categories": list(categories),
    }


def write_github_output(path: Path, policy: dict) -> None:
    delimiter = "CCF_PLUGIN_CHECK_CATEGORIES"
    categories = "\n".join(policy["categories"])
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"slug={policy['slug']}\n")
        stream.write(f"distribution={policy['distribution']}\n")
        stream.write(
            "directory_policy="
            + ("true" if policy["directory_policy"] else "false")
            + "\n"
        )
        stream.write(f"categories<<{delimiter}\n")
        stream.write(categories + "\n")
        stream.write(delimiter + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def render_text(policy: dict) -> str:
    return (
        f"{policy['slug']}: distribution={policy['distribution']}; "
        f"directory_policy={str(policy['directory_policy']).lower()}; "
        f"categories={','.join(policy['categories'])}"
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = read_manifest(args.manifest)
        policy = resolve_policy(manifest)
        if args.github_output is not None:
            write_github_output(args.github_output, policy)
    except PolicyError as exc:
        if args.format == "json":
            print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(policy, indent=2, sort_keys=True))
    else:
        print(render_text(policy))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
