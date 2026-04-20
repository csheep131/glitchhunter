# GlitchHunter v2.0 - User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Problem-Solver Mode](#problem-solver-mode)
5. [Bug-Hunting Mode](#bug-hunting-mode)
6. [TUI Guide](#tui-guide)
7. [API Reference](#api-reference)
8. [Configuration](#configuration)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

---

## Introduction

GlitchHunter v2.0 is an intelligent code analysis and auto-fix tool powered by local LLMs. It features two distinct modes:

### Problem-Solver Mode
Accepts general problem statements, diagnoses root causes, and implements validated solutions automatically.

**Best for:**
- Performance issues
- Missing features
- Workflow automation
- Integration gaps
- General improvement requests

### Bug-Hunting Mode
Traditional static analysis with AI-augmented verification and automatic patch generation.

**Best for:**
- Security vulnerabilities
- Code defects
- Bug fixes
- Code quality improvements

---

## Installation

### Prerequisites

- Python 3.10+
- Git
- 8GB+ RAM (16GB+ recommended)
- Optional: NVIDIA GPU with 8GB+ VRAM

### Step 1: Clone Repository

```bash
git clone https://github.com/glitchhunter/glitchhunter.git
cd glitchhunter
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

### Step 3: Install Dependencies

```bash
pip install -e .
```

### Step 4: Download Models (Optional)

```bash
# Download recommended models
python scripts/download_models.py
```

### Step 5: Verify Installation

```bash
glitchhunter check
```

---

## Quick Start

### Problem-Solver Mode (Recommended for New Users)

```bash
# 1. Describe your problem
glitchhunter problem intake "The application startup is too slow"

# 2. Let GlitchHunter analyze it
glitchhunter problem classify prob_20260415_001
glitchhunter problem diagnose prob_20260415_001

# 3. Review the plan
glitchhunter problem plan prob_20260415_001

# 4. Execute fixes (DRY RUN FIRST!)
glitchhunter problem fix prob_20260415_001 --dry-run

# 5. Apply if satisfied
glitchhunter problem fix prob_20260415_001

# 6. Validate
glitchhunter problem validate prob_20260415_001
```

### Bug-Hunting Mode

```bash
# 1. Scan your codebase
glitchhunter analyze /path/to/your/code

# 2. Review findings
glitchhunter reports show latest

# 3. Apply fixes
glitchhunter fix apply latest
```

---

## Problem-Solver Mode

### Step 1: Problem Intake

Create a new problem case:

```bash
# From text
glitchhunter problem intake "STL files are not processed but GER files work"

# From file
glitchhunter problem intake -f problem.txt

# With custom title
glitchhunter problem intake "Description..." -t "My Problem"
```

**Tips:**
- Be specific about the problem
- Include expected behavior
- Mention affected components

### Step 2: Classification

GlitchHunter automatically classifies your problem:

```bash
glitchhunter problem classify prob_20260415_001
```

**Output includes:**
- Problem type (bug, performance, integration_gap, etc.)
- Confidence score
- Keywords found
- Affected components

### Step 3: Diagnosis

Get detailed diagnosis with root causes:

```bash
glitchhunter problem diagnose prob_20260415_001
```

**Diagnosis includes:**
- Root causes with confidence scores
- Contributing factors
- Data flows
- Uncertainties
- Recommended next steps

### Step 4: Decomposition

Break complex problems into manageable subproblems:

```bash
glitchhunter problem decompose prob_20260415_001
```

**Output:**
- List of subproblems
- Dependencies between them
- Execution order
- Estimated effort

### Step 5: Solution Planning

Generate multiple solution paths:

```bash
glitchhunter problem plan prob_20260415_001
```

**Plan includes:**
- Multiple solution paths per subproblem
- Scores (effectiveness, invasiveness, risk, effort)
- Implementation steps
- Quick-win identification

### Step 6: Stack Selection

Choose execution environment:

```bash
# Get recommendation
glitchhunter problem stack --recommend prob_20260415_001

# View all stacks
glitchhunter problem stack

# Compare
glitchhunter problem stack --compare
```

**Stacks:**
- **Stack A** (Standard): 8GB VRAM, suitable for most tasks
- **Stack B** (Enhanced): 24GB VRAM, required for dynamic analysis

### Step 7: Auto-Fix

Execute solutions:

```bash
# ALWAYS dry-run first!
glitchhunter problem fix prob_20260415_001 --dry-run

# Apply fixes
glitchhunter problem fix prob_20260415_001

# Skip validation (not recommended)
glitchhunter problem fix prob_20260415_001 --no-validate
```

### Step 8: Validation

Verify success:

```bash
# Goal validation (success criteria)
glitchhunter problem validate prob_20260415_001

# Intent validation (detect superficial fixes)
glitchhunter problem intent prob_20260415_001 -s "Implemented caching"
```

### Step 9: Rollback (If Needed)

Revert changes if something goes wrong:

```bash
glitchhunter problem rollback prob_20260415_001
```

---

## Bug-Hunting Mode

### Full Scan

```bash
glitchhunter analyze /path/to/project
```

### Incremental Scan

```bash
# Only changed files
glitchhunter analyze /path/to/project --incremental
```

### Security-Focused Scan

```bash
glitchhunter analyze /path/to/project --security-only
```

---

## TUI Guide

### Launch TUI

```bash
glitchhunter tui
```

### Keyboard Shortcuts

#### Main Menu
- `F1`: Help
- `F2`: Bug-Hunting Mode
- `F4`: Problem-Solver Mode
- `q`: Quit

#### Problem-Solver Screens
- `d`: Next step (Diagnosis → Decomposition → Plan)
- `s`: Show details
- `r`: Refresh
- `escape`: Back

#### DataTable Navigation
- Arrow keys: Navigate
- `Enter`: Select
- `Space`: Toggle

---

## API Reference

### Start API Server

```bash
glitchhunter api start
```

### Endpoints

#### Problems

```bash
# Create problem
curl -X POST http://localhost:8000/api/problems \
  -H "Content-Type: application/json" \
  -d '{"description": "Performance issue"}'

# List problems
curl http://localhost:8000/api/problems

# Get problem
curl http://localhost:8000/api/problems/prob_001

# Classify
curl -X POST http://localhost:8000/api/problems/prob_001/classify

# Get diagnosis
curl http://localhost:8000/api/problems/prob_001/diagnosis

# Create solution plan
curl -X POST http://localhost:8000/api/problems/prob_001/plan

# Execute auto-fix
curl -X POST http://localhost:8000/api/problems/prob_001/fix \
  -d '{"dry_run": true}'

# Validate
curl -X POST http://localhost:8000/api/problems/prob_001/validate
```

#### Analysis

```bash
# Start analysis
curl -X POST http://localhost:8000/api/analysis \
  -d '{"path": "/path/to/code"}'

# Get results
curl http://localhost:8000/api/analysis/latest
```

---

## Configuration

### config.yaml Location

`~/.glitchhunter/config.yaml` or project root

### Key Settings

```yaml
# Model Configuration
stack_a:
  models:
    primary:
      path: "/path/to/model.gguf"
      n_gpu_layers: 35
      n_threads: 8

# Problem-Solver
problem_solver:
  enabled: true
  auto_fix_dry_run: true  # Always dry-run by default
  validation_required: true

# Cache
cache:
  enabled: true
  symbol_graph_persist: true
  auto_invalidate: true

# Logging
logging:
  level: "INFO"
  file: "logs/glitchhunter.log"
```

---

## Troubleshooting

### Common Issues

#### "Model not found"

```bash
# Download models
python scripts/download_models.py

# Or update config.yaml with correct path
```

#### "Out of memory"

```bash
# Reduce context length
# Edit config.yaml:
models:
  primary:
    n_ctx: 2048  # Reduce from 4096

# Or use CPU-only mode
glitchhunter analyze --cpu-only
```

#### "Auto-fix failed"

```bash
# Check dry-run first
glitchhunter problem fix prob_001 --dry-run

# Review validation errors
glitchhunter problem validate prob_001

# Rollback if needed
glitchhunter problem rollback prob_001
```

#### "Classification confidence low"

```bash
# Provide more detailed description
glitchhunter problem intake "More specific description..."

# Or manually set type
# Edit .glitchhunter/problems/prob_001.json
```

---

## Best Practices

### Problem Intake

✅ **DO:**
- Be specific: "Startup takes 30 seconds" vs "It's slow"
- Include context: "After the recent update..."
- Mention affected components: "The API endpoint /users..."
- State expected behavior: "Should complete in <5 seconds"

❌ **DON'T:**
- Vague descriptions: "Something's broken"
- Multiple problems in one: Split into separate problems
- Assume knowledge: Provide context

### Auto-Fix Safety

✅ **DO:**
- Always dry-run first: `--dry-run`
- Review generated patches
- Run validation after fix
- Keep backups (automatic)
- Test in staging environment

❌ **DON'T:**
- Skip validation: `--no-validate`
- Apply without review
- Skip rollback if needed

### Stack Selection

✅ **DO:**
- Use Stack A for standard tasks
- Use Stack B for dynamic analysis
- Follow recommendations

### Workflow

**Recommended:**
1. Intake → 2. Classify → 3. Diagnose → 4. Decompose → 5. Plan → 6. Stack → 7. Fix (dry-run) → 8. Fix → 9. Validate

**Quick (for simple issues):**
1. Intake → 2. Plan → 3. Fix (dry-run) → 4. Fix

---

## Getting Help

- Documentation: `docs/`
- Examples: `examples/`
- Issues: GitHub Issues
- Discussions: GitHub Discussions

---

**GlitchHunter v2.0** - Finds problems. Fixes them safely. Learns from success.
