"""
Verifier-Node für State Machine.

Verifiziert gefundene Issues und priorisiert sie.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from inference.engine import InferenceEngine, InferenceConfig, InferenceResult

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """
    Ergebnis der Issue-Verifikation.
    
    Attributes:
        issue: Original-Issue.
        verified: True wenn Issue verifiziert.
        confidence: Konfidenz (0-1).
        false_positive_reason: Grund falls False Positive.
        priority: Priorität (1-5, 1=höchste).
        llm_analysis: LLM-Analyse-Text.
    """
    
    issue: dict
    verified: bool = False
    confidence: float = 0.0
    false_positive_reason: str = ""
    priority: int = 3
    llm_analysis: str = ""
    
    @property
    def is_true_positive(self) -> bool:
        """True wenn echtes Issue."""
        return self.verified and self.confidence > 0.5
    
    def to_dict(self) -> dict:
        """Konvertiert zu Dict."""
        return {
            "issue": self.issue,
            "verified": self.verified,
            "confidence": self.confidence,
            "false_positive_reason": self.false_positive_reason,
            "priority": self.priority,
            "is_true_positive": self.is_true_positive,
        }


class VerifierNode:
    """
    Verifier-Node der State Machine.
    
    Verwendet LLM um Issues zu verifizieren:
    - False Positives filtern
    - Priorität bestimmen
    - Kontext-basierte Bewertung
    
    Usage:
        verifier = VerifierNode(model_path)
        result = verifier.verify(issue, code)
    """
    
    VERIFICATION_PROMPT = """Du bist ein Code-Analyse-Experte. Verifiziere das folgende Issue:

CODE:
```{language}
{code}
```

ISSUE:
- Typ: {issue_type}
- Schweregrad: {severity}
- Kategorie: {category}
- Nachricht: {message}
- Zeile: {line}

AUFGABE:
1. Ist dies ein echtes Issue oder ein False Positive?
2. Wie hoch ist die Konfidenz (0.0-1.0)?
3. Was ist die Priorität (1-5, 1=höchste)?
4. Gib eine kurze Begründung.

ANTWORT (JSON):
{{
    "verified": true/false,
    "confidence": 0.0-1.0,
    "priority": 1-5,
    "reason": "..."
}}
"""
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        use_llm: bool = True,
    ) -> None:
        """
        Initialisiert Verifier-Node.
        
        Args:
            model_path: Pfad zum LLM-Modell.
            use_llm: LLM-Verifikation aktivieren.
        """
        self.model_path = model_path
        self.use_llm = use_llm
        
        self._engine: Optional[InferenceEngine] = None
        
        if use_llm and model_path:
            self._init_engine()
        
        logger.info(f"VerifierNode initialisiert: use_llm={use_llm}")
    
    def _init_engine(self) -> None:
        """Initialisiert Inference-Engine."""
        if self.model_path:
            self._engine = InferenceEngine(
                model_path=self.model_path,
                config=InferenceConfig(
                    temperature=0.1,
                    max_tokens=500,
                ),
            )
    
    def verify(
        self,
        issue: dict,
        code: str,
        language: str = "python",
    ) -> VerificationResult:
        """
        Verifiziert ein Issue.
        
        Args:
            issue: Zu verifizierendes Issue.
            code: Code.
            language: Sprache.
        
        Returns:
            VerificationResult.
        """
        logger.debug(f"Verifiziere Issue: {issue.get('category', 'unknown')}")
        
        result = VerificationResult(issue=issue)
        
        if self.use_llm and self._engine:
            # LLM-basierte Verifikation
            llm_result = self._verify_with_llm(issue, code, language)
            result.verified = llm_result.get("verified", False)
            result.confidence = llm_result.get("confidence", 0.0)
            result.priority = llm_result.get("priority", 3)
            result.llm_analysis = llm_result.get("reason", "")
        else:
            # Regelbasierte Verifikation
            result.verified = self._verify_rule_based(issue)
            result.confidence = 0.7 if result.verified else 0.3
            result.priority = self._calculate_priority(issue)
        
        logger.debug(
            f"Verifikation: verified={result.verified}, "
            f"confidence={result.confidence}, priority={result.priority}"
        )
        
        return result
    
    def _verify_with_llm(
        self,
        issue: dict,
        code: str,
        language: str,
    ) -> dict:
        """
        Verifiziert mit LLM.
        
        Args:
            issue: Issue.
            code: Code.
            language: Sprache.
        
        Returns:
            LLM-Antwort als Dict.
        """
        if not self._engine:
            return {"verified": False, "confidence": 0.0, "priority": 3}
        
        # Prompt bauen
        prompt = self.VERIFICATION_PROMPT.format(
            language=language,
            code=code[:2000],  # Truncate für Context-Limit
            issue_type=issue.get("type", "unknown"),
            severity=issue.get("severity", "MEDIUM"),
            category=issue.get("category", "unknown"),
            message=issue.get("message", ""),
            line=issue.get("line", 0),
        )
        
        try:
            response = self._engine.generate(
                prompt=prompt,
                system_prompt="Du bist ein Code-Analyse-Experte. Antworte präzise im JSON-Format.",
            )
            
            # Parse JSON-Antwort
            # TODO: Robustes JSON-Parsing
            import json
            content = response.content.strip()
            
            # JSON aus Response extrahieren
            start = content.find("{")
            end = content.rfind("}") + 1
            
            if start >= 0 and end > start:
                json_str = content[start:end]
                return json.loads(json_str)
            
            return {"verified": False, "confidence": 0.0, "priority": 3}
            
        except Exception as e:
            logger.error(f"LLM-Verifikation-Fehler: {e}")
            return {"verified": False, "confidence": 0.0, "priority": 3}
    
    def _verify_rule_based(self, issue: dict) -> bool:
        """
        Regelbasierte Verifikation.
        
        Args:
            issue: Issue.
        
        Returns:
            True wenn Issue wahrscheinlich echt.
        """
        # Hohe Confidence bei ERROR-Level
        if issue.get("severity") == "ERROR":
            return True
        
        # Security-Issues sind meist echt
        if issue.get("type") == "security":
            return True
        
        # Semgrep mit spezifischen Rules
        rule_id = issue.get("category", "")
        if "sql-injection" in rule_id.lower():
            return True
        if "command-injection" in rule_id.lower():
            return True
        
        # Default: Medium Confidence
        return True
    
    def _calculate_priority(self, issue: dict) -> int:
        """
        Berechnet Priorität basierend auf Severity und Typ.
        
        Args:
            issue: Issue.
        
        Returns:
            Priorität (1-5).
        """
        severity = issue.get("severity", "MEDIUM")
        issue_type = issue.get("type", "general")
        
        # Security-Issues haben höhere Priorität
        if issue_type == "security":
            if severity == "CRITICAL":
                return 1
            elif severity == "HIGH":
                return 2
            elif severity == "MEDIUM":
                return 3
        
        # Error-Level Issues
        if severity == "ERROR":
            return 2
        elif severity == "HIGH":
            return 3
        elif severity == "MEDIUM":
            return 4
        else:
            return 5
    
    def verify_all(
        self,
        issues: list[dict],
        code: str,
        language: str = "python",
    ) -> list[VerificationResult]:
        """
        Verifiziert alle Issues.
        
        Args:
            issues: Liste von Issues.
            code: Code.
            language: Sprache.
        
        Returns:
            Liste von VerificationResults.
        """
        results = []
        
        for issue in issues:
            result = self.verify(issue, code, language)
            results.append(result)
        
        # Nach Priorität sortieren
        results.sort(key=lambda r: r.priority)
        
        return results
    
    def __call__(self, state: Any) -> dict:
        """
        Callable für LangGraph.
        
        Args:
            state: AgentState.
        
        Returns:
            State-Updates.
        """
        # TODO: Typisierung verbessern
        findings = getattr(state, "findings", [])
        code = getattr(state, "code", "")
        language = getattr(state, "language", "python")
        
        results = self.verify_all(findings, code, language)
        
        # Nur verifizierte Issues behalten
        verified_findings = [r.to_dict() for r in results if r.is_true_positive]
        
        return {
            "findings": verified_findings,
            "metadata": {
                "verified_count": len(verified_findings),
                "total_verified": len(results),
            },
        }
