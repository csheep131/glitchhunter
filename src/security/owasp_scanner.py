"""
OWASP Top 10 2025 Scanner.

Scannt Code auf OWASP Top 10 2025 Vulnerabilities.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from core.exceptions import SecurityError

logger = logging.getLogger(__name__)


@dataclass
class OWAPFinding:
    """
    Repräsentiert ein OWASP-Finding.
    
    Attributes:
        category: OWASP-Kategorie (z.B. "A03_Injection").
        severity: Schweregrad (CRITICAL, HIGH, MEDIUM, LOW).
        title: Kurzer Titel.
        description: Detaillierte Beschreibung.
        line: Zeilennummer.
        code: Betroffener Code.
        remediation: Behebungsempfehlung.
        cwe: CWE-ID falls zutreffend.
    """
    
    category: str
    severity: str
    title: str
    description: str
    line: int = 0
    code: str = ""
    remediation: str = ""
    cwe: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Konvertiert zu Dict."""
        return {
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "line": self.line,
            "code": self.code,
            "remediation": self.remediation,
            "cwe": self.cwe,
        }


class OWAPScanner:
    """
    Scanner für OWASP Top 10 2025.
    
    Unterstützte Kategorien:
    - A01: Broken Access Control
    - A02: Cryptographic Failures
    - A03: Injection
    - A04: Insecure Design
    - A05: Security Misconfiguration
    - A06: Vulnerable Components
    - A07: Identification/Auth Failures
    - A08: Software/Data Integrity Failures
    - A09: Security Logging/Monitoring Failures
    - A10: Server-Side Request Forgery
    
    Usage:
        scanner = OWAPScanner()
        findings = scanner.scan(code, "python")
    """
    
    # Patterns für verschiedene Vulnerabilities
    INJECTION_PATTERNS = {
        "sql_injection": [
            r"execute\s*\(\s*[\"'].*%s",
            r"cursor\.execute\s*\([^,]+\s*\+",
            r"raw\s*\(\s*[\"'].*\{",
        ],
        "command_injection": [
            r"os\.system\s*\(",
            r"subprocess\.(call|run|Popen)\s*\([^)]*\+[^)]*\)",
            r"eval\s*\(",
            r"exec\s*\(",
        ],
        "path_traversal": [
            r"open\s*\([^)]*\+[^)]*\)",
            r"\.\./",
        ],
    }
    
    CRYPTO_PATTERNS = [
        r"MD5",
        r"SHA1",
        r"DES",
        r"RC4",
        r"password\s*=\s*[\"'][^\"']+[\"']",  # Hardcoded passwords
        r"api_key\s*=\s*[\"'][^\"']+[\"']",
        r"secret\s*=\s*[\"'][^\"']+[\"']",
    ]
    
    ACCESS_CONTROL_PATTERNS = [
        r"is_admin\s*=\s*request",  # Admin-Flag aus Request
        r"role\s*=\s*request",
        r"@app\.route.*admin.*without.*decorator",
    ]
    
    def __init__(self) -> None:
        """Initialisiert OWASP-Scanner."""
        self._patterns_compiled: dict[str, list] = {}
        self._compile_patterns()
        logger.debug("OWASP-Scanner initialisiert")
    
    def _compile_patterns(self) -> None:
        """Kompiliert Regex-Patterns."""
        for category, patterns in self.INJECTION_PATTERNS.items():
            self._patterns_compiled[category] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        
        self._patterns_compiled["crypto"] = [
            re.compile(p, re.IGNORECASE) for p in self.CRYPTO_PATTERNS
        ]
        
        self._patterns_compiled["access_control"] = [
            re.compile(p, re.IGNORECASE) for p in self.ACCESS_CONTROL_PATTERNS
        ]
    
    def scan(self, code: str, language: str = "python") -> list[OWAPFinding]:
        """
        Scannt Code auf OWASP Top 10 Vulnerabilities.
        
        Args:
            code: Zu scannender Code.
            language: Programmiersprache.
        
        Returns:
            Liste von OWAPFinding.
        """
        findings = []
        lines = code.split("\n")
        
        # A03: Injection
        findings.extend(self._scan_injection(code, lines))
        
        # A02: Cryptographic Failures
        findings.extend(self._scan_crypto(code, lines))
        
        # A01: Access Control
        findings.extend(self._scan_access_control(code, lines))
        
        # A07: Auth Failures
        findings.extend(self._scan_auth(code, lines))
        
        # A10: SSRF
        findings.extend(self._scan_ssrf(code, lines))
        
        logger.debug(f"OWASP-Scan: {len(findings)} Findings")
        return findings
    
    def _scan_injection(self, code: str, lines: list[str]) -> list[OWAPFinding]:
        """Scannt auf Injection-Vulnerabilities."""
        findings = []
        
        for category, patterns in self._patterns_compiled.items():
            if category not in ["sql_injection", "command_injection", "path_traversal"]:
                continue
            
            for pattern in patterns:
                for i, line in enumerate(lines):
                    if pattern.search(line):
                        findings.append(OWAPFinding(
                            category="A03_Injection",
                            severity="HIGH",
                            title=f"{category.replace('_', ' ').title()} detected",
                            description=f"Potentielle {category} Vulnerability gefunden",
                            line=i + 1,
                            code=line.strip(),
                            remediation=self._get_injection_remediation(category),
                            cwe=self._get_injection_cwe(category),
                        ))
        
        return findings
    
    def _scan_crypto(self, code: str, lines: list[str]) -> list[OWAPFinding]:
        """Scannt auf Cryptographic Failures."""
        findings = []
        
        for pattern in self._patterns_compiled["crypto"]:
            for i, line in enumerate(lines):
                if pattern.search(line):
                    severity = "CRITICAL" if "password" in line.lower() else "MEDIUM"
                    
                    findings.append(OWAPFinding(
                        category="A02_Cryptographic_Failures",
                        severity=severity,
                        title="Weak cryptography or hardcoded secret",
                        description="Schwache Kryptographie oder hardcoded Secret gefunden",
                        line=i + 1,
                        code=line.strip(),
                        remediation="Verwende starke Kryptographie (AES-256, bcrypt) und store Secrets in Environment Variables",
                        cwe="CWE-327",
                    ))
        
        return findings
    
    def _scan_access_control(self, code: str, lines: list[str]) -> list[OWAPFinding]:
        """Scannt auf Access Control Issues."""
        findings = []
        
        for pattern in self._patterns_compiled["access_control"]:
            for i, line in enumerate(lines):
                if pattern.search(line):
                    findings.append(OWAPFinding(
                        category="A01_Broken_Access_Control",
                        severity="HIGH",
                        title="Broken Access Control",
                        description="Access Control wird nicht richtig implementiert",
                        line=i + 1,
                        code=line.strip(),
                        remediation="Implementiere server-seitige Access-Control-Checks",
                        cwe="CWE-284",
                    ))
        
        return findings
    
    def _scan_auth(self, code: str, lines: list[str]) -> list[OWAPFinding]:
        """Scannt auf Authentication Failures."""
        findings = []
        
        # Primitive Auth-Checks
        auth_patterns = [
            (r"password\s*==\s*[\"'][^\"']+[\"']", "Hardcoded password comparison"),
            (r"if\s+user\s*==\s*[\"']admin[\"']", "Weak admin check"),
        ]
        
        for pattern_str, description in auth_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            for i, line in enumerate(lines):
                if pattern.search(line):
                    findings.append(OWAPFinding(
                        category="A07_Identification_Authentication_Failures",
                        severity="HIGH",
                        title="Weak Authentication",
                        description=description,
                        line=i + 1,
                        code=line.strip(),
                        remediation="Verwende sichere Authentication-Mechanismen (OAuth2, JWT)",
                        cwe="CWE-287",
                    ))
        
        return findings
    
    def _scan_ssrf(self, code: str, lines: list[str]) -> list[OWAPFinding]:
        """Scannt auf SSRF-Vulnerabilities."""
        findings = []
        
        ssrf_patterns = [
            r"requests\.get\s*\([^)]*\+[^)]*\)",
            r"urllib\.request\.urlopen\s*\([^)]*\+[^)]*\)",
            r"http://\{",
        ]
        
        for pattern_str in ssrf_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            for i, line in enumerate(lines):
                if pattern.search(line):
                    findings.append(OWAPFinding(
                        category="A10_Server_Side_Request_Forgery",
                        severity="HIGH",
                        title="Potential SSRF",
                        description="User-controlled URL in HTTP request",
                        line=i + 1,
                        code=line.strip(),
                        remediation="Validiere URLs gegen Allowlist, verwende keine user-controlled URLs",
                        cwe="CWE-918",
                    ))
        
        return findings
    
    def _get_injection_remediation(self, category: str) -> str:
        """Gibt Remediation für Injection-Typ."""
        remediations = {
            "sql_injection": "Verwende Parameterized Queries oder ORM",
            "command_injection": "Vermeide shell=True, verwende subprocess mit Liste",
            "path_traversal": "Validiere Pfade, verwende os.path.realpath()",
        }
        return remediations.get(category, "Input validieren und sanitizen")
    
    def _get_injection_cwe(self, category: str) -> Optional[str]:
        """Gibt CWE-ID für Injection-Typ."""
        cwes = {
            "sql_injection": "CWE-89",
            "command_injection": "CWE-78",
            "path_traversal": "CWE-22",
        }
        return cwes.get(category)
    
    def scan_api_security(self, code: str) -> list[OWAPFinding]:
        """
        Scannt spezifisch auf API-Security-Issues.
        
        Args:
            code: Code.
        
        Returns:
            API-spezifische Findings.
        """
        findings = []
        lines = code.split("\n")
        
        # BOLA (Broken Object Level Authorization)
        for i, line in enumerate(lines):
            if re.search(r"get_object\s*\(\s*request\.", line, re.IGNORECASE):
                findings.append(OWAPFinding(
                    category="API_BOLA",
                    severity="HIGH",
                    title="Potential BOLA",
                    description="Objekt-ID direkt aus Request ohne Authorization-Check",
                    line=i + 1,
                    code=line.strip(),
                    remediation="Implementiere Authorization-Checks für Objekt-Zugriff",
                    cwe="CWE-639",
                ))
        
        # Rate Limiting fehlt
        if "rate_limit" not in code.lower() and "throttle" not in code.lower():
            if "@app.route" in code or "def api_" in code:
                findings.append(OWAPFinding(
                    category="API_Rate_Limiting",
                    severity="MEDIUM",
                    title="Missing Rate Limiting",
                    description="Kein Rate Limiting für API-Endpoints",
                    line=0,
                    code="",
                    remediation="Implementiere Rate Limiting (z.B. flask-limiter)",
                    cwe="CWE-770",
                ))
        
        return findings


def scan_for_owasp(code: str, language: str = "python") -> list[OWAPFinding]:
    """
    Convenience-Funktion für OWASP-Scan.
    
    Args:
        code: Code.
        language: Sprache.
    
    Returns:
        OWASP-Findings.
    """
    scanner = OWAPScanner()
    return scanner.scan(code, language)
