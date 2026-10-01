# Plugin Profile

## simple

Für kleine, klar begrenzte PHP-Plugins mit wenig eigener Infrastruktur.

Typische Beispiele:

- Doctype Inserter
- At Head Tag
- Widget Custom CSS Classes

## application

Für Plugins mit tieferen Integrationen, Datenflüssen, APIs, Admin-Bereichen oder höheren Security-/Privacy-Anforderungen.

Typische Beispiele:

- CCF Sites & Ads WordPress Connector
- WordPress Calendar Booking

## block

Für Block-Editor-orientierte Plugins.

Der Produkt-Scaffold kommt bewusst vom offiziellen `@wordpress/create-block`-Tool. Repository Governance legt anschließend die gemeinsame Governance-Schicht darüber.

## Grundsatz

Das Profil standardisiert nur das, was wirklich gemeinsam sein soll. Produktarchitektur und plugin-spezifische Tests bleiben individuell.
