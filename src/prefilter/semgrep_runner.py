"""
Semgrep runner for GlitchHunter.

Executes Semgrep security and correctness scans with OWASP Top 10 2025
and API Security rules. Provides comprehensive security scanning capabilities.
"""

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.exceptions import SecurityScanError

logger = logging.getLogger(__name__)


# OWASP Top 10 2025 Categories
OWASP_TOP_10_2025 = {
    "A01": "Broken Access Control",
    "A02": "Cryptographic Failures",
    "A03": "Injection",
    "A04": "Insecure Design",
    "A05": "Security Misconfiguration",
    "A06": "Vulnerable and Outdated Components",
    "A07": "Identification and Authentication Failures",
    "A08": "Software and Data Integrity Failures",
    "A09": "Security Logging and Monitoring Failures",
    "A10": "Server-Side Request Forgery (SSRF)",
}

# API Security Top 10 Categories
API_SECURITY_TOP_10 = {
    "API1": "Broken Object Level Authorization",
    "API2": "Broken Authentication",
    "API3": "Broken Object Property Level Authorization",
    "API4": "Unrestricted Resource Consumption",
    "API5": "Broken Function Level Authorization",
    "API6": "Unrestricted Access to Sensitive Business Flows",
    "API7": "Server Side Request Forgery",
    "API8": "Security Misconfiguration",
    "API9": "Improper Inventory Management",
    "API10": "Unsafe Consumption of APIs",
}


@dataclass
class SemgrepFinding:
    """
    Represents a Semgrep finding.

    Attributes:
        rule_id: Semgrep rule identifier
        severity: Finding severity (INFO, WARNING, ERROR, CRITICAL)
        category: Finding category (security, correctness, performance)
        file_path: Path to the file with the finding
        line_start: Starting line number
        line_end: Ending line number
        column_start: Starting column number
        column_end: Ending column number
        message: Finding message
        fix: Suggested fix
        metadata: Additional metadata
    """

    rule_id: str
    severity: str
    category: str
    file_path: str
    line_start: int
    line_end: int
    column_start: int
    column_end: int
    message: str
    fix: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "category": self.category,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "column_start": self.column_start,
            "column_end": self.column_end,
            "message": self.message,
            "fix": self.fix,
            "metadata": self.metadata,
        }


@dataclass
class SemgrepResult:
    """
    Result of a Semgrep scan.

    Attributes:
        findings: List of findings
        errors: List of error messages
        scan_duration_sec: Scan duration in seconds
        files_scanned: Number of files scanned
        rules_applied: Number of rules applied
    """

    findings: List[SemgrepFinding] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    scan_duration_sec: float = 0.0
    files_scanned: int = 0
    rules_applied: int = 0

    @property
    def finding_count(self) -> int:
        """Get total number of findings."""
        return len(self.findings)

    @property
    def has_critical(self) -> bool:
        """Check if any critical findings exist."""
        return any(f.severity in ("ERROR", "CRITICAL") for f in self.findings)

    def by_severity(self) -> Dict[str, List[SemgrepFinding]]:
        """Group findings by severity."""
        result: Dict[str, List[SemgrepFinding]] = {
            "CRITICAL": [],
            "ERROR": [],
            "WARNING": [],
            "INFO": [],
        }
        for finding in self.findings:
            severity = finding.severity.upper()
            if severity in result:
                result[severity].append(finding)
        return result

    def by_category(self) -> Dict[str, List[SemgrepFinding]]:
        """Group findings by category."""
        result: Dict[str, List[SemgrepFinding]] = {
            "security": [],
            "correctness": [],
            "performance": [],
            "other": [],
        }
        for finding in self.findings:
            category = finding.category.lower()
            if category in result:
                result[category].append(finding)
            else:
                result["other"].append(finding)
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "findings": [f.to_dict() for f in self.findings],
            "errors": self.errors,
            "scan_duration_sec": self.scan_duration_sec,
            "files_scanned": self.files_scanned,
            "rules_applied": self.rules_applied,
            "summary": {
                "total_findings": self.finding_count,
                "by_severity": {k: len(v) for k, v in self.by_severity().items()},
                "by_category": {k: len(v) for k, v in self.by_category().items()},
            },
        }


class SemgrepRunner:
    """
    Runs Semgrep security and correctness scans.

    Supports OWASP Top 10 2025, API Security, and custom rules.

    Attributes:
        rules_path: Path to custom rules directory
        timeout: Scan timeout in seconds

    Example:
        >>> runner = SemgrepRunner()
        >>> result = runner.run_security_scan(Path("/path/to/repo"))
        >>> print(f"Found {result.finding_count} issues")
    """

    def __init__(
        self,
        rules_path: Optional[Path] = None,
        timeout: int = 300,
        semgrep_path: str = "semgrep",
    ) -> None:
        """
        Initialize Semgrep runner.

        Args:
            rules_path: Path to custom rules directory
            timeout: Scan timeout in seconds
            semgrep_path: Path to semgrep executable
        """
        self.rules_path = rules_path
        self.timeout = timeout
        self.semgrep_path = semgrep_path

        logger.debug(f"SemgrepRunner initialized (rules={rules_path}, timeout={timeout}s)")

    def run_security_scan(
        self,
        repo_path: Path,
        config_files: Optional[List[Path]] = None,
        languages: Optional[List[str]] = None,
    ) -> SemgrepResult:
        """
        Run security-focused Semgrep scan.

        Includes OWASP Top 10 2025 and API Security rules.

        Args:
            repo_path: Path to repository
            config_files: Additional config files
            languages: Languages to scan

        Returns:
            SemgrepResult with findings
        """
        logger.info(f"Running Semgrep security scan on {repo_path}")

        import time
        start_time = time.time()

        # Build command
        cmd = [
            self.semgrep_path,
            "--json",
            "--quiet",
            "--no-redirect",
        ]

        # Add OWASP Top 10 rules
        cmd.extend(["--config", "p/owasp-top-ten"])
        logger.debug("Including OWASP Top 10 2025 rules")

        # Add API Security rules
        cmd.extend(["--config", "p/api-security"])
        logger.debug("Including API Security Top 10 rules")

        # Add JWT security rules
        cmd.extend(["--config", "p/jwt"])
        logger.debug("Including JWT security rules")

        # Add custom rules
        if self.rules_path and self.rules_path.exists():
            cmd.extend(["--config", str(self.rules_path)])
            logger.debug(f"Using custom rules from {self.rules_path}")

        # Add additional config files
        if config_files:
            for config_file in config_files:
                if config_file.exists():
                    cmd.extend(["--config", str(config_file)])

        # Add languages filter
        if languages:
            for lang in languages:
                cmd.extend(["--lang", lang])

        # Add target path
        cmd.append(str(repo_path))

        logger.debug(f"Semgrep command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=repo_path,
            )

            scan_duration = time.time() - start_time

            # Parse JSON output
            if result.stdout:
                parsed_result = self.parse_json_output(result.stdout)
                parsed_result.scan_duration_sec = scan_duration
                return parsed_result
            else:
                if result.stderr:
                    logger.error(f"Semgrep error: {result.stderr}")
                return SemgrepResult(
                    errors=[result.stderr],
                    scan_duration_sec=scan_duration,
                )

        except subprocess.TimeoutExpired:
            raise SecurityScanError(
                f"Semgrep scan timed out after {self.timeout}s",
                scanner="semgrep",
            )

        except FileNotFoundError:
            raise SecurityScanError(
                f"Semgrep not found at '{self.semgrep_path}'",
                scanner="semgrep",
                details={"hint": "Install with: pip install semgrep"},
            )

        except Exception as e:
            raise SecurityScanError(
                f"Semgrep scan failed: {e}",
                scanner="semgrep",
            )

    def run_correctness_scan(
        self,
        repo_path: Path,
        languages: Optional[List[str]] = None,
    ) -> SemgrepResult:
        """
        Run correctness-focused Semgrep scan.

        Args:
            repo_path: Path to repository
            languages: Languages to scan

        Returns:
            SemgrepResult with findings
        """
        logger.info(f"Running Semgrep correctness scan on {repo_path}")

        import time
        start_time = time.time()

        cmd = [
            self.semgrep_path,
            "--json",
            "--quiet",
            "--no-redirect",
            "--config",
            "p/correctness",
        ]

        if languages:
            for lang in languages:
                cmd.extend(["--lang", lang])

        cmd.append(str(repo_path))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=repo_path,
            )

            scan_duration = time.time() - start_time

            if result.stdout:
                parsed_result = self.parse_json_output(result.stdout)
                parsed_result.scan_duration_sec = scan_duration
                return parsed_result
            else:
                return SemgrepResult(
                    errors=[result.stderr] if result.stderr else [],
                    scan_duration_sec=scan_duration,
                )

        except subprocess.TimeoutExpired:
            raise SecurityScanError(
                f"Semgrep correctness scan timed out after {self.timeout}s",
                scanner="semgrep",
            )

        except Exception as e:
            raise SecurityScanError(
                f"Semgrep correctness scan failed: {e}",
                scanner="semgrep",
            )

    def run_owasp_scan(
        self,
        repo_path: Path,
        languages: Optional[List[str]] = None,
    ) -> SemgrepResult:
        """
        Run OWASP Top 10 2025 focused scan.

        Args:
            repo_path: Path to repository
            languages: Languages to scan

        Returns:
            SemgrepResult with findings
        """
        logger.info(f"Running OWASP Top 10 scan on {repo_path}")

        import time
        start_time = time.time()

        cmd = [
            self.semgrep_path,
            "--json",
            "--quiet",
            "--no-redirect",
            "--config",
            "p/owasp-top-ten",
        ]

        if languages:
            for lang in languages:
                cmd.extend(["--lang", lang])

        cmd.append(str(repo_path))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=repo_path,
            )

            scan_duration = time.time() - start_time

            if result.stdout:
                parsed_result = self.parse_json_output(result.stdout)
                parsed_result.scan_duration_sec = scan_duration
                return parsed_result
            else:
                return SemgrepResult(
                    errors=[result.stderr] if result.stderr else [],
                    scan_duration_sec=scan_duration,
                )

        except Exception as e:
            raise SecurityScanError(
                f"OWASP scan failed: {e}",
                scanner="semgrep",
            )

    def run_api_security_scan(
        self,
        repo_path: Path,
        languages: Optional[List[str]] = None,
    ) -> SemgrepResult:
        """
        Run API Security Top 10 focused scan.

        Args:
            repo_path: Path to repository
            languages: Languages to scan

        Returns:
            SemgrepResult with findings
        """
        logger.info(f"Running API Security scan on {repo_path}")

        import time
        start_time = time.time()

        cmd = [
            self.semgrep_path,
            "--json",
            "--quiet",
            "--no-redirect",
            "--config",
            "p/api-security",
        ]

        if languages:
            for lang in languages:
                cmd.extend(["--lang", lang])

        cmd.append(str(repo_path))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=repo_path,
            )

            scan_duration = time.time() - start_time

            if result.stdout:
                parsed_result = self.parse_json_output(result.stdout)
                parsed_result.scan_duration_sec = scan_duration
                return parsed_result
            else:
                return SemgrepResult(
                    errors=[result.stderr] if result.stderr else [],
                    scan_duration_sec=scan_duration,
                )

        except Exception as e:
            raise SecurityScanError(
                f"API Security scan failed: {e}",
                scanner="semgrep",
            )

    def run_custom_rules(
        self,
        repo_path: Path,
        rule_files: List[Path],
    ) -> SemgrepResult:
        """
        Run scan with custom rule files.

        Args:
            repo_path: Path to repository
            rule_files: List of custom rule YAML files

        Returns:
            SemgrepResult with findings
        """
        logger.info(f"Running Semgrep with {len(rule_files)} custom rules")

        import time
        start_time = time.time()

        cmd = [
            self.semgrep_path,
            "--json",
            "--quiet",
            "--no-redirect",
        ]

        for rule_file in rule_files:
            if rule_file.exists():
                cmd.extend(["--config", str(rule_file)])
            else:
                logger.warning(f"Rule file not found: {rule_file}")

        cmd.append(str(repo_path))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=repo_path,
            )

            scan_duration = time.time() - start_time

            if result.stdout:
                parsed_result = self.parse_json_output(result.stdout)
                parsed_result.scan_duration_sec = scan_duration
                return parsed_result
            else:
                return SemgrepResult(
                    errors=[result.stderr] if result.stderr else [],
                    scan_duration_sec=scan_duration,
                )

        except Exception as e:
            raise SecurityScanError(
                f"Custom rules scan failed: {e}",
                scanner="semgrep",
            )

    def parse_json_output(self, json_str: str) -> SemgrepResult:
        """
        Parse Semgrep JSON output.

        Args:
            json_str: JSON output from Semgrep

        Returns:
            SemgrepResult with parsed findings
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Semgrep JSON: {e}")
            return SemgrepResult(errors=[f"JSON parse error: {e}"])

        findings = []

        for match in data.get("results", []):
            # Determine category from rule metadata
            rule_info = match.get("extra", {}).get("metadata", {})
            category = self._determine_category(match.get("rule_id", ""), rule_info)

            # Map severity
            severity = match.get("severity", "WARNING").upper()
            if severity == "ERROR":
                severity = "ERROR"
            elif severity == "WARNING":
                severity = "WARNING"
            elif severity in ("INFO", "NOTE"):
                severity = "INFO"
            else:
                severity = "WARNING"

            finding = SemgrepFinding(
                rule_id=match.get("rule_id", "unknown"),
                severity=severity,
                category=category,
                file_path=match.get("path", ""),
                line_start=match.get("start", {}).get("line", 0),
                line_end=match.get("end", {}).get("line", 0),
                column_start=match.get("start", {}).get("col", 0),
                column_end=match.get("end", {}).get("col", 0),
                message=match.get("message", ""),
                fix=match.get("extra", {}).get("fix"),
                metadata=rule_info,
            )
            findings.append(finding)

        # Count scanned files
        files_scanned = len(set(f.file_path for f in findings))

        # Count unique rules
        rules_applied = len(set(f.rule_id for f in findings))

        errors = []
        for error in data.get("errors", []):
            if isinstance(error, dict):
                errors.append(error.get("message", str(error)))
            else:
                errors.append(str(error))

        result = SemgrepResult(
            findings=findings,
            errors=errors,
            files_scanned=files_scanned,
            rules_applied=rules_applied,
        )

        logger.info(
            f"Semgrep scan complete: {result.finding_count} findings, "
            f"{result.rules_applied} rules, {result.files_scanned} files"
        )

        return result

    def _determine_category(self, rule_id: str, metadata: Dict[str, Any]) -> str:
        """Determine finding category from rule metadata."""
        # Check metadata for category
        category = metadata.get("category", "")
        if category:
            category_lower = category.lower()
            if "security" in category_lower:
                return "security"
            elif "correctness" in category_lower:
                return "correctness"
            elif "performance" in category_lower:
                return "performance"

        # Infer from rule ID
        rule_lower = rule_id.lower()
        if any(x in rule_lower for x in ["owasp", "cwe", "security", "injection", "xss", "csrf"]):
            return "security"
        elif any(x in rule_lower for x in ["bug", "error", "correctness"]):
            return "correctness"
        elif any(x in rule_lower for x in ["slow", "inefficient", "performance"]):
            return "performance"

        return "security"  # Default to security

    def is_available(self) -> bool:
        """
        Check if Semgrep is available.

        Returns:
            True if Semgrep is installed
        """
        try:
            result = subprocess.run(
                [self.semgrep_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_version(self) -> Optional[str]:
        """
        Get Semgrep version.

        Returns:
            Version string or None
        """
        try:
            result = subprocess.run(
                [self.semgrep_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None
