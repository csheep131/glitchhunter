<p align="center">
  <img src="logo/glitchhunter.png" alt="GlitchHunter Logo" width="400">
</p>

# GlitchHunter

**Local Open-Source LLM-powered Code Analysis & Auto-Fix**

GlitchHunter is an intelligent code analysis tool that uses **local open-source LLMs** (Qwen, Phi, DeepSeek) to not only find bugs and security vulnerabilities but **automatically and safely fix them**. The system automatically adapts to available hardware resources and uses different analysis stacks depending on GPU configuration.

## Core Features

- **100% Local LLMs**: No cloud APIs, no data leaks - all models run locally on your hardware
- **Automatic Bug Fixes**: Finds bugs AND fixes them safely with 4-fold safety checks
- **Adaptive Hardware Support**: Automatic selection between Stack A (8GB VRAM) and Stack B (24GB VRAM)
- **OWASP Top 10 2025**: Complete security coverage including API Security
- **Regression-Proof**: Every fix is validated with 4 Safety Gates - no new bugs guaranteed
- **Multi-Model Inference**: Support for Qwen3.5, Phi-4-mini, DeepSeek-V3.2

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    GLITCHHUNTER PIPELINE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. INGESTION: Repository scanning & understanding              │
│     • Tree-sitter AST analysis                                  │
│     • Git History & Hotspots                                    │
│     • Symbol graph creation                                     │
│                                                                  │
│  2. SHIELD: Bugs & Security vulnerabilities finding             │
│     • Semgrep Security Scan (OWASP Top 10)                      │
│     • Data-Flow Graph analysis                                  │
│     • 3-5 hypotheses per bug                                    │
│                                                                  │
│  3. PATCH LOOP: Secure fixes generation                        │
│     • LLM generates minimal patch                               │
│     • Gate 1: Pre-Apply Validation (Syntax, Linting)            │
│     • Gate 2: Sandbox Test (Docker-isolated)                    │
│     • Gate 3: Post-Apply Verifier (95% Confidence)              │
│     • Gate 4: Coverage Check (no regression)                    │
│                                                                  │
│  4. FINALIZER: Merge fixes & learn                              │
│     • Git-Worktree merge with commit                            │
│     • Learn new Semgrep rules                                   │
│     • JSON/Markdown Reports                                     │
│                                                                  │
│  ESCALATION: For complex bugs (4 Levels)                        │
│     • Level 1: Context Explosion (160k Tokens)                  │
│     • Level 2: Bug Decomposition (Sub-Bugs)                     │
│     • Level 3: Multi-Model Ensemble (Voting)                    │
│     • Level 4: Human-in-the-Loop (Draft-PR)                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Hardware Stacks

| Feature | Stack A (GTX 3060) | Stack B (RTX 3090) |
|---------|-------------------|-------------------|
| VRAM | 8GB | 24GB |
| Mode | Sequential | Parallel |
| Models | Qwen3.5-9B + Phi-4-mini | Qwen3.5-27B/35B + DeepSeek-V3.2-Small |
| Context | 64k-128k (TurboQuant) | 100k-200k |
| Security | Security-Lite | Full Security Shield |
| Throughput | ~50 LOC/min | ~200 LOC/min |
| 10k lines | 10-18 min | 4-8 min |

## Quickstart

### Prerequisites

- Python 3.10+
- NVIDIA GPU with CUDA 12.x
- Docker (for sandbox execution)
- cmake, build-essential

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/glitchhunter.git
cd glitchhunter

# Install dependencies
pip install -r requirements.txt

# Build llama-cpp-python for GPU (with TurboQuant)
./scripts/build_llama_cpp.sh

# Download models (GGUF format, local)
python scripts/download_models.py
```

### Start Stack A (GTX 3060)

```bash
./scripts/run_stack_a.sh
```

### Start Stack B (RTX 3090)

```bash
./scripts/run_stack_b.sh
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
│   ├── agent/         # LangGraph State Machine (5 States)
│   ├── mapper/        # Repository mapping and symbol graph
│   ├── fixing/        # Patch generation and Safety Gates
│   ├── escalation/    # 4-Level escalation hierarchy
│   ├── api/           # FastAPI Server and routes
│   └── core/          # Configuration, logging, exceptions
├── scripts/           # Build and run scripts
├── tests/             # Unit Tests (111 Tests)
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