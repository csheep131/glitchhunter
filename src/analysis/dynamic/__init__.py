#!/usr/bin/env python3
"""
Dynamic Analysis Module for GlitchHunter v2.0

Provides coverage-guided fuzzing capabilities:
- AFL++ integration for C/C++ code
- libFuzzer for LLVM-based fuzzing
- Atheris for Python fuzzing
- Coverage tracking and crash analysis
"""

from .fuzzer import AFLPlusPlusFuzzer, LibFuzzer, AtherisFuzzer
from .coverage import CoverageTracker
from .dynamic_analyzer import DynamicAnalyzer
from .harness_generator import HarnessGenerator
from .crash_analyzer import CrashAnalyzer

__all__ = [
    "AFLPlusPlusFuzzer",
    "LibFuzzer",
    "AtherisFuzzer",
    "CoverageTracker",
    "DynamicAnalyzer",
    "HarnessGenerator",
    "CrashAnalyzer",
]
