# Verbindlicher Arbeitsstandard: Projektführung und Nachweise

**Version:** 2026-10-31 · **Geltung:** jedes vom Owner beauftragte, erreichbare eigene GitHub-Produkt- oder Service-Repository. **Sonderfall:** Upstream-Forks/Spiegel werden zunächst **nur gelesen**; nicht pauschal verändert.  
**Art:** interne operative Arbeitsvereinbarung; keine eigenständige rechtsverbindliche Dienstleistungsvereinbarung und kein Versprechen über Stunden, Budget, Liefertermine oder unzugängliche Systeme.

## 1. Verantwortlichkeiten (nicht austauschbar)

| Funktion | Eigentümer der Entscheidung/Prüfung |
| --- | --- |
| Produktziel, strategische Richtung, fachliche Priorität, Budget, UX-Zielbild, wirtschaftliche Regeln und finale sichtbare Abnahme | Auftraggeber/Product Owner |
| Technische Analyse, Architektur innerhalb geltender Produktentscheidungen, Implementierung/Delegation, Code-/Security-/Datenbank-/UI-Review, Fehlerdiagnose, CI, Release- und Rollback-Integrität | Technical Lead/technischer Auftragnehmer |
| Implementieren, testen und konkret dokumentieren ohne selbstständige technische Endfreigabe | beauftragte Coding-Agenten |
| Nachweis, was wirklich gemergt, veröffentlicht, installiert, gemessen und abgenommen wurde | Technical Lead durch **lesbare Primärquellen** (GitHub, CI, Betriebsinventur, echte Tests, Owner-Abnahme) |

Der Auftraggeber **muss keine Codes prüfen**, keine alten Chats rekonstruieren und keine bekannten Grundsatzentscheidungen wiederholen. Er erhält nur tatsächlich entscheidungspflichtige Fragen, mit begründeter Empfehlung und Folgen. Kein Agent behauptet, einen Host, Browser, Kundenbestand oder eine private Ressource geprüft zu haben, wenn nur Repository-Dokumentation gelesen wurde.

## 2. Quellenrangfolge und Wahrheitstest

**Projektportfolio & Reihenfolge:** im **privaten** übergeordneten Portfolio des Owners.  
**Pro Produkt:** gültige Produktdefinition/Entscheidungseinträge, eigene `AGENTS.md`, Architektur-/Sicherheits-/Supportverträge und aktives Issue sind maßgeblich. Die technischen Universalstandards dieses Repositories **ergänzen** sie, sie überschreiben keine strengeren lokalen Regeln, Plan-Locks, Release-Prozesse oder CI-Trigger.

| Aussage | Zulässiger Nachweis |
| --- | --- |
| „Beschlossen“ | explizite Owner-Entscheidung mit Datum und ggf. abgelöster Vorentscheidung |
| „Implementiert“ | aktueller Code/Commit und Issue-Anforderungen |
| „Getestet“ | exakte SHA, prüfbare Tests/CI-Run, Laufzeit und Ergebnis |
| „Gemergt“ | PR-Merge, aktueller Zielbranch und Git-Tree-Readback |
| „Veröffentlicht“ | unveränderliches Tag, signiertes Artefakt und zuständige Release-/Feed-Gates |
| „Installiert“ | redigierte **echte** Host-/Deployment-Inventur nach dem Rollout |
| „Abgenommen“ | explizit dokumentierte fachliche/visuelle/reale Betriebsabnahme am richtigen Ziel |

Bei Widersprüchen zuerst Quelle, Gültigkeit und Zeitpunkt vergleichen. Unbekannter Live-Zustand heißt **nicht überprüft**, niemals „sicher nicht vorhanden“. Dokumentierte Historie darf bleiben, aber kein Einstiegstext darf einen **veralteten** Versionsstand als aktuellen ausgeben. Modellgedächtnis und frühere Chats sind Kontext, **keine** primären Betriebsnachweise.

## 3. Pflichtablauf jeder neuen Arbeit

1. **Vor Beginn** in den privaten Portfolio-Kontext und das genannte Produktrepo einlesen: gültige Entscheidungen, aktuelle Projektstatus-Datei (mit Zeitstempel!), aktuelles Issue, `main`/Default-Head, offene PRs, letzte Releases und relevante Deployment-/CI-Evidenz. Existiert keine Statusdatei, `not documented` festhalten; nie einen Status erfinden.
2. **Arbeitsauftrag abgrenzen:** Ziel, Nutzerwirkung, A/B/C/D-Bezug (bestehend/Gap/Vorschlag/Konflikt), geltende Entscheidungen, konkrete Nichtziele, Risiken/Abhängigkeiten und **prüfbare Akzeptanzkriterien** im Issue. Neue Produkt-, Budget- und UX-Entscheidungen vorher Owner-Freigabe; kein heimlicher Scope-Wechsel.
3. **Umsetzen und prüfen:** quellennahe statische Prüfung; gezielte Regressionen; keine Trial-and-Error-Runs und kein blindes erneutes GitHub Actions. Ausführbare lokale Prüfungen nutzen; technische Begutachtung des kompletten finalen Diffs durch nicht denselben Implementierer, soweit getrennte Agenten beteiligt.
4. **CI und Merge:** dauerhafte globale Regel **kein PR vor grüner Branch-CI des exakten finalen Heads**. Bei noch fehlender echter CI zuerst einen verlässlichen projektspezifischen PR-Test etablieren, **keine künstlichen Dummy-Green-Checks**. Nach Branch-Grün eigenständige PR-CI, danach Merge und identische Code-Tree-Prüfung. Unterschiedliche CI-Trigger der Projekte bleiben erhalten.
5. **Release/Deployment:** Veröffentlichung ist **nicht** Installation. Signatur, SHA, Release-Commit und geplanter Channel vor dem Tag prüfen; reale Host-/Datenbank-/Backup-/Rollback-Gates separat belegen. Owner-freigabepflichtige irreversible oder kostenpflichtige Änderungen nicht still ausführen.
6. **Abnahme und Übergabe:** Nutzerfunktionen/Visuals mit realen Referenzen und Browser-/Rollenprüfungen vergleichen, soweit relevant; Owner entscheidet fachliche Annahme. Pro Arbeitsetappe kurz `Fertig / Evidenz / Offen / nächster zulässiger Schritt / nicht verändert` samt Issue-/Commit-/Run-/Host-Beleg berichten.

**Statusfolge (getrennt führen):** `Vorgeschlagen → Beauftragt → Implementiert → Lokal getestet → Branch-CI grün → PR-CI grün → Gemergt → Signiert veröffentlicht → Tatsächlich installiert → Real abgenommen`. Im Einzelfall können Release- oder UI-Gates „nicht anwendbar“ sein, aber nie aus einer anderen Stufe abgeleitet werden.

## 4. Statuspflege als Arbeitsergebnis, nicht Dekoration

Jedes aktive **erstparteiliche** Projekt muss einen **eindeutigen, datierten Status-Einstieg** besitzen, z.B. `docs/PROJECT-STATUS.md` oder eine vorhandene gleichwertige Datei. Die [Vorlage](../templates/PROJECT-STATUS.md) ist ein Hilfsmittel, **keine zweite parallele Wahrheit**.

Der Status nennt:
- Projekt-/Produktziel sowie aktuelle verbindliche Entscheidung/Issue;
- erfassten Default-Branch/SHA und den tatsächlichen Prüfzeitpunkt;
- letzte GitHub-Veröffentlichung, tatsächliche Installation(en) **nur mit echtem Beleg**;
- Tests, reale Off-host-Recovery, Sicherheits-/Berechtigungsgrenzen und UI/Owner-Abnahme jeweils gesondert;
- aktiven Meilenstein, priorisierte abhängige Issues und messbare Done-Kriterien;
- **offene oder unbekannte** Host-/Kunden-/Provider-Informationen;
- letzten realen Arbeitsfortschritt und nächste erlaubte Aktion.

Nach jedem Owner-Beschluss, abgeschlossenem Arbeitspaket, Merge, Release, Rollout oder abgebrochenem Test **Status nachführen**. Während eines **SHA-fixierten Release-Freeze** dürfen selbst reine Dokumentationscommits den geprüften Paket-Commit nicht unbemerkt ändern: Evidence vorläufig am Issue erfassen und Dokumentation kontrolliert nach dem Tag integrieren, oder das neue exakte Paket neu testen. Nie behaupten, eine auf einem Branch befindliche Datei sei schon auf `main`.

**Sicherheitsgrenze:** In einem öffentlichen Governance-Repository ausschließlich generische Standards veröffentlichen. Private Repositorynamen und vollständige Portfolio-Listen gehören in das **private** Portfolio. Keine Secrets, Kundendaten, privaten IP-Adressen oder Credentials in Dokumentation, CI-Logs oder Issues.

## 5. Effizienz und Eskalation

- Zusammenhängende Arbeit in **einem** umgrenzten Block: Code, Tests, Dokumentation und Versionierung im passenden Paket. Keine Serie von Mini-PRs allein wegen verspäteter Dokumentation.
- Keine Massen-Runs, keine Blind-Reruns. Vor jedem CI-Lauf Toolchain und lokale Checks; nur notwendige echte GitHub-Gates.
- Forks, Legacy-Projekte, externe Upstreams und Repositories mit besonderem Branch-/Ruleset-Vertrag **erst auditieren**, nicht automatisch angleichen.
- Bei fehlendem Connector, fehlendem Hostzugriff oder widersprüchlichen Quellen **konkrete Beweisgrenze** und risikokleine nächste Prüfung nennen. Nur fachliche oder finanziell relevante Entscheidungen dem Owner vorlegen.
- Nie Arbeitsversprechen „läuft im Hintergrund“ abgeben; jeder Status beschreibt **jetzt** beendete Arbeit und belegte offene Schritte.

## 6. Mindest-Definition-of-Done für Governance

- Ein prüfbarer Status-Einstieg pro aktivem, erstparteilichem Projekt, mit Datum, Quellen und genau **einer** aktuellen Versions-/Installationswahrheit.
- Repository-README/AGENTS/Issue-/PR-Vorlagen verweisen darauf und **können** keine neueren Live-Fakten ohne Prüfnachweis behaupten.
- Ein neuer Agent kann aus dem aktuellen Repo **ohne Frage an den Owner** Ziel, gültige Beschlüsse, belegten technischen Stand, echte offene Gates und nächste erlaubte Aktion richtig nennen.
- Audit-Evidenz und Status werden im Projekt-Repo integriert, mit passender echter Branch-/PR-CI; ein universelles Markdown-Template ist **kein Beleg**, dass alle Projekte bereits umgestellt wurden.
