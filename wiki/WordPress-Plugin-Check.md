# WordPress Plugin Check

Der offizielle WordPress Plugin Check ist eine **optionale gemeinsame Qualitätsschicht**.

## Wann einsetzen?

Erst wenn:

1. ein deterministisches installierbares Paket erzeugt werden kann;
2. dieses Paket in CI gebaut wird;
3. die ersten Findings fachlich geprüft wurden;
4. Branch-CI zuverlässig grün ist.

## Was wird geprüft?

Für `github-releases` oder `none`:

- general
- security
- performance
- accessibility

Für `wordpress.org` zusätzlich:

- plugin_repo

Damit werden WordPress.org-Verzeichnisregeln nicht irrtümlich auf bewusst extern verteilte Plugins angewandt.

## Regeln

- Paket bauen, dann **das Paket** prüfen.
- Nicht gegen eine Produktions-WordPress-Instanz laufen lassen.
- Den echten Plugin-Slug aus dem Manifest verwenden.
- Keine globalen Suppressions, nur um CI grün zu bekommen.
- Plugin Check ersetzt keine plugin-spezifischen Regression-/Integrationstests.
