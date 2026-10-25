# GitHub-Repositories mit einem Terminal-Befehl absichern

Fuer alle deine GitHub-Projekte reicht das bestehende zentrale Repository **[repository-governance](https://github.com/cemfirat/repository-governance)**. Du brauchst **kein** neues `repository-blueprint-ai`.

## Einmal auf deinem Mac einrichten

1. Terminal oeffnen und [GitHub CLI](https://cli.github.com/) installieren: `brew install gh` (Homebrew muss vorhanden sein).
2. Mit `gh auth login` einmalig am eigenen GitHub-Konto anmelden. Die CLI muss die Berechtigung besitzen, Repository-Rulesets zu verwalten.
3. `git clone https://github.com/cemfirat/repository-governance.git` und dann `cd repository-governance`.
4. Aktuelle Version bei spaeteren Aufrufen per `git pull --ff-only` holen. Python 3 wird benoetigt; `python3 --version` prueft das.

## 1. GitHub-Repository vorbereiten

Du kannst ein bereits vorhandenes oder neu angelegtes Repository verwenden (Public oder Private). Ein neues Repository muss seinen Hauptbranch `main` haben. Vor dem Setzen verpflichtender CI-Checks muss eine **echte Projekt-CI auf Pull Requests nach main** mindestens einmal erfolgreich gelaufen sein. Ohne Code/Tests kann das Tool keine inhaltlichen Anwendungstests erfinden.

## 2. Genau ein Befehl

```bash
./scripts/setup.sh cemfirat/mein-projekt
```

`mein-projekt` durch den echten Repository-Namen ersetzen.

Das Tool liest die GitHub-Einstellungen und zeigt dir:
- Sichtbarkeit Public/Private und aktuellen Hauptbranch;
- vorhandene Hard-Guardrails und Merge-Regeln;
- bekannte reale GitHub-Actions-Tests;
- genau welche Schutzregeln neu eingerichtet oder aktualisiert wuerden.

**Es schreibt erst nach einer sichtbaren Vorschau und deiner Eingabe `ja`.** Wenn das Tool in einer nicht-interaktiven Umgebung laeuft, schreibt es ohne `--yes` generell nichts. Unbekannte Sonderregeln werden nicht einfach ueberschrieben.

Erfolg bedeutet: Pflicht-Pull-Requests, ein echter verpflichtender GitHub-Actions-Check (strikter aktueller Branch), aufgeloeste Code-Diskussionen, keine normalen Ausnahmen sowie Hard-Guardrails gegen Loeschen und Force-Push. `0` Pflicht-Approvals ist absichtlich korrekt, weil KI-Agenten entwickeln und ChatGPT als Technical Lead prueft. Es wird keine Fake-Review erzeugt.

## 3. Alle sicheren Korrekturen auf einmal vornehmen

Nach dem ersten Test an einem einzelnen Repository ist das der einfachste Weg fuer den Rest deiner Projekte:

```bash
./scripts/setup.sh --apply-safe-all --dry-run
./scripts/setup.sh --apply-safe-all
```

Der erste Befehl zeigt nur die Vorschau. Der zweite zeigt dieselbe Art von Vorschau und fragt am Ende **einmalig** nach `ALLE N`, wobei `N` die angezeigte Anzahl ist. Ein normales `ja` reicht bewusst nicht aus. Das Tool nimmt danach die betroffenen Projekte nacheinander vor und prueft die gespeicherten GitHub-Regeln nach jedem Schreibvorgang.

**Wichtig:** Nur `AENDERN`-Repos mit eindeutig sicherem Aenderungsplan werden aktualisiert. Alle als `PRUEFEN` eingestuften Repositories werden uebersprungen (z. B. fehlende echte CI, Sonderregeln, Forks, `develop`/`master`-Branches). Die Zuweisung wird vor jeder Aenderung erneut kontrolliert. Bei einem unerwarteten Fehler stoppt der Lauf; die zuvor erfolgreich gespeicherten Schutzregeln bleiben erhalten. Nach Fehlerklaerung kannst du den Befehl erneut ausfuehren. Der Sammelmodus unterstuetzt aus Sicherheitsgruenden kein `--yes` und keine nicht-interaktive Freigabe.

Zum Abschluss:

```bash
./scripts/setup.sh --all
```

Dieser Kontrollbefehl aendert grundsaetzlich nichts. Er zeigt auch die verbliebenen Sonderfaelle an, die wir in Ruhe einzeln behandeln.

## 4. Erst alle Repositories pruefen (ohne Aenderungen)

```bash
./scripts/setup.sh --all
```

Das listet die Repositories des angemeldeten GitHub-Kontos und meldet **OK**, **AENDERN** oder **PRUEFEN**. Dieser Aufruf ist strikt read-only; er schreibt nie Einstellungen. Optional: `./scripts/setup.sh --all --owner cemfirat`.

## Weitere Optionen

```bash
./scripts/setup.sh cemfirat/mein-projekt --dry-run
./scripts/setup.sh cemfirat/mein-projekt --check 'Name des echten CI-Jobs'
./scripts/setup.sh cemfirat/mein-projekt --yes
```

- `--dry-run`: absolut keine Aenderungen;
- `--check`: falls GitHub mehrere passende PR-Jobs zeigt; mehrfach nutzbar, aber nur fuer nachweislich erfolgreiche GitHub-Actions-PR-Jobs;
- `--yes`: bewusste, nicht-interaktive Zustimmung, **nicht** mit `--all` kombinierbar.

## Wann das Tool absichtlich stoppt

- **Keine echte PR-CI:** zuerst einen Workflow mit Projekt-Tests einrichten und einen PR erfolgreich pruefen; danach erneut aufrufen.
- **Mehrere unterschiedliche CI-Checks:** den benoetigten Job mit `--check` waehlen; vorhandene Pflichtchecks werden nicht ersetzt.
- **Hauptbranch `master` / `develop`:** keine automatische Umbenennung, manuell das passende Schutzkonzept festlegen.
- **Alte Sonder-Rulesets oder klassische Branch Protection:** erst manuell einschaetzen, nicht duplizieren.
- **Archiviert, Fork, Pflicht-Reviewer bereits > 0 oder fehlende GitHub-Rechte:** keine stillschweigende Aenderung.
- **Aenderung durch anderen Agenten waehrend deiner Vorschau:** Abbruch statt Ueberschreiben; neuen Plan erstellen.

Die vorhandenen fortgeschrittenen Skripte `apply-rulesets.sh` und `create-protected-repository.sh` bleiben verfuegbar. Ein normales GitHub-Projekt-Template uebernimmt administrative Regeln **nicht** automatisch. Der hier beschriebene Weg ist fuer **bereits bestehende** Repositories geeignet und benoetigt keine zusaetzliche Projektvorlage.

**Sicherheitsgrenze:** Die Offline-Tests beweisen die korrekte geplante Logik, nicht die tatsaechliche GitHub-Administratorausfuehrung mit einem neuen Testrepo. Nach der ersten echten Einrichtung auch die gespeicherten Rulesets und die Merge-Blockade bei fehlendem CI einmal kontrollieren.
