"""
Attack-Scenarios für Security-Testing.

Simuliert Angriffe um Vulnerabilities zu finden.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..core.exceptions import SecurityError

logger = logging.getLogger(__name__)


class AttackType(str, Enum):
    """Typen von Attack-Scenarios."""
    INJECTION = "injection"
    BOLA = "bola"
    AUTH_BYPASS = "auth_bypass"
    XSS = "xss"
    SSRF = "ssrf"
    CSRF = "csrf"


@dataclass
class AttackResult:
    """
    Ergebnis eines Attack-Scenarios.
    
    Attributes:
        scenario: Name des Scenarios.
        attack_type: Typ des Angriffs.
        vulnerable: True wenn Code verwundbar ist.
        payload: Verwendeter Payload.
        evidence: Beweis für Vulnerability.
        severity: Schweregrad.
    """
    
    scenario: str
    attack_type: AttackType
    vulnerable: bool
    payload: str = ""
    evidence: str = ""
    severity: str = "MEDIUM"
    
    def to_dict(self) -> dict:
        """Konvertiert zu Dict."""
        return {
            "scenario": self.scenario,
            "attack_type": self.attack_type.value,
            "vulnerable": self.vulnerable,
            "payload": self.payload,
            "evidence": self.evidence,
            "severity": self.severity,
        }


class AttackScenario:
    """
    Repräsentiert ein Attack-Scenario.
    
    Simuliert spezifische Angriffe um Vulnerabilities zu finden.
    
    Usage:
        scenario = AttackScenario.injection()
        result = scenario.simulate(code, "python")
        
        if result.vulnerable:
            print(f"Vulnerable to {scenario.name}")
    """
    
    def __init__(
        self,
        name: str,
        attack_type: AttackType,
        payloads: list[str],
        detection_patterns: list[str],
    ) -> None:
        """
        Initialisiert Attack-Scenario.
        
        Args:
            name: Name des Scenarios.
            attack_type: Typ des Angriffs.
            payloads: Test-Payloads.
            detection_patterns: Patterns zur Erkennung.
        """
        self.name = name
        self.attack_type = attack_type
        self.payloads = payloads
        self.detection_patterns = detection_patterns
    
    def simulate(self, code: str, language: str = "python") -> AttackResult:
        """
        Simuliert Angriff auf Code.
        
        Args:
            code: Zu testender Code.
            language: Programmiersprache.
        
        Returns:
            AttackResult mit Ergebnis.
        """
        # Statische Analyse: Prüfe ob Code anfällig erscheint
        vulnerable = False
        evidence = ""
        used_payload = ""
        
        for payload in self.payloads:
            if self._check_payload(code, payload):
                vulnerable = True
                used_payload = payload
                evidence = self._find_evidence(code, payload)
                break
        
        severity = self._calculate_severity(code, vulnerable)
        
        return AttackResult(
            scenario=self.name,
            attack_type=self.attack_type,
            vulnerable=vulnerable,
            payload=used_payload,
            evidence=evidence,
            severity=severity,
        )
    
    def _check_payload(self, code: str, payload: str) -> bool:
        """
        Prüft ob Payload erfolgreich wäre.
        
        Args:
            code: Code.
            payload: Test-Payload.
        
        Returns:
            True wenn Code anfällig.
        """
        import re
        
        # Einfache Pattern-Matching-Analyse
        for pattern in self.detection_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return True
        
        # Payload-spezifische Checks
        if "eval" in payload and "eval(" in code:
            return True
        
        if "'" in payload and "+" in code and "sql" in code.lower():
            return True
        
        return False
    
    def _find_evidence(self, code: str, payload: str) -> str:
        """
        Findet Evidence für Vulnerability.
        
        Args:
            code: Code.
            payload: Payload.
        
        Returns:
            Evidence-String.
        """
        lines = code.split("\n")
        
        for i, line in enumerate(lines):
            for pattern in self.detection_patterns:
                import re
                if re.search(pattern, line, re.IGNORECASE):
                    return f"Line {i+1}: {line.strip()[:100]}"
        
        return ""
    
    def _calculate_severity(self, code: str, vulnerable: bool) -> str:
        """
        Berechnet Schweregrad.
        
        Args:
            code: Code.
            vulnerable: True wenn verwundbar.
        
        Returns:
            Severity-String.
        """
        if not vulnerable:
            return "INFO"
        
        # Höhere Severity für kritische Patterns
        critical_patterns = ["eval", "exec", "system", "raw"]
        if any(p in code.lower() for p in critical_patterns):
            return "CRITICAL"
        
        high_patterns = ["execute", "query", "open", "request"]
        if any(p in code.lower() for p in high_patterns):
            return "HIGH"
        
        return "MEDIUM"
    
    @classmethod
    def injection(cls) -> "AttackScenario":
        """Erstellt Injection-Scenario."""
        return cls(
            name="SQL/Command Injection",
            attack_type=AttackType.INJECTION,
            payloads=[
                "'; DROP TABLE users; --",
                "1 OR 1=1",
                "$(cat /etc/passwd)",
                "`id`",
            ],
            detection_patterns=[
                r"execute\s*\(.*\+",
                r"cursor\.execute\s*\([^,]+\s*\+",
                r"os\.system\s*\(",
                r"eval\s*\(",
                r"exec\s*\(",
            ],
        )
    
    @classmethod
    def bola(cls) -> "AttackScenario":
        """Erstellt BOLA-Scenario (Broken Object Level Authorization)."""
        return cls(
            name="BOLA Attack",
            attack_type=AttackType.BOLA,
            payloads=[
                "/api/users/123",
                "/api/users/admin",
                "/api/orders/999",
            ],
            detection_patterns=[
                r"get_object\s*\(\s*request\.",
                r"user_id\s*=\s*request\.",
                r"id\s*=\s*kwargs\['id'\]",
            ],
        )
    
    @classmethod
    def auth_bypass(cls) -> "AttackScenario":
        """Erstellt Auth-Bypass-Scenario."""
        return cls(
            name="Authentication Bypass",
            attack_type=AttackType.AUTH_BYPASS,
            payloads=[
                "admin'--",
                "' OR '1'='1",
                "admin'/*",
            ],
            detection_patterns=[
                r"password\s*==",
                r"if\s+user\s*==",
                r"==\s*[\"']admin[\"']",
                r"login.*without.*hash",
            ],
        )
    
    @classmethod
    def xss(cls) -> "AttackScenario":
        """Erstellt XSS-Scenario."""
        return cls(
            name="Cross-Site Scripting",
            attack_type=AttackType.XSS,
            payloads=[
                "<script>alert('xss')</script>",
                "<img src=x onerror=alert(1)>",
                "javascript:alert(1)",
            ],
            detection_patterns=[
                r"render.*user.*input",
                r"\{\{.*\|\s*safe\s*\}\}",
                r"dangerouslySetInnerHTML",
                r"innerHTML\s*=",
            ],
        )
    
    @classmethod
    def ssrf(cls) -> "AttackScenario":
        """Erstellt SSRF-Scenario."""
        return cls(
            name="Server-Side Request Forgery",
            attack_type=AttackType.SSRF,
            payloads=[
                "http://169.254.169.254/latest/meta-data/",
                "http://localhost:8080",
                "file:///etc/passwd",
            ],
            detection_patterns=[
                r"requests\.get\s*\([^)]*\+[^)]*\)",
                r"urlopen\s*\([^)]*\+[^)]*\)",
                r"http://\{",
            ],
        )


def simulate_all_attacks(code: str, language: str = "python") -> list[AttackResult]:
    """
    Simuliert alle Attack-Scenarios.
    
    Args:
        code: Code.
        language: Sprache.
    
    Returns:
        Liste von AttackResults.
    """
    scenarios = [
        AttackScenario.injection(),
        AttackScenario.bola(),
        AttackScenario.auth_bypass(),
        AttackScenario.xss(),
        AttackScenario.ssrf(),
    ]
    
    results = []
    for scenario in scenarios:
        result = scenario.simulate(code, language)
        results.append(result)
        logger.debug(
            f"Attack-Scenario {scenario.name}: "
            f"vulnerable={result.vulnerable}, severity={result.severity}"
        )
    
    return results
