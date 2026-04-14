"""
AST analyzer for GlitchHunter.

Uses Tree-sitter for parsing source code and extracting symbols,
patterns, and code structure information. Detects security patterns
like hardcoded secrets, SQL injection, command injection, etc.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ..core.exceptions import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class ASTSymbol:
    """
    Represents a symbol extracted from AST.

    Attributes:
        name: Symbol name
        kind: Symbol kind (function, class, method, variable, import)
        file_path: File path
        line_start: Starting line number
        line_end: Ending line number
        column_start: Starting column number
        column_end: Ending column number
        signature: Function signature
        parameters: Function parameters
        return_type: Return type
        docstring: Docstring content
        children: Child symbols
    """

    name: str
    kind: str
    file_path: str
    line_start: int
    line_end: int
    column_start: int
    column_end: int
    signature: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    children: List["ASTSymbol"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "kind": self.kind,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "signature": self.signature,
            "parameters": self.parameters,
            "return_type": self.return_type,
            "docstring": self.docstring,
        }


@dataclass
class ASTPattern:
    """
    Represents a detected code pattern.

    Attributes:
        pattern_type: Pattern type (security, complexity, style)
        description: Pattern description
        file_path: File path
        line_start: Starting line number
        line_end: Ending line number
        severity: Severity level
        code_snippet: Code snippet
    """

    pattern_type: str
    description: str
    file_path: str
    line_start: int
    line_end: int
    severity: str
    code_snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_type": self.pattern_type,
            "description": self.description,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "severity": self.severity,
            "code_snippet": self.code_snippet,
        }


@dataclass
class SecurityFinding:
    """
    Represents a security-related finding.

    Attributes:
        finding_type: Type of security finding
        description: Finding description
        file_path: File path
        line_start: Starting line number
        line_end: Ending line number
        severity: Severity level
        code_snippet: Code snippet
        recommendation: Recommended fix
    """

    finding_type: str
    description: str
    file_path: str
    line_start: int
    line_end: int
    severity: str
    code_snippet: Optional[str] = None
    recommendation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "finding_type": self.finding_type,
            "description": self.description,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "severity": self.severity,
            "code_snippet": self.code_snippet,
            "recommendation": self.recommendation,
        }


@dataclass
class Import:
    """Represents an import statement."""

    module: str
    name: str
    alias: Optional[str] = None
    line_start: int = 0
    is_relative: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "module": self.module,
            "name": self.name,
            "alias": self.alias,
            "line_start": self.line_start,
            "is_relative": self.is_relative,
        }


@dataclass
class FunctionCall:
    """Represents a function call."""

    name: str
    file_path: str
    line_start: int
    arguments: List[str] = field(default_factory=list)
    receiver: Optional[str] = None  # For method calls

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "arguments": self.arguments,
            "receiver": self.receiver,
        }


@dataclass
class ClassHierarchy:
    """Represents class hierarchy information."""

    class_name: str
    base_classes: List[str] = field(default_factory=list)
    subclasses: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "class_name": self.class_name,
            "base_classes": self.base_classes,
            "subclasses": self.subclasses,
            "methods": self.methods,
            "attributes": self.attributes,
        }


class ASTAnalyzer:
    """
    Analyzes source code using Tree-sitter.

    Supports multiple languages and provides symbol extraction,
    pattern detection, and security analysis.

    Example:
        >>> analyzer = ASTAnalyzer()
        >>> symbols = analyzer.parse_file(Path("example.py"))
        >>> findings = analyzer.find_security_patterns(Path("example.py"))
    """

    def __init__(self) -> None:
        """Initialize AST analyzer."""
        self.languages: Set[str] = {"python", "javascript", "typescript", "rust", "go", "java"}
        self._parser_cache: Dict[str, Any] = {}

        # Security patterns for detection
        self._security_patterns = self._init_security_patterns()

        logger.debug("ASTAnalyzer initialized")

    def _init_security_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize security pattern definitions."""
        return {
            "hardcoded_secrets": [
                {
                    "pattern": r"(?:password|passwd|pwd|secret|api_key|apikey|token|auth)\s*=\s*['\"][^'\"]+['\"]",
                    "description": "Hardcoded secret or credential",
                    "severity": "ERROR",
                },
                {
                    "pattern": r"(?:AWS_SECRET|PRIVATE_KEY|ENCRYPTION_KEY)\s*=\s*['\"][^'\"]+['\"]",
                    "description": "Hardcoded cryptographic key",
                    "severity": "CRITICAL",
                },
            ],
            "sql_injection": [
                {
                    "pattern": r"(?:execute|query|cursor\.execute)\s*\(\s*f['\"]",
                    "description": "Possible SQL injection via f-string",
                    "severity": "CRITICAL",
                },
                {
                    "pattern": r"(?:SELECT|INSERT|UPDATE|DELETE|DROP).*\+.*\%",
                    "description": "Possible SQL injection via string concatenation",
                    "severity": "ERROR",
                },
            ],
            "command_injection": [
                {
                    "pattern": r"os\.system\s*\([^)]*\%",
                    "description": "Command injection via string formatting",
                    "severity": "CRITICAL",
                },
                {
                    "pattern": r"subprocess\.(?:call|run|Popen)\s*\([^)]*shell\s*=\s*True",
                    "description": "Command injection via shell=True",
                    "severity": "ERROR",
                },
            ],
            "path_traversal": [
                {
                    "pattern": r"open\s*\([^)]*request\.",
                    "description": "Possible path traversal via user input",
                    "severity": "ERROR",
                },
            ],
            "unsafe_deserialization": [
                {
                    "pattern": r"pickle\.(?:load|loads)\s*\(",
                    "description": "Unsafe deserialization with pickle",
                    "severity": "CRITICAL",
                },
                {
                    "pattern": r"eval\s*\([^)]*\)",
                    "description": "Unsafe code execution with eval",
                    "severity": "CRITICAL",
                },
                {
                    "pattern": r"exec\s*\([^)]*\)",
                    "description": "Unsafe code execution with exec",
                    "severity": "CRITICAL",
                },
            ],
            "weak_crypto": [
                {
                    "pattern": r"hashlib\.(?:md5|sha1)\s*\(",
                    "description": "Weak cryptographic hash function",
                    "severity": "WARNING",
                },
                {
                    "pattern": r"(?:DES|RC4|Blowfish)",
                    "description": "Weak encryption algorithm",
                    "severity": "WARNING",
                },
            ],
        }

    def parse_file(
        self,
        file_path: Path,
        language: Optional[str] = None,
    ) -> List[ASTSymbol]:
        """
        Parse a file and extract symbols.

        Args:
            file_path: Path to the file
            language: Language hint (auto-detected if not provided)

        Returns:
            List of extracted ASTSymbol objects
        """
        if not file_path.exists():
            raise ValidationError(
                f"File does not exist: {file_path}",
                field="file_path",
            )

        # Auto-detect language
        if language is None:
            language = self._detect_language(file_path)

        if language is None:
            logger.warning(f"Could not detect language for {file_path}")
            return []

        try:
            if language == "python":
                return self._parse_python_file(file_path)
            elif language in ("javascript", "typescript"):
                return self._parse_javascript_file(file_path)
            elif language == "rust":
                return self._parse_rust_file(file_path)
            else:
                logger.debug(f"Parsing not fully implemented for {language}")
                return self._parse_generic_file(file_path)

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return []

    def find_patterns(
        self,
        file_path: Path,
        pattern_types: Optional[List[str]] = None,
        language: Optional[str] = None,
    ) -> List[ASTPattern]:
        """
        Find code patterns in a file.

        Args:
            file_path: Path to the file
            pattern_types: Types of patterns to find
            language: Language hint

        Returns:
            List of detected ASTPattern objects
        """
        if not file_path.exists():
            return []

        if language is None:
            language = self._detect_language(file_path)

        patterns = []

        try:
            # Security patterns
            if pattern_types is None or "security" in pattern_types:
                patterns.extend(self._find_security_patterns(file_path))

            # Complexity patterns
            if pattern_types is None or "complexity" in pattern_types:
                patterns.extend(self._find_complexity_patterns(file_path))

        except Exception as e:
            logger.error(f"Error finding patterns in {file_path}: {e}")

        return patterns

    def find_security_patterns(
        self,
        file_path: Path,
    ) -> List[SecurityFinding]:
        """
        Find security-related patterns in a file.

        Detects:
        - Hardcoded secrets (API keys, passwords, tokens)
        - SQL injection vulnerabilities
        - Command injection vulnerabilities
        - Path traversal vulnerabilities
        - Unsafe deserialization
        - Weak cryptography

        Args:
            file_path: Path to the file

        Returns:
            List of SecurityFinding objects
        """
        if not file_path.exists():
            return []

        findings = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            content = "".join(lines)

            for category, patterns in self._security_patterns.items():
                for pattern_def in patterns:
                    pattern = pattern_def["pattern"]
                    description = pattern_def["description"]
                    severity = pattern_def["severity"]

                    for match in re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE):
                        # Find line numbers
                        start_pos = match.start()
                        line_start = content[:start_pos].count("\n") + 1
                        line_end = content[:match.end()].count("\n") + 1

                        # Get code snippet
                        snippet = match.group(0)

                        finding = SecurityFinding(
                            finding_type=category,
                            description=description,
                            file_path=str(file_path),
                            line_start=line_start,
                            line_end=line_end,
                            severity=severity,
                            code_snippet=snippet,
                            recommendation=self._get_recommendation(category),
                        )
                        findings.append(finding)

        except Exception as e:
            logger.error(f"Error finding security patterns in {file_path}: {e}")

        return findings

    def get_imports(
        self,
        file_path: Path,
    ) -> List[Import]:
        """
        Extract imports from a file.

        Args:
            file_path: Path to the file

        Returns:
            List of Import objects
        """
        if not file_path.exists():
            return []

        imports = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            language = self._detect_language(file_path)

            for line_num, line in enumerate(lines, 1):
                if language == "python":
                    # Python imports
                    import_match = re.match(
                        r"^import\s+([\w.]+)(?:\s+as\s+(\w+))?", line
                    )
                    if import_match:
                        imports.append(Import(
                            module=import_match.group(1),
                            name=import_match.group(1).split(".")[-1],
                            alias=import_match.group(2),
                            line_start=line_num,
                        ))

                    from_match = re.match(
                        r"^from\s+([\w.]+)\s+import\s+(.+)", line
                    )
                    if from_match:
                        module = from_match.group(1)
                        names = from_match.group(2).split(",")
                        for name in names:
                            name = name.strip().split(" as ")[-1].strip()
                            imports.append(Import(
                                module=module,
                                name=name,
                                line_start=line_num,
                                is_relative=module.startswith("."),
                            ))

                elif language in ("javascript", "typescript"):
                    # JavaScript/TypeScript imports
                    import_match = re.match(
                        r"import\s+(?:{([^}]+)}|(\w+))\s+from\s+['\"]([^'\"]+)['\"]",
                        line,
                    )
                    if import_match:
                        named = import_match.group(1)
                        default = import_match.group(2)
                        module = import_match.group(3)

                        if named:
                            for name in named.split(","):
                                name = name.strip().split(" as ")[-1].strip()
                                imports.append(Import(
                                    module=module,
                                    name=name,
                                    line_start=line_num,
                                ))
                        if default:
                            imports.append(Import(
                                module=module,
                                name=default,
                                line_start=line_num,
                            ))

        except Exception as e:
            logger.error(f"Error extracting imports from {file_path}: {e}")

        return imports

    def get_function_calls(
        self,
        file_path: Path,
    ) -> List[FunctionCall]:
        """
        Extract function calls from a file.

        Args:
            file_path: Path to the file

        Returns:
            List of FunctionCall objects
        """
        if not file_path.exists():
            return []

        calls = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                # Match function calls: func_name(args) or obj.method(args)
                call_match = re.search(r"(\w+)\.(\w+)\s*\(([^)]*)\)", line)
                if call_match:
                    calls.append(FunctionCall(
                        name=call_match.group(2),
                        file_path=str(file_path),
                        line_start=line_num,
                        receiver=call_match.group(1),
                        arguments=[a.strip() for a in call_match.group(3).split(",") if a.strip()],
                    ))
                else:
                    standalone_match = re.search(r"(\w+)\s*\(([^)]*)\)", line)
                    if standalone_match and standalone_match.group(1) not in ("if", "for", "while", "with"):
                        calls.append(FunctionCall(
                            name=standalone_match.group(1),
                            file_path=str(file_path),
                            line_start=line_num,
                            arguments=[a.strip() for a in standalone_match.group(2).split(",") if a.strip()],
                        ))

        except Exception as e:
            logger.error(f"Error extracting function calls from {file_path}: {e}")

        return calls

    def get_class_hierarchy(
        self,
        file_path: Path,
    ) -> List[ClassHierarchy]:
        """
        Extract class hierarchy information from a file.

        Args:
            file_path: Path to the file

        Returns:
            List of ClassHierarchy objects
        """
        if not file_path.exists():
            return []

        hierarchies = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            language = self._detect_language(file_path)

            current_class = None
            current_hierarchy = None

            for line_num, line in enumerate(lines, 1):
                if language == "python":
                    class_match = re.match(r"^class\s+(\w+)(?:\(([^)]+)\))?:", line)
                    if class_match:
                        if current_hierarchy:
                            hierarchies.append(current_hierarchy)

                        class_name = class_match.group(1)
                        bases_str = class_match.group(2) or ""
                        base_classes = [b.strip() for b in bases_str.split(",") if b.strip()]

                        current_hierarchy = ClassHierarchy(
                            class_name=class_name,
                            base_classes=base_classes,
                        )

                    elif current_hierarchy:
                        # Check for methods
                        method_match = re.match(r"^\s+def\s+(\w+)\s*\(", line)
                        if method_match:
                            current_hierarchy.methods.append(method_match.group(1))

            if current_hierarchy:
                hierarchies.append(current_hierarchy)

        except Exception as e:
            logger.error(f"Error extracting class hierarchy from {file_path}: {e}")

        return hierarchies

    def _parse_python_file(self, file_path: Path) -> List[ASTSymbol]:
        """Parse Python file and extract symbols."""
        symbols = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            import re

            for line_num, line in enumerate(lines, 1):
                # Function definitions
                func_match = re.search(r"^(\s*)def\s+(\w+)\s*\(([^)]*)\)", line)
                if func_match:
                    indent = len(func_match.group(1))
                    func_name = func_match.group(2)
                    params_str = func_match.group(3)
                    params = [p.strip().split("=")[0].strip() for p in params_str.split(",") if p.strip()]

                    kind = "method" if indent > 0 else "function"

                    symbol = ASTSymbol(
                        name=func_name,
                        kind=kind,
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 10,  # Estimate
                        column_start=len(func_match.group(1)),
                        column_end=len(line),
                        parameters=params,
                    )
                    symbols.append(symbol)

                # Class definitions
                class_match = re.search(r"^class\s+(\w+)", line)
                if class_match:
                    class_name = class_match.group(1)
                    symbol = ASTSymbol(
                        name=class_name,
                        kind="class",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 50,
                        column_start=0,
                        column_end=len(line),
                    )
                    symbols.append(symbol)

        except Exception as e:
            logger.error(f"Error parsing Python file {file_path}: {e}")

        return symbols

    def _parse_javascript_file(self, file_path: Path) -> List[ASTSymbol]:
        """Parse JavaScript/TypeScript file and extract symbols."""
        symbols = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            import re

            for line_num, line in enumerate(lines, 1):
                # Function declarations
                func_match = re.search(r"function\s+(\w+)\s*\(", line)
                if func_match:
                    symbol = ASTSymbol(
                        name=func_match.group(1),
                        kind="function",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 20,
                        column_start=0,
                        column_end=len(line),
                    )
                    symbols.append(symbol)

                # Class declarations
                class_match = re.search(r"class\s+(\w+)", line)
                if class_match:
                    symbol = ASTSymbol(
                        name=class_match.group(1),
                        kind="class",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 50,
                        column_start=0,
                        column_end=len(line),
                    )
                    symbols.append(symbol)

        except Exception as e:
            logger.error(f"Error parsing JavaScript file {file_path}: {e}")

        return symbols

    def _parse_rust_file(self, file_path: Path) -> List[ASTSymbol]:
        """Parse Rust file and extract symbols."""
        symbols = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            import re

            for line_num, line in enumerate(lines, 1):
                # Function definitions
                func_match = re.search(r"^(?:pub\s+)?fn\s+(\w+)", line)
                if func_match:
                    symbol = ASTSymbol(
                        name=func_match.group(1),
                        kind="function",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 30,
                        column_start=0,
                        column_end=len(line),
                    )
                    symbols.append(symbol)

                # Struct definitions
                struct_match = re.search(r"^(?:pub\s+)?struct\s+(\w+)", line)
                if struct_match:
                    symbol = ASTSymbol(
                        name=struct_match.group(1),
                        kind="struct",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 50,
                        column_start=0,
                        column_end=len(line),
                    )
                    symbols.append(symbol)

        except Exception as e:
            logger.error(f"Error parsing Rust file {file_path}: {e}")

        return symbols

    def _parse_generic_file(self, file_path: Path) -> List[ASTSymbol]:
        """Generic file parsing fallback."""
        return []

    def _detect_language(self, file_path: Path) -> Optional[str]:
        """Detect language from file extension."""
        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
        }
        return extension_map.get(file_path.suffix.lower())

    def _find_security_patterns(
        self, file_path: Path
    ) -> List[ASTPattern]:
        """Find security-related patterns."""
        patterns = []
        findings = self.find_security_patterns(file_path)

        for finding in findings:
            pattern = ASTPattern(
                pattern_type="security",
                description=finding.description,
                file_path=finding.file_path,
                line_start=finding.line_start,
                line_end=finding.line_end,
                severity=finding.severity,
                code_snippet=finding.code_snippet,
            )
            patterns.append(pattern)

        return patterns

    def _find_complexity_patterns(
        self, file_path: Path
    ) -> List[ASTPattern]:
        """Find complexity-related patterns (deep nesting, long functions)."""
        patterns = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            # Check for deep nesting
            for line_num, line in enumerate(lines, 1):
                stripped = line.lstrip()
                if not stripped:
                    continue

                indent = len(line) - len(stripped)
                nesting_level = indent // 4

                if nesting_level > 4:
                    pattern = ASTPattern(
                        pattern_type="complexity",
                        description=f"Deep nesting detected (level {nesting_level})",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num,
                        severity="WARNING",
                        code_snippet=line.strip()[:100],
                    )
                    patterns.append(pattern)

        except Exception as e:
            logger.error(f"Error finding complexity patterns in {file_path}: {e}")

        return patterns

    def _get_recommendation(self, finding_type: str) -> str:
        """Get recommendation for a finding type."""
        recommendations = {
            "hardcoded_secrets": "Use environment variables or a secrets manager",
            "sql_injection": "Use parameterized queries or prepared statements",
            "command_injection": "Avoid shell=True, use subprocess with list arguments",
            "path_traversal": "Validate and sanitize user input, use os.path.abspath",
            "unsafe_deserialization": "Use safe serialization formats like JSON",
            "weak_crypto": "Use SHA-256 or stronger, use AES instead of DES",
        }
        return recommendations.get(finding_type, "Review and fix this issue")
