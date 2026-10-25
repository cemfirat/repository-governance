# WordPress-Sonderregeln: zwei gezielte Reparaturen

Diese Anleitung gehoert zu [Fleet-Aufgabe #41](https://github.com/cemfirat/repository-governance/issues/41). Sie ersetzt **nicht** die allgemeinen CI-, PR- oder Ruleset-Vorgaben.

## wordpress-widget-custom-css-classes (mehrere Test-Workflows)

Das Repository besitzt echte erfolgreiche PR-Tests auf dem gleichen PR-Commit (PR #11). Seine drei Workflows \`test.yml\`, \`blueprint.yml\` und \`plugin-check.yml\` laufen auf \`pull_request\` und enthalten zusammen **neun relevante GitHub-Actions-Jobs**. Keinen davon als Dummy ersetzen und keine nicht belegten Jobs verlangen.

Erst nur die Vorschau anzeigen:

\`\`\`bash
./scripts/setup.sh cemfirat/wordpress-widget-custom-css-classes \
  --check 'PHP 8.0 regression' \
  --check 'PHP 8.3 regression' \
  --check 'PHP 8.4 regression' \
  --check 'PHP 8.5 regression' \
  --check 'WordPress 6.5 / PHP 8.0' \
  --check 'WordPress latest / PHP 8.3' \
  --check 'Deterministic package' \
  --check 'WordPress plugin blueprint' \
  --check 'Official WordPress Plugin Check' \
  --dry-run
\`\`\`

Wenn alle neun Checks nachweislich in der Vorschau stehen, **denselben Befehl ohne \`--dry-run\`** ausfuehren, die Einzelaktion ansehen und mit \`ja\` bestaetigen. Das Script legt dann die zwei Standard-Rulesets neu an, prueft auf Drift, liest die gespeicherten Regeln zurueck und meldet jeden Fehler. Niemals \`--check test\` verwenden, wenn kein solcher PR-Job existiert.

## wordpress-calendar-booking (bestehendes Legacy-Ruleset)

Hier gibt es bereits ein aktives Ruleset \`main protection\` (ID **23837020**) mit vier Regeltypen, davon elf echten GitHub-Actions-Pflichtchecks. Der alte Zustand erlaubt noch die persoenliche User-Bypass-Ausnahme und erzwingt das Abschliessen der PR-Diskussionen nicht.

**Nicht** die zwei neuen Standard-Rulesets parallel hinzufuegen. Stattdessen das bestehende Regelnpaket gezielt haerten:

\`\`\`bash
python3 scripts/migrate_calendar_booking.py --dry-run
python3 scripts/migrate_calendar_booking.py
\`\`\`

Das Tool arbeitet **ausschliesslich** auf \`cemfirat/wordpress-calendar-booking\` mit der bekannten Ruleset-ID. Es verlangt genau elf unveraenderte Pflichtchecks mit offizieller GitHub-Actions-App, die bekannte alte User-Bypass-Ausnahme und das aktive \`main\`-Ziel. Stimmen Name, Typen, Checks, Branch oder Revision nicht, bricht es **ohne Schreibzugriff** ab.

Der zweite Befehl zeigt den exakten Plan und verlangt **\`KALENDER\`** als ausdrueckliche Freigabe. Die einzigen inhaltlichen Aenderungen sind:

- \`bypass_actors\` wird leer: kein Admin-Bypass;
- \`required_review_thread_resolution\` wird \`true\`: PR-Gespraeche muessen abgeschlossen sein.

Die Regeln gegen Loeschen/Force-Push, der bestehende PR-Check, strikter CI-Modus sowie alle elf CI-Checknamen und die restlichen Regelparameter bleiben exakt erhalten. Jede Revision wird direkt vor PUT erneut gelesen und danach anhand einer GitHub-GET-Antwort verifiziert. Die Migration unterstuetzt absichtlich kein \`--yes\`.

## Nachkontrolle

\`\`\`bash
./scripts/setup.sh --all
\`\`\`

Das Inventur-Tool kann das Calendar-Repo weiterhin als \`PRUEFEN\` anzeigen, **weil es ein anders benanntes Einzel-Ruleset nutzt**. Das bedeutet nach erfolgreicher Migration **nicht automatisch**, dass es ungeschuetzt ist. Die gespeicherten Werte im GitHub-Ruleset sind hier der technische Nachweis; fuer echte Merge-Gates danach einen Test-PR verwenden.

Einige andere Repositories sind absichtlich noch reine Website-Platzhalter (\`kalkurama-site\`, \`mediarama-site\`); dort waeren erfundene gruene Application-Tests nicht zulaessig.
