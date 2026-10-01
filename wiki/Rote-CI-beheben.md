# Rote CI beheben

Nicht blind neu starten.

## Vorgehen

1. Den ersten fachlich relevanten roten Job identifizieren.
2. Den exakten fehlgeschlagenen Step lesen.
3. Ursache einordnen:
   - Codefehler;
   - Testfehler;
   - Workflow-/Umgebungsfehler;
   - externe Abhängigkeit;
   - falsche Policy-Annahme.
4. Nur die Ursache korrigieren.
5. Branch-CI erneut vollständig bewerten.
6. PR erst bei Grün.

## Vermeiden

- Trial-and-Error-Commits ohne Diagnose;
- Warnungen pauschal unterdrücken;
- Tests abschalten, um grün zu werden;
- einen PR öffnen, obwohl die Branch-CI noch nicht grün ist.

Ein Retry ist nur sinnvoll, wenn ein plausibler transienter Infrastrukturfehler vorliegt.
