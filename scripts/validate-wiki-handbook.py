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
    "Erste-Schritte.md",
    "Glossar.md",
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
        titles = {
            filename: Path(filename).stem.replace("-", " ")
            for filename in REQUIRED - {"_Sidebar.md", "_Footer.md"}
        }
        titles["Governance-aendern.md"] = "Governance ändern"
        for filename in sorted(titles):
            title = titles[filename]
            if f"[[{title}]]" not in sidebar:
                errors.append(f"sidebar does not link to: {title}")

        home = (WIKI / "Home.md").read_text(encoding="utf-8")
        if "Kein Pull Request vor vollständig grüner Branch-CI" not in home:
            errors.append("Home.md is missing the branch-CI-before-PR rule")
        if "technische Quelle der Wahrheit" not in home:
            errors.append("Home.md is missing the source-of-truth boundary")

        first_steps = (WIKI / "Erste-Schritte.md").read_text(encoding="utf-8")
        if "klonst Du Governance nicht nochmals" not in first_steps:
            errors.append("Erste-Schritte.md must explain that governance is cloned only once")

        new_plugin = (WIKI / "Neues-WordPress-Plugin.md").read_text(encoding="utf-8")
        required_new_plugin_markers = (
            "git clone https://github.com/cemfirat/repository-governance.git",
            "python3 scripts/wordpress-plugin-scaffold.py",
            "git push -u origin main",
            "Ohne Clone und ohne Terminal",
        )
        for marker in required_new_plugin_markers:
            if marker not in new_plugin:
                errors.append(f"Neues-WordPress-Plugin.md is missing: {marker}")

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"Wiki handbook OK: {len(REQUIRED)} required files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
