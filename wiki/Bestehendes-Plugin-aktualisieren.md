# Bestehendes Plugin aktualisieren

## Zuerst Drift prüfen

Gesamte Flotte:

```bash
python3 scripts/wordpress-plugin-fleet.py
```

Ein Repository:

```bash
python3 scripts/wordpress-plugin-fleet.py \
  --repository cemfirat/wordpress-widget-custom-css-classes
```

## Upgrade-Vorschlag prüfen

```bash
python3 scripts/wordpress-plugin-upgrade-plan.py \
  --repository OWNER/REPO
```

Nur explizit bekannte und getestete Migrationen dürfen als `safe-upgrade` gelten.

## Kontrollierte Propagation

Der Orchestrator arbeitet absichtlich zweistufig.

### 1. Vorschlag nur anzeigen

```bash
python3 scripts/wordpress-plugin-pr-orchestrator.py \
  --repository OWNER/REPO
```

### 2. Branch anlegen und Änderungen schreiben

```bash
python3 scripts/wordpress-plugin-pr-orchestrator.py \
  --repository OWNER/REPO \
  --apply
```

**Das öffnet noch keinen PR.**

Jetzt muss die Branch-CI vollständig grün werden.

### 3. Erst danach PR öffnen

```bash
python3 scripts/wordpress-plugin-pr-orchestrator.py \
  --repository OWNER/REPO \
  --open-pr
```

`--open-pr` verweigert die PR-Erstellung, wenn Checks noch laufen, fehlschlagen oder für den Branch-HEAD gar keine CI-Signale vorhanden sind.

Danach folgt die normale PR-CI und erst dann der Merge.
