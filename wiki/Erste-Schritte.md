# Erste Schritte

Diese Seite ist für den Fall gedacht, dass Du noch nicht weißt, was Du mit `repository-governance` machen sollst.

## 1. Die Grundidee

Du **kopierst oder benennst `repository-governance` für ein neues Plugin nicht um**. Das Repository bleibt immer die zentrale Quelle für Regeln, Blueprint, Generator und gemeinsame Dateien.

Für ein neues Plugin passiert stattdessen Folgendes:

```text
repository-governance
        ↓  erzeugt
wordpress-mein-plugin
        ↓  wird
cemfirat/wordpress-mein-plugin
```

Das neue Plugin ist danach ein komplett eigenständiges Repository.

## 2. Was Du einmalig auf Deinem Mac brauchst

Du brauchst Git und Python 3. Öffne das Terminal und prüfe:

```bash
git --version
python3 --version
```

Wenn beide Befehle eine Versionsnummer ausgeben, ist die technische Grundlage vorhanden.

Für das spätere Hochladen zu GitHub muss Git auf Deinem Mac außerdem mit GitHub authentifiziert sein. Wenn Du bereits andere Repositories pushen kannst, ist das schon erledigt.

## 3. Einen festen Arbeitsordner anlegen

Ein Beispiel:

```bash
mkdir -p ~/Developer
cd ~/Developer
```

Du kannst natürlich einen anderen Ordner verwenden. Wichtig ist nur, dass `repository-governance` und Deine Plugin-Projekte sauber nebeneinander liegen.

## 4. Repository Governance genau einmal klonen

Im Arbeitsordner:

```bash
git clone https://github.com/cemfirat/repository-governance.git
cd repository-governance
```

Danach sieht es ungefähr so aus:

```text
~/Developer/
└── repository-governance/
```

**Für das nächste Plugin klonst Du Governance nicht nochmals.** Du verwendest dieselbe lokale Arbeitskopie weiter.

## 5. Governance vor jedem neuen Plugin aktualisieren

Bevor Du ein neues Plugin erzeugst:

```bash
cd ~/Developer/repository-governance
git switch main
git pull --ff-only
```

Damit benutzt der Generator die aktuelle geprüfte Blueprint-Version.

## 6. Dann erzeugst Du das neue Plugin

Der Generator liegt in `repository-governance`, aber das Ergebnis wird **daneben** erstellt, nicht darin.

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

Wenn alles passt, meldet der Generator `audit clean`.

Danach:

```text
~/Developer/
├── repository-governance/
└── wordpress-mein-plugin/
```

`wordpress-mein-plugin` ist nun Dein neues Projekt. `repository-governance` bleibt unverändert die zentrale Governance.

Die komplette Anleitung für das Anlegen des GitHub-Repositories und den ersten Push steht unter [[Neues WordPress Plugin]].

## 7. Was der Generator bereits für Dich erledigt

Er erstellt unter anderem Manifest, README, Changelog, Logo, WordPress-`readme.txt`, Plugin-Hauptdatei, Lizenzdatei bei `managed-gpl` und die Blueprint-CI. Danach führt er automatisch den Blueprint-Audit aus. Ein fehlerhaftes Ergebnis wird nicht einfach als fertiger Plugin-Ordner ausgegeben.

## 8. Was der Generator bewusst nicht tut

Er erfindet keine Plugin-Funktion, keine Lizenzentscheidung und keinen nicht vorhandenen Update-Mechanismus. Außerdem erstellt er derzeit noch kein GitHub-Repository und pusht nichts selbst.

## Ohne Clone und ohne Terminal

Dieser Komfortweg ist **noch nicht implementiert**. Das Ziel ist später ein geführter GitHub-Ablauf, bei dem Name, Slug, Profil, Lizenz und Distribution eingegeben werden und Governance daraus das Repository erzeugt.

Bis dieser Weg entwickelt und getestet ist, ist der oben beschriebene lokale Scaffold der verbindliche Ablauf.
