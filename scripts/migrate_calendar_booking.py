#!/usr/bin/env python3
"""Fail-closed one-time in-place migration for the legacy Calendar Booking ruleset.

This script never creates a second ruleset and never rewrites CI check names.
Run interactively on the owner's Mac after reviewing the dry-run. It is not
part of the fleet auto-updater: the existing ruleset has a bespoke layout.
"""

from __future__ import annotations

import argparse
import copy
import sys
from dataclasses import dataclass
from typing import Any

from repository_setup import GitHub, SetupError, safe_payload, stable_rule, verify_main_target

REPO = "cemfirat/wordpress-calendar-booking"
RULESET_ID = 23837020
RULESET_NAME = "main protection"
APP_ID = 15368
EXPECTED_CHECKS = frozenset({
    "PHP 8.0 syntax",
    "PHP 8.1 syntax",
    "PHP 8.2 syntax",
    "PHP 8.3 syntax",
    "PHP 8.4 syntax",
    "PHP 8.5 syntax",
    "WordPress 6.5 / PHP 8.0",
    "WordPress latest / PHP 8.3",
    "Build release ZIP",
    "Fresh install release ZIP",
    "Imported 1.x migration",
})
EXPECTED_BYPASS = {
    "actor_id": 5923877, "actor_type": "User", "bypass_mode": "always",
}
EXPECTED_TYPES = ["deletion", "non_fast_forward", "pull_request", "required_status_checks"]


@dataclass
class CalendarPlan:
    head_sha: str
    before: dict[str, Any]
    after: dict[str, Any]
    checks: tuple[str, ...]


def migrate_plan(client: GitHub) -> CalendarPlan:
    """Read and validate every relevant assumption, without any write."""
    meta = client.get(f"repos/{REPO}")
    if (
        meta.get("visibility") != "public" or meta.get("default_branch") != "main"
        or meta.get("archived") or meta.get("disabled") or meta.get("fork")
    ):
        raise SetupError("Repository-Metadaten weichen ab: nur aktives public/main ohne Fork")

    branch = client.get(f"repos/{REPO}/branches/main")
    head = branch.get("commit", {}).get("sha", "")
    if not head:
        raise SetupError("Kein lesbarer main-Commit; nichts speichern")

    summary = client.get(f"repos/{REPO}/rulesets?per_page=100")
    if not isinstance(summary, list) or len(summary) != 1:
        raise SetupError("Die Ruleset-Liste wurde veraendert; Migration anhalten")
    if summary[0].get("id") != RULESET_ID or summary[0].get("name") != RULESET_NAME:
        raise SetupError("Das erwartete historische Ruleset wurde nicht gefunden")

    rule = client.get(f"repos/{REPO}/rulesets/{RULESET_ID}")
    if (rule.get("id") != RULESET_ID or rule.get("name") != RULESET_NAME
            or rule.get("enforcement") != "active" or not verify_main_target(rule)
            or rule.get("source_type") not in (None, "Repository")):
        raise SetupError("Unerwartetes Ruleset: nicht automatisch aendern")

    kinds = sorted(x.get("type") for x in rule.get("rules", []))
    if kinds != EXPECTED_TYPES:
        raise SetupError("Unbekannte oder fehlende Einzelregeln; nicht automatisch aendern")
    old_bypass = rule.get("bypass_actors", [])
    if old_bypass not in ([], [EXPECTED_BYPASS]):
        raise SetupError("Unbekannte Bypass-Ausnahmen; zuerst manuell pruefen")

    pr = next(x["parameters"] for x in rule["rules"] if x["type"] == "pull_request")
    if (pr.get("required_approving_review_count") != 0
            or pr.get("require_code_owner_review") is not False
            or pr.get("require_last_push_approval") is not False
            or pr.get("required_reviewers", []) != []):
        raise SetupError("Bestehende Review-Vorgaben haben ein Sonderformat")

    status = next(x["parameters"] for x in rule["rules"] if x["type"] == "required_status_checks")
    actual = status.get("required_status_checks")
    if (
        not status.get("strict_required_status_checks_policy")
        or not isinstance(actual, list)
        or len(actual) != len(EXPECTED_CHECKS)
        or {x.get("context") for x in actual} != EXPECTED_CHECKS
        or any(x.get("integration_id") != APP_ID for x in actual)
    ):
        raise SetupError("Die elf vorhandenen CI-Pflichtchecks weichen ab; nicht ueberschreiben")

    after = safe_payload(rule)
    after["bypass_actors"] = []
    after_pr = next(x["parameters"] for x in after["rules"] if x["type"] == "pull_request")
    after_pr["required_review_thread_resolution"] = True
    return CalendarPlan(head, copy.deepcopy(rule), after, tuple(x["context"] for x in actual))


def save_calendar_plan(client: GitHub, approved: CalendarPlan) -> bool:
    """Recheck the exact remote revision; PUT once; verify preserved checks."""
    current = migrate_plan(client)
    if (
        current.head_sha != approved.head_sha
        or stable_rule(current.before) != stable_rule(approved.before)
        or current.after != approved.after
    ):
        raise SetupError("Repository/Ruleset seit der Vorschau veraendert; nichts gespeichert")

    if safe_payload(current.before) == approved.after:
        return False

    print("Aktualisiere NUR das vorhandene Ruleset main protection ...")
    client.put(f"repos/{REPO}/rulesets/{RULESET_ID}", approved.after)
    saved = client.get(f"repos/{REPO}/rulesets/{RULESET_ID}")

    if (
        saved.get("id") != RULESET_ID
        or saved.get("enforcement") != "active"
        or saved.get("bypass_actors") != []
        or not verify_main_target(saved)
        or safe_payload(saved) != approved.after
    ):
        raise SetupError("GitHub hat die geplanten Regeln nicht exakt bestaetigt")
    print("OK: Bestehendes Ruleset aktualisiert, alle elf CI-Checks erhalten.")
    return True


def cli(argv: list[str] | None = None, client: GitHub | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Nur cemfirat/wordpress-calendar-booking: historisches Ruleset sicher haerten."
    )
    parser.add_argument("--dry-run", action="store_true", help="Nur lesen, niemals speichern")
    args = parser.parse_args(argv)
    gh = client or GitHub()
    try:
        plan = migrate_plan(gh)
        print(f"Repository: {REPO} | Branch: main | Stand: {plan.head_sha[:12]}")
        print("Vorhandene GitHub-Actions-Pflichtchecks (unveraendert):")
        for check in plan.checks:
            print(f"  - {check}")
        if safe_payload(plan.before) == plan.after:
            print("OK: Kein Handlungsbedarf; Ruleset entspricht bereits dem Ziel.")
            return 0
        print("\nGeplant (nur bestehendes Ruleset #23837020):")
        print("  - persoenliche Administrator-Bypass-Ausnahme entfernen")
        print("  - Abschluss aller PR-Diskussionen verpflichtend machen")
        print("  - Hard Guards, PR-/CI-Pflicht und alle elf Checks unveraendert erhalten")
        if args.dry_run:
            print("Nur Vorschau: Es wurde nichts veraendert.")
            return 0
        if not sys.stdin.isatty():
            print("Nichtinteraktives Terminal: keine Aenderung. Bitte manuell bestaetigen.")
            return 0
        if input("Zum Aktualisieren exakt 'KALENDER' eingeben: ").strip() != "KALENDER":
            print("Abgebrochen. Es wurde nichts veraendert.")
            return 0
        save_calendar_plan(gh, plan)
        print(f"Einstellungen: https://github.com/{REPO}/settings/rules")
        return 0
    except SetupError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(cli())
