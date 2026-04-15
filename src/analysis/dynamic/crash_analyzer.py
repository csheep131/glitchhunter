#!/usr/bin/env python3
"""
Crash Analyzer for GlitchHunter Dynamic Analysis

Analysiert und klassifiziert Crashes aus Fuzzing:
- Crash-Typ identifizieren (Segfault, Buffer-Overflow, etc.)
- Reproduktions-Pfad extrahieren
- Duplicate Detection
- Severity-Bewertung
"""

import hashlib
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class CrashInfo:
    """Informationen über einen Crash."""

    crash_file: str
    crash_id: str
    crash_type: str
    signal: int
    address: Optional[int] = None
    stack_trace: List[str] = field(default_factory=list)
    severity: str = "unknown"  # critical, high, medium, low
    reproducible: bool = True
    input_hex: str = ""
    input_size: int = 0
    target_function: Optional[str] = None
    duplicate_of: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "crash_id": self.crash_id,
            "crash_type": self.crash_type,
            "signal": self.signal,
            "address": self.address,
            "severity": self.severity,
            "stack_trace": self.stack_trace,
            "reproducible": self.reproducible,
            "input_size": self.input_size,
            "target_function": self.target_function,
        }


class CrashAnalyzer:
    """
    Analysiert und klassifiziert Fuzzing-Crashes.

    Usage:
        analyzer = CrashAnalyzer(target_binary="./fuzz_target")
        crashes = analyzer.analyze_crash_dir("./crashes")
        
        for crash in crashes:
            print(f"{crash.crash_type}: {crash.severity}")
    """

    def __init__(
        self,
        target_binary: str,
        timeout: int = 5,
    ):
        """
        Initialisiert Crash-Analyzer.

        Args:
            target_binary: Zu fuzzendes Binary
            timeout: Timeout pro Crash-Reproduktion
        """
        self.target_binary = Path(target_binary)
        self.timeout = timeout
        self.seen_crashes: Set[str] = set()  # Für Duplicate Detection

    def analyze_crash_dir(self, crash_dir: str) -> List[CrashInfo]:
        """
        Analysiert alle Crashes in einem Verzeichnis.

        Args:
            crash_dir: Verzeichnis mit Crash-Files

        Returns:
            Liste von CrashInfo-Objekten
        """
        crashes = []
        crash_path = Path(crash_dir)

        if not crash_path.exists():
            logger.warning(f"Crash directory not found: {crash_dir}")
            return []

        for crash_file in crash_path.glob("id:*"):
            try:
                crash = self.analyze_crash(str(crash_file))
                if crash:
                    crashes.append(crash)
            except Exception as e:
                logger.error(f"Failed to analyze {crash_file}: {e}")

        # Duplikate entfernen
        unique_crashes = self._remove_duplicates(crashes)

        logger.info(
            f"Analyzed {len(crashes)} crashes, "
            f"{len(unique_crashes)} unique"
        )

        return unique_crashes

    def analyze_crash(self, crash_file: str) -> Optional[CrashInfo]:
        """
        Analysiert einen einzelnen Crash.

        Args:
            crash_file: Pfad zur Crash-Input-Datei

        Returns:
            CrashInfo-Objekt oder None
        """
        crash_path = Path(crash_file)
        if not crash_path.exists():
            return None

        # Metadaten aus Filename extrahieren
        metadata = self._parse_crash_filename(crash_path.name)

        # Crash reproduzieren und analysieren
        reproduction = self._reproduce_crash(crash_path)

        # Crash-Typ bestimmen
        crash_type = self._classify_crash(
            signal=metadata.get("signal", 0),
            stack_trace=reproduction.get("stack_trace", []),
            address=metadata.get("address"),
        )

        # Severity bewerten
        severity = self._assess_severity(crash_type, metadata)

        # Input-Information
        input_hex = ""
        input_size = 0
        try:
            content = crash_path.read_bytes()
            input_hex = content[:200].hex()
            input_size = len(content)
        except Exception:
            pass

        # Crash-ID generieren (Hash von Typ + Stack)
        crash_id = self._generate_crash_id(crash_type, reproduction.get("stack_trace", []))

        # Duplicate-Check
        duplicate_of = None
        if crash_id in self.seen_crashes:
            duplicate_of = crash_id
        else:
            self.seen_crashes.add(crash_id)

        return CrashInfo(
            crash_file=str(crash_path),
            crash_id=crash_id,
            crash_type=crash_type,
            signal=metadata.get("signal", 0),
            address=metadata.get("address"),
            stack_trace=reproduction.get("stack_trace", []),
            severity=severity,
            reproducible=reproduction.get("reproducible", False),
            input_hex=input_hex,
            input_size=input_size,
            target_function=self._extract_target_function(
                reproduction.get("stack_trace", [])
            ),
            duplicate_of=duplicate_of,
        )

    def _parse_crash_filename(self, filename: str) -> Dict[str, Any]:
        """
        Parst Metadaten aus AFL++ Crash-Filename.

        Format: id:000000,sig:11,src:000001,op:flip1,pos:42,addr:0x1234
        """
        metadata: Dict[str, Any] = {}

        parts = filename.split(",")
        for part in parts:
            if ":" in part:
                key, value = part.split(":", 1)
                if key == "id":
                    metadata["crash_id"] = value
                elif key == "sig":
                    metadata["signal"] = int(value)
                elif key == "addr":
                    try:
                        metadata["address"] = int(value, 16)
                    except ValueError:
                        pass
                elif key == "op":
                    metadata["mutation_op"] = value

        return metadata

    def _reproduce_crash(self, crash_file: Path) -> Dict[str, Any]:
        """
        Reproduziert einen Crash und extrahiert Informationen.

        Args:
            crash_file: Crash-Input-Datei

        Returns:
            Dict mit reproduction, stack_trace, etc.
        """
        result = {
            "reproducible": False,
            "stack_trace": [],
            "stderr": "",
        }

        if not self.target_binary.exists():
            return result

        try:
            # Binary mit Crash-Input ausführen
            proc = subprocess.Popen(
                [str(self.target_binary), str(crash_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            stdout, stderr = proc.communicate(timeout=self.timeout)

            # Crash erkannt?
            if proc.returncode != 0 and proc.returncode != 1:
                result["reproducible"] = True
                result["stderr"] = stderr.decode("utf-8", errors="ignore")

                # Stack-Trace aus stderr extrahieren
                result["stack_trace"] = self._extract_stack_trace(
                    result["stderr"]
                )

        except subprocess.TimeoutExpired:
            result["reproducible"] = True
            result["stderr"] = "Timeout (possible hang)"
        except Exception as e:
            result["stderr"] = str(e)

        return result

    def _extract_stack_trace(self, stderr: str) -> List[str]:
        """Extrahiert Stack-Trace aus stderr."""
        stack = []
        in_stack = False

        for line in stderr.split("\n"):
            # ASan Stack-Trace
            if "SUMMARY:" in line:
                break

            if in_stack:
                # Stack-Frame: #0 0x... in function_name
                if line.strip().startswith("#"):
                    stack.append(line.strip())

            # Stack-Trace beginnt
            if "Stack trace" in line or "AddressSanitizer" in line:
                in_stack = True

        return stack

    def _classify_crash(
        self,
        signal: int,
        stack_trace: List[str],
        address: Optional[int] = None,
    ) -> str:
        """
        Klassifiziert Crash-Typ basierend auf Signal und Stack-Trace.
        """
        # Signal-basierte Klassifikation
        signal_types = {
            4: "SIGILL (Illegal Instruction)",
            6: "SIGABRT (Abort)",
            7: "SIGBUS (Bus Error)",
            8: "SIGFPE (Floating Point Exception)",
            11: "SIGSEGV (Segmentation Fault)",
        }

        base_type = signal_types.get(signal, f"Signal {signal}")

        # Stack-Trace für detailliertere Klassifikation
        stack_str = " ".join(stack_trace).lower()

        if "heap-buffer-overflow" in stack_str:
            return "Heap-Buffer-Overflow"
        elif "stack-buffer-overflow" in stack_str:
            return "Stack-Buffer-Overflow"
        elif "use-after-free" in stack_str:
            return "Use-After-Free"
        elif "double-free" in stack_str:
            return "Double-Free"
        elif "null-pointer" in stack_str or "nullptr" in stack_str:
            return "Null-Pointer-Dereference"
        elif "memcpy" in stack_str or "memmove" in stack_str:
            return f"Memory-Corruption ({base_type})"
        elif "strcpy" in stack_str or "sprintf" in stack_str:
            return f"Buffer-Overflow ({base_type})"

        return base_type

    def _assess_severity(
        self,
        crash_type: str,
        metadata: Dict[str, Any],
    ) -> str:
        """
        Bewertet Crash-Severity.

        Critical: Exploitable (RCE, severe memory corruption)
        High: Memory corruption, use-after-free
        Medium: Null-pointer, assertion failures
        Low: Information leaks, minor issues
        """
        crash_lower = crash_type.lower()

        # Critical: Potentiell exploitable
        if any(
            x in crash_lower
            for x in ["rce", "remote", "command-injection", "format-string"]
        ):
            return "critical"

        # High: Memory-Corruption
        if any(
            x in crash_lower
            for x in [
                "buffer-overflow",
                "use-after-free",
                "double-free",
                "heap-corruption",
            ]
        ):
            return "high"

        # Medium: Null-Pointer, Assertion
        if any(
            x in crash_lower
            for x in [
                "null-pointer",
                "assertion",
                "sigabrt",
            ]
        ):
            return "medium"

        # Low: Andere
        return "low"

    def _generate_crash_id(
        self,
        crash_type: str,
        stack_trace: List[str],
    ) -> str:
        """
        Generiert eindeutige Crash-ID für Duplicate-Detection.
        """
        # Hash von Crash-Typ + erstem Stack-Frame
        key = f"{crash_type}:{stack_trace[0] if stack_trace else 'unknown'}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def _remove_duplicates(
        self,
        crashes: List[CrashInfo],
    ) -> List[CrashInfo]:
        """Entfernt Duplikate aus Crash-Liste."""
        unique: Dict[str, CrashInfo] = {}

        for crash in crashes:
            if crash.duplicate_of:
                continue

            if crash.crash_id not in unique:
                unique[crash.crash_id] = crash

        return list(unique.values())

    def _extract_target_function(self, stack_trace: List[str]) -> Optional[str]:
        """Extrahiert Ziel-Funktion aus Stack-Trace."""
        for frame in stack_trace:
            # Funktion aus Stack-Frame extrahieren
            # Format: #0 0x... in function_name
            if " in " in frame:
                parts = frame.split(" in ")
                if len(parts) >= 2:
                    func = parts[1].split("(")[0].strip()
                    if func and func != "??":
                        return func
        return None

    def generate_crash_report(
        self,
        crashes: List[CrashInfo],
        output_file: Optional[str] = None,
    ) -> str:
        """
        Generiert Crash-Report.

        Args:
            crashes: Liste von CrashInfo-Objekten
            output_file: Optionale Datei zum Speichern

        Returns:
            Report-String
        """
        report_lines = [
            "# 🚨 GlitchHunter Crash Report",
            "",
            f"**Total Crashes:** {len(crashes)}",
            f"**Unique Crashes:** {len(set(c.crash_id for c in crashes))}",
            "",
            "## Summary by Severity",
            "",
        ]

        # Nach Severity gruppieren
        by_severity: Dict[str, List[CrashInfo]] = {}
        for crash in crashes:
            if crash.severity not in by_severity:
                by_severity[crash.severity] = []
            by_severity[crash.severity].append(crash)

        for severity in ["critical", "high", "medium", "low"]:
            count = len(by_severity.get(severity, []))
            if count > 0:
                report_lines.append(f"- **{severity.upper()}:** {count}")

        report_lines.extend(["", "## Crash Details", ""])

        # Details pro Crash
        for crash in crashes:
            report_lines.extend(
                [
                    f"### {crash.crash_type}",
                    "",
                    f"- **ID:** {crash.crash_id}",
                    f"- **Severity:** {crash.severity}",
                    f"- **Signal:** {crash.signal}",
                    f"- **Reproducible:** {'Yes' if crash.reproducible else 'No'}",
                    f"- **Input Size:** {crash.input_size} bytes",
                ]
            )

            if crash.target_function:
                report_lines.append(f"- **Target Function:** `{crash.target_function}`")

            if crash.stack_trace:
                report_lines.extend(["", "**Stack Trace:**", "```"])
                report_lines.extend(crash.stack_trace[:10])  # Erste 10 Frames
                report_lines.append("```")

            report_lines.append("")

        report = "\n".join(report_lines)

        if output_file:
            Path(output_file).write_text(report)
            logger.info(f"Crash report saved: {output_file}")

        return report
