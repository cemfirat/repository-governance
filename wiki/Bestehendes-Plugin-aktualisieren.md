# Bestehendes Plugin aktualisieren

Hier muss zuerst unterschieden werden, **was** Du aktualisieren möchtest.

## Fall A: Du entwickelst eine normale Plugin-Funktion

Dann arbeitest Du direkt im Plugin-Repository. `repository-governance` wird dafür nicht kopiert und normalerweise auch nicht geändert.

Beispiel:

```bash
cd ~/Developer/wordpress-mein-plugin
git switch main
git pull --ff-only
git switch -c feat/neue-funktion
```

Danach gilt [[Arbeitsablauf]]: ändern → commit → push → Branch-CI grün → PR → PR-CI grün → Merge.

## Fall B: Der zentrale Blueprint wurde verbessert

Dann soll geprüft werden, ob das bestehende Plugin vom neuen Blueprint abweicht.

Diese Arbeit wird aus der lokalen `repository-governance`-Arbeitskopie ausgeführt.

### 1. Governance aktualisieren

```bash
cd ~/Developer/repository-governance
git switch main
git pull --ff-only
```

### 2. Flotte oder einzelnes Repository prüfen

Gesamte Flotte:

```bash
python3 scripts/wordpress-plugin-fleet.py
```

Nur ein Plugin:

```bash
python3 scripts/wordpress-plugin-fleet.py \
  --repository cemfirat/wordpress-widget-custom-css-classes
```

Das ist zunächst nur eine Prüfung. Es wird noch nichts geändert.

### 3. Upgrade-Vorschlag ansehen

```bash
python3 scripts/wordpress-plugin-upgrade-plan.py \
  --repository OWNER/REPO
```

Nur bekannte, getestete Migrationen dürfen als `safe-upgrade` behandelt werden.

### 4. Upgrade-Branch anlegen

```bash
python3 scripts/wordpress-plugin-pr-orchestrator.py \
  --repository OWNER/REPO \
  --apply
```

`--apply` erstellt bzw. befüllt den Upgrade-Branch. **Es öffnet noch keinen PR.**

### 5. Branch-CI abwarten

Die Branch-CI des Ziel-Plugins muss vollständig grün sein.

### 6. Erst dann PR öffnen

```bash
python3 scripts/wordpress-plugin-pr-orchestrator.py \
  --repository OWNER/REPO \
  --open-pr
```

Der Orchestrator verweigert die PR-Erstellung, wenn der Branch keine CI-Signale hat, Checks noch laufen oder nicht grün sind.

Danach folgt wieder PR-CI → Merge → `main` prüfen.

## Wichtig

Ein Blueprint-Upgrade soll gemeinsame Governance-Dateien aktualisieren, nicht ungefragt Plugin-Funktionscode überschreiben. Produktcode bleibt Eigentum des jeweiligen Plugin-Repositories.
