"""
Auto-Refactoring für GlitchHunter v3.0.

Facade für automatisches Code-Refactoring mit:
- Modulweiser Refactoring-Engine
- Git-basiertem Rollback-Support
- Code-Improvement-Vorschlägen
"""

import asyncio
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from fixing.types import RefactoringSuggestion, RefactoringResult
from fixing.analyzers.complexity_analyzer import ComplexityAnalyzer
from fixing.analyzers.smell_analyzer import SmellAnalyzer
from fixing.analyzers.duplicate_analyzer import DuplicateAnalyzer
from fixing.refactorings.base import BaseRefactoring
from fixing.refactorings.extract_method import ExtractMethodRefactoring
from fixing.refactorings.remove_duplicate import RemoveDuplicateRefactoring
from fixing.refactorings.replace_magic_number import ReplaceMagicNumberRefactoring
from fixing.refactorings.simplify_condition import SimplifyConditionRefactoring

logger = logging.getLogger(__name__)


class AutoRefactor:
    """
    Führt automatisches Code-Refactoring durch.

    Usage:
        refactoring = AutoRefactor()
        suggestions = await refactoring.analyze_file(file_path)
        result = await refactoring.refactor_file(file_path, suggestion)
    """

    def __init__(
        self,
        use_git: bool = True,
        run_tests: bool = True,
        backup: bool = True,
    ):
        """
        Initialisiert AutoRefactor.

        Args:
            use_git: Git für Rollback verwenden
            run_tests: Tests nach Refactoring ausführen
            backup: Backup-Dateien erstellen
        """
        self.use_git = use_git
        self.run_tests = run_tests
        self.backup = backup

        self._refactoring_history: List[RefactoringResult] = []

        # Analyzer initialisieren
        self.complexity_analyzer = ComplexityAnalyzer()
        self.smell_analyzer = SmellAnalyzer()
        self.duplicate_analyzer = DuplicateAnalyzer()

        # Refactorings initialisieren
        self.refactorings: List[BaseRefactoring] = [
            ExtractMethodRefactoring(),
            RemoveDuplicateRefactoring(),
            ReplaceMagicNumberRefactoring(),
            SimplifyConditionRefactoring(),
        ]

        logger.info(
            f"AutoRefactor initialisiert: "
            f"git={use_git}, tests={run_tests}, backup={backup}"
        )

    async def analyze_file(
        self,
        file_path: Path,
        complexity_data: Optional[Dict[str, Any]] = None,
    ) -> List[RefactoringSuggestion]:
        """
        Analysiert Datei auf Refactoring-Möglichkeiten.

        Args:
            file_path: Pfad zur Datei
            complexity_data: Optionale Complexity-Daten

        Returns:
            Liste von RefactoringSuggestions
        """
        logger.info(f"Analysiere {file_path} auf Refactoring-Möglichkeiten")

        suggestions = []

        try:
            content = file_path.read_text(encoding="utf-8")

            # Complexity-Analyse
            complexity_metrics = self.complexity_analyzer.analyze(file_path, content)
            suggestions.extend(self.complexity_analyzer.get_suggestions())

            # Smell-Analyse
            smell_metrics = self.smell_analyzer.analyze(file_path, content)
            suggestions.extend(self.smell_analyzer.get_suggestions())

            # Duplikat-Analyse
            duplicate_metrics = self.duplicate_analyzer.analyze(file_path, content)
            suggestions.extend(self.duplicate_analyzer.get_suggestions())

            logger.info(f"{len(suggestions)} Refactoring-Möglichkeiten gefunden")

        except Exception as e:
            logger.error(f"Analyse fehlgeschlagen: {e}")

        return suggestions

    async def refactor_file(
        self,
        file_path: Path,
        suggestion: RefactoringSuggestion,
    ) -> RefactoringResult:
        """
        Führt Refactoring durch.

        Args:
            file_path: Pfad zur Datei
            suggestion: RefactoringSuggestion

        Returns:
            RefactoringResult
        """
        logger.info(f"Führe Refactoring durch: {suggestion.title}")

        result = RefactoringResult(suggestion=suggestion, success=False)

        try:
            # 1. Git-Commit für Rollback
            if self.use_git:
                result.git_commit = self._create_git_commit(file_path, suggestion.title)

            # 2. Backup erstellen
            if self.backup:
                backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                backup_path.write_text(file_path.read_text(encoding="utf-8"))
                result.metadata["backup_path"] = str(backup_path)

            # 3. Passendes Refactoring finden und anwenden
            content = file_path.read_text(encoding="utf-8")
            new_content = self._apply_refactoring(content, suggestion)

            # 4. Syntax prüfen
            syntax_valid = self._validate_syntax(new_content, suggestion.file_path)
            if not syntax_valid:
                result.error = "Syntax-Validierung fehlgeschlagen"
                await self._rollback(file_path, result)
                return result

            # 5. Code schreiben
            file_path.write_text(new_content, encoding="utf-8")
            result.applied_code = new_content

            # Diff generieren
            result.diff = self._generate_diff(suggestion.original_code, new_content)

            # 6. Tests ausführen
            if self.run_tests:
                test_result = await self._run_tests(file_path)
                result.test_result = test_result

                if not test_result.get("success", False):
                    result.error = "Tests fehlgeschlagen"
                    await self._rollback(file_path, result)
                    return result

            # Erfolg!
            result.success = True
            result.metadata["refactoring_type"] = self._infer_refactoring_type(suggestion)

            self._refactoring_history.append(result)

            logger.info(f"Refactoring erfolgreich: {suggestion.id}")

        except Exception as e:
            logger.error(f"Refactoring fehlgeschlagen: {e}")
            result.error = str(e)
            await self._rollback(file_path, result)

        return result

    def _apply_refactoring(
        self,
        content: str,
        suggestion: RefactoringSuggestion,
    ) -> str:
        """
        Wendet Refactoring an.

        Args:
            content: Original-Code
            suggestion: RefactoringSuggestion

        Returns:
            Neuer Code
        """
        # Passendes Refactoring finden
        for refactoring in self.refactorings:
            if refactoring.can_apply(suggestion):
                return refactoring.apply(content, suggestion)

        # Fallback: suggested_code verwenden
        if suggestion.suggested_code:
            lines = content.split("\n")
            if suggestion.line_start > 0 and suggestion.line_end > 0:
                start_idx = suggestion.line_start - 1
                end_idx = suggestion.line_end
                new_lines = suggestion.suggested_code.split("\n")
                lines[start_idx:end_idx] = new_lines
            return "\n".join(lines)

        return content

    async def _rollback(
        self,
        file_path: Path,
        result: RefactoringResult,
    ):
        """Führt Rollback durch."""
        logger.info(f"Führe Rollback durch für {file_path}")

        try:
            # Git Rollback
            if self.use_git and result.git_commit:
                self._git_rollback(result.git_commit)

            # Backup Restore
            backup_path = Path(result.metadata.get("backup_path", ""))
            if backup_path.exists():
                file_path.write_text(backup_path.read_text(encoding="utf-8"))
                backup_path.unlink()
                logger.info(f"Backup restored: {backup_path}")

        except Exception as e:
            logger.error(f"Rollback fehlgeschlagen: {e}")
            result.metadata["rollback_error"] = str(e)

    def _create_git_commit(
        self,
        file_path: Path,
        message: str,
    ) -> Optional[str]:
        """Erstellt Git-Commit vor Refactoring."""
        try:
            subprocess.run(
                ["git", "add", str(file_path)],
                check=True,
                capture_output=True,
            )

            result = subprocess.run(
                ["git", "commit", "-m", f"Pre-refactoring: {message}"],
                check=True,
                capture_output=True,
                text=True,
            )

            hash_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )

            commit_hash = hash_result.stdout.strip()
            logger.info(f"Git-Commit erstellt: {commit_hash[:8]}")

            return commit_hash

        except Exception as e:
            logger.warning(f"Git-Commit fehlgeschlagen: {e}")
            return None

    def _git_rollback(self, commit_hash: str):
        """Führt Git-Rollback durch."""
        try:
            subprocess.run(
                ["git", "reset", "--hard", commit_hash],
                check=True,
                capture_output=True,
            )
            logger.info(f"Git-Rollback durchgeführt: {commit_hash[:8]}")
        except Exception as e:
            logger.error(f"Git-Rollback fehlgeschlagen: {e}")

    def _validate_syntax(
        self,
        code: str,
        file_path: str,
    ) -> bool:
        """Validiert Syntax."""
        try:
            language = self._detect_language(Path(file_path))

            if language == "python":
                compile(code, "<string>", "exec")

            return True

        except SyntaxError:
            return False
        except Exception:
            return True

    async def _run_tests(
        self,
        file_path: Path,
    ) -> Dict[str, Any]:
        """Führt Tests aus."""
        try:
            language = self._detect_language(file_path)

            if language == "python":
                test_file = self._find_test_file(file_path)

                if test_file and test_file.exists():
                    result = subprocess.run(
                        ["python", "-m", "pytest", str(test_file), "-v"],
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )

                    return {
                        "success": result.returncode == 0,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    }

            return {"success": True, "message": "Keine Tests gefunden"}

        except Exception as e:
            logger.warning(f"Test-Ausführung fehlgeschlagen: {e}")
            return {"success": True, "message": f"Test error: {e}"}

    def _find_test_file(self, file_path: Path) -> Optional[Path]:
        """Findet Test-Datei für eine Datei."""
        test_name = f"test_{file_path.name}"
        test_path = file_path.parent / "tests" / test_name

        if test_path.exists():
            return test_path

        test_name_alt = f"{file_path.stem}_test.py"
        test_path_alt = file_path.parent / test_name_alt

        if test_path_alt.exists():
            return test_path_alt

        return None

    def _generate_diff(
        self,
        original: str,
        new: str,
    ) -> str:
        """Generiert Diff."""
        import difflib

        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile="original",
            tofile="refactored",
        )

        return "".join(diff)

    def _detect_language(self, file_path: Path) -> str:
        """Erkennt Sprache aus Extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
        }
        return ext_map.get(file_path.suffix.lower(), "python")

    def _infer_refactoring_type(
        self,
        suggestion: RefactoringSuggestion,
    ) -> str:
        """Leitet Refactoring-Typ ab."""
        category = suggestion.category.lower()

        if "complexity" in category:
            return "extract_method"
        elif "duplicate" in category:
            return "remove_duplicate"
        elif "magic" in suggestion.title.lower():
            return "replace_magic_number"
        else:
            return "other"

    def get_history(self) -> List[RefactoringResult]:
        """Returns Refactoring-Historie."""
        return self._refactoring_history

    def rollback_last(self) -> Optional[RefactoringResult]:
        """Rollback des letzten Refactorings."""
        if not self._refactoring_history:
            return None

        last = self._refactoring_history.pop()

        if last.git_commit:
            self._git_rollback(last.git_commit)

        logger.info(f"Rollback durchgeführt für {last.suggestion.id}")

        return last
