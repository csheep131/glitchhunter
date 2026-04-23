# GlitchHunter v3.0 - API-Referenz

**Version:** 3.0.0-dev  
**Letztes Update:** 20. April 2026  
**Status:** Implementiert ✅

## Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Swarm Coordinator](#swarm-coordinator)
3. [Agenten](#agenten)
4. [ML Prediction](#ml-prediction)
5. [Auto-Refactoring](#auto-refactoring)
6. [Sandbox & Tracing](#sandbox--tracing)
7. [Types & Interfaces](#types--interfaces)
8. [CLI-API](#cli-api)

---

## Übersicht

GlitchHunter v3.0 bietet eine vollständige Python-API für alle Funktionen. Alle öffentlichen Klassen sind in den folgenden Modulen verfügbar:

```python
from glitchhunter import SwarmCoordinator, GlitchHunter
from glitchhunter.agent import BaseAgent, SwarmFinding
from glitchhunter.prediction import PredictionEngine, PredictionResult
from glitchhunter.fixing import AutoRefactor, RefactoringSuggestion
from glitchhunter.sandbox import DynamicTracer, BaseTracer
```

---

## Swarm Coordinator

### SwarmCoordinator

**Modul:** `agent.swarm_coordinator`  
**Beschreibung:** Haupt-Koordinator für den Multi-Agent Swarm

#### Constructor

```python
class SwarmCoordinator:
    def __init__(
        self,
        config: Optional[Config] = None
    )
```

**Parameter:**
- `config` (Optional[Config]): Optionale Konfiguration. Wenn nicht angegeben, wird `Config.load()` verwendet.

**Beispiel:**
```python
from glitchhunter import SwarmCoordinator

coordinator = SwarmCoordinator()
```

#### Methoden

##### run_swarm

Führt eine komplette Swarm-Analyse durch.

```python
async def run_swarm(
    repo_path: str | Path,
    agents: Optional[List[str]] = None,
    enable_ml: bool = True,
    enable_refactoring: bool = True,
) -> SwarmState
```

**Parameter:**
- `repo_path`: Pfad zum Repository
- `agents`: Optionale Liste von Agenten-Namen (default: alle)
- `enable_ml`: ML-Prediction aktivieren (default: True)
- `enable_refactoring`: Auto-Refactoring aktivieren (default: True)

**Returns:** `SwarmState` mit allen Findings

**Beispiel:**
```python
from pathlib import Path

coordinator = SwarmCoordinator()
results = await coordinator.run_swarm(
    Path("/path/to/repo"),
    agents=["static", "dynamic"],
    enable_ml=True,
)

print(f"Static Findings: {len(results.static_findings)}")
print(f"Dynamic Findings: {len(results.dynamic_findings)}")
```

##### get_all_findings

Extrahiert alle Findings aus dem Swarm-State.

```python
def get_all_findings(
    self,
    state: SwarmState,
    min_confidence: float = 0.0,
    severity: Optional[str] = None,
) -> List[SwarmFinding]
```

**Parameter:**
- `state`: SwarmState nach `run_swarm()`
- `min_confidence`: Minimum Confidence-Filter (0-1)
- `severity`: Optionaler Severity-Filter

**Returns:** Liste von SwarmFinding

**Beispiel:**
```python
all_findings = coordinator.get_all_findings(
    results,
    min_confidence=0.7,
    severity="high",
)
```

---

## Agenten

### BaseAgent

**Modul:** `agent.agents.base`  
**Beschreibung:** Abstrakte Basisklasse für alle Agenten

```python
class BaseAgent(ABC):
    def __init__(self, name: str)
    
    @abstractmethod
    async def analyze(self, repo_path: Path, **kwargs) -> Dict[str, Any]:
        """Führt Hauptanalyse durch."""
        pass
    
    @abstractmethod
    async def get_findings(self) -> List[Dict[str, Any]]:
        """Extrahiert Findings."""
        pass
    
    async def cleanup(self) -> None:
        """Räumt Ressourcen auf."""
    
    def get_metadata(self) -> Dict[str, Any]:
        """Returns Metadaten."""
```

### StaticScannerAgent

**Modul:** `agent.agents.static_scanner`  
**Beschreibung:** Statische Code-Analyse mit Tree-sitter

```python
class StaticScannerAgent(BaseAgent):
    async def analyze(self, repo_path: Path, **kwargs) -> Dict[str, Any]:
        """
        Führt statische Analyse durch.
        
        Features:
        - Tree-sitter AST-Parsing
        - Complexity-Metriken
        - Code-Smell-Detection
        """
```

**Beispiel:**
```python
from agent.agents.static_scanner import StaticScannerAgent

scanner = StaticScannerAgent()
results = await scanner.analyze(Path("/path/to/repo"))
findings = await scanner.get_findings()
```

### DynamicTracerAgent

**Modul:** `agent.agents.dynamic_tracer`  
**Beschreibung:** Dynamische Analyse mit Runtime-Tracing

```python
class DynamicTracerAgent(BaseAgent):
    async def analyze(self, repo_path: Path, **kwargs) -> Dict[str, Any]:
        """
        Führt dynamische Analyse durch.
        
        Features:
        - Coverage-guided Fuzzing
        - eBPF/ptrace Tracing
        - Runtime Error Detection
        """
```

**Beispiel:**
```python
from agent.agents.dynamic_tracer import DynamicTracerAgent

tracer = DynamicTracerAgent()
results = await tracer.analyze(
    Path("/path/to/repo"),
    enable_ebpf=True,
    timeout=60,
)
```

### ExploitGeneratorAgent

**Modul:** `agent.agents.exploit_generator`  
**Beschreibung:** Generiert PoC-Testcases für Findings

```python
class ExploitGeneratorAgent(BaseAgent):
    async def analyze(self, repo_path: Path, **kwargs) -> Dict[str, Any]:
        """
        Generiert Exploits für Findings.
        
        Input: Findings mit 'exploit_ready=True'
        Output: PoC-Testcases
        """
```

### RefactoringBotAgent

**Modul:** `agent.agents.refactoring_bot`  
**Beschreibung:** Generiert Auto-Refactoring Vorschläge

```python
class RefactoringBotAgent(BaseAgent):
    async def analyze(self, repo_path: Path, **kwargs) -> Dict[str, Any]:
        """
        Generiert Refactoring-Vorschläge.
        
        Features:
        - Extract Method
        - Remove Duplicates
        - Replace Magic Numbers
        - Simplify Conditions
        """
```

### ReportAggregatorAgent

**Modul:** `agent.agents.report_aggregator`  
**Beschreibung:** Konsolidiert alle Findings

```python
class ReportAggregatorAgent(BaseAgent):
    async def analyze(self, repo_path: Path, **kwargs) -> Dict[str, Any]:
        """
        Konsolidiert alle Findings.
        
        Features:
        - Deduplizierung
        - Confidence-Boosting
        - Evidence-Merging
        """
```

---

## ML Prediction

### PredictionEngine

**Modul:** `prediction.engine`  
**Beschreibung:** Engine für ML-basierte Bug-Vorhersage

#### Constructor

```python
class PredictionEngine:
    def __init__(
        self,
        model_path: Optional[Path] = None,
        use_cpu: bool = True,
        min_probability: float = 0.4,
    )
```

**Parameter:**
- `model_path`: Pfad zum ONNX-Modell
- `use_cpu`: Nur CPU verwenden (default: True)
- `min_probability`: Minimum Bug-Wahrscheinlichkeit (default: 0.4)

#### Methoden

##### predict

Führt Bug-Vorhersage für Repository durch.

```python
async def predict(
    self,
    repo_path: Path,
    symbol_graph: Optional[nx.DiGraph] = None,
    **kwargs,
) -> List[PredictionFinding]
```

**Parameter:**
- `repo_path`: Pfad zum Repository
- `symbol_graph`: Optionaler Symbol-Graph

**Returns:** Liste von PredictionFinding

**Beispiel:**
```python
from glitchhunter.prediction import PredictionEngine
import networkx as nx

engine = PredictionEngine(min_probability=0.5)

# Mit Symbol-Graph
symbol_graph = nx.read_graphml("symbol_graph.graphml")
predictions = await engine.predict(
    Path("/path/to/repo"),
    symbol_graph=symbol_graph,
)

for pred in predictions:
    print(f"{pred.file_path}:{pred.line_start}")
    print(f"  Risk: {pred.risk_level}")
    print(f"  Probability: {pred.bug_probability:.0%}")
```

##### predict_batch

Batch-Prediction für mehrere Dateien.

```python
async def predict_batch(
    self,
    file_paths: List[Path],
    batch_size: int = 32,
) -> List[PredictionResult]
```

**Beispiel:**
```python
files = list(Path("/path/to/repo").glob("**/*.py"))
results = await engine.predict_batch(files, batch_size=64)
```

### GlitchPredictionModel

**Modul:** `prediction.model`  
**Beschreibung:** ONNX-Modell für Bug-Vorhersage

```python
class GlitchPredictionModel:
    def __init__(
        self,
        model_path: Optional[Path] = None,
        use_cpu: bool = True,
    )
    
    def predict(
        self,
        features: np.ndarray,
    ) -> List[PredictionResult]:
        """
        Führt Prediction durch.
        
        Parameter:
        - features: Feature-Matrix (n_samples, 32)
        
        Returns:
        - Liste von PredictionResult
        """
```

### FeatureExtractor

**Modul:** `prediction.features.extractor`  
**Beschreibung:** Extrahiert 32-dimensionale Features

```python
class FeatureExtractor:
    def extract(
        self,
        symbol: str,
        graph: nx.DiGraph,
        code: str,
    ) -> FeatureVector:
        """Extrahiert Features für ein Symbol."""
    
    def batch_extract(
        self,
        graph: nx.DiGraph,
    ) -> List[FeatureVector]:
        """Extrahiert Features für alle Symbole."""
```

**Feature-Kategorien:**

| Kategorie | Features | Extraktor |
|-----------|----------|-----------|
| Graph | 8 | `GraphFeatureExtractor` |
| Complexity | 8 | `ComplexityFeatureExtractor` |
| Structural | 8 | `StructuralFeatureExtractor` |
| History | 8 | `HistoryFeatureExtractor` |

---

## Auto-Refactoring

### AutoRefactor

**Modul:** `fixing.auto_refactor`  
**Beschreibung:** Engine für automatisches Refactoring

#### Constructor

```python
class AutoRefactor:
    def __init__(
        self,
        use_git: bool = True,
        run_tests: bool = True,
        backup: bool = True,
    )
```

**Parameter:**
- `use_git`: Git für Rollback verwenden (default: True)
- `run_tests`: Tests nach Refactoring ausführen (default: True)
- `backup`: Backup-Dateien erstellen (default: True)

#### Methoden

##### analyze_file

Analysiert Datei auf Refactoring-Möglichkeiten.

```python
async def analyze_file(
    self,
    file_path: Path,
    complexity_data: Optional[Dict[str, Any]] = None,
) -> List[RefactoringSuggestion]
```

**Beispiel:**
```python
from glitchhunter.fixing import AutoRefactor

refactor = AutoRefactor()
suggestions = await refactor.analyze_file(Path("src/module.py"))

for suggestion in suggestions:
    print(f"{suggestion.title}: {suggestion.description}")
    print(f"  Confidence: {suggestion.confidence:.0%}")
```

##### refactor_file

Wendet Refactoring auf Datei an.

```python
async def refactor_file(
    self,
    file_path: Path,
    suggestion: RefactoringSuggestion,
) -> RefactoringResult
```

**Returns:** `RefactoringResult` mit Erfolgsstatus

**Beispiel:**
```python
if suggestions:
    result = await refactor.refactor_file(
        Path("src/module.py"),
        suggestions[0],
    )
    
    if result.success:
        print(f"Refactoring erfolgreich!")
        print(f"Git-Commit: {result.git_commit}")
        print(f"Diff:\n{result.diff}")
    else:
        print(f"Refactoring fehlgeschlagen: {result.error}")
```

##### rollback

Führt Rollback durch.

```python
def rollback(
    self,
    commit_hash: str,
) -> bool:
    """Rollback zu Git-Commit."""
```

### RefactoringSuggestion

**Modul:** `fixing.types`  
**Beschreibung:** Datenklasse für Refactoring-Vorschlag

```python
@dataclass
class RefactoringSuggestion:
    id: str
    file_path: str
    line_start: int
    line_end: int
    category: str  # complexity, duplication, smell, optimization
    title: str
    description: str
    original_code: str
    suggested_code: str
    confidence: float = 0.5
    risk_level: str = "medium"
    estimated_impact: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### RefactoringResult

**Modul:** `fixing.types`  
**Beschreibung:** Datenklasse für Refactoring-Ergebnis

```python
@dataclass
class RefactoringResult:
    suggestion: RefactoringSuggestion
    success: bool
    applied_code: Optional[str] = None
    git_commit: Optional[str] = None
    diff: Optional[str] = None
    test_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### Analyzer

#### ComplexityAnalyzer

**Modul:** `fixing.analyzers.complexity_analyzer`

```python
class ComplexityAnalyzer(BaseAnalyzer):
    async def analyze(self, code: str) -> ComplexityAnalysisResult:
        """
        Analysiert Code-Complexity.
        
        Metriken:
        - Cyclomatic Complexity
        - Cognitive Complexity
        - LOC
        - Halstead Metrics
        """
```

#### SmellAnalyzer

**Modul:** `fixing.analyzers.smell_analyzer`

```python
class SmellAnalyzer(BaseAnalyzer):
    async def analyze(self, code: str) -> SmellAnalysisResult:
        """
        Erkennt Code-Smells.
        
        Smells:
        - Magic Numbers
        - Long Methods
        - God Classes
        - Feature Envy
        """
```

#### DuplicateAnalyzer

**Modul:** `fixing.analyzers.duplicate_analyzer`

```python
class DuplicateAnalyzer(BaseAnalyzer):
    async def analyze(self, code: str) -> DuplicateAnalysisResult:
        """
        Erkennt Code-Duplikate.
        
        Features:
        - Token-basierter Vergleich
        - AST-basierter Vergleich
        - Fuzzy Matching
        """
```

---

## Sandbox & Tracing

### DynamicTracer

**Modul:** `sandbox.dynamic_tracer`  
**Beschreibung:** Facade für Dynamic Tracing

```python
class DynamicTracer:
    async def trace(
        self,
        target: str,
        timeout: int = 60,
        enable_ebpf: bool = True,
    ) -> TraceResult:
        """
        Führt Runtime-Tracing durch.
        
        Parameter:
        - target: Ziel-Datei oder Funktion
        - timeout: Timeout in Sekunden
        - enable_ebpf: eBPF aktivieren (Linux)
        """
```

### BaseTracer

**Modul:** `sandbox.tracers.base`  
**Beschreibung:** Interface für alle Tracer

```python
class BaseTracer(ABC):
    @abstractmethod
    async def trace(self, target: str) -> TraceResult:
        pass
    
    @abstractmethod
    async def get_coverage(self) -> CoverageResult:
        pass
    
    async def cleanup(self) -> None:
        """Räumt Ressourcen auf."""
```

### PythonTracer

**Modul:** `sandbox.tracers.python_tracer`  
**Beschreibung:** Tracer für Python mit coverage.py

```python
class PythonTracer(BaseTracer):
    async def trace(self, target: str) -> TraceResult:
        """
        Traced Python-Code.
        
        Features:
        - coverage.py Integration
        - Line Coverage
        - Branch Coverage
        """
```

### EbpfTracer

**Modul:** `sandbox.tracers.ebpf_tracer`  
**Beschreibung:** eBPF-Tracer für Linux (BCC)

```python
class EbpfTracer(BaseTracer):
    async def trace(self, target: str) -> TraceResult:
        """
        Traced mit eBPF.
        
        Features:
        - System Calls
        - Function Entry/Exit
        - Memory Access
        """
```

**Hinweis:** Nur auf Linux mit BCC verfügbar.

---

## Types & Interfaces

### SwarmFinding

**Modul:** `agent.state`  
**Beschreibung:** Einheitliches Finding-Format

```python
@dataclass
class SwarmFinding:
    id: str
    agent: str  # static, dynamic, exploit, refactor, report
    file_path: str
    line_start: int
    line_end: int
    severity: str  # critical, high, medium, low, info
    category: str  # security, performance, correctness, style
    title: str
    description: str
    evidence: List[Evidence]
    confidence: float  # 0-1
    exploit_ready: bool
    fix_suggestion: Optional[str]
    metadata: Dict[str, Any]
```

### SwarmState

**Modul:** `agent.state`  
**Beschreibung:** Geteilter State für Swarm

```python
@dataclass
class SwarmState:
    repo_path: Optional[str]
    current_phase: str
    static_findings: List[SwarmFinding]
    dynamic_findings: List[SwarmFinding]
    exploit_findings: List[SwarmFinding]
    refactor_findings: List[SwarmFinding]
    aggregated_findings: List[SwarmFinding]
    prediction_results: List[PredictionResult]
    errors: List[str]
    metadata: Dict[str, Any]
```

### PredictionResult

**Modul:** `prediction.types`

```python
@dataclass
class PredictionResult:
    symbol_name: str
    file_path: str
    bug_probability: float  # 0-1
    severity_score: float  # 0-1
    risk_level: str  # low, medium, high, critical
    confidence: float  # 0-1
    feature_importance: Optional[Dict[str, float]]
```

### Evidence

**Modul:** `agent.evidence_types`  
**Beschreibung:** Evidence für Finding-Validierung

```python
@dataclass
class Evidence:
    type: str  # static, dynamic, ml, history
    source: str  # Agent oder Tool
    data: Dict[str, Any]
    confidence: float  # 0-1
    timestamp: datetime
```

---

## CLI-API

### Command-Line Interface

GlitchHunter bietet ein CLI für alle Hauptfunktionen:

```bash
# Hilfe
glitchhunter --help

# Analyse
glitchhunter analyze <pfad> [Optionen]

# Refactoring
glitchhunter refactor <pfad> [Optionen]

# Report
glitchhunter report <pfad> [Optionen]

# Check
glitchhunter check
```

### CLI als Python-Modul

```python
from glitchhunter.cli import main

# CLI programmatisch aufrufen
if __name__ == "__main__":
    main(["analyze", "/path/to/repo", "--swarm"])
```

---

## Fehlerbehandlung

### Exceptions

GlitchHunter definiert folgende Exceptions:

```python
class GlitchHunterError(Exception):
    """Base-Exception für alle GlitchHunter-Fehler."""

class AnalysisError(GlitchHunterError):
    """Fehler während der Analyse."""

class PredictionError(GlitchHunterError):
    """Fehler während ML-Prediction."""

class RefactoringError(GlitchHunterError):
    """Fehler während Refactoring."""

class SandboxError(GlitchHunterError):
    """Fehler in der Sandbox."""
```

### Error Handling Beispiel

```python
from glitchhunter import SwarmCoordinator
from glitchhunter.exceptions import AnalysisError, PredictionError

coordinator = SwarmCoordinator()

try:
    results = await coordinator.run_swarm(Path("/path/to/repo"))
except AnalysisError as e:
    print(f"Analyse fehlgeschlagen: {e}")
except PredictionError as e:
    print(f"Prediction fehlgeschlagen: {e}")
except Exception as e:
    print(f"Unbekannter Fehler: {e}")
```

---

## Best Practices

### 1. Async/Await korrekt verwenden

Alle Hauptmethoden sind async:

```python
# ✅ Korrekt
results = await coordinator.run_swarm(path)

# ❌ Falsch (blockiert)
results = coordinator.run_swarm(path)
```

### 2. Ressourcen aufräumen

```python
async with SwarmCoordinator() as coordinator:
    results = await coordinator.run_swarm(path)
# Automatische cleanup()
```

### 3. Confidence-Filter verwenden

```python
# Nur hochwertige Findings
findings = [f for f in results.static_findings if f.confidence >= 0.7]
```

### 4. Git-Rollback vorbereiten

```python
# Vor Refactoring
refactor = AutoRefactor(use_git=True, backup=True)

# Bei Fehler
if not result.success:
    refactor.rollback(checkpoint_commit)
```

---

## Verwandte Dokumente

- **[Getting Started](GETTING_STARTED.md)** - Installationsanleitung
- **[Architektur](ARCHITECTURE.md)** - System-Design
- **[Contributing](CONTRIBUTING.md)** - Entwicklungsrichtlinien
