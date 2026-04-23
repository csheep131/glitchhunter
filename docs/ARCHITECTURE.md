# GlitchHunter v3.0 Architektur

**Version:** 3.0.0-dev  
**Letztes Update:** 20. April 2026  
**Status:** Implementiert (Phase 1 & 2 ✅)

## Überblick

GlitchHunter v3.0 ist eine **modulare, KI-gestützte Code-Analyse-Plattform** die auf einem **Multi-Agent Swarm** basiert. Die Architektur folgt dem **Single-Responsibility-Prinzip** mit strenger Trennung der Belange.

## Systemübersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                     GlitchHunter v3.0                            │
│                   Multi-Agent Swarm System                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Swarm Coordinator                             │
│              (LangGraph StateGraph Orchestrator)                 │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ Static Scanner│   │ Dynamic Tracer  │   │  ML Prediction  │
│   (Tree-      │   │  (Coverage-     │   │   (32-dim       │
│   sitter)     │   │   guided)       │   │   Features)     │
└───────────────┘   └─────────────────┘   └─────────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │    Exploit      │
                    │   Generator     │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Refactoring    │
                    │      Bot        │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │    Report       │
                    │  Aggregator     │
                    └─────────────────┘
```

## Kernkomponenten

### 1. Swarm Coordinator

**Datei:** `src/agent/swarm_coordinator.py`  
**LOC:** ~270  
**Verantwortlichkeit:** Orchestrierung aller Agenten via LangGraph StateGraph

```python
class SwarmCoordinator:
    """
    Haupt-Koordinator für den Multi-Agent Swarm.
    
    Features:
    - LangGraph StateGraph mit 6 Nodes
    - Evidence-basierte Entscheidungsfindung
    - Confidence-Boosting bei multiplen Agenten
    """
```

**State Graph:**

```
static_scan → dynamic_scan → generate_exploits → 
generate_refactors → aggregate_reports → add_predictions → END
```

**Agenten:**

| Agent | Datei | LOC | Aufgabe |
|-------|-------|-----|---------|
| StaticScanner | `agents/static_scanner.py` | ~110 | Tree-sitter + Complexity |
| DynamicTracer | `agents/dynamic_tracer.py` | ~120 | Coverage-Fuzzing + eBPF |
| ExploitGenerator | `agents/exploit_generator.py` | ~100 | PoC-Testcase-Generierung |
| RefactoringBot | `agents/refactoring_bot.py` | ~100 | Auto-Refactoring Vorschläge |
| ReportAggregator | `agents/report_aggregator.py` | ~130 | Konsolidierung |

### 2. Sandbox & Dynamic Analysis

**Paket:** `src/sandbox/`  
**Dateien:** 5  
**Gesamt-LOC:** ~450

**Komponenten:**

```
sandbox/
├── base.py              # BaseSandbox (Interface)
├── dynamic_tracer.py    # DynamicTracer (Facade)
└── tracers/
    ├── base.py          # BaseTracer (Interface)
    ├── python_tracer.py # coverage.py Integration
    ├── js_tracer.py     # Istanbul/nyc Integration
    └── ebpf_tracer.py   # BCC/eBPF für Linux
```

**Features:**

- **Docker-Isolation** für sichere Ausführung
- **Coverage-guided Fuzzing** (Python: coverage.py)
- **eBPF/ptrace Tracing** für Linux (BCC)
- **Runtime Error Detection**

### 3. ML Bug Prediction

**Paket:** `src/prediction/`  
**Dateien:** 9  
**Gesamt-LOC:** ~1200

**Komponenten:**

```
prediction/
├── types.py                  # PredictionResult, PredictionFinding
├── engine.py                 # PredictionEngine (Facade)
├── model.py                  # GlitchPredictionModel (ONNX)
└── features/
    ├── extractor.py          # FeatureExtractor (32-dim)
    ├── graph_features.py     # Degree, Centrality, PageRank
    ├── complexity_features.py# Cyclomatic, Cognitive, LOC
    └── history_features.py   # Churn, Bug-Rate, Contributors
```

**Feature-Kategorien:**

| Kategorie | Features | Beispiele |
|-----------|----------|-----------|
| Graph | 8 | Degree, Centrality, PageRank, Betweenness |
| Complexity | 8 | Cyclomatic, Cognitive, LOC, Halstead |
| Structural | 8 | Clustering, Triangles, Community |
| History | 8 | Churn, Bug-Rate, Contributors, Age |

**ML-Modell:**

- **Format:** ONNX (CPU/CUDA)
- **Output:** Bug-Wahrscheinlichkeit (0-1), Severity (0-1)
- **Risk-Levels:** low, medium, high, critical
- **Feature-Importance:** Für Interpretierbarkeit

### 4. Auto-Refactoring

**Paket:** `src/fixing/`  
**Dateien:** 15  
**Gesamt-LOC:** ~2000

**Komponenten:**

```
fixing/
├── types.py                # RefactoringSuggestion, RefactoringResult
├── auto_refactor.py        # AutoRefactor (Facade, ~350 LOC)
├── refactorings/
│   ├── base.py             # BaseRefactoring (Interface)
│   ├── extract_method.py   # Extract Method Refactoring
│   ├── remove_duplicate.py # Remove Duplicate Code
│   ├── replace_magic_number.py
│   └── simplify_condition.py
└── analyzers/
    ├── base.py             # BaseAnalyzer (Interface)
    ├── complexity_analyzer.py
    ├── smell_analyzer.py
    └── duplicate_analyzer.py
```

**Refactoring-Typen:**

1. **Extract Method** - Bei hoher cyclomatischer Komplexität
2. **Remove Duplicate Code** - Bei Code-Duplikaten
3. **Replace Magic Number** - Bei harten Kodierungen
4. **Simplify Condition** - Bei komplexen Bedingungen
5. **Extract Variable** - Bei langen Ausdrücken

**Safety-Features:**

```
1. Git-Commit vor Refactoring → Rollback möglich
2. Backup-Dateien → Datenverlust-Schutz
3. Syntax-Validierung → Compiler-Check
4. Test-Ausführung → Regressionstests
5. Automatisches Rollback → Bei Fehlern
```

## Datenfluss

### Analyse-Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│                     Analyse-Pipeline                          │
└──────────────────────────────────────────────────────────────┘

1. Repository Input
         │
         ▼
2. Static Scanner (Tree-sitter AST + Complexity)
         │
         ▼
3. Dynamic Tracer (Coverage-Fuzzing + Runtime)
         │
         ▼
4. Exploit Generator (PoC-Testcases)
         │
         ▼
5. Refactoring Bot (Code-Improvement Vorschläge)
         │
         ▼
6. ML Prediction Engine (32-dim Features → Bug-Vorhersage)
         │
         ▼
7. Report Aggregator (Konsolidierung + Deduplizierung)
         │
         ▼
8. Final Report (Markdown/JSON + Confidence Scores)
```

### Evidence-Tracking

Jedes Finding enthält Evidence-Metadaten:

```python
@dataclass
class SwarmFinding:
    id: str
    file_path: str
    severity: str
    category: str
    title: str
    description: str
    evidence: Dict[str, Any]  # Evidence-Daten
    confidence: float         # 0-1 Confidence-Score
    source_agent: str         # Welcher Agent hat es gefunden
```

## Modulare Architektur

### Verzeichnisstruktur

```
src/
├── agent/                    # Swarm Coordinator + Agenten
│   ├── state.py              # SwarmState, SwarmFinding
│   ├── swarm_coordinator.py  # Haupt-Koordinator (~270 LOC)
│   └── agents/
│       ├── base.py           # BaseAgent Interface (~70 LOC)
│       ├── static_scanner.py (~110 LOC)
│       ├── dynamic_tracer.py (~120 LOC)
│       ├── exploit_generator.py (~100 LOC)
│       ├── refactoring_bot.py (~100 LOC)
│       └── report_aggregator.py (~130 LOC)
│
├── sandbox/                  # Sandbox-Isolation + Tracer
│   ├── base.py               # BaseSandbox (~140 LOC)
│   ├── dynamic_tracer.py     # Facade (~220 LOC)
│   └── tracers/
│       ├── base.py           # BaseTracer (~90 LOC)
│       ├── python_tracer.py  (~150 LOC)
│       ├── js_tracer.py      (~180 LOC)
│       └── ebpf_tracer.py    (~180 LOC)
│
├── prediction/               # ML Bug Prediction
│   ├── types.py              # ~100 LOC
│   ├── engine.py             # ~150 LOC
│   ├── model.py              # ~220 LOC
│   └── features/
│       ├── extractor.py      # ~250 LOC
│       ├── graph_features.py # ~130 LOC
│       ├── complexity_features.py # ~90 LOC
│       └── history_features.py    # ~90 LOC
│
├── fixing/                   # Auto-Refactoring
│   ├── types.py              # ~100 LOC
│   ├── auto_refactor.py      # ~350 LOC
│   ├── refactorings/
│   │   ├── base.py           # ~80 LOC
│   │   ├── extract_method.py # ~100 LOC
│   │   └── ...
│   └── analyzers/
│       ├── base.py           # ~90 LOC
│       ├── complexity_analyzer.py # ~180 LOC
│       └── ...
│
├── prefilter/                # Pre-Filter Pipeline
├── mapper/                   # Symbol-Graph + Mapping
└── core/                     # Konfiguration + Basis-Klassen
```

### Design-Prinzipien

| Prinzip | Umsetzung |
|---------|-----------|
| **Single Responsibility** | Jede Klasse < 200 LOC, jede Funktion < 50 LOC |
| **Modulare Struktur** | Pro Agent/Komponente eigene Datei |
| **Dependency Injection** | Lose Kopplung über Base Interfaces |
| **Type Hints** | Vollständige Typisierung überall |
| **Docstrings** | Google-Style für alle öffentlichen APIs |
| **Keine Logik-Änderung** | Nur Struktur verbessert (Refactoring) |

### Base Interfaces

Alle Komponenten implementieren abstrakte Base-Interfaces:

```python
# agent/agents/base.py
class BaseAgent(ABC):
    @abstractmethod
    async def analyze(self, repo_path: Path, **kwargs) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def get_findings(self) -> List[Dict[str, Any]]:
        pass

# sandbox/tracers/base.py
class BaseTracer(ABC):
    @abstractmethod
    async def trace(self, target: str) -> TraceResult:
        pass

# fixing/refactorings/base.py
class BaseRefactoring(ABC):
    @abstractmethod
    async def refactor(self, code: str) -> RefactoringResult:
        pass

# fixing/analyzers/base.py
class BaseAnalyzer(ABC):
    @abstractmethod
    async def analyze(self, code: str) -> AnalysisResult:
        pass
```

## Integrationen

### LangGraph StateGraph

Swarm Coordinator verwendet LangGraph für Workflow-Orchestrierung:

```python
from langgraph.graph import StateGraph, END

def _build_graph(self) -> StateGraph:
    workflow = StateGraph(SwarmStateGraphInput)
    
    workflow.add_node("static_scan", self._run_static_scan)
    workflow.add_node("dynamic_scan", self._run_dynamic_scan)
    workflow.add_node("generate_exploits", self._run_exploit_generation)
    workflow.add_node("generate_refactors", self._run_refactor_generation)
    workflow.add_node("aggregate_reports", self._run_aggregation)
    workflow.add_node("add_predictions", self._add_predictions)
    
    workflow.set_entry_point("static_scan")
    workflow.add_edge("static_scan", "dynamic_scan")
    workflow.add_edge("dynamic_scan", "generate_exploits")
    workflow.add_edge("generate_exploits", "generate_refactors")
    workflow.add_edge("generate_refactors", "aggregate_reports")
    workflow.add_edge("aggregate_reports", "add_predictions")
    workflow.add_edge("add_predictions", END)
    
    return workflow.compile()
```

### ONNX Runtime

ML-Modell mit ONNX für CPU/CUDA-Support:

```python
import onnxruntime as ort

class GlitchPredictionModel:
    def __init__(self, model_path: str):
        # CPU oder CUDA automatisch erkennen
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        self.session = ort.InferenceSession(model_path, providers=providers)
    
    def predict(self, features: np.ndarray) -> PredictionResult:
        outputs = self.session.run(None, {'input': features})
        # ... Verarbeitung
```

### Git-Rollback

Auto-Refactoring mit Git-basiertem Rollback:

```python
import git

class AutoRefactor:
    def __init__(self, repo_path: Path):
        self.repo = git.Repo(repo_path)
    
    def _create_checkpoint(self) -> str:
        """Erstellt Git-Commit für Rollback."""
        commit = self.repo.index.commit("Pre-refactoring checkpoint")
        return commit.hexsha
    
    def _rollback(self, commit_hash: str):
        """Rollback zuCheckpoint."""
        self.repo.git.reset('--hard', commit_hash)
```

## Konfiguration

### config.yaml

```yaml
# Swarm Configuration
agent:
  max_iterations: 5
  timeout_per_state: 300
  enable_swarm: true

# Sandbox Configuration
sandbox:
  use_docker: true
  timeout: 60
  enable_ebpf: true

# Prediction Configuration
prediction:
  min_probability: 0.4
  model_path: "models/glitch_model.onnx"
  use_cuda: true

# Refactoring Configuration
refactoring:
  auto_apply: false
  min_confidence: 0.7
  create_backup: true
```

## Entscheidungsprotokolle

### Warum LangGraph?

**Entscheidung:** LangGraph für State-Orchestrierung  
**Alternativen:** Airflow, Prefect, Custom State Machine  
**Begründung:**
- Native LLM-Integration
- Asynchrone Ausführung
- Einfache State-Persistence
- Gute Testbarkeit

### Warum ONNX?

**Entscheidung:** ONNX für ML-Modell  
**Alternativen:** PyTorch, TensorFlow, Scikit-learn  
**Begründung:**
- CPU/CUDA automatisch
- Platform-unabhängig
- Performance-optimiert
- Keine PyTorch-Abhängigkeit nötig

### Warum modulare Architektur?

**Entscheidung:** 37 kleine Dateien statt 7 Monolithen  
**Alternativen:** Monolithische Architektur  
**Begründung:**
- Bessere Testbarkeit (isolierte Komponenten)
- Einfachere Wartung (fokussierte Module)
- Bessere Lesbarkeit (klare Verantwortlichkeiten)
- Einfachere Erweiterung (neue Agenten leicht hinzufügbar)

## Performance-Charakteristika

### Skalierung

| Repository-Größe | Analyse-Zeit | Speicher |
|------------------|--------------|----------|
| < 10k LOC | ~20s | ~500MB |
| 10k-50k LOC | ~1-2min | ~1GB |
| 50k-100k LOC | ~5min | ~2GB |
| > 100k LOC | ~10min | ~4GB |

### Parallelisierung

- **Agenten:** Sequentiell (LangGraph)
- **Feature-Extraction:** Parallel pro Datei
- **ML-Prediction:** Batch-Verarbeitung
- **Refactoring:** Sequentiell (Git-Lock)

## Sicherheit

### Sandbox-Isolation

1. **Docker-Container** für Code-Ausführung
2. **Netzwerk-disabled** für Security
3. **Resource-Limits** (CPU, RAM, Timeouts)
4. **File-System-Isolation** (Read-only außer Temp)

### Git-Rollback

1. **Pre-Commit** vor jedem Refactoring
2. **Backup-Dateien** zusätzlich zu Git
3. **Syntax-Check** vor Anwendung
4. **Test-Ausführung** nach Refactoring
5. **Auto-Rollback** bei Fehlern

## Tests

### Test-Strategie

```
tests/
├── test_agent/
│   ├── test_swarm_coordinator.py
│   ├── test_static_scanner.py
│   └── ...
├── test_sandbox/
│   ├── test_base.py
│   ├── test_dynamic_tracer.py
│   └── ...
├── test_prediction/
│   ├── test_engine.py
│   ├── test_model.py
│   └── ...
└── test_fixing/
    ├── test_auto_refactor.py
    ├── test_refactorings.py
    └── ...
```

### Test-Status

| Komponente | Tests | Coverage | Status |
|------------|-------|----------|--------|
| Swarm Coordinator | ⏳ Ausstehend | - | 🟡 Pending |
| Sandbox | ⏳ Ausstehend | - | 🟡 Pending |
| Prediction | ⏳ Ausstehend | - | 🟡 Pending |
| Auto-Refactoring | ⏳ Ausstehend | - | 🟡 Pending |

## Zukünftige Erweiterungen

### Phase 3: Sprachen & Skalierung

- Tree-sitter auf 13 Sprachen erweitern (Zig, Solidity, Kotlin, Swift, PHP, Ruby)
- Parallele Swarm-Verarbeitung für große Repos

### Phase 4: User Experience

- Zero-Config One-Click Binary (PyInstaller)
- Web-UI (FastAPI + React)
- VS Code Extension

### Phase 5: Hybrid & Team Mode

- Cloud-Fallback für lokale Limits
- WebSocket-basierter Team-Mode

---

## Verwandte Dokumente

- **[API-Referenz](API.md)** - Detaillierte API-Dokumentation
- **[Getting Started](GETTING_STARTED.md)** - Installationsanleitung
- **[Contribution Guide](CONTRIBUTING.md)** - Entwicklungsrichtlinien
- **[Upgrade Guide](../development/UPGRADE3_PROGRESS.md)** - Implementierungsstatus
