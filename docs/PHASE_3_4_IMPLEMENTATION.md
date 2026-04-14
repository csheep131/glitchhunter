# GlitchHunter Phase 3 & 4 Implementierungsdokumentation

**Datum:** 14. April 2026  
**Version:** 2.0  
**Status:** Abgeschlossen

---

## Übersicht

Diese Dokumentation beschreibt die Implementierung von Phase 3 (Patch Loop) und Phase 4 (Finalizer + Escalation) des GlitchHunter-Projekts.

---

## Phase 3: Regression-Proof Patch Loop

### Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 3: PATCH LOOP                           │
│                                                                   │
│  Input: PrioritizedCandidates (aus Phase 2)                      │
│          │                                                       │
│          ▼                                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 1. Regression Test Generation (Fail2Pass)                 │  │
│  │    • 3-5 Edge-Case Tests pro Bug                          │  │
│  │    • Tests MÜSSEN vor Patch fehlschlagen                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│          │                                                       │
│          ▼                                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 2. SAFETY GATE 1: Pre-Apply Validation                    │  │
│  │    • Syntax-Check + Linter                                │  │
│  │    • Semantischer Diff (Tree-sitter)                      │  │
│  │    • Policy-Check (max 3 Dateien, max 160 Zeilen)         │  │
│  │    • Security-Check (verbotene Imports)                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│          │                                                       │
│          ▼                                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 3. Sandbox Execution (Git-Worktree + Docker)              │  │
│  │    • Patch in isoliertem Worktree anwenden                │  │
│  │    • Test-Suite ausführen (pytest, cargo test, npm test)  │  │
│  │    • Netzwerk disabled, Timeout 60s                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│          │                                                       │
│          ▼                                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 4. SAFETY GATE 2: Post-Apply Verification                 │  │
│  │    • Verifier-Confidence >= 95%                           │  │
│  │    • Graph-Vergleich (Before/After DFG + Call-Graph)      │  │
│  │    • Breaking Changes Detection                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│          │                                                       │
│          ▼                                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 5. Coverage Check                                         │  │
│  │    • Coverage-Regression erkennen                         │  │
│  │    • Toleranz: 1%                                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│          │                                                       │
│          ▼                                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 6. Decision: ACCEPT / RETRY / ESCALATE                    │  │
│  │    • ACCEPT: Alle Gates bestanden                         │  │
│  │    • RETRY: Max 5 Iterationen                             │  │
│  │    • ESCALATE: Nach 2x ohne Fortschritt                   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Komponenten

#### 3.1 PreApplyValidator (`src/fixing/pre_apply_validator.py`)

**Zweck:** Validiert Patches VOR dem Anwenden (Gate 1)

**Features:**
- Syntax-Check (AST-Parsing für Python, Node.js für JS, Rustc für Rust)
- Linter-Integration (Ruff, Pylint, ESLint, Clippy)
- Semantischer Diff mit Tree-sitter
- Policy-Checks:
  - Max 3 Dateien berührt
  - Max 160 Zeilen geändert
  - Keine neuen Dependencies
  - Keine verbotenen Imports (os.system, eval, exec, etc.)

**Usage:**
```python
from fixing.pre_apply_validator import PreApplyValidator

validator = PreApplyValidator(language="python")
result = validator.validate(original_code, patched_code, patch_diff=diff)

if result.passed:
    # Continue to sandbox
else:
    # Discard patch
```

#### 3.2 GraphComparator (`src/analysis/graph_comparator.py`)

**Zweck:** Vergleicht Before/After Graphen um Änderungen zu erkennen

**Features:**
- Data-Flow Graph Vergleich
- Call-Graph Vergleich
- Control-Flow Graph Vergleich
- Breaking Changes Detection
- Security-relevante Änderungen erkennen

**Usage:**
```python
from analysis.graph_comparator import GraphComparator

comparator = GraphComparator()
comparison = comparator.compare(before_graph, after_graph, graph_type="dfg")

if comparison.has_breaking_changes:
    # Reject patch
if comparison.has_security_relevant_changes:
    # Security review required
```

#### 3.3 PostApplyVerifier (`src/fixing/post_apply_verifier.py`)

**Zweck:** Validiert Patches NACH dem Anwenden (Gate 2)

**Features:**
- LLM-basierte Verifikation (Confidence >= 95%)
- Regelbasierte Verifikation (Fallback)
- Graph-Vergleich Integration
- Breaking Changes Detection
- Test-Ergebnisse einbeziehen

**Usage:**
```python
from fixing.post_apply_verifier import PostApplyVerifier

verifier = PostApplyVerifier(model_path="path/to/model")
result = verifier.verify(
    original_code=original,
    patched_code=patched,
    before_graph=before,
    after_graph=after,
    test_results=test_results,
)

if result.passed:
    # Accept patch
```

#### 3.4 CoverageChecker (`src/fixing/coverage_checker.py`)

**Zweck:** Stellt sicher, dass Patches keine Coverage-Regression verursachen

**Features:**
- Multi-Language Support (Python, Rust, JavaScript/TypeScript)
- Coverage-Messung mit:
  - Python: coverage.py, pytest-cov
  - Rust: cargo-tarpaulin
  - JS/TS: nyc, jest --coverage
- Toleranz: 1%
- Empfehlungen generieren

**Usage:**
```python
from fixing.coverage_checker import CoverageChecker

checker = CoverageChecker(language="python")
result = checker.check_coverage(code, test_code, before_coverage=before)

if result.coverage_diff.regression:
    # Reject patch
```

#### 3.5 SandboxExecutor (`src/agent/sandbox_executor.py`)

**Zweck:** Führt Patches in isolierter Sandbox aus

**Features:**
- Docker-Container für Isolation
- Git-Worktree für sichere Patch-Anwendung
- Test-Suite Execution (pytest, cargo test, npm test)
- Security-Checks vor Ausführung
- Resource-Limits (CPU, Memory, Time)
- Netzwerk disabled

**Usage:**
```python
from agent.sandbox_executor import SandboxExecutor, SandboxConfig

config = SandboxConfig(
    docker_image="python:3.11-slim",
    timeout=180,
    worktree_enabled=True,
)

executor = SandboxExecutor(config)
result = executor.execute_patch(
    patch_diff=patch,
    repo_path="/path/to/repo",
    test_command="pytest",
)

if result.all_tests_passed:
    # Continue to Gate 2
```

#### 3.6 PatchLoopStateMachine (`src/agent/patch_loop.py`)

**Zweck:** Koordiniert den kompletten Patch-Loop

**Features:**
- LangGraph State Machine Integration
- Maximal 5 Iterationen
- Accept / Retry / Escalate Logik
- Fail2Pass-Prinzip

**Usage:**
```python
from agent.patch_loop import PatchLoopStateMachine

machine = PatchLoopStateMachine(
    candidate=candidate,
    original_code=code,
    before_graph=graph,
    max_iterations=5,
)

result = machine.run_all_iterations()

if result.final_decision == "accept":
    # Patch accepted
elif result.final_decision == "escalate":
    # Escalate to Phase 4
```

---

## Phase 4: Finalizer + Escalation

### Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 4: FINALIZER                            │
│                                                                   │
│  Input: AcceptedPatch | EscalationTrigger                        │
│          │                                                       │
│          ▼                                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 4.1 Rule Learner                                          │  │
│  │     • Muster aus Patches extrahieren                      │  │
│  │     • Semgrep-Regeln generieren                           │  │
│  │     • rules.yaml aktualisieren                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│          │                                                       │
│          ▼                                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 4.2 Patch Merger                                          │  │
│  │     • Git-Worktree Isolation                              │  │
│  │     • Auto-Branch-Erstellung                              │  │
│  │     • Commit mit detaillierter Message                    │  │
│  │     • Bug-ID Tags                                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│          │                                                       │
│          ▼                                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 4.3 Report Generator                                      │  │
│  │     • JSON-Report (maschinenlesbar)                       │  │
│  │     • Markdown-Report (menschenlesbar)                    │  │
│  │     • Session Summary                                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ESCALATION HIERARCHY (4 Levels)                                 │
│  ─────────────────────────────                                   │
│  Level 1: Context Explosion                                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ • Repomix XML-Packung (gesamtes Repo)                     │  │
│  │ • Git-Blame Integration                                   │  │
│  │ • Dependency-Graphs                                       │  │
│  │ • Call-Chains                                             │  │
│  │ • Target: 160k+ Tokens                                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│          │ Success?                                              │
│          ▼                                                       │
│  Level 2: Bug Decomposition                                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ • Zerlege Bug in 2-4 Sub-Bugs                             │  │
│  │ • Strategien: Causal, Component, Symptom                  │  │
│  │ • Priorisierung nach Schweregrad                          │  │
│  │ • Mini-Patch-Loops pro Sub-Bug                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│          │ All fixed?                                            │
│          ▼                                                       │
│  Level 3: Multi-Model Ensemble                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ • Parallele Analysen mit 3+ Modellen                      │  │
│  │ • Ensemble-Voting                                         │  │
│  │ • Agreement-Levels: unanimous, majority, plurality        │  │
│  │ • Weighted Voting mit Confidence                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│          │ Agreement?                                            │
│          ▼                                                       │
│  Level 4: Human-in-the-Loop                                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ • Detaillierter Report                                    │  │
│  │ • Liste versuchter Fixes                                  │  │
│  │ • Evidenz-Zusammenstellung                                │  │
│  │ • Handlungsempfehlungen                                   │  │
│  │ • Draft-PR mit 3 Fix-Vorschlägen                          │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Komponenten

#### 4.1 RuleLearner (`src/fixing/rule_learner.py`)

**Zweck:** Extrahiert Muster aus erfolgreichen Patches und generiert Semgrep-Regeln

**Features:**
- Pattern-Extraktion aus Diffs
- Pattern-Typen: fix, vulnerability, optimization, best_practice
- Semgrep-Regel-Generierung
- YAML-Export
- Generalisierung (Strings → "$STRING", Numbers → "$NUMBER")

**Usage:**
```python
from fixing.rule_learner import RuleLearner

learner = RuleLearner(output_dir="src/fixing/rules")
result = learner.learn_from_patches(patches)

# result.semgrep_rules enthält generierte Regeln
# result.rules_file zeigt auf YAML-Datei
```

#### 4.2 PatchMerger (`src/fixing/patch_merger.py`)

**Zweck:** Mergt akzeptierte Patches in die Main-Branch

**Features:**
- Git-Worktree für Isolation
- Automatische Branch-Erstellung (`glitchhunter/fix_BUG-ID_TIMESTAMP`)
- Detaillierte Commit-Messages
- Bug-ID Tags
- Cleanup-Funktion

**Usage:**
```python
from fixing.patch_merger import PatchMerger

merger = PatchMerger(repo_path="/path/to/repo")
result = merger.merge_patches(patches)

if result.success:
    commit_hash = result.commit.hash[:8]
    # Patches erfolgreich gemergt
```

#### 4.3 ReportGenerator (`src/fixing/report_generator.py`)

**Zweck:** Generiert JSON + Markdown Reports

**Features:**
- JSON-Reports (maschinenlesbar)
- Markdown-Reports (menschenlesbar)
- Eskalations-Reports
- Session Summaries
- Automatische Speicherung

**Usage:**
```python
from fixing.report_generator import ReportGenerator

generator = ReportGenerator(output_dir="reports")
bundle = generator.generate_report(bugs, fixes, metadata)

# bundle.json_report für Maschinen
# bundle.markdown_report für Menschen
```

#### 4.4 ContextExplosion (`src/escalation/context_explosion.py`)

**Zweck:** Erweitert Kontext auf 160k+ Tokens (Level 1)

**Features:**
- Repomix XML-Packung
- Git-Blame Integration
- Dependency-Graphs
- Call-Chains
- Token-Schätzung

**Usage:**
```python
from escalation.context_explosion import ContextExplosion

explosion = ContextExplosion(repo_path="/path/to/repo")
context = explosion.explode(
    file_path="src/auth.py",
    bug_context="SQL injection vulnerability",
    include_dependencies=True,
    include_call_chains=True,
)

# context.total_tokens ~ 160000
```

#### 4.5 BugDecomposer (`src/escalation/bug_decomposer.py`)

**Zweck:** Zerlegt komplexe Bugs in 2-4 Sub-Bugs (Level 2)

**Features:**
- Strategien: Causal, Component, Symptom
- Priorisierung (high, medium, low)
- Max 4 Sub-Bugs

**Usage:**
```python
from escalation.bug_decomposer import BugDecomposer

decomposer = BugDecomposer()
result = decomposer.decompose(bug, strategy="causal")

# result.sub_bugs enthält zerlegte Bugs
# result.total_sub_bugs <= 4
```

#### 4.6 EnsembleCoordinator (`src/escalation/ensemble_coordinator.py`)

**Zweck:** Koordiniert Multi-Model Ensemble (Level 3)

**Features:**
- Parallele Analysen mit 3+ Modellen
- Ensemble-Voting
- Agreement-Levels: unanimous, majority, plurality, none
- Weighted Voting mit Confidence

**Usage:**
```python
from escalation.ensemble_coordinator import EnsembleCoordinator

coordinator = EnsembleCoordinator()
result = coordinator.run_ensemble(bug, models=["analyzer_1", "analyzer_2", "analyzer_3"])

# result.winning_hypothesis
# result.agreement_level
```

#### 4.7 HumanReportGenerator (`src/escalation/human_report_generator.py`)

**Zweck:** Generiert Reports für menschliche Review (Level 4)

**Features:**
- Detaillierte Bug-Beschreibung
- Liste versuchter Fixes
- Evidenz-Zusammenstellung
- Handlungsempfehlungen
- Draft-PR Generierung

**Usage:**
```python
from escalation.human_report_generator import HumanReportGenerator

generator = HumanReportGenerator()
report = generator.generate(
    bug=bug,
    attempted_fixes=fixes,
    evidence=evidence,
    escalation_level=4,
)

# report.to_dict() für JSON
# generator._report_to_markdown(report) für Markdown
```

---

## Test-Abdeckung

### Unit Tests

- **Phase 3:** `tests/test_phase3.py`
  - PreApplyValidator: 7 Tests
  - PostApplyVerifier: 3 Tests
  - CoverageChecker: 3 Tests
  - GraphComparator: 5 Tests
  - GateResults: 2 Tests

- **Phase 4:** `tests/test_phase4.py`
  - RuleLearner: 5 Tests
  - PatchMerger: 3 Tests
  - ReportGenerator: 5 Tests
  - ContextExplosion: 2 Tests
  - BugDecomposer: 4 Tests
  - EnsembleCoordinator: 4 Tests
  - HumanReportGenerator: 3 Tests

### Integration Tests

Siehe `tests/integration/test_pipeline/` (in Arbeit)

### E2E Tests

Siehe `tests/e2e/test_full_pipeline/` (in Arbeit)

---

## Performance-Metriken

| Metrik | Stack A (GTX 3060) | Stack B (RTX 3090) |
|--------|-------------------|-------------------|
| Lines per Minute | ~50 | ~200 |
| Analysis Time 10k | 10-18 min | 4-8 min |
| Patch Loop (pro Candidate) | 3-6 min | 1-3 min |
| Filtering Rate | 85% | 95% |

---

## Nächste Schritte

1. **Integration Tests vervollständigen**
2. **E2E Tests implementieren**
3. **Performance Optimization (Parallel Execution)**
4. **Benchmark Suite erstellen**

---

## Referenzen

- [IMPLEMENTIERUNGSPLAN.md](../development/IMPLEMENTIERUNGSPLAN.md)
- [REGRESSION_PROOF_FIXING.md](./REGRESSION_PROOF_FIXING.md)
- [ESCALATION_STRATEGY.md](./ESCALATION_STRATEGY.md)
