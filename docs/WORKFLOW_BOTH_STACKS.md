# GlitchHunter: Complete Workflow Documentation for Both Hardware Stacks

## Overview

GlitchHunter is an intelligent code analysis tool that uses **local open-source LLMs** (Qwen, Phi, DeepSeek) to not only find bugs and security vulnerabilities but **automatically and safely fix them**. The system automatically adapts to available hardware resources and uses different analysis stacks depending on GPU configuration.

## Hardware Stack Configuration

### Stack A: GTX 3060 (8GB VRAM)
- **Mode:** Sequential processing
- **Models:** Qwen3.5-9B + Phi-4-mini
- **Context:** 64k-128k tokens (TurboQuant optimized)
- **Security:** Security-Lite (OWASP Top 10 only)
- **Throughput:** ~50 LOC/minute
- **10k lines:** 10-18 minutes

### Stack B: RTX 3090 (24GB VRAM)
- **Mode:** Parallel processing
- **Models:** Qwen3.5-27B + DeepSeek-V3.2-Small
- **Context:** 100k-200k tokens
- **Security:** Full Security Shield (OWASP Top 10 + API Security + Attack Scenarios)
- **Throughput:** ~200 LOC/minute
- **10k lines:** 4-8 minutes

## Complete Workflow Architecture

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

## Phase 1: Ingestion - Repository Scanning & Understanding

### Purpose
Parse the repository structure, build comprehensive symbol graphs, and establish baseline understanding.

### Detailed Process

**1.1 Repository Scanning**
- **Tree-sitter AST Analysis:** Parse source files for Python, JavaScript/TypeScript, Go, Java
- **Symbol Extraction:** Extract functions, classes, variables, imports, exports
- **File Manifest Generation:** Create inventory of all files with metadata (size, language, complexity)

**1.2 Git History Analysis**
- **Git Churn Analysis:** Identify frequently changed files (hotspots)
- **Blame Integration:** Associate code sections with authors and timestamps
- **Commit Pattern Detection:** Identify patterns in bug introductions

**1.3 Symbol Graph Construction**
- **Node Creation:** Each symbol becomes a node with metadata
- **Edge Creation:** Define relationships (calls, imports, inheritance, dependencies)
- **Graph Optimization:** Prune irrelevant nodes, cluster related symbols

**1.4 Repository Mapping**
- **Architecture Detection:** Identify project structure (monolith, microservices, libraries)
- **Dependency Analysis:** Map internal and external dependencies
- **Entry Point Identification:** Locate main files, configuration files, test suites

### Stack-Specific Differences
- **Stack A:** Sequential scanning, limited to 1000 files per batch
- **Stack B:** Parallel scanning, processes entire repository simultaneously

### Output
- Symbol graph with 1000-5000+ nodes (depending on repository size)
- Repository manifest with file categorization
- Complexity hotspots and churn analysis
- Dependency graph

## Phase 2: Shield - Bug & Security Vulnerability Detection

### Purpose
Identify potential bugs and security vulnerabilities using multi-layered analysis.

### Detailed Process

**2.1 Semgrep Security Scan**
- **OWASP Top 10 2025 Rules:** SQL injection, XSS, CSRF, broken authentication, etc.
- **Custom Rules:** Project-specific security patterns
- **Language-Specific Rules:** Python, JavaScript, Java, Go vulnerabilities

**2.2 AST-Based Pattern Detection**
- **Control Flow Analysis:** Identify unreachable code, infinite loops
- **Data Flow Analysis:** Track variable usage, identify uninitialized variables
- **Type Inference:** Detect type mismatches, incorrect API usage

**2.3 Complexity Analysis**
- **Cyclomatic Complexity:** Functions exceeding threshold (15 for Stack A, 25 for Stack B)
- **Cognitive Complexity:** Hard-to-understand code sections
- **Nesting Depth:** Deeply nested control structures

**2.4 Git-Based Risk Assessment**
- **Hotspot Correlation:** Link complexity with frequent changes
- **Author Experience:** Associate code with author experience level
- **Temporal Patterns:** Detect recently introduced high-risk code

**2.5 Hypothesis Generation**
- For each potential bug, generate 3-5 hypotheses about root cause
- Each hypothesis includes:
  - Causal explanation
  - Confidence score (0.0-1.0)
  - Evidence references
  - Suggested fix approach

### Stack-Specific Differences
- **Stack A:** Security-Lite (OWASP Top 10 only)
- **Stack B:** Full Security Shield (OWASP Top 10 + API Security + Attack Scenarios + Business Logic)

### Output
- List of prioritized bug candidates (50-500 depending on repository size)
- Each candidate with severity, confidence, location, hypotheses
- Security vulnerability report with CWE classification

## Phase 3: Patch Loop - Secure Fix Generation with 4 Safety Gates

### Purpose
Generate, validate, and apply fixes for identified bugs with guaranteed safety.

### Detailed Process

**3.1 Regression Test Generation (Fail2Pass Principle)**
- Generate 3-5 edge-case tests per bug
- Tests MUST fail before patch application
- Tests validate both bug existence and fix correctness

**3.2 Safety Gate 1: Pre-Apply Validation**
```
┌─────────────────────────────────────────────────────────┐
│                   SAFETY GATE 1                          │
├─────────────────────────────────────────────────────────┤
│ • Syntax Check: Valid syntax in target language         │
│ • Linter Integration: Ruff, Pylint, ESLint, Clippy      │
│ • Semantic Diff: Tree-sitter comparison                 │
│ • Policy Checks:                                        │
│   - Max 3 files changed                                 │
│   - Max 160 lines changed                               │
│   - No new dependencies                                 │
│   - No forbidden imports (os.system, eval, exec)       │
└─────────────────────────────────────────────────────────┘
```

**3.3 Safety Gate 2: Sandbox Execution**
- **Docker Isolation:** Each patch tested in fresh container
- **Git Worktree:** Apply patch to isolated copy of repository
- **Test Suite Execution:** Run existing tests + generated regression tests
- **Network Disabled:** Prevent external calls
- **Resource Limits:** CPU, memory, time constraints

**3.4 Safety Gate 3: Post-Apply Verification**
- **LLM Verifier:** Independent model evaluates patch (95% confidence threshold)
- **Graph Comparison:** Compare before/after Data-Flow and Control-Flow graphs
- **Breaking Changes Detection:** Ensure no API contract violations
- **Behavior Preservation:** Verify functional equivalence

**3.5 Safety Gate 4: Coverage Check**
- **Coverage Measurement:** Line, branch, function coverage
- **Regression Detection:** No coverage loss > 1% tolerance
- **New Coverage:** Ensure fix adds test coverage for affected code

**3.6 Decision Logic**
- **ACCEPT:** All 4 gates passed
- **RETRY:** Failed gate with potential for improvement (max 5 iterations)
- **ESCALATE:** Failed after 2 iterations without progress → Phase 4 Escalation

### Stack-Specific Differences
- **Stack A:** Sequential patch evaluation, 1 patch at a time
- **Stack B:** Parallel patch evaluation, up to 4 patches simultaneously
- **Stack A:** 3 safety gates (skips coverage check if not configured)
- **Stack B:** All 4 safety gates with comprehensive validation

### Output
- Verified patches ready for application
- Patch metadata (iteration count, gate results, performance metrics)
- Escalation triggers for complex bugs

## Phase 4: Finalizer + Escalation Hierarchy

### Purpose
Apply successful fixes, learn from patterns, and handle complex bugs through escalation.

### Detailed Process

**4.1 Rule Learning**
- **Pattern Extraction:** Analyze successful patches for common patterns
- **Semgrep Rule Generation:** Create new detection rules
- **Rule Categorization:** Security, correctness, performance, best practice
- **Generalization:** Replace specific values with metavariables ($STRING, $NUMBER)

**4.2 Patch Merging**
- **Git Worktree Isolation:** Apply patches without affecting main branch
- **Auto-Branch Creation:** `glitchhunter/fix_BUG-ID_TIMESTAMP`
- **Detailed Commit Messages:** Include bug description, root cause, fix approach
- **Bug ID Tags:** Track fixes for auditing and reporting

**4.3 Report Generation**
- **JSON Report:** Machine-readable for integration with CI/CD
- **Markdown Report:** Human-readable with executive summary
- **Session Summary:** Overall metrics (bugs found, fixed, escalated)
- **Recommendations:** Architectural improvements, test coverage gaps

### Escalation Hierarchy (4 Levels)

**Level 1: Context Explosion**
```
Trigger: Patch loop iteration >= 5 AND no successful fix
Action: Expand context to 160k+ tokens
Components:
  • Full Repomix XML of relevant subsystem
  • Git-Blame + last 5 commits of affected files
  • Data-Flow Graph + Control-Flow Graph as text diagrams
  • API documentation and similar historical bugs
Goal: Provide maximum context for LLM to understand complex dependencies
```

**Level 2: Bug Decomposition**
```
Trigger: Context explosion fails to produce fix
Action: Decompose complex bug into 2-4 independent sub-bugs
Strategies:
  • Causal: Break by cause-effect chains
  • Component: Split by affected modules
  • Symptom: Separate observable symptoms
Process: Each sub-bug gets own mini patch loop
Goal: Solve complexity through divide-and-conquer
```

**Level 3: Multi-Model Ensemble**
```
Trigger: Bug decomposition fails or produces conflicting fixes
Action: Parallel analysis with 3+ different models
Models:
  • Primary: Qwen3.5-27B/35B (analytical)
  • Secondary: DeepSeek-V3.2-32B (creative)
  • Verifier: Phi-4-mini (conservative)
Voting Strategies:
  • Unanimous: All models agree
  • Majority: 2/3 models agree
  • Plurality: Highest confidence wins
  • Weighted: Confidence-weighted combination
Goal: Leverage model diversity for better solutions
```

**Level 4: Human-in-the-Loop**
```
Trigger: Ensemble fails or produces low-confidence fixes
Action: Generate comprehensive human report
Components:
  • Exact bug + root cause analysis
  • Why previous patches failed
  • 3 concrete fix suggestions with pros/cons
  • Ready-to-use regression tests
  • Optional: Draft PR with all information
Goal: Provide human developers with everything needed for manual fix
```

### Stack-Specific Differences
- **Stack A:** Limited to Level 2 escalation (Context Explosion + Bug Decomposition)
- **Stack B:** Full 4-level escalation hierarchy
- **Stack A:** Single-model analysis throughout
- **Stack B:** Multi-model capabilities from Level 3

### Output
- Applied fixes in separate git branches
- Learned Semgrep rules for future detection
- Comprehensive reports (JSON + Markdown)
- Escalation reports for manual intervention

## State Machine Implementation

### LangGraph State Machine States
1. **INGESTION:** Repository parsing and symbol graph building
2. **SHIELD:** Pre-filtering and security scanning
3. **HYPOTHESIS:** Generate 3-5 hypotheses per candidate
4. **ANALYZER:** Test hypotheses causally
5. **OBSERVER:** Evaluate evidence and confidence
6. **LLIFT_PRIORITIZER:** Prioritize candidates by severity/confidence
7. **PATCH_LOOP:** Iterative patch generation and verification
8. **FINALIZER:** Report generation and rule learning

### Conditional Transitions
- **Success Flow:** INGESTION → SHIELD → HYPOTHESIS → ANALYZER → OBSERVER → LLIFT_PRIORITIZER → PATCH_LOOP → FINALIZER
- **Empty Results:** Skip to FINALIZER if no candidates/hypotheses
- **Escalation Flow:** PATCH_LOOP → HYPOTHESIS (re-hypothesize) → [Escalation Hierarchy]
- **Error Handling:** Any state → END with error reporting

## Safety Guarantees & Regression-Proof Principle

### 4-Fold Safety Gates
1. **Gate 1: Pre-Apply Validation** - Ensures patch is syntactically and semantically valid
2. **Gate 2: Sandbox Execution** - Ensures patch doesn't break existing functionality
3. **Gate 3: Post-Apply Verification** - Ensures patch actually fixes the bug
4. **Gate 4: Coverage Check** - Ensures no test coverage regression

### Fail2Pass Principle
- Every bug fix must include tests that:
  1. Fail before the fix (proving bug existence)
  2. Pass after the fix (proving bug resolution)
- Generated tests cover edge cases and boundary conditions
- Tests are added to the repository's test suite

### Performance Metrics

| Metric | Stack A (GTX 3060) | Stack B (RTX 3090) |
|--------|-------------------|-------------------|
| Lines per Minute | ~50 | ~200 |
| Analysis Time (10k lines) | 10-18 min | 4-8 min |
| Patch Loop per Candidate | 3-6 min | 1-3 min |
| Filtering Rate | 85% | 95% |
| False Positive Rate | < 15% | < 5% |
| Fix Success Rate | 70% | 85% |

## Configuration & Customization

### Hardware Detection
- Automatic detection of GPU model and VRAM
- Fallback to CPU-only mode if no GPU available
- Dynamic model loading based on available resources

### Feature Toggles
```yaml
features:
  parallel_inference: false  # Stack B only
  deep_security_scan: false  # Stack B only  
  multi_model_consensus: false  # Stack B only
  ast_analysis: true  # Both stacks
  complexity_check: true  # Both stacks
  basic_security: true  # Both stacks
  patch_generation: true  # Both stacks
  sandbox_execution: true  # Both stacks
```

### Language Support
- **Primary:** Python, JavaScript, TypeScript
- **Secondary:** Go, Java, Rust
- **Limited:** C++, C#, PHP, Ruby

## Integration Points

### CI/CD Integration
- JSON reports compatible with GitHub Actions, GitLab CI, Jenkins
- SARIF output for security scanning integration
- JUnit XML for test results

### API Endpoints
- `/api/analyze`: Full repository analysis
- `/api/fix`: Individual bug fixing
- `/api/status`: System status and metrics
- `/api/report`: Generate reports for completed analyses

### MCP (Model Context Protocol) Integration
- **SocratiCode Client:** Semantic code search and context retrieval
- **Fallback Management:** Graceful degradation when MCP unavailable
- **Context Enrichment:** Augment LLM prompts with relevant code snippets

## Troubleshooting & Debugging

### Common Issues
1. **GPU Memory Exhaustion:** Switch to smaller models or CPU mode
2. **Docker Permission Errors:** Configure Docker socket permissions
3. **Network Timeouts:** Adjust timeout settings in config.yaml
4. **Model Loading Failures:** Verify GGUF file paths and permissions

### Debug Mode
```bash
python -m src.main analyze /path/to/repo --config config.yaml --debug
```

### Log Files
- `logs/glitchhunter.log`: Main application log
- `logs/stack_a.log` / `logs/stack_b.log`: Stack-specific logs
- `logs/patch_loop_*.log`: Individual patch loop executions

## Future Enhancements

### Planned Features
1. **Multi-Repository Analysis:** Cross-project dependency analysis
2. **Live Monitoring:** Real-time code change detection and analysis
3. **Team Collaboration:** Shared rule repositories and findings
4. **Custom Model Training:** Fine-tune models on organization-specific code

### Research Directions
1. **Causal Inference:** Better root cause identification
2. **Architecture Reconstruction:** Automatic architecture diagram generation
3. **Technical Debt Quantification:** Measure and prioritize technical debt
4. **Automated Refactoring:** Beyond bug fixes to code improvement

## Conclusion

GlitchHunter provides a comprehensive, safe, and scalable solution for automated bug detection and fixing. By adapting to available hardware resources through Stack A and Stack B configurations, it delivers practical value across a wide range of development environments. The 4-fold safety gates and escalation hierarchy ensure reliable operation while the regression-proof principle guarantees that fixes don't introduce new bugs.

The system represents a significant advancement in automated code maintenance, bringing enterprise-grade bug fixing capabilities to individual developers and small teams through efficient use of local open-source LLMs.