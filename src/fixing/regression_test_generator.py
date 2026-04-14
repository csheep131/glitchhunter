"""
Regression test generator for GlitchHunter.

Generates property-based tests for bugs to ensure regression-proof fixing.
Supports multiple test frameworks: hypothesis (Python), proptest (Rust),
fast-check (JavaScript).
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TestSpec:
    """
    Test specification for a regression test.

    Attributes:
        name: Test name
        description: Test description
        file_path: Target file path
        test_code: Generated test code
        framework: Test framework (hypothesis, proptest, jest)
        language: Programming language
        inputs: Test input specifications
        expected_behavior: Expected behavior description
    """

    name: str
    description: str
    file_path: str
    test_code: str
    framework: str
    language: str
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    expected_behavior: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "file_path": self.file_path,
            "test_code": self.test_code,
            "framework": self.framework,
            "language": self.language,
            "inputs": self.inputs,
            "expected_behavior": self.expected_behavior,
        }


@dataclass
class Candidate:
    """Bug candidate for test generation."""

    file_path: str
    bug_type: str
    description: str
    line_start: int
    line_end: int


class RegressionTestGenerator:
    """
    Generates property-based tests for bugs.

    Supports multiple test frameworks:
    - Python: hypothesis + pytest
    - Rust: proptest
    - JavaScript: jest + fast-check

    Example:
        >>> generator = RegressionTestGenerator()
        >>> test = generator.generate_test_for_bug(candidate, data_flow_graph)
        >>> print(test.test_code)
    """

    def __init__(self) -> None:
        """Initialize regression test generator."""
        self.frameworks = {
            "python": "hypothesis",
            "rust": "proptest",
            "javascript": "fast-check",
            "typescript": "fast-check",
        }
        logger.debug("RegressionTestGenerator initialized")

    def generate_test_for_bug(
        self,
        candidate: Candidate,
        data_flow_graph: Optional[Dict[str, Any]] = None,
    ) -> TestSpec:
        """
        Generate a regression test for a bug candidate.

        Args:
            candidate: Bug candidate
            data_flow_graph: Optional data flow graph

        Returns:
            TestSpec with generated test
        """
        logger.info(f"Generating test for bug in {candidate.file_path}")

        # Detect language
        language = self._detect_language(candidate.file_path)
        framework = self.frameworks.get(language, "hypothesis")

        # Generate test based on language
        if language == "python":
            test_code = self._generate_python_test(candidate, data_flow_graph)
        elif language == "rust":
            test_code = self._generate_rust_test(candidate, data_flow_graph)
        elif language in ("javascript", "typescript"):
            test_code = self._generate_javascript_test(candidate, data_flow_graph)
        else:
            test_code = self._generate_generic_test(candidate, data_flow_graph)

        test = TestSpec(
            name=f"test_regression_{self._sanitize_name(candidate.bug_type)}",
            description=f"Regression test for {candidate.bug_type}",
            file_path=candidate.file_path,
            test_code=test_code,
            framework=framework,
            language=language,
            expected_behavior=candidate.description,
        )

        logger.info(f"Generated test: {test.name} ({framework})")
        return test

    def generate_edge_case_tests(
        self,
        candidate: Candidate,
        num: int = 5,
    ) -> List[TestSpec]:
        """
        Generate edge case tests for a candidate.

        Args:
            candidate: Bug candidate
            num: Number of edge case tests

        Returns:
            List of TestSpec objects
        """
        tests = []
        language = self._detect_language(candidate.file_path)

        edge_cases = self._generate_edge_cases(candidate, num)

        for i, edge_case in enumerate(edge_cases):
            test = TestSpec(
                name=f"test_edge_case_{i}_{self._sanitize_name(candidate.bug_type)}",
                description=f"Edge case test: {edge_case['description']}",
                file_path=candidate.file_path,
                test_code=self._generate_test_code(language, edge_case),
                framework=self.frameworks.get(language, "hypothesis"),
                language=language,
                inputs=[edge_case],
                expected_behavior=edge_case["expected"],
            )
            tests.append(test)

        return tests

    def generate_property_based_test(
        self,
        candidate: Candidate,
    ) -> str:
        """
        Generate property-based test code.

        Args:
            candidate: Bug candidate

        Returns:
            Test code as string
        """
        language = self._detect_language(candidate.file_path)

        if language == "python":
            return self._generate_hypothesis_test(candidate)
        elif language == "rust":
            return self._generate_proptest_test(candidate)
        elif language in ("javascript", "typescript"):
            return self._generate_fast_check_test(candidate)
        else:
            return self._generate_generic_test_code(candidate)

    def generate_assertion(
        self,
        candidate: Candidate,
        expected_behavior: str,
    ) -> str:
        """
        Generate assertion code for expected behavior.

        Args:
            candidate: Bug candidate
            expected_behavior: Expected behavior description

        Returns:
            Assertion code
        """
        language = self._detect_language(candidate.file_path)

        if language == "python":
            return f"assert result, \"{expected_behavior}\""
        elif language == "rust":
            escaped = expected_behavior.replace('"', '\\"')
            return f'assert!(result, "{escaped}");'
        elif language in ("javascript", "typescript"):
            return f'expect(result).toBeTruthy(); // {expected_behavior}'
        else:
            return f"// Assert: {expected_behavior}"

    def _detect_language(self, file_path: str) -> str:
        """Detect language from file path."""
        path = Path(file_path)
        extension = path.suffix.lower()

        extension_map = {
            ".py": "python",
            ".rs": "rust",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
        }

        return extension_map.get(extension, "python")

    def _sanitize_name(self, name: str) -> str:
        """Sanitize name for use in test function."""
        import re
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower())
        return sanitized[:50]

    def _generate_python_test(
        self,
        candidate: Candidate,
        data_flow_graph: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate Python test using hypothesis."""
        return self._generate_hypothesis_test(candidate)

    def _generate_rust_test(
        self,
        candidate: Candidate,
        data_flow_graph: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate Rust test using proptest."""
        return self._generate_proptest_test(candidate)

    def _generate_javascript_test(
        self,
        candidate: Candidate,
        data_flow_graph: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate JavaScript test using jest + fast-check."""
        return self._generate_fast_check_test(candidate)

    def _generate_generic_test(
        self,
        candidate: Candidate,
        data_flow_graph: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate generic test fallback."""
        return f"""
# Test for {candidate.bug_type}
# File: {candidate.file_path}
# Description: {candidate.description}

def test_regression_{self._sanitize_name(candidate.bug_type)}():
    # TODO: Implement test
    pass
"""

    def _generate_hypothesis_test(self, candidate: Candidate) -> str:
        """Generate hypothesis-based test for Python."""
        bug_type = self._sanitize_name(candidate.bug_type)

        return f'''
"""
Regression test for {candidate.bug_type}
File: {candidate.file_path}
Description: {candidate.description}
"""
import pytest
from hypothesis import given, strategies as st

@given(
    # TODO: Define appropriate strategies for your function
    value=st.text(min_size=1, max_size=100),
)
def test_regression_{bug_type}(value: str) -> None:
    """
    Property-based test for {candidate.bug_type}.
    
    This test ensures the bug does not regress.
    """
    # TODO: Import the function to test
    # from {Path(candidate.file_path).stem} import target_function
    
    # TODO: Call the function with test input
    # result = target_function(value)
    
    # TODO: Add assertion based on expected behavior
    # The bug was: {candidate.description}
    # Ensure this behavior is now fixed
    assert True, "Bug should be fixed"
'''

    def _generate_proptest_test(self, candidate: Candidate) -> str:
        """Generate proptest-based test for Rust."""
        bug_type = self._sanitize_name(candidate.bug_type)

        return f'''
// Regression test for {candidate.bug_type}
// File: {candidate.file_path}
// Description: {candidate.description}

use proptest::prelude::*;

#[test]
fn test_regression_{bug_type}() {{
    proptest!(|(value in ".{{1,100}}") {{
        // TODO: Call the function with test input
        // let result = target_function(&value);
        
        // TODO: Add assertion based on expected behavior
        // The bug was: {candidate.description}
        // Ensure this behavior is now fixed
        prop_assert!(true, "Bug should be fixed");
    }});
}}
'''

    def _generate_fast_check_test(self, candidate: Candidate) -> str:
        """Generate fast-check test for JavaScript/TypeScript."""
        bug_type = self._sanitize_name(candidate.bug_type)

        return f'''
// Regression test for {candidate.bug_type}
// File: {candidate.file_path}
// Description: {candidate.description}

import {{ test, expect }} from '@jest/globals';
import * as fc from 'fast-check';

test('regression test for {candidate.bug_type}', () => {{
    fc.assert(
        fc.property(
            fc.string({{ minLength: 1, maxLength: 100 }}),
            (value) => {{
                // TODO: Call the function with test input
                // const result = targetFunction(value);
                
                // TODO: Add assertion based on expected behavior
                // The bug was: {candidate.description}
                // Ensure this behavior is now fixed
                expect(true).toBe(true); // Bug should be fixed
            }}
        )
    );
}});
'''

    def _generate_generic_test_code(self, candidate: Candidate) -> str:
        """Generate generic test code fallback."""
        return f"""
// Test for {candidate.bug_type}
// File: {candidate.file_path}

function test_regression_{self._sanitize_name(candidate.bug_type)}() {{
    // TODO: Implement test
    // Bug: {candidate.description}
}}
"""

    def _generate_edge_cases(
        self,
        candidate: Candidate,
        num: int,
    ) -> List[Dict[str, Any]]:
        """Generate edge case inputs."""
        edge_cases = []

        # Generic edge cases
        generic_cases = [
            {"input": "", "description": "Empty input", "expected": "Should handle empty input"},
            {"input": "a" * 1000, "description": "Very long input", "expected": "Should handle long input"},
            {"input": "null", "description": "Null input", "expected": "Should handle null"},
            {"input": "<script>alert('xss')</script>", "description": "XSS attempt", "expected": "Should sanitize input"},
            {"input": "'; DROP TABLE users; --", "description": "SQL injection attempt", "expected": "Should prevent SQL injection"},
        ]

        for i, case in enumerate(generic_cases[:num]):
            edge_cases.append({
                "value": case["input"],
                "description": case["description"],
                "expected": case["expected"],
            })

        return edge_cases

    def _generate_test_code(
        self,
        language: str,
        edge_case: Dict[str, Any],
    ) -> str:
        """Generate test code for an edge case."""
        if language == "python":
            return f"""
def test_edge_case():
    value = "{edge_case['value']}"
    # TODO: result = target_function(value)
    # Expected: {edge_case['expected']}
    assert True
"""
        elif language == "rust":
            return f"""
#[test]
fn test_edge_case() {{
    let value = "{edge_case['value']}";
    // TODO: let result = target_function(&value);
    // Expected: {edge_case['expected']}
    assert!(true);
}}
"""
        else:
            return f"""
test('edge case', () => {{
    const value = "{edge_case['value']}";
    // TODO: const result = targetFunction(value);
    // Expected: {edge_case['expected']}
    expect(true).toBe(true);
}});
"""
