#!/usr/bin/env python3
"""Safely inspect and reconcile GitHub repository protections for a solo/AI team.

The default is an interactive review, never a blind bulk write. The only
external executable is the authenticated GitHub CLI (`gh`). Python stdlib only.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HARD_NAME = "main protection - hard guardrails"
MERGE_NAME = "main protection - merge gates"
GITHUB_ACTIONS_APP_ID = 15368
REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class SetupError(Exception):
    """An expected safety or API problem, reported without a traceback."""


class GitHub:
    def call(self, arguments: list[str]) -> str:
        try:
            result = subprocess.run(
                ["gh", *arguments], capture_output=True, text=True, check=False,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SetupError(f"GitHub CLI kann nicht ausgefuehrt werden: {exc}") from exc
        if result.returncode != 0:
            # stderr may reveal repository names but no request authentication headers.
            reason = (result.stderr or result.stdout or "Unbekannter Fehler").strip()
            raise SetupError(f"GitHub API Fehler: {reason[:650]}")
        return result.stdout

    def get(self, path: str) -> Any:
        try:
            return json.loads(self.call(["api", path]))
        except ValueError as exc:
            raise SetupError(f"Ungueltige GitHub-Antwort: {path}") from exc

    def put(self, path: str, payload: dict[str, Any]) -> Any:
        return self._write("PUT", path, payload)

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        return self._write("POST", path, payload)

    def _write(self, verb: str, path: str, payload: dict[str, Any]) -> Any:
        # --input avoids shell interpolation of JSON, filenames, credentials.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json") as tmp:
            json.dump(payload, tmp, ensure_ascii=False)
            tmp.flush()
            try:
                return json.loads(self.call(["api", "--method", verb, path, "--input", tmp.name]))
            except ValueError as exc:
                raise SetupError("GitHub hat ungueltige Daten nach dem Speichern geliefert") from exc

    def list_owned_repositories(self, owner: str) -> list[str]:
        try:
            repos = json.loads(self.call([
                "repo", "list", owner, "--limit", "1000", "--json", "nameWithOwner",
            ]))
        except ValueError as exc:
            raise SetupError("GitHub konnte die Repository-Liste nicht lesen") from exc
        names = [r.get("nameWithOwner", "") for r in repos]
        return sorted(x for x in names if REPO_PATTERN.fullmatch(x))


@dataclass
class Action:
    operation: str  # POST or PUT
    name: str
    payload: dict[str, Any]
    ruleset_id: int | None = None
    previous: dict[str, Any] | None = None


@dataclass
class Inspection:
    name: str
    visibility: str = "unbekannt"
    branch: str = "unbekannt"
    branch_sha: str = ""
    actions: list[Action] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    known_rulesets: list[dict[str, Any]] = field(default_factory=list)
    ci_options: list[str] = field(default_factory=list)
    snapshot: str = ""


def read_template(filename: str) -> dict[str, Any]:
    return json.loads((ROOT / "rulesets" / filename).read_text(encoding="utf-8"))


def stable_rule(rule: dict[str, Any]) -> dict[str, Any]:
    """Only the parts of a ruleset whose change is relevant to race prevention."""
    return {key: rule.get(key) for key in (
        "id", "name", "target", "enforcement", "bypass_actors", "conditions", "rules", "updated_at",
    )}


def snapshot(visibility: str, default: str, sha: str, rules: list[dict[str, Any]]) -> str:
    return json.dumps({
        "visibility": visibility, "default": default, "main_head": sha,
        "rulesets": sorted((stable_rule(x) for x in rules), key=lambda x: x["name"]),
    }, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def get_current(client: GitHub, name: str) -> tuple[dict[str, Any], str, list[dict[str, Any]], bool]:
    meta = client.get(f"repos/{name}")
    default = meta.get("default_branch")
    if default != "main":
        return meta, "", [], False
    branch = client.get(f"repos/{name}/branches/main")
    sha = branch.get("commit", {}).get("sha", "")
    if not sha:
        raise SetupError("main hat keinen lesbaren Commit-Stand")
    summary = client.get(f"repos/{name}/rulesets?per_page=100")
    if not isinstance(summary, list) or len(summary) >= 100:
        raise SetupError("Ruleset-Liste kann nicht vollstaendig geprueft werden")
    rules = []
    for item in summary:
        if "id" not in item:
            raise SetupError("Ruleset ohne ID; Abbruch")
        rules.append(client.get(f"repos/{name}/rulesets/{item['id']}"))
    return meta, sha, rules, bool(branch.get("protected", False))


def verify_main_target(rule: dict[str, Any]) -> bool:
    refs = rule.get("conditions", {}).get("ref_name", {})
    return (
        rule.get("target") == "branch"
        and refs.get("include") == ["refs/heads/main"]
        and refs.get("exclude", []) == []
    )


def main_branch_has_pr_workflow(client: GitHub, repo: str, path: str) -> bool:
    """Fail-closed: PR success on an unmerged workflow cannot become mandatory.

    Check the actual YAML file already present on main, not the workflow copied
    into the PR branch. Recognise simple YAML 'on' syntaxes conservatively;
    unusual formats require manual review rather than guessing.
    """
    if not re.fullmatch(r"\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml", path):
        return False
    try:
        file = client.get(f"repos/{repo}/contents/{path}?ref=main")
    except SetupError:
        return False  # Missing on main or not accessible: never invent an eligible check.
    if not isinstance(file, dict) or file.get("encoding") != "base64":
        return False
    try:
        encoded = "".join(file.get("content", "").split())
        yaml = base64.b64decode(encoded, validate=True).decode("utf-8")
    except (ValueError, UnicodeError, binascii.Error, AttributeError):
        return False
    if len(yaml) > 200_000:
        return False
    lines = yaml.splitlines()
    for i, raw in enumerate(lines):
        cleaned = raw.split("#", 1)[0].rstrip()
        m = re.fullmatch(r"""(?:on|'on'|"on")\s*:\s*(.*)""", cleaned)
        if not m:
            continue
        # Top-level inline sequence (e.g. "on: [push, pull_request]").
        if re.search(r"\bpull_request\b", m.group(1)):
            return True
        # Top-level mapping with a 2-space-indented pull_request key.
        if m.group(1).strip():
            return False
        for following in lines[i + 1:]:
            line = following.split("#", 1)[0].rstrip()
            if not line.strip():
                continue
            if line[0] not in (" ", "\t"):
                break
            if re.match(r"""^  (?:pull_request|'pull_request'|"pull_request")\s*:""", line):
                return True
        return False
    return False


def successful_pr_checks(client: GitHub, repo: str) -> list[str]:
    """Prove job names using successful PR workflows on one identical commit SHA.

    Aggregate successful jobs from independent workflows on one PR commit.
    Only a workflow already configured for pull_request on main qualifies;
    check every job against official GitHub Actions check-runs as well.
    """
    runs = client.get(f"repos/{repo}/actions/runs?event=pull_request&per_page=30")
    recent = runs.get("workflow_runs", [])
    if not isinstance(recent, list):
        raise SetupError("Unerwartetes GitHub Actions-Format")

    target_sha: str | None = None
    same_commit_runs: list[dict[str, Any]] = []
    for run in recent:
        if (run.get("event") != "pull_request" or run.get("conclusion") != "success"
                or not run.get("id") or not run.get("head_sha")):
            continue
        if target_sha is None:
            target_sha = run["head_sha"]
        if run["head_sha"] == target_sha:
            same_commit_runs.append(run)

    if target_sha is None:
        return []

    passed_jobs: set[str] = set()
    eligible_workflows: dict[str, bool] = {}
    for run in same_commit_runs:
        path = run.get("path", "")
        if path not in eligible_workflows:
            eligible_workflows[path] = main_branch_has_pr_workflow(client, repo, path)
        if not eligible_workflows[path]:
            continue
        jobs = client.get(f"repos/{repo}/actions/runs/{run['id']}/jobs?per_page=100")
        if jobs.get("total_count", 0) > len(jobs.get("jobs", [])):
            raise SetupError("CI-Jobliste hat mehr als 100 Eintraege; manuell pruefen")
        passed_jobs.update(
            job["name"] for job in jobs.get("jobs", [])
            if job.get("conclusion") == "success" and job.get("name")
        )

    check_runs = client.get(f"repos/{repo}/commits/{target_sha}/check-runs?per_page=100")
    if check_runs.get("total_count", 0) > len(check_runs.get("check_runs", [])):
        raise SetupError("CI-Checkliste hat mehr als 100 Eintraege; manuell pruefen")
    actions_checks = {
        check["name"] for check in check_runs.get("check_runs", [])
        if check.get("conclusion") == "success"
        and check.get("app", {}).get("id") == GITHUB_ACTIONS_APP_ID
    }
    return sorted(passed_jobs & actions_checks)

def required_checks(rule: dict[str, Any]) -> list[dict[str, Any]]:
    matches = [x for x in rule.get("rules", []) if x.get("type") == "required_status_checks"]
    if len(matches) > 1:
        raise SetupError("Mehrere Required-Status-Regeln im selben Ruleset; manuell pruefen")
    return matches[0].get("parameters", {}).get("required_status_checks", []) if matches else []


def safe_payload(rule: dict[str, Any]) -> dict[str, Any]:
    """No server-managed fields such as id, source or timestamps in PUT."""
    return {key: copy.deepcopy(rule[key]) for key in (
        "name", "target", "enforcement", "bypass_actors", "conditions", "rules",
    )}


def inspect(client: GitHub, repo: str, requested_checks: list[str] | None = None) -> Inspection:
    result = Inspection(name=repo)
    if not REPO_PATTERN.fullmatch(repo):
        result.blockers.append("Repository-Name muss OWNER/REPO sein")
        return result
    requested_checks = list(dict.fromkeys(requested_checks or []))
    if any(not check.strip() for check in requested_checks):
        result.blockers.append("Ein erforderlicher CI-Checkname ist leer")
        return result

    meta, head, all_rules, branch_protected = get_current(client, repo)
    result.visibility = meta.get("visibility", "unbekannt")
    result.branch = meta.get("default_branch", "unbekannt")
    result.branch_sha = head
    result.known_rulesets = all_rules
    result.snapshot = snapshot(result.visibility, result.branch, head, all_rules)

    if result.branch != "main":
        result.blockers.append(f"Default-Branch ist {result.branch}, nicht main. Keine automatische Umstellung.")
    if result.visibility not in ("public", "private"):
        result.blockers.append("Unbekannte Sichtbarkeit (public/private nicht erkennbar)")
    if meta.get("archived") or meta.get("disabled"):
        result.blockers.append("Repository ist archiviert oder deaktiviert")
    if meta.get("fork"):
        result.blockers.append("Fork: Upstream-Regeln koennen abweichen; manuell pruefen")
    if not all_rules and branch_protected:
        result.blockers.append("main ist bereits anderweitig geschuetzt (z. B. klassische Branch Protection); manuell pruefen")
    if result.blockers:
        return result

    by_name = {x.get("name"): x for x in all_rules}
    if len(by_name) != len(all_rules):
        result.blockers.append("Doppelte Ruleset-Namen; manuell pruefen")
        return result
    extra = [name for name in by_name if name not in (HARD_NAME, MERGE_NAME)]
    if extra:
        result.blockers.append("Sonder-Rulesets vorhanden: " + ", ".join(str(x) for x in extra))
        return result
    for rule in all_rules:
        if not verify_main_target(rule):
            result.blockers.append(f"Ruleset {rule['name']} hat abweichendes Branch-Ziel")
        if rule.get("source_type") not in (None, "Repository"):
            result.blockers.append(f"Ruleset {rule['name']} hat uebergeordnete Quelle")
    if result.blockers:
        return result

    hard = by_name.get(HARD_NAME)
    if hard:
        types = [x.get("type") for x in hard.get("rules", [])]
        if sorted(types) != ["deletion", "non_fast_forward"]:
            result.blockers.append("Vorhandene Hard-Guardrails haben eine Sonderkonfiguration")
        desired_hard = safe_payload(hard)
        desired_hard["enforcement"] = "active"
        desired_hard["bypass_actors"] = []
    else:
        desired_hard = read_template("main-protection-hard-guardrails.json")

    merge = by_name.get(MERGE_NAME)
    desired_merge = safe_payload(merge) if merge else read_template("main-protection-merge-gates-base.json")
    desired_merge["enforcement"] = "active"
    desired_merge["bypass_actors"] = []

    # Preserve every existing stronger rule; never manufacture an independent approval.
    pr_rules = [x for x in desired_merge["rules"] if x.get("type") == "pull_request"]
    status_rules = [x for x in desired_merge["rules"] if x.get("type") == "required_status_checks"]
    # The template contains an illustrative `test` context. For a *new* repo
    # this MUST NOT be trusted until we observe a real successful PR check.
    if not merge and len(status_rules) == 1:
        status_rules[0]["parameters"]["required_status_checks"] = []
    if len(pr_rules) == 0:
        # Adding a missing mandatory PR gate is safe; existing rules are preserved.
        baseline = read_template("main-protection-merge-gates-base.json")
        desired_merge["rules"].insert(0, next(x for x in baseline["rules"] if x["type"] == "pull_request"))
        pr_rules = [desired_merge["rules"][0]]
    if len(status_rules) == 0:
        baseline = read_template("main-protection-merge-gates-base.json")
        status_rule = next(x for x in baseline["rules"] if x["type"] == "required_status_checks")
        status_rule["parameters"]["required_status_checks"] = []
        desired_merge["rules"].append(status_rule)
        status_rules = [status_rule]
    if len(pr_rules) != 1 or len(status_rules) != 1:
        result.blockers.append("Sonderformat bei PR-/CI-Regeln; bitte manuell pruefen")
    else:
        pr = pr_rules[0].get("parameters", {})
        approvals = pr.get("required_approving_review_count")
        if approvals != 0:
            result.blockers.append(f"Bereits {approvals} verpflichtende Reviews konfiguriert; nicht abschwaechen")
        else:
            pr["required_review_thread_resolution"] = True
            pr["require_extra_approval_for_unattributed_changes"] = False
        st = status_rules[0].get("parameters", {})
        existing_checks = st.get("required_status_checks", [])
        if not isinstance(existing_checks, list):
            result.blockers.append("Bestehende CI-Liste hat ein unerwartetes Format")
        elif existing_checks:
            if requested_checks and set(requested_checks) != {
                x.get("context") for x in existing_checks
            }:
                result.blockers.append("--check wuerde bestehende Pflichtchecks ersetzen; manuell pruefen")
            if any(not x.get("context") for x in existing_checks):
                result.blockers.append("CI-Liste enthaelt einen leeren Check")
            if any(x.get("integration_id") != GITHUB_ACTIONS_APP_ID for x in existing_checks):
                result.blockers.append("Bestehende CI-Checks stammen nicht eindeutig von GitHub Actions; manuell pruefen")
            st["strict_required_status_checks_policy"] = True
            result.notes.append("Bestehende CI-Pflichtchecks werden unveraendert erhalten.")
        else:
            try:
                result.ci_options = successful_pr_checks(client, repo)
            except SetupError as exc:
                result.blockers.append("CI-Erkennung fehlgeschlagen: " + str(exc))
                result.ci_options = []
            checks = requested_checks
            if requested_checks:
                missing = sorted(set(requested_checks) - set(result.ci_options))
                if missing:
                    result.blockers.append("Nicht durch erfolgreiche PR-CI belegte Checks: " + ", ".join(missing))
            elif "test" in result.ci_options:
                checks = ["test"]
            elif len(result.ci_options) == 1:
                checks = list(result.ci_options)
            elif not result.ci_options:
                result.blockers.append("Kein erfolgreicher GitHub-Actions-PR-Test nachweisbar; erst echte CI einrichten und PR testen")
            else:
                result.blockers.append("Mehrere moegliche CI-Checks; passenden mit --check NAME explizit waehlen")
            if checks and not result.blockers:
                st["required_status_checks"] = [
                    {"context": name, "integration_id": GITHUB_ACTIONS_APP_ID}
                    for name in sorted(set(checks))
                ]
                st["strict_required_status_checks_policy"] = True
                result.notes.append("Neue CI-Pflicht basiert auf erfolgreich ausgefuehrten GitHub-Actions-PR-Jobs.")

    if result.blockers:
        return result

    if not hard or safe_payload(hard) != desired_hard:
        result.actions.append(Action("PUT" if hard else "POST", HARD_NAME, desired_hard,
                                     hard.get("id") if hard else None, hard))
    if not merge or safe_payload(merge) != desired_merge:
        result.actions.append(Action("PUT" if merge else "POST", MERGE_NAME, desired_merge,
                                     merge.get("id") if merge else None, merge))
    return result


def print_plan(plan: Inspection, compact: bool = False) -> None:
    if compact:
        status = "PRUEFEN" if plan.blockers else "AENDERN" if plan.actions else "OK"
        message = "; ".join(plan.blockers[:2]) if plan.blockers else ", ".join(a.name for a in plan.actions)
        print(f"{status:8} {plan.name:47} {plan.visibility:7} {plan.branch:9} {message}")
        return
    print(f"\nRepository: {plan.name}")
    print(f"Sichtbarkeit: {plan.visibility} | Hauptbranch: {plan.branch}")
    if plan.branch_sha:
        print(f"Aktueller Stand: {plan.branch_sha[:12]}")
    for warning in plan.notes:
        print(f"  Hinweis: {warning}")
    if plan.ci_options:
        print("  Nachgewiesene PR-CI-Jobs: " + ", ".join(plan.ci_options))
    for reason in plan.blockers:
        print(f"  NICHT AUTOMATISCH AENDERN: {reason}")
    if plan.actions:
        for action in plan.actions:
            operation = "AKTUALISIEREN" if action.operation == "PUT" else "NEU EINRICHTEN"
            print(f"  {operation}: {action.name}")
            if action.name == MERGE_NAME:
                checks = required_checks(action.payload)
                print("     Pflichtchecks: " + ", ".join(x["context"] for x in checks))
                print("     PR-Pflicht, 0 Reviews, Diskussionen aufloesen, kein Bypass, strict CI")
            else:
                print("     Kein Loeschen, kein Force-Push, kein Bypass")
    elif not plan.blockers:
        print("  OK: Die zentralen Schutzregeln erfuellen den Standard; keine Aenderung noetig.")


def verify_action(client: GitHub, repo: str, action: Action, ruleset_id: int) -> None:
    saved = client.get(f"repos/{repo}/rulesets/{ruleset_id}")
    if saved.get("enforcement") != "active" or saved.get("bypass_actors") != []:
        raise SetupError(f"Schutzregel {action.name} konnte nicht korrekt verifiziert werden")
    if not verify_main_target(saved):
        raise SetupError(f"Schutzregel {action.name} hat falsches Branch-Ziel")
    if action.name == HARD_NAME:
        if sorted(x["type"] for x in saved.get("rules", [])) != ["deletion", "non_fast_forward"]:
            raise SetupError("Hard-Guardrails unvollstaendig")
    else:
        prs = [x for x in saved.get("rules", []) if x["type"] == "pull_request"]
        ci = [x for x in saved.get("rules", []) if x["type"] == "required_status_checks"]
        if len(prs) != 1 or len(ci) != 1:
            raise SetupError("PR- oder CI-Pflicht fehlt nach der Einrichtung")
        pr = prs[0]["parameters"]
        params = ci[0]["parameters"]
        if pr.get("required_approving_review_count") != 0 or not pr.get("required_review_thread_resolution"):
            raise SetupError("PR-Review-Einstellungen stimmen nicht")
        if not params.get("strict_required_status_checks_policy"):
            raise SetupError("Die GitHub-CI-Sperre ist nicht strict")
        checks = params.get("required_status_checks", [])
        expected = required_checks(action.payload)
        identity = lambda c: (c.get("context"), c.get("integration_id"))
        if not checks or sorted(map(identity, checks)) != sorted(map(identity, expected)):
            raise SetupError("Erforderliche CI-Checks wurden nicht wie geplant gespeichert")


def apply_plan(client: GitHub, plan: Inspection, selected_checks: list[str] | None) -> None:
    # After the interactive prompt, re-read both branch and rulesets. Any drift aborts.
    current = inspect(client, plan.name, selected_checks)
    if current.blockers or current.snapshot != plan.snapshot or [
        (x.name, x.operation, x.payload) for x in current.actions
    ] != [(x.name, x.operation, x.payload) for x in plan.actions]:
        raise SetupError("Repository hat sich seit der Vorschau geaendert. Bitte setup.sh erneut starten.")
    for action in plan.actions:
        # A different agent may move main after our initial reinspection.
        latest_sha = client.get(f"repos/{plan.name}/branches/main").get("commit", {}).get("sha")
        if latest_sha != plan.branch_sha:
            raise SetupError("main wurde vor dem Schreiben geaendert. Bitte neu pruefen.")
        print(f"Speichere {action.name} ...")
        endpoint = f"repos/{plan.name}/rulesets"
        if action.operation == "PUT":
            # Re-read the exact remote revision immediately before PUT.
            original = client.get(f"{endpoint}/{action.ruleset_id}")
            if stable_rule(original) != stable_rule(action.previous or {}):
                raise SetupError("Ruleset wurde zwischenzeitlich geaendert; Abbruch ohne Ueberschreiben")
            saved = client.put(f"{endpoint}/{action.ruleset_id}", action.payload)
        else:
            # Detect a newly-created ruleset of the same name before POST.
            existing = client.get(f"{endpoint}?per_page=100")
            if any(x.get("name") == action.name for x in existing):
                raise SetupError("Ruleset existiert inzwischen bereits; Abbruch statt Duplikat")
            saved = client.post(endpoint, action.payload)
        saved_id = saved.get("id", action.ruleset_id)
        if not saved_id:
            raise SetupError("GitHub hat keine Ruleset-ID zur Bestaetigung geliefert")
        verify_action(client, plan.name, action, int(saved_id))
    print("OK: GitHub hat alle vorgenommenen Rulesets bestaetigt.")
    print(f"Einstellungen: https://github.com/{plan.name}/settings/rules")


def preview_safe_batch(client: GitHub, owner: str) -> tuple[list[str], list[Inspection]]:
    """Read-only fleet preflight; unrecognised or blocked repos never join the batch."""
    names = client.list_owned_repositories(owner)
    if len(names) != len(set(names)):
        raise SetupError("Repository-Liste enthaelt Duplikate; keine Sammelaenderung")

    plans: list[Inspection] = []
    counts = {"OK": 0, "AENDERN": 0, "PRUEFEN": 0}
    print(f"Sammel-Vorschau: {len(names)} Repositories; noch keine Aenderungen")
    for name in names:
        try:
            plan = inspect(client, name)
        except SetupError as exc:
            counts["PRUEFEN"] += 1
            print(f"PRUEFEN  {name:47} API-Fehler: {exc}")
            continue
        status = "PRUEFEN" if plan.blockers else "AENDERN" if plan.actions else "OK"
        counts[status] += 1
        print_plan(plan, compact=True)
        if status == "AENDERN":
            plans.append(plan)

    print(
        f"Ergebnis: {counts['OK']} OK, {counts['AENDERN']} sichere Kandidaten, "
        f"{counts['PRUEFEN']} ausgeschlossen / einzeln pruefen."
    )
    if plans:
        print("\nDETAILS der vorgesehenen Aenderungen (noch nichts gespeichert):")
        for plan in plans:
            print_plan(plan)
    else:
        print("Keine automatischen Aenderungen notwendig.")
    return names, plans


def apply_safe_batch(client: GitHub, owner: str, dry_run: bool = False) -> int:
    """One deliberate authorisation for the safe subset, never a blind fleet write."""
    names, plans = preview_safe_batch(client, owner)
    if dry_run:
        print("Nur Vorschau: Es wurde nichts veraendert.")
        return 0
    if not plans:
        print("Es wurde nichts veraendert.")
        return 0

    if not sys.stdin.isatty():
        print("Kein interaktives Terminal. Keine Sammelaenderung moeglich.")
        print("Die Sammelfunktion akzeptiert absichtlich kein --yes.")
        return 0

    token = f"ALLE {len(plans)}"
    answer = input(
        f"\nWirklich genau diese {len(plans)} Repositories bearbeiten? "
        f"Zur Bestaetigung exakt '{token}' eingeben: "
    ).strip()
    if answer != token:
        print("Abgebrochen. Kein Repository wurde veraendert.")
        return 0

    # Guard against an owner-fleet change between inventory and approval.
    if client.list_owned_repositories(owner) != names:
        raise SetupError(
            "Die Repository-Liste hat sich seit der Vorschau geaendert. "
            "Noch keine Aenderung; bitte neu starten."
        )

    successful: list[str] = []
    for index, plan in enumerate(plans, 1):
        print(f"\n[{index}/{len(plans)}] {plan.name}")
        try:
            # apply_plan re-reads main, CI evidence and the exact ruleset state;
            # each remote write is also individually verified after GitHub saves it.
            apply_plan(client, plan, [])
        except SetupError as exc:
            print(
                f"\nSTOP bei {plan.name}: {exc}\n"
                f"Vorher erfolgreich: {len(successful)} von {len(plans)}. "
                "Diese zuvor gespeicherten Schutzregeln bleiben bestehen.",
                file=sys.stderr,
            )
            print(
                "Nicht fortfahren; Ursache pruefen und spaeter die "
                "Sammel-Vorschau neu starten.",
                file=sys.stderr,
            )
            return 1
        successful.append(plan.name)

    print(f"\nFERTIG: {len(successful)} Repositories einzeln gespeichert und bei GitHub verifiziert.")
    print("Die in der Vorschau als PRUEFEN markierten Sonderfaelle blieben unberuehrt.")
    print("Zur abschliessenden Bestandsaufnahme: ./scripts/setup.sh --all")
    return 0


def cli(argv: list[str] | None = None, client: GitHub | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="GitHub-Repositories sicher pruefen und nach Bestaetigung schuetzen."
    )
    parser.add_argument("repository", nargs="?", help="OWNER/REPO (z. B. cemfirat/mein-projekt)")
    parser.add_argument("--dry-run", action="store_true", help="Nur lesen, keine Aenderungen")
    parser.add_argument("--yes", action="store_true", help="Nach Vorschau bewusst ohne Rueckfrage ausfuehren")
    parser.add_argument("--check", action="append", default=[], metavar="NAME", help="Echten GitHub-Actions-Job angeben (mehrfach moeglich)")
    parser.add_argument("--all", action="store_true", help="Alle eigenen Repositories nur pruefen (nie aendern)")
    parser.add_argument("--apply-safe-all", action="store_true", help="Sichere Repositories nach einmaliger ausdruecklicher Sammelbestaetigung anpassen")
    parser.add_argument("--owner", help="Bei --all/--apply-safe-all: GitHub-Kontoname")
    args = parser.parse_args(argv)
    gh = client or GitHub()
    try:
        if args.all and args.apply_safe_all:
            raise SetupError("--all bleibt nur lesend; --apply-safe-all separat aufrufen")
        if args.apply_safe_all:
            if args.repository or args.yes or args.check:
                raise SetupError(
                    "--apply-safe-all kann nicht mit Repository, --yes oder --check kombiniert werden"
                )
            owner = args.owner or gh.get("user").get("login", "")
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner):
                raise SetupError("Owner konnte nicht ermittelt werden; --owner USER angeben")
            return apply_safe_batch(gh, owner, args.dry_run)
        if args.all:
            if args.repository or args.yes or args.check:
                raise SetupError("--all ist eine reine Bestandsaufnahme, nicht mit Schreiboptionen kombinierbar")
            owner = args.owner or gh.get("user").get("login", "")
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner):
                raise SetupError("Owner konnte nicht ermittelt werden; --owner USER angeben")
            names = gh.list_owned_repositories(owner)
            print(f"Bestandsaufnahme: {len(names)} Repositories; ausschliesslich lesend")
            counts = {"OK": 0, "AENDERN": 0, "PRUEFEN": 0}
            for name in names:
                try:
                    plan = inspect(gh, name)
                    status = "PRUEFEN" if plan.blockers else "AENDERN" if plan.actions else "OK"
                    counts[status] += 1
                    print_plan(plan, compact=True)
                except SetupError as exc:
                    counts["PRUEFEN"] += 1
                    print(f"PRUEFEN  {name:47} API-Fehler: {exc}")
            print(f"Ergebnis: {counts['OK']} OK, {counts['AENDERN']} moegliche Aenderungen, {counts['PRUEFEN']} manuell pruefen.")
            print("Es wurde nichts veraendert.")
            return 0
        if args.owner or not args.repository:
            parser.error("Bitte OWNER/REPO angeben oder --all verwenden")
        plan = inspect(gh, args.repository, args.check)
        print_plan(plan)
        if plan.blockers:
            print("Keine Aenderungen ausgefuehrt. Bitte zuerst die genannten Punkte klaeren.")
            return 2
        if not plan.actions:
            return 0
        if args.dry_run:
            print("Vorschau: Es wurde nichts veraendert.")
            return 0
        if not args.yes:
            if not sys.stdin.isatty():
                print("Keine interaktive Eingabe: nichts gespeichert. Mit --yes bewusst ausfuehren.")
                return 0
            answer = input("Nur diese aufgelisteten Schutzregeln jetzt aendern? [ja/NEIN] ").strip().lower()
            if answer != "ja":
                print("Abgebrochen, keine Aenderungen.")
                return 0
        apply_plan(gh, plan, args.check)
        return 0
    except SetupError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(cli())
