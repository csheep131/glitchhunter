# GlitchHunter Web-UI - Phase 3 Plan

## Phase 3: Stack-Management & Advanced Features (3-4 Wochen)

**Ziel:** Vollständige Verwaltung der Hardware-Stacks mit Konfiguration, Monitoring und Testing

---

## Feature 1: Stack-Management UI

### Beschreibung
Benutzeroberfläche zur Verwaltung aller Hardware-Stacks (A, B, C) mit Konfiguration, Status-Anzeige und Testing.

### CLI-Äquivalent
`glitchhunter stack list/select/status`

### Komponenten

**Backend (`ui/web/backend/stacks.py`):**
- StackManager Klasse
- Hardware-Detektion Integration
- Model-Status-Checking
- Stack-Testing

**Frontend (`ui/web/frontend/stacks.html`):**
- Stack-Übersicht (Karten für A/B/C)
- Konfigurations-Editor pro Stack
- Model-Status-Anzeige
- Test-Buttons mit Live-Feedback

**API-Endpoints:**
```python
GET    /api/v1/stacks                # Alle Stacks
GET    /api/v1/stacks/{id}           # Stack-Details
PUT    /api/v1/stacks/{id}           # Stack konfigurieren
POST   /api/v1/stacks/{id}/test      # Stack testen
GET    /api/v1/stacks/{id}/status    # Status
GET    /api/v1/stacks/{id}/models    # Verfügbare Modelle
```

**Geschätzte LOC:**
- Backend: ~400 LOC
- Frontend: ~500 LOC
- Tests: ~250 LOC

---

## Feature 2: Stack-Konfiguration

### Beschreibung
Detaillierte Konfiguration jedes Stacks mit Modellen, Security-Einstellungen und Limits.

### Stack A (Standard)
- **Hardware:** GTX 3060 (8GB VRAM)
- **Modus:** Sequenziell
- **Modelle:**
  - Primary: Qwen3.5-9B (4-bit quantized)
  - Secondary: Phi-4-mini (8-bit)
- **Security:** Full (OWASP Top-10, API Security)
- **Inference:** max_batch_size=4, parallel_requests=false

### Stack B (Enhanced)
- **Hardware:** RTX 3090 (24GB VRAM)
- **Modus:** Parallel
- **Modelle:**
  - Primary: Qwen3.5-27B (4-bit quantized)
  - Secondary: DeepSeek-V3.2 (8-bit)
- **Security:** Full
- **Inference:** max_batch_size=10, parallel_requests=true

### Stack C (Remote API)
- **Hardware:** Remote (Ollama LAN, Cloud APIs)
- **Modus:** Hybrid (Remote-first mit lokalem Fallback)
- **Provider:**
  - Ollama (LAN): qwen3.5:9b, qwen3.5:27b
  - vLLM (LAN): Qwen/Qwen3.5-27B-Instruct
  - OpenAI (Cloud): gpt-4o, gpt-4o-mini
  - Anthropic (Cloud): claude-3-sonnet, claude-3-opus
  - DeepSeek (Cloud): deepseek-chat
- **Fallback-Kette:** ollama → vllm → deepseek → openai → local
- **Caching:** enabled (TTL=3600s, max_size=500MB)
- **Circuit-Breaker:** failure_threshold=5, recovery_timeout=60s

---

## Feature 3: Model-Status-Monitoring

### Beschreibung
Echtzeit-Überwachung der Modell-Verfügbarkeit und Performance.

### Features
- **Lokale Modelle:**
  - Pfad-Existenz prüfen
  - VRAM-Verbrauch anzeigen
  - Load/Unload Status
  - Letzte Verwendung

- **Remote Modelle:**
  - API-Verfügbarkeit prüfen
  - Response-Zeiten messen
  - Rate-Limit-Status
  - Kosten-Tracking (Cloud-APIs)

### API-Endpoints
```python
GET    /api/v1/models                # Alle Modelle
GET    /api/v1/models/local          # Lokale Modelle
GET    /api/v1/models/remote         # Remote Modelle
POST   /api/v1/models/{id}/load      # Modell laden
POST   /api/v1/models/{id}/unload    # Modell entladen
GET    /api/v1/models/{id}/status    # Modell-Status
```

---

## Feature 4: Stack-Testing

### Beschreibung
Umfassende Test-Funktionen für Stacks und Modelle.

### Test-Typen

**1. Quick-Test (30s)**
- Modell-Laden testen
- Einfache Inference
- Basis-Response-Validierung

**2. Performance-Test (2-5 min)**
- Batch-Inference (10-100 Requests)
- Response-Zeiten messen
- VRAM-Verbrauch tracken
- Throughput berechnen

**3. Stress-Test (10-20 min)**
- Maximale Auslastung
- Memory-Limits testen
- Error-Handling prüfen
- Recovery testen

### Test-Result
```json
{
  "test_id": "test_20260421_123456",
  "stack_id": "stack_b",
  "test_type": "performance",
  "status": "completed",
  "duration_seconds": 145.5,
  "results": {
    "avg_response_time_ms": 234.5,
    "p95_response_time_ms": 456.7,
    "p99_response_time_ms": 678.9,
    "requests_per_second": 12.5,
    "vram_usage_mb": 18432,
    "success_rate": 98.5,
    "error_count": 2
  },
  "recommendation": "Stack B ist bereit für Produktion"
}
```

---

## Feature 5: Hardware-Monitoring

### Beschreibung
Echtzeit-Überwachung der Hardware-Ressourcen.

### Monitoring-Daten
- **GPU:**
  - Auslastung (%)
  - VRAM-Verbrauch (MB/GB)
  - Temperatur (°C)
  - Power-Draw (W)
  - Fan-Speed (%)

- **CPU:**
  - Auslastung (%)
  - Kerne aktiv
  - Temperatur (°C)

- **RAM:**
  - Verbrauch (GB)
  - Verfügbar (GB)
  - Swap-Nutzung

### API-Endpoints
```python
GET    /api/v1/hardware              # Hardware-Info
GET    /api/v1/hardware/gpu          # GPU-Status
GET    /api/v1/hardware/cpu          # CPU-Status
GET    /api/v1/hardware/memory       # Memory-Status
WS     /ws/hardware                  # Live-Monitoring
```

---

## Implementierungs-Reihenfolge

### Woche 1: Stack-Management UI
1. Backend-Manager erstellen
2. API-Endpoints implementieren
3. Frontend-Übersicht (Karten für A/B/C)
4. Konfigurations-Editor
5. Tests

### Woche 2: Model-Status-Monitoring
1. Model-Manager erstellen
2. Lokale Modell-Prüfung
3. Remote-Modell-Prüfung
4. Frontend-Status-Anzeige
5. Tests

### Woche 3: Stack-Testing
1. Test-Framework erstellen
2. Quick-Test implementieren
3. Performance-Test implementieren
4. Stress-Test implementieren
5. Frontend-Test-UI
6. Tests

### Woche 4: Hardware-Monitoring
1. Hardware-Detector erweitern
2. Monitoring-Service erstellen
3. WebSocket für Live-Updates
4. Frontend-Monitoring-Dashboard
5. Tests

---

## Dateistruktur

```
ui/web/
├── backend/
│   ├── stacks.py              # Stack-Manager
│   ├── models.py              # Model-Manager
│   ├── hardware_monitor.py    # Hardware-Monitoring
│   └── test_runner.py         # Test-Framework
│
└── frontend/
    ├── stacks.html            # Stack-Übersicht
    ├── stacks.css
    ├── stacks.js
    ├── hardware.html          # Hardware-Monitoring
    ├── hardware.css
    └── hardware.js
```

---

## API-Endpoints Komplette Liste

### Stacks
```python
GET    /api/v1/stacks                       # Alle Stacks
GET    /api/v1/stacks/{id}                  # Stack-Details
PUT    /api/v1/stacks/{id}                  # Stack konfigurieren
POST   /api/v1/stacks/{id}/test             # Stack testen
GET    /api/v1/stacks/{id}/status           # Status
GET    /api/v1/stacks/{id}/models           # Modelle
POST   /api/v1/stacks/{id}/models/load      # Modell laden
POST   /api/v1/stacks/{id}/models/unload    # Modell entladen
```

### Models
```python
GET    /api/v1/models                       # Alle Modelle
GET    /api/v1/models/local                 # Lokale Modelle
GET    /api/v1/models/remote                # Remote Modelle
GET    /api/v1/models/{id}                  # Modell-Details
POST   /api/v1/models/{id}/load             # Laden
POST   /api/v1/models/{id}/unload           # Entladen
GET    /api/v1/models/{id}/status           # Status
```

### Hardware
```python
GET    /api/v1/hardware                     # Hardware-Info
GET    /api/v1/hardware/gpu                 # GPU-Status
GET    /api/v1/hardware/cpu                 # CPU-Status
GET    /api/v1/hardware/memory              # Memory-Status
WS     /ws/hardware                         # Live-Monitoring
```

### Testing
```python
POST   /api/v1/tests/quick                  # Quick-Test
POST   /api/v1/tests/performance            # Performance-Test
POST   /api/v1/tests/stress                 # Stress-Test
GET    /api/v1/tests/{id}/status            # Test-Status
GET    /api/v1/tests/{id}/results           # Test-Ergebnisse
```

---

## Success Criteria

### Stack-Management
- [ ] Stack-Übersicht zeigt alle 3 Stacks (A/B/C)
- [ ] Konfiguration pro Stack speicherbar
- [ ] Stack-Status aktuell (Online/Offline/Error)
- [ ] Modell-Liste pro Stack

### Model-Monitoring
- [ ] Lokale Modelle: Pfad, Größe, Status
- [ ] Remote Modelle: Verfügbarkeit, Latenz
- [ ] Modell laden/entladen funktioniert
- [ ] Status-Updates in Echtzeit

### Stack-Testing
- [ ] Quick-Test (< 30s)
- [ ] Performance-Test (2-5 min)
- [ ] Stress-Test (10-20 min)
- [ ] Test-Ergebnisse mit Empfehlung

### Hardware-Monitoring
- [ ] GPU: Auslastung, VRAM, Temperatur
- [ ] CPU: Auslastung, Temperatur
- [ ] RAM: Verbrauch, Verfügbar
- [ ] Live-Updates via WebSocket

### Gesamt
- [ ] 80%+ Code-Coverage
- [ ] Alle E2E-Tests bestanden
- [ ] Performance < 2s für alle API-Calls

---

## Risiken & Mitigation

| Risiko | Wahrscheinlichkeit | Auswirkung | Mitigation |
|--------|-------------------|------------|------------|
| **GPU-Treiber nicht verfügbar** | Mittel | Hoch | Fallback auf CPU-Mode, Docker-Support |
| **Remote-APIs nicht erreichbar** | Hoch | Mittel | Circuit-Breaker, Fallback-Kette |
| **VRAM-Overload** | Mittel | Hoch | Auto-Unload, Memory-Limits |
| **Test-Timeout** | Niedrig | Mittel | Configurable Timeouts, Cancel-Support |

---

## Geschätzter Aufwand

**Gesamt:** ~2500 LOC, 3-4 Wochen bei Vollzeit-Entwicklung

| Komponente | Backend | Frontend | Tests | Gesamt |
|------------|---------|----------|-------|--------|
| Stack-Management | 400 | 500 | 250 | 1150 |
| Model-Monitoring | 350 | 400 | 200 | 950 |
| Stack-Testing | 400 | 350 | 250 | 1000 |
| Hardware-Monitoring | 300 | 350 | 150 | 800 |
| **Gesamt** | **1450** | **1600** | **850** | **3900** |

---

**Nächste Schritte:**
1. Plan reviewen und freigeben
2. Mit Stack-Management UI beginnen
3. Woche für Woche implementieren
