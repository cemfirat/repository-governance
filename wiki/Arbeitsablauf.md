# Arbeitsablauf

Diese Seite beschreibt die normale Arbeit **nachdem ein Repository existiert**.

## Warum überhaupt ein Branch?

`main` ist der stabile Hauptstand. Neue Arbeit findet auf einem separaten Branch statt, damit sie geprüft werden kann, bevor sie in `main` kommt.

Beispiel: Du möchtest eine Funktion ergänzen.

## Schritt 1: Lokales `main` aktualisieren

```bash
git switch main
git pull --ff-only
```

## Schritt 2: Arbeits-Branch erstellen

```bash
git switch -c feat/meine-funktion
```

Jetzt arbeitest Du auf `feat/meine-funktion`, nicht direkt auf `main`.

## Schritt 3: Änderung durchführen und committen

Wenn die Änderung fertig ist:

```bash
git add .
git commit -m "feat: describe the change"
```

Ein Commit ist ein gespeicherter Zwischenstand im Git-Verlauf.

## Schritt 4: Branch zu GitHub pushen

```bash
git push -u origin feat/meine-funktion
```

Jetzt startet GitHub Actions die Branch-CI.

## Schritt 5: Warten, bis die Branch-CI grün ist

Im Reiter **Actions** bzw. bei den Checks prüfen, ob alle relevanten Jobs erfolgreich abgeschlossen sind.

**Solange ein relevanter Check läuft oder rot ist, wird kein Pull Request geöffnet.**

Wenn etwas fehlschlägt, siehe [[Rote CI beheben]].

## Schritt 6: Erst jetzt Pull Request öffnen

Wenn die Branch-CI vollständig grün ist, darf ein PR von `feat/meine-funktion` nach `main` geöffnet werden.

Der PR ist kein Ersatz für Branch-CI. Er kommt **danach**.

## Schritt 7: PR-CI prüfen

GitHub führt die Checks für den Pull Request erneut im PR-Kontext aus. Auch diese Checks müssen grün sein.

## Schritt 8: Mergen

Erst nach grüner PR-CI wird der PR gemergt.

## Schritt 9: `main` kontrollieren

Nach dem Merge prüfen:

- zeigt `main` auf den erwarteten neuen Stand?
- sind die `main`-Checks grün?
- wurde kein unbeabsichtigter Release ausgelöst?
- sind Dokumentation und Issues noch aktuell?

## Merksatz

`main aktualisieren → Branch → ändern → commit → push → Branch-CI grün → PR → PR-CI grün → Merge → main prüfen`

## Was Du nicht tun sollst

Keinen PR öffnen, während Branch-CI noch läuft. Keine roten Checks durch Abschalten von Tests oder pauschale Suppressions verstecken. Einen fehlgeschlagenen Job nur dann einfach erneut starten, wenn es einen plausiblen temporären Infrastrukturfehler gab.
