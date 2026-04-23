# Migration Guide: GlitchHunter v2.0 → v3.0

**Stand:** 20. April 2026  
**Version:** 3.0.0-alpha

Dieser Guide hilft bei der Migration von GlitchHunter v2.0 auf v3.0.

---

## ⚠️ Breaking Changes

### 1. Agent API

**v2.0:**
```python
from agent.analyzer_agent import AnalyzerAgent

agent = AnalyzerAgent()
result = agent.analyze(repo_path)
```

**v3.0:**
```python
from agent.swarm_coordinator import SwarmCoordinator

coordinator = SwarmCoordinator()
result = await coordinator.run_swarm(repo_path)
```

**Oder parallel:**
```python
from agent.parallel_swarm import ParallelSwarmCoordinator

coordinator = ParallelSwarmCoordinator(max_workers=4)
result = await coordinator.run_swarm_parallel(repo_path)
```

### 2. Evidence → SwarmFinding

**v2.0:**
```python
from agent.evidence_types import Evidence

evidence = Evidence(
    evidence_type=EvidenceType.CALL_CHAIN,
    description="...",
)
```

**v3.0:**
```python
from agent.state import SwarmFinding

finding = SwarmFinding(
    id="unique_id",
    agent="static",
    file_path="test.py",
    line_start=10,
    line_end=20,
    severity="high",
    category="security",
    title="Security Issue",
    description="...",
    evidence=[...],
)
```

### 3. Import-Pfade für Agenten

**v2.0:**
```python
from agent.analyzer_agent import AnalyzerAgent
```

**v3.0:**
```python
from agent.agents.static_scanner import StaticScannerAgent
from agent.agents.dynamic_tracer import DynamicTracerAgent
from agent.agents.exploit_generator import ExploitGeneratorAgent
from agent.agents.refactoring_bot import RefactoringBotAgent
from agent.agents.report_aggregator import ReportAggregatorAgent
```

### 4. Konfiguration

**v2.0 config.yaml:**
```yaml
agent:
  max_iterations: 5
  timeout_per_state: 300
```

**v3.0 config.yaml:**
```yaml
agent:
  max_iterations: 5
  timeout_per_state: 300
  enable_swarm: true  # NEU

parallel:  # NEU
  max_workers: 4
  enable_sharding: true
  shard_size_threshold: 50000

sandbox:  # NEU
  use_docker: true
  timeout: 60
  enable_ebpf: true

prediction:  # NEU
  min_probability: 0.4
  model_path: "models/glitch_model.onnx"
```

### 5. CLI Commands

**v2.0:**
```bash
glitchhunter analyze /path/to/repo --fast
```

**v3.0:**
```bash
glitchhunter analyze /path/to/repo --parallel --max-workers 4
```

**Neue Commands:**
```bash
# Auto-Refactoring
glitchhunter refactor /path/to/repo --auto-apply

# Report generieren
glitchhunter report /path/to/repo --format markdown --output report.md

# Web-UI starten
glitchhunter web --port 8000
```

---

## 🆕 Neue Features nutzen

### Multi-Agent Swarm

```python
from agent.swarm_coordinator import SwarmCoordinator

coordinator = SwarmCoordinator()
result = await coordinator.run_swarm("/path/to/repo")

print(f"Found {len(result['findings'])} issues")
```

### Parallele Analyse

```python
from agent.parallel_swarm import ParallelSwarmCoordinator, ParallelConfig

config = ParallelConfig(
    max_workers=8,
    enable_sharding=True,
    agent_timeout=600,
)

coordinator = ParallelSwarmCoordinator(
    max_workers=config.max_workers,
    enable_sharding=config.enable_sharding,
)

result = await coordinator.run_swarm_parallel("/path/to/repo")

print(f"Speedup: {result.parallelization_factor}x")
```

### ML Prediction

```python
from prediction import PredictionEngine

engine = PredictionEngine(
    model_path="models/glitch_model.onnx",
    min_probability=0.4,
)

predictions = await engine.predict(
    repo_path=Path("/path/to/repo"),
    symbol_graph=symbol_graph,
)

for pred in predictions:
    print(f"{pred.file_path}: {pred.bug_probability:.1%} risk")
```

### Auto-Refactoring

```python
from fixing.auto_refactor import AutoRefactor

refactor = AutoRefactor(
    use_git=True,
    run_tests=True,
    backup=True,
)

# Analysieren
suggestions = await refactor.analyze_file(Path("test.py"))

# Anwenden
for suggestion in suggestions:
    result = await refactor.refactor_file(Path("test.py"), suggestion)
    if result.success:
        print(f"Refactoring applied: {result.git_commit}")
```

### Web-UI

```bash
# Server starten
python -m ui.web.backend.app

# Oder mit CLI
glitchhunter web --port 8000 --host 0.0.0.0
```

### VS Code Extension

```bash
# Extension installieren
cd ui/vscode
npm install
npm run compile

# In VS Code laden
# F1 → "Developer: Reload Window"
```

---

## 🔧 Code-Migration

### Schritt-für-Schritt

1. **Dependencies aktualisieren:**
   ```bash
   pip install -e ".[dev]"
   ```

2. **Imports anpassen:**
   ```python
   # Alt
   from agent.analyzer_agent import AnalyzerAgent
   
   # Neu
   from agent.swarm_coordinator import SwarmCoordinator
   ```

3. **Konfiguration erweitern:**
   - Neue Sektionen in config.yaml hinzufügen (siehe oben)

4. **Tests aktualisieren:**
   ```bash
   pytest tests/test_v3_components.py -v
   ```

5. **Benchmarks ausführen:**
   ```bash
   pytest tests/benchmarks_v3.py --benchmark-only
   ```

---

## ✅ Checkliste

- [ ] Dependencies aktualisiert (`pip install -e ".[dev]"`)
- [ ] Imports angepasst (AnalyzerAgent → SwarmCoordinator)
- [ ] config.yaml um neue Sektionen erweitert
- [ ] Tests ausgeführt (`pytest tests/`)
- [ ] Benchmarks ausgeführt (`pytest tests/benchmarks_v3.py`)
- [ ] Web-UI getestet (`python -m ui.web.backend.app`)
- [ ] VS Code Extension installiert (optional)

---

## 🆘 Troubleshooting

### ImportError: tree_sitter_*

**Problem:** Tree-sitter Bibliothek nicht installiert

**Lösung:**
```bash
pip install tree-sitter-python
pip install tree-sitter-javascript
pip install tree-sitter-typescript
# etc.
```

### ONNX Runtime Error

**Problem:** ONNX-Modell nicht gefunden

**Lösung:**
```bash
pip install onnxruntime
# Oder Dummy-Modell verwenden (default)
```

### eBPF nicht verfügbar

**Problem:** eBPF nur auf Linux

**Lösung:**
```yaml
# config.yaml
sandbox:
  use_docker: true  # Docker-Fallback aktivieren
```

### Circuit-Breaker öffnet

**Problem:** Agenten produzieren zu viele Fehler

**Lösung:**
```python
coordinator.reset_circuit_breakers()
```

---

## 📞 Support

Bei Problemen:

- **Issues:** https://github.com/glitchhunter/glitchhunter/issues
- **Dokumentation:** docs/
- **Discussions:** https://github.com/glitchhunter/glitchhunter/discussions

---

**Viel Erfolg bei der Migration!** 🚀
