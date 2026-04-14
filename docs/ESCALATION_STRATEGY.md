# Escalation-First Fixing Strategy

**Version:** 2.0
**Date:** April 13, 2026
**Status:** Architecture Specification

---

## Table of Contents

1. [Overview](#1-overview)
2. [Escalation Level 1: Context Explosion](#2-escalation-level-1-context-explosion)
3. [Escalation Level 2: Bug Decomposition](#3-escalation-level-2-bug-decomposition)
4. [Escalation Level 3: Multi-Model Ensemble](#4-escalation-level-3-multi-model-ensemble)
5. [Escalation Level 4: Human-in-the-Loop](#5-escalation-level-4-human-in-the-loop)
6. [Configuration Reference](#6-configuration-reference)

---

## 1. Overview

### 1.1 Problem Analysis

When the automated fixing system fails to fix a bug after 5 loops, it's typically due to one of these reasons:

| Reason | Description | Frequency |
|--------|-------------|-----------|
| **Bug Too Complex** | Requires refactoring instead of minimal patch | ~35% |
| **Insufficient Context** | Even with tiered context, critical information was missing | ~25% |
| **Incomplete Tests** | Tests don't cover the bug or bug is "silent" | ~20% |
| **Shallow Understanding** | Model doesn't deeply understand the root cause | ~15% |
| **Architecture Mismatch** | Fix requires architectural changes | ~5% |

### 1.2 Solution: Intelligent Escalation Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ESCALATION-FIRST FIXING HIERARCHY                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Trigger: Loop iteration >= 5 AND no successful fix                         │
│          │                                                                   │
│          ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  ESCALATION LEVEL 1: Context Explosion                               │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │ • Activate escalation_ctx: 160000 tokens                     │    │   │
│  │  │ • Full Repomix XML of entire relevant subsystem              │    │   │
│  │  │ • Add Git-Blame + last 5 commits of affected files           │    │   │
│  │  │ • Add Data-Flow Graph + Control-Flow Graph as text diagrams  │    │   │
│  │  │ • Prompt: "Think bigger - suggest minimal fix or refactoring"│    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  │          │                                                            │   │
│  │          ▼ Success?                                                   │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │  YES → Apply patch, exit escalation                          │    │   │
│  │  │  NO  → Continue to Level 2                                   │    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│          │                                                                   │
│          ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  ESCALATION LEVEL 2: Bug Decomposition                               │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │ • Agent decomposes bug into 2-4 smaller independent sub-bugs │    │   │
│  │  │ • Each sub-bug treated as separate mini-loop                 │    │   │
│  │  │ • Own regression tests per sub-bug                           │    │   │
│  │  │ • Patches applied sequentially and tested in isolation       │    │   │
│  │  │ • Example: "Race Condition in Auth + DB" →                   │    │   │
│  │  │   Sub-bug 1: Missing lock in auth module                     │    │   │
│  │  │   Sub-bug 2: Non-atomic DB write                             │    │   │
│  │  │   Sub-bug 3: No retry logic                                  │    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  │          │                                                            │   │
│  │          ▼ All sub-bugs fixed?                                        │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │  YES → Merge all patches, exit escalation                    │    │   │
│  │  │  NO  → Continue to Level 3                                   │    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│          │                                                                   │
│          ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  ESCALATION LEVEL 3: Multi-Model Ensemble                            │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │ • Start second Analyzer in parallel                          │    │   │
│  │  │   - Primary: Qwen3.5-27B (or 35B)                            │    │   │
│  │  │   - Secondary: DeepSeek-V3.2-32B (or creative model)         │    │   │
│  │  │ • Both suggest patches independently                         │    │   │
│  │  │ • Verifier chooses best or combines ("ensemble voting")      │    │   │
│  │  │ • Cost on 3090: Nearly free (Verifier runs in parallel)      │    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  │          │                                                            │   │
│  │          ▼ Ensemble agrees?                                           │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │  YES → Apply best patch, exit escalation                     │    │   │
│  │  │  NO  → Continue to Level 4                                   │    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│          │                                                                   │
│          ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  ESCALATION LEVEL 4: Human-in-the-Loop + Report                      │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │ • Sentinel stops cleanly                                     │    │   │
│  │  │ • Generate extremely detailed report:                        │    │   │
│  │  │   - Exact bug + root cause (with graph snippets)             │    │   │
│  │  │   - Why previous patches failed                              │    │   │
│  │  │   - 3 concrete fix suggestions with pros/cons                │    │   │
│  │  │   - Ready-to-use regression tests                            │    │   │
│  │  │ • Optional: Generate Draft-PR with all info                  │    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  │          │                                                            │   │
│  │          ▼ Human reviews and applies fix manually                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Output: FixedBug | HumanReport                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 State Machine Integration

```python
# src/escalation/escalation_state.py

from typing import TypedDict, List, Optional, Literal
from typing_extensions import NotRequired


class EscalationState(TypedDict):
    """State machine state for escalation hierarchy."""

    # Trigger information
    original_bug: dict
    failed_patches: List[dict]
    test_results: List[dict]
    iteration_count: int

    # Current escalation level
    current_level: int  # 1-4
    level_results: NotRequired[List[dict]]

    # Level 1: Context Explosion
    context_explosion_result: NotRequired[dict]
    expanded_context: NotRequired[dict]

    # Level 2: Bug Decomposition
    decomposition_result: NotRequired[dict]
    sub_bugs: NotRequired[List[dict]]
    sub_bug_fixes: NotRequired[List[dict]]

    # Level 3: Multi-Model Ensemble
    ensemble_result: NotRequired[dict]
    primary_patch: NotRequired[dict]
    secondary_patch: NotRequired[dict]
    voting_result: NotRequired[dict]

    # Level 4: Human-in-the-Loop
    human_report: NotRequired[dict]
    draft_pr: NotRequired[dict]

    # Final decision
    success: bool
    final_patch: NotRequired[dict]
    escalation_reason: NotRequired[str]
```

---

## 2. Escalation Level 1: Context Explosion

### 2.1 Implementation

**Goal:** Provide the model with maximum context to understand the full scope of the bug.

```python
# src/escalation/context_explosion.py

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import asyncio


@dataclass
class ExpandedContext:
    """Expanded context for escalation level 1."""
    repomix_xml: str
    git_blame: Dict[str, str]
    commits: Dict[str, List[Dict]]
    dfg_diagram: str
    cfg_diagram: str
    api_docs: str
    similar_bugs: str


@dataclass
class ContextExplosionResult:
    """Result of context explosion escalation."""
    success: bool
    patch: Optional[Dict]
    context_size: int
    reasoning: str


class ContextExplosion:
    """Escalation Level 1: Maximum context provision."""

    def __init__(self, config: Dict[str, Any], llm_client: Any):
        self.config = config
        self.llm = llm_client
        self.context_window = config.get(
            "escalation_policy", {}
        ).get("level_1", {}).get("context_window", 160000)

    async def execute(
        self,
        bug: Dict[str, Any],
        failed_patches: List[Dict],
        test_results: List[Dict]
    ) -> ContextExplosionResult:
        """
        Escalation Level 1: Context Explosion

        Activates 160k context window with full subsystem context.
        """
        # 1. Gather full context
        context = await self._gather_expanded_context(bug)

        # 2. Build prompt with context explosion
        prompt = self._build_context_explosion_prompt(
            bug=bug,
            context=context,
            failed_patches=failed_patches,
            test_results=test_results
        )

        # 3. Generate fix with expanded context
        response = await self.llm.generate(
            prompt=prompt,
            max_tokens=8000,
            temperature=0.3  # Slightly higher for creativity
        )

        # 4. Parse and validate
        patch = self._parse_patch(response)

        return ContextExplosionResult(
            success=patch is not None,
            patch=patch,
            context_size=len(context.repomix_xml),
            reasoning=self._extract_reasoning(response)
        )

    async def _gather_expanded_context(self, bug: Dict) -> ExpandedContext:
        """Gathers expanded context for escalation level 1."""
        context = ExpandedContext(
            repomix_xml="",
            git_blame={},
            commits={},
            dfg_diagram="",
            cfg_diagram="",
            api_docs="",
            similar_bugs=""
        )

        # 1. Full Repomix XML of relevant subsystem
        affected_files = self._find_all_affected_files(bug)
        context.repomix_xml = await self._generate_repomix(affected_files)

        # 2. Git blame + last 5 commits
        for file in affected_files:
            context.git_blame[file] = await self._get_git_blame(file)
            context.commits[file] = await self._get_last_commits(file, count=5)

        # 3. Data-Flow Graph as text diagram
        context.dfg_diagram = self._render_dfg_as_text(bug.get("location"))

        # 4. Control-Flow Graph as text diagram
        context.cfg_diagram = self._render_cfg_as_text(bug.get("location"))

        # 5. Related API documentation
        context.api_docs = await self._find_related_api_docs(bug)

        # 6. Similar bugs from issue tracker
        context.similar_bugs = await self._find_similar_bugs(bug)

        return context

    def _build_context_explosion_prompt(
        self,
        bug: Dict,
        context: ExpandedContext,
        failed_patches: List[Dict],
        test_results: List[Dict]
    ) -> str:
        """Builds the context explosion prompt."""
        return f"""
# Context Explosion - Escalation Level 1

## Bug Description
{bug.get('description', 'N/A')}

## Failed Attempts ({len(failed_patches)} patches)
{self._format_failed_patches(failed_patches, test_results)}

## Expanded Context ({self.context_window} tokens)

### 1. Full Subsystem Structure (Repomix XML)
{context.repomix_xml[:100000]}  # Truncated for brevity

### 2. Git History (Blame + Commits)
{self._format_git_history(context.git_blame, context.commits)}

### 3. Data-Flow Graph
```
{context.dfg_diagram}
```

### 4. Control-Flow Graph
```
{context.cfg_diagram}
```

### 5. Related API Documentation
{context.api_docs}

### 6. Similar Historical Bugs
{context.similar_bugs}

## Task

You now have the FULL context of this bug. Previous attempts failed because:
{self._analyze_failures(failed_patches)}

**Think bigger now.** Suggest either:
1. A minimal but effective fix that addresses the root cause
2. A small refactoring that makes the fix obvious
3. A different approach entirely that previous attempts missed

Constraints:
- Still prefer minimal changes (<160 lines)
- But you may touch more files if necessary
- Explain your reasoning clearly

Generate a patch that fixes this bug WITHOUT introducing new bugs.

## Response Format

```diff
<your patch in unified diff format>
```

**Reasoning:** <explain why this fix works and why previous attempts failed>
"""

    async def _generate_repomix(self, files: List[str]) -> str:
        """Generates Repomix XML for given files."""
        # Call Repomix CLI or use local implementation
        import subprocess

        result = subprocess.run(
            ["repomix", "--format", "xml", "--output", "-", *files],
            capture_output=True,
            text=True
        )

        return result.stdout

    async def _get_git_blame(self, file_path: str) -> str:
        """Gets git blame for a file."""
        import subprocess

        result = subprocess.run(
            ["git", "blame", file_path],
            capture_output=True,
            text=True
        )

        return result.stdout

    async def _get_last_commits(self, file_path: str, count: int = 5) -> List[Dict]:
        """Gets last N commits for a file."""
        import subprocess
        import json

        result = subprocess.run(
            [
                "git", "log", "-n", str(count),
                "--format=json", "--", file_path
            ],
            capture_output=True,
            text=True
        )

        commits = []
        for line in result.stdout.strip().split('\n'):
            if line:
                commits.append(json.loads(line))

        return commits

    def _render_dfg_as_text(self, location: Dict) -> str:
        """Renders Data-Flow Graph as ASCII diagram."""
        # Use NetworkX to generate ASCII representation
        import networkx as nx

        dfg = location.get("data_flow_graph")
        if dfg is None:
            return "No DFG available"

        # Generate ASCII art using networkx drawing
        try:
            import matplotlib.pyplot as plt
            pos = nx.spring_layout(dfg)
            # Convert to text representation
            return nx.generate_graphml(dfg).decode('utf-8')[:5000]
        except Exception:
            return str(list(dfg.edges()))[:5000]

    def _render_cfg_as_text(self, location: Dict) -> str:
        """Renders Control-Flow Graph as ASCII diagram."""
        # Similar to DFG rendering
        pass

    def _find_all_affected_files(self, bug: Dict) -> List[str]:
        """Finds all files affected by the bug."""
        affected = [bug.get("file_path")]

        # Add files from call graph
        call_graph = bug.get("call_graph", {})
        for caller, callees in call_graph.items():
            for callee in callees:
                if callee.get("file_path"):
                    affected.append(callee["file_path"])

        # Add files from data flow
        data_flow = bug.get("data_flow", {})
        for node in data_flow.get("nodes", []):
            if node.get("file_path"):
                affected.append(node["file_path"])

        return list(set(affected))
```

### 2.2 Configuration

```yaml
# config.yaml
escalation_policy:
  level_1:
    enabled: true
    context_window: 160000  # tokens
    include_repomix: true
    include_git_blame: true
    include_git_commits: 5
    include_dfg_diagram: true
    include_cfg_diagram: true
    include_api_docs: true
    include_similar_bugs: true
    temperature: 0.3
    max_tokens: 8000
```

---

## 3. Escalation Level 2: Bug Decomposition

### 3.1 Algorithm

**Goal:** Break complex bugs into smaller, independently fixable sub-bugs.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BUG DECOMPOSITION ALGORITHM                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Input: Complex Bug                                                          │
│          │                                                                   │
│          ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  1. Analyze Bug Complexity                                           │   │
│  │     • Count affected files                                           │   │
│  │     • Count data flows                                               │   │
│  │     • Count control flows                                            │   │
│  │     • Detect concurrent access                                       │   │
│  │     • Identify state dependencies                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│          │                                                                   │
│          ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  2. LLM-Based Decomposition                                          │   │
│  │     • Prompt: "Decompose this bug into 2-4 independent sub-bugs"     │   │
│  │     • Each sub-bug must have:                                        │   │
│  │       - Clear description                                            │   │
│  │       - Specific location                                            │   │
│  │       - Testable hypothesis                                          │   │
│  │       - Independent fix path                                         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│          │                                                                   │
│          ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  3. Validate Independence                                            │   │
│  │     • Build dependency graph between sub-bugs                        │   │
│  │     • Ensure minimal coupling                                        │   │
│  │     • Identify fix order dependencies                                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│          │                                                                   │
│          ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  4. Topological Sort                                                 │   │
│  │     • Order sub-bugs for sequential fixing                           │   │
│  │     • Independent bugs first                                         │   │
│  │     • Dependent bugs after their dependencies                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│          │                                                                   │
│          ▼                                                                   │
│  Output: OrderedSubBugs (List[SubBug])                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Implementation

```python
# src/escalation/bug_decomposer.py

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import networkx as nx


@dataclass
class SubBug:
    """Represents a decomposed sub-bug."""
    id: str
    description: str
    location: Dict[str, Any]
    hypothesis: str
    test: str
    dependencies: List[str]  # IDs of dependent sub-bugs
    fix_order: int


@dataclass
class BugDecomposition:
    """Result of bug decomposition."""
    original_bug: Dict
    sub_bugs: List[SubBug]
    independence_graph: nx.Graph
    fix_order: List[str]


class BugDecomposer:
    """Decomposes complex bugs into smaller sub-bugs."""

    def __init__(self, llm_client: Any, data_flow_graph: nx.DiGraph):
        self.llm = llm_client
        self.dfg = data_flow_graph

    async def decompose(self, bug: Dict[str, Any]) -> BugDecomposition:
        """
        Decomposes a complex bug into 2-4 independent sub-bugs.
        """
        # 1. Analyze bug complexity
        complexity = self._analyze_complexity(bug)

        # 2. Use LLM to identify decomposition
        decomposition_prompt = self._build_decomposition_prompt(
            bug, complexity
        )
        response = await self.llm.generate(
            prompt=decomposition_prompt,
            max_tokens=4000,
            temperature=0.2
        )

        # 3. Parse sub-bugs
        sub_bugs = self._parse_sub_bugs(response)

        # 4. Validate independence
        independence_graph = self._check_independence(sub_bugs)

        # 5. Order sub-bugs for sequential fixing
        fix_order = self._topological_sort(sub_bugs, independence_graph)

        # Apply fix order to sub-bugs
        for i, bug_id in enumerate(fix_order):
            sub_bug = next(b for b in sub_bugs if b.id == bug_id)
            sub_bug.fix_order = i

        return BugDecomposition(
            original_bug=bug,
            sub_bugs=sub_bugs,
            independence_graph=independence_graph,
            fix_order=fix_order
        )

    def _analyze_complexity(self, bug: Dict) -> Dict:
        """Analyzes bug complexity metrics."""
        return {
            'affected_files': len(bug.get('affected_files', [])),
            'data_flow_count': self.dfg.number_of_edges(),
            'control_flow_count': bug.get('control_flow_count', 0),
            'has_concurrent_access': bug.get('has_concurrent_access', False),
            'state_dependencies': bug.get('state_dependencies', [])
        }

    def _build_decomposition_prompt(
        self,
        bug: Dict,
        complexity: Dict
    ) -> str:
        """Builds the bug decomposition prompt."""
        return f"""
# Bug Decomposition - Escalation Level 2

## Original Bug
{bug.get('description', 'N/A')}

## Complexity Analysis
- Files involved: {complexity['affected_files']}
- Data flows: {complexity['data_flow_count']}
- Control flows: {complexity['control_flow_count']}
- Concurrent access: {complexity['has_concurrent_access']}
- State dependencies: {len(complexity['state_dependencies'])}

## Task

This bug is too complex to fix in a single patch. Decompose it into
2-4 SMALLER, INDEPENDENT sub-bugs that can be fixed separately.

For each sub-bug, provide:
1. **ID:** Short identifier (e.g., "SUB-1", "SUB-2")
2. **Description:** What specific aspect of the bug does this address?
3. **Location:** Which file(s) and line(s)?
4. **Hypothesis:** What's the root cause of this sub-bug?
5. **Test:** What test would verify this sub-bug is fixed?
6. **Dependencies:** Does fixing this require another sub-bug to be fixed first?

Example decomposition for "Race Condition in Auth + DB":

### Sub-bug SUB-1: Missing Lock in Auth Module
- **ID:** SUB-1
- **Description:** Auth token update is not atomic
- **Location:** src/auth/token_manager.py:45-67
- **Hypothesis:** Two concurrent requests can overwrite each other's token
- **Test:** Concurrent token update test with 100 threads
- **Dependencies:** None

### Sub-bug SUB-2: Non-Atomic DB Write
- **ID:** SUB-2
- **Description:** User session write is not transactional
- **Location:** src/db/session_store.py:123-145
- **Hypothesis:** Partial writes can leave session in inconsistent state
- **Test:** Transaction rollback test with forced failure
- **Dependencies:** None

### Sub-bug SUB-3: No Retry Logic
- **ID:** SUB-3
- **Description:** Failed auth updates are not retried
- **Location:** src/auth/auth_service.py:89-102
- **Hypothesis:** Transient failures cause permanent auth failures
- **Test:** Retry test with simulated transient failures
- **Dependencies:** SUB-1, SUB-2

Now decompose the actual bug:
"""

    def _parse_sub_bugs(self, response: str) -> List[SubBug]:
        """Parses sub-bugs from LLM response."""
        import re

        sub_bugs = []
        pattern = r'###\s*Sub-bug\s*(\w+):?\s*(.+?)(?=###|$)'

        for match in re.finditer(pattern, response, re.DOTALL):
            bug_id = match.group(1).strip()
            content = match.group(2).strip()

            # Extract fields
            description = self._extract_field(content, 'Description')
            location = self._extract_field(content, 'Location')
            hypothesis = self._extract_field(content, 'Hypothesis')
            test = self._extract_field(content, 'Test')
            dependencies = self._extract_field(content, 'Dependencies')

            sub_bugs.append(SubBug(
                id=bug_id,
                description=description,
                location=self._parse_location(location),
                hypothesis=hypothesis,
                test=test,
                dependencies=self._parse_dependencies(dependencies),
                fix_order=0
            ))

        return sub_bugs

    def _check_independence(self, sub_bugs: List[SubBug]) -> nx.Graph:
        """Checks independence between sub-bugs."""
        graph = nx.Graph()

        for i, bug in enumerate(sub_bugs):
            graph.add_node(bug.id, bug=bug)

        # Add edges for dependencies
        for bug in sub_bugs:
            for dep_id in bug.dependencies:
                if dep_id in [b.id for b in sub_bugs]:
                    graph.add_edge(bug.id, dep_id, type='dependency')

        return graph

    def _topological_sort(
        self,
        sub_bugs: List[SubBug],
        independence_graph: nx.Graph
    ) -> List[str]:
        """Orders sub-bugs for sequential fixing."""
        try:
            return list(nx.topological_sort(independence_graph))
        except nx.NetworkXUnfeasible:
            # Cycle detected - return bugs with no dependencies first
            independent = [
                b.id for b in sub_bugs if len(b.dependencies) == 0
            ]
            dependent = [
                b.id for b in sub_bugs if len(b.dependencies) > 0
            ]
            return independent + dependent
```

### 3.3 Configuration

```yaml
# config.yaml
escalation_policy:
  level_2:
    enabled: true
    max_sub_bugs: 4
    min_sub_bugs: 2
    require_independence: true
    sequential_fix: true
    parallel_test: true  # Tests can run in parallel
    temperature: 0.2
    max_tokens: 4000
```

---

## 4. Escalation Level 3: Multi-Model Ensemble

### 4.1 Implementation

**Goal:** Leverage multiple models for diverse perspectives on the same bug.

```python
# src/escalation/ensemble_coordinator.py

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import asyncio


@dataclass
class VotingResult:
    """Result of ensemble voting."""
    winner: str  # 'primary', 'secondary', 'combined'
    confidence: float
    reasoning: str


@dataclass
class EnsembleResult:
    """Result of multi-model ensemble."""
    success: bool
    patch: Optional[Dict]
    primary_patch: Optional[Dict]
    secondary_patch: Optional[Dict]
    voting_result: VotingResult
    primary_score: float
    secondary_score: float


class EnsembleCoordinator:
    """Coordinates multi-model ensemble for complex bug fixes."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.primary_llm = self._create_llm_client(
            config.get("escalation_policy", {}).get(
                "level_3", {}
            ).get("primary_model", "qwen3.5-27b")
        )
        self.secondary_llm = self._create_llm_client(
            config.get("escalation_policy", {}).get(
                "level_3", {}
            ).get("secondary_model", "deepseek-v3.2-32b")
        )
        self.verifier_llm = self._create_llm_client(
            config.get("escalation_policy", {}).get(
                "level_3", {}
            ).get("verifier_model", "phi-4-mini")
        )

    async def ensemble_fix(
        self,
        bug: Dict[str, Any],
        context: Dict[str, Any]
    ) -> EnsembleResult:
        """
        Escalation Level 3: Multi-Model Ensemble

        Runs two models in parallel and uses voting to select best patch.
        """
        # 1. Build fix prompt
        fix_prompt = self._build_fix_prompt(bug, context)

        # 2. Run both models in parallel
        primary_task = self.primary_llm.generate(
            prompt=fix_prompt,
            max_tokens=4000,
            temperature=self.config.get(
                "escalation_policy", {}
            ).get("level_3", {}).get("primary_temperature", 0.3)
        )
        secondary_task = self.secondary_llm.generate(
            prompt=fix_prompt,
            max_tokens=4000,
            temperature=self.config.get(
                "escalation_policy", {}
            ).get("level_3", {}).get("secondary_temperature", 0.4)
        )

        # 3. Wait for both responses
        primary_response, secondary_response = await asyncio.gather(
            primary_task, secondary_task
        )

        # 4. Parse patches
        primary_patch = self._parse_patch(primary_response)
        secondary_patch = self._parse_patch(secondary_response)

        # 5. Verifier evaluates both patches
        primary_eval = await self.verifier_llm.evaluate(
            prompt=self._build_evaluation_prompt(bug, primary_patch, context),
            patch=primary_patch
        )
        secondary_eval = await self.verifier_llm.evaluate(
            prompt=self._build_evaluation_prompt(bug, secondary_patch, context),
            patch=secondary_patch
        )

        # 6. Ensemble voting
        voting_result = self._vote(
            primary_patch, secondary_patch,
            primary_eval, secondary_eval
        )

        # Select winner
        if voting_result.winner == 'primary':
            winner_patch = primary_patch
        elif voting_result.winner == 'secondary':
            winner_patch = secondary_patch
        else:  # combined
            winner_patch = self._combine_patches(
                primary_patch, secondary_patch
            )

        return EnsembleResult(
            success=winner_patch is not None,
            patch=winner_patch,
            primary_patch=primary_patch,
            secondary_patch=secondary_patch,
            voting_result=voting_result,
            primary_score=primary_eval.get('score', 0),
            secondary_score=secondary_eval.get('score', 0)
        )

    def _vote(
        self,
        primary_patch: Dict,
        secondary_patch: Dict,
        primary_eval: Dict,
        secondary_eval: Dict
    ) -> VotingResult:
        """Implements ensemble voting strategy."""
        primary_score = primary_eval.get('score', 0)
        secondary_score = secondary_eval.get('score', 0)

        score_diff = abs(primary_score - secondary_score)

        if score_diff < 0.1:
            # Tie: Combine patches
            return VotingResult(
                winner='combined',
                confidence=0.5,
                reasoning="Scores too close - combining both approaches"
            )
        elif primary_score > secondary_score:
            return VotingResult(
                winner='primary',
                confidence=score_diff,
                reasoning=f"Primary model scored higher ({primary_score:.2f} vs {secondary_score:.2f})"
            )
        else:
            return VotingResult(
                winner='secondary',
                confidence=score_diff,
                reasoning=f"Secondary model scored higher ({secondary_score:.2f} vs {primary_score:.2f})"
            )

    def _combine_patches(
        self,
        primary_patch: Dict,
        secondary_patch: Dict
    ) -> Dict:
        """Combines two patches intelligently."""
        # Merge changes from both patches
        combined = {
            'files': {},
            'description': "Combined fix from ensemble voting"
        }

        # Add all files from primary
        for file_path, content in primary_patch.get('files', {}).items():
            combined['files'][file_path] = content

        # Add/merge files from secondary
        for file_path, content in secondary_patch.get('files', {}).items():
            if file_path in combined['files']:
                # Merge changes (simple concatenation for now)
                combined['files'][file_path] += "\n" + content
            else:
                combined['files'][file_path] = content

        return combined
```

### 4.2 Configuration

```yaml
# config.yaml
escalation_policy:
  level_3:
    enabled: true
    primary_model: "qwen3.5-27b"  # or 35b
    secondary_model: "deepseek-v3.2-32b"  # or creative model
    verifier_model: "phi-4-mini"
    primary_temperature: 0.3
    secondary_temperature: 0.4  # More creative
    voting_strategy: "verifier_score"  # or "consensus" or "majority"
    combine_on_tie: true
    parallel_execution: true
```

---

## 5. Escalation Level 4: Human-in-the-Loop

### 5.1 Human Report Format

**Goal:** Provide humans with all necessary information to fix the bug manually.

```python
# src/escalation/human_report_generator.py

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class HumanReport:
    """Human-readable escalation report."""
    executive_summary: str
    root_cause: str
    failed_patches_analysis: str
    escalation_history: str
    fix_suggestions: List[Dict]
    regression_tests: str
    draft_pr: Optional[Dict]


class HumanReportGenerator:
    """Generates detailed human-readable escalation reports."""

    def generate_report(
        self,
        bug: Dict[str, Any],
        failed_patches: List[Dict],
        test_results: List[Dict],
        escalation_history: List[Dict]
    ) -> HumanReport:
        """Generates comprehensive escalation report for human review."""

        report = HumanReport(
            executive_summary="",
            root_cause="",
            failed_patches_analysis="",
            escalation_history="",
            fix_suggestions=[],
            regression_tests="",
            draft_pr=None
        )

        # 1. Executive Summary
        report.executive_summary = self._generate_executive_summary(bug)

        # 2. Root Cause Analysis (with graph snippets)
        report.root_cause = self._analyze_root_cause(bug)

        # 3. Failed Patch Analysis
        report.failed_patches_analysis = self._analyze_failures(
            failed_patches, test_results
        )

        # 4. Escalation History
        report.escalation_history = self._format_escalation_history(
            escalation_history
        )

        # 5. Three Concrete Fix Suggestions
        report.fix_suggestions = self._generate_fix_suggestions(
            bug, escalation_history
        )

        # 6. Ready-to-Use Regression Tests
        report.regression_tests = self._generate_regression_tests(bug)

        # 7. Draft PR (optional)
        report.draft_pr = self._generate_draft_pr(
            bug, report.fix_suggestions
        )

        return report

    def _generate_executive_summary(self, bug: Dict) -> str:
        """Generates executive summary."""
        return f"""
# Escalation Report: {bug.get('id', 'UNKNOWN')}

## Summary

| Field | Value |
|-------|-------|
| **Bug Type** | {bug.get('type', 'Unknown')} |
| **Severity** | {bug.get('severity', 'Unknown')} |
| **Location** | `{bug.get('file_path', 'N/A')}:{bug.get('line_number', 'N/A')}` |
| **Loops Attempted** | {bug.get('loops_attempted', 0)} |
| **Escalation Level Reached** | {bug.get('max_escalation_level', 0)} |

### Why Automated Fixing Failed

{self._summarize_failure_reasons(bug)}

### Recommendation

{self._generate_recommendation(bug)}
"""

    def _analyze_root_cause(self, bug: Dict) -> str:
        """Analyzes and documents root cause."""
        return f"""
## Root Cause Analysis

### Data-Flow Graph Snippet

```
{self._render_dfg_snippet(bug)}
```

### Control-Flow Graph Snippet

```
{self._render_cfg_snippet(bug)}
```

### Root Cause

{bug.get('root_cause_analysis', 'Analysis not available')}
"""

    def _generate_fix_suggestions(
        self,
        bug: Dict,
        escalation_history: List[Dict]
    ) -> List[Dict]:
        """Generates 3 concrete fix suggestions."""
        suggestions = []

        # Suggestion 1: Minimal fix
        suggestions.append({
            'id': 1,
            'title': 'Minimal Fix',
            'description': 'Smallest change that addresses the root cause',
            'files_to_change': self._get_minimal_files(bug),
            'estimated_effort': 'Low',
            'risk': 'Low',
            'code_example': self._generate_minimal_fix_code(bug)
        })

        # Suggestion 2: Refactoring
        suggestions.append({
            'id': 2,
            'title': 'Refactoring Approach',
            'description': 'Small refactoring that makes the fix obvious',
            'files_to_change': self._get_refactor_files(bug),
            'estimated_effort': 'Medium',
            'risk': 'Medium',
            'code_example': self._generate_refactor_code(bug)
        })

        # Suggestion 3: Architectural fix
        suggestions.append({
            'id': 3,
            'title': 'Architectural Fix',
            'description': 'Long-term solution addressing systemic issues',
            'files_to_change': self._get_architectural_files(bug),
            'estimated_effort': 'High',
            'risk': 'High',
            'code_example': self._generate_architectural_code(bug)
        })

        return suggestions
```

### 5.2 Report Template (Markdown)

```markdown
# Escalation Report: BUG-2024-0042

## Executive Summary

| Field | Value |
|-------|-------|
| **Bug Type** | Race Condition |
| **Severity** | Critical |
| **Location** | `src/auth/token_manager.py:45-67` |
| **Loops Attempted** | 5 |
| **Escalation Level Reached** | 4 (Human Review) |

### Why Automated Fixing Failed

The automated fixing system attempted 5 iterations but could not find a valid patch because:

1. **Complexity:** The bug involves concurrent access across 3 modules (auth, db, cache)
2. **Interdependence:** Fixing one aspect introduces regressions in another
3. **Missing Abstraction:** The current architecture lacks a proper locking mechanism

### Recommendation

Manual intervention required. Recommended approach: Implement distributed locking with Redis RedLock.

---

## Root Cause Analysis

### Data-Flow Graph Snippet

```
[User Input] → [AuthHandler.validate()] → [TokenManager.update()]
                                              ↓
                                    [Cache.set(token)] ←── RACE CONDITION
                                              ↓
                                    [DB.session.write()] ←── NON-ATOMIC
```

### Control-Flow Graph Snippet

```
AuthHandler.validate()
  ├─→ TokenManager.update()
  │     ├─→ Cache.set() [async, no lock]
  │     └─→ DB.session.write() [async, no transaction]
  └─→ Response.send()
```

### Root Cause

**Two concurrent requests can interleave as follows:**

1. Request A: TokenManager.update() → Cache.set(token_A)
2. Request B: TokenManager.update() → Cache.set(token_B)
3. Request A: DB.session.write(session_A)
4. Request B: DB.session.write(session_B)

**Result:** Cache has token_B, but DB has session_A → Inconsistent state

---

## Failed Patch Analysis

### Attempt 1: Add Lock to TokenManager
- **Why it failed:** Lock not shared across processes
- **Test failure:** `test_concurrent_auth_still_fails`

### Attempt 2: Make DB Write Atomic
- **Why it failed:** Doesn't address cache inconsistency
- **Test failure:** `test_cache_db_consistency`

### Attempt 3: Retry Logic
- **Why it failed:** Retries don't fix root cause
- **Test failure:** `test_no_race_condition`

---

## Escalation History

### Level 1: Context Explosion
- **Result:** Generated patch touched 8 files (exceeded 3-file limit)
- **Status:** Rejected by policy check

### Level 2: Bug Decomposition
- **Decomposed into:** 3 sub-bugs
- **Result:** Sub-bug 2 fix broke sub-bug 1
- **Status:** Interdependence too high

### Level 3: Multi-Model Ensemble
- **Primary (Qwen3.5-27B):** Suggested distributed lock (Redis)
- **Secondary (DeepSeek-V3.2):** Suggested event sourcing
- **Result:** Both require architectural changes
- **Status:** Escalated to human

---

## Fix Suggestions

### Suggestion 1: Distributed Lock with Redis (Recommended)

**Description:** Use Redis RedLock for distributed locking across processes.

**Files to change:**
- `src/auth/token_manager.py` (add lock acquisition)
- `src/cache/redis_client.py` (add RedLock implementation)
- `config.yaml` (add Redis configuration)

**Code Example:**
```python
# src/auth/token_manager.py
from redis_lock import RedLock

class TokenManager:
    def __init__(self, redis_client):
        self.lock = RedLock(
            redis_client,
            "token_update_lock",
            timeout=10000
        )

    def update_token(self, user_id, token):
        with self.lock.acquire(user_id):
            # Critical section - only one process can execute
            self.cache.set(user_id, token)
            self.db.session.write(user_id, token)
```

**Pros:**
- Solves race condition completely
- Industry-standard solution
- Well-tested libraries available

**Cons:**
- Adds Redis dependency
- Requires infrastructure change
- Slight latency increase (~10ms per operation)

**Estimated Effort:** 2-4 hours

---

### Suggestion 2: Event Sourcing

**Description:** Replace direct updates with event-based architecture.

**Files to change:**
- `src/auth/` (new event handlers)
- `src/events/` (new event types)
- `src/db/` (event store)

**Pros:**
- Eliminates race conditions by design
- Provides audit trail
- Enables replay debugging

**Cons:**
- Major architectural change
- Significant refactoring required
- Learning curve for team

**Estimated Effort:** 2-4 days

---

### Suggestion 3: Database-Only Locking

**Description:** Use database-level locking (SELECT FOR UPDATE).

**Files to change:**
- `src/auth/token_manager.py`
- `src/db/session_store.py`

**Pros:**
- No new dependencies
- Minimal code changes
- Uses existing infrastructure

**Cons:**
- Database contention under high load
- Doesn't solve cache inconsistency
- Potential deadlocks

**Estimated Effort:** 1-2 hours

---

## Ready-to-Use Regression Tests

```python
# tests/regression/test_race_condition.py

import pytest
import asyncio
from concurrent.futures import ThreadPoolExecutor

class TestTokenManagerRaceCondition:
    """Regression tests for token manager race condition."""

    @pytest.mark.asyncio
    async def test_concurrent_token_updates(self, token_manager, 100_users):
        """Tests that concurrent token updates don't cause inconsistency."""
        async def update_token(user_id):
            return await token_manager.update_token(user_id, f"token_{user_id}")

        # Run 100 concurrent updates
        tasks = [update_token(i) for i in range(100)]
        await asyncio.gather(*tasks)

        # Verify consistency
        for i in range(100):
            cached = await token_manager.cache.get(i)
            db_value = await token_manager.db.get(i)
            assert cached == db_value, f"Inconsistency for user {i}"

    @pytest.mark.asyncio
    async def test_cache_db_consistency(self, token_manager):
        """Tests that cache and DB remain consistent after updates."""
        for i in range(10):
            await token_manager.update_token(i, f"token_{i}")

            cached = await token_manager.cache.get(i)
            db_value = await token_manager.db.get(i)

            assert cached == db_value
```

---

## Draft Pull Request

**Title:** Fix: Race condition in TokenManager with Redis RedLock

**Description:**
This PR fixes the race condition in TokenManager by implementing distributed locking with Redis RedLock.

**Changes:**
- Added Redis RedLock implementation
- Wrapped token update in lock acquisition
- Added regression tests

**Testing:**
- All existing tests pass
- New regression tests added
- Manual testing with concurrent requests

**Deployment Notes:**
- Requires Redis instance
- Update config.yaml with Redis connection
- No breaking changes

---

## Appendix: Additional Context

### Git Blame (Affected Files)
<git blame output>

### Recent Commits
<last 5 commits>

### Related Issues
<links to similar historical bugs>
```

### 5.3 Configuration

```yaml
# config.yaml
escalation_policy:
  level_4:
    enabled: true
    generate_draft_pr: true
    include_git_blame: true
    include_recent_commits: 5
    include_graph_snippets: true
    include_regression_tests: true
    fix_suggestions_count: 3
    output_format: "markdown"
    output_path: "reports/escalation/"
```

---

## 6. Configuration Reference

### 6.1 Complete Escalation Configuration

```yaml
# config.yaml - Escalation Section

escalation_policy:
  # Global settings
  hard_escalate_after_no_improvement: 2
  max_total_escalation_time_minutes: 60

  # Level 1: Context Explosion
  level_1:
    enabled: true
    context_window: 160000
    include_repomix: true
    include_git_blame: true
    include_git_commits: 5
    include_dfg_diagram: true
    include_cfg_diagram: true
    include_api_docs: true
    include_similar_bugs: true
    temperature: 0.3
    max_tokens: 8000
    timeout_seconds: 300

  # Level 2: Bug Decomposition
  level_2:
    enabled: true
    max_sub_bugs: 4
    min_sub_bugs: 2
    require_independence: true
    sequential_fix: true
    parallel_test: true
    temperature: 0.2
    max_tokens: 4000
    timeout_seconds: 300

  # Level 3: Multi-Model Ensemble
  level_3:
    enabled: true
    primary_model: "qwen3.5-27b"
    secondary_model: "deepseek-v3.2-32b"
    verifier_model: "phi-4-mini"
    primary_temperature: 0.3
    secondary_temperature: 0.4
    voting_strategy: "verifier_score"
    combine_on_tie: true
    parallel_execution: true
    timeout_seconds: 300

  # Level 4: Human-in-the-Loop
  level_4:
    enabled: true
    generate_draft_pr: true
    include_git_blame: true
    include_recent_commits: 5
    include_graph_snippets: true
    include_regression_tests: true
    fix_suggestions_count: 3
    output_format: "markdown"
    output_path: "reports/escalation/"

# Model configurations for escalation
models:
  escalation_primary:
    model: "Qwen3.5-27B-Instruct-Q4_K_M.gguf"
    ngl: 99
    ctx_size: 160000
    port: 8080

  escalation_secondary:
    model: "DeepSeek-V3.2-Small-Q4_K_M.gguf"
    ngl: 99
    ctx_size: 64000
    port: 8083

  escalation_verifier:
    model: "Phi-4-mini-3.8B-Q4_K_M.gguf"
    ngl: 35
    ctx_size: 32000
    port: 8081

# External tools for escalation
external_tools:
  repomix:
    enabled: true
    path: "repomix"
    format: "xml"
    max_files: 100

  git:
    enabled: true
    blame_enabled: true
    log_enabled: true
    max_commits: 5
```

### 6.2 Environment Variables

```bash
# .env - Escalation Settings

# Escalation triggers
GLITCHHUNTER_MAX_ITERATIONS=5
GLITCHHUNTER_ESCALATE_AFTER_NO_PROGRESS=2

# Level 1 settings
GLITCHHUNTER_CONTEXT_EXPLOSION_ENABLED=true
GLITCHHUNTER_CONTEXT_WINDOW=160000

# Level 2 settings
GLITCHHUNTER_DECOMPOSITION_ENABLED=true
GLITCHHUNTER_MAX_SUB_BUGS=4

# Level 3 settings
GLITCHHUNTER_ENSEMBLE_ENABLED=true
GLITCHHUNTER_ENSEMBLE_PRIMARY_MODEL=qwen3.5-27b
GLITCHHUNTER_ENSEMBLE_SECONDARY_MODEL=deepseek-v3.2-32b

# Level 4 settings
GLITCHHUNTER_HUMAN_REPORT_ENABLED=true
GLITCHHUNTER_DRAFT_PR_ENABLED=true
GLITCHHUNTER_REPORT_OUTPUT_PATH=reports/escalation/

# Timeouts
GLITCHHUNTER_ESCALATION_TIMEOUT_SECONDS=300
GLITCHHUNTER_MAX_ESCALATION_TIME_MINUTES=60
```

---

## Appendix A: Example Escalation Flow

### A.1 Complete Escalation Trace

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EXAMPLE ESCALATION TRACE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Bug: Race condition in distributed cache system                            │
│  Severity: Critical                                                          │
│  Location: src/cache/distributed.py:234-289                                 │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ ITERATION 1-5: Standard Patch Loop                                 │     │
│  │                                                                     │     │
│  │ Attempt 1: Add local lock → Failed (not distributed)               │     │
│  │ Attempt 2: Use Redis SETNX → Failed (race in expiry)               │     │
│  │ Attempt 3: Add retry logic → Failed (doesn't fix root cause)       │     │
│  │ Attempt 4: Increase timeout → Failed (timing issue)                │     │
│  │ Attempt 5: Combine locks → Failed (deadlock detected)              │     │
│  │                                                                     │     │
│  │ Result: ESCALATE                                                   │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│          │                                                                   │
│          ▼                                                                   │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ ESCALATION LEVEL 1: Context Explosion                              │     │
│  │                                                                     │     │
│  │ Actions:                                                            │     │
│  │ • Gather full Repomix XML (45 files, 12k lines)                    │     │
│  │ • Add git blame for all affected files                             │     │
│  │ • Generate DFG + CFG diagrams                                      │     │
│  │ • Fetch similar bugs from issue tracker                            │     │
│  │                                                                     │     │
│  │ Result: Generated patch with 8 files (exceeded 3-file limit)       │     │
│  │ Status: FAILED - Policy violation                                  │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│          │                                                                   │
│          ▼                                                                   │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ ESCALATION LEVEL 2: Bug Decomposition                              │     │
│  │                                                                     │     │
│  │ Decomposed into:                                                    │     │
│  │ • SUB-1: Missing distributed lock (cache layer)                    │     │
│  │ • SUB-2: Non-atomic read-modify-write (DB layer)                   │     │
│  │ • SUB-3: No cache invalidation (invalidation layer)                │     │
│  │                                                                     │     │
│  │ Attempt SUB-1: Redis RedLock → Failed (complexity)                 │     │
│  │ Attempt SUB-2: DB transaction → Failed (interdependence)           │     │
│  │                                                                     │     │
│  │ Result: Sub-bugs too interdependent                                │     │
│  │ Status: FAILED - Cannot isolate fixes                              │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│          │                                                                   │
│          ▼                                                                   │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ ESCALATION LEVEL 3: Multi-Model Ensemble                           │     │
│  │                                                                     │     │
│  │ Primary (Qwen3.5-27B):                                              │     │
│  │ • Suggestion: Implement RedLock with fallback                      │     │
│  │ • Score: 0.78                                                      │     │
│  │                                                                     │     │
│  │ Secondary (DeepSeek-V3.2-32B):                                      │     │
│  │ • Suggestion: Event sourcing with CQRS                             │     │
│  │ • Score: 0.72                                                      │     │
│  │                                                                     │     │
│  │ Verifier Decision: Primary approach selected                       │     │
│  │                                                                     │     │
│  │ Result: Requires architectural change (Redis cluster)              │     │
│  │ Status: FAILED - Beyond automated fixing scope                     │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│          │                                                                   │
│          ▼                                                                   │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ ESCALATION LEVEL 4: Human-in-the-Loop                              │     │
│  │                                                                     │     │
│  │ Generated:                                                          │     │
│  │ • 15-page escalation report                                        │     │
│  │ • Root cause analysis with graph snippets                          │     │
│  │ • 3 fix suggestions with code examples                             │     │
│  │ • Ready-to-use regression tests                                    │     │
│  │ • Draft PR with full implementation                                │     │
│  │                                                                     │     │
│  │ Recommendation: Implement Redis RedLock (Suggestion 1)             │     │
│  │                                                                     │     │
│  │ Status: HUMAN REVIEW REQUIRED                                      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  Total Escalation Time: 45 minutes                                          │
│  Final Outcome: Human report generated, Draft PR ready                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

**END OF DOCUMENT**