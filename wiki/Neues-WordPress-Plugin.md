# Neues WordPress Plugin

Diese Anleitung führt ein vollständiges Beispiel von null bis zum ersten GitHub-Repository durch.

Wenn Begriffe wie `Repository`, `Branch`, `CI` oder `Slug` unbekannt sind, zuerst [[Glossar]] lesen.

## Wichtig: Was Du nicht tun sollst

**Nicht** `repository-governance` klonen, den Ordner umbenennen und Dateien löschen.

Governance ist die Fabrik. Das Plugin ist ein neues Produkt, das von dieser Fabrik erzeugt wird.

## Schritt 1: Entscheide die Grunddaten

Für ein normales kleines Plugin brauchst Du vorerst:

- **Name:** lesbarer Name, z. B. `Mein Plugin`
- **Slug:** technische Kennung, nur Kleinbuchstaben/Zahlen/Bindestriche, z. B. `wordpress-mein-plugin`
- **Profil:** meistens `simple`; größere Integrationen verwenden `application`
- **Lizenz:** für ein normales GPL-Plugin `managed-gpl`
- **Distribution:** wenn Releases auf GitHub liegen sollen `github-releases`
- **Updates:** bei einem neuen GitHub-Plugin zunächst `none`, weil der Scaffold keinen Updater erfindet
- **Repository:** z. B. `cemfirat/wordpress-mein-plugin`

Bei Unsicherheit zu den Profilen siehe [[Plugin Profile]].

## Schritt 2: Repository Governance aktualisieren

Im Terminal:

```bash
cd ~/Developer/repository-governance
git switch main
git pull --ff-only
```

Falls Du Governance noch gar nicht lokal hast:

```bash
cd ~/Developer
git clone https://github.com/cemfirat/repository-governance.git
cd repository-governance
```

Das Klonen ist normalerweise **nur einmal** nötig.

## Schritt 3: Plugin erzeugen

Beispiel:

```bash
python3 scripts/wordpress-plugin-scaffold.py \
  --destination ../wordpress-mein-plugin \
  --profile simple \
  --slug wordpress-mein-plugin \
  --name "Mein Plugin" \
  --description "Erledigt eine klar beschriebene Aufgabe in WordPress." \
  --license-mode managed-gpl \
  --distribution github-releases \
  --updates none \
  --repository cemfirat/wordpress-mein-plugin
```

Der Zielordner `../wordpress-mein-plugin` muss leer bzw. noch nicht vorhanden sein. Der Generator überschreibt keinen gefüllten Ordner.

Wenn der Befehl erfolgreich war, endet die Meldung mit `audit clean`.

## Schritt 4: Ergebnis ansehen

Jetzt existiert neben Governance ungefähr:

```text
~/Developer/
├── repository-governance/
└── wordpress-mein-plugin/
    ├── .ccf-wordpress-plugin.json
    ├── .github/
    │   └── workflows/
    │       └── blueprint.yml
    ├── assets/
    │   └── logo.svg
    ├── CHANGELOG.md
    ├── LICENSE
    ├── README.md
    ├── readme.txt
    └── wordpress-mein-plugin.php
```

Das ist bereits die eigenständige Basis des neuen Plugins. Die eigentliche Plugin-Funktion kommt danach hinzu.

## Schritt 5: Leeres GitHub-Repository anlegen

Auf GitHub:

1. `New repository` wählen.
2. Als Namen `wordpress-mein-plugin` eintragen.
3. Sichtbarkeit passend wählen, z. B. Public.
4. **Keine** README, `.gitignore` oder License von GitHub zusätzlich erzeugen lassen – diese Dateien existieren bereits im Scaffold.
5. Repository erstellen.

Das GitHub-Repository ist zu diesem Zeitpunkt leer.

## Schritt 6: Den erzeugten Ordner zum Git-Repository machen

Zurück im Terminal:

```bash
cd ~/Developer/wordpress-mein-plugin
git init -b main
git add .
git commit -m "chore: initial plugin scaffold"
git remote add origin https://github.com/cemfirat/wordpress-mein-plugin.git
git push -u origin main
```

Dieser erste Push ist die einmalige Repository-Initialisierung. Der Scaffold wurde davor bereits lokal auditiert. Nach dem Push muss die GitHub-CI auf `main` grün werden.

## Schritt 7: Erste GitHub-CI prüfen

Öffne im neuen Repository den Reiter **Actions**. Dort muss der Workflow `WordPress plugin blueprint` erfolgreich durchlaufen.

Wenn er rot ist: nicht einfach weiterarbeiten oder blind neu starten. Siehe [[Rote CI beheben]].

## Schritt 8: Ab jetzt immer mit Branch arbeiten

Für die erste echte Plugin-Funktion:

```bash
git switch -c feat/erste-funktion
```

Nach der Änderung:

```bash
git add .
git commit -m "feat: add first plugin capability"
git push -u origin feat/erste-funktion
```

Der generierte Workflow läuft auf **jedem Branch-Push**. Jetzt wartest Du, bis die Branch-CI vollständig grün ist.

**Erst danach** wird ein Pull Request nach `main` geöffnet.

Nach dem PR läuft die PR-CI nochmals. Erst wenn auch sie grün ist, wird gemergt.

Die Regel lautet immer:

`Branch → Branch-CI grün → PR → PR-CI grün → Merge → main prüfen`

## Schritt 9: Was Du jetzt entwickeln darfst

Ab diesem Punkt arbeitest Du im neuen Plugin-Repository. Dort entstehen Plugin-Funktionen, Admin-Oberflächen, Tests und plugin-spezifische Dokumentation.

`repository-governance` änderst Du nur, wenn eine gemeinsame Regel oder ein gemeinsamer Blueprint für mehrere Repositories verbessert werden soll.

## Ohne Clone und ohne Terminal

Ein vollständig geführter GitHub-Button für `Neues Plugin erstellen` existiert derzeit noch nicht. Der aktuelle geprüfte Weg benötigt die lokale Governance-Arbeitskopie und den Scaffold-Befehl.

Ein späterer UI-Flow soll diese Schritte automatisieren, darf aber erst verwendet werden, wenn er dieselben Validierungen und CI-Grenzen zuverlässig einhält.
