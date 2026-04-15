# 🔬 GlitchHunter Dynamic Analysis Module

**Teil von GlitchHunter v2.0 - Coverage-guided Fuzzing Integration**

## Überblick

Das Dynamic Analysis Module erweitert GlitchHunter um automatisiertes Fuzzing:

- **AFL++** für C/C++ Code
- **Atheris** für Python Code
- **Coverage-Tracking** für intelligente Input-Selektion
- **Crash-Analyse** mit automatischer Klassifikation
- **Hybrid-Analyse** (Static + Dynamic) für höhere Trefferquote

---

## Installation

### Voraussetzungen

```bash
# AFL++ installieren (Ubuntu/Debian)
sudo apt install afl++

# ODER aus Source bauen (empfohlen für neueste Features)
git clone https://github.com/AFLplusplus/AFLplusplus
cd AFLplusplus
sudo ./build.sh
sudo ./install.sh

# Python-Dependencies
pip install atheris  # Für Python-Fuzzing
```

### GlitchHunter Dependencies

```bash
# Im GlitchHunter-Verzeichnis
pip install -e .
```

---

## Quick Start

### 1. Automatische Dynamic Analysis

```python
from analysis.dynamic import DynamicAnalyzer

analyzer = DynamicAnalyzer(
    repo_path="/path/to/your/project",
    output_dir="/tmp/glitchhunter_dynamic",
)

# Automatische Analyse starten
result = analyzer.analyze(
    max_targets=5,           # Maximale Targets
    timeout_per_target=600,  # 10 Minuten pro Target
    use_coverage_guided=True,
)

# Ergebnisse
print(f"Executions: {result.total_execs}")
print(f"Crashes: {result.crashes_found} ({result.unique_crashes} unique)")
print(f"Coverage: {result.coverage:.1f}%")
```

### 2. Manuelle Target-Auswahl

```python
from analysis.dynamic import DynamicAnalyzer

analyzer = DynamicAnalyzer(repo_path=".")

# Fuzzing-Targets identifizieren
targets = analyzer.identify_targets()

for i, target in enumerate(targets):
    print(f"{i+1}. {target.function_name} ({target.language})")
    print(f"   Risk Score: {target.risk_score}")
    print(f"   File: {target.file_path}:{target.line_number}")
```

### 3. Harness generieren

```python
# Harness für spezifisches Target
harness = analyzer.generate_harness(targets[0])

print(f"Harness: {harness.harness_file}")
print(f"Build:  {harness.build_command}")
print(f"Run:    {harness.run_command}")
```

---

## Module-Übersicht

### `DynamicAnalyzer`

Hauptklasse für Dynamic Analysis.

**Methoden:**
- `analyze()` - Automatische komplette Analyse
- `identify_targets()` - Fuzzing-Targets finden
- `generate_harness()` - Harness für Target generieren
- `analyze_crashes()` - Crashes analysieren
- `export_report()` - Report generieren

### `HarnessGenerator`

Generiert Fuzzing-Harnesses automatisch.

**Unterstützte Sprachen:**
- C/C++ → AFL++ Harness
- Python → Atheris Harness

### `AFLPlusPlusFuzzer`

AFL++ Integration.

**Features:**
- Auto-detect AFL++ Installation
- Persistent Mode Support
- Corpus Minimization
- Crash-Sampling

### `CoverageTracker`

Coverage-Tracking während Fuzzing.

**Features:**
- AFL++ Coverage-Map Parsing
- LCOV-Report-Generierung
- Coverage-guided Input-Selektion
- HTML-Report-Generierung

### `CrashAnalyzer`

Analysiert und klassifiziert Crashes.

**Features:**
- Automatische Crash-Typ-Erkennung
- Severity-Bewertung (critical/high/medium/low)
- Duplicate-Detection
- Stack-Trace-Extraktion
- Markdown-Report-Generierung

---

## Crash-Typen

Das Modul erkennt automatisch:

| Crash-Typ | Beschreibung | Severity |
|-----------|--------------|----------|
| **Heap-Buffer-Overflow** | Pufferüberlauf im Heap | High |
| **Stack-Buffer-Overflow** | Pufferüberlauf im Stack | High |
| **Use-After-Free** | Verwendung freigegebenen Speichers | High |
| **Double-Free** | Doppeltes Freigeben | High |
| **Null-Pointer-Dereference** | Zugriff auf Null-Pointer | Medium |
| **SIGSEGV** | Segmentation Fault | Variabel |
| **SIGABRT** | Programm-Abbruch | Medium |
| **SIGFPE** | Gleitkomma-Fehler | Medium |

---

## Beispiele

### Beispiel 1: C/C++ Projekt fuzzieren

```python
from analysis.dynamic import DynamicAnalyzer, AFLPlusPlusFuzzer

# Analyzer initialisieren
analyzer = DynamicAnalyzer(repo_path="/path/to/c-project")

# Targets finden
targets = analyzer.identify_targets(max_targets=3)

# Für jedes Target fuzzieren
for target in targets:
    print(f"Fuzzing: {target.function_name}")
    
    # Harness generieren
    harness = analyzer.generate_harness(target)
    
    # AFL++ starten
    afl = AFLPlusPlusFuzzer(output_dir="/tmp/afl_output")
    result = afl.fuzz(
        target_binary=harness.harness_file,
        input_corpus=harness.corpus_seeds[0],
        timeout=3600,  # 1 Stunde
    )
    
    print(f"  Execs: {result.total_execs}")
    print(f"  Crashes: {result.crashes_found}")
```

### Beispiel 2: Python-Projekt mit Atheris

```python
from analysis.dynamic import DynamicAnalyzer, AtherisFuzzer

analyzer = DynamicAnalyzer(repo_path="/path/to/python-project")
targets = analyzer.identify_targets()

for target in targets:
    if target.language == "python":
        harness = analyzer.generate_harness(target)
        
        # Atheris Fuzzer
        atheris = AtherisFuzzer(output_dir="/tmp/atheris_output")
        result = atheris.fuzz(
            harness_file=harness.harness_file,
            timeout=1800,  # 30 Minuten
        )
        
        print(f"Found {result.crashes_found} crashes")
```

### Beispiel 3: Crash-Report generieren

```python
from analysis.dynamic import CrashAnalyzer

# Crash-Analyzer initialisieren
crash_analyzer = CrashAnalyzer(
    target_binary="./fuzz_target",
    timeout=5,
)

# Crashes analysieren
crashes = crash_analyzer.analyze_crash_dir("./crashes")

# Report generieren
report = crash_analyzer.generate_crash_report(
    crashes=crashes,
    output_file="crash_report.md",
)

print(report)
```

### Beispiel 4: Coverage-Report

```python
from analysis.dynamic import CoverageTracker

tracker = CoverageTracker(repo_path=".")

# Coverage aus AFL++ Output parsen
report = tracker.parse_afl_coverage(
    afl_output_dir="/tmp/afl_output"
)

print(f"Total Coverage: {report.total_coverage:.1f}%")
print(f"New Paths: {len(report.new_coverage_paths)}")

# HTML-Report generieren
html_report = tracker.generate_lcov_report(
    binary_path="./instrumented_binary",
    output_format="html",
)

print(f"HTML Report: {html_report}")
```

---

## Konfiguration

### `config.yaml` Erweiterung

```yaml
dynamic_analysis:
  enabled: true
  
  # AFL++ Konfiguration
  afl:
    enabled: true
    path: "/usr/bin/afl-fuzz"  # Auto-detect wenn leer
    timeout: 1000  # ms pro Exec
    memory_limit: 256  # MB
    
  # Atheris Konfiguration
  atheris:
    enabled: true
    workers: 4
    jobs: 4
    
  # Coverage-Tracking
  coverage:
    enabled: true
    format: "lcov"  # oder "html"
    min_coverage_gain: 0.01
    
  # Crash-Analyse
  crash_analysis:
    enabled: true
    max_samples: 10
    duplicate_detection: true
    
  # Targets
  targets:
    max_targets: 10
    min_risk_score: 0.5
    languages: ["c", "cpp", "python"]
```

---

## Output-Struktur

```
.glitchhunter/dynamic_analysis/
├── harnesses/           # Generierte Fuzzing-Harnesses
│   ├── fuzz_function1.cpp
│   └── fuzz_function2.py
├── afl/                 # AFL++ Output
│   ├── function1/
│   │   ├── queue/
│   │   ├── crashes/
│   │   ├── hangs/
│   │   └── fuzzer_stats
│   └── function2/
├── atheris/             # Atheris Output
│   └── function1/
├── coverage/            # Coverage-Reports
│   ├── coverage.info
│   └── html/
└── reports/             # Analyse-Reports
    ├── crash_report.md
    └── dynamic_analysis.json
```

---

## Performance-Tipps

1. **AFL++ Persistent Mode**
   - Deutlich schneller (10x-100x)
   - `#define AFL_PERSISTENT` im Harness
   - Siehe `fuzzer.py` für Beispiele

2. **Corpus-Minimierung**
   - `afl-cmin` vor Fuzzing starten
   - Reduziert redundante Inputs
   - Beschleunigt Coverage-Entdeckung

3. **Parallel-Fuzzing**
   - Master/Slave-Setup mit `-M` und `-S`
   - `parallel_jobs` in Config erhöhen

4. **Coverage-Guided**
   - Nur interessante Inputs weiterverfolgen
   - `+cov` markierte Inputs priorisieren

---

## Troubleshooting

### AFL++ nicht gefunden

```bash
# Installation prüfen
which afl-fuzz

# ODER AFL_PATH setzen
export AFL_PATH=/opt/aflplusplus/afl-fuzz
```

### Instrumentation fehlgeschlagen

```bash
# AFL++ Compiler verwenden
afl-clang-lto -g -O2 -fsanitize=address target.c -o target
```

### Keine Crashes gefunden

- Fuzzing-Zeit erhöhen
- Besseres Initial-Corpus verwenden
- Riskante Funktionen manuell als Target markieren

### Memory-Limit exceeded

```yaml
# In config.yaml
afl:
  memory_limit: 512  # MB erhöhen
```

---

## Integration in GlitchHunter Pipeline

```python
from agent.state_machine import StateMachine
from analysis.dynamic import DynamicAnalyzer

# Dynamic Analysis in Pipeline integrieren
state_machine = StateMachine()
state = state_machine.run(repo_path=".")

# Nach Static Analysis
if state.get("candidates"):
    # Dynamic Analysis für高风险 Candidates
    analyzer = DynamicAnalyzer(repo_path=".")
    dynamic_result = analyzer.analyze(timeout_per_target=300)
    
    # Ergebnisse mergen
    state["dynamic_crashes"] = dynamic_result.crashes
    state["dynamic_coverage"] = dynamic_result.coverage
```

---

## Sicherheitshinweise

⚠️ **Achtung:** Fuzzing kann zu Programmabstürzen führen!

- **Sandbox-Umgebung** verwenden für unbekannte Binaries
- **Resource-Limits** setzen (Memory, Timeout)
- **Keine Production-Systeme** fuzzieren
- **Sensitive Daten** aus Test-Inputs entfernen

---

## Weiterführende Links

- [AFL++ Dokumentation](https://aflplus.plus/)
- [Atheris (Google)](https://github.com/google/atheris)
- [libFuzzer Guide](https://llvm.org/docs/LibFuzzer.html)
- [GlitchHunter ROADMAP2_0](../development/ROADMAP2_0.md)

---

**Autor:** GlitchHunter Team  
**Version:** v2.0 (April 2026)
