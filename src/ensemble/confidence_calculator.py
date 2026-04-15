"""
Fix Confidence Calculator für GlitchHunter v2.0

Berechnet detaillierte Confidence Scores für Fixes mit Begründungen.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import ast
import re

logger = logging.getLogger(__name__)


class ConfidenceFactor(Enum):
    """Faktoren die in die Confidence-Berechnung einfließen."""
    SYNTAX_VALIDITY = "syntax_validity"
    TEST_PRESERVATION = "test_preservation"
    NO_NEW_DEPS = "no_new_dependencies"
    API_COMPATIBILITY = "api_compatibility"
    SEMANTIC_CORRECTNESS = "semantic_correctness"
    COMPLEXITY_REDUCTION = "complexity_reduction"
    SECURITY_IMPROVEMENT = "security_improvement"


@dataclass
class ConfidenceScore:
    """Detaillierter Confidence Score mit Begründung."""
    overall_score: float  # 0-100
    factors: Dict[ConfidenceFactor, float]
    explanation: str
    warnings: List[str]
    recommendations: List[str]
    confidence_level: str  # "high", "medium", "low"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "factors": {k.value: v for k, v in self.factors.items()},
            "explanation": self.explanation,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "confidence_level": self.confidence_level,
        }


class ConfidenceCalculator:
    """
    Berechnet Confidence Scores für generierte Fixes.
    
    Analysiert:
    - Syntax-Korrektheit
    - Test-Erhaltung
    - Keine neuen Dependencies
    - API-Kompatibilität
    - Semantische Korrektheit
    """
    
    def __init__(self):
        self.factor_weights = {
            ConfidenceFactor.SYNTAX_VALIDITY: 0.20,
            ConfidenceFactor.TEST_PRESERVATION: 0.25,
            ConfidenceFactor.NO_NEW_DEPS: 0.15,
            ConfidenceFactor.API_COMPATIBILITY: 0.20,
            ConfidenceFactor.SEMANTIC_CORRECTNESS: 0.20,
        }
    
    def calculate(
        self,
        original_code: str,
        fixed_code: str,
        file_path: str,
        test_results: Optional[Dict[str, Any]] = None,
        ast_diff: Optional[Dict[str, Any]] = None,
    ) -> ConfidenceScore:
        """
        Berechnet den Confidence Score für einen Fix.
        
        Args:
            original_code: Originaler Code
            fixed_code: Fixierter Code
            file_path: Pfad zur Datei
            test_results: Optionale Test-Ergebnisse
            ast_diff: Optionaler AST-Diff
            
        Returns:
            ConfidenceScore mit detaillierter Begründung
        """
        factors = {}
        warnings = []
        recommendations = []
        
        # 1. Syntax-Validität
        syntax_score = self._check_syntax_validity(fixed_code, file_path)
        factors[ConfidenceFactor.SYNTAX_VALIDITY] = syntax_score
        if syntax_score < 100:
            warnings.append("Syntax-Validierung teilweise fehlgeschlagen")
            recommendations.append("Code manuell auf Syntaxfehler prüfen")
        
        # 2. Test-Erhaltung
        test_score = self._check_test_preservation(test_results)
        factors[ConfidenceFactor.TEST_PRESERVATION] = test_score
        if test_score < 100:
            warnings.append(f"Nicht alle Tests bestehen ({test_score:.0f}%)")
            recommendations.append("Fehlgeschlagene Tests überprüfen")
        
        # 3. Keine neuen Dependencies
        deps_score = self._check_no_new_dependencies(original_code, fixed_code)
        factors[ConfidenceFactor.NO_NEW_DEPS] = deps_score
        if deps_score < 100:
            warnings.append("Neue Imports/Dependencies erkannt")
            recommendations.append("Neue Dependencies auf Sicherheit prüfen")
        
        # 4. API-Kompatibilität
        api_score = self._check_api_compatibility(original_code, fixed_code, ast_diff)
        factors[ConfidenceFactor.API_COMPATIBILITY] = api_score
        if api_score < 100:
            warnings.append("Potenzielle API-Inkompatibilität erkannt")
            recommendations.append("API-Änderungen dokumentieren")
        
        # 5. Semantische Korrektheit
        semantic_score = self._check_semantic_correctness(original_code, fixed_code, ast_diff)
        factors[ConfidenceFactor.SEMANTIC_CORRECTNESS] = semantic_score
        if semantic_score < 80:
            warnings.append("Semantische Änderungen signifikant")
            recommendations.append("Logik-Änderung gründlich testen")
        
        # Gesamt-Score berechnen
        overall = sum(
            score * self.factor_weights.get(factor, 0.1)
            for factor, score in factors.items()
        )
        
        # Confidence-Level bestimmen
        if overall >= 90:
            level = "high"
        elif overall >= 70:
            level = "medium"
        else:
            level = "low"
        
        # Begründung generieren
        explanation = self._generate_explanation(factors, overall)
        
        logger.info(f"Confidence Score berechnet: {overall:.1f}/100 ({level})")
        
        return ConfidenceScore(
            overall_score=round(overall, 1),
            factors=factors,
            explanation=explanation,
            warnings=warnings,
            recommendations=recommendations,
            confidence_level=level,
        )
    
    def _check_syntax_validity(self, code: str, file_path: str) -> float:
        """Prüft Syntax-Validität des Codes."""
        if file_path.endswith('.py'):
            try:
                ast.parse(code)
                return 100.0
            except SyntaxError as e:
                logger.warning(f"Syntax-Fehler: {e}")
                return 0.0
        # Für andere Sprachen: Basis-Heuristik
        # Prüfe auf unbalanced braces, etc.
        score = 100.0
        open_braces = code.count('{') - code.count('}')
        open_parens = code.count('(') - code.count(')')
        open_brackets = code.count('[') - code.count(']')
        
        if open_braces != 0 or open_parens != 0 or open_brackets != 0:
            score -= 50.0
        
        return max(0.0, score)
    
    def _check_test_preservation(self, test_results: Optional[Dict[str, Any]]) -> float:
        """Prüft ob Tests erhalten bleiben."""
        if not test_results:
            return 75.0  # Neutral wenn keine Tests
        
        total = test_results.get("total", 0)
        passed = test_results.get("passed", 0)
        
        if total == 0:
            return 75.0
        
        return (passed / total) * 100
    
    def _check_no_new_dependencies(
        self, original: str, fixed: str
    ) -> float:
        """Prüft ob neue Dependencies hinzugefügt wurden."""
        orig_imports = self._extract_imports(original)
        fixed_imports = self._extract_imports(fixed)
        
        new_imports = fixed_imports - orig_imports
        
        if not new_imports:
            return 100.0
        
        # Bewerte neue Imports
        # Standard-Library ist OK, externe nicht
        stdlib_modules = {
            'os', 'sys', 'json', 're', 'datetime', 'collections',
            'itertools', 'functools', 'typing', 'pathlib', 'hashlib',
            'random', 'string', 'math', 'statistics', 'decimal',
            'urllib', 'http', 'socket', 'subprocess', 'tempfile',
            'shutil', 'glob', 'fnmatch', 'pickle', 'copy', 'pprint',
            'textwrap', 'enum', 'dataclasses', 'abc', 'inspect',
        }
        
        risky_imports = [imp for imp in new_imports if imp.split('.')[0] not in stdlib_modules]
        
        if not risky_imports:
            return 100.0
        
        # Abzug proportional zu neuen externen Imports
        penalty = min(len(risky_imports) * 20, 50)
        return 100.0 - penalty
    
    def _extract_imports(self, code: str) -> Set[str]:
        """Extrahiert Imports aus Python-Code."""
        imports = set()
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])
        except:
            pass
        return imports
    
    def _check_api_compatibility(
        self, original: str, fixed: str, ast_diff: Optional[Dict[str, Any]]
    ) -> float:
        """Prüft API-Kompatibilität zwischen Original und Fix."""
        score = 100.0
        
        # Extrahiere Funktions-Signaturen
        orig_sigs = self._extract_function_signatures(original)
        fixed_sigs = self._extract_function_signatures(fixed)
        
        # Prüfe auf Änderungen in öffentlichen APIs
        for func_name, orig_sig in orig_sigs.items():
            if func_name in fixed_sigs:
                fixed_sig = fixed_sigs[func_name]
                if not self._signatures_compatible(orig_sig, fixed_sig):
                    score -= 25.0
                    logger.debug(f"API-Inkompatibilität: {func_name}")
        
        # Prüfe auf entfernte öffentliche Funktionen
        for func_name in orig_sigs:
            if func_name not in fixed_sigs and not func_name.startswith('_'):
                score -= 30.0
        
        return max(0.0, score)
    
    def _extract_function_signatures(self, code: str) -> Dict[str, Dict[str, Any]]:
        """Extrahiert Funktions-Signaturen aus Code."""
        sigs = {}
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    args = []
                    defaults_start = len(node.args.args) - len(node.args.defaults)
                    for i, arg in enumerate(node.args.args):
                        arg_info = {"name": arg.arg}
                        if i >= defaults_start:
                            arg_info["default"] = True
                        args.append(arg_info)
                    sigs[node.name] = {"args": args, "vararg": bool(node.args.vararg)}
        except:
            pass
        return sigs
    
    def _signatures_compatible(self, sig1: Dict, sig2: Dict) -> bool:
        """Prüft ob zwei Signaturen kompatibel sind."""
        args1 = {a["name"]: a for a in sig1.get("args", [])}
        args2 = {a["name"]: a for a in sig2.get("args", [])}
        
        # Pflicht-Argumente dürfen nicht entfernt werden
        for name, arg in args1.items():
            if not arg.get("default") and name not in args2:
                return False
        
        return True
    
    def _check_semantic_correctness(
        self, original: str, fixed: str, ast_diff: Optional[Dict[str, Any]]
    ) -> float:
        """Bewertet semantische Korrektheit des Fixes."""
        score = 100.0
        
        # Heuristik: Anzahl der geänderten Zeilen
        orig_lines = original.split('\n')
        fixed_lines = fixed.split('\n')
        
        # Zu viele Änderungen = niedriger Score
        diff_ratio = len(fixed_lines) / max(len(orig_lines), 1)
        if diff_ratio > 2.0:
            score -= 20.0
        elif diff_ratio > 1.5:
            score -= 10.0
        
        # Prüfe auf "suspicious patterns"
        suspicious_patterns = [
            r'eval\s*\(',
            r'exec\s*\(',
            r'__import__\s*\(',
            r'subprocess\.call\s*\([^)]*shell\s*=\s*True',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, fixed):
                score -= 30.0
                logger.warning(f"Verdächtiges Pattern gefunden: {pattern}")
        
        return max(0.0, score)
    
    def _generate_explanation(
        self, factors: Dict[ConfidenceFactor, float], overall: float
    ) -> str:
        """Generiert eine natürlichsprachliche Begründung."""
        parts = []
        
        # Sortiere Faktoren nach Score
        sorted_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)
        
        high_factors = [f for f, s in sorted_factors if s >= 90]
        med_factors = [f for f, s in sorted_factors if 70 <= s < 90]
        low_factors = [f for s, s in sorted_factors if s < 70]
        
        if overall >= 90:
            parts.append(f"Fix Confidence: {overall:.0f}% – Hervorragende Qualität.")
        elif overall >= 70:
            parts.append(f"Fix Confidence: {overall:.0f}% – Gute Qualität mit kleinen Einschränkungen.")
        else:
            parts.append(f"Fix Confidence: {overall:.0f}% – Vorsicht, Qualitätsprobleme erkannt.")
        
        if high_factors:
            names = [f.value.replace('_', ' ').title() for f in high_factors[:2]]
            parts.append(f"Stärken: {', '.join(names)}.")
        
        if low_factors:
            names = [f.value.replace('_', ' ').title() for f in low_factors[:2]]
            parts.append(f"Achtung bei: {', '.join(names)}.")
        
        return " ".join(parts)