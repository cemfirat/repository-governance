# Glossar

Die wichtigsten Begriffe im Mini-Handbuch:

## Repository

Ein GitHub-Projekt mit Dateien und Git-Verlauf. Jedes Plugin hat sein eigenes Repository. `repository-governance` ist ebenfalls ein eigenes Repository, aber kein Plugin.

## Repository Governance

Die zentrale Bauordnung und Werkzeugkiste. Sie enthält Regeln, Blueprint, Generatoren, Prüfungen und gemeinsame Dateien.

## Blueprint

Die gemeinsame technische Grundstruktur und Regeln für eine Repository-Familie. Der WordPress-Plugin-Blueprint legt fest, welche gemeinsamen Dateien und Metadaten vorhanden sein müssen.

## Scaffold

Ein automatisch erzeugtes Startgerüst. Der Scaffold-Generator erstellt aus dem Blueprint einen neuen Plugin-Ordner.

## Slug

Die technische, stabile Kennung eines Plugins, z. B. `wordpress-mein-plugin`. Normalerweise nur Kleinbuchstaben, Zahlen und Bindestriche.

## `main`

Der stabile Haupt-Branch eines Repositories.

## Branch

Ein separater Arbeitszweig. Änderungen werden dort entwickelt und geprüft, bevor sie nach `main` kommen.

## Commit

Ein gespeicherter Stand im Git-Verlauf mit einer Beschreibung der Änderung.

## Push

Überträgt lokale Commits zu GitHub. Ein Branch-Push startet die dafür konfigurierten GitHub Actions.

## CI

`Continuous Integration`. Automatische Prüfungen, z. B. Syntax, Tests, Blueprint-Audit oder Plugin Check.

## Branch-CI

CI, die direkt auf dem Arbeits-Branch nach einem Push läuft. Bei Cem gilt: **Kein Pull Request vor vollständig grüner Branch-CI.**

## Pull Request / PR

Ein kontrollierter Vorschlag, einen Branch in einen anderen Branch – meistens `main` – zu übernehmen.

## PR-CI

Prüfungen im Pull-Request-Kontext. Auch sie müssen grün sein, bevor gemergt wird.

## Merge

Übernimmt die freigegebenen Änderungen aus einem Branch in `main`.

## Manifest

Die Datei `.ccf-wordpress-plugin.json`. Sie beschreibt für Governance die wichtigsten Fakten des Plugins, z. B. Blueprint-Version, Profil, Slug, Lizenz und Distribution.

## Profil

Legt die Art des Plugins fest: `simple`, `application` oder `block`. Siehe [[Plugin Profile]].

## Distribution

Woher Benutzer das Plugin bekommen, z. B. GitHub Releases, WordPress.org oder gar keine öffentliche Distribution.

## Update-Kanal

Wie WordPress Aktualisierungen tatsächlich findet und installiert. Eine GitHub-URL allein implementiert noch keinen GitHub-Updater.

## Audit

Eine Prüfung, ob das Repository die Blueprint-Regeln erfüllt. `audit clean` bedeutet, dass die geprüften Blueprint-Regeln erfüllt sind.

## GitHub Actions

GitHubs Automationssystem, in dem CI-Workflows laufen.
