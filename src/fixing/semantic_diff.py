"""
Semantic diff validator for GlitchHunter.

Tree-sitter-based semantic diff for detecting code changes,
affected symbols, and potential side effects.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class SymbolChange:
    """
    Represents a change to a symbol.

    Attributes:
        symbol_name: Symbol name
        change_type: Type of change (added, removed, modified)
        old_signature: Old signature (if modified)
        new_signature: New signature (if modified)
        impact: Impact level (low, medium, high)
    """

    symbol_name: str
    change_type: str
    old_signature: Optional[str] = None
    new_signature: Optional[str] = None
    impact: str = "low"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol_name": self.symbol_name,
            "change_type": self.change_type,
            "old_signature": self.old_signature,
            "new_signature": self.new_signature,
            "impact": self.impact,
        }


@dataclass
class DataFlowChange:
    """Represents a change in data flow."""

    source: str
    target: str
    change_type: str  # added, removed, modified
    variable: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "change_type": self.change_type,
            "variable": self.variable,
        }


@dataclass
class CallChange:
    """Represents a change in function calls."""

    caller: str
    callee: str
    change_type: str  # added, removed, modified
    line_number: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "caller": self.caller,
            "callee": self.callee,
            "change_type": self.change_type,
            "line_number": self.line_number,
        }


@dataclass
class SideEffect:
    """Represents a potential side effect."""

    description: str
    severity: str  # low, medium, high, critical
    affected_symbols: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "description": self.description,
            "severity": self.severity,
            "affected_symbols": self.affected_symbols,
        }


@dataclass
class SemanticDiff:
    """
    Semantic diff between two code versions.

    Attributes:
        original_symbols: Set of original symbol names
        patched_symbols: Set of patched symbol names
        added_symbols: Set of added symbols
        removed_symbols: Set of removed symbols
        modified_symbols: Set of modified symbols
        symbol_changes: List of symbol changes
    """

    original_symbols: Set[str] = field(default_factory=set)
    patched_symbols: Set[str] = field(default_factory=set)
    added_symbols: Set[str] = field(default_factory=set)
    removed_symbols: Set[str] = field(default_factory=set)
    modified_symbols: Set[str] = field(default_factory=set)
    symbol_changes: List[SymbolChange] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_symbols": list(self.original_symbols),
            "patched_symbols": list(self.patched_symbols),
            "added_symbols": list(self.added_symbols),
            "removed_symbols": list(self.removed_symbols),
            "modified_symbols": list(self.modified_symbols),
            "symbol_changes": [c.to_dict() for c in self.symbol_changes],
        }


class SemanticDiffValidator:
    """
    Tree-sitter-based semantic diff validator.

    Compares original and patched code to detect:
    - Added/removed/modified symbols
    - Changed data flows
    - Changed function calls
    - Potential side effects

    Example:
        >>> validator = SemanticDiffValidator()
        >>> diff = validator.compute_diff(original_code, patched_code)
        >>> changes = diff.get_changed_symbols()
    """

    def __init__(self) -> None:
        """Initialize semantic diff validator."""
        logger.debug("SemanticDiffValidator initialized")

    def compute_diff(
        self,
        original_code: str,
        patched_code: str,
        language: str = "python",
    ) -> SemanticDiff:
        """
        Compute semantic diff between original and patched code.

        Args:
            original_code: Original code
            patched_code: Patched code
            language: Programming language

        Returns:
            SemanticDiff with changes
        """
        logger.info("Computing semantic diff")

        diff = SemanticDiff()

        # Extract symbols from both versions
        original_symbols = self._extract_symbols(original_code, language)
        patched_symbols = self._extract_symbols(patched_code, language)

        diff.original_symbols = set(original_symbols.keys())
        diff.patched_symbols = set(patched_symbols.keys())

        # Find added symbols
        diff.added_symbols = diff.patched_symbols - diff.original_symbols

        # Find removed symbols
        diff.removed_symbols = diff.original_symbols - diff.patched_symbols

        # Find modified symbols (same name, different signature)
        common_symbols = diff.original_symbols & diff.patched_symbols
        for symbol in common_symbols:
            orig_sig = original_symbols.get(symbol, "")
            patch_sig = patched_symbols.get(symbol, "")

            if orig_sig != patch_sig:
                diff.modified_symbols.add(symbol)

                # Determine impact
                impact = self._determine_impact(symbol, orig_sig, patch_sig)

                diff.symbol_changes.append(SymbolChange(
                    symbol_name=symbol,
                    change_type="modified",
                    old_signature=orig_sig,
                    new_signature=patch_sig,
                    impact=impact,
                ))

        # Add changes for added symbols
        for symbol in diff.added_symbols:
            diff.symbol_changes.append(SymbolChange(
                symbol_name=symbol,
                change_type="added",
                new_signature=patched_symbols.get(symbol, ""),
                impact="low",
            ))

        # Add changes for removed symbols
        for symbol in diff.removed_symbols:
            diff.symbol_changes.append(SymbolChange(
                symbol_name=symbol,
                change_type="removed",
                old_signature=original_symbols.get(symbol, ""),
                impact="high",
            ))

        logger.info(
            f"Semantic diff complete: "
            f"{len(diff.added_symbols)} added, "
            f"{len(diff.removed_symbols)} removed, "
            f"{len(diff.modified_symbols)} modified"
        )

        return diff

    def get_changed_symbols(self, diff: SemanticDiff) -> List[SymbolChange]:
        """
        Get list of changed symbols.

        Args:
            diff: SemanticDiff object

        Returns:
            List of SymbolChange objects
        """
        return diff.symbol_changes

    def get_changed_data_flows(
        self,
        original_code: str,
        patched_code: str,
        language: str = "python",
    ) -> List[DataFlowChange]:
        """
        Get changed data flows between versions.

        Args:
            original_code: Original code
            patched_code: Patched code
            language: Programming language

        Returns:
            List of DataFlowChange objects
        """
        # This would require full data flow analysis
        # For now, return empty list as placeholder
        return []

    def get_changed_calls(
        self,
        original_code: str,
        patched_code: str,
        language: str = "python",
    ) -> List[CallChange]:
        """
        Get changed function calls between versions.

        Args:
            original_code: Original code
            patched_code: Patched code
            language: Programming language

        Returns:
            List of CallChange objects
        """
        original_calls = self._extract_function_calls(original_code, language)
        patched_calls = self._extract_function_calls(patched_code, language)

        changes = []

        # Find removed calls
        for call in original_calls - patched_calls:
            parts = call.split("->")
            if len(parts) == 2:
                changes.append(CallChange(
                    caller=parts[0],
                    callee=parts[1],
                    change_type="removed",
                    line_number=0,
                ))

        # Find added calls
        for call in patched_calls - original_calls:
            parts = call.split("->")
            if len(parts) == 2:
                changes.append(CallChange(
                    caller=parts[0],
                    callee=parts[1],
                    change_type="added",
                    line_number=0,
                ))

        return changes

    def has_unexpected_side_effects(
        self,
        diff: SemanticDiff,
    ) -> bool:
        """
        Check if diff has unexpected side effects.

        Args:
            diff: SemanticDiff object

        Returns:
            True if unexpected side effects detected
        """
        # Check for high-impact changes
        for change in diff.symbol_changes:
            if change.impact == "high":
                return True

        # Check for removed public symbols
        for symbol in diff.removed_symbols:
            if not symbol.startswith("_"):
                return True

        return False

    def get_side_effects(
        self,
        diff: SemanticDiff,
    ) -> List[SideEffect]:
        """
        Get potential side effects of changes.

        Args:
            diff: SemanticDiff object

        Returns:
            List of SideEffect objects
        """
        side_effects = []

        # Check for removed symbols
        if diff.removed_symbols:
            side_effects.append(SideEffect(
                description=f"Removed {len(diff.removed_symbols)} symbols",
                severity="high",
                affected_symbols=list(diff.removed_symbols),
            ))

        # Check for modified function signatures
        for change in diff.symbol_changes:
            if change.change_type == "modified" and change.impact in ("medium", "high"):
                side_effects.append(SideEffect(
                    description=f"Modified signature of {change.symbol_name}",
                    severity=change.impact,
                    affected_symbols=[change.symbol_name],
                ))

        return side_effects

    def _extract_symbols(
        self,
        code: str,
        language: str,
    ) -> Dict[str, str]:
        """
        Extract symbols from code.

        Returns dictionary mapping symbol name to signature.
        """
        symbols = {}

        if language == "python":
            symbols = self._extract_python_symbols(code)
        elif language in ("javascript", "typescript"):
            symbols = self._extract_javascript_symbols(code)
        elif language == "rust":
            symbols = self._extract_rust_symbols(code)
        else:
            symbols = self._extract_generic_symbols(code)

        return symbols

    def _extract_python_symbols(self, code: str) -> Dict[str, str]:
        """Extract Python symbols."""
        import re

        symbols = {}

        # Extract functions
        for match in re.finditer(r"def\s+(\w+)\s*\(([^)]*)\)", code):
            name = match.group(1)
            params = match.group(2)
            symbols[name] = f"def {name}({params})"

        # Extract classes
        for match in re.finditer(r"class\s+(\w+)(?:\(([^)]*)\))?:", code):
            name = match.group(1)
            bases = match.group(2) or ""
            symbols[name] = f"class {name}({bases})" if bases else f"class {name}"

        return symbols

    def _extract_javascript_symbols(self, code: str) -> Dict[str, str]:
        """Extract JavaScript/TypeScript symbols."""
        import re

        symbols = {}

        # Extract functions
        for match in re.finditer(r"function\s+(\w+)\s*\(([^)]*)\)", code):
            name = match.group(1)
            params = match.group(2)
            symbols[name] = f"function {name}({params})"

        # Extract classes
        for match in re.finditer(r"class\s+(\w+)", code):
            name = match.group(1)
            symbols[name] = f"class {name}"

        # Extract const arrow functions
        for match in re.finditer(r"const\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)", code):
            name = match.group(1)
            params = match.group(2)
            symbols[name] = f"const {name} = ({params}) => ..."

        return symbols

    def _extract_rust_symbols(self, code: str) -> Dict[str, str]:
        """Extract Rust symbols."""
        import re

        symbols = {}

        # Extract functions
        for match in re.finditer(r"fn\s+(\w+)\s*\(([^)]*)\)", code):
            name = match.group(1)
            params = match.group(2)
            symbols[name] = f"fn {name}({params})"

        # Extract structs
        for match in re.finditer(r"struct\s+(\w+)", code):
            name = match.group(1)
            symbols[name] = f"struct {name}"

        # Extract traits
        for match in re.finditer(r"trait\s+(\w+)", code):
            name = match.group(1)
            symbols[name] = f"trait {name}"

        return symbols

    def _extract_generic_symbols(self, code: str) -> Dict[str, str]:
        """Generic symbol extraction fallback."""
        import re

        symbols = {}

        # Generic function pattern
        for match in re.finditer(r"\b(?:function|def|fn)\s+(\w+)", code):
            name = match.group(1)
            symbols[name] = f"function {name}"

        # Generic class pattern
        for match in re.finditer(r"\b(?:class|struct|type)\s+(\w+)", code):
            name = match.group(1)
            symbols[name] = f"class {name}"

        return symbols

    def _extract_function_calls(
        self,
        code: str,
        language: str,
    ) -> Set[str]:
        """Extract function calls from code."""
        import re

        calls = set()

        # Pattern for method calls: obj.method()
        for match in re.finditer(r"(\w+)\.(\w+)\s*\(", code):
            caller = match.group(1)
            callee = match.group(2)
            calls.add(f"{caller}->{callee}")

        # Pattern for function calls: func()
        for match in re.finditer(r"(?<!\.)(\w+)\s*\([^)]*\)", code):
            func = match.group(1)
            if func not in ("if", "for", "while", "with", "return", "import"):
                calls.add(f"__module__->{func}")

        return calls

    def _determine_impact(
        self,
        symbol: str,
        old_signature: str,
        new_signature: str,
    ) -> str:
        """Determine impact level of a symbol change."""
        # Count parameter changes
        import re

        old_params = re.findall(r"\w+", old_signature)
        new_params = re.findall(r"\w+", new_signature)

        param_diff = abs(len(old_params) - len(new_params))

        if param_diff > 2:
            return "high"
        elif param_diff > 0:
            return "medium"

        # Check for return type changes
        if " -> " in old_signature and " -> " in new_signature:
            old_return = old_signature.split(" -> ")[-1]
            new_return = new_signature.split(" -> ")[-1]
            if old_return != new_return:
                return "medium"

        return "low"
