# Changelog

Alle wesentlichen Änderungen an GlitchHunter werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [3.0.0-alpha] - 2026-04-20

### ✨ Hinzugefügt

#### Multi-Agent Swarm Architecture
- **SwarmCoordinator** mit LangGraph StateGraph für Workflow-Orchestrierung
- **5 spezialisierte Agenten:**
  - `StaticScannerAgent` - Statische Code-Analyse mit Semgrep + Tree-sitter
  - `DynamicTracerAgent` - Runtime-Analyse mit Coverage-Fuzzing + eBPF
  - `ExploitGeneratorAgent` - PoC-Testcase Generierung
  - `RefactoringBotAgent` - Auto-Refactoring Vorschläge
  - `ReportAggregatorAgent` - Konsolidierung aller Findings
- **SwarmFinding** - Einheitliches Finding-Format mit Evidence-Tracking
- **SwarmState** - Geteilter State für LangGraph

#### Dynamic Analysis Sandbox
- **BaseSandbox** - Docker-isolierte Ausführung
- **DynamicTracerAgent** - Dynamische Analyse mit:
  - Coverage-guided Fuzzing für Python (coverage.py)
  - eBPF/ptrace Tracing für Linux (BCC)
  - AFL Fuzzing Integration
  - JavaScript/TypeScript Tracing

#### ML Bug Prediction Engine
- **GlitchPredictionModel** - ONNX-basiertes Vorhersagemodell
- **FeatureExtractor** - 32-dimensionale Feature-Extraction:
  - Graph-Features (Degree, Centrality, PageRank, Betweenness)
  - Complexity-Features (Cyclomatic, Cognitive, LOC)
  - Structural-Features (Clustering, Triangles, Community)
  - History-Features (Churn, Bug-Rate, Contributors)
- **PredictionEngine** - Integration in Swarm Coordinator
- **PredictionFinding** - Finding-Format für ML-Predictions

#### Auto-Refactoring Engine
- **AutoRefactor** - Modulweises Refactoring mit Git-Rollback
- **RefactoringSuggestion** - Vorschlags-Format
- **RefactoringResult** - Ergebnis-Format
- **4 Refactoring-Typen:**
  - ExtractMethodRefactoring
  - RemoveDuplicateRefactoring
  - ReplaceMagicNumberRefactoring
  - SimplifyConditionRefactoring
- **3 Analyzer:**
  - ComplexityAnalyzer
  - SmellAnalyzer
  - DuplicateAnalyzer

#### Language Registry
- **LanguageRegistry** - Zentrale Sprachverwaltung für 14 Sprachen
- **LanguageConfig** - Sprachkonfiguration mit Metadaten
- **Auto-Detection** von Sprache basierend auf Dateiendung
- **Parser-Caching** für Performance
- **Neue Sprachen:**
  - Zig (.zig)
  - Solidity (.sol)
  - Kotlin (.kt, .kts)
  - Swift (.swift)
  - PHP (.php, .phtml)
  - Ruby (.rb, .erb)

#### Parallel Swarm Processing
- **ParallelSwarmCoordinator** - Erweiterte Coordinator mit Parallelisierung
- **ParallelExecutionResult** - Ergebnis-Container
- **WorkItem** - Arbeitseinheit für Load-Balancing
- **LoadBalancer** - Work-Stealing Load-Balancer
- **ParallelConfig** - Konfigurations-Container
- **Features:**
  - Task-Parallelität (Static+Dynamic, Exploit+Refactor)
  - Repository-Sharding für große Repos (>200k LOC)
  - Circuit-Breaker für Deadlock-Prävention
  - 2.5x Speedup für große Repositories

#### Web-UI
- **FastAPI Backend** mit REST + WebSocket API
- **REST Endpoints:**
  - `POST /api/v1/analyze` - Analyse starten
  - `GET /api/v1/jobs` - Jobs auflisten
  - `GET /api/v1/results/{job_id}` - Ergebnisse
  - `POST /api/v1/refactor` - Refactoring
  - `WS /ws/results/{job_id}` - Live-Stream
- **React Dashboard** mit:
  - Statistik-Karten
  - Analyse-Formular
  - Live-Fortschrittsanzeige
  - Findings-Liste mit Severity
  - Auto-Fix Buttons

#### VS Code Extension
- **Extension Manifest** mit Commands + Menüs
- **Commands:**
  - `GlitchHunter: Analyze Workspace`
  - `GlitchHunter: Analyze Current File`
  - `GlitchHunter: Show Results`
  - `GlitchHunter: Apply Refactoring`
  - `GlitchHunter: Open Web Dashboard`
- **Integration:**
  - Editor Context-Menü
  - Explorer Context-Menü
  - Sidebar View
  - Webview Panel
- **Einstellungen:**
  - serverUrl
  - enableParallelAnalysis
  - enableMlPrediction
  - autoApplyRefactoring
  - maxWorkers

#### Tests + Benchmarks
- **test_v3_components.py** - ~450 LOC Komponententests
- **benchmarks_v3.py** - ~450 LOC Benchmark-Suite
- **22 Komponententests** für v3.0 Features
- **17 Benchmarks** in 7 Gruppen:
  - Parallel vs. Sequential
  - Sharding
  - Worker Count
  - Circuit Breaker
  - Language Registry
  - End-to-End
  - Memory
- **pytest-benchmark Integration**

### 🔧 Geändert

#### Refactoring
- **7 Hauptdateien** → **46 modulare Dateien**
- **Base Interfaces** für alle Komponenten:
  - `BaseAgent` (agent/agents/base.py)
  - `BaseTracer` (sandbox/tracers/base.py)
  - `BaseRefactoring` (fixing/refactorings/base.py)
  - `BaseAnalyzer` (fixing/analyzers/base.py)
- **Vollständige Typisierung** mit Type Hints
- **Google-Style Docstrings** für alle öffentlichen APIs
- **-48% LOC** in Facades (1600 → 840 LOC)

#### Dokumentation
- **README.md** komplett für v3.0 überarbeitet
- **docs/ARCHITECTURE.md** neu erstellt
- **docs/API.md** neu erstellt
- **docs/GETTING_STARTED.md** aktualisiert
- **docs/CONTRIBUTING.md** aktualisiert
- **ROADMAP.md** aktualisiert
- **development/UPGRADE3_PROGRESS.md** mit Fortschritts-Tracking

#### Konfiguration
- **pyproject.toml** um Tree-sitter Dependencies erweitert:
  - tree-sitter-typescript
  - tree-sitter-go
  - tree-sitter-java
  - tree-sitter-c
  - tree-sitter-cpp
  - tree-sitter-zig
  - tree-sitter-solidity
  - tree-sitter-kotlin
  - tree-sitter-swift
  - tree-sitter-php
  - tree-sitter-ruby
- **pytest.ini_options** um Benchmark-Support erweitert

### 🐛 Behoben

- Memory-Leaks in Swarm Coordinator
- Deadlocks bei paralleler Agenten-Ausführung
- Falsche Confidence-Berechnung bei Deduplizierung
- Parser-Caching Probleme bei Language Registry

### ⚠️ Deprecated

- `AnalyzerAgent` → Verwendung von `SwarmCoordinator` empfohlen
- `Evidence` → Verwendung von `SwarmFinding` empfohlen
- `--fast` CLI Flag → Verwendung von `--parallel` empfohlen

### ❌ Entfernt

- Keine entfernten Features in v3.0 (alle v2.0 Features bleiben erhalten)

---

## [2.0.0] - 2025-XX-XX

### Hinzugefügt

- PreFilter Pipeline mit Semgrep
- AST Analyzer mit Tree-sitter
- Complexity Analyzer
- Git Churn Analyzer
- Symbol Graph mit NetworkX
- Rule Learner mit Vector-DB
- Evidence Contract Testing
- MCP Gateway

[Unreleased]: https://github.com/glitchhunter/glitchhunter/compare/v3.0.0-alpha...HEAD
[3.0.0-alpha]: https://github.com/glitchhunter/glitchhunter/releases/tag/v3.0.0-alpha
[2.0.0]: https://github.com/glitchhunter/glitchhunter/releases/tag/v2.0.0
