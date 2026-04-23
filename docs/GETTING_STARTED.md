# GlitchHunter v3.0 - Getting Started

**Version:** 3.0.0-dev  
**Letztes Update:** 20. April 2026

## Inhaltsverzeichnis

1. [Einführung](#einführung)
2. [Voraussetzungen](#voraussetzungen)
3. [Installation](#installation)
4. [Erste Schritte](#erste-schritte)
5. [Konfiguration](#konfiguration)
6. [Verwendung](#verwendung)
7. [Beispiele](#beispiele)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Einführung

GlitchHunter v3.0 ist ein **KI-gestütztes Code-Analyse-Tool** das folgende Technologien kombiniert:

- **Multi-Agent Swarm** - 5 spezialisierte KI-Agenten
- **ML Bug Prediction** - 32-dimensionale Feature-Analyse
- **Dynamic Analysis** - Runtime-Tracing mit Coverage-Fuzzing
- **Auto-Refactoring** - Automatisches Refactoring mit Git-Rollback

### Was kann GlitchHunter?

✅ **Code-Analyse** - Statische und dynamische Analyse  
✅ **Bug-Erkennung** - ML-basierte Bug-Vorhersage  
✅ **Auto-Refactoring** - Automatisches Code-Improvement  
✅ **Security-Scan** - OWASP Top 10 Detection  
✅ **Coverage-Tracking** - Runtime-Analyse mit eBPF  

---

## Voraussetzungen

### Systemanforderungen

| Komponente | Minimum | Empfohlen |
|------------|---------|-----------|
| **Python** | 3.10 | 3.11+ |
| **RAM** | 8 GB | 16 GB+ |
| **Speicher** | 5 GB | 10 GB+ |
| **CPU** | 4 Kerne | 8+ Kerne |
| **GPU** | Optional | NVIDIA 8GB+ VRAM |

### Software

- **Git** - Für Repository-Klonung
- **Node.js 18+** - Für JS/TS-Analyse (optional)
- **Docker** - Für Sandbox-Isolation (optional)
- **BCC** - Für eBPF-Tracing auf Linux (optional)

---

## Installation

### Schritt 1: Repository klonen

```bash
git clone https://github.com/glitchhunter/glitchhunter.git
cd glitchhunter
```

### Schritt 2: Virtuelle Umgebung erstellen

**Linux/macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

### Schritt 3: Dependencies installieren

```bash
# Installation im Development-Modus
pip install -e .

# Oder mit allen optionalen Dependencies
pip install -e ".[dev,docs]"
```

### Schritt 4: Installation verifizieren

```bash
# Version prüfen
glitchhunter --version

# Hilfe anzeigen
glitchhunter --help

# System-Check
glitchhunter check
```

### Optionale Installationen

#### Docker für Sandbox

```bash
# Docker installieren (Ubuntu/Debian)
sudo apt-get install docker.io
sudo usermod -aG docker $USER

# Docker testen
docker run hello-world
```

#### BCC für eBPF-Tracing (Linux)

```bash
# BCC installieren (Ubuntu/Debian)
sudo apt-get install bpfcc-tools

# eBPF testen
sudo /usr/share/bcc/tools/execsnoop
```

#### Node.js für JS/TS-Analyse

```bash
# Node.js installieren
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Version prüfen
node --version  # Sollte v18+ sein
```

---

## Erste Schritte

### Schnellstart: Einzelne Datei analysieren

```bash
# Einfache statische Analyse
glitchhunter analyze /path/to/your/code.py

# Mit Output-Verzeichnis
glitchhunter analyze /path/to/repo --output ./reports

# Mit spezifischen Agenten
glitchhunter analyze /path/to/repo --agents static,dynamic
```

### Komplette Swarm-Analyse

```bash
# Alle Agenten verwenden
glitchhunter analyze /path/to/repo --swarm

# Mit ML-Prediction
glitchhunter analyze /path/to/repo --swarm --ml

# Mit Auto-Refactoring Vorschlägen
glitchhunter analyze /path/to/repo --swarm --ml --suggest-refactors
```

### Report generieren

```bash
# Markdown Report
glitchhunter report /path/to/repo --format markdown --output report.md

# JSON Report
glitchhunter report /path/to/repo --format json --output report.json

# HTML Report
glitchhunter report /path/to/repo --format html --output report.html
```

---

## Konfiguration

### config.yaml

GlitchHunter verwendet `config.yaml` im Projektroot:

```yaml
# Swarm Configuration
agent:
  max_iterations: 5
  timeout_per_state: 300  # Sekunden
  enable_swarm: true

# Sandbox Configuration
sandbox:
  use_docker: true
  timeout: 60  # Sekunden
  enable_ebpf: true  # Nur Linux

# Prediction Configuration
prediction:
  min_probability: 0.4  # Minimum Bug-Wahrscheinlichkeit
  model_path: "models/glitch_model.onnx"
  use_cuda: true  # GPU-Beschleunigung wenn verfügbar

# Refactoring Configuration
refactoring:
  auto_apply: false  # Nicht automatisch anwenden
  min_confidence: 0.7  # Minimum Confidence für Vorschläge
  create_backup: true  # Backup-Dateien erstellen
  run_tests: true  # Tests nach Refactoring ausführen
```

### Umgebungsvariablen

```bash
# Model-Pfad
export GLITCHHUNTER_MODEL_PATH="/path/to/model.onnx"

# Config-Pfad
export GLITCHHUNTER_CONFIG="/path/to/config.yaml"

# Log-Level
export GLITCHHUNTER_LOG_LEVEL="DEBUG"

# CUDA aktivieren
export GLITCHHUNTER_USE_CUDA=1
```

---

## Verwendung

### CLI-Befehle

#### analyze

Analysiert ein Repository mit allen Agenten.

```bash
glitchhunter analyze <pfad> [Optionen]

Optionen:
  --agents LISTE        Spezifische Agenten (comma-separated)
  --swarm               Alle Agenten verwenden
  --ml                  ML-Prediction aktivieren
  --output DIR          Output-Verzeichnis
  --format FORMAT       Output-Format (markdown, json, html)
  --verbose             Detaillierte Ausgabe
```

#### refactor

Führt Auto-Refactoring durch.

```bash
glitchhunter refactor <pfad> [Optionen]

Optionen:
  --auto-apply          Automatisch anwenden
  --dry-run             Nur Vorschläge anzeigen
  --min-confidence FLOAT  Minimum Confidence (0-1)
  --backup              Backup erstellen
  --test                Tests ausführen
```

#### report

Generiert einen Analyse-Report.

```bash
glitchhunter report <pfad> [Optionen]

Optionen:
  --format FORMAT       markdown, json, html
  --output DATEI        Output-Datei
  --include-ml          ML-Predictions einschließen
  --include-refactors   Refactoring-Vorschläge einschließen
```

#### check

Überprüft die Installation.

```bash
glitchhunter check

# Ausgabe:
✓ Python 3.11.0
✓ Dependencies installiert
✓ config.yaml gefunden
✓ Model geladen (ONNX)
✓ Docker verfügbar
✓ eBPF verfügbar (Linux)
```

### Python API

#### Einfache Analyse

```python
from glitchhunter import GlitchHunter

# Initialisieren
hunter = GlitchHunter()

# Analysieren
results = hunter.analyze("/path/to/repo")

# Ergebnisse anzeigen
for finding in results.findings:
    print(f"{finding.severity}: {finding.title}")
    print(f"  File: {finding.file_path}:{finding.line_start}")
    print(f"  Confidence: {finding.confidence:.0%}")
```

#### Swarm-Analyse

```python
from glitchhunter import SwarmCoordinator
import asyncio

async def run_swarm():
    coordinator = SwarmCoordinator()
    results = await coordinator.run_swarm("/path/to/repo")
    
    print(f"Static Findings: {len(results.static_findings)}")
    print(f"Dynamic Findings: {len(results.dynamic_findings)}")
    print(f"ML Predictions: {len(results.ml_predictions)}")
    print(f"Refactoring Vorschläge: {len(results.refactoring_suggestions)}")

asyncio.run(run_swarm())
```

#### ML-Prediction

```python
from glitchhunter.prediction import PredictionEngine
import asyncio

async def predict():
    engine = PredictionEngine()
    predictions = await engine.predict("/path/to/repo")
    
    for pred in predictions:
        print(f"{pred.symbol_name}: {pred.risk_level}")
        print(f"  Bug-Wahrscheinlichkeit: {pred.bug_probability:.0%}")
        print(f"  Top-Feature: {max(pred.feature_importance, key=pred.feature_importance.get)}")

asyncio.run(predict())
```

#### Auto-Refactoring

```python
from glitchhunter.fixing import AutoRefactor
import asyncio

async def refactor():
    refactoring = AutoRefactor("/path/to/repo")
    
    # Vorschläge generieren
    suggestions = await refactoring.analyze()
    
    for suggestion in suggestions:
        print(f"{suggestion.title}: {suggestion.description}")
        print(f"  Confidence: {suggestion.confidence:.0%}")
        print(f"  Risk: {suggestion.risk_level}")
    
    # Refactoring anwenden (mit Git-Rollback)
    if suggestions:
        result = await refactoring.apply(suggestions[0])
        print(f"Erfolg: {result.success}")
        if result.git_commit:
            print(f"Git-Commit: {result.git_commit}")

asyncio.run(refactor())
```

---

## Beispiele

### Beispiel 1: Python-Projekt analysieren

```bash
# Repository klonen
git clone https://github.com/example/python-project.git
cd python-project

# GlitchHunter Analyse
glitchhunter analyze . --swarm --ml --output ./glitch-report

# Report anzeigen
cat ./glitch-report/report.md
```

### Beispiel 2: Auto-Refactoring durchführen

```bash
# Analyse mit Refactoring-Vorschlägen
glitchhunter analyze /path/to/repo --suggest-refactors

# Refactoring im Dry-Run Modus
glitchhunter refactor /path/to/repo --dry-run

# Refactoring automatisch anwenden (mit Backup)
glitchhunter refactor /path/to/repo --auto-apply --backup
```

### Beispiel 3: ML-Prediction für große Codebase

```bash
# Batch-Prediction für gesamtes Repository
glitchhunter predict /path/to/large-repo --batch --output predictions.json

# Nur高风险 Dateien
glitchhunter predict /path/to/repo --min-probability 0.7

# Mit Feature-Importance
glitchhunter predict /path/to/repo --show-features
```

### Beispiel 4: CI/CD Integration

```yaml
# .github/workflows/glitchhunter.yml
name: GlitchHunter Analysis

on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install GlitchHunter
        run: |
          pip install -e .
      
      - name: Run Analysis
        run: |
          glitchhunter analyze . --swarm --ml --output ./report
      
      - name: Upload Report
        uses: actions/upload-artifact@v3
        with:
          name: glitchhunter-report
          path: ./report
```

---

## Troubleshooting

### Installation-Probleme

#### "No module named 'glitchhunter'"

```bash
# Virtuelle Umgebung aktivieren
source .venv/bin/activate

# Installation wiederholen
pip install -e .
```

#### "ONNX Runtime nicht gefunden"

```bash
# ONNX Runtime installieren
pip install onnxruntime  # CPU
pip install onnxruntime-gpu  # GPU
```

#### "Docker nicht verfügbar"

```bash
# Docker Service starten
sudo systemctl start docker

# User zur Docker-Gruppe hinzufügen
sudo usermod -aG docker $USER
newgrp docker
```

### Runtime-Probleme

#### "Out of Memory"

```bash
# Batch-Größe reduzieren
export GLITCHHUNTER_BATCH_SIZE=16

# Weniger Agenten verwenden
glitchhunter analyze /path/to/repo --agents static
```

#### "eBPF nicht verfügbar"

```bash
# eBPF ist nur auf Linux verfügbar
# Alternative: Docker-Sandbox verwenden
export GLITCHHUNTER_USE_DOCKER=1
```

#### "ML-Modell nicht gefunden"

```bash
# Model-Pfad prüfen
ls -la models/glitch_model.onnx

# Model herunterladen (falls verfügbar)
./scripts/download_model.sh
```

---

## FAQ

### Häufige Fragen

**F: Wie lange dauert eine Analyse?**  
A: Abhängig von der Codebase-Größe:
- < 10k LOC: ~20 Sekunden
- 10k-50k LOC: ~1-2 Minuten
- 50k-100k LOC: ~5 Minuten
- > 100k LOC: ~10 Minuten

**F: Benötige ich eine GPU?**  
A: Nein, aber GPU beschleunigt:
- ML-Prediction (ONNX mit CUDA)
- Feature-Extraction (parallel)

**F: Ist GlitchHunter sicher?**  
A: Ja, mit mehreren Sicherheitsmechanismen:
- Docker-Sandbox für Code-Ausführung
- Git-Rollback für Refactoring
- Syntax-Validierung vor Anwendung

**F: Welche Sprachen werden unterstützt?**  
A: 8 Sprachen:
- Python, JavaScript, TypeScript
- Rust, Go, Java
- C, C++

**F: Kann ich eigene Agenten hinzufügen?**  
A: Ja, über BaseAgent-Interface:
```python
from agent.agents.base import BaseAgent

class MyCustomAgent(BaseAgent):
    async def analyze(self, repo_path: Path, **kwargs):
        # Deine Implementierung
        pass
```

**F: Wie funktioniert das Git-Rollback?**  
A: Vor jedem Refactoring wird ein Git-Commit erstellt:
```bash
# Bei Fehler automatisch
git reset --hard <checkpoint-commit>
```

**F: Wo sind die Reports gespeichert?**  
A: Standardmäßig in `./reports/`:
- `report.md` - Markdown-Report
- `report.json` - JSON-Report
- `findings/` - Einzelne Findings

---

## Nächste Schritte

1. **[Architektur-Dokumentation](ARCHITECTURE.md)** - System-Design verstehen
2. **[API-Referenz](API.md)** - Detaillierte API-Dokumentation
3. **[Contributing](CONTRIBUTING.md)** - Zu GlitchHunter beitragen
4. **[Upgrade Guide](../development/UPGRADE3_PROGRESS.md)** - v3.0 Features

---

## Support

- **GitHub Issues:** [Issues erstellen](https://github.com/glitchhunter/glitchhunter/issues)
- **Dokumentation:** [Vollständige Docs](https://glitchhunter.readthedocs.io)
- **Community:** [Discord beitreten](https://discord.gg/glitchhunter)
