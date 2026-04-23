"""
Language Registry für GlitchHunter v3.0.

Verwaltet Tree-sitter-Grammatiken für alle 13 unterstützten Sprachen.
Bietet zentralen Zugriff auf Parser und Sprachkonfiguration.

Unterstützte Sprachen:
1. Python (.py)
2. JavaScript (.js, .mjs)
3. TypeScript (.ts, .tsx)
4. Rust (.rs)
5. Go (.go)
6. Java (.java)
7. C (.c, .h)
8. C++ (.cpp, .cc, .cxx, .hpp)
9. Zig (.zig)
10. Solidity (.sol)
11. Kotlin (.kt, .kts)
12. Swift (.swift)
13. PHP (.php)
14. Ruby (.rb)
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class LanguageConfig:
    """
    Konfiguration für eine unterstützte Sprache.
    
    Attributes:
        name: Sprachname (z.B. "python", "javascript")
        display_name: Anzeigename (z.B. "Python", "JavaScript")
        extensions: Dateiendungen (z.B. [".py", ".pyi"])
        tree_sitter_lib: Tree-sitter Bibliotheksname (z.B. "tree_sitter_python")
        mime_type: MIME-Typ (optional)
        priority: Parser-Priorität (höher = bevorzugt)
        supports_types: Unterstützt die Sprache Typisierung?
        supports_classes: Unterstützt die Sprache Klassen?
    """
    name: str
    display_name: str
    extensions: List[str]
    tree_sitter_lib: str
    mime_type: Optional[str] = None
    priority: int = 1
    supports_types: bool = True
    supports_classes: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "extensions": self.extensions,
            "tree_sitter_lib": self.tree_sitter_lib,
            "mime_type": self.mime_type,
            "priority": self.priority,
            "supports_types": self.supports_types,
            "supports_classes": self.supports_classes,
        }


class LanguageRegistry:
    """
    Zentrale Registry für alle unterstützten Sprachen.
    
    Bietet:
    - Auto-Detection von Sprache basierend auf Dateiendung
    - Zugriff auf Tree-sitter Parser
    - Sprachspezifische Konfiguration
    
    Usage:
        registry = LanguageRegistry()
        language = registry.detect_language(Path("example.py"))
        parser = registry.get_parser("python")
    """
    
    # Alle unterstützten Sprachen
    SUPPORTED_LANGUAGES: Dict[str, LanguageConfig] = {
        "python": LanguageConfig(
            name="python",
            display_name="Python",
            extensions=[".py", ".pyi", ".pyw"],
            tree_sitter_lib="tree_sitter_python",
            mime_type="text/x-python",
            priority=1,
            supports_types=True,
            supports_classes=True,
        ),
        "javascript": LanguageConfig(
            name="javascript",
            display_name="JavaScript",
            extensions=[".js", ".mjs", ".cjs"],
            tree_sitter_lib="tree_sitter_javascript",
            mime_type="text/javascript",
            priority=1,
            supports_types=False,
            supports_classes=True,
        ),
        "typescript": LanguageConfig(
            name="typescript",
            display_name="TypeScript",
            extensions=[".ts", ".tsx", ".mts", ".cts"],
            tree_sitter_lib="tree_sitter_typescript",
            mime_type="text/typescript",
            priority=2,  # Höher als JavaScript bei .ts
            supports_types=True,
            supports_classes=True,
        ),
        "rust": LanguageConfig(
            name="rust",
            display_name="Rust",
            extensions=[".rs"],
            tree_sitter_lib="tree_sitter_rust",
            mime_type="text/x-rust",
            priority=1,
            supports_types=True,
            supports_classes=True,
        ),
        "go": LanguageConfig(
            name="go",
            display_name="Go",
            extensions=[".go"],
            tree_sitter_lib="tree_sitter_go",
            mime_type="text/x-go",
            priority=1,
            supports_types=True,
            supports_classes=False,
        ),
        "java": LanguageConfig(
            name="java",
            display_name="Java",
            extensions=[".java"],
            tree_sitter_lib="tree_sitter_java",
            mime_type="text/x-java",
            priority=1,
            supports_types=True,
            supports_classes=True,
        ),
        "c": LanguageConfig(
            name="c",
            display_name="C",
            extensions=[".c", ".h"],
            tree_sitter_lib="tree_sitter_c",
            mime_type="text/x-c",
            priority=1,
            supports_types=False,
            supports_classes=False,
        ),
        "cpp": LanguageConfig(
            name="cpp",
            display_name="C++",
            extensions=[".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".h"],
            tree_sitter_lib="tree_sitter_cpp",
            mime_type="text/x-c++src",
            priority=2,  # Höher als C bei .cpp/.hpp
            supports_types=True,
            supports_classes=True,
        ),
        "zig": LanguageConfig(
            name="zig",
            display_name="Zig",
            extensions=[".zig"],
            tree_sitter_lib="tree_sitter_zig",
            mime_type="text/x-zig",
            priority=1,
            supports_types=True,
            supports_classes=False,
        ),
        "solidity": LanguageConfig(
            name="solidity",
            display_name="Solidity",
            extensions=[".sol"],
            tree_sitter_lib="tree_sitter_solidity",
            mime_type="text/x-solidity",
            priority=1,
            supports_types=True,
            supports_classes=True,
        ),
        "kotlin": LanguageConfig(
            name="kotlin",
            display_name="Kotlin",
            extensions=[".kt", ".kts"],
            tree_sitter_lib="tree_sitter_kotlin",
            mime_type="text/x-kotlin",
            priority=1,
            supports_types=True,
            supports_classes=True,
        ),
        "swift": LanguageConfig(
            name="swift",
            display_name="Swift",
            extensions=[".swift"],
            tree_sitter_lib="tree_sitter_swift",
            mime_type="text/x-swift",
            priority=1,
            supports_types=True,
            supports_classes=True,
        ),
        "php": LanguageConfig(
            name="php",
            display_name="PHP",
            extensions=[".php", ".php3", ".php4", ".php5", ".phtml"],
            tree_sitter_lib="tree_sitter_php",
            mime_type="application/x-php",
            priority=1,
            supports_types=True,
            supports_classes=True,
        ),
        "ruby": LanguageConfig(
            name="ruby",
            display_name="Ruby",
            extensions=[".rb", ".erb", ".rake"],
            tree_sitter_lib="tree_sitter_ruby",
            mime_type="text/x-ruby",
            priority=1,
            supports_types=False,
            supports_classes=True,
        ),
    }
    
    def __init__(self):
        """Initialisiert die Language Registry."""
        self._parser_cache: Dict[str, Any] = {}
        self._language_by_ext: Dict[str, str] = self._build_ext_map()
        
        logger.info(
            f"LanguageRegistry initialisiert mit "
            f"{len(self.SUPPORTED_LANGUAGES)} Sprachen"
        )
    
    def _build_ext_map(self) -> Dict[str, str]:
        """
        Erstellt Mapping von Dateiendungen zu Sprachen.
        
        Returns:
            Dict mapping extension -> language name
        """
        ext_map = {}
        
        for lang_name, config in self.SUPPORTED_LANGUAGES.items():
            for ext in config.extensions:
                # Bei Konflikten gewinnt höhere Priorität
                if ext not in ext_map or config.priority > self.SUPPORTED_LANGUAGES[ext_map[ext]].priority:
                    ext_map[ext] = lang_name
        
        return ext_map
    
    def detect_language(self, file_path: Path) -> Optional[str]:
        """
        Erkennt Sprache basierend auf Dateiendung.
        
        Args:
            file_path: Pfad zur Datei
            
        Returns:
            Sprachname oder None
        """
        ext = file_path.suffix.lower()
        return self._language_by_ext.get(ext)
    
    def get_language_config(
        self,
        language: str,
    ) -> Optional[LanguageConfig]:
        """
        Returns Sprachkonfiguration.
        
        Args:
            language: Sprachname
            
        Returns:
            LanguageConfig oder None
        """
        return self.SUPPORTED_LANGUAGES.get(language.lower())
    
    def get_supported_languages(self) -> List[str]:
        """
        Returns Liste aller unterstützten Sprachen.
        
        Returns:
            Liste von Sprachnamen
        """
        return list(self.SUPPORTED_LANGUAGES.keys())
    
    def get_extensions_for_language(
        self,
        language: str,
    ) -> List[str]:
        """
        Returns alle Dateiendungen für eine Sprache.
        
        Args:
            language: Sprachname
            
        Returns:
            Liste von Dateiendungen
        """
        config = self.SUPPORTED_LANGUAGES.get(language)
        return config.extensions if config else []
    
    def get_tree_sitter_lib(
        self,
        language: str,
    ) -> Optional[str]:
        """
        Returns Tree-sitter Bibliotheksname für eine Sprache.
        
        Args:
            language: Sprachname
            
        Returns:
            Bibliotheksname oder None
        """
        config = self.SUPPORTED_LANGUAGES.get(language)
        return config.tree_sitter_lib if config else None
    
    def get_parser(self, language: str) -> Optional[Any]:
        """
        Returns Tree-sitter Parser für eine Sprache.
        
        Args:
            language: Sprachname
            
        Returns:
            Parser oder None
        """
        # Cache prüfen
        if language in self._parser_cache:
            return self._parser_cache[language]
        
        try:
            from tree_sitter import Parser
            
            # Tree-sitter Bibliothek laden
            lib_name = self.get_tree_sitter_lib(language)
            if not lib_name:
                logger.warning(f"Keine Tree-sitter Bibliothek für {language}")
                return None
            
            # Dynamisch importieren
            import importlib
            ts_module = importlib.import_module(lib_name)
            
            # Parser erstellen
            parser = Parser()
            parser.set_language(ts_module.language())
            
            # Cachen
            self._parser_cache[language] = parser
            
            logger.debug(f"Parser für {language} geladen")
            
            return parser
            
        except ImportError as e:
            logger.warning(
                f"Tree-sitter Bibliothek '{lib_name}' nicht installiert: {e}"
            )
            return None
        except Exception as e:
            logger.error(f"Parser für {language} fehlgeschlagen: {e}")
            return None
    
    def has_parser(self, language: str) -> bool:
        """
        Prüft ob Parser für Sprache verfügbar ist.
        
        Args:
            language: Sprachname
            
        Returns:
            True wenn verfügbar
        """
        return self.get_parser(language) is not None
    
    def get_all_extensions(self) -> List[str]:
        """
        Returns alle unterstützten Dateiendungen.
        
        Returns:
            Liste von Dateiendungen
        """
        return list(self._language_by_ext.keys())
    
    def is_supported(self, file_path: Path) -> bool:
        """
        Prüft ob Dateiendung unterstützt wird.
        
        Args:
            file_path: Pfad zur Datei
            
        Returns:
            True wenn unterstützt
        """
        ext = file_path.suffix.lower()
        return ext in self._language_by_ext
    
    def __len__(self) -> int:
        """Returns Anzahl unterstützter Sprachen."""
        return len(self.SUPPORTED_LANGUAGES)
    
    def __repr__(self) -> str:
        """String-Repräsentation."""
        return (
            f"LanguageRegistry(languages={len(self)}, "
            f"extensions={len(self._language_by_ext)})"
        )


# Globale Instanz für einfachen Zugriff
_registry: Optional[LanguageRegistry] = None


def get_registry() -> LanguageRegistry:
    """
    Returns globale LanguageRegistry Instanz.
    
    Returns:
        LanguageRegistry
    """
    global _registry
    if _registry is None:
        _registry = LanguageRegistry()
    return _registry


def detect_language(file_path: Path) -> Optional[str]:
    """
    Erkennt Sprache basierend auf Dateiendung.
    
    Convenience-Funktion die globale Registry verwendet.
    
    Args:
        file_path: Pfad zur Datei
        
    Returns:
        Sprachname oder None
    """
    return get_registry().detect_language(file_path)


def get_parser(language: str) -> Optional[Any]:
    """
    Returns Tree-sitter Parser für eine Sprache.
    
    Convenience-Funktion die globale Registry verwendet.
    
    Args:
        language: Sprachname
        
    Returns:
        Parser oder None
    """
    return get_registry().get_parser(language)


def get_supported_languages() -> List[str]:
    """
    Returns Liste aller unterstützten Sprachen.
    
    Convenience-Funktion die globale Registry verwendet.
    
    Returns:
        Liste von Sprachnamen
    """
    return get_registry().get_supported_languages()
