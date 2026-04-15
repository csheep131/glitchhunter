#!/usr/bin/env python3
"""
Fuzzing Harness Generator for GlitchHunter

Automatically generates fuzzing harnesses from code analysis:
- Identifies target functions via Symbol-Graph
- Generates C/C++ harness for AFL++
- Generates Python harness for Atheris
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FuzzTarget:
    """Eine zu fuzzende Funktion."""

    function_name: str
    file_path: str
    line_number: int
    parameters: List[Dict[str, str]] = field(default_factory=list)
    return_type: str = "void"
    language: str = "unknown"
    risk_score: float = 0.0
    is_entry_point: bool = False


@dataclass
class HarnessResult:
    """Ergebnis der Harness-Generierung."""

    harness_file: str
    target_function: str
    language: str
    build_command: Optional[str] = None
    run_command: Optional[str] = None
    corpus_seeds: List[str] = field(default_factory=list)


class HarnessGenerator:
    """
    Generiert Fuzzing-Harnesses automatisch aus Code-Analyse.

    Usage:
        generator = HarnessGenerator(repo_path="/path/to/repo")
        targets = generator.identify_fuzz_targets()
        harness = generator.generate_harness(targets[0])
    """

    def __init__(self, repo_path: Path):
        """
        Initialisiert Harness-Generator.

        Args:
            repo_path: Pfad zum zu analysierenden Repository
        """
        self.repo_path = Path(repo_path)
        self.symbol_graph = None

    def load_symbol_graph(self) -> bool:
        """Lädt den Symbol-Graph für die Analyse."""
        try:
            from mapper.repo_mapper import RepositoryMapper

            mapper = RepositoryMapper(self.repo_path)
            self.symbol_graph = mapper.build_graph()
            logger.info(f"Symbol-Graph loaded: {len(self.symbol_graph._graph.nodes())} symbols")
            return True
        except Exception as e:
            logger.warning(f"Failed to load symbol graph: {e}")
            return False

    def identify_fuzz_targets(
        self,
        max_targets: int = 10,
        min_risk_score: float = 0.5,
    ) -> List[FuzzTarget]:
        """
        Identifiziert vielversprechende Fuzzing-Ziele.

        Args:
            max_targets: Maximale Anzahl zurückgegebener Targets
            min_risk_score: Minimale Risikobewertung

        Returns:
            Liste von FuzzTarget-Objekten
        """
        if not self.symbol_graph:
            if not self.load_symbol_graph():
                return []

        targets: List[FuzzTarget] = []

        # Durchlaufe alle Symbole im Graph
        for node_id, node_data in self.symbol_graph._graph.nodes(data=True):
            # Nur Funktionen analysieren
            if node_data.get("type") != "function":
                continue

            # Risikobewertung berechnen
            risk_score = self._calculate_risk_score(node_data)
            if risk_score < min_risk_score:
                continue

            # Target erstellen
            target = FuzzTarget(
                function_name=node_data.get("name", "unknown"),
                file_path=node_data.get("file_path", ""),
                line_number=node_data.get("line", 0),
                parameters=self._extract_parameters(node_data),
                return_type=node_data.get("return_type", "void"),
                language=node_data.get("language", "unknown"),
                risk_score=risk_score,
                is_entry_point=node_data.get("is_entry_point", False),
            )
            targets.append(target)

        # Nach Risiko sortieren und begrenzen
        targets.sort(key=lambda t: t.risk_score, reverse=True)
        return targets[:max_targets]

    def _calculate_risk_score(self, node_data: Dict[str, Any]) -> float:
        """
        Berechnet Risikobewertung für eine Funktion.

        Faktoren:
        - Name-Indikatoren (parse, read, write, exec, etc.)
        - Parameter-Typen (Pointer, Arrays, Strings)
        - Externe Aufrufe
        - Speicheroperationen
        """
        score = 0.0
        name = node_data.get("name", "").lower()
        code_context = node_data.get("code_context", "")

        # Riskante Funktionsnamen
        risky_names = [
            "parse", "read", "write", "exec", "eval", "strcpy", "sprintf",
            "malloc", "free", "memcpy", "memmove", "open", "close",
            "socket", "connect", "send", "recv",
        ]
        for risky in risky_names:
            if risky in name:
                score += 0.2

        # Riskante Operationen im Code
        risky_ops = [
            "strcpy", "strcat", "sprintf", "gets", "scanf",
            "malloc", "calloc", "realloc", "free",
            "memcpy", "memmove", "memset",
        ]
        for op in risky_ops:
            if op in code_context:
                score += 0.15

        # Pointer-Parameter
        params = self._extract_parameters(node_data)
        for param in params:
            param_type = param.get("type", "")
            if "*" in param_type or "ptr" in param_type.lower():
                score += 0.1

        # Externe Aufrufe
        if node_data.get("calls_external", False):
            score += 0.2

        return min(score, 1.0)

    def _extract_parameters(self, node_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extrahiert Parameter-Informationen."""
        params = node_data.get("parameters", [])
        if isinstance(params, str):
            # String parsen (z.B. "int x, char* buf")
            param_list = []
            for param in params.split(","):
                param = param.strip()
                if param:
                    parts = param.rsplit(" ", 1)
                    if len(parts) == 2:
                        param_list.append({"type": parts[0], "name": parts[1]})
                    else:
                        param_list.append({"type": "unknown", "name": param})
            return param_list
        return params if isinstance(params, list) else []

    def generate_harness(
        self,
        target: FuzzTarget,
        output_dir: Optional[str] = None,
    ) -> Optional[HarnessResult]:
        """
        Generiert Fuzzing-Harness für ein Target.

        Args:
            target: FuzzTarget-Objekt
            output_dir: Ausgabe-Verzeichnis (default: .glitchhunter/fuzz_harness)

        Returns:
            HarnessResult mit generierter Harness
        """
        if output_dir is None:
            output_dir = str(self.repo_path / ".glitchhunter" / "fuzz_harness")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Sprachspezifische Generierung
        if target.language == "python":
            return self._generate_python_harness(target, output_path)
        elif target.language in ("c", "cpp", "c++"):
            return self._generate_cpp_harness(target, output_path)
        else:
            logger.warning(f"Unsupported language for harness: {target.language}")
            return None

    def _generate_cpp_harness(
        self,
        target: FuzzTarget,
        output_path: Path,
    ) -> Optional[HarnessResult]:
        """Generiert C/C++ Harness für AFL++."""
        harness_file = output_path / f"fuzz_{target.function_name}.cpp"

        # Header generieren
        header = f"""// AFL++ Fuzzing Harness für {target.function_name}
// Auto-generated by GlitchHunter v2.0

#include <stdint.h>
#include <stddef.h>
#include <stdio.h>

// Externe Deklaration der Target-Funktion
"""

        # Funktions-Deklaration
        params_str = ", ".join(
            f"{p.get('type', 'void')} {p.get('name', 'arg')}"
            for p in target.parameters
        )
        header += f"{target.return_type} {target.function_name}({params_str});\n\n"

        # Harness-Body
        body = """
// LLVM libFuzzer Entry Point
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    // Input aufteilen für Parameter
    // TODO: Anpassen basierend auf tatsächlichen Parametern
    
    if (size < 1) return 0;
    
    // Beispiel: String-Input für erste Parameter
    char *input = (char *)malloc(size + 1);
    if (!input) return 0;
    
    memcpy(input, data, size);
    input[size] = '\\0';
    
    // Target-Funktion aufrufen
    // HINWEIS: Dies ist ein Template - anpassen!
    try {
        // Beispiel-Aufruf (muss angepasst werden)
        // target_function(input);
    } catch (...) {
        // Exceptions fangen für Continued Fuzzing
    }
    
    free(input);
    return 0;
}

// AFL++ persistent mode (optional, für bessere Performance)
#ifdef AFL_PERSISTENT
int main(int argc, char **argv) {
    char buf[4096];
    
    while (__AFL_LOOP(10000)) {
        int len = read(0, buf, sizeof(buf));
        if (len > 0) {
            buf[len] = '\\0';
            // Target aufrufen
            // target_function(buf);
        }
    }
    
    return 0;
}
#endif
"""

        harness_file.write_text(header + body)
        logger.info(f"Generated C++ harness: {harness_file}")

        # Build-Command
        build_cmd = (
            f"afl-clang-lto++ -g -O2 -fsanitize=address "
            f"-o {harness_file.stem} {harness_file}"
        )

        # Run-Command
        run_cmd = f"afl-fuzz -i corpus -o output -- ./{harness_file.stem} @@"

        return HarnessResult(
            harness_file=str(harness_file),
            target_function=target.function_name,
            language="cpp",
            build_command=build_cmd,
            run_command=run_cmd,
            corpus_seeds=self._generate_cpp_corpus_seeds(output_path),
        )

    def _generate_python_harness(
        self,
        target: FuzzTarget,
        output_path: Path,
    ) -> Optional[HarnessResult]:
        """Generiert Python Harness für Atheris."""
        harness_file = output_path / f"fuzz_{target.function_name}.py"

        # Import-Modul extrahieren
        module_name = Path(target.file_path).stem

        # Harness generieren
        harness_code = f'''#!/usr/bin/env python3
"""
Atheris Fuzzing Harness für {target.function_name}
Auto-generated by GlitchHunter v2.0

Usage:
    pip install atheris
    python {harness_file.name}
"""

import sys
import atheris

# Target-Modul importieren
with atheris.instrument_imports():
    try:
        import {module_name}
    except ImportError:
        print(f"Warning: Could not import {{module_name}}")
        # Fallback: Leere Funktion
        class {module_name}:
            @staticmethod
            def {target.function_name}(*args):
                pass


def fuzz_target(input_bytes):
    """
    Fuzzing-Entry-Point für Atheris.
    
    Args:
        input_bytes: Fuzzing-Input (bytes)
    """
    try:
        # Input dekodieren (für String-Inputs)
        try:
            input_str = input_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return  # Ungültiger Input
        
        # Target-Funktion aufrufen
        # HINWEIS: Dies ist ein Template - anpassen!
        
        # Beispiel für Funktion mit einem String-Parameter:
        # {module_name}.{target.function_name}(input_str)
        
        # Beispiel für Funktion mit mehreren Parametern:
        # parts = input_str.split("\\n")
        # if len(parts) >= {len(target.parameters)}:
        #     {module_name}.{target.function_name}(*parts[:{len(target.parameters)}])
        
    except Exception as e:
        # Exceptions sind expected beim Fuzzing
        # Atheris reportet nur Crashes
        pass


def main():
    """Startet Atheris Fuzzing."""
    # Atheris konfigurieren
    atheris.Setup(sys.argv, fuzz_target)
    
    # Fuzzing starten
    # --dict=... für Custom-Dictionaries
    # -jobs=4 für paralleles Fuzzing
    atheris.Fuzz()


if __name__ == "__main__":
    main()
'''

        harness_file.write_text(harness_code)
        logger.info(f"Generated Python harness: {harness_file}")

        # Run-Command
        run_cmd = f"python {harness_file} -jobs=4 -workers=4"

        return HarnessResult(
            harness_file=str(harness_file),
            target_function=target.function_name,
            language="python",
            run_command=run_cmd,
            corpus_seeds=self._generate_python_corpus_seeds(output_path),
        )

    def _generate_cpp_corpus_seeds(self, output_path: Path) -> List[str]:
        """Generiert initiale Corpus-Seeds für C/C++."""
        corpus_dir = output_path / "corpus"
        corpus_dir.mkdir(parents=True, exist_ok=True)

        seeds = []

        # Seed 1: Leere Input
        seed1 = corpus_dir / "seed1_empty"
        seed1.write_bytes(b"")
        seeds.append(str(seed1))

        # Seed 2: Kurzer String
        seed2 = corpus_dir / "seed2_short"
        seed2.write_bytes(b"A" * 10)
        seeds.append(str(seed2))

        # Seed 3: Längerer String
        seed3 = corpus_dir / "seed3_long"
        seed3.write_bytes(b"B" * 100)
        seeds.append(str(seed3))

        # Seed 4: Special Characters
        seed4 = corpus_dir / "seed4_special"
        seed4.write_bytes(b"\x00\x01\x02\\x00\\xff\\xfe")
        seeds.append(str(seed4))

        logger.info(f"Generated {len(seeds)} corpus seeds")
        return seeds

    def _generate_python_corpus_seeds(self, output_path: Path) -> List[str]:
        """Generiert initiale Corpus-Seeds für Python."""
        corpus_dir = output_path / "corpus"
        corpus_dir.mkdir(parents=True, exist_ok=True)

        seeds = []

        # Seed 1: Leerer String
        seed1 = corpus_dir / "seed1_empty.txt"
        seed1.write_text("")
        seeds.append(str(seed1))

        # Seed 2: Einfacher String
        seed2 = corpus_dir / "seed2_simple.txt"
        seed2.write_text("test input")
        seeds.append(str(seed2))

        # Seed 3: Multi-Line
        seed3 = corpus_dir / "seed3_multiline.txt"
        seed3.write_text("line1\\nline2\\nline3")
        seeds.append(str(seed3))

        # Seed 4: Special Characters
        seed4 = corpus_dir / "seed4_unicode.txt"
        seed4.write_text("Hello 世界 🌍")
        seeds.append(str(seed4))

        logger.info(f"Generated {len(seeds)} corpus seeds")
        return seeds
