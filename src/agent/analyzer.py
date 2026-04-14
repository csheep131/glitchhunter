"""
Analyzer-Node für State Machine.

Analysiert Code und identifiziert Issues.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from prefilter.pipeline import PreFilterPipeline, PreFilterResult
from security.shield import SecurityShield, SecurityReport

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """
    Ergebnis der Code-Analyse.
    
    Attributes:
        code: Analysierter Code.
        prefilter: Pre-Filter-Ergebnis.
        security: Security-Report.
        issues: Alle gefundenen Issues.
        summary: Zusammenfassung.
    """
    
    code: str
    prefilter: Optional[PreFilterResult] = None
    security: Optional[SecurityReport] = None
    issues: list[dict] = field(default_factory=list)
    summary: str = ""
    
    @property
    def has_issues(self) -> bool:
        """True wenn Issues gefunden."""
        return len(self.issues) > 0
    
    @property
    def issue_count(self) -> int:
        """Anzahl Issues."""
        return len(self.issues)
    
    @property
    def critical_count(self) -> int:
        """Anzahl kritischer Issues."""
        return sum(1 for i in self.issues if i.get("severity") == "CRITICAL")
    
    def to_dict(self) -> dict:
        """Konvertiert zu Dict."""
        return {
            "issues": self.issues,
            "summary": self.summary,
            "has_issues": self.has_issues,
            "issue_count": self.issue_count,
            "critical_count": self.critical_count,
        }


class AnalyzerNode:
    """
    Analyzer-Node der State Machine.
    
    Führt durch:
    1. Pre-Filter-Analyse (Semgrep, AST, Complexity)
    2. Security-Analyse (OWASP, Attack-Scenarios)
    3. Issue-Aggregation
    
    Usage:
        analyzer = AnalyzerNode()
        result = analyzer.analyze(code, "python")
    """
    
    def __init__(
        self,
        enable_prefilter: bool = True,
        enable_security: bool = True,
    ) -> None:
        """
        Initialisiert Analyzer-Node.
        
        Args:
            enable_prefilter: Pre-Filter aktivieren.
            enable_security: Security-Analyse aktivieren.
        """
        self.enable_prefilter = enable_prefilter
        self.enable_security = enable_security
        
        self.prefilter_pipeline = PreFilterPipeline() if enable_prefilter else None
        self.security_shield = SecurityShield() if enable_security else None
        
        logger.info(
            f"AnalyzerNode initialisiert: "
            f"prefilter={enable_prefilter}, security={enable_security}"
        )
    
    def analyze(
        self,
        code: str,
        language: str = "python",
        context: Optional[dict] = None,
    ) -> AnalysisResult:
        """
        Analysiert Code.
        
        Args:
            code: Zu analysierender Code.
            language: Programmiersprache.
            context: Optionaler Kontext.
        
        Returns:
            AnalysisResult.
        """
        logger.info(f"Analyzer: Starte Analyse für {language}")
        
        result = AnalysisResult(code=code)
        issues = []
        
        # 1. Pre-Filter-Analyse
        if self.enable_prefilter and self.prefilter_pipeline:
            prefilter_result = self.prefilter_pipeline.analyze(code, language)
            result.prefilter = prefilter_result
            
            # Semgrep-Issues extrahieren
            for issue in prefilter_result.semgrep_issues:
                issues.append({
                    "type": "semgrep",
                    "severity": issue.severity,
                    "category": issue.rule_id,
                    "message": issue.message,
                    "line": issue.line,
                    "code": issue.code,
                })
            
            # Complexity-Issues
            if prefilter_result.complexity and prefilter_result.complexity.is_complex:
                issues.append({
                    "type": "complexity",
                    "severity": "MEDIUM",
                    "category": "Code Quality",
                    "message": f"High complexity: CC={prefilter_result.complexity.cyclomatic}",
                    "line": 0,
                })
        
        # 2. Security-Analyse
        if self.enable_security and self.security_shield:
            security_report = self.security_shield.analyze(code, language)
            result.security = security_report
            
            # Security-Findings extrahieren
            for finding in security_report.findings:
                issues.append({
                    "type": "security",
                    "severity": finding.severity,
                    "category": finding.category,
                    "message": finding.title,
                    "description": finding.description,
                    "line": finding.line,
                    "code": finding.code,
                    "remediation": finding.remediation,
                })
        
        # 3. Issues aggregieren
        result.issues = issues
        
        # 4. Summary erstellen
        result.summary = self._create_summary(result)
        
        logger.info(
            f"Analyzer: Abgeschlossen - {len(issues)} Issues, "
            f"critical={result.critical_count}"
        )
        
        return result
    
    def _create_summary(self, result: AnalysisResult) -> str:
        """
        Erstellt Zusammenfassung der Analyse.
        
        Args:
            result: AnalysisResult.
        
        Returns:
            Summary-String.
        """
        parts = []
        
        if result.prefilter:
            parts.append(f"Semgrep: {result.prefilter.issue_count} Issues")
        
        if result.security:
            parts.append(
                f"Security: {result.security.finding_count} Findings, "
                f"Risk={result.security.risk_level}"
            )
        
        if result.issues:
            critical = result.critical_count
            high = sum(1 for i in result.issues if i.get("severity") == "HIGH")
            parts.append(f"Total: {result.issue_count} Issues ({critical} critical, {high} high)")
        else:
            parts.append("Keine Issues gefunden")
        
        return " | ".join(parts)
    
    def __call__(self, state: Any) -> dict:
        """
        Callable für LangGraph.
        
        Args:
            state: AgentState.
        
        Returns:
            State-Updates.
        """
        # TODO: Typisierung verbessern
        code = getattr(state, "code", "")
        language = getattr(state, "language", "python")
        
        result = self.analyze(code, language)
        
        return {
            "findings": result.issues,
            "metadata": {
                "analysis_summary": result.summary,
                "prefilter_passed": result.prefilter.passed if result.prefilter else True,
            },
        }
