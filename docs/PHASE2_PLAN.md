# GlitchHunter Web-UI - Phase 2 Plan

## Phase 2: Core Experience (4-6 Wochen)

**Ziel:** Kompletter Happy-Path für Benutzer mit erweiterter Funktionalität

---

## Feature 1: Problemlöse-Funktion (Prompt-basiert)

### Beschreibung
Interaktive Problemlösung mit natürlicher Sprachbeschreibung. Benutzer kann ein Problem beschreiben und erhält Live-Analyse mit Lösungsvorschlägen.

### CLI-Äquivalent
`glitchhunter problem solve/intake/classify/diagnose/plan/fix`

### Komponenten

**Backend (`ui/web/backend/problem_solver.py`):**
- ProblemSolverService Klasse
- Integration mit bestehendem ProblemManager (`src/problem/`)
- WebSocket für Live-Updates
- Klassifikation und Diagnose

**Frontend (`ui/web/frontend/problem.html`):**
- Prompt-Editor (Textarea mit Syntax-Highlighting)
- Live-Status-Anzeige (Klassifikation → Diagnose → Plan → Lösung)
- Ergebnis-Viewer mit Code-Highlighting
- Option: Mit ML Prediction, Mit Code-Analyse, Auto-Fix

**API-Endpoints:**
```python
POST   /api/v1/problem/solve         # Problem mit Prompt lösen
GET    /api/v1/problem/{id}          # Problem-Details
GET    /api/v1/problem/{id}/result   # Ergebnis
WS     /ws/problem/{id}              # Live-Updates
POST   /api/v1/problem/{id}/apply    # Lösung anwenden
GET    /api/v1/problem/history       # Verlauf
```

**Geschätzte LOC:**
- Backend: ~600 LOC
- Frontend: ~800 LOC
- Tests: ~400 LOC

---

## Feature 2: Report-Generator

### Beschreibung
Generiert analysierbare Reports in verschiedenen Formaten (JSON, Markdown, HTML, PDF).

### CLI-Äquivalent
`glitchhunter report --format <format>`

### Komponenten

**Backend (`ui/web/backend/reports.py`):**
- ReportService Klasse
- Integration mit bestehendem ReportGenerator (`src/fixing/report_generator.py`)
- Template-System für Reports
- PDF-Generierung (WeasyPrint oder ReportLab)

**Frontend (`ui/web/frontend/reports.html`):**
- Report-Übersicht mit Filter
- Format-Auswahl (JSON, Markdown, HTML, PDF)
- Report-Vorschau
- Download-Manager

**API-Endpoints:**
```python
POST   /api/v1/reports/generate      # Report generieren
GET    /api/v1/reports               # Report-Liste
GET    /api/v1/reports/{id}          # Report-Details
GET    /api/v1/reports/{id}/download # Download
DELETE /api/v1/reports/{id}          # Löschen
```

**Geschätzte LOC:**
- Backend: ~400 LOC
- Frontend: ~500 LOC
- Tests: ~300 LOC

---

## Feature 3: History/Verlauf

### Beschreibung
Verlauf aller durchgeführten Analysen mit Timeline, Vergleich und Filter.

### Komponenten

**Backend (`ui/web/backend/history.py`):**
- HistoryManager Klasse
- SQLite-Integration für Persistenz
- Aggregation für Statistiken
- Cleanup für alte Einträge

**Frontend (`ui/web/frontend/history.html`):**
- Timeline-Ansicht
- Filter nach Datum, Stack, Status
- Vergleichs-Ansicht für zwei Analysen
- Details pro Analyse

**API-Endpoints:**
```python
GET    /api/v1/history               # Verlauf (paginiert)
GET    /api/v1/history/{id}          # Detail
DELETE /api/v1/history/{id}          # Eintrag löschen
DELETE /api/v1/history/all           # Alles löschen
POST   /api/v1/history/{id}/rerun    # Erneut ausführen
```

**Geschätzte LOC:**
- Backend: ~350 LOC
- Frontend: ~450 LOC
- Tests: ~250 LOC

---

## Implementierungs-Reihenfolge

### Woche 1-2: Problemlöse-Funktion
1. Backend-Service erstellen
2. WebSocket-Integration
3. Frontend mit Prompt-Editor
4. Live-Status-Anzeige
5. Tests

### Woche 3: Report-Generator
1. Backend-Service erstellen
2. Template-System
3. Frontend mit Format-Auswahl
4. Download-Funktion
5. Tests

### Woche 4: History/Verlauf
1. Backend-Manager erstellen
2. SQLite-Integration
3. Frontend mit Timeline
4. Vergleichs-Ansicht
5. Tests

### Woche 5-6: Integration & Polish
1. E2E-Tests
2. Performance-Optimierung
3. UI-Polish
4. Dokumentation

---

## Abhängigkeiten

**Problemlöse-Funktion:**
- Benötigt: ProblemManager (src/problem/)
- Optional: LLM-Client für Klassifikation

**Report-Generator:**
- Benötigt: ReportGenerator (src/fixing/report_generator.py)
- Optional: WeasyPrint für PDF

**History:**
- Benötigt: SQLite (bereits in Phase 1 eingerichtet)
- Benötigt: JobManager (bereits vorhanden)

---

## Success Criteria

**Problemlöse-Funktion:**
- [ ] Prompt-Eingabe führt zu Problemlösung
- [ ] Live-Updates via WebSocket funktionieren
- [ ] Klassifikation und Diagnose werden angezeigt
- [ ] Lösungsvorschläge anwendbar

**Report-Generator:**
- [ ] Reports in 4 Formaten generierbar (JSON, MD, HTML, PDF)
- [ ] Download funktioniert für alle Formate
- [ ] Report-Vorschau zeigt korrekte Daten

**History:**
- [ ] History-Liste zeigt vergangene Analysen
- [ ] Vergleichs-Ansicht funktioniert
- [ ] Filter sortieren korrekt

**Gesamt:**
- [ ] 80%+ Code-Coverage
- [ ] Alle E2E-Tests bestanden
- [ ] Performance < 3s für alle API-Calls

---

## Risiken & Mitigation

| Risiko | Wahrscheinlichkeit | Auswirkung | Mitigation |
|--------|-------------------|------------|------------|
| WebSocket-Verbindungsabbrüche | Mittel | Hoch | Auto-Reconnect, Polling-Fallback |
| PDF-Generierung komplex | Mittel | Mittel | Fallback auf HTML, externe Library |
| Große History-Datenmenge | Niedrig | Mittel | Pagination, Cleanup-Job |
| LLM-API nicht verfügbar | Mittel | Hoch | Fallback auf lokale Analyse |

---

**Gesamtaufwand Phase 2:** ~3000 LOC, 4-6 Wochen
