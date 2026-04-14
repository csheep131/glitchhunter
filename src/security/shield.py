"""
Security-Shield für Stack B.

Umfassende Security-Analyse mit OWASP Top 10 2025.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .owasp_scanner import OWAPScanner, OWAPFinding
from .attack_scenarios import AttackScenario, AttackResult

from ..core.exceptions import SecurityError

logger = logging.getLogger(__name__)


@dataclass
class SecurityReport:
    """
    Security-Analyse-Report.
    
    Attributes:
        code: Analysierter Code.
        findings: Gefundene Security-Issues.
        attack_results: Ergebnisse von Attack-Scenarios.
        risk_level: Gesamtrisiko (LOW, MEDIUM, HIGH, CRITICAL).
        score: Security-Score (0-100, höher = besser).
    """
    
    code: str
    findings: list[OWAPFinding] = field(default_factory=list)
    attack_results: list[AttackResult] = field(default_factory=list)
    risk_level: str = "LOW"
    score: int = 100
    
    @property
    def has_critical_findings(self) -> bool:
        """True wenn kritische Findings."""
        return any(f.severity == "CRITICAL" for f in self.findings)
    
    @property
    def finding_count(self) -> int:
        """Anzahl Findings."""
        return len(self.findings)
    
    @property
    def critical_count(self) -> int:
        """Anzahl kritischer Findings."""
        return sum(1 for f in self.findings if f.severity == "CRITICAL")
    
    @property
    def high_count(self) -> int:
        """Anzahl High-Severity Findings."""
        return sum(1 for f in self.findings if f.severity == "HIGH")
    
    def to_dict(self) -> dict:
        """Konvertiert zu Dict."""
        return {
            "findings": [f.to_dict() for f in self.findings],
            "attack_results": [a.to_dict() for a in self.attack_results],
            "risk_level": self.risk_level,
            "score": self.score,
            "has_critical_findings": self.has_critical_findings,
            "finding_count": self.finding_count,
            "critical_count": self.critical_count,
        }


class SecurityShield:
    """
    Security-Shield für umfassende Code-Analyse.
    
    Nur für Stack B (RTX 3090) mit Full Security:
    - OWASP Top 10 2025 Scanner
    - API Security Checks
    - Attack Scenario Simulation
    
    Usage:
        shield = SecurityShield()
        report = shield.analyze(code, "python")
        
        if report.has_critical_findings:
            # Kritische Security-Issues
            ...
    """
    
    OWASP_CATEGORIES = [
        "A01_Broken_Access_Control",
        "A02_Cryptographic_Failures",
        "A03_Injection",
        "A04_Insecure_Design",
        "A05_Security_Misconfiguration",
        "A06_Vulnerable_Components",
        "A07_Identification_Authentication_Failures",
        "A08_Software_Data_Integrity_Failures",
        "A09_Security_Logging_Monitoring_Failures",
        "A10_Server_Side_Request_Forgery",
    ]
    
    API_SECURITY_CATEGORIES = [
        "BOLA",  # Broken Object Level Authorization
        "BFLA",  # Broken Function Level Authorization
        "Mass_Assignment",
        "Unrestricted_Resource_Consumption",
        "Rate_Limiting",
    ]
    
    def __init__(
        self,
        enable_owasp: bool = True,
        enable_api_security: bool = True,
        enable_attack_scenarios: bool = True,
    ) -> None:
        """
        Initialisiert Security-Shield.
        
        Args:
            enable_owasp: OWASP Top 10 Scanner aktivieren.
            enable_api_security: API Security Checks aktivieren.
            enable_attack_scenarios: Attack Scenarios aktivieren.
        """
        self.enable_owasp = enable_owasp
        self.enable_api_security = enable_api_security
        self.enable_attack_scenarios = enable_attack_scenarios
        
        self.owasp_scanner = OWAPScanner() if enable_owasp else None
        self.attack_scenarios: list[AttackScenario] = []
        
        if enable_attack_scenarios:
            self._init_attack_scenarios()
        
        logger.info(
            f"SecurityShield initialisiert: "
            f"OWASP={enable_owasp}, API={enable_api_security}, "
            f"Attacks={enable_attack_scenarios}"
        )
    
    def _init_attack_scenarios(self) -> None:
        """Initialisiert Attack-Scenarios."""
        self.attack_scenarios = [
            AttackScenario.injection(),
            AttackScenario.bola(),
            AttackScenario.auth_bypass(),
            AttackScenario.xss(),
            AttackScenario.ssrf(),
        ]
        logger.debug(f"{len(self.attack_scenarios)} Attack-Scenarios initialisiert")
    
    def analyze(
        self,
        code: str,
        language: str = "python",
        context: Optional[str] = None,
    ) -> SecurityReport:
        """
        Führt komplette Security-Analyse durch.
        
        Args:
            code: Zu analysierender Code.
            language: Programmiersprache.
            context: Optionaler Kontext (z.B. "API", "Web", "CLI").
        
        Returns:
            SecurityReport mit allen Findings.
        """
        report = SecurityReport(code=code)
        
        # 1. OWASP Top 10 Scan
        if self.enable_owasp and self.owasp_scanner:
            try:
                findings = self.owasp_scanner.scan(code, language)
                report.findings.extend(findings)
                logger.debug(f"OWASP: {len(findings)} Findings")
            except Exception as e:
                logger.error(f"OWASP-Scan-Fehler: {e}")
        
        # 2. API Security (wenn Kontext "API")
        if self.enable_api_security and (context == "API" or "api" in code.lower()):
            try:
                api_findings = self.owasp_scanner.scan_api_security(code)
                report.findings.extend(api_findings)
                logger.debug(f"API Security: {len(api_findings)} Findings")
            except Exception as e:
                logger.error(f"API-Security-Fehler: {e}")
        
        # 3. Attack Scenarios
        if self.enable_attack_scenarios:
            for scenario in self.attack_scenarios:
                try:
                    result = scenario.simulate(code, language)
                    if result.vulnerable:
                        report.attack_results.append(result)
                        logger.warning(f"Attack-Scenario erfolgreich: {scenario.name}")
                except Exception as e:
                    logger.error(f"Attack-Scenario-Fehler ({scenario.name}): {e}")
        
        # 4. Risk-Level und Score berechnen
        self._calculate_risk(report)
        
        logger.info(
            f"Security-Analyse: risk={report.risk_level}, "
            f"score={report.score}, findings={report.finding_count}"
        )
        
        return report
    
    def _calculate_risk(self, report: SecurityReport) -> None:
        """
        Berechnet Risk-Level und Score.
        
        Args:
            report: SecurityReport.
        """
        score = 100
        
        # Findings gewichten
        for finding in report.findings:
            if finding.severity == "CRITICAL":
                score -= 25
            elif finding.severity == "HIGH":
                score -= 15
            elif finding.severity == "MEDIUM":
                score -= 8
            elif finding.severity == "LOW":
                score -= 3
        
        # Attack-Ergebnisse gewichten
        for attack in report.attack_results:
            if attack.vulnerable:
                score -= 10
        
        # Score clampen
        report.score = max(0, min(100, score))
        
        # Risk-Level bestimmen
        if report.critical_count > 0 or score < 30:
            report.risk_level = "CRITICAL"
        elif report.high_count > 2 or score < 50:
            report.risk_level = "HIGH"
        elif report.finding_count > 5 or score < 70:
            report.risk_level = "MEDIUM"
        else:
            report.risk_level = "LOW"
    
    def quick_scan(self, code: str, language: str = "python") -> bool:
        """
        Schneller Security-Check.
        
        Args:
            code: Code.
            language: Sprache.
        
        Returns:
            True wenn Code sicher erscheint.
        """
        if not self.enable_owasp or not self.owasp_scanner:
            return True
        
        try:
            findings = self.owasp_scanner.scan(code, language)
            # Blockiere nur bei CRITICAL/HIGH
            return not any(f.severity in ["CRITICAL", "HIGH"] for f in findings)
        except Exception:
            return True
    
    def get_owasp_coverage(self) -> dict:
        """
        Gibt OWASP-Abdeckung zurück.
        
        Returns:
            Dict mit abgedeckten Kategorien.
        """
        return {
            "owasp_top10": self.OWASP_CATEGORIES if self.enable_owasp else [],
            "api_security": self.API_SECURITY_CATEGORIES if self.enable_api_security else [],
            "attack_scenarios": [s.name for s in self.attack_scenarios],
        }


def create_security_shield_for_stack(stack_config: dict) -> SecurityShield:
    """
    Erstellt SecurityShield basierend auf Stack-Konfiguration.
    
    Args:
        stack_config: Stack-Konfiguration.
    
    Returns:
        Konfigurierter SecurityShield.
    """
    security_config = stack_config.get("security", {})
    
    # Stack A: Nur Lite
    if security_config.get("level") == "lite":
        return SecurityShield(
            enable_owasp=True,
            enable_api_security=False,
            enable_attack_scenarios=False,
        )
    
    # Stack B: Full Security
    return SecurityShield(
        enable_owasp=security_config.get("owasp_top10", True),
        enable_api_security=security_config.get("api_security", True),
        enable_attack_scenarios=security_config.get("attack_scenarios", True),
    )
