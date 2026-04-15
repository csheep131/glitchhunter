<p align="center">
  <img src="logo/glitchhunter.png" alt="GlitchHunter Logo" width="400">
</p>

# GlitchHunter

**Local Open-Source LLM-powered Code Analysis & Auto-Fix**

GlitchHunter is an intelligent code analysis tool that uses **local open-source LLMs** (Qwen, Phi, DeepSeek) to not only find bugs and security vulnerabilities but **automatically and safely fix them**. The system automatically adapts to available hardware resources and uses different analysis stacks depending on GPU configuration.

## Core Features

- **100% Local LLMs**: No cloud APIs, no data leaks - all models run locally on your hardware
- **AI-Augmented Scanning**: Uses semantic LLM reasoning to verify findings where static analysis fallback (Semantic Logic Analysis).
- **Full Automation**: One command handles building, starting the LLM server, scanning, and fixing.
- **TurboQuant Acceleration**: Optimized KV-Cache and Flash-Attention for 128k+ context on consumer GPUs.
- **OWASP Top 10 2025**: Complete security coverage including API Security and JWT rules.
- **Automated Reporting**: Generates detailed Markdown and JSON reports for every run.
- **Smart Ignore Service**: Filter out dependency noise using the `.glitchignore` system.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    GLITCHHUNTER PIPELINE                         │
│             (Fully Automated Single-Terminal Workflow)             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. INGESTION: Repository scanning & understanding              │
│     • Tree-sitter AST analysis                                  │
│     • Smart Ignore system (.glitchignore)                       │
│     • Symbol graph creation                                     │
│                                                                  │
│  2. SHIELD: Bugs & Security vulnerabilities finding             │
│     • Semgrep Security Scan (OWASP Top 10)                      │
│     • AI Hypothesis Generation (LLM-driven for unknown types)   │
│     • Data-Flow Graph analysis                                  │
│                                                                  │
│  3. ANALYZER: Semantic AI Verification                         │
│     • LLM Verifier confirms weak graph findings                 │
│     • Logical reasoning boost (85%+ Confidence)                 │
│                                                                  │
│  4. PATCH LOOP: Secure fixes generation                        │
│     • LLM generates minimal patch                               │
│     • 4 Safety Gates: Syntax, Sandbox, Verifier, Coverage       │
│                                                                  │
│  5. FINALIZER: Merge fixes & reporting                          │
│     • Git-Worktree merge with commit                            │
│     • Automatic Markdown/JSON Report generation                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Hardware Stacks

| Feature | Stack A (GTX 3060) | Stack B (RTX 3090) |
|---------|-------------------|-------------------|
| VRAM | 8GB | 24GB |
| Acceleration | TurboQuant + Flash-Attention | Native 16-bit / FP8 |
| Context | 64k-128k (Layer-Adaptive) | 100k-200k |
| Build | Automated (CMake/CUDA) | Automated (CMake/CUDA) |
| Security | Security-Lite | Full Security Shield |

## Quickstart

### Installation

```bash
# Clone repository
git clone https://github.com/csheep131/glitchhunter.git
cd glitchhunter

# Install dependencies
pip install -r requirements.txt
```

### Automatic Workflow (Recommended)

GlitchHunter now features a **fully automated lifecycle**. The scripts handle building the optimized inference engine, starting the background LLM server, performing analysis, and cleaning up processes automatically.

**Scan Only (Safety Audit)**
Find vulnerabilities without modifying code.
```bash
./scripts/run_stack_a.sh scan /path/to/repo
```

**Fix (Full Repair)**
Find and automatically repair vulnerabilities with 4-layer validation.
```bash
./scripts/run_stack_a.sh fix /path/to/repo
```

## Advanced Features

### Automated Reports
Every run generates two types of reports in the `reports/` directory (configurable in `config.yaml`):
- **Markdown (`*_report.md`)**: Human-readable summary with severity icons and findings.
- **JSON (`*_report.json`)**: Machine-readable data for CI/CD integration.

### Smart Ignores (.glitchignore)
To prevent GlitchHunter from wasting VRAM on dependencies or build artifacts, use a `.glitchignore` file in your repository root.
It supports standard glob patterns (similar to `.gitignore`):
```text
# .glitchignore example
venv/
node_modules/
target/
dist/
tests/data/
```

### System Configuration
The `config.yaml` controls hardware profiles, paths, and feature toggles:
- `llama_tools_path`: Path to the TurboQuant build directory.
- `paths.reports`: Directory for analysis reports.
- `features`: Toggle specific analysis levels (AST, Complexity, etc.).

### Usage (Stack B - RTX 3090)

```bash
# Option 1: Scan only
./scripts/run_stack_b.sh scan /path/to/repo

# Option 2: Fix
./scripts/run_stack_b.sh fix /path/to/repo
```

### Use API

```bash
# Start server
python -m src.api.server --host 0.0.0.0 --port 8000

# Request code analysis
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"code": "def vulnerable(): eval(user_input)", "language": "python"}'

# Request automatic fix
curl -X POST http://localhost:8000/api/fix \
  -H "Content-Type: application/json" \
  -d '{"file": "src/vulnerable.py", "bug_id": "BUG-001"}'
```

## Project Structure

```
glitchhunter/
├── src/
│   ├── hardware/      # Hardware detection and VRAM management
│   ├── inference/     # Local model inference with llama-cpp
│   ├── prefilter/     # AST analysis and complexity checks
│   ├── security/      # OWASP Scanner and Security Shield
│   ├── agent/         # LangGraph State Machine (8 States) - Status: docs/STATE_MACHINE_STATUS.md
│   ├── mapper/        # Repository mapping and symbol graph
│   ├── fixing/        # Patch generation and Safety Gates (4 Gates + EvidenceGate)
│   ├── escalation/    # 4-Level escalation hierarchy
│   ├── api/           # FastAPI Server and routes
│   └── core/          # Configuration, logging, exceptions
├── scripts/           # Build and run scripts
├── tests/             # Unit Tests (150 Tests) - Coverage: ~80%
└── docs/              # Documentation
```

## Security Guarantees

GlitchHunter uses a **Regression-Proof Fixing** principle with 4 Safety Gates:

1. **Gate 1: Pre-Apply Validation**
   - Syntax-Check + Linter
   - Semantic Diff (Tree-sitter)
   - Policy-Check (max 3 files, max 160 lines)

2. **Gate 2: Sandbox Execution**
   - Docker-isolated execution
   - All tests must pass
   - Network disabled

3. **Gate 3: Post-Apply Verifier**
   - LLM-Verifier (95% Confidence)
   - Graph comparison (Before/After)
   - Breaking Changes Detection

4. **Gate 4: Coverage Check**
   - No coverage regression
   - Fail2Pass principle

**Result:** Every fix is safe and does not introduce new bugs.

## Configuration

The `config.yaml` controls all hardware profiles and feature toggles:

```yaml
hardware:
  stack_a:
    vram_limit: 8GB
    models: [qwen3.5-9b, phi-4-mini]
    mode: sequential
    security: lite
    context: 64k-128k

  stack_b:
    vram_limit: 24GB
    models: [qwen3.5-27b, deepseek-v3.2-small]
    mode: parallel
    security: full
    context: 100k-200k

features:
  hypothesis_flow: true       # 3-5 hypotheses per bug
  regression_tests: true      # Fail2Pass tests
  escalation_levels: 4        # 4-Level escalation
  self_improving_rules: true  # Automatic Semgrep rules
```

## Tests

```bash
# Run all tests
pytest tests/

# With coverage
pytest tests/ --cov=src --cov-report=html

# Phase-specific tests
pytest tests/test_phase1.py  # Repository Mapping
pytest tests/test_phase2.py  # Security Shield
pytest tests/test_phase3.py  # Patch Loop (20 Tests)
pytest tests/test_phase4.py  # Finalizer (26 Tests)
```

## Why GlitchHunter?

| Feature | GlitchHunter | Commercial Tools |
|---------|--------------|-------------------|
| Local LLMs | 100% local | Cloud-API |
| Automatic Fixes | With 4 Gates | Only Finding |
| Data Privacy | No cloud | Cloud-based |
| Cost | Open Source | Expensive subscriptions |
| Customizable | Fully | Closed |

## License

MIT License

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

**GlitchHunter** - Finds bugs. Fixes them safely. 100% local.