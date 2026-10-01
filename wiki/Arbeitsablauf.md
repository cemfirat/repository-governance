# Arbeitsablauf

## Standard

1. Von aktuellem `main` einen kurzen Arbeits-Branch erstellen.
2. Eine klar abgegrenzte Änderung durchführen.
3. Branch-CI vollständig ausführen.
4. Fehler analysieren und gezielt korrigieren.
5. **Erst wenn alle relevanten Branch-Checks grün sind, einen PR öffnen.**
6. PR-CI vollständig prüfen.
7. PR mergen.
8. Den neuen `main`-Stand nochmals prüfen.

## Nicht erlaubt

- PR öffnen, obwohl Branch-CI noch läuft.
- PR öffnen, um dadurch erst die eigentliche CI zu starten.
- Fehlgeschlagene Jobs blind wiederholen.
- Direkt auf `main` schreiben, wenn die Änderung über den normalen PR-Prozess laufen kann.
- Eine rote CI durch pauschale Ausnahmen oder Suppressions „grün machen“.

## Nach dem Merge

Prüfen:

- zeigt `main` auf den erwarteten Commit?
- sind die `main`-Checks grün?
- wurde kein unbeabsichtigter Release ausgelöst?
- sind Issues/Docs noch aktuell?
