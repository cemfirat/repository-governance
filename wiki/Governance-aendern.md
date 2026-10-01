# Governance ändern

Eine Regel, die mehrere Repositories betrifft, wird **zuerst zentral** geändert.

## Reihenfolge

1. Änderung in `repository-governance` entwerfen.
2. Tests und technische Dokumentation mitändern.
3. Governance-Branch vollständig grün bekommen.
4. Erst dann Governance-PR öffnen.
5. PR-CI prüfen und mergen.
6. `main` nochmals prüfen.
7. Betroffene Plugins mit Fleet-/Upgrade-Planung identifizieren.
8. Jedes Plugin separat aktualisieren und testen.

## Keine ungeprüften Massenänderungen

Die Flotte wird nicht direkt auf `main` umgeschrieben. Blueprint-Upgrades bleiben pro Repository nachvollziehbar und reviewbar.
