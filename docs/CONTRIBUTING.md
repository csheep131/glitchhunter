# GlitchHunter v3.0 - Contributing Guide

**Version:** 3.0.0-dev  
**Letztes Update:** 20. April 2026

## Inhaltsverzeichnis

1. [Einleitung](#einleitung)
2. [Development-Setup](#development-setup)
3. [Code-Standards](#code-standards)
4. [Test-Richtlinien](#test-richtlinien)
5. [PR-Prozess](#pr-prozess)
6. [Architektur-Prinzipien](#architektur-prinzipien)
7. [Commit-Conventions](#commit-conventions)
8. [Release-Prozess](#release-prozess)

---

## Einleitung

Willkommen bei GlitchHunter! Wir freuen uns über jeden Beitrag. Dieses Dokument beschreibt wie du zum Projekt beitragen kannst.

### Wie kann ich beitragen?

- 🐛 **Bug Reports** - Fehler im Issue-Tracker melden
- ✨ **Feature Requests** - Neue Features vorschlagen
- 📝 **Dokumentation** - Docs verbessern oder erweitern
- 💻 **Code** - Features implementieren oder Bugs fixen
- 🧪 **Tests** - Testabdeckung erhöhen
- 🔍 **Code Reviews** - PRs reviewen

---

## Development-Setup

### Voraussetzungen

- Python 3.10+
- Git
- Node.js 18+ (für JS/TS-Analyse)
- Docker (optional, für Sandbox-Tests)

### Schritt 1: Repository forken

```bash
# Fork auf GitHub erstellen
# Dann klonen:
git clone https://github.com/DEIN_USERNAME/glitchhunter.git
cd glitchhunter
```

### Schritt 2: Virtuelle Umgebung

```bash
# Virtuelle Umgebung erstellen
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# oder: .venv\Scripts\activate  # Windows
```

### Schritt 3: Dependencies installieren

```bash
# Development-Dependencies
pip install -e ".[dev]"

# Oder manuell:
pip install pytest pytest-cov pytest-asyncio black mypy ruff pre-commit
```

### Schritt 4: Pre-Commit Hooks

```bash
# Pre-Commit Hooks installieren
pre-commit install

# Hooks testen
pre-commit run --all-files
```

### Schritt 5: Tests ausführen

```bash
# Alle Tests
pytest

# Mit Coverage
pytest --cov=src --cov-report=html

# Spezifische Tests
pytest tests/test_agent/
pytest tests/test_prediction/
```

### Schritt 6: Entwicklungsumgebung prüfen

```bash
# System-Check
glitchhunter check

# Linting
ruff check src/
black --check src/

# Type-Checking
mypy src/
```

---

## Code-Standards

### Python Style Guide

Wir folgen **PEP 8** mit folgenden Anpassungen:

- **Line Length:** 100 Zeichen
- **Quotes:** Doppelte Anführungszeichen `"`
- **Imports:** Sortiert mit `ruff`
- **Type Hints:** Erforderlich für alle öffentlichen APIs

### Code-Beispiel

```python
"""
Beispiel für korrekten GlitchHunter Code.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.agents.base import BaseAgent


class StaticScannerAgent(BaseAgent):
    """
    StaticScannerAgent für Code-Analyse.
    
    Attributes:
        name: Name des Agenten
        findings: Liste von Findings
    """

    def __init__(self, name: str = "static_scanner"):
        """
        Initialisiert StaticScannerAgent.
        
        Args:
            name: Name des Agenten
        """
        super().__init__(name)
        self._findings: List[Dict[str, Any]] = []

    async def analyze(
        self,
        repo_path: Path,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Führt statische Analyse durch.
        
        Args:
            repo_path: Pfad zum Repository
            **kwargs: Zusätzliche Argumente
            
        Returns:
            Analyse-Ergebnis
            
        Raises:
            FileNotFoundError: Wenn repo_path nicht existiert
        """
        if not repo_path.exists():
            raise FileNotFoundError(f"Path not found: {repo_path}")
        
        # Implementierung
        return {"status": "success"}

    async def get_findings(self) -> List[Dict[str, Any]]:
        """Extrahiert alle Findings."""
        return self._findings.copy()
```

### Docstring-Format

Wir verwenden **Google-Style Docstrings**:

```python
def example_function(param1: str, param2: int) -> bool:
    """
    Kurzbeschreibung der Funktion.
    
    Detaillierte Beschreibung wenn nötig.
    
    Args:
        param1: Beschreibung von param1
        param2: Beschreibung von param2
        
    Returns:
        Beschreibung des Rückgabewerts
        
    Raises:
        ValueError: Wenn param1 ungültig ist
    """
```

### Type Hints

**Alle öffentlichen APIs müssen getypt sein:**

```python
# ✅ Korrekt
def analyze(repo_path: Path, timeout: int = 60) -> AnalysisResult:
    pass

# ❌ Falsch
def analyze(repo_path, timeout=60):
    pass
```

### Naming Conventions

| Element | Convention | Beispiel |
|---------|------------|----------|
| Klassen | PascalCase | `SwarmCoordinator` |
| Funktionen | snake_case | `run_swarm()` |
| Variablen | snake_case | `repo_path` |
| Konstanten | UPPER_SNAKE | `MAX_ITERATIONS` |
| Private | `_prefix` | `_findings` |
| Module | snake_case | `swarm_coordinator.py` |

---

## Test-Richtlinien

### Test-Struktur

```
tests/
├── test_agent/
│   ├── test_swarm_coordinator.py
│   ├── test_static_scanner.py
│   └── ...
├── test_prediction/
│   ├── test_engine.py
│   ├── test_model.py
│   └── ...
└── test_fixing/
    ├── test_auto_refactor.py
    └── ...
```

### Test-Beispiel

```python
"""Tests für SwarmCoordinator."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from agent.swarm_coordinator import SwarmCoordinator
from agent.state import SwarmState


class TestSwarmCoordinator:
    """Tests für SwarmCoordinator."""

    @pytest.fixture
    def coordinator(self):
        """Erstellt Test-Coordinator."""
        return SwarmCoordinator()

    @pytest.fixture
    def sample_repo(self, tmp_path):
        """Erstellt Test-Repository."""
        repo = tmp_path / "test_repo"
        repo.mkdir()
        (repo / "test.py").write_text("def hello(): pass")
        return repo

    @pytest.mark.asyncio
    async def test_run_swarm(self, coordinator, sample_repo):
        """Testet Swarm-Analyse."""
        # Arrange
        repo_path = sample_repo
        
        # Act
        results = await coordinator.run_swarm(repo_path)
        
        # Assert
        assert isinstance(results, SwarmState)
        assert results.repo_path == str(repo_path)
        assert results.current_phase == "complete"

    @pytest.mark.asyncio
    async def test_run_swarm_with_agents(self, coordinator, sample_repo):
        """Testet Swarm mit spezifischen Agenten."""
        # Act
        results = await coordinator.run_swarm(
            sample_repo,
            agents=["static", "dynamic"],
        )
        
        # Assert
        assert results.static_findings is not None
        assert results.dynamic_findings is not None

    def test_get_all_findings(self, coordinator):
        """Testet Finding-Extraktion."""
        # Arrange
        state = SwarmState()
        state.static_findings = [...]
        
        # Act
        findings = coordinator.get_all_findings(state)
        
        # Assert
        assert len(findings) > 0
```

### Test-Types

| Type | Beschreibung | Beispiel |
|------|--------------|----------|
| **Unit Tests** | Einzelne Komponenten | `test_swarm_coordinator.py` |
| **Integration Tests** | Komponenten-Zusammenspiel | `test_pipeline.py` |
| **E2E Tests** | Gesamter Workflow | `test_e2e.py` |
| **Performance Tests** | Laufzeit/Memory | `test_benchmarks.py` |

### Test-Markers

```python
@pytest.mark.asyncio  # Async-Tests
@pytest.mark.slow  # Langsame Tests (>5s)
@pytest.mark.integration  # Integrationstests
@pytest.mark.gpu  # GPU-required Tests
```

### Coverage-Anforderungen

| Komponente | Minimum | Ziel |
|------------|---------|------|
| Agent | 80% | 90% |
| Prediction | 80% | 90% |
| Fixing | 80% | 90% |
| Sandbox | 70% | 85% |
| **Gesamt** | **75%** | **85%** |

---

## PR-Prozess

### 1. Issue erstellen

Vor jedem PR ein Issue erstellen:

```markdown
## Beschreibung
Kurze Beschreibung des Problems/Features.

## Motivation
Warum ist dieses Feature wichtig?

## Proposed Solution
Wie soll das Problem gelöst werden?
```

### 2. Branch erstellen

```bash
# Von main branchen
git checkout main
git pull origin main
git checkout -b feature/my-new-feature
```

**Branch-Naming:**
- `feature/` - Neue Features
- `fix/` - Bug-Fixes
- `docs/` - Dokumentation
- `refactor/` - Refactoring
- `test/` - Tests

### 3. Implementieren

```bash
# Code schreiben
# Tests schreiben
# Tests laufen lassen
pytest

# Linting
ruff check src/
black src/

# Type-Checking
mypy src/
```

### 4. Committen

```bash
# Änderungen hinzufügen
git add .

# Committen mit Convention
git commit -m "feat: add new ML prediction engine"

# Pushen
git push origin feature/my-new-feature
```

### 5. PR erstellen

**PR-Template:**

```markdown
## Beschreibung
Was macht dieser PR?

## Änderungen
- [x] Feature implementiert
- [x] Tests hinzugefügt
- [x] Dokumentation aktualisiert

## Testing
Wie wurde getestet?

## Checklist
- [ ] Tests bestanden
- [ ] Linting bestanden
- [ ] Type-Checking bestanden
- [ ] Dokumentation aktuell
```

### 6. Code Review

**Review-Kriterien:**

- ✅ Code folgt Standards
- ✅ Tests sind vorhanden
- ✅ Dokumentation ist aktuell
- ✅ Keine Breaking Changes (oder dokumentiert)
- ✅ Performance ist akzeptabel

### 7. Merge

Nach Approval:

```bash
# Rebase auf main
git fetch origin
git rebase origin/main

# Merge (durch Maintainer)
git checkout main
git merge --no-ff feature/my-new-feature
git push origin main
```

---

## Architektur-Prinzipien

### 1. Single Responsibility

Jede Klasse hat eine Aufgabe:

```python
# ✅ Korrekt: Separate Klassen
class FeatureExtractor:
    """Extrahiert Features."""

class PredictionModel:
    """Führt Prediction durch."""

# ❌ Falsch: Alles in einer Klasse
class Everything:
    """Extrahiert Features UND macht Prediction."""
```

### 2. Dependency Injection

Lose Kopplung über Interfaces:

```python
# ✅ Korrekt
class SwarmCoordinator:
    def __init__(self, agent: BaseAgent):
        self.agent = agent

# ❌ Falsch
class SwarmCoordinator:
    def __init__(self):
        self.agent = StaticScannerAgent()  # Hard-coded
```

### 3. Type Safety

Vollständige Typisierung:

```python
# ✅ Korrekt
def process(data: Dict[str, Any]) -> List[Result]:
    ...

# ❌ Falsch
def process(data):
    ...
```

### 4. Error Handling

Explizite Fehlerbehandlung:

```python
# ✅ Korrekt
try:
    result = await analyze()
except AnalysisError as e:
    logger.error(f"Analysis failed: {e}")
    raise

# ❌ Falsch
try:
    result = await analyze()
except:
    pass  # Silent failure
```

### 5. Async-First

Alle I/O-Operationen sind async:

```python
# ✅ Korrekt
async def analyze_file(path: Path) -> Result:
    content = await asyncio.to_thread(path.read_text)
    return await self._analyze(content)

# ❌ Falsch (blockiert)
def analyze_file(path: Path) -> Result:
    content = path.read_text()  # Blocking I/O
```

---

## Commit-Conventions

Wir folgen **Conventional Commits**:

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Beschreibung |
|------|--------------|
| `feat` | Neues Feature |
| `fix` | Bug-Fix |
| `docs` | Dokumentation |
| `style` | Formatting, Semicolons, etc. |
| `refactor` | Code-Refactoring |
| `test` | Tests hinzufügen/ändern |
| `chore` | Build-Tooling, Dependencies |

### Beispiele

```bash
# Feature
feat(prediction): add ONNX model support

# Bug-Fix
fix(agent): resolve memory leak in swarm coordinator

# Dokumentation
docs(api): update SwarmCoordinator examples

# Refactoring
refactor(fixing): extract analyzer interfaces

# Tests
test(prediction): add unit tests for feature extractor

# Chore
chore(deps): bump onnxruntime to 1.18.0
```

### Scope

| Scope | Beschreibung |
|-------|--------------|
| `agent` | Swarm Coordinator, Agents |
| `prediction` | ML Prediction Engine |
| `fixing` | Auto-Refactoring |
| `sandbox` | Sandbox, Tracing |
| `api` | REST API |
| `cli` | Command-Line Interface |
| `docs` | Dokumentation |
| `tests` | Test-Suite |

---

## Release-Prozess

### Versionierung

Wir folgen **Semantic Versioning** (MAJOR.MINOR.PATCH):

- **MAJOR:** Breaking Changes
- **MINOR:** Neue Features (rückwärtskompatibel)
- **PATCH:** Bug-Fixes (rückwärtskompatibel)

### Release-Checklist

Vor jedem Release:

- [ ] Alle Tests bestanden
- [ ] Coverage > 75%
- [ ] Dokumentation aktuell
- [ ] CHANGELOG.md aktualisiert
- [ ] Version in `pyproject.toml` aktualisiert
- [ ] Git-Tag erstellt
- [ ] Release auf GitHub erstellt
- [ ] Package auf PyPI veröffentlicht

### Release-Schritte

```bash
# 1. Version aktualisieren (pyproject.toml)
version = "3.0.0"

# 2. CHANGELOG.md aktualisieren
# 3. Committen
git commit -m "chore: release v3.0.0"

# 4. Tag erstellen
git tag -a v3.0.0 -m "Release v3.0.0"

# 5. Pushen
git push origin main
git push origin v3.0.0

# 6. Package bauen
python -m build

# 7. Auf PyPI veröffentlichen
twine upload dist/*
```

---

## Code of Conduct

### Unsere Verpflichtung

Wir verpflichten uns zu einem offenen, freundlichen und inklusiven Umfeld für alle.

### Unsere Standards

Beispiele für erwünschtes Verhalten:

- Respektvoller Umgang
- Konstruktive Kritik
- Fokus auf gemeinsames Ziel

Beispiele für inakzeptables Verhalten:

- Beleidigungen
- Trolling
- Sexuelle Belästigung

### Durchsetzung

Bei Verstößen bitte melden an: team@glitchhunter.dev

---

## Lizenz

Mit dem Beitragen stimmst du der MIT-Lizenz zu.

---

## Fragen?

- **Dokumentation:** [docs/](README.md)
- **Issues:** [GitHub Issues](https://github.com/glitchhunter/glitchhunter/issues)
- **Discord:** [Community](https://discord.gg/glitchhunter)

---

**Danke für deinen Beitrag! 🎉**
