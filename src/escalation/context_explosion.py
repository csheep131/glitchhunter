"""
Context Explosion für GlitchHunter Escalation Level 1.

Erweitert den Kontext auf 160k+ Tokens mit:
- Repomix XML-Packung
- Git-Blame Integration
- Dependency-Graphs
- Call-Chains
"""

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExplodedContext:
    """
    Explodierter Kontext.

    Attributes:
        original_context: Originaler Kontext
        expanded_context: Erweiterter Kontext
        repomix_xml: Repomix XML-Inhalt
        git_blame: Git-Blame Informationen
        dependency_graph: Dependency-Graph
        call_chains: Call-Chains
        total_tokens: Geschätzte Token-Anzahl
    """

    original_context: str = ""
    expanded_context: str = ""
    repomix_xml: str = ""
    git_blame: Dict[str, Any] = field(default_factory=dict)
    dependency_graph: Dict[str, Any] = field(default_factory=dict)
    call_chains: List[str] = field(default_factory=list)
    total_tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "original_context": self.original_context[:500],
            "expanded_context": self.expanded_context[:500],
            "repomix_xml": self.repomix_xml[:500],
            "git_blame": self.git_blame,
            "dependency_graph": self.dependency_graph,
            "call_chains": self.call_chains,
            "total_tokens": self.total_tokens,
            "metadata": self.metadata,
        }


class ContextExplosion:
    """
    Context Explosion für Escalation Level 1.

    Features:
    - Repomix XML-Packung für vollständigen Repo-Kontext
    - Git-Blame für Historie
    - Dependency-Graph für Abhängigkeiten
    - Call-Chains für Aufruf-Hierarchien

    Usage:
        explosion = ContextExplosion(repo_path)
        context = explosion.explode(file_path, bug_context)
    """

    # Token-Limits
    TARGET_TOKENS = 160000  # 160k Tokens
    MAX_TOKENS = 200000  # 200k Maximum

    def __init__(
        self,
        repo_path: str,
        use_repomix: bool = True,
        use_git_blame: bool = True,
    ) -> None:
        """
        Initialisiert Context Explosion.

        Args:
            repo_path: Pfad zum Repository.
            use_repomix: Repomix verwenden.
            use_git_blame: Git-Blame verwenden.
        """
        self.repo_path = Path(repo_path)
        self.use_repomix = use_repomix
        self.use_git_blame = use_git_blame

        self._repomix_available = self._check_repomix()
        self._git_available = self._check_git()

        logger.debug(
            f"ContextExplosion initialisiert: repo={repo_path}, "
            f"repomix={self._repomix_available}, git={self._git_available}"
        )

    def _check_repomix(self) -> bool:
        """Prüft ob Repomix verfügbar ist."""
        try:
            result = subprocess.run(
                ["npx", "repomix", "--version"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def _check_git(self) -> bool:
        """Prüft ob Git verfügbar ist."""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def explode(
        self,
        file_path: str,
        bug_context: str,
        include_dependencies: bool = True,
        include_call_chains: bool = True,
    ) -> ExplodedContext:
        """
        Explodiert Kontext auf 160k+ Tokens.

        Args:
            file_path: Betroffene Datei.
            bug_context: Bug-Kontext.
            include_dependencies: Dependencies einbeziehen.
            include_call_chains: Call-Chains einbeziehen.

        Returns:
            ExplodedContext.
        """
        logger.info(f"Context Explosion für {file_path}")

        context = ExplodedContext(
            original_context=bug_context,
            metadata={
                "file_path": file_path,
                "repo_path": str(self.repo_path),
            },
        )

        # 1. Repomix XML-Packung
        if self.use_repomix and self._repomix_available:
            context.repomix_xml = self._generate_repomix_xml()
            context.expanded_context += "\n" + context.repomix_xml

        # 2. Git-Blame
        if self.use_git_blame and self._git_available:
            context.git_blame = self._get_git_blame(file_path)
            context.expanded_context += "\n\n## Git Blame\n" + self._format_git_blame(
                context.git_blame
            )

        # 3. Dependency-Graph
        if include_dependencies:
            context.dependency_graph = self._build_dependency_graph(file_path)
            context.expanded_context += (
                "\n\n## Dependencies\n"
                + self._format_dependency_graph(context.dependency_graph)
            )

        # 4. Call-Chains
        if include_call_chains:
            context.call_chains = self._extract_call_chains(file_path)
            context.expanded_context += (
                "\n\n## Call Chains\n"
                + "\n".join(context.call_chains)
            )

        # Token-Schätzung
        context.total_tokens = self._estimate_tokens(context.expanded_context)
        context.metadata["token_estimate"] = context.total_tokens

        logger.info(
            f"Context Explosion abgeschlossen: ~{context.total_tokens:,} Tokens"
        )

        return context

    def _generate_repomix_xml(self) -> str:
        """
        Generiert Repomix XML-Packung.

        Returns:
            Repomix XML-String.
        """
        try:
            # Repomix mit XML-Output
            result = subprocess.run(
                [
                    "npx", "repomix",
                    "--format", "xml",
                    "--compress",
                    "--output", "-",  # stdout
                ],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                return result.stdout
            else:
                logger.warning(f"Repomix fehlgeschlagen: {result.stderr}")
                return ""

        except Exception as e:
            logger.error(f"Repomix-Fehler: {e}")
            return ""

    def _get_git_blame(self, file_path: str) -> Dict[str, Any]:
        """
        Holt Git-Blame für Datei.

        Args:
            file_path: Dateipfad.

        Returns:
            Git-Blame als Dict.
        """
        blame_data = {}

        try:
            # Git-Blame mit Details
            result = subprocess.run(
                [
                    "git", "-C", str(self.repo_path),
                    "blame",
                    "--line-porcelain",
                    file_path,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                # Porcelain-Output parsen
                lines = result.stdout.split("\n")
                current_commit = {}

                for line in lines:
                    if line.startswith("commit "):
                        if current_commit:
                            blame_data[current_commit.get("line", 0)] = current_commit
                        current_commit = {"commit": line[7:], "line": int(current_commit.get("line", 0))}
                    elif line.startswith("\t"):
                        # Code-Line
                        current_commit["code"] = line[1:]
                    elif " " in line:
                        parts = line.split(" ", 1)
                        if len(parts) == 2:
                            current_commit[parts[0]] = parts[1]

                if current_commit:
                    blame_data[current_commit.get("line", 0)] = current_commit

        except Exception as e:
            logger.error(f"Git-Blame-Fehler: {e}")

        return blame_data

    def _format_git_blame(self, blame_data: Dict[str, Any]) -> str:
        """
        Formatiert Git-Blame.

        Args:
            blame_data: Git-Blame-Daten.

        Returns:
            Formatierter String.
        """
        lines = []

        for line_num, data in sorted(blame_data.items(), key=lambda x: x[0])[:50]:  # Max 50 Lines
            author = data.get("author", "unknown")
            commit = data.get("commit", "")[:8]
            code = data.get("code", "")

            lines.append(f"L{line_num}: {author} ({commit}): {code}")

        return "\n".join(lines)

    def _build_dependency_graph(self, file_path: str) -> Dict[str, Any]:
        """
        Baut Dependency-Graph für Datei.

        Args:
            file_path: Dateipfad.

        Returns:
            Dependency-Graph als Dict.
        """
        graph = {
            "file": file_path,
            "imports": [],
            "imported_by": [],
            "dependencies": [],
        }

        try:
            # Imports extrahieren (Python-spezifisch)
            if file_path.endswith(".py"):
                graph["imports"] = self._extract_python_imports(file_path)
                graph["imported_by"] = self._find_importers(file_path)

            # Mehr Sprachen können hinzugefügt werden

        except Exception as e:
            logger.error(f"Dependency-Graph-Fehler: {e}")

        return graph

    def _extract_python_imports(self, file_path: str) -> List[str]:
        """Extrahiert Python-Imports."""
        imports = []

        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.is_absolute():
                file_path_obj = self.repo_path / file_path

            if file_path_obj.exists():
                with open(file_path_obj) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("import ") or line.startswith("from "):
                            imports.append(line)

        except Exception as e:
            logger.error(f"Import-Extraktion-Fehler: {e}")

        return imports

    def _find_importers(self, file_path: str) -> List[str]:
        """Findet Dateien die diese Datei importieren."""
        importers = []

        try:
            # Einfache Suche nach Import-Statements
            module_name = Path(file_path).stem

            for py_file in self.repo_path.glob("**/*.py"):
                if py_file.name == Path(file_path).name:
                    continue

                try:
                    with open(py_file) as f:
                        content = f.read()
                        if f"import {module_name}" in content or f"from {module_name}" in content:
                            importers.append(str(py_file.relative_to(self.repo_path)))

                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Importer-Suche-Fehler: {e}")

        return importers

    def _format_dependency_graph(self, graph: Dict[str, Any]) -> str:
        """Formatiert Dependency-Graph."""
        lines = [
            f"File: {graph['file']}",
            "",
            "Imports:",
        ]

        for imp in graph.get("imports", []):
            lines.append(f"  - {imp}")

        lines.extend([
            "",
            "Imported by:",
        ])

        for importer in graph.get("imported_by", []):
            lines.append(f"  - {importer}")

        return "\n".join(lines)

    def _extract_call_chains(self, file_path: str) -> List[str]:
        """
        Extrahiert Call-Chains.

        Args:
            file_path: Dateipfad.

        Returns:
            Liste von Call-Chains.
        """
        chains = []

        try:
            # Einfache Call-Extraktion für Python
            if file_path.endswith(".py"):
                chains = self._extract_python_call_chains(file_path)

        except Exception as e:
            logger.error(f"Call-Chain-Extraktion-Fehler: {e}")

        return chains

    def _extract_python_call_chains(self, file_path: str) -> List[str]:
        """Extrahiert Python-Call-Chains."""
        chains = []

        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.is_absolute():
                file_path_obj = self.repo_path / file_path

            if file_path_obj.exists():
                with open(file_path_obj) as f:
                    for i, line in enumerate(f, 1):
                        line = line.strip()

                        # Funktionsaufrufe finden
                        if "(" in line and ")" in line:
                            # Einfache Heuristik
                            chains.append(f"L{i}: {line}")

        except Exception as e:
            logger.error(f"Python-Call-Chain-Fehler: {e}")

        return chains[:100]  # Max 100 Call-Chains

    def _estimate_tokens(self, text: str) -> int:
        """
        Schätzt Token-Anzahl.

        Args:
            text: Text.

        Returns:
            Geschätzte Tokens.
        """
        # Einfache Schätzung: ~4 Zeichen pro Token
        return len(text) // 4

    def __call__(self, state: Any) -> Dict[str, Any]:
        """
        Callable für LangGraph.

        Args:
            state: AgentState.

        Returns:
            State-Updates.
        """
        file_path = getattr(state, "file_path", "")
        bug_context = getattr(state, "bug_context", "")

        context = self.explode(file_path, bug_context)

        return {
            "exploded_context": context.to_dict(),
            "metadata": {
                "context_expanded": True,
                "total_tokens": context.total_tokens,
                "repomix_used": bool(context.repomix_xml),
                "git_blame_used": bool(context.git_blame),
            },
        }
