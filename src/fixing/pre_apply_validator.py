"""
Pre-Apply Validator für GlitchHunter.

Validiert Patches VOR dem Anwenden mit:
- Syntax-Check + Linter
- Semantischer Diff (Tree-sitter)
- Policy-Check (max 3 Dateien, max 160 Zeilen, keine neuen Dependencies)
"""

import logging
import subprocess
import tempfile
import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.fixing.semantic_diff import SemanticDiff, SemanticDiffValidator

logger = logging.getLogger(__name__)


@dataclass
class PolicyViolation:
    """
    Policy-Verletzung.

    Attributes:
        rule: Verletzte Regel
        description: Beschreibung der Verletzung
        severity: Schweregrad (warning, error, block)
        details: Zusätzliche Details
    """

    rule: str
    description: str
    severity: str = "error"
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "rule": self.rule,
            "description": self.description,
            "severity": self.severity,
            "details": self.details,
        }


@dataclass
class Gate1Result:
    """
    Ergebnis der Pre-Apply Validierung.

    Attributes:
        passed: True wenn alle Checks bestanden.
        syntax_valid: True wenn Syntax korrekt.
        linter_valid: True wenn Linter keine Issues.
        static_score_before: Statische Bewertung vor Patch.
        static_score_after: Statische Bewertung nach Patch.
        semantic_diff_clean: True wenn semantischer Diff sauber.
        policy_violations: Liste von Policy-Verletzungen.
    """

    passed: bool = False
    syntax_valid: bool = False
    linter_valid: bool = False
    static_score_before: float = 0.0
    static_score_after: float = 0.0
    semantic_diff_clean: bool = False
    policy_violations: List[PolicyViolation] = field(default_factory=list)

    @property
    def has_blocking_violations(self) -> bool:
        """True wenn blockierende Policy-Verletzungen vorhanden."""
        return any(v.severity == "block" for v in self.policy_violations)

    @property
    def has_errors(self) -> bool:
        """True wenn Error-Level Verletzungen vorhanden."""
        return any(v.severity == "error" for v in self.policy_violations)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "passed": self.passed,
            "syntax_valid": self.syntax_valid,
            "linter_valid": self.linter_valid,
            "static_score_before": self.static_score_before,
            "static_score_after": self.static_score_after,
            "semantic_diff_clean": self.semantic_diff_clean,
            "policy_violations": [v.to_dict() for v in self.policy_violations],
            "has_blocking_violations": self.has_blocking_violations,
            "has_errors": self.has_errors,
        }


class PreApplyValidator:
    """
    Validiert Patches vor dem Anwenden (Gate 1).

    Checks:
    1. Syntax-Check (AST-Parsing)
    2. Linter (Ruff, Pylint, ESLint, etc.)
    3. Semantischer Diff (Tree-sitter)
    4. Policy-Check:
       - Max 3 Dateien berührt
       - Max 160 Zeilen geändert
       - Keine neuen Dependencies
       - Keine verbotenen Imports

    Usage:
        validator = PreApplyValidator()
        result = validator.validate(original_code, patched_code, language)
    """

    # Policy-Konstanten
    MAX_FILES_TOUCHED = 3
    MAX_LINES_CHANGED = 160
    ALLOW_NEW_DEPENDENCIES = False

    # Verbotene Imports (Security)
    FORBIDDEN_IMPORTS = {
        "os.system",
        "os.popen",
        "subprocess.call",
        "subprocess.Popen",
        "subprocess.check_output",
        "eval",
        "exec",
        "__import__",
        "pickle.load",
        "yaml.load",  # Unsafe YAML
        "marshal.load",
    }

    def __init__(
        self,
        language: str = "python",
        enable_linter: bool = True,
        enable_semantic_diff: bool = True,
    ) -> None:
        """
        Initialisiert Pre-Apply Validator.

        Args:
            language: Programmiersprache.
            enable_linter: Linter-Checks aktivieren.
            enable_semantic_diff: Semantische Diff-Analyse aktivieren.
        """
        self.language = language
        self.enable_linter = enable_linter
        self.enable_semantic_diff = enable_semantic_diff

        self.semantic_diff_validator = SemanticDiffValidator()

        logger.debug(
            f"PreApplyValidator initialisiert: language={language}, "
            f"linter={enable_linter}, semantic_diff={enable_semantic_diff}"
        )

    def validate(
        self,
        original_code: str,
        patched_code: str,
        file_path: Optional[str] = None,
        patch_diff: Optional[str] = None,
    ) -> Gate1Result:
        """
        Validiert Patch vor dem Anwenden.

        Args:
            original_code: Original-Code.
            patched_code: Gepatchter Code.
            file_path: Optionaler Dateipfad.
            patch_diff: Optionaler Diff-String.

        Returns:
            Gate1Result mit Validierungsergebnis.
        """
        logger.info("Starte Pre-Apply Validierung (Gate 1)")

        result = Gate1Result()

        # 1. Syntax-Check
        result.syntax_valid = self._check_syntax(patched_code)
        if not result.syntax_valid:
            logger.warning("Syntax-Check fehlgeschlagen")
            result.policy_violations.append(PolicyViolation(
                rule="syntax_check",
                description="Syntax-Fehler im gepatchten Code",
                severity="block",
            ))

        # 2. Linter-Check
        if self.enable_linter:
            result.linter_valid, linter_issues = self._check_linter(patched_code)
            if not result.linter_valid:
                logger.warning(f"Linter-Check fehlgeschlagen: {linter_issues}")
                result.policy_violations.append(PolicyViolation(
                    rule="linter_check",
                    description=f"Linter-Issues: {linter_issues}",
                    severity="error" if len(linter_issues) > 3 else "warning",
                    details={"issues": linter_issues},
                ))
        else:
            result.linter_valid = True

        # 3. Semantischer Diff
        if self.enable_semantic_diff:
            semantic_diff = self.semantic_diff_validator.compute_diff(
                original_code, patched_code, self.language
            )
            result.semantic_diff_clean = not self.semantic_diff_validator.has_unexpected_side_effects(
                semantic_diff
            )

            if not result.semantic_diff_clean:
                side_effects = self.semantic_diff_validator.get_side_effects(semantic_diff)
                for side_effect in side_effects:
                    result.policy_violations.append(PolicyViolation(
                        rule="semantic_diff",
                        description=side_effect.description,
                        severity=side_effect.severity,
                        details={"affected_symbols": side_effect.affected_symbols},
                    ))
        else:
            result.semantic_diff_clean = True

        # 4. Policy-Check
        if patch_diff:
            policy_violations = self._check_policy(patch_diff)
            result.policy_violations.extend(policy_violations)

        # Gesamtergebnis bestimmen
        result.passed = (
            result.syntax_valid
            and result.linter_valid
            and result.semantic_diff_clean
            and not result.has_blocking_violations
            and not result.has_errors
        )

        logger.info(
            f"Pre-Apply Validierung abgeschlossen: passed={result.passed}"
        )

        return result

    def validate_patch(
        self,
        patch_diff: str,
        original_code: str,
        patched_code: str,
    ) -> Gate1Result:
        """
        Validiert Patch mit Diff-String.

        Args:
            patch_diff: Unified Diff-String.
            original_code: Original-Code.
            patched_code: Gepatchter Code.

        Returns:
            Gate1Result.
        """
        return self.validate(original_code, patched_code, patch_diff=patch_diff)

    def _check_syntax(self, code: str) -> bool:
        """
        Prüft Syntax des Codes.

        Args:
            code: Zu prüfender Code.

        Returns:
            True wenn Syntax korrekt.
        """
        if self.language == "python":
            try:
                ast.parse(code)
                return True
            except SyntaxError as e:
                logger.error(f"Syntax-Fehler: {e}")
                return False

        elif self.language in ("javascript", "typescript"):
            return self._check_javascript_syntax(code)

        elif self.language == "rust":
            return self._check_rust_syntax(code)

        else:
            logger.warning(f"Syntax-Check für {self.language} nicht implementiert")
            return True  # Default: Annehmen dass OK

    def _check_javascript_syntax(self, code: str) -> bool:
        """Prüft JavaScript/TypeScript Syntax."""
        try:
            # Versuch mit subprocess und node
            result = subprocess.run(
                ["node", "--check", "-"],
                input=code,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("Node.js nicht verfügbar - überspringe JS-Syntax-Check")
            return True

    def _check_rust_syntax(self, code: str) -> bool:
        """Prüft Rust Syntax."""
        try:
            # Temporäre Datei erstellen
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".rs", delete=False
            ) as f:
                f.write(code)
                f.flush()

                result = subprocess.run(
                    ["rustc", "--emit", "metadata", f.name],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("Rust nicht verfügbar - überspringe Rust-Syntax-Check")
            return True

    def _check_linter(self, code: str) -> Tuple[bool, List[str]]:
        """
        Führt Linter-Check aus.

        Args:
            code: Zu prüfender Code.

        Returns:
            Tuple (valid, issues).
        """
        if self.language == "python":
            return self._check_python_linter(code)
        elif self.language in ("javascript", "typescript"):
            return self._check_javascript_linter(code)
        elif self.language == "rust":
            return self._check_rust_linter(code)
        else:
            return True, []

    def _check_python_linter(self, code: str) -> Tuple[bool, List[str]]:
        """Prüft Python-Code mit Ruff."""
        issues = []

        try:
            # Ruff bevorzugen (schneller)
            result = subprocess.run(
                ["ruff", "check", "-", "--output-format=json"],
                input=code,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                import json
                try:
                    ruff_issues = json.loads(result.stdout)
                    issues = [
                        f"{q['code']}: {q['message']} (Zeile {q['location']['row']})"
                        for q in ruff_issues
                    ]
                except (json.JSONDecodeError, KeyError):
                    issues = ["Ruff-Check fehlgeschlagen"]

        except (subprocess.SubprocessError, FileNotFoundError):
            # Fallback zu Pylint
            try:
                result = subprocess.run(
                    ["pylint", "--output-format=json", "-"],
                    input=code,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode != 0:
                    import json
                    try:
                        pylint_issues = json.loads(result.stdout)
                        issues = [
                            f"{q['symbol']}: {q['message']} (Zeile {q['line']})"
                            for q in pylint_issues
                            if q["type"] in ("error", "warning")
                        ]
                    except (json.JSONDecodeError, KeyError):
                        issues = ["Pylint-Check fehlgeschlagen"]

            except (subprocess.SubprocessError, FileNotFoundError):
                logger.warning("Kein Python-Linter verfügbar - überspringe Linter-Check")
                return True, []

        # Issues bewerten
        if len(issues) > 5:
            return False, issues
        elif len(issues) > 0:
            logger.debug(f"Linter-Issues gefunden: {issues}")

        return len(issues) == 0, issues

    def _check_javascript_linter(self, code: str) -> Tuple[bool, List[str]]:
        """Prüft JavaScript/TypeScript mit ESLint."""
        issues = []

        try:
            # ESLint mit stdin
            result = subprocess.run(
                ["npx", "eslint", "--stdin", "--format=json"],
                input=code,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                import json
                try:
                    eslint_issues = json.loads(result.stdout)
                    if eslint_issues:
                        issues = [
                            f"{q['ruleId']}: {q['message']} (Zeile {q['line']})"
                            for q in eslint_issues[0].get("messages", [])
                        ]
                except (json.JSONDecodeError, KeyError):
                    issues = ["ESLint-Check fehlgeschlagen"]

        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("ESLint nicht verfügbar - überspringe JS-Linter-Check")
            return True, []

        return len(issues) == 0, issues

    def _check_rust_linter(self, code: str) -> Tuple[bool, List[str]]:
        """Prüft Rust mit Clippy."""
        issues = []

        try:
            # Temporäres Cargo-Projekt erstellen
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)

                # Cargo.toml erstellen
                cargo_toml = tmpdir_path / "Cargo.toml"
                cargo_toml.write_text("""
[package]
name = "temp"
version = "0.1.0"
edition = "2021"
""")

                # src/main.rs erstellen
                src_dir = tmpdir_path / "src"
                src_dir.mkdir()
                main_rs = src_dir / "main.rs"
                main_rs.write_text(code)

                # Clippy ausführen
                result = subprocess.run(
                    ["cargo", "clippy", "--message-format=json"],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                # JSON-Output parsen
                for line in result.stdout.split("\n"):
                    if line.strip():
                        try:
                            msg = json.loads(line)
                            if msg.get("reason") == "compiler-message":
                                message = msg["message"]["message"]
                                if "error" in msg["message"]["level"]:
                                    issues.append(f"Clippy: {message}")
                        except (json.JSONDecodeError, KeyError):
                            continue

        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("Clippy nicht verfügbar - überspringe Rust-Linter-Check")
            return True, []

        return len(issues) == 0, issues

    def _check_policy(self, patch_diff: str) -> List[PolicyViolation]:
        """
        Prüft Policy-Regeln.

        Args:
            patch_diff: Unified Diff-String.

        Returns:
            Liste von Policy-Verletzungen.
        """
        violations = []

        # 1. Anzahl berührter Dateien prüfen
        files_touched = self._count_files_touched(patch_diff)
        if files_touched > self.MAX_FILES_TOUCHED:
            violations.append(PolicyViolation(
                rule="max_files_touched",
                description=f"Patch berührt {files_touched} Dateien (Maximum: {self.MAX_FILES_TOUCHED})",
                severity="block",
                details={"files_touched": files_touched},
            ))

        # 2. Anzahl geänderter Zeilen prüfen
        lines_changed = self._count_lines_changed(patch_diff)
        if lines_changed > self.MAX_LINES_CHANGED:
            violations.append(PolicyViolation(
                rule="max_lines_changed",
                description=f"Patch ändert {lines_changed} Zeilen (Maximum: {self.MAX_LINES_CHANGED})",
                severity="block" if lines_changed > self.MAX_LINES_CHANGED * 2 else "error",
                details={"lines_changed": lines_changed},
            ))

        # 3. Neue Dependencies prüfen
        if self.ALLOW_NEW_DEPENDENCIES:
            new_deps = self._find_new_dependencies(patch_diff)
            if new_deps:
                violations.append(PolicyViolation(
                    rule="no_new_dependencies",
                    description=f"Patch fügt neue Dependencies hinzu: {new_deps}",
                    severity="error",
                    details={"new_dependencies": new_deps},
                ))

        # 4. Verbotene Imports prüfen
        forbidden_imports = self._find_forbidden_imports(patch_diff)
        if forbidden_imports:
            violations.append(PolicyViolation(
                rule="forbidden_imports",
                description=f"Patch verwendet verbotene Imports: {forbidden_imports}",
                severity="block",
                details={"forbidden_imports": forbidden_imports},
            ))

        return violations

    def _count_files_touched(self, patch_diff: str) -> int:
        """Zählt Anzahl berührter Dateien im Diff."""
        files = set()

        for line in patch_diff.split("\n"):
            if line.startswith("+++ ") or line.startswith("--- "):
                # Dateiname extrahieren
                parts = line.split(" ", 2)
                if len(parts) > 1:
                    filename = parts[1].split("/")[-1]
                    if filename and filename != "/dev/null":
                        files.add(filename)

        return len(files)

    def _count_lines_changed(self, patch_diff: str) -> int:
        """Zählt Anzahl geänderter Zeilen im Diff."""
        lines_changed = 0

        for line in patch_diff.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                lines_changed += 1
            elif line.startswith("-") and not line.startswith("---"):
                lines_changed += 1

        return lines_changed

    def _find_new_dependencies(self, patch_diff: str) -> List[str]:
        """Findet neue Dependencies im Diff."""
        new_deps = []

        # requirements.txt Änderungen
        for line in patch_diff.split("\n"):
            if line.startswith("+") and "requirements.txt" in line:
                # Package-Name extrahieren
                package = line[1:].strip().split("==")[0].split(">=")[0]
                if package and package not in ("#", "-r", "-e"):
                    new_deps.append(package)

        # package.json Änderungen (JavaScript)
        if '"dependencies"' in patch_diff or '"devDependencies"' in patch_diff:
            # Einfache Heuristik für neue Dependencies
            for line in patch_diff.split("\n"):
                if line.startswith('+    "') and ":" in line:
                    package = line.split('"')[1]
                    new_deps.append(package)

        # Cargo.toml Änderungen (Rust)
        if "[dependencies]" in patch_diff:
            for line in patch_diff.split("\n"):
                if line.startswith("+") and "=" in line and "[dependencies]" not in line:
                    package = line[1:].split("=")[0].strip()
                    new_deps.append(package)

        return new_deps

    def _find_forbidden_imports(self, patch_diff: str) -> List[str]:
        """Findet verbotene Imports im Diff."""
        forbidden = []

        for line in patch_diff.split("\n"):
            if line.startswith("+"):
                for forbidden_import in self.FORBIDDEN_IMPORTS:
                    if forbidden_import in line:
                        forbidden.append(forbidden_import)

        return list(set(forbidden))

    def __call__(self, state: Any) -> Dict[str, Any]:
        """
        Callable für LangGraph.

        Args:
            state: AgentState.

        Returns:
            State-Updates.
        """
        # TODO: Typisierung verbessern
        original_code = getattr(state, "original_code", "")
        patched_code = getattr(state, "patched_code", "")
        patch_diff = getattr(state, "patch_diff", "")

        result = self.validate(original_code, patched_code, patch_diff=patch_diff)

        return {
            "gate1_result": result.to_dict(),
            "metadata": {
                "gate1_passed": result.passed,
                "syntax_valid": result.syntax_valid,
                "linter_valid": result.linter_valid,
                "semantic_diff_clean": result.semantic_diff_clean,
                "policy_violations_count": len(result.policy_violations),
            },
        }
