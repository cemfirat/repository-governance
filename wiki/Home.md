# Repository Governance – Mini-Handbuch

Dieses Wiki ist die **kurze Bedienungsanleitung** für die tägliche Arbeit mit `cemfirat/repository-governance`.

> **Wichtig:** Das Wiki erklärt den Ablauf. Die technische Quelle der Wahrheit bleibt im Repository: `standards/`, `blueprints/`, `rulesets/`, `scripts/` und die Tests.

## Die wichtigste Regel

**Kein Pull Request vor vollständig grüner Branch-CI.**

Der normale Ablauf ist:

`Branch → Änderung → Branch-CI grün → PR → PR-CI grün → Merge → main prüfen`

Diese Reihenfolge gilt auch für automatisierte Blueprint-Upgrades.

## Schnellzugriff

- [[Arbeitsablauf]]
- [[Neues WordPress Plugin]]
- [[Bestehendes Plugin aktualisieren]]
- [[Plugin Profile]]
- [[WordPress Plugin Check]]
- [[WordPress Playground]]
- [[Releases und Updates]]
- [[Rote CI beheben]]
- [[Governance ändern]]
- [[Entscheidungsgrenzen]]
- [[Technische Referenz]]

## Was Repository Governance leistet

Repository Governance sorgt dafür, dass die WordPress-Plugins als zusammengehörige Familie gepflegt werden, ohne ihre unterschiedliche Produktarchitektur künstlich zu vereinheitlichen.

Gemeinsam geregelt werden vor allem:

- Repository- und Branch-Schutz;
- Manifest und Blueprint-Version;
- Branding und Basis-Metadaten;
- Lizenz- und Distributionsmodell als explizite Angaben;
- Packaging- und Release-Grundsätze;
- wiederverwendbare Audits;
- optionaler WordPress Plugin Check;
- kontrollierte Blueprint-Upgrades.

Plugin-spezifische Funktionen, Tests, Abhängigkeiten und Oberflächen bleiben im jeweiligen Plugin-Repository.
