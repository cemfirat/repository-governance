# Repository Governance – Mini-Handbuch

Dieses Wiki ist die Bedienungsanleitung für die Repository Governance und die gemeinsamen WordPress-Plugin-Blueprints.

**Wenn Du damit noch nie gearbeitet hast, beginne mit [[Erste Schritte]].** Dort wird ohne Vorwissen erklärt, was `repository-governance` ist, was ein Blueprint ist und wie daraus ein neues Plugin entsteht.

> **Wichtig:** Das Wiki erklärt den Ablauf. Die technische Quelle der Wahrheit bleibt im Repository: `standards/`, `blueprints/`, `rulesets/`, `scripts/` und die Tests.

## Das Wichtigste zuerst

`repository-governance` ist **nicht** die Vorlage, die Du für jedes neue Plugin kopierst und umbenennst.

Es ist die zentrale **Bauordnung und Werkzeugkiste**. Du hast sie normalerweise genau einmal lokal. Der Scaffold-Generator darin erzeugt für jedes neue Plugin einen eigenen Ordner mit eigener README, eigenem Plugin-Code, eigener CI und eigenem GitHub-Repository.

Das Grundprinzip:

```text
repository-governance
        ↓
Scaffold-Generator
        ↓
neues eigenständiges Plugin
        ↓
eigenes GitHub-Repository
```

## Die wichtigste GitHub-Regel

**Kein Pull Request vor vollständig grüner Branch-CI.**

Der normale Ablauf nach der einmaligen Repository-Initialisierung ist:

`main aktualisieren → Arbeits-Branch → Änderung → push → Branch-CI grün → PR → PR-CI grün → Merge → main prüfen`

Siehe [[Arbeitsablauf]] für die Schritt-für-Schritt-Version.

## Ich möchte …

- **zum ersten Mal anfangen** → [[Erste Schritte]]
- **ein neues WordPress-Plugin erstellen** → [[Neues WordPress Plugin]]
- **an einem bestehenden Plugin arbeiten** → [[Arbeitsablauf]]
- **ein bestehendes Plugin auf einen neuen Blueprint bringen** → [[Bestehendes Plugin aktualisieren]]
- **verstehen, was `simple`, `application` und `block` bedeuten** → [[Plugin Profile]]
- **eine rote GitHub Action verstehen** → [[Rote CI beheben]]
- **Begriffe wie Branch, PR, CI oder Scaffold nachschlagen** → [[Glossar]]

## Was zentral geregelt wird

Repository Governance hält gemeinsame Dinge konsistent: Branding, Manifest, Lizenz-Metadaten, Packaging-Regeln, CI-Baseline, Plugin Check und kontrollierte Blueprint-Upgrades.

Die eigentliche Plugin-Funktion bleibt immer im jeweiligen Plugin-Repository. Ein Booking-Plugin darf intern völlig anders aufgebaut sein als ein kleines Utility-Plugin.

## Was heute noch nicht automatisch geht

Ein neues Plugin kann noch nicht mit einem einzigen Button direkt auf GitHub erzeugt werden. Der aktuelle, geprüfte Weg verwendet den lokalen Scaffold-Generator. Der geplante Komfortweg ohne Clone und ohne Terminal ist noch nicht implementiert.
