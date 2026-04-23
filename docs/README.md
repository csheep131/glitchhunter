# GlitchHunter Dokumentation

**Version:** 3.0.0-dev  
**Letztes Update:** 20. April 2026

## Inhaltsverzeichnis

### Einführung

- **[Hauptdokumentation](../README.md)** - Überblick, Installation, Quickstart
- **[Getting Started](GETTING_STARTED.md)** - Schritt-für-Schritt Installation und erste Analyse
- **[Architektur](ARCHITECTURE.md)** - Detaillierte Systemarchitektur und Design-Entscheidungen
- **[API-Referenz](API.md)** - Vollständige API-Dokumentation

### Entwicklung

- **[Contributing](CONTRIBUTING.md)** - Beitragsrichtlinien und Development-Setup
- **[Upgrade Guide](../development/UPGRADE3_PROGRESS.md)** - v3.0 Implementierungsstatus
- **[Roadmap](../ROADMAP.md)** - Zukünftige Features und Planung

### Technische Dokumente

#### Analyse & Detection

- **Multi-Agent Swarm** - Architektur des Agenten-Systems
- **ML Bug Prediction** - Feature-Extraction und ONNX-Modell
- **Dynamic Analysis** - Coverage-guided Fuzzing und Runtime-Tracing
- **Static Analysis** - Tree-sitter Parser und Complexity-Metriken

#### Refactoring & Fixing

- **Auto-Refactoring** - Automatisches Refactoring mit Git-Rollback
- **Code Smell Detection** - Erkennung von Code-Problemen
- **Safety Gates** - Validierung vor/nach Refactoring

#### Infrastruktur

- **Sandbox System** - Docker-Isolation und Security
- **Symbol Graph** - Dependency Mapping und Graph-Analyse
- **Configuration** - config.yaml Referenz

## Dokumentations-Status

| Dokument | Status | Version | Letztes Update |
|----------|--------|---------|----------------|
| README.md | ✅ Aktuell | v3.0 | 20. Apr 2026 |
| ARCHITECTURE.md | ✅ Aktuell | v3.0 | 20. Apr 2026 |
| GETTING_STARTED.md | ✅ Aktuell | v3.0 | 20. Apr 2026 |
| API.md | ✅ Aktuell | v3.0 | 20. Apr 2026 |
| CONTRIBUTING.md | ✅ Aktuell | v3.0 | 20. Apr 2026 |

## v3.0 Features

### Phase 1: Multi-Agent Swarm ✅

- **Swarm Coordinator** mit LangGraph StateGraph
- **5 spezialisierte Agenten:**
  - StaticScanner - Statische Code-Analyse
  - DynamicTracer - Runtime-Analyse
  - ExploitGenerator - PoC-Generierung
  - RefactoringBot - Auto-Refactoring
  - ReportAggregator - Konsolidierung

### Phase 2: ML & Auto-Refactoring ✅

- **Glitch Prediction Engine**
  - 32-dimensionale Feature-Extraction
  - ONNX-Modell für Bug-Vorhersage
  - Risk-Level-Klassifikation

- **Auto-Refactoring**
  - Extract Method, Remove Duplicates
  - Git-basiertes Rollback
  - Safety-Validierung

### Refactoring: Modulare Architektur ✅

- **37 modulare Dateien** (refactored von 7 Monolithen)
- **Base Interfaces** für alle Komponenten
- **Vollständige Typisierung** mit Type-Hints
- **Google-Style Docstrings** für alle öffentlichen APIs

## Schnellzugriff

### Installation

```bash
git clone https://github.com/glitchhunter/glitchhunter.git
cd glitchhunter
pip install -e .
```

### Erste Analyse

```bash
glitchhunter analyze /path/to/repo
```

### Python API

```python
from glitchhunter import SwarmCoordinator

coordinator = SwarmCoordinator()
results = await coordinator.run_swarm("/path/to/repo")
```

## Support

- **GitHub Issues:** [Issues erstellen](https://github.com/glitchhunter/glitchhunter/issues)
- **Dokumentation:** [Vollständige Docs](https://glitchhunter.readthedocs.io)
- **Discord:** [Community beitreten](https://discord.gg/glitchhunter)

---

**Hinweis:** Diese Dokumentation wird automatisch aus dem Code generiert. Bei Inkonsistenzen bitte Issue eröffnen.
