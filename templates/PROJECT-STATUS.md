# <Projekt> – verifizierter Projektstand

**Stand / geprüft am:** <ISO-Zeit Europe/Vienna>; **belegter Default-Commit:** `<SHA>`.  
**Status dieses Dokuments:** datierter Snapshot, **keine Live-Telemetrie**.  
**Aktives Issue / Arbeitsauftrag:** <Link>. **Letzte fachliche Owner-Entscheidung:** <Link + Datum>.

## 1. Ziel und geltende Entscheidungen

**Produktziel:** <Kurzbeschreibung mit Link zum maßgeblichen Produkt-/Business-Vertrag>.  
**Strengere lokale Regeln:** <AGENTS/Architecture/Release/CI-Verträge>.  
**Owner / Technical Lead / Implementierer:** <Zuständigkeiten, kein Code-Review vom Owner>.

## 2. Nachgewiesener Zustand

| Schicht | Letzter **wirklich** geprüfter Stand | Beleg und Datum |
| --- | --- | --- |
| Quelle / Default-Branch | <SHA oder nicht geprüft> | <Commit-URL> |
| Implementiert / Test | <Funktion / grüner exakter Test / nicht geprüft> | <CI-/Diff-Link> |
| Branch-CI / PR-CI / Merge | <getrennte Stufen, echte SHAs> | <Run-/PR-Links> |
| Veröffentlichung / Signatur | <Tag/Asset/Channel oder keine> | <GitHub Release + signierter Feed> |
| Installation / Deployment | <Host/Version nur nach echter Inventur; ansonsten unbekannt> | <Datum, redigierter Nachweis> |
| Backup / Restore / Isolation | <getrennte Tests oder nicht geprüft> | <Evidenz-Link> |
| Browser / Rollen / Fachabnahme | <wirklich geprüfte Plattformen/Rollen oder offen> | <Owner-Freigabe/Issue> |

**Ausdrücklich nicht belegt:** <Unzugängliche Provider, andere Kundeninstanzen, fehlende Screenshots, offene Tests>. Nicht aus der Abwesenheit von Einträgen auf ihre Nichtexistenz schließen.

## 3. Meilensteine und Akzeptanz

| Meilenstein | Ziel und messbares Done-Kriterium | Status | Issue/Beleg |
| --- | --- | --- | --- |
| <M1> | <Was muss **tatsächlich** laufen / prüfbar sein?> | <geplant/in Arbeit/tested/...> | <Link> |

**Fertig:** <exakte abgeschlossene Nachweise>  
**Offen / Blockiert:** <Risiko, echter nächster Bedarf>  
**Nächste zulässige Aktion:** <ein konkreter Schritt und Abhängigkeit>  
**Nicht verändert:** <Hosting, Kunden, Releases, Daten, falls relevant>

## 4. Pflegevertrag

Vor jeder neuen Arbeit und jedem Statusbericht die aktuelle Projektentscheidung, dieses Dokument, aktives Issue sowie **live verfügbare GitHub-/Deployment-Daten** abgleichen. Nach Merge/Release/Installation/Owner-Abnahme diese Datei und widersprechende README-Texte korrigieren. Bei eingefrorenem Release-Commit nicht durch einen Dokumentationscommit den exakt getesteten Paket-Commit verändern. Das Datum der echten Beobachtung gehört zu **jeder** veränderlichen Aussage; die heutige Uhrzeit ist kein Ersatz für Host-Evidenz.
