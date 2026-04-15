"""
Rule Learner für GlitchHunter.

Extrahiert Muster aus erfolgreichen Patches und generiert
neue Semgrep-Regeln für zukünftige Runs.

Vector-DB Integration:
- Qdrant (primär) für Vector-Similarity-Search
- ChromaDB (Fallback) für lokale Entwicklung
- sentence-transformers für Embeddings
"""

import logging
import re
import uuid
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CodePattern:
    """
    Extrahiertes Code-Muster.

    Attributes:
        pattern_type: Typ des Musters (fix, vulnerability, optimization)
        language: Programmiersprache
        pattern: Pattern-String
        message: Beschreibung
        severity: Schweregrad
        files_seen: Dateien in denen Pattern gesehen wurde
        fix_success_rate: Erfolgsrate des Fixes
    """

    pattern_type: str
    language: str
    pattern: str
    message: str
    severity: str = "medium"
    files_seen: List[str] = field(default_factory=list)
    fix_success_rate: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "pattern_type": self.pattern_type,
            "language": self.language,
            "pattern": self.pattern,
            "message": self.message,
            "severity": self.severity,
            "files_seen": self.files_seen,
            "fix_success_rate": self.fix_success_rate,
            "metadata": self.metadata,
        }


@dataclass
class SemgrepRule:
    """
    Semgrep-Regel.

    Attributes:
        rule_id: Eindeutige Regel-ID
        pattern: Pattern-String
        message: Fehlermeldung
        severity: Schweregrad
        languages: Betroffene Sprachen
        metadata: Zusätzliche Metadaten
    """

    rule_id: str
    pattern: str
    message: str
    severity: str
    languages: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "id": self.rule_id,
            "pattern": self.pattern,
            "message": self.message,
            "severity": self.severity,
            "languages": self.languages,
            "metadata": self.metadata,
        }

    def to_yaml(self) -> str:
        """Konvertiert zu YAML-String."""
        rule_dict = {
            "rules": [
                {
                    "id": self.rule_id,
                    "pattern": self.pattern,
                    "message": self.message,
                    "severity": self.severity,
                    "languages": self.languages,
                    **self.metadata,
                }
            ]
        }
        return yaml.dump(rule_dict, default_flow_style=False, sort_keys=False)


@dataclass
class LearningResult:
    """
    Ergebnis des Rule Learning.

    Attributes:
        patterns: Extrahierte Patterns
        semgrep_rules: Generierte Semgrep-Regeln
        rules_file: Pfad zur rules.yaml Datei
        learned_at: Lern-Zeitpunkt
    """

    patterns: List[CodePattern] = field(default_factory=list)
    semgrep_rules: List[SemgrepRule] = field(default_factory=list)
    rules_file: Optional[str] = None
    learned_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "patterns": [p.to_dict() for p in self.patterns],
            "semgrep_rules": [r.to_dict() for r in self.semgrep_rules],
            "rules_file": self.rules_file,
            "learned_at": self.learned_at.isoformat(),
            "total_patterns": len(self.patterns),
            "total_rules": len(self.semgrep_rules),
        }


class RuleLearner:
    """
    Lernt Regeln aus erfolgreichen Patches.

    Extrahiert Muster aus:
    - Erfolgreichen Patches
    - Code-Änderungen
    - Fix-Kommentaren

    Usage:
        learner = RuleLearner()
        result = learner.learn_from_patches(patches)
    """

    # Pattern-Typen
    PATTERN_FIX = "fix"
    PATTERN_VULNERABILITY = "vulnerability"
    PATTERN_OPTIMIZATION = "optimization"
    PATTERN_BEST_PRACTICE = "best_practice"

    # Severity-Mapping
    SEVERITY_MAP = {
        "critical": "CRITICAL",
        "high": "HIGH",
        "medium": "MEDIUM",
        "low": "LOW",
        "info": "INFO",
    }

    def __init__(
        self,
        output_dir: str = "src/fixing/rules",
        min_occurrences: int = 2,
    ) -> None:
        """
        Initialisiert Rule Learner.

        Args:
            output_dir: Ausgabe-Verzeichnis für rules.yaml
            min_occurrences: Minimale Vorkommen für Regel-Generierung
        """
        self.output_dir = Path(output_dir)
        self.min_occurrences = min_occurrences

        self._patterns: List[CodePattern] = []
        self._rules: List[SemgrepRule] = []

        # Output-Verzeichnis erstellen
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(
            f"RuleLearner initialisiert: output_dir={self.output_dir}, "
            f"min_occurrences={min_occurrences}"
        )

    def learn_from_patches(
        self,
        patches: List[Dict[str, Any]],
    ) -> LearningResult:
        """
        Lernt aus erfolgreichen Patches.

        Args:
            patches: Liste von erfolgreichen Patches.

        Returns:
            LearningResult.
        """
        logger.info(f"Lerne aus {len(patches)} Patches")

        result = LearningResult()

        for patch in patches:
            # Muster extrahieren
            patterns = self._extract_patterns_from_patch(patch)
            result.patterns.extend(patterns)
            self._patterns.extend(patterns)

        # Ähnliche Patterns gruppieren
        result.patterns = self._group_similar_patterns(result.patterns)

        # Semgrep-Regeln generieren
        result.semgrep_rules = self._generate_semgrep_rules(result.patterns)
        self._rules = result.semgrep_rules

        # Rules-Datei speichern
        if result.semgrep_rules:
            result.rules_file = str(self._save_rules_file(result.semgrep_rules))

        result.learned_at = datetime.now()

        logger.info(
            f"Rule Learning abgeschlossen: "
            f"{len(result.patterns)} Patterns, "
            f"{len(result.semgrep_rules)} Regeln"
        )

        return result

    def learn_from_code_diff(
        self,
        original_code: str,
        patched_code: str,
        file_path: str,
        bug_type: Optional[str] = None,
    ) -> LearningResult:
        """
        Lernt aus Code-Differenz.

        Args:
            original_code: Original-Code.
            patched_code: Gepatchter Code.
            file_path: Dateipfad.
            bug_type: Bug-Typ.

        Returns:
            LearningResult.
        """
        logger.info(f"Lerne aus Code-Diff: {file_path}")

        result = LearningResult()

        # Pattern extrahieren
        patterns = self._extract_patterns_from_diff(
            original_code, patched_code, file_path, bug_type
        )
        result.patterns = patterns
        self._patterns.extend(patterns)

        # Semgrep-Regeln generieren
        result.semgrep_rules = self._generate_semgrep_rules(patterns)
        self._rules.extend(result.semgrep_rules)

        # Rules speichern
        if result.semgrep_rules:
            result.rules_file = str(self._save_rules_file(result.semgrep_rules))

        logger.info(
            f"Code-Diff Learning abgeschlossen: "
            f"{len(result.patterns)} Patterns, "
            f"{len(result.semgrep_rules)} Regeln"
        )

        return result

    def _extract_patterns_from_patch(
        self,
        patch: Dict[str, Any],
    ) -> List[CodePattern]:
        """
        Extrahiert Muster aus Patch.

        Args:
            patch: Patch-Dict.

        Returns:
            Liste von CodePattern.
        """
        patterns = []

        patch_diff = patch.get("patch_diff", "")
        file_path = patch.get("file_path", "")
        bug_type = patch.get("bug_type", "")
        explanation = patch.get("explanation", "")

        # Sprache erkennen
        language = self._detect_language(file_path)

        # Pattern-Typ bestimmen
        pattern_type = self._determine_pattern_type(bug_type, explanation)

        # Pattern aus Diff extrahieren
        diff_patterns = self._extract_diff_patterns(patch_diff, language)

        for pattern_str in diff_patterns:
            patterns.append(CodePattern(
                pattern_type=pattern_type,
                language=language,
                pattern=pattern_str,
                message=explanation or f"Fix for {bug_type}",
                severity=self._infer_severity(bug_type),
                files_seen=[file_path],
                metadata={
                    "bug_type": bug_type,
                    "source": "patch",
                },
            ))

        return patterns

    def _extract_patterns_from_diff(
        self,
        original_code: str,
        patched_code: str,
        file_path: str,
        bug_type: Optional[str] = None,
    ) -> List[CodePattern]:
        """
        Extrahiert Muster aus Code-Differenz.

        Args:
            original_code: Original-Code.
            patched_code: Gepatchter Code.
            file_path: Dateipfad.
            bug_type: Bug-Typ.

        Returns:
            Liste von CodePattern.
        """
        patterns = []
        language = self._detect_language(file_path)

        # Zeilenweise Differenz
        original_lines = original_code.split("\n")
        patched_lines = patched_code.split("\n")

        # Removed Lines (was war vorher)
        removed = set(patched_lines) - set(original_lines)
        added = set(original_lines) - set(patched_lines)

        # Pattern aus entfernten Lines extrahieren (Bad Pattern)
        for line in removed:
            if line.strip() and not line.startswith("#"):
                pattern_str = self._generalize_line(line, language)
                if pattern_str:
                    patterns.append(CodePattern(
                        pattern_type=self.PATTERN_VULNERABILITY,
                        language=language,
                        pattern=pattern_str,
                        message=f"Problematic pattern in {file_path}",
                        severity="medium",
                        files_seen=[file_path],
                        metadata={
                            "bug_type": bug_type,
                            "source": "diff_removed",
                        },
                    ))

        # Pattern aus hinzugefügten Lines extrahieren (Good Pattern)
        for line in added:
            if line.strip() and not line.startswith("#"):
                pattern_str = self._generalize_line(line, language)
                if pattern_str:
                    patterns.append(CodePattern(
                        pattern_type=self.PATTERN_FIX,
                        language=language,
                        pattern=pattern_str,
                        message=f"Recommended fix in {file_path}",
                        severity="low",
                        files_seen=[file_path],
                        metadata={
                            "bug_type": bug_type,
                            "source": "diff_added",
                        },
                    ))

        return patterns

    def _extract_diff_patterns(
        self,
        patch_diff: str,
        language: str,
    ) -> List[str]:
        """
        Extrahiert Patterns aus Diff-String.

        Args:
            patch_diff: Diff-String.
            language: Sprache.

        Returns:
            Liste von Pattern-Strings.
        """
        patterns = []

        for line in patch_diff.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                # Hinzugefügte Line als Pattern
                code_line = line[1:].strip()
                if code_line and not code_line.startswith("#"):
                    generalized = self._generalize_line(code_line, language)
                    if generalized:
                        patterns.append(generalized)

            elif line.startswith("-") and not line.startswith("---"):
                # Entfernte Line als Anti-Pattern
                code_line = line[1:].strip()
                if code_line and not code_line.startswith("#"):
                    generalized = self._generalize_line(code_line, language)
                    if generalized:
                        patterns.append(f"NOT {generalized}")

        return patterns

    def _generalize_line(self, line: str, language: str) -> Optional[str]:
        """
        Generalisiert Line zu Pattern.

        Args:
            line: Code-Line.
            language: Sprache.

        Returns:
            Generalisiertes Pattern.
        """
        if not line.strip():
            return None

        pattern = line.strip()

        # Spezifische Werte durch Platzhalter ersetzen
        # Strings
        pattern = re.sub(r'"[^"]*"', '"..."' , pattern)
        pattern = re.sub(r"'[^']*'", "'...' ", pattern)

        # Numbers
        pattern = re.sub(r"\b\d+\b", "N", pattern)

        # Variable names (teilweise)
        if language == "python":
            # Funktionaufrufe generalisieren
            pattern = re.sub(r"\b\w+\s*\(", "FUNC(", pattern)

        return pattern if len(pattern) > 3 else None

    def _determine_pattern_type(
        self,
        bug_type: str,
        explanation: str,
    ) -> str:
        """
        Bestimmt Pattern-Typ.

        Args:
            bug_type: Bug-Typ.
            explanation: Erklärung.

        Returns:
            Pattern-Typ.
        """
        bug_type_lower = bug_type.lower()
        explanation_lower = explanation.lower()

        # Security-relevant
        if any(kw in bug_type_lower for kw in ["injection", "xss", "csrf", "auth", "security"]):
            return self.PATTERN_VULNERABILITY

        # Performance
        if any(kw in explanation_lower for kw in ["performance", "optimize", "fast"]):
            return self.PATTERN_OPTIMIZATION

        # Best Practice
        if any(kw in explanation_lower for kw in ["best practice", "convention", "standard"]):
            return self.PATTERN_BEST_PRACTICE

        # Default: Fix
        return self.PATTERN_FIX

    def _infer_severity(self, bug_type: str) -> str:
        """
        Leitet Schweregrad ab.

        Args:
            bug_type: Bug-Typ.

        Returns:
            Schweregrad.
        """
        bug_type_lower = bug_type.lower()

        if any(kw in bug_type_lower for kw in ["critical", "security", "injection"]):
            return "critical"
        elif any(kw in bug_type_lower for kw in ["high", "error", "bug"]):
            return "high"
        elif any(kw in bug_type_lower for kw in ["medium", "warning"]):
            return "medium"
        else:
            return "low"

    def _group_similar_patterns(
        self,
        patterns: List[CodePattern],
    ) -> List[CodePattern]:
        """
        Gruppiert ähnliche Patterns.

        Args:
            patterns: Liste von Patterns.

        Returns:
            Gruppierte Patterns.
        """
        grouped: Dict[str, CodePattern] = {}

        for pattern in patterns:
            key = f"{pattern.pattern_type}:{pattern.language}:{pattern.pattern}"

            if key in grouped:
                # Existierendes Pattern aktualisieren
                grouped[key].files_seen.extend(pattern.files_seen)
                grouped[key].metadata["occurrences"] = (
                    grouped[key].metadata.get("occurrences", 1) + 1
                )
            else:
                # Neues Pattern
                pattern.metadata["occurrences"] = 1
                grouped[key] = pattern

        # Nur Patterns mit min_occurrences zurückgeben
        return [
            p for p in grouped.values()
            if p.metadata.get("occurrences", 1) >= self.min_occurrences
        ]

    def _generate_semgrep_rules(
        self,
        patterns: List[CodePattern],
    ) -> List[SemgrepRule]:
        """
        Generiert Semgrep-Regeln aus Patterns.

        Args:
            patterns: Liste von Patterns.

        Returns:
            Liste von SemgrepRule.
        """
        rules = []

        for i, pattern in enumerate(patterns):
            # Regel-ID generieren
            rule_id = f"glitchhunter/learned/{pattern.pattern_type}_{i}"

            # Pattern zu Semgrep-Syntax konvertieren
            semgrep_pattern = self._convert_to_semgrep_pattern(pattern.pattern)

            rule = SemgrepRule(
                rule_id=rule_id,
                pattern=semgrep_pattern,
                message=pattern.message,
                severity=self.SEVERITY_MAP.get(pattern.severity, "MEDIUM"),
                languages=[pattern.language],
                metadata={
                    "pattern_type": pattern.pattern_type,
                    "learned_from": pattern.metadata.get("source", "unknown"),
                    "occurrences": pattern.metadata.get("occurrences", 1),
                    "fix_success_rate": pattern.fix_success_rate,
                },
            )

            rules.append(rule)

        return rules

    def _convert_to_semgrep_pattern(self, pattern: str) -> str:
        """
        Konvertiert Pattern zu Semgrep-Syntax.

        Args:
            pattern: Original-Pattern.

        Returns:
            Semgrep-Pattern.
        """
        # Einfache Konvertierung
        semgrep = pattern

        # Platzhalter anpassen
        semgrep = semgrep.replace('"..."', '"$STRING"')
        semgrep = semgrep.replace("'...' ", "'$STRING'")
        semgrep = semgrep.replace("N", "$NUMBER")
        semgrep = semgrep.replace("FUNC(", "$FUNC(...")

        # Ellipsis für beliebigen Code
        if "..." in semgrep:
            semgrep = semgrep.replace("...", "...")

        return semgrep

    def _detect_language(self, file_path: str) -> str:
        """Erkennt Sprache aus Dateipfad."""
        path = Path(file_path)
        extension = path.suffix.lower()

        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "cpp",
        }

        return extension_map.get(extension, "python")

    def _save_rules_file(self, rules: List[SemgrepRule]) -> Path:
        """
        Speichert Rules-Datei.

        Args:
            rules: Liste von Regeln.

        Returns:
            Pfad zur Rules-Datei.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rules_file = self.output_dir / f"learned_rules_{timestamp}.yaml"

        # YAML zusammenbauen
        rules_dict = {"rules": [r.to_dict() for r in rules]}

        with open(rules_file, "w") as f:
            yaml.dump(rules_dict, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Rules-Datei gespeichert: {rules_file}")
        return rules_file

    def get_existing_rules(self) -> List[SemgrepRule]:
        """
        Lädt existierende Regeln.

        Returns:
            Liste von SemgrepRule.
        """
        rules = []

        for rules_file in self.output_dir.glob("*.yaml"):
            try:
                with open(rules_file) as f:
                    data = yaml.safe_load(f)

                    for rule_dict in data.get("rules", []):
                        rule = SemgrepRule(
                            rule_id=rule_dict.get("id", ""),
                            pattern=rule_dict.get("pattern", ""),
                            message=rule_dict.get("message", ""),
                            severity=rule_dict.get("severity", "MEDIUM"),
                            languages=rule_dict.get("languages", []),
                            metadata=rule_dict,
                        )
                        rules.append(rule)

            except Exception as e:
                logger.warning(f"Fehler beim Laden von {rules_file}: {e}")

        return rules

    def __call__(self, state: Any) -> Dict[str, Any]:
        """
        Callable für LangGraph.

        Args:
            state: AgentState.

        Returns:
            State-Updates.
        """
        patches = getattr(state, "accepted_patches", [])

        if not patches:
            return {"metadata": {"rules_learned": 0}}

        result = self.learn_from_patches(patches)

        return {
            "learning_result": result.to_dict(),
            "rules_file": result.rules_file,
            "metadata": {
                "rules_learned": len(result.semgrep_rules),
                "patterns_extracted": len(result.patterns),
            },
        }


# =============================================================================
# Vector-DB Integration für selbstlernende Regeln
# =============================================================================


@dataclass
class VectorRule:
    """
    Regel mit Vector-Embedding.

    Attributes:
        id: Eindeutige ID
        pattern: CodePattern
        embedding: Vector-Embedding
        metadata: Zusatzinformationen
        similarity: Ähnlichkeit zum Query (bei Search)
    """

    id: str
    pattern: CodePattern
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    similarity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "id": self.id,
            "pattern": self.pattern.to_dict(),
            "metadata": self.metadata,
            "similarity": self.similarity,
        }


class VectorRuleLearner:
    """
    Lernt Rules aus Patches und speichert in Vector-DB.

    Verwendet Qdrant als primäre Vector-DB mit ChromaDB als Fallback
    für lokale Entwicklung ohne Docker.

    Features:
    - Embedding-Generierung mit sentence-transformers
    - Auto-Fallback von Qdrant zu ChromaDB
    - Similarity-Search für neue Bugs
    - Persistente Speicherung von Rules

    Usage:
        config = load_config()
        learner = VectorRuleLearner(config)
        
        # Lernen aus Patches
        result = learner.learn_from_patches(patches)
        
        # Ähnliche Rules finden
        similar = learner.find_similar_rules("null pointer exception")
    """

    DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION = 384  # Dimension von all-MiniLM-L6-v2

    # Pattern-Typen
    PATTERN_FIX = "fix"
    PATTERN_VULNERABILITY = "vulnerability"
    PATTERN_OPTIMIZATION = "optimization"
    PATTERN_BEST_PRACTICE = "best_practice"

    # Severity-Mapping
    SEVERITY_MAP = {
        "critical": "CRITICAL",
        "high": "HIGH",
        "medium": "MEDIUM",
        "low": "LOW",
        "info": "INFO",
    }

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        output_dir: str = "src/fixing/rules",
    ) -> None:
        """
        Initialisiert VectorRuleLearner.

        Args:
            config: Konfiguration mit Embedding/Vector-DB Settings.
            output_dir: Ausgabe-Verzeichnis für rules.yaml.
        """
        self.config = config or {}
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Embedding-Modell
        self.embedding_model: Optional[Any] = None
        self._embedding_model_name: str = ""

        # Vector-DB Clients
        self.qdrant_client: Optional[Any] = None
        self.chroma_client: Optional[Any] = None
        self.chroma_collection: Optional[Any] = None

        # Collection-Name
        self.collection_name = self.config.get("learned_rules", {}).get(
            "collection", "learned_rules"
        )

        # Initialisierung
        self._load_embedding_model()
        self._init_vector_db()

        logger.info("VectorRuleLearner initialisiert")

    def _load_embedding_model(self) -> None:
        """
        Lädt sentence-transformers Modell.

        Lädt das Embedding-Modell mit optionalem Cache.
        """
        model_name = self.config.get("embeddings", {}).get(
            "model", self.DEFAULT_EMBEDDING_MODEL
        )
        cache_dir_str = self.config.get("embeddings", {}).get(
            "cache_dir", ".glitchhunter/embeddings"
        )
        device = self.config.get("embeddings", {}).get("device", None)

        cache_dir = Path(cache_dir_str)
        cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Lade Embedding-Modell: {model_name}")

        try:
            from sentence_transformers import SentenceTransformer

            model_kwargs = {"cache_folder": str(cache_dir)}
            if device:
                model_kwargs["device"] = device

            self.embedding_model = SentenceTransformer(model_name, **model_kwargs)
            self._embedding_model_name = model_name

            logger.info(f"Embedding-Modell geladen: {model_name}")

        except ImportError as e:
            logger.error(
                f"sentence-transformers nicht installiert: {e}. "
                "Bitte 'pip install sentence-transformers' ausführen."
            )
            raise
        except Exception as e:
            logger.error(f"Fehler beim Laden des Embedding-Modells: {e}")
            raise

    def _init_vector_db(self) -> None:
        """
        Initialisiert Vector-DB (Qdrant oder ChromaDB).

        Versucht zuerst Qdrant zu verbinden. Falls nicht verfügbar,
        wird ChromaDB als Fallback verwendet.
        """
        vector_db_type = self.config.get("learned_rules", {}).get(
            "vector_db", "qdrant"
        )
        redis_enabled = self.config.get("cache", {}).get("redis", {}).get("enabled", False)

        # Qdrant versuchen wenn konfiguriert oder redis enabled
        if vector_db_type == "qdrant" or redis_enabled:
            try:
                self._init_qdrant()
                logger.info("Qdrant erfolgreich initialisiert")
                return
            except Exception as e:
                logger.warning(f"Qdrant nicht verfügbar, Fallback zu ChromaDB: {e}")

        # ChromaDB Fallback
        try:
            self._init_chromadb()
            logger.info("ChromaDB initialisiert (Fallback)")
        except Exception as e:
            logger.error(f"Vektor-DB Initialisierung fehlgeschlagen: {e}")
            raise

    def _init_qdrant(self) -> None:
        """Initialisiert Qdrant Client."""
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        qdrant_config = self.config.get("learned_rules", {}).get("qdrant", {})
        host = qdrant_config.get("host", "localhost")
        port = qdrant_config.get("port", 6379)
        https = qdrant_config.get("https", False)
        timeout = qdrant_config.get("timeout", 30)

        # Client erstellen
        self.qdrant_client = QdrantClient(
            host=host,
            port=port,
            https=https,
            timeout=timeout,
        )

        # Collection erstellen falls nicht existiert
        self._ensure_qdrant_collection()

        logger.debug(f"Qdrant verbunden: {host}:{port}")

    def _ensure_qdrant_collection(self) -> None:
        """Erstellt Qdrant Collection falls nicht existiert."""
        from qdrant_client.models import Distance, VectorParams

        try:
            collections = self.qdrant_client.get_collections().collections
            collection_exists = any(
                c.name == self.collection_name for c in collections
            )

            if not collection_exists:
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.EMBEDDING_DIMENSION,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Qdrant Collection '{self.collection_name}' erstellt")
        except Exception as e:
            logger.warning(f"Qdrant Collection Check fehlgeschlagen: {e}")
            raise

    def _init_chromadb(self) -> None:
        """Initialisiert ChromaDB Client."""
        import chromadb
        from chromadb.config import Settings

        chroma_config = self.config.get("learned_rules", {}).get("chromadb", {})
        persist_dir_str = chroma_config.get(
            "persist_dir", ".glitchhunter/chroma"
        )
        anonymized_telemetry = chroma_config.get("anonymized_telemetry", False)

        persist_dir = Path(persist_dir_str)
        persist_dir.mkdir(parents=True, exist_ok=True)

        # Persistent Client erstellen
        self.chroma_client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=chromadb.Settings(
                anonymized_telemetry=anonymized_telemetry
            ),
        )

        # Collection erstellen
        self._ensure_chroma_collection()

        logger.debug(f"ChromaDB initialisiert: {persist_dir}")

    def _ensure_chroma_collection(self) -> None:
        """Erstellt ChromaDB Collection."""
        if not self.chroma_client:
            raise ValueError("ChromaDB Client nicht initialisiert")

        self.chroma_collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.debug(f"ChromaDB Collection '{self.collection_name}' bereit")

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generiert Embedding für Text.

        Args:
            text: Text für Embedding.

        Returns:
            Embedding-Vector als Liste von Floats.
        """
        if not self.embedding_model:
            raise ValueError("Embedding-Modell nicht geladen")

        embedding = self.embedding_model.encode(text)
        # embedding kann numpy array oder liste sein
        if hasattr(embedding, "tolist"):
            return embedding.tolist()
        return list(embedding)

    def _pattern_to_text(self, pattern: CodePattern) -> str:
        """
        Konvertiert Pattern zu Text für Embedding.

        Args:
            pattern: CodePattern.

        Returns:
            Text-Repräsentation für Embedding.
        """
        bug_type = pattern.metadata.get("bug_type", "unknown")
        file_path = pattern.metadata.get("file_path", "")
        language = pattern.language
        pattern_type = pattern.pattern_type
        fix_description = pattern.message

        # Code-Kontext begrenzen
        code_context = pattern.pattern
        if len(code_context) > 500:
            code_context = code_context[:500] + "..."

        return (
            f"Bug Type: {bug_type}\n"
            f"File: {file_path}\n"
            f"Language: {language}\n"
            f"Pattern Type: {pattern_type}\n"
            f"Code Context: {code_context}\n"
            f"Fix Description: {fix_description}"
        ).strip()

    def _extract_patterns_from_patch(
        self,
        patch: Dict[str, Any],
    ) -> List[CodePattern]:
        """
        Extrahiert Muster aus Patch.

        Args:
            patch: Patch-Dict.

        Returns:
            Liste von CodePattern.
        """
        patterns = []

        patch_diff = patch.get("patch_diff", "")
        file_path = patch.get("file_path", "")
        bug_type = patch.get("bug_type", "")
        explanation = patch.get("explanation", "")

        # Sprache erkennen
        language = self._detect_language(file_path)

        # Pattern-Typ bestimmen
        pattern_type = self._determine_pattern_type(bug_type, explanation)

        # Pattern aus Diff extrahieren
        diff_patterns = self._extract_diff_patterns(patch_diff, language)

        for pattern_str in diff_patterns:
            patterns.append(CodePattern(
                pattern_type=pattern_type,
                language=language,
                pattern=pattern_str,
                message=explanation or f"Fix for {bug_type}",
                severity=self._infer_severity(bug_type),
                files_seen=[file_path],
                metadata={
                    "bug_type": bug_type,
                    "source": "patch",
                },
            ))

        return patterns

    def _detect_language(self, file_path: str) -> str:
        """Erkennt Sprache aus Dateipfad."""
        path = Path(file_path)
        extension = path.suffix.lower()

        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "cpp",
        }

        return extension_map.get(extension, "python")

    def _determine_pattern_type(
        self,
        bug_type: str,
        explanation: str,
    ) -> str:
        """
        Bestimmt Pattern-Typ.

        Args:
            bug_type: Bug-Typ.
            explanation: Erklärung.

        Returns:
            Pattern-Typ.
        """
        bug_type_lower = bug_type.lower()
        explanation_lower = explanation.lower()

        # Security-relevant
        if any(kw in bug_type_lower for kw in ["injection", "xss", "csrf", "auth", "security"]):
            return self.PATTERN_VULNERABILITY

        # Performance
        if any(kw in explanation_lower for kw in ["performance", "optimize", "fast"]):
            return self.PATTERN_OPTIMIZATION

        # Best Practice
        if any(kw in explanation_lower for kw in ["best practice", "convention", "standard"]):
            return self.PATTERN_BEST_PRACTICE

        # Default: Fix
        return self.PATTERN_FIX

    def _infer_severity(self, bug_type: str) -> str:
        """
        Leitet Schweregrad ab.

        Args:
            bug_type: Bug-Typ.

        Returns:
            Schweregrad.
        """
        bug_type_lower = bug_type.lower()

        if any(kw in bug_type_lower for kw in ["critical", "security", "injection"]):
            return "critical"
        elif any(kw in bug_type_lower for kw in ["high", "error", "bug"]):
            return "high"
        elif any(kw in bug_type_lower for kw in ["medium", "warning"]):
            return "medium"
        else:
            return "low"

    def _extract_diff_patterns(
        self,
        patch_diff: str,
        language: str,
    ) -> List[str]:
        """
        Extrahiert Patterns aus Diff-String.

        Args:
            patch_diff: Diff-String.
            language: Sprache.

        Returns:
            Liste von Pattern-Strings.
        """
        patterns = []

        for line in patch_diff.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                # Hinzugefügte Line als Pattern
                code_line = line[1:].strip()
                if code_line and not code_line.startswith("#"):
                    generalized = self._generalize_line(code_line, language)
                    if generalized:
                        patterns.append(generalized)

            elif line.startswith("-") and not line.startswith("---"):
                # Entfernte Line als Anti-Pattern
                code_line = line[1:].strip()
                if code_line and not code_line.startswith("#"):
                    generalized = self._generalize_line(code_line, language)
                    if generalized:
                        patterns.append(f"NOT {generalized}")

        return patterns

    def _generalize_line(self, line: str, language: str) -> Optional[str]:
        """
        Generalisiert Line zu Pattern.

        Args:
            line: Code-Line.
            language: Sprache.

        Returns:
            Generalisiertes Pattern.
        """
        if not line.strip():
            return None

        pattern = line.strip()

        # Spezifische Werte durch Platzhalter ersetzen
        # Strings
        pattern = re.sub(r'"[^"]*"', '"..."' , pattern)
        pattern = re.sub(r"'[^']*'", "'...' ", pattern)

        # Numbers
        pattern = re.sub(r"\b\d+\b", "N", pattern)

        # Variable names (teilweise)
        if language == "python":
            # Funktionaufrufe generalisieren
            pattern = re.sub(r"\b\w+\s*\(", "FUNC(", pattern)

        return pattern if len(pattern) > 3 else None

    def _generate_semgrep_rules(
        self,
        patterns: List[CodePattern],
    ) -> List[SemgrepRule]:
        """
        Generiert Semgrep-Regeln aus Patterns.

        Args:
            patterns: Liste von Patterns.

        Returns:
            Liste von SemgrepRule.
        """
        rules = []

        for i, pattern in enumerate(patterns):
            # Regel-ID generieren
            rule_id = f"glitchhunter/learned/{pattern.pattern_type}_{i}"

            # Pattern zu Semgrep-Syntax konvertieren
            semgrep_pattern = self._convert_to_semgrep_pattern(pattern.pattern)

            rule = SemgrepRule(
                rule_id=rule_id,
                pattern=semgrep_pattern,
                message=pattern.message,
                severity=self.SEVERITY_MAP.get(pattern.severity, "MEDIUM"),
                languages=[pattern.language],
                metadata={
                    "pattern_type": pattern.pattern_type,
                    "learned_from": pattern.metadata.get("source", "unknown"),
                    "occurrences": pattern.metadata.get("occurrences", 1),
                    "fix_success_rate": pattern.fix_success_rate,
                },
            )

            rules.append(rule)

        return rules

    def _convert_to_semgrep_pattern(self, pattern: str) -> str:
        """
        Konvertiert Pattern zu Semgrep-Syntax.

        Args:
            pattern: Original-Pattern.

        Returns:
            Semgrep-Pattern.
        """
        # Einfache Konvertierung
        semgrep = pattern

        # Platzhalter anpassen
        semgrep = semgrep.replace('"..."', '"$STRING"')
        semgrep = semgrep.replace("'...' ", "'$STRING'")
        semgrep = semgrep.replace("N", "$NUMBER")
        semgrep = semgrep.replace("FUNC(", "$FUNC(...")

        # Ellipsis für beliebigen Code
        if "..." in semgrep:
            semgrep = semgrep.replace("...", "...")

        return semgrep

    def _save_rules_file(self, rules: List[SemgrepRule]) -> Path:
        """
        Speichert Rules-Datei.

        Args:
            rules: Liste von Regeln.

        Returns:
            Pfad zur Rules-Datei.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rules_file = self.output_dir / f"learned_rules_{timestamp}.yaml"

        # YAML zusammenbauen
        rules_dict = {"rules": [r.to_dict() for r in rules]}

        with open(rules_file, "w") as f:
            yaml.dump(rules_dict, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Rules-Datei gespeichert: {rules_file}")
        return rules_file

    def learn_from_patches(
        self, patches: List[Dict[str, Any]]
    ) -> LearningResult:
        """
        Lernt aus erfolgreichen Patches und speichert in Vector-DB.

        Args:
            patches: Liste von erfolgreichen Patches.

        Returns:
            LearningResult mit gelernten Rules.
        """
        logger.info(f"Lerne aus {len(patches)} Patches")

        result = LearningResult()

        for patch in patches:
            # Patterns extrahieren
            patterns = self._extract_patterns_from_patch(patch)
            result.patterns.extend(patterns)

            # Für jedes Pattern: Embedding + Rule speichern
            for pattern in patterns:
                self._store_pattern_in_vector_db(pattern, patch)

        # Semgrep-Regeln generieren
        if result.patterns:
            result.semgrep_rules = self._generate_semgrep_rules(result.patterns)
            result.rules_file = str(self._save_rules_file(result.semgrep_rules))

        logger.info(
            f"Gelernte Rules: {len(result.semgrep_rules)} Semgrep-Regeln"
        )
        return result

    def _store_pattern_in_vector_db(
        self, pattern: CodePattern, patch: Dict[str, Any]
    ) -> None:
        """
        Speichert Pattern in Vector-DB mit Embedding.

        Args:
            pattern: CodePattern.
            patch: Patch-Dict mit Metadaten.
        """
        # Embedding generieren
        pattern_text = self._pattern_to_text(pattern)
        embedding = self._generate_embedding(pattern_text)

        # Metadata für Rule
        metadata = {
            "bug_type": patch.get("bug_type", "unknown"),
            "file_path": patch.get("file_path", ""),
            "language": pattern.language,
            "pattern_type": pattern.pattern_type,
            "fix_type": getattr(pattern, "fix_type", "fix"),
            "confidence": patch.get("confidence", 0.5),
            "learned_at": datetime.utcnow().isoformat(),
            "pattern_id": str(uuid.uuid4()),
        }

        if self.qdrant_client:
            # Qdrant: PointStruct speichern
            self._store_in_qdrant(pattern, embedding, metadata)
        else:
            # ChromaDB: Add mit Embedding
            self._store_in_chromadb(pattern, embedding, metadata, pattern_text)

        logger.debug(f"Pattern gespeichert in Vector-DB: {pattern.pattern_type}")

    def _store_in_qdrant(
        self,
        pattern: CodePattern,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        """Speichert in Qdrant."""
        from qdrant_client.models import PointStruct

        point_id = metadata.get("pattern_id", str(uuid.uuid4()))
        payload = {**metadata, "pattern": pattern.to_dict()}

        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
        )

    def _store_in_chromadb(
        self,
        pattern: CodePattern,
        embedding: List[float],
        metadata: Dict[str, Any],
        pattern_text: str,
    ) -> None:
        """Speichert in ChromaDB."""
        if not self.chroma_collection:
            raise ValueError("ChromaDB Collection nicht initialisiert")

        doc_id = metadata.get("pattern_id", str(uuid.uuid4()))

        self.chroma_collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[pattern_text],
        )

    def find_similar_rules(
        self,
        bug_description: str,
        top_k: int = 5,
        min_similarity: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Findet ähnliche Rules für Bug-Beschreibung.

        Args:
            bug_description: Beschreibung des Bugs.
            top_k: Anzahl der Ergebnisse.
            min_similarity: Minimum Similarity Threshold.

        Returns:
            Liste von ähnlichen Rules mit Similarity-Score.
        """
        logger.info(f"Suche ähnliche Rules für: {bug_description[:50]}...")

        # Embedding für Bug-Beschreibung generieren
        query_embedding = self._generate_embedding(bug_description)

        results = []

        if self.qdrant_client:
            # Qdrant: Similarity Search
            results = self._search_qdrant(query_embedding, top_k)
        else:
            # ChromaDB: Similarity Search
            results = self._search_chromadb(query_embedding, top_k)

        # Filtern nach min_similarity
        if min_similarity is not None:
            results = [
                r for r in results if r.get("similarity", 0.0) >= min_similarity
            ]

        logger.info(f"Similarity Search: {len(results)} Treffer gefunden")
        return results

    def _search_qdrant(
        self, query_embedding: List[float], top_k: int
    ) -> List[Dict[str, Any]]:
        """Sucht in Qdrant."""
        search_results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
        )

        results = []
        for hit in search_results:
            results.append(
                {
                    "id": hit.id,
                    "pattern": hit.payload.get("pattern", {}),
                    "similarity": hit.score,
                    "metadata": hit.payload,
                    "document": None,
                }
            )

        return results

    def _search_chromadb(
        self, query_embedding: List[float], top_k: int
    ) -> List[Dict[str, Any]]:
        """Sucht in ChromaDB."""
        if not self.chroma_collection:
            raise ValueError("ChromaDB Collection nicht initialisiert")

        search_results = self.chroma_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["embeddings", "metadatas", "documents"],
        )

        results = []
        if search_results and search_results.get("ids") and len(search_results["ids"]) > 0:
            ids = search_results["ids"][0]
            distances = search_results.get("distances", [[]])[0]
            metadatas = search_results.get("metadatas", [[]])[0]
            documents = search_results.get("documents", [[]])[0]

            for i in range(len(ids)):
                # Cosine similarity aus Distanz berechnen
                distance = distances[i] if i < len(distances) else 0.0
                similarity = 1.0 - (distance / 2)  # Cosine similarity

                results.append(
                    {
                        "id": ids[i],
                        "pattern": metadatas[i] if i < len(metadatas) else {},
                        "similarity": similarity,
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                        "document": documents[i] if i < len(documents) else None,
                    }
                )

        return results

    def get_rule_statistics(self) -> Dict[str, Any]:
        """
        Ruft Statistiken über gespeicherte Rules ab.

        Returns:
            Dict mit Statistiken.
        """
        stats = {
            "collection_name": self.collection_name,
            "vector_db": "qdrant" if self.qdrant_client else "chromadb",
            "total_rules": 0,
            "embedding_model": self._embedding_model_name,
            "embedding_dimension": self.EMBEDDING_DIMENSION,
        }

        try:
            if self.qdrant_client:
                # Qdrant: Collection info
                collection_info = self.qdrant_client.get_collection(
                    self.collection_name
                )
                stats["total_rules"] = collection_info.points_count
            elif self.chroma_collection:
                # ChromaDB: Collection count
                stats["total_rules"] = self.chroma_collection.count()
        except Exception as e:
            logger.warning(f"Statistiken konnten nicht abgerufen werden: {e}")

        return stats

    def clear_rules(self) -> None:
        """Löscht alle gespeicherten Rules."""
        logger.info(f"Lösche alle Rules aus Collection '{self.collection_name}'")

        if self.qdrant_client:
            # Qdrant: Collection neu erstellen
            self.qdrant_client.delete_collection(self.collection_name)
            self._ensure_qdrant_collection()
        elif self.chroma_collection and self.chroma_client:
            # ChromaDB: Collection neu erstellen
            self.chroma_client.delete_collection(self.collection_name)
            self._ensure_chroma_collection()

        logger.info("Alle Rules gelöscht")

    def __call__(self, state: Any) -> Dict[str, Any]:
        """
        Callable für LangGraph.

        Args:
            state: AgentState.

        Returns:
            State-Updates.
        """
        patches = getattr(state, "accepted_patches", [])

        if not patches:
            return {"metadata": {"rules_learned": 0}}

        result = self.learn_from_patches(patches)

        return {
            "learning_result": result.to_dict(),
            "rules_file": result.rules_file,
            "metadata": {
                "rules_learned": len(result.semgrep_rules),
                "patterns_extracted": len(result.patterns),
            },
        }
