# Repository Governance

Zentrale Vorlagen und Hilfsmittel fuer die GitHub-Repository-Schutzregeln.

## Struktur

- `rulesets/main-protection-hard-guardrails.json`  
  Nicht umgehbarer Schutz fuer `main`: kein Loeschen, keine Force-Pushes.

- `rulesets/main-protection-merge-gates-base.json`  
  PR-Gate fuer `main` mit `Maintain` und `Repository admin` als `Always allow`-Bypass.  
  Repository-spezifische CI-Checks werden absichtlich nicht fest in der Vorlage gespeichert.

- `scripts/apply-rulesets.sh`  
  Wendet beide Vorlagen ueber die GitHub CLI auf ein neues Repository an.

## Neues Repository absichern

Voraussetzungen:

1. Das neue Repository besitzt bereits einen `main`-Branch.
2. `gh` und `jq` sind installiert.
3. GitHub CLI ist angemeldet: `gh auth login`.
4. Falls CI-Checks verpflichtend werden sollen, CI mindestens einmal ausfuehren, damit die Check-Namen feststehen.

Ohne CI-Checks:

```bash
./scripts/apply-rulesets.sh cemfirat/NEUES-REPO
```

Mit verpflichtenden Checks:

```bash
./scripts/apply-rulesets.sh cemfirat/NEUES-REPO \
  --check "Build, typecheck and test" \
  --check "Smoke test"
```

Wenn vor dem Merge alle PR-Unterhaltungen aufgeloest sein sollen:

```bash
./scripts/apply-rulesets.sh cemfirat/NEUES-REPO \
  --require-conversation-resolution \
  --check "CI"
```

Nur anzeigen, was gesendet wuerde:

```bash
./scripts/apply-rulesets.sh cemfirat/NEUES-REPO --dry-run
```

## Schutzmodell

### main protection - hard guardrails

- nur `main`
- Branch-Loeschung blockiert
- Force-Push blockiert
- keine Bypass-Akteure

### main protection - merge gates

- nur `main`
- Pull Request erforderlich
- `Maintain` -> `Always allow`
- `Repository admin` -> `Always allow`
- keine Loesch-/Force-Push-Regeln in diesem Ruleset
- optionale, repository-spezifische Pflichtchecks

Die Trennung ist absichtlich: Ein Merge-Bypass darf nicht gleichzeitig das Loeschen oder Force-Pushen von `main` erlauben.

## Dieses Repository

Die Dateien werden bei Pull Requests und auf `main` automatisch validiert. Nach Aenderungen an den Vorlagen sollte immer geprueft werden, dass beide Rulesets weiterhin exakt dem oben beschriebenen Modell entsprechen.

## Sichtbarkeit

Die Vorlagen enthalten keine Secrets. Das Repository kann daher technisch oeffentlich sein. Wenn hier spaeter interne Governance-Dokumente, private Organisationsdetails oder weitere betriebliche Informationen abgelegt werden, ist `Private` die sinnvollere Einstellung.
