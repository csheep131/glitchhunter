# Safety Guarantees

**Version:** 2.0
**Date:** April 13, 2026
**Status:** System Specification

---

## Table of Contents

1. [System Invariants](#1-system-invariants)
2. [Rollback Mechanisms](#2-rollback-mechanisms)
3. [Testing Guarantees](#3-testing-guarantees)
4. [Security Guarantees](#4-security-guarantees)
5. [Escalation Safety](#5-escalation-safety)
6. [Configuration Reference](#6-configuration-reference)

---

## 1. System Invariants

### 1.1 Core Invariants

System invariants are properties that **must never be violated** during any execution of GlitchHunter. These are hard constraints enforced at multiple levels.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SYSTEM INVARIANTS                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  INVARIANT 1: No Data Loss                                                   │
│  ─────────────────────────────────                                           │
│  • Original source code is NEVER modified directly                          │
│  • All changes go through git-worktree isolation                            │
│  • Patches are NEVER applied to main branch without verification            │
│  • Backup of original state before any operation                            │
│                                                                              │
│  INVARIANT 2: No Silent Failures                                             │
│  ───────────────────────────────────                                         │
│  • Every failure MUST be logged                                             │
│  • Every failure MUST be reported                                           │
│  • No failure can be swallowed silently                                     │
│  • Escalation after 2× no progress                                          │
│                                                                              │
│  INVARIANT 3: No Regression Introduction                                     │
│  ──────────────────────────────────────────────                              │
│  • Patches MUST pass all existing tests                                     │
│  • Patches MUST NOT reduce code coverage                                    │
│  • Patches MUST NOT introduce new static analysis warnings                  │
│  • Verifier confidence MUST be >= 95%                                       │
│                                                                              │
│  INVARIANT 4: No Security Degradation                                        │
│  ────────────────────────────────────────                                    │
│  • Patches MUST NOT introduce new security vulnerabilities                  │
│  • OWASP Top 10 coverage MUST be maintained                                 │
│  • Security gates MUST pass before any patch application                    │
│  • Network access in sandbox is ALWAYS disabled                             │
│                                                                              │
│  INVARIANT 5: No Resource Exhaustion                                         │
│  ──────────────────────────────────────                                      │
│  • VRAM usage MUST stay within configured limits                            │
│  • Disk space MUST be monitored                                             │
│  • Timeout enforcement for all operations                                   │
│  • Memory limits for sandbox execution                                      │
│                                                                              │
│  INVARIANT 6: No Infinite Loops                                              │
│  ────────────────────────────────────                                        │
│  • Maximum 5 iterations per bug fix                                         │
│  • Maximum 2 escalations per run                                            │
│  • Timeout on all async operations                                          │
│  • Circuit breaker for external services                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Invariant Enforcement

```python
# src/safety/invariants.py

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio


class InvariantType(Enum):
    NO_DATA_LOSS = "no_data_loss"
    NO_SILENT_FAILURE = "no_silent_failure"
    NO_REGRESSION = "no_regression"
    NO_SECURITY_DEGRADATION = "no_security_degradation"
    NO_RESOURCE_EXHAUSTION = "no_resource_exhaustion"
    NO_INFINITE_LOOP = "no_infinite_loop"


@dataclass
class InvariantViolation:
    """Represents an invariant violation."""
    invariant: InvariantType
    message: str
    severity: str  # "critical", "high", "medium", "low"
    context: Dict[str, Any]
    timestamp: str


class InvariantEnforcer:
    """Enforces system invariants."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.violations: list[InvariantViolation] = []
        self.critical_violations = 0

    def check_no_data_loss(
        self,
        original_state: Dict,
        current_state: Dict
    ) -> Optional[InvariantViolation]:
        """Checks that no data was lost."""
        # Verify original files are intact
        for file_path, original_content in original_state.get("files", {}).items():
            current_content = current_state.get("files", {}).get(file_path)

            if current_content is None:
                # File was deleted - check if it's in a backup
                if not self._is_backed_up(file_path):
                    return InvariantViolation(
                        invariant=InvariantType.NO_DATA_LOSS,
                        message=f"File {file_path} was deleted without backup",
                        severity="critical",
                        context={"file_path": file_path},
                        timestamp=self._now()
                    )

        return None

    def check_no_silent_failure(
        self,
        operation: str,
        result: Dict
    ) -> Optional[InvariantViolation]:
        """Checks that failures are not silent."""
        if result.get("status") == "failed" and not result.get("logged"):
            return InvariantViolation(
                invariant=InvariantType.NO_SILENT_FAILURE,
                message=f"Operation {operation} failed without logging",
                severity="high",
                context={"operation": operation, "result": result},
                timestamp=self._now()
            )

        return None

    def check_no_regression(
        self,
        original_tests: Dict,
        new_tests: Dict,
        original_coverage: float,
        new_coverage: float
    ) -> Optional[InvariantViolation]:
        """Checks that no regression was introduced."""
        # Check test failures
        failed_tests = [
            test_id for test_id, result in new_tests.items()
            if not result.get("passed") and original_tests.get(test_id, {}).get("passed")
        ]

        if failed_tests:
            return InvariantViolation(
                invariant=InvariantType.NO_REGRESSION,
                message=f"Tests regressed: {failed_tests}",
                severity="critical",
                context={"failed_tests": failed_tests},
                timestamp=self._now()
            )

        # Check coverage regression
        if new_coverage < original_coverage:
            return InvariantViolation(
                invariant=InvariantType.NO_REGRESSION,
                message=f"Coverage regressed: {original_coverage:.2f} → {new_coverage:.2f}",
                severity="high",
                context={
                    "original_coverage": original_coverage,
                    "new_coverage": new_coverage
                },
                timestamp=self._now()
            )

        return None

    def check_resource_limits(
        self,
        vram_used: int,
        vram_limit: int,
        disk_used: int,
        disk_limit: int,
        memory_used: int,
        memory_limit: int
    ) -> Optional[InvariantViolation]:
        """Checks resource limits are not exceeded."""
        if vram_used > vram_limit:
            return InvariantViolation(
                invariant=InvariantType.NO_RESOURCE_EXHAUSTION,
                message=f"VRAM limit exceeded: {vram_used} > {vram_limit}",
                severity="critical",
                context={"vram_used": vram_used, "vram_limit": vram_limit},
                timestamp=self._now()
            )

        if disk_used > disk_limit:
            return InvariantViolation(
                invariant=InvariantType.NO_RESOURCE_EXHAUSTION,
                message=f"Disk limit exceeded: {disk_used} > {disk_limit}",
                severity="high",
                context={"disk_used": disk_used, "disk_limit": disk_limit},
                timestamp=self._now()
            )

        if memory_used > memory_limit:
            return InvariantViolation(
                invariant=InvariantType.NO_RESOURCE_EXHAUSTION,
                message=f"Memory limit exceeded: {memory_used} > {memory_limit}",
                severity="high",
                context={"memory_used": memory_used, "memory_limit": memory_limit},
                timestamp=self._now()
            )

        return None

    def check_iteration_limit(
        self,
        current_iteration: int,
        max_iterations: int
    ) -> Optional[InvariantViolation]:
        """Checks iteration limit is not exceeded."""
        if current_iteration > max_iterations:
            return InvariantViolation(
                invariant=InvariantType.NO_INFINITE_LOOP,
                message=f"Iteration limit exceeded: {current_iteration} > {max_iterations}",
                severity="critical",
                context={
                    "current_iteration": current_iteration,
                    "max_iterations": max_iterations
                },
                timestamp=self._now()
            )

        return None

    def record_violation(self, violation: InvariantViolation) -> None:
        """Records an invariant violation."""
        self.violations.append(violation)

        if violation.severity == "critical":
            self.critical_violations += 1

        # Log violation
        self._log_violation(violation)

        # Trigger escalation if critical
        if violation.severity == "critical":
            self._trigger_escalation(violation)

    def has_critical_violations(self) -> bool:
        """Checks if there are any critical violations."""
        return self.critical_violations > 0

    def get_violations(self) -> list[InvariantViolation]:
        """Returns all recorded violations."""
        return self.violations

    def _log_violation(self, violation: InvariantViolation) -> None:
        """Logs violation to file and console."""
        import logging
        logger = logging.getLogger("glitchhunter.safety")

        logger.error(
            f"INVARIANT VIOLATION: {violation.invariant.value} - {violation.message}",
            extra={"violation": violation.__dict__}
        )

    def _trigger_escalation(self, violation: InvariantViolation) -> None:
        """Triggers escalation for critical violations."""
        # Import here to avoid circular dependency
        from ..escalation.escalation_manager import EscalationManager

        escalation = EscalationManager(self.config)
        asyncio.create_task(escalation.escalate_critical_violation(violation))

    def _is_backed_up(self, file_path: str) -> bool:
        """Checks if file is backed up."""
        # Check backup directory
        import os
        backup_path = f".glitchunter/backups/{file_path}"
        return os.path.exists(backup_path)

    def _now(self) -> str:
        """Returns current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
```

---

## 2. Rollback Mechanisms

### 2.1 Git-Worktree Rollback

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      GIT-WORKTREE ROLLBACK MECHANISM                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Normal Operation:                                                           │
│  ──────────────────                                                          │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Main      │─────▶│  Worktree   │─────▶│   Patch     │                  │
│  │   Branch    │      │  (Isolated) │      │   Apply     │                  │
│  └─────────────┘      └─────────────┘      └─────────────┘                  │
│                            │                     │                           │
│                            │                     ▼                           │
│                            │              ┌─────────────┐                    │
│                            │              │   Tests     │                    │
│                            │              │   Run       │                    │
│                            │              └──────┬──────┘                    │
│                            │                     │                           │
│                            │          ┌──────────┴──────────┐                │
│                            │          │                     │                │
│                            │          ▼ (Pass)              ▼ (Fail)        │
│                            │   ┌─────────────┐      ┌─────────────┐         │
│                            │   │   Merge     │      │  ROLLBACK   │         │
│                            │   │   to Main   │      │  (Destroy   │         │
│                            │   │             │      │   Worktree) │         │
│                            │   └─────────────┘      └─────────────┘         │
│                                                                              │
│  Rollback Process:                                                           │
│  ────────────────                                                            │
│  1. Detect test failure or gate failure                                     │
│  2. Mark worktree for deletion                                              │
│  3. Remove worktree directory                                               │
│  4. Clean up any temporary files                                            │
│  5. Log rollback event                                                      │
│  6. Continue with retry or escalation                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Implementation

```python
# src/safety/git_worktree_manager.py

from typing import Dict, Any, Optional
from dataclasses import dataclass
import subprocess
import os
import shutil


@dataclass
class WorktreeInfo:
    """Information about a git worktree."""
    path: str
    branch: str
    commit: str
    created_at: str


class GitWorktreeManager:
    """Manages git worktrees for isolated patch testing."""

    def __init__(self, repo_path: str, config: Dict[str, Any]):
        self.repo_path = repo_path
        self.config = config
        self.worktrees: Dict[str, WorktreeInfo] = {}
        self.backup_path = config.get("safety", {}).get(
            "backup_path", ".glitchunter/backups"
        )

    def create_worktree(self, branch_name: str) -> str:
        """Creates a new worktree for isolated testing."""
        worktree_path = os.path.join(
            self.repo_path,
            ".glitchunter",
            "worktrees",
            branch_name
        )

        # Create worktree
        result = subprocess.run(
            ["git", "worktree", "add", "-b", branch_name, worktree_path],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to create worktree: {result.stderr}")

        # Get current commit
        commit_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )

        # Store worktree info
        from datetime import datetime
        self.worktrees[branch_name] = WorktreeInfo(
            path=worktree_path,
            branch=branch_name,
            commit=commit_result.stdout.strip(),
            created_at=datetime.utcnow().isoformat()
        )

        # Create backup of original state
        self._create_backup(branch_name)

        return worktree_path

    def apply_patch(self, worktree_path: str, patch: str) -> bool:
        """Applies a patch to the worktree."""
        # Write patch to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
            f.write(patch)
            patch_file = f.name

        try:
            # Apply patch
            result = subprocess.run(
                ["git", "apply", patch_file],
                cwd=worktree_path,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return False

            # Commit patch
            subprocess.run(
                ["git", "add", "-A"],
                cwd=worktree_path,
                capture_output=True
            )

            subprocess.run(
                ["git", "commit", "-m", "Applied patch"],
                cwd=worktree_path,
                capture_output=True
            )

            return True
        finally:
            # Clean up patch file
            os.unlink(patch_file)

    def rollback(self, branch_name: str) -> bool:
        """Rolls back by removing the worktree."""
        if branch_name not in self.worktrees:
            return False

        worktree_info = self.worktrees[branch_name]

        try:
            # Remove worktree
            result = subprocess.run(
                ["git", "worktree", "remove", "-f", worktree_info.path],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                # Force remove directory
                if os.path.exists(worktree_info.path):
                    shutil.rmtree(worktree_info.path)

            # Remove from tracking
            del self.worktrees[branch_name]

            # Log rollback
            self._log_rollback(branch_name)

            return True
        except Exception as e:
            self._log_rollback_error(branch_name, str(e))
            return False

    def merge_to_main(self, branch_name: str) -> bool:
        """Merges worktree changes back to main branch."""
        if branch_name not in self.worktrees:
            return False

        worktree_info = self.worktrees[branch_name]

        try:
            # Checkout main
            subprocess.run(
                ["git", "checkout", "main"],
                cwd=self.repo_path,
                capture_output=True
            )

            # Merge worktree branch
            result = subprocess.run(
                ["git", "merge", branch_name, "--no-ff", "-m", f"GlitchHunter fix: {branch_name}"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return False

            # Remove worktree after successful merge
            self.rollback(branch_name)

            return True
        except Exception as e:
            self._log_merge_error(branch_name, str(e))
            return False

    def _create_backup(self, branch_name: str) -> None:
        """Creates a backup of the original state."""
        import shutil
        from datetime import datetime

        backup_dir = os.path.join(
            self.backup_path,
            branch_name,
            datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        )

        os.makedirs(backup_dir, exist_ok=True)

        # Copy important files
        for root, dirs, files in os.walk(self.repo_path):
            # Skip hidden directories and worktrees
            dirs[:] = [
                d for d in dirs
                if not d.startswith('.') and d != 'worktrees'
            ]

            for file in files:
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, self.repo_path)
                dst_path = os.path.join(backup_dir, rel_path)

                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)

    def _log_rollback(self, branch_name: str) -> None:
        """Logs rollback event."""
        import logging
        logger = logging.getLogger("glitchhunter.safety")
        logger.info(f"Rollback completed for worktree: {branch_name}")

    def _log_rollback_error(self, branch_name: str, error: str) -> None:
        """Logs rollback error."""
        import logging
        logger = logging.getLogger("glitchhunter.safety")
        logger.error(f"Rollback error for {branch_name}: {error}")

    def _log_merge_error(self, branch_name: str, error: str) -> None:
        """Logs merge error."""
        import logging
        logger = logging.getLogger("glitchhunter.safety")
        logger.error(f"Merge error for {branch_name}: {error}")

    def cleanup_all(self) -> None:
        """Cleans up all worktrees."""
        for branch_name in list(self.worktrees.keys()):
            self.rollback(branch_name)

        # Clean up worktree directory
        worktree_dir = os.path.join(
            self.repo_path,
            ".glitchunter",
            "worktrees"
        )
        if os.path.exists(worktree_dir):
            shutil.rmtree(worktree_dir)
```

### 2.3 Docker Sandbox Cleanup

```python
# src/safety/docker_sandbox_cleanup.py

from typing import Dict, Any, Optional
import docker
import asyncio


class DockerSandboxCleanup:
    """Manages Docker sandbox cleanup for safety."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = docker.from_env()
        self.active_containers: Dict[str, str] = {}  # container_id -> purpose

    def create_sandbox(self, purpose: str) -> str:
        """Creates a sandbox container."""
        container = self.client.containers.run(
            image="glitchhunter/sandbox:latest",
            detach=True,
            network_disabled=True,  # Security: no network access
            mem_limit=self.config.get("sandbox", {}).get("memory_limit", "2g"),
            cpu_quota=self.config.get("sandbox", {}).get("cpu_quota", 200000),
            tmpfs={
                '/tmp': 'rw,noexec,nosuid,size=512m'
            },
            read_only=True,  # Security: read-only filesystem
            security_opt=[
                'no-new-privileges:true'
            ],
            cap_drop=['ALL']  # Security: drop all capabilities
        )

        self.active_containers[container.id] = purpose
        return container.id

    async def execute_in_sandbox(
        self,
        container_id: str,
        command: str,
        timeout: int = 180
    ) -> Dict[str, Any]:
        """Executes a command in the sandbox."""
        container = self.client.containers.get(container_id)

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: container.exec_run(command, demux=True)
                ),
                timeout=timeout
            )

            return {
                "exit_code": result.exit_code,
                "output": result.output,
                "success": result.exit_code == 0
            }
        except asyncio.TimeoutError:
            # Kill container on timeout
            container.kill()
            return {
                "exit_code": -1,
                "output": b"Timeout exceeded",
                "success": False,
                "error": "timeout"
            }

    def cleanup_container(self, container_id: str) -> bool:
        """Cleans up a sandbox container."""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=5)
            container.remove(force=True)

            # Remove from tracking
            if container_id in self.active_containers:
                del self.active_containers[container_id]

            return True
        except docker.errors.NotFound:
            return True  # Already removed
        except Exception as e:
            self._log_cleanup_error(container_id, str(e))
            return False

    def cleanup_all(self) -> Dict[str, bool]:
        """Cleans up all active containers."""
        results = {}

        for container_id in list(self.active_containers.keys()):
            results[container_id] = self.cleanup_container(container_id)

        return results

    def health_check(self) -> Dict[str, Any]:
        """Performs health check on Docker infrastructure."""
        try:
            # Check Docker daemon
            self.client.ping()

            # Check active containers
            active_count = len(self.active_containers)

            return {
                "healthy": True,
                "docker_daemon": "running",
                "active_containers": active_count
            }
        except Exception as e:
            return {
                "healthy": False,
                "docker_daemon": "error",
                "error": str(e)
            }

    def _log_cleanup_error(self, container_id: str, error: str) -> None:
        """Logs cleanup error."""
        import logging
        logger = logging.getLogger("glitchhunter.safety")
        logger.error(f"Cleanup error for container {container_id}: {error}")
```

---

## 3. Testing Guarantees

### 3.1 Coverage Guarantees

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COVERAGE GUARANTEES                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  GUARANTEE 1: No Coverage Regression                                         │
│  ──────────────────────────────────────                                      │
│  • Patches MUST NOT reduce overall code coverage                            │
│  • Minimum coverage threshold: 80%                                          │
│  • Coverage delta must be >= 0                                              │
│  • Enforcement: Gate 3 (Test Suite Execution)                               │
│                                                                              │
│  GUARANTEE 2: Regression Test Coverage                                       │
│  ────────────────────────────────────────                                    │
│  • At least 3 regression tests per bug                                      │
│  • Tests MUST cover edge cases from Data-Flow Graph                         │
│  • Tests MUST fail on original code (Fail2Pass)                             │
│  • Enforcement: Phase 3.1 (Regression Test Generation)                      │
│                                                                              │
│  GUARANTEE 3: Security Test Coverage                                         │
│  ────────────────────────────────────────                                    │
│  • OWASP Top 10 2025 coverage: 100%                                         │
│  • API Security Top 10 coverage: 100%                                       │
│  • Attack scenario coverage: All defined scenarios                          │
│  • Enforcement: Phase 2 (The Shield)                                        │
│                                                                              │
│  GUARANTEE 4: Branch Coverage                                                │
│  ─────────────────────────────────────                                       │
│  • All conditional branches must be tested                                  │
│  • Exception paths must be tested                                           │
│  • Error handling paths must be tested                                      │
│  • Enforcement: Coverage checker with branch tracking                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Implementation

```python
# src/safety/coverage_checker.py

from typing import Dict, Any, Optional
from dataclasses import dataclass
import coverage
import json


@dataclass
class CoverageResult:
    """Result of coverage check."""
    overall_coverage: float
    branch_coverage: float
    line_coverage: float
    coverage_delta: float
    files_below_threshold: list
    passed: bool


class CoverageChecker:
    """Checks coverage guarantees."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_coverage = config.get("safety", {}).get(
            "min_coverage", 0.80
        )
        self.require_non_regressive = config.get("safety", {}).get(
            "coverage_non_regressive", True
        )

    def check_coverage(
        self,
        test_results: Dict,
        original_coverage: float,
        repo_path: str
    ) -> CoverageResult:
        """Checks coverage guarantees."""
        # Run coverage analysis
        cov = coverage.Coverage(
            data_file=".glitchunter/coverage/.coverage",
            branch=True,
            source=[repo_path]
        )

        cov.load()
        cov.report()

        # Get coverage metrics
        overall = cov.coverage()
        branch = cov._branch_stats()

        # Calculate branch coverage percentage
        branch_total = sum(b[0] + b[1] for b in branch.values())
        branch_covered = sum(b[2] + b[3] for b in branch.values())
        branch_coverage = (branch_covered / branch_total * 100) if branch_total > 0 else 0

        # Calculate delta
        coverage_delta = overall - original_coverage

        # Find files below threshold
        files_below = []
        for file_path, file_coverage in cov.report(file_precision=2).items():
            if file_coverage < self.min_coverage * 100:
                files_below.append({
                    "file": file_path,
                    "coverage": file_coverage
                })

        # Determine if passed
        passed = (
            overall >= self.min_coverage * 100 and
            (not self.require_non_regressive or coverage_delta >= 0) and
            len(files_below) == 0
        )

        return CoverageResult(
            overall_coverage=overall / 100,
            branch_coverage=branch_coverage / 100,
            line_coverage=overall / 100,
            coverage_delta=coverage_delta / 100,
            files_below_threshold=files_below,
            passed=passed
        )

    def check_regression_tests(
        self,
        regression_tests: list,
        test_results: Dict
    ) -> Dict[str, Any]:
        """Checks regression test guarantees."""
        # Check minimum test count
        min_tests = self.config.get("regression_testing", {}).get("min_tests", 3)
        test_count_passed = len(regression_tests) >= min_tests

        # Check Fail2Pass validation
        fail2pass_validated = all(
            t.get("actual_failure_on_original", False)
            for t in regression_tests
        )

        # Check test results
        all_passed = all(
            test_results.get(t["id"], {}).get("passed", False)
            for t in regression_tests
        )

        return {
            "test_count_passed": test_count_passed,
            "test_count": len(regression_tests),
            "min_required": min_tests,
            "fail2pass_validated": fail2pass_validated,
            "all_tests_passed": all_passed,
            "passed": test_count_passed and fail2pass_validated and all_passed
        }

    def check_security_coverage(
        self,
        security_scan_results: Dict
    ) -> Dict[str, Any]:
        """Checks security test coverage guarantees."""
        # Check OWASP coverage
        owasp_coverage = security_scan_results.get("owasp_coverage", {})
        owasp_passed = all(
            category.get("covered", False)
            for category in owasp_coverage.values()
        )

        # Check API Security coverage
        api_coverage = security_scan_results.get("api_coverage", {})
        api_passed = all(
            category.get("covered", False)
            for category in api_coverage.values()
        )

        # Check attack scenario coverage
        attack_coverage = security_scan_results.get("attack_scenario_coverage", {})
        attack_passed = all(
            scenario.get("covered", False)
            for scenario in attack_coverage.values()
        )

        return {
            "owasp_coverage_passed": owasp_passed,
            "owasp_categories": owasp_coverage,
            "api_coverage_passed": api_passed,
            "api_categories": api_coverage,
            "attack_coverage_passed": attack_passed,
            "attack_scenarios": attack_coverage,
            "passed": owasp_passed and api_passed and attack_passed
        }
```

---

## 4. Security Guarantees

### 4.1 OWASP Coverage

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OWASP TOP 10 2025 COVERAGE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  A01:2025 - Broken Access Control                                           │
│  ────────────────────────────────────                                        │
│  • BOLA (Broken Object Level Authorization) detection                       │
│  • BFLA (Broken Function Level Authorization) detection                     │
│  • Mass assignment detection                                                │
│  • Enforcement: Semgrep rules + LLM analysis                                │
│                                                                              │
│  A02:2025 - Cryptographic Failures                                          │
│  ─────────────────────────────────────                                       │
│  • Weak algorithm detection (MD5, SHA1, DES)                                │
│  • Hardcoded key detection                                                  │
│  • Insecure random number generation                                        │
│  • Enforcement: Semgrep cryptographic rules                                 │
│                                                                              │
│  A03:2025 - Injection                                                       │
│  ────────────────────────                                                    │
│  • SQL Injection detection                                                  │
│  • NoSQL Injection detection                                                │
│  • Command Injection detection                                              │
│  • LDAP Injection detection                                                 │
│  • ORM Injection detection                                                  │
│  • Enforcement: Semgrep + LLM + Data-Flow analysis                          │
│                                                                              │
│  A04:2025 - Insecure Design                                                 │
│  ───────────────────────────────                                             │
│  • Missing rate limiting                                                    │
│  • Missing input validation                                                 │
│  • Missing output encoding                                                  │
│  • Enforcement: LLM design review                                           │
│                                                                              │
│  A05:2025 - Security Misconfiguration                                       │
│  ──────────────────────────────────────────                                  │
│  • Debug mode enabled                                                       │
│  • Verbose error messages                                                   │
│  • Missing security headers                                                 │
│  • CORS misconfiguration                                                    │
│  • Enforcement: Semgrep + configuration scanner                             │
│                                                                              │
│  A06:2025 - Vulnerable and Outdated Components                              │
│  ─────────────────────────────────────────────────────                       │
│  • Dependency vulnerability scanning                                        │
│  • Version checking against CVE database                                    │
│  • Enforcement: Trivy/Grype integration                                     │
│                                                                              │
│  A07:2025 - Identification and Authentication Failures                      │
│  ──────────────────────────────────────────────────────                      │
│  • Session fixation detection                                               │
│  • Weak password policies                                                   │
│  • Missing MFA                                                              │
│  • JWT misconfiguration                                                     │
│  • Enforcement: Semgrep auth rules                                          │
│                                                                              │
│  A08:2025 - Software and Data Integrity Failures                            │
│  ─────────────────────────────────────────────────────                       │
│  • CI/CD pipeline security                                                  │
│  • Code signing verification                                                │
│  • Deserialization of untrusted data                                        │
│  • Enforcement: LLM review + Semgrep                                        │
│                                                                              │
│  A09:2025 - Security Logging and Monitoring Failures                        │
│  ──────────────────────────────────────────────────────                      │
│  • Missing audit logs                                                       │
│  • Insufficient log context                                                 │
│  • Log injection vulnerabilities                                            │
│  • Enforcement: Semgrep logging rules                                       │
│                                                                              │
│  A10:2025 - Server-Side Request Forgery (SSRF)                              │
│  ─────────────────────────────────────────────────────                       │
│  • URL validation bypass                                                    │
│  • Internal network access                                                  │
│  • Cloud metadata access                                                    │
│  • Enforcement: Semgrep SSRF rules + Data-Flow analysis                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Implementation

```python
# src/safety/security_guarantees.py

from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class SecurityGuaranteeResult:
    """Result of security guarantee check."""
    owasp_coverage: Dict[str, bool]
    api_coverage: Dict[str, bool]
    attack_scenarios: Dict[str, bool]
    all_passed: bool


class SecurityGuarantees:
    """Enforces security guarantees."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.owasp_categories = [
            "A01_Broken_Access_Control",
            "A02_Cryptographic_Failures",
            "A03_Injection",
            "A04_Insecure_Design",
            "A05_Security_Misconfiguration",
            "A06_Vulnerable_Components",
            "A07_Auth_Failures",
            "A08_Data_Integrity_Failures",
            "A09_Logging_Monitoring_Failures",
            "A10_SSRF"
        ]
        self.api_categories = [
            "BOLA",
            "BFLA",
            "Mass_Assignment",
            "Rate_Limiting",
            "Authentication",
            "Input_Validation",
            "Output_Encoding"
        ]
        self.attack_scenarios = [
            "SQL_Injection",
            "NoSQL_Injection",
            "Command_Injection",
            "XSS",
            "CSRF",
            "SSRF",
            "Path_Traversal",
            "File_Upload",
            "Auth_Bypass",
            "Privilege_Escalation"
        ]

    def check_owasp_coverage(
        self,
        scan_results: Dict
    ) -> Dict[str, bool]:
        """Checks OWASP Top 10 coverage."""
        coverage = {}

        for category in self.owasp_categories:
            # Check if category was scanned
            scanned = category in scan_results.get("categories_scanned", [])

            # Check if any issues were found
            issues_found = len(
                scan_results.get("findings", {}).get(category, [])
            ) > 0

            # Coverage means we checked for this category
            coverage[category] = scanned

        return coverage

    def check_api_coverage(
        self,
        scan_results: Dict
    ) -> Dict[str, bool]:
        """Checks API Security coverage."""
        coverage = {}

        for category in self.api_categories:
            scanned = category in scan_results.get("api_categories_scanned", [])
            coverage[category] = scanned

        return coverage

    def check_attack_scenarios(
        self,
        scan_results: Dict
    ) -> Dict[str, bool]:
        """Checks attack scenario coverage."""
        coverage = {}

        for scenario in self.attack_scenarios:
            # Check if scenario was tested
            tested = scenario in scan_results.get("scenarios_tested", [])

            # Check if any vulnerabilities were found
            vulnerabilities = scan_results.get("vulnerabilities", {}).get(
                scenario, []
            )

            coverage[scenario] = tested

        return coverage

    def verify_all_guarantees(
        self,
        scan_results: Dict
    ) -> SecurityGuaranteeResult:
        """Verifies all security guarantees."""
        owasp = self.check_owasp_coverage(scan_results)
        api = self.check_api_coverage(scan_results)
        attack = self.check_attack_scenarios(scan_results)

        all_passed = (
            all(owasp.values()) and
            all(api.values()) and
            all(attack.values())
        )

        return SecurityGuaranteeResult(
            owasp_coverage=owasp,
            api_coverage=api,
            attack_scenarios=attack,
            all_passed=all_passed
        )
```

---

## 5. Escalation Safety

### 5.1 Escalation Safety Guarantees

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ESCALATION SAFETY GUARANTEES                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  GUARANTEE 1: No Data Loss During Escalation                                │
│  ─────────────────────────────────────────────────────                       │
│  • Original code is preserved at each escalation level                      │
│  • All intermediate states are backed up                                    │
│  • Rollback is always possible                                              │
│  • Enforcement: Backup before each escalation level                         │
│                                                                              │
│  GUARANTEE 2: Clean Failure Reporting                                       │
│  ────────────────────────────────────────                                    │
│  • Every escalation produces a detailed report                              │
│  • Reports include root cause analysis                                      │
│  • Reports include fix suggestions                                          │
│  • Reports include regression tests                                         │
│  • Enforcement: Level 4 human report generation                             │
│                                                                              │
│  GUARANTEE 3: No Infinite Escalation Loops                                  │
│  ──────────────────────────────────────────────                              │
│  • Maximum 4 escalation levels                                              │
│  • Hard stop at Level 4 (human review)                                      │
│  • Timeout enforcement per level                                            │
│  • Enforcement: EscalationManager with level tracking                       │
│                                                                              │
│  GUARANTEE 4: Preserved Test Coverage                                       │
│  ─────────────────────────────────────                                       │
│  • Regression tests are preserved across escalation levels                  │
│  • Each sub-bug (Level 2) has its own tests                                 │
│  • Ensemble patches (Level 3) are tested together                           │
│  • Enforcement: Test preservation in escalation state                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Implementation

```python
# src/safety/escalation_safety.py

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json
import os


@dataclass
class EscalationBackup:
    """Backup information for escalation."""
    level: int
    timestamp: str
    state_snapshot: Dict
    backup_path: str


class EscalationSafety:
    """Manages safety during escalation."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backup_dir = config.get("safety", {}).get(
            "escalation_backup_dir",
            ".glitchunter/escalation_backups"
        )
        self.backups: List[EscalationBackup] = []

    def create_backup(
        self,
        level: int,
        state: Dict
    ) -> EscalationBackup:
        """Creates a backup before escalation level."""
        from datetime import datetime

        timestamp = datetime.utcnow().isoformat()
        backup_path = os.path.join(
            self.backup_dir,
            f"level_{level}_{timestamp.replace(':', '-')}"
        )

        os.makedirs(backup_path, exist_ok=True)

        # Save state snapshot
        state_file = os.path.join(backup_path, "state.json")
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

        # Save code snapshot
        code_dir = os.path.join(backup_path, "code")
        self._copy_code_snapshot(code_dir, state)

        backup = EscalationBackup(
            level=level,
            timestamp=timestamp,
            state_snapshot=state,
            backup_path=backup_path
        )

        self.backups.append(backup)
        return backup

    def restore_from_backup(
        self,
        backup: EscalationBackup
    ) -> Dict:
        """Restores state from backup."""
        state_file = os.path.join(backup.backup_path, "state.json")

        with open(state_file, 'r') as f:
            return json.load(f)

    def get_latest_backup(self, level: int) -> Optional[EscalationBackup]:
        """Gets the latest backup for a level."""
        level_backups = [b for b in self.backups if b.level == level]

        if not level_backups:
            return None

        return max(level_backups, key=lambda b: b.timestamp)

    def cleanup_old_backups(
        self,
        keep_per_level: int = 2
    ) -> int:
        """Cleans up old backups."""
        import shutil

        removed = 0

        # Group backups by level
        by_level: Dict[int, List[EscalationBackup]] = {}
        for backup in self.backups:
            if backup.level not in by_level:
                by_level[backup.level] = []
            by_level[backup.level].append(backup)

        # Remove old backups
        for level, backups in by_level.items():
            if len(backups) > keep_per_level:
                # Sort by timestamp
                sorted_backups = sorted(
                    backups,
                    key=lambda b: b.timestamp,
                    reverse=True
                )

                # Remove old ones
                for backup in sorted_backups[keep_per_level:]:
                    if os.path.exists(backup.backup_path):
                        shutil.rmtree(backup.backup_path)
                    self.backups.remove(backup)
                    removed += 1

        return removed

    def _copy_code_snapshot(
        self,
        code_dir: str,
        state: Dict
    ) -> None:
        """Copies code snapshot for backup."""
        import shutil

        repo_path = state.get("repository_path", ".")

        # Copy relevant files
        files_to_copy = state.get("phase1", {}).get("affected_files", [])

        for file_path in files_to_copy:
            src = os.path.join(repo_path, file_path)
            dst = os.path.join(code_dir, file_path)

            if os.path.exists(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
```

---

## 6. Configuration Reference

### 6.1 Complete Safety Configuration

```yaml
# config.yaml - Safety Section

safety:
  # Invariant enforcement
  invariants:
    no_data_loss: true
    no_silent_failure: true
    no_regression: true
    no_security_degradation: true
    no_resource_exhaustion: true
    no_infinite_loop: true

  # Resource limits
  resource_limits:
    vram_limit_mb: 23000  # Stack B
    vram_limit_mb_stack_a: 7500  # Stack A
    disk_limit_gb: 50
    memory_limit_gb: 8
    max_concurrent_operations: 10

  # Timeout configuration
  timeouts:
    operation_timeout_seconds: 300
    sandbox_timeout_seconds: 180
    mcp_timeout_seconds: 30
    escalation_timeout_seconds: 600
    total_run_timeout_minutes: 120

  # Backup configuration
  backup:
    enabled: true
    path: ".glitchunter/backups"
    keep_last_n: 5
    compress: true

  # Git worktree configuration
  git_worktree:
    enabled: true
    path: ".glitchunter/worktrees"
    auto_cleanup: true

  # Docker sandbox configuration
  sandbox:
    enabled: true
    network_disabled: true
    memory_limit: "2g"
    cpu_quota: 200000
    read_only: true
    cap_drop_all: true
    no_new_privileges: true
    tmpfs_size: "512m"

  # Coverage requirements
  coverage:
    min_coverage: 0.80
    coverage_non_regressive: true
    branch_coverage_required: true
    min_branch_coverage: 0.70

  # Security requirements
  security:
    owasp_coverage_required: true
    api_security_coverage_required: true
    attack_scenario_coverage_required: true
    severity_threshold: "high"  # Block on high/critical

  # Escalation safety
  escalation:
    max_levels: 4
    backup_enabled: true
    backup_dir: ".glitchunter/escalation_backups"
    keep_backups_per_level: 2
    timeout_per_level_seconds: 600

  # Rollback configuration
  rollback:
    auto_rollback_on_failure: true
    rollback_timeout_seconds: 60
    preserve_logs: true
    notify_on_rollback: true

  # Circuit breaker configuration
  circuit_breaker:
    enabled: true
    failure_threshold: 5
    recovery_timeout_seconds: 60
    half_open_requests: 3

  # Logging and audit
  logging:
    level: "INFO"
    file: ".glitchunter/logs/safety.log"
    audit_file: ".glitchunter/logs/audit.log"
    log_all_violations: true
    log_all_rollbacks: true
    log_all_escalations: true
```

### 6.2 Environment Variables

```bash
# .env - Safety Configuration

# Resource limits
GLITCHHUNTER_VRAM_LIMIT_MB=23000
GLITCHHUNTER_DISK_LIMIT_GB=50
GLITCHHUNTER_MEMORY_LIMIT_GB=8

# Timeouts
GLITCHHUNTER_OPERATION_TIMEOUT=300
GLITCHHUNTER_SANDBOX_TIMEOUT=180
GLITCHHUNTER_TOTAL_RUN_TIMEOUT=7200

# Coverage
GLITCHHUNTER_MIN_COVERAGE=0.80
GLITCHHUNTER_COVERAGE_NON_REGRESSIVE=true

# Security
GLITCHHUNTER_OWASP_COVERAGE_REQUIRED=true
GLITCHHUNTER_SEVERITY_THRESHOLD=high

# Rollback
GLITCHHUNTER_AUTO_ROLLBACK=true
GLITCHHUNTER_ROLLBACK_TIMEOUT=60

# Logging
GLITCHHUNTER_LOG_LEVEL=INFO
GLITCHHUNTER_LOG_ALL_VIOLATIONS=true
GLITCHHUNTER_LOG_ALL_ROLLBACKS=true
```

---

## Appendix A: Safety Checklist

### A.1 Pre-Run Checklist

```
□ Resource limits configured correctly
□ Backup directory exists and is writable
□ Docker daemon is running
□ Git worktree support is available
□ Coverage tools are installed
□ Security scanning tools are updated
□ Logging is configured
□ Circuit breaker is enabled
□ Timeout values are appropriate
□ Emergency contact information is available
```

### A.2 Post-Run Checklist

```
□ All worktrees cleaned up
□ All containers stopped and removed
□ Backups created for any changes
□ Logs reviewed for violations
□ Coverage report generated
□ Security scan results reviewed
□ Rollback status verified (if applicable)
□ Escalation reports generated (if applicable)
□ Resource usage within limits
□ No orphan processes running
```

---

**END OF DOCUMENT**
