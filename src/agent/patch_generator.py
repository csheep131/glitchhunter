"""
Patch-Generator für State Machine.

Erstellt Patches für gefundene Issues.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from ..inference.engine import InferenceEngine, InferenceConfig, InferenceResult

logger = logging.getLogger(__name__)


@dataclass
class PatchResult:
    """
    Ergebnis der Patch-Generierung.
    
    Attributes:
        issue: Original-Issue.
        original_code: Original-Code.
        patched_code: Gepatchter Code.
        patch_diff: Diff-String.
        explanation: Erklärung des Patches.
        confidence: Konfidenz (0-1).
    """
    
    issue: dict
    original_code: str
    patched_code: str
    patch_diff: str = ""
    explanation: str = ""
    confidence: float = 0.0
    
    @property
    def has_patch(self) -> bool:
        """True wenn Patch generiert."""
        return bool(self.patched_code.strip()) and self.patched_code != self.original_code
    
    def to_dict(self) -> dict:
        """Konvertiert zu Dict."""
        return {
            "issue": self.issue,
            "original_code": self.original_code,
            "patched_code": self.patched_code,
            "patch_diff": self.patch_diff,
            "explanation": self.explanation,
            "confidence": self.confidence,
            "has_patch": self.has_patch,
        }


class PatchGenerator:
    """
    Patch-Generator der State Machine.
    
    Verwendet LLM um Patches für Issues zu erstellen:
    - Security-Fixes
    - Bug-Fixes
    - Code-Quality-Verbesserungen
    
    Usage:
        generator = PatchGenerator(model_path)
        patch = generator.generate(issue, code)
    """
    
    PATCH_PROMPT = """Du bist ein Code-Reparatur-Experte. Erstelle einen Patch für das folgende Issue:

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
1. Analysiere das Issue
2. Erstelle einen korrekten Patch
3. Erkläre die Änderung

ANTWORT (JSON):
{{
    "patched_code": "...",
    "explanation": "...",
    "confidence": 0.0-1.0
}}
"""
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        use_llm: bool = True,
    ) -> None:
        """
        Initialisiert Patch-Generator.
        
        Args:
            model_path: Pfad zum LLM-Modell.
            use_llm: LLM-Generierung aktivieren.
        """
        self.model_path = model_path
        self.use_llm = use_llm
        
        self._engine: Optional[InferenceEngine] = None
        
        if use_llm and model_path:
            self._init_engine()
        
        logger.info(f"PatchGenerator initialisiert: use_llm={use_llm}")
    
    def _init_engine(self) -> None:
        """Initialisiert Inference-Engine."""
        if self.model_path:
            self._engine = InferenceEngine(
                model_path=self.model_path,
                config=InferenceConfig(
                    temperature=0.2,  # Etwas höher für Kreativität
                    max_tokens=2048,
                ),
            )
    
    def generate(
        self,
        issue: dict,
        code: str,
        language: str = "python",
    ) -> PatchResult:
        """
        Generiert Patch für Issue.
        
        Args:
            issue: Zu fixendes Issue.
            code: Code.
            language: Sprache.
        
        Returns:
            PatchResult.
        """
        logger.info(f"Generiere Patch für: {issue.get('category', 'unknown')}")
        
        result = PatchResult(
            issue=issue,
            original_code=code,
        )
        
        if self.use_llm and self._engine:
            # LLM-basierte Patch-Generierung
            llm_result = self._generate_with_llm(issue, code, language)
            result.patched_code = llm_result.get("patched_code", code)
            result.explanation = llm_result.get("explanation", "")
            result.confidence = llm_result.get("confidence", 0.0)
            
            # Diff generieren
            result.patch_diff = self._generate_diff(code, result.patched_code)
        else:
            # Regelbasierte Patches
            result.patched_code = self._generate_rule_based_patch(issue, code)
            result.explanation = "Regelbasierter Patch"
            result.confidence = 0.5
            result.patch_diff = self._generate_diff(code, result.patched_code)
        
        logger.debug(
            f"Patch generiert: has_patch={result.has_patch}, "
            f"confidence={result.confidence}"
        )
        
        return result
    
    def _generate_with_llm(
        self,
        issue: dict,
        code: str,
        language: str,
    ) -> dict:
        """
        Generiert Patch mit LLM.
        
        Args:
            issue: Issue.
            code: Code.
            language: Sprache.
        
        Returns:
            LLM-Antwort als Dict.
        """
        if not self._engine:
            return {"patched_code": code, "explanation": "", "confidence": 0.0}
        
        # Prompt bauen
        prompt = self.PATCH_PROMPT.format(
            language=language,
            code=code[:3000],  # Truncate für Context-Limit
            issue_type=issue.get("type", "unknown"),
            severity=issue.get("severity", "MEDIUM"),
            category=issue.get("category", "unknown"),
            message=issue.get("message", ""),
            line=issue.get("line", 0),
        )
        
        try:
            response = self._engine.generate(
                prompt=prompt,
                system_prompt="Du bist ein Code-Reparatur-Experte. Antworte im JSON-Format.",
            )
            
            # Parse JSON-Antwort
            import json
            content = response.content.strip()
            
            start = content.find("{")
            end = content.rfind("}") + 1
            
            if start >= 0 and end > start:
                json_str = content[start:end]
                return json.loads(json_str)
            
            return {"patched_code": code, "explanation": "", "confidence": 0.0}
            
        except Exception as e:
            logger.error(f"LLM-Patch-Fehler: {e}")
            return {"patched_code": code, "explanation": "", "confidence": 0.0}
    
    def _generate_rule_based_patch(self, issue: dict, code: str) -> str:
        """
        Regelbasierter Patch.
        
        Args:
            issue: Issue.
            code: Code.
        
        Returns:
            Gepatchter Code.
        """
        # TODO: Spezifische Patches für bekannte Issues
        # Placeholder-Implementierung
        
        category = issue.get("category", "").lower()
        
        # SQL-Injection: String-Format zu Parameterized Query
        if "sql" in category and "injection" in category:
            # Sehr einfacher Pattern-Replacement
            return code.replace(
                'execute(f"',
                'execute("',
            ).replace(
                '{',
                '%s',
            ).replace(
                '}',
                '',
            )
        
        # Default: Keine Änderung
        return code
    
    def _generate_diff(self, original: str, patched: str) -> str:
        """
        Generiert Diff-String.
        
        Args:
            original: Original-Code.
            patched: Gepatchter Code.
        
        Returns:
            Diff-String.
        """
        if original == patched:
            return "Keine Änderungen"
        
        # Einfacher Diff
        original_lines = original.split("\n")
        patched_lines = patched.split("\n")
        
        diff_lines = []
        diff_lines.append("--- original")
        diff_lines.append("+++ patched")
        
        for i, (orig, patch) in enumerate(zip(original_lines, patched_lines)):
            if orig != patch:
                diff_lines.append(f"-{orig}")
                diff_lines.append(f"+{patch}")
        
        return "\n".join(diff_lines)
    
    def generate_all(
        self,
        issues: list[dict],
        code: str,
        language: str = "python",
    ) -> list[PatchResult]:
        """
        Generiert Patches für alle Issues.
        
        Args:
            issues: Liste von Issues.
            code: Code.
            language: Sprache.
        
        Returns:
            Liste von PatchResults.
        """
        results = []
        current_code = code
        
        for issue in issues:
            result = self.generate(issue, current_code, language)
            
            if result.has_patch:
                results.append(result)
                current_code = result.patched_code  # Für nächsten Patch verwenden
        
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
        
        patches = self.generate_all(findings, code, language)
        
        # Code mit allen Patches
        final_code = patches[-1].patched_code if patches else code
        
        return {
            "code": final_code,
            "patches": [p.to_dict() for p in patches],
            "metadata": {
                "patch_count": len(patches),
                "patches_applied": sum(1 for p in patches if p.has_patch),
            },
        }
