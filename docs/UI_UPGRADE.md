# GlitchHunter Web-UI Upgrade Plan

**Dokument erstellt:** 21. April 2026  
**Version:** 1.0  
**Status:** In Progress  

---

## Überblick

Dieses Dokument beschreibt den kompletten Plan zur Erweiterung der GlitchHunter Web-UI um alle CLI-Features. Die aktuelle Web-UI bietet bereits Repository-Analyse mit Stack-Auswahl, Live-Status via WebSocket und Ergebnisanzeige.

**Ziel:** Vollständige Web-UI mit allen CLI-Features plus erweiterten Funktionen wie Settings, Problem-Solving, Report-Generator, und mehr.

---

## Feature-Priorisierung

| Priorität | Feature | CLI-Äquivalent | LOC (FE/BE) | Phase |
|-----------|---------|----------------|-------------|-------|
| **HIGH** | Settings-Seite | `config show/set/reset` | 800 / 600 | 1 |
| **HIGH** | Problemlöse-Funktion | `problem solve` | 1200 / 900 | 2 |
| **HIGH** | Report-Generator | `report --format` | 600 / 500 | 2 |
| **HIGH** | Refactoring-Preview/Apply | `refactor --preview/--apply` | 900 / 700 | 1 |
| **MEDIUM** | Stack-Management | `stack list/select/status` | 500 / 400 | 3 |
| **MEDIUM** | Filter/Sortierung | `--severity`, `--languages` | 400 / 300 | 1 |
| **MEDIUM** | History/Verlauf | - | 500 / 400 | 2 |
| **MEDIUM** | Export-Funktionen | `--output` | 300 / 250 | 3 |
| **LOW** | Config-Management UI | `config show/set/reset` | 600 / 450 | 4 |
| **LOW** | User-Management | - | 1000 / 800 | 4 (optional) |

**Gesamtumfang:** ~8.100 LOC, 40+ API-Endpoints, 6 neue UI-Seiten

---

## Implementierungs-Phasen

### Phase 1: Minimum Viable (2-3 Wochen)

**Ziel:** Kleinste nutzbare Erweiterung

**Features:**
1. ✅ Settings-Seite
   - Allgemeine Einstellungen (Sprache, Theme, Zeitzone)
   - Analyse-Einstellungen (Default Stack, Worker, Timeout)
   - Speichern/Laden mit SQLite
2. ✅ Filter/Sortierung
   - Severity-Filter (critical, high, medium, low)
   - Sortierung nach Severity, Datei, Confidence
3. ✅ Refactoring-Preview
   - Vorschläge anzeigen
   - Diff-View mit Syntax-Highlighting
   - Anwenden/Rollback mit Git-Integration

**Lieferbare:**
- `ui/web/frontend/settings.html`, `settings.js`, `settings.css`
- `ui/web/backend/settings.py` (Settings-Service)
- `ui/web/backend/refactor.py` (Refactoring-Service)
- SQLite Schema für Settings
- API-Endpoints: `/api/v1/settings/*`, `/api/v1/refactor/*`

**Success Criteria:**
- [ ] Settings-Seite ist erreichbar und funktional
- [ ] Einstellungen werden persistent gespeichert
- [ ] Filter/Sortierung funktioniert auf Ergebnisseite
- [ ] Refactoring-Preview zeigt korrekte Diffs
- [ ] Refactoring kann angewendet und zurückgenommen werden

---

### Phase 2: Core Experience (3-4 Wochen)

**Ziel:** Kompletter Happy-Path

**Features:**
1. ✅ Problemlöse-Funktion
   - Prompt-Eingabe mit Text-Editor
   - Live-Updates via WebSocket
   - Klassifikation, Diagnose, Lösungsvorschläge
2. ✅ Report-Generator
   - JSON, Markdown, HTML Export
   - Report-Vorschau
   - Download-Funktion
3. ✅ History/Verlauf
   - Analyse-Historie mit Timeline
   - Filtern nach Datum, Stack, Status
   - Löschen einzelner Einträge

**Lieferbare:**
- `ui/web/frontend/problem.html`, `problem.js`, `problem.css`
- `ui/web/frontend/reports.html`, `reports.js`, `reports.css`
- `ui/web/frontend/history.html`, `history.js`, `history.css`
- `ui/web/backend/problem_solver.py`
- `ui/web/backend/reports.py`
- `ui/web/backend/history.py`

**Success Criteria:**
- [ ] Problem kann mit Prompt eingegeben werden
- [ ] Live-Updates via WebSocket funktionieren
- [ ] Klassifikation und Diagnose werden angezeigt
- [ ] Reports können in 3 Formaten generiert werden
- [ ] History zeigt alle vergangenen Analysen

---

### Phase 3: Edge Cases & Polish (2-3 Wochen)

**Ziel:** Robustheit und Benutzerfreundlichkeit

**Features:**
1. ✅ Stack-Management
   - Stack-Übersicht (A/B/C)
   - Konfiguration der Modelle
   - Stack-Testing mit Live-Feedback
2. ✅ Export-Funktionen
   - Multi-Format Export (JSON, CSV, Markdown)
   - Batch-Export für alle Ergebnisse
3. ✅ Error-Handling
   - Benutzerfreundliche Fehlermeldungen
   - Retry-Logik bei Netzwerkfehlern
   - Offline-Handling

**Lieferbare:**
- `ui/web/frontend/stacks.html`, `stacks.js`, `stacks.css`
- `ui/web/backend/stacks.py`
- Export-API-Endpoints
- Error-Boundaries im Frontend

**Success Criteria:**
- [ ] Stack-Management ermöglicht Wechsel zwischen A/B/C
- [ ] Export funktioniert für alle Formate
- [ ] Error-Messages sind benutzerfreundlich
- [ ] Alle E2E-Tests bestehen
- [ ] >80% Code-Coverage im Backend

---

### Phase 4: Optional (nach Bedarf)

**Features:**
1. ⏸️ Config-Management UI
   - YAML-Editor mit Syntax-Highlighting
   - Validierung mit Pydantic
   - Live-Vorschau
2. ⏸️ User-Management
   - Login/Logout mit JWT
   - Multi-User Support
   - Berechtigungen (Admin, User, Guest)

**Lieferbare:**
- YAML-Editor Komponente
- Auth-Middleware
- User-Database-Schema

---

## Dateistruktur

```
ui/web/
├── frontend/
│   ├── index.html              # Dashboard (✅ vorhanden)
│   ├── settings.html           # Settings-Seite (📝 Phase 1)
│   ├── problem.html           # Problemlöser (📝 Phase 2)
│   ├── reports.html           # Reports (📝 Phase 2)
│   ├── history.html           # Verlauf (📝 Phase 2)
│   ├── stacks.html            # Stack-Management (📝 Phase 3)
│   ├── css/
│   │   ├── main.css           # (✅ vorhanden)
│   │   ├── settings.css       # (📝 Phase 1)
│   │   ├── problem.css        # (📝 Phase 2)
│   │   ├── reports.css        # (📝 Phase 2)
│   │   ├── history.css        # (📝 Phase 2)
│   │   ├── stacks.css         # (📝 Phase 3)
│   │   └── refactor.css       # (📝 Phase 1)
│   └── js/
│       ├── main.js            # (✅ vorhanden)
│       ├── settings.js        # (📝 Phase 1)
│       ├── problem.js         # (📝 Phase 2)
│       ├── reports.js         # (📝 Phase 2)
│       ├── history.js         # (📝 Phase 2)
│       ├── stacks.js          # (📝 Phase 3)
│       └── refactor.js        # (📝 Phase 1)
│
└── backend/
    ├── app.py                 # (✅ vorhanden, erweitern)
    ├── schemas.py             # Pydantic Models (✅ vorhanden)
    ├── settings.py            # Settings-Service (📝 Phase 1)
    ├── problem_solver.py      # Problem-Solver-Service (📝 Phase 2)
    ├── reports.py             # Report-Service (📝 Phase 2)
    ├── refactor.py            # Refactoring-Service (📝 Phase 1)
    ├── history.py             # History-Service (📝 Phase 2)
    ├── stacks.py            # Stack-Service (📝 Phase 3)
    └── storage.py             # SQLite-Storage (📝 Phase 1)
```

---

## API-Endpoints

### Bestehende Endpoints (✅ implementiert)

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| POST | `/api/v1/analyze` | Analyse starten |
| GET | `/api/v1/jobs` | Job-Liste |
| GET | `/api/v1/jobs/{job_id}` | Job-Details |
| GET | `/api/v1/results/{job_id}` | Ergebnisse |
| GET | `/api/v1/status` | Server-Status |
| WS | `/ws/results/{job_id}` | Live-Updates |

### Neue Endpoints (nach Phase)

#### Phase 1: Settings & Refactoring

```python
# Settings
GET    /api/v1/settings              # Alle Settings laden
PUT    /api/v1/settings              # Alle Settings speichern
GET    /api/v1/settings/{category}   # Kategorie laden
PUT    /api/v1/settings/{category}   # Kategorie speichern
POST   /api/v1/settings/export       # Exportieren (JSON)
POST   /api/v1/settings/import       # Importieren (JSON)
POST   /api/v1/settings/reset        # Zurücksetzen

# Refactoring
GET    /api/v1/refactor/suggestions  # Vorschläge für Datei
POST   /api/v1/refactor/preview      # Preview generieren
POST   /api/v1/refactor/apply        # Anwenden
POST   /api/v1/refactor/rollback     # Rollback
GET    /api/v1/refactor/history      # Verlauf
```

#### Phase 2: Problem, Reports, History

```python
# Problem-Solving
POST   /api/v1/problem/solve         # Problem mit Prompt lösen
GET    /api/v1/problem/{id}          # Problem-Details
GET    /api/v1/problem/{id}/result   # Ergebnis
WS     /ws/problem/{id}              # Live-Updates
POST   /api/v1/problem/{id}/apply    # Lösung anwenden
GET    /api/v1/problem/history       # Verlauf
DELETE /api/v1/problem/{id}          # Problem löschen

# Reports
POST   /api/v1/reports/generate      # Report generieren
GET    /api/v1/reports               # Report-Liste
GET    /api/v1/reports/{id}          # Report-Details
GET    /api/v1/reports/{id}/download # Download
DELETE /api/v1/reports/{id}          # Löschen

# History
GET    /api/v1/history               # Verlauf (paginiert)
GET    /api/v1/history/{id}          # Detail
DELETE /api/v1/history/{id}          # Eintrag löschen
DELETE /api/v1/history/all           # Alles löschen
```

#### Phase 3: Stacks & Export

```python
# Stacks
GET    /api/v1/stacks                # Alle Stacks
GET    /api/v1/stacks/{id}           # Stack-Details
PUT    /api/v1/stacks/{id}           # Konfigurieren
POST   /api/v1/stacks/{id}/test      # Testen
GET    /api/v1/stacks/{id}/status    # Status

# Export
POST   /api/v1/export                # Export starten
GET    /api/v1/export/{id}/download  # Download
```

#### Phase 4: Optional

```python
# Config
GET    /api/v1/config/raw            # Raw YAML
PUT    /api/v1/config/raw            # YAML speichern
POST   /api/v1/config/validate       # Validierung

# Auth
POST   /api/v1/auth/login            # Login
POST   /api/v1/auth/logout           # Logout
GET    /api/v1/auth/me               # Current User
```

---

## Datenbankschema (SQLite)

### Settings

```sql
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,  -- JSON-serialized
    category TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_settings_category ON settings(category);
```

### History

```sql
CREATE TABLE IF NOT EXISTS analysis_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL UNIQUE,
    repo_path TEXT NOT NULL,
    stack TEXT NOT NULL,
    status TEXT NOT NULL,
    findings_count INTEGER DEFAULT 0,
    duration_seconds REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_history_created_at ON analysis_history(created_at);
CREATE INDEX idx_history_status ON analysis_history(status);
```

### Problems

```sql
CREATE TABLE IF NOT EXISTS problems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id TEXT NOT NULL UNIQUE,
    prompt TEXT NOT NULL,
    repo_path TEXT,
    status TEXT NOT NULL,
    classification TEXT,
    diagnosis TEXT,
    solution TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_problems_status ON problems(status);
```

### Reports

```sql
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT NOT NULL UNIQUE,
    job_id TEXT,
    problem_id TEXT,
    format TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reports_job_id ON reports(job_id);
```

---

## Settings-Kategorien

### 1. Allgemein

| Key | Typ | Default | Validierung |
|-----|-----|---------|-------------|
| `language` | String | `"de"` | `"de"`, `"en"` |
| `theme` | String | `"auto"` | `"light"`, `"dark"`, `"auto"` |
| `timezone` | String | `"Europe/Berlin"` | IANA Timezone |
| `date_format` | String | `"DD.MM.YYYY"` | Format-String |

### 2. Analyse

| Key | Typ | Default | Validierung |
|-----|-----|---------|-------------|
| `default_stack` | String | `"stack_b"` | `"stack_a"`, `"stack_b"`, `"stack_c"` |
| `default_parallel` | Boolean | `true` | - |
| `default_ml` | Boolean | `true` | - |
| `max_workers` | Integer | `4` | `1-16` |
| `timeout_per_analysis` | Integer | `300` | `60-3600` Sekunden |
| `auto_refresh_interval` | Integer | `30` | `5-300` Sekunden |

### 3. Security

| Key | Typ | Default | Validierung |
|-----|-----|---------|-------------|
| `api_keys` | Dict | `{}` | Verschlüsselt speichern |
| `session_timeout_minutes` | Integer | `60` | `5-1440` |
| `cors_origins` | List | `["http://localhost:6262"]` | URLs |
| `rate_limit_per_minute` | Integer | `60` | `10-1000` |

### 4. Logging

| Key | Typ | Default | Validierung |
|-----|-----|---------|-------------|
| `logging_level` | String | `"INFO"` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `logging_file` | String | `"logs/glitchhunter.log"` | Pfad |
| `logging_max_size_mb` | Integer | `10` | `1-100` MB |
| `logging_backup_count` | Integer | `5` | `1-20` |

---

## Test-Strategie

### Test-Pyramide

```
                    /\
                   /  \
                  / E2E \       (10-20 Tests)
                 /________\
                /          \
               /Integration \   (50-100 Tests)
              /______________\
             /                \
            /      Unit        \ (200-500 Tests)
           /____________________\
```

### Unit-Tests (Frontend)

| Feature | Test-Datei | Tests |
|---------|------------|-------|
| Settings | `tests/frontend/test_settings.js` | Form-Validierung, API-Calls, Storage |
| Problem | `tests/frontend/test_problem.js` | Prompt-Handling, WebSocket, Rendering |
| Reports | `tests/frontend/test_reports.js` | Format-Auswahl, Download |
| Refactor | `tests/frontend/test_refactor.js` | Diff-Rendering, Apply/Reject |

### Unit-Tests (Backend)

| Feature | Test-Datei | Tests |
|---------|------------|-------|
| Settings | `tests/backend/test_settings_api.py` | CRUD, Encryption, Validierung |
| Problem | `tests/backend/test_problem_api.py` | Solve, Classify, Apply |
| Reports | `tests/backend/test_reports_api.py` | Generate, Download |
| Refactor | `tests/backend/test_refactor_api.py` | Suggestions, Apply, Rollback |

### Integration-Tests

| Test | Beschreibung |
|------|--------------|
| `test_settings_integration.py` | Settings → SQLite → API → Frontend |
| `test_problem_integration.py` | Problem-Solver → ProblemManager → API |
| `test_reports_integration.py` | ReportGenerator → File-System → Download |
| `test_refactor_integration.py` | AutoRefactor → Git → Rollback |

### E2E-Tests (Playwright)

| Test | Flow |
|------|------|
| `test_e2e_settings.py` | Settings öffnen → Ändern → Speichern → Neu laden → Prüfen |
| `test_e2e_problem.py` | Problem eingeben → Lösen → Ergebnis prüfen → Anwenden |
| `test_e2e_reports.py` | Report generieren → Download → Inhalt prüfen |
| `test_e2e_refactor.py` | Refactoring vorschauen → Anwenden → Git-Log prüfen |

### Coverage-Ziele

| Bereich | Ziel |
|---------|------|
| Backend API | >85% Coverage |
| Frontend JS | >75% Coverage |
| Critical Paths | 100% (Analyse, Problem-Solving, Refactoring) |
| E2E | Alle User-Journeys abgedeckt |

---

## Risiken & Mitigation

| Risiko | Wahrscheinlichkeit | Auswirkung | Mitigation |
|--------|-------------------|------------|------------|
| **WebSocket-Verbindungsabbrüche** | Mittel | Hoch | Auto-Reconnect, Queue für Updates, Polling-Fallback |
| **Settings-Korruption** | Niedrig | Hoch | Backup vor Write, Validierung, Versionierung |
| **Performance bei großen Repos** | Hoch | Mittel | Pagination, Lazy-Loading, Caching, Worker-Threads |
| **Security (API-Keys)** | Mittel | Hoch | Fernet-Verschlüsselung, Environment-Vars, Key-Rotation |
| **Browser-Kompatibilität** | Niedrig | Niedrig | Modernes JS, Polyfills nur wenn nötig, Feature-Detection |
| **Git-Konflikte bei Refactoring** | Mittel | Mittel | Pre-Check, Merge-Strategie, Rollback, User-Warning |

---

## Abhängigkeits-Graph

```
                    ┌─────────────────┐
                    │   Settings-Seite│
                    │   (Phase 1)     │
                    └────────┬────────┘
                             │
                             ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│Filter/Sortierung│◄───│  Refactoring-   │    │  Problem-Solver │
│   (Phase 1)     │    │    Preview      │    │    (Phase 2)    │
└─────────────────┘    │   (Phase 1)     │    └────────┬────────┘
                       └────────┬────────┘             │
                                │                      │
                                ▼                      ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Report-Generator│    │  Stack-Management│
                       │   (Phase 2)     │    │    (Phase 3)    │
                       └────────┬────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ History/Verlauf │
                       │   (Phase 2)     │
                       └─────────────────┘
```

---

## Fortschritts-Tracking

### Phase 1: Minimum Viable

**Start:** 21. April 2026  
**Status:** ✅ Completed (100%)

| Feature | Status | Fertig | Notes |
|---------|--------|--------|-------|
| Settings-Seite | ✅ Completed | 100% | Backend + Frontend |
| Filter/Sortierung | ✅ Completed | 100% | Frontend |
| Refactoring-Preview | ✅ Completed | 100% | Backend + Frontend |
| Backend Services | ✅ Completed | 100% | Settings + Refactoring |
| API-Endpoints | ✅ Completed | 100% | Alle Endpoints |
| Tests | ✅ Completed | 100% | Unit + Integration |

**Lieferbare:**
- ✅ Settings-Seite funktional
- ✅ Filter/Sortierung implementiert
- ✅ Refactoring-Preview mit Diff-View
- ✅ Alle Phase-1-API-Endpoints
- ✅ Unit-Tests (>80% Coverage)
- ✅ Integration-Tests bestanden

---

### Phase 2: Core Experience

**Start:** 21. April 2026  
**Status:** ✅ Completed (100%)

| Feature | Status | Fertig | Notes |
|---------|--------|--------|-------|
| Problemlöse-Funktion | ✅ Completed | 100% | Backend + Frontend |
| Report-Generator | ✅ Completed | 100% | Backend + Frontend |
| History/Verlauf | ✅ Completed | 100% | Backend + Frontend |
| Backend Services | ✅ Completed | 100% | Problem + Report + History |
| API-Endpoints | ✅ Completed | 100% | Alle Endpoints |
| Tests | ✅ Completed | 100% | Unit + Integration + Performance |

**Lieferbare:**
- ✅ Problemlöse-Funktion mit WebSocket
- ✅ Report-Generator (JSON, MD, HTML)
- ✅ History mit Timeline & Charts
- ✅ Alle Phase-2-API-Endpoints
- ✅ Unit-Tests (>80% Coverage)
- ✅ Integration-Tests bestanden
- ✅ Performance-Tests bestanden

**Abgeschlossene Arbeiten (Phase 2.1 - 2.7):**

1. **Problemlöse-Funktion Backend** (`ui/web/backend/problem_solver.py`)
   - ✅ ProblemSolverService mit Multi-Step-Flow
   - ✅ WebSocket für Live-Updates
   - ✅ Klassifikation, Diagnose, Plan, Lösung
   - ✅ API-Endpoints: /api/v1/problem/*

2. **Problemlöse-Funktion Frontend** (`ui/web/frontend/problem.html`, `.css`, `.js`)
   - ✅ Prompt-Editor mit Optionen
   - ✅ Live-Status-Timeline (5 Schritte)
   - ✅ Ergebnis-Anzeige mit 4 Sektionen
   - ✅ ~1110 LOC gesamt

3. **Report-Generator Backend** (`ui/web/backend/reports.py`)
   - ✅ ReportService mit Multi-Format-Support
   - ✅ JSON, Markdown, HTML Generierung
   - ✅ Template-System (vorbereitet)
   - ✅ API-Endpoints: /api/v1/reports/*

4. **Report-Generator Frontend** (`ui/web/frontend/reports.html`, `.css`, `.js`)
   - ✅ Report-Formular mit Format-Auswahl
   - ✅ Reports-Übersicht mit Toolbar
   - ✅ Vorschau mit Download/Delete
   - ✅ ~910 LOC gesamt

5. **History Backend** (`ui/web/backend/history.py`, `history_router.py`)
   - ✅ HistoryManager mit SQLite
   - ✅ 3 Tabellen: analysis, problem, report
   - ✅ Statistik-Aggregation
   - ✅ Auto-Cleanup-Funktion
   - ✅ API-Endpoints: /api/v1/history/*

6. **History Frontend** (`ui/web/frontend/history.html`, `.css`, `.js`)
   - ✅ 4 Tabs: Analysen, Probleme, Reports, Timeline
   - ✅ Statistik-Übersicht (4 Karten)
   - ✅ Chart.js Integration für Timeline
   - ✅ Filter-Funktionen
   - ✅ ~1110 LOC gesamt

7. **Tests** (`tests/webui/test_phase2_features.py`)
   - ✅ Unit-Tests für alle Services
   - ✅ Integration-Tests für Flows
   - ✅ API-Endpoint-Tests
   - ✅ Performance-Tests
   - ✅ ~450 LOC Tests

**Getestete Funktionalität:**
```
✅ Problem-Solver Service (Intake → Classify → Diagnose → Plan → Fix)
✅ WebSocket Live-Updates
✅ Report-Generator (JSON, MD, HTML)
✅ History Manager (SQLite, Statistics, Cleanup)
✅ API-Endpoints (Problem, Report, History)
✅ Frontend-Integration (Problem, Reports, History)
✅ Performance (< 5s für 10 Problems, < 3s für 10 Reports)
✅ Build-Checks bestanden
```

**Nächste Schritte:**
- Phase 2 ist abgeschlossen!
- Optional: Phase 3 (Stack-Management) oder Phase 4 (User-Management)
- Oder: v3.0.0 Release vorbereiten

---

### Phase 2: Core Experience

**Start:** TBD  
**Status:** ⏳ Pending  

| Feature | Status | Fertig | Notes |
|---------|--------|--------|-------|
| Problemlöse-Funktion | ⏳ Pending | 0% | - |
| Report-Generator | ⏳ Pending | 0% | - |
| History/Verlauf | ⏳ Pending | 0% | - |
| Backend Services | ⏳ Pending | 0% | - |
| API-Endpoints | ⏳ Pending | 0% | - |
| Tests | ⏳ Pending | 0% | - |

**Lieferbare:**
- [ ] Problem-Solver UI
- [ ] Report-Generator (3 Formate)
- [ ] History-UI
- [ ] Alle Phase-2-API-Endpoints
- [ ] Unit-Tests (>80% Coverage)
- [ ] E2E-Tests bestanden

---

### Phase 3: Edge Cases & Polish

**Start:** TBD  
**Status:** ⏳ Pending  

| Feature | Status | Fertig | Notes |
|---------|--------|--------|-------|
| Stack-Management | ⏳ Pending | 0% | - |
| Export-Funktionen | ⏳ Pending | 0% | - |
| Error-Handling | ⏳ Pending | 0% | - |
| Backend Services | ⏳ Pending | 0% | - |
| API-Endpoints | ⏳ Pending | 0% | - |
| Tests | ⏳ Pending | 0% | - |

**Lieferbare:**
- [ ] Stack-Management UI
- [ ] Export für alle Formate
- [ ] Error-Boundaries
- [ ] Alle Phase-3-API-Endpoints
- [ ] >80% Gesamt-Coverage
- [ ] Performance-Tests bestanden

---

### Phase 4: Optional

**Start:** TBD  
**Status:** ⏳ Pending  

| Feature | Status | Fertig | Notes |
|---------|--------|--------|-------|
| Config-Management UI | ⏳ Pending | 0% | - |
| User-Management | ⏳ Pending | 0% | Optional |

---

## Code-Beispiele

### Settings-API Beispiel

```python
# ui/web/backend/settings.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal, Dict, List, Any
import sqlite3
from datetime import datetime

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])

class GeneralSettings(BaseModel):
    language: str = "de"
    theme: Literal["light", "dark", "auto"] = "auto"
    timezone: str = "Europe/Berlin"

@router.get("/")
async def get_all_settings() -> Dict[str, Any]:
    """Alle Settings laden."""
    conn = sqlite3.connect("settings.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT key, value, category FROM settings")
    rows = cursor.fetchall()
    conn.close()
    
    settings = {}
    for key, value, category in rows:
        if category not in settings:
            settings[category] = {}
        settings[category][key] = json.loads(value)
    
    return settings

@router.put("/general")
async def update_general_settings(settings: GeneralSettings):
    """Allgemeine Einstellungen speichern."""
    conn = sqlite3.connect("settings.db")
    cursor = conn.cursor()
    
    for key, value in settings.model_dump().items():
        cursor.execute(
            """INSERT OR REPLACE INTO settings (key, value, category, updated_at)
               VALUES (?, ?, ?, ?)""",
            (key, json.dumps(value), "general", datetime.now())
        )
    
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": "Settings gespeichert"}
```

### Frontend Settings.js Beispiel

```javascript
// ui/web/frontend/js/settings.js

class SettingsManager {
    constructor() {
        this.categories = ['general', 'analysis', 'security', 'logging'];
        this.currentCategory = 'general';
    }

    async loadSettings(category = null) {
        const url = category 
            ? `/api/v1/settings/${category}`
            : '/api/v1/settings';
        
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return await response.json();
    }

    async saveSettings(category, settings) {
        const response = await fetch(`/api/v1/settings/${category}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Speichern fehlgeschlagen');
        }
        
        return await response.json();
    }

    async exportSettings() {
        const response = await fetch('/api/v1/settings/export', {
            method: 'POST',
        });
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'glitchhunter-settings.json';
        a.click();
        window.URL.revokeObjectURL(url);
    }
}

// Initialisierung
const settingsManager = new SettingsManager();
```

---

## Zusammenfassung

Dieser Plan bietet eine vollständige Roadmap für die Erweiterung der GlitchHunter Web-UI um alle CLI-Features. Die Implementierung ist in 4 Phasen unterteilt, wobei Phase 1 (Settings, Filter, Refactoring-Preview) die höchste Priorität hat und innerhalb von 2-3 Wochen lieferbar ist.

**Gesamtaufwand:** ~8.100 LOC, 7-10 Wochen bei Vollzeit-Entwicklung

**Kritische Success Factors:**
1. Konsistente API-Designs nach REST-Prinzipien
2. Robustes Error-Handling im Frontend
3. Verschlüsselung sensibler Settings
4. Umfassende Test-Abdeckung (>80%)
5. Benutzerfreundliche Fehlermeldungen

**Nächste Schritte:**
1. ✅ Plan in UI_UPGRADE.md fixieren
2. ⏳ Mit Phase 1 Implementation beginnen
3. ⏳ Jede abgeschlossene Phase dokumentieren

---

## Changelog

| Datum | Version | Änderung | Autor |
|-------|---------|----------|-------|
| 21.04.2026 | 1.0 | Initiale Version | Planning Specialist |
