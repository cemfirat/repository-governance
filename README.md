<p align="center">
  <img src="assets/brand-banner.webp" alt="Cem Firat creative consultancy artwork" width="900" />
</p>

<h1 align="center">Repository Governance</h1>

<p align="center">
  Reusable GitHub ruleset templates and a small GitHub CLI helper for protecting a repository's <code>main</code> branch.
</p>

The policy is intentionally split into two rulesets:

- **Hard guardrails** protect `main` from deletion and force-pushes with **no bypass actors**.
- **Merge gates** require pull requests, real passing GitHub Actions CI checks, up-to-date branches and resolved discussions. **No administrator bypass** and **0 mandatory reviewers** for the solo-owner/AI-agent workflow.

Public and private repositories use the same technical protection. Explicit profiles prevent accidentally configuring the wrong visibility.

## Einfacher Schnellstart fuer vorhandene Repositories

### Lokaler Speicherort auf meinem Mac

Die bereits vorhandene Arbeitskopie von `repository-governance` liegt auf diesem Mac hier:

`/Users/cemfirat/CCF/Klientel/CCF Development/GitHub/repository-governance`

**Im Finder oeffnen:** `⌘ + ⇧ + G` druecken, den Pfad einfuegen und mit Enter bestaetigen.

**Im Terminal verwenden** (die Anfuehrungszeichen sind wegen des Leerzeichens in `CCF Development` wichtig):

```bash
cd "$HOME/CCF/Klientel/CCF Development/GitHub/repository-governance"
git pull --ff-only
./scripts/setup.sh --all
```

`--all` zeigt nur den Status deiner Repositories und aendert keine Einstellungen. **Nicht erneut klonen**, wenn dieser Ordner bereits existiert. Dieser Pfad ist ein persoenlicher Speicherort; auf einem anderen Mac kann er anders sein.

### Alle sicher korrigierbaren Repositories in einem Durchgang aktualisieren

Nach einer lesenden Pruefung mit `./scripts/setup.sh --all` kannst du **nur die eindeutig als `AENDERN` eingestuften Repositories gesammelt absichern**:

```bash
./scripts/setup.sh --apply-safe-all --dry-run  # Erst alles ansehen, garantiert nur lesend
./scripts/setup.sh --apply-safe-all            # Einmal bestaetigen, dann einzeln verifiziert speichern
```

Der zweite Befehl zeigt zunaechst alle betroffenen Projekte sowie deren konkreten CI-Pflichtchecks und GitHub-Regeln. Danach musst du bewusst **`ALLE N`** eintippen, wobei `N` die aktuell angezeigte Zahl ist (z. B. `ALLE 9`). Ein einfaches `ja` reicht absichtlich nicht. Vor **jedem** Repository wird der vollstaendige Remote-Zustand neu geprueft und jede Aenderung nach dem Speichern verifiziert. Bei Abweichungen oder API-Fehlern **stoppt der gesamte Lauf**; vorher bereits erfolgreich gepruefte Korrekturen bleiben erhalten. Ein erneuter Aufruf ist nach der Fehlerklaerung sicher moeglich.

`PRUEFEN`-Sonderfaelle (fehlende echte PR-CI, Forks, fremde Regeln, Sonderbranch) werden **nie automatisch korrigiert**, ebenso wenig bereits geschuetzte `OK`-Repos. Es gibt **keinen** `--yes`-Modus fuer die Sammelfunktion und in nichtinteraktiven Sitzungen wird nichts geschrieben. `./scripts/setup.sh --all` bleibt dauerhaft **streng nur lesend**. Danach mit `--all` den neuen Stand kontrollieren.


### Gezielte WordPress-Sonderfaelle

Einige WordPress-Repositories brauchen einen bewusst abgestimmten Ansatz statt eines pauschalen CI-Defaults:

- **wordpress-widget-custom-css-classes:** Die vorhandenen neun echten PR-GitHub-Actions-Jobs aus drei Workflows (\`Test\`, \`WordPress plugin blueprint\`, \`WordPress Plugin Check\`) koennen gemeinsam vorgeschrieben werden. Der Setup-Helfer prueft dafuer nur erfolgreiche Jobs vom **selben PR-Commit**, ohne alte Commits oder fremde CI-Apps zu mischen. Im [Sonderfall-Handbuch](wiki/WordPress-Sonderregeln.md) stehen die neun genauen \`--check\`-Namen.
- **wordpress-calendar-booking:** Besitzt bereits ein kombiniertes, speziell benanntes Ruleset mit **elf echten Pflichtchecks**. \`setup.sh\` ueberschreibt solche Sonderregeln **absichtlich nicht**. \`python3 scripts/migrate_calendar_booking.py --dry-run\` prueft eine eng auf dieses Repo begrenzte **In-place-Migration** (ohne duplizierte Rulesets). Nach ausdruecklicher interaktiver Zustimmung koennen damit die persoenliche Bypass-Ausnahme entfernt und verpflichtend geschlossene PR-Diskussionen aktiviert werden, wobei alle elf Checks unveraendert erhalten bleiben.
- **Clickdummy-Projekte:** PR-Workflows muessen einen echten erfolgreichen \`Verify\`-Check liefern, bevor die Regeln gesetzt werden. Bei \`kalkurama-clickdummy\` kann ein Merge wegen \`pages-preview.yml\` ein Pages-Deployment ausloesen; ohne separate Deployment-Freigabe nicht mergen.

**Keine** Sondermigration schreibt ohne interaktive Freigabe oder verändert fremde Repositories. Echte Anwendungstests und Ruleset-Wirksamkeit bleiben danach am konkreten PR zu validieren.

**Kein weiteres Repository notwendig:** Alle Regeln und Werkzeuge bleiben zentral in `repository-governance`. Fuer ein vorhandenes GitHub-Repository:

```bash
# Einmal auf dem Mac:
brew install gh
gh auth login
# Nur falls das Repository noch nicht lokal vorhanden ist:
git clone https://github.com/cemfirat/repository-governance.git
cd repository-governance

# Bei spaeteren Aufrufen zuerst: git pull --ff-only
./scripts/setup.sh cemfirat/mein-projekt
```

Das Werkzeug erkennt die Sichtbarkeit (public/private), bestehende Rulesets und echte bereits erfolgreiche GitHub-Actions-PR-Checks. Es zeigt **vor jeder Aenderung** die konkreten Schritte und fragt erst danach im Terminal nach `ja`. In Skripten ohne Terminal wird nicht automatisch geschrieben. Es aktualisiert auch bereits vorhandene Standard-Rulesets, ohne deren weitere Checks oder strengere Sonderregeln still zu ersetzen.

```bash
./scripts/setup.sh cemfirat/mein-projekt --dry-run   # Nur pruefen
./scripts/setup.sh --all                             # Alle eigenen Repositories NUR LESEN
./scripts/setup.sh cemfirat/mein-projekt --check "Real CI Job"
./scripts/setup.sh cemfirat/mein-projekt --yes       # Bewusst ohne Rueckfrage
```

**Wichtig:** Der Check muss vorher in einem erfolgreichen Pull-Request-Lauf von GitHub Actions tatsaechlich gelaufen sein. Ein neues/leeres Repository ohne echte PR-CI wird **nicht** durch einen fiktiven Pflichtcheck blockiert; erst die passende Projekt-CI einrichten und einen PR testen. Wenn mehrere passende Checks existieren, `--check` verwenden. Bestehende Sonder-Rulesets, Forks, archivierte Repositories, Default-Branches ohne `main` und zuvor eingerichtete menschliche Review-Pflichten werden zur manuellen Pruefung markiert. `--all` ist prinzipiell read-only, auch mit vielen Projekten.

[Ausfuehrliche deutschsprachige Schritt-fuer-Schritt-Anleitung](wiki/Neue-Repositories-absichern.md).

## Repository layout

- `rulesets/main-protection-hard-guardrails.json`  
  Non-bypassable deletion and force-push protection for `main`.

- `rulesets/main-protection-merge-gates-base.json`  
  Secure PR and mandatory GitHub Actions CI rules with no bypass.

- `profiles/public.json` / `profiles/private.json`  
  Public/private visibility profiles; each requires a real CI check (default `test`).

- `scripts/apply-rulesets.sh`  
  Applies and verifies both rulesets on a matching existing repository.

- `scripts/create-protected-repository.sh`  
  One-command creation from a project-specific GitHub template plus automatic protection.

- `.github/workflows/validate.yml`  
  Validates the templates and helper scripts on every branch push and on pull requests. This keeps the repository aligned with the rule that branch CI must be green before a PR is opened.

- `standards/wordpress-plugin.md`  
  Shared presentation, metadata, licensing, packaging, testing and release baseline for public WordPress plugin repositories.

- `blueprints/wordpress-plugin/`  
  Versioned WordPress plugin profiles, manifest schema, research notes and controlled audit/sync methodology.

- `scripts/wordpress-plugin-blueprint.py`  
  Audits enrolled plugin repositories and synchronizes only explicitly exact-managed files.

- `scripts/wordpress-plugin-scaffold.py`  
  Creates a new simple or application WordPress plugin baseline from the same blueprint metadata and validates it before exposing the generated directory.

- `scripts/wordpress-plugin-fleet.py` / `wordpress-plugin-upgrade-plan.py` / `wordpress-plugin-pr-orchestrator.py`  
  Plan and propagate reviewed blueprint upgrades across enrolled plugin repositories without writing directly to protected `main`.

- `blueprints/wordpress-plugin/plugin-check/`  
  Optional distribution-aware wrapper around the official WordPress Plugin Check action. It runs against built/installable plugin contents and derives the appropriate category set from the plugin manifest.

## Handbook / Wiki

A concise operator handbook is version-controlled in [`wiki/`](wiki/). The handbook explains daily workflows; the technical source of truth remains the standards, blueprints, scripts, rulesets and tests in this repository. New users should start with [`wiki/Erste-Schritte.md`](wiki/Erste-Schritte.md).

`.github/workflows/publish-wiki.yml` mirrors that source to the repository's initialized GitHub Wiki. For matching feature-branch pushes, the workflow validates the handbook and performs an authenticated Wiki clone plus `git push --dry-run` so Git access is proven before a pull request is opened. Actual Wiki publication is restricted to `main`; main changes and Wiki `gollum` events keep the published handbook synchronized.

## Requirements

- Bash
- `jq`
- GitHub CLI (`gh`) for live changes
- A GitHub account and repository plan that supports the rules you intend to use
- An existing `main` branch in the target repository

Authenticate the GitHub CLI before making live changes:

```bash
gh auth login
```

If you want to make CI checks required, run CI at least once in the target repository so the check names are known.

## New public or private repository — one command

GitHub *project templates* copy files and workflows, **not repository Settings or Rulesets**. Governance stays the central policy source; your application must come from an actual language/project-specific GitHub template with working CI.

Run one of these commands in the checked-out `repository-governance` folder after `gh auth login`:

```bash
bash scripts/create-protected-repository.sh OWNER/new-public --profile public --template OWNER/my-project-template --check test
bash scripts/create-protected-repository.sh OWNER/new-private --profile private --template OWNER/my-project-template --check test
```

The project template must be marked as a GitHub template, use `main` and contain real Actions workflows with the named test job. Change `--check test` to the real GitHub Actions job/context for your stack. Multiple `--check` arguments are supported. Without an explicit `--check`, `test` is the default. **Never use a dummy green test.**

The creation wrapper calls `gh repo create` and immediately applies both rulesets, without clicking GitHub Settings. A `--dry-run` previews the command and the complete policies offline. If rule creation fails, the new repository is left in place with a prominent warning; it must not be used until protected.

```bash
bash scripts/create-protected-repository.sh OWNER/new-private --profile private --template OWNER/my-project-template --dry-run
```

For an *existing* repository, use:

```bash
bash scripts/apply-rulesets.sh OWNER/existing-public --profile public --check test
bash scripts/apply-rulesets.sh OWNER/existing-private --profile private --check 'unit-tests'
```

`apply-rulesets.sh` checks the repository's real visibility, requires an existing `main`, **refuses to overwrite an existing ruleset**, and verifies the resulting protection. To upgrade a repo that already has older rulesets, adjust those existing rules under Settings → Rules → Rulesets; do not create duplicates.

## Public and private profiles

Both profiles enforce identical security:

- Active hard guardrails on `main`: no deletion or force-push, no bypass.
- Active merge gates: PR required, 0 approvals (no unavailable second human reviewer), resolved discussions and no bypass.
- At least one real passing GitHub Actions required check, bound to the GitHub Actions app (`integration_id: 15368`), with strict up-to-date enforcement.
- The correct CI job depends on the actual application template. Green CI does not replace a Technical Lead review of the final code diff.

The profiles differ only in declared repository visibility. This is deliberate: private source deserves **at least** the same protection as public source. Protecting secrets, release credentials, dependencies and public license/disclosure obligations remain application-specific.

**Automatic for every newly created repository without running a command?** Not from a normal template in a personal `cemfirat/*` account. Use this one-command creation workflow. Alternatively, organization-wide GitHub rulesets can cover newly added repositories automatically when an eligible organization plan and ownership arrangement are chosen.

Official references: [repo templates](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template), [repo rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository), [organization rulesets](https://docs.github.com/en/organizations/managing-organization-settings/creating-rulesets-for-repositories-in-your-organization).

## Safety

The helper performs preflight checks before writing rulesets and attempts to roll back the hard-guardrail ruleset if creation of the merge-gate ruleset fails.

Always review the generated payload with `--dry-run` before applying it to a repository you do not control. The CLI must have repository administration rights; no authentication token is checked into this repository.

Do not store tokens, credentials, private keys, customer data, or internal-only operational details in this repository.

## Contributing

Small, focused pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Licensed under the [MIT License](LICENSE).
