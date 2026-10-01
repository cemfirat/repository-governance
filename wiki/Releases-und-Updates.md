# Releases und Updates

Drei Dinge immer getrennt betrachten:

1. **Distribution** – woher bekommt der Benutzer das Plugin?
2. **Update URI** – welche Update-Quelle signalisiert WordPress?
3. **Update-Implementierung** – wie wird ein Update tatsächlich gefunden und installiert?

Eine GitHub-Distribution bedeutet nicht automatisch, dass bereits ein GitHub-Updater implementiert ist.

## Vor einem Release

- Paket deterministisch bauen;
- Plugin-Version und Metadaten prüfen;
- Regression-/Integrationstests grün;
- gegebenenfalls Plugin Check grün;
- Release-Guard kontrollieren.

## Wichtig

Governance darf niemals einen Update-Mechanismus behaupten, den der Plugin-Code nicht tatsächlich implementiert.
