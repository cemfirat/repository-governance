#!/usr/bin/env python3
"""Validate the version-controlled GitHub Wiki handbook source."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
REQUIRED = {
    "Home.md",
    "Arbeitsablauf.md",
    "Neues-WordPress-Plugin.md",
    "Bestehendes-Plugin-aktualisieren.md",
    "Plugin-Profile.md",
    "WordPress-Plugin-Check.md",
    "WordPress-Playground.md",
    "Releases-und-Updates.md",
    "Rote-CI-beheben.md",
    "Governance-aendern.md",
    "Entscheidungsgrenzen.md",
    "Technische-Referenz.md",
    "_Sidebar.md",
    "_Footer.md",
}
INVALID_FILENAME = re.compile(r'[\\/:*?"<>|]')


def main() -> int:
    errors: list[str] = []

    if not WIKI.is_dir():
        errors.append("wiki/ directory is missing")
    else:
        present = {p.name for p in WIKI.iterdir() if p.is_file()}
        missing = sorted(REQUIRED - present)
        if missing:
            errors.append("missing required wiki files: " + ", ".join(missing))

        for path in sorted(WIKI.iterdir()):
            if not path.is_file():
                continue
            if INVALID_FILENAME.search(path.name):
                errors.append(f"invalid wiki filename: {path.name}")
            if path.suffix != ".md":
                errors.append(f"wiki source must be Markdown: {path.name}")
            if not path.read_text(encoding="utf-8").strip():
                errors.append(f"empty wiki page: {path.name}")

        sidebar = (WIKI / "_Sidebar.md").read_text(encoding="utf-8")
        for filename in sorted(REQUIRED - {"_Sidebar.md", "_Footer.md"}):
            title = Path(filename).stem.replace("-", " ")
            if f"[[{title}]]" not in sidebar:
                errors.append(f"sidebar does not link to: {title}")

        home = (WIKI / "Home.md").read_text(encoding="utf-8")
        if "Kein Pull Request vor vollständig grüner Branch-CI" not in home:
            errors.append("Home.md is missing the branch-CI-before-PR rule")
        if "technische Quelle der Wahrheit" not in home:
            errors.append("Home.md is missing the source-of-truth boundary")

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"Wiki handbook OK: {len(REQUIRED)} required files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
