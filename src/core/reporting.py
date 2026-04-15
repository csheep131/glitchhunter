"""
Reporting module for GlitchHunter.

Generates Markdown and JSON reports for repository scans and analysis results.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import Config

logger = logging.getLogger(__name__)


class ScanReporter:
    """
    Generates scan reports in Markdown and JSON formats.

    This class aggregates findings, candidates, and metadata from the analysis
    workflow and creates structured reports for human and machine consumption.
    """
    
    # Verzeichnisse die von Bug-Reports ausgeschlossen werden
    # Hinweis: test_bugs/ ist ein spezielles Verzeichnis für GlitchHunter-Tests und wird NICHT ausgeschlossen
    EXCLUDED_DIRS = {'docs', 'tests', 'test', 'sandbox', 'examples', 'demos'}
    
    @staticmethod
    def _should_exclude_file(file_path: str) -> bool:
        """
        Prüft ob eine Datei aus den Bug-Reports ausgeschlossen werden soll.
        
        Ausschließen:
        - docs/, tests/, test/, sandbox/, examples/, demos/
        - Markdown-Dateien (.md) - sind Dokumentation
        - Test-Dateien (*_test.py, test_*.py, *_spec.js, etc.)
        
        Args:
            file_path: Zu prüfender Dateipfad
            
        Returns:
            True wenn Datei ausgeschlossen werden soll, False otherwise
        """
        from pathlib import Path
        p = Path(file_path)
        
        # Prüfe Verzeichnis-Pfad auf ausgeschlossene Ordner
        parts = p.parts
        for part in parts:
            if part in ScanReporter.EXCLUDED_DIRS:
                return True
        
        # Prüfe auf Dokumentations-Dateien
        if p.suffix.lower() == '.md':
            return True
        
        # Prüfe auf Test-Dateien
        name_lower = p.name.lower()
        if name_lower.endswith(('_test.py', '_test.js', '_test.ts', '_spec.js', '_spec.ts', '_spec.py')):
            return True
        if name_lower.startswith(('test_', 'spec_')):
            return True
            
        return False

    def __init__(self, repo_path: Path, reports_dir: Optional[Path] = None) -> None:
        """
        Initialize the reporter.

        Args:
            repo_path: Path to the scanned repository
            reports_dir: Directory where reports should be saved (optional override)
        """
        self.repo_path = repo_path.resolve()
        self.project_name = self.repo_path.name if self.repo_path.name else "project"
        
        # Load base reports directory from config
        if reports_dir:
            base_reports = reports_dir
        else:
            try:
                config = Config.load()
                project_root = Path(__file__).parent.parent.parent
                base_reports = project_root / config.paths.reports
            except Exception as e:
                logger.warning(f"Failed to load reports dir from config, using default: {e}")
                base_reports = Path("reports")
        
        # Create project-specific structure
        self.project_reports_dir = base_reports / self.project_name
        self.scans_dir = self.project_reports_dir / "scans"
        self.patches_dir = self.project_reports_dir / "patches"
        
        for d in [self.scans_dir, self.patches_dir]:
            d.mkdir(parents=True, exist_ok=True)
            
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.debug(f"ScanReporter initialized for {self.project_name} (scans: {self.scans_dir}, patches: {self.patches_dir})")

    def generate_report(self, state: Dict[str, Any]) -> Dict[str, Path]:
        """
        Generate both Markdown and JSON reports.

        Args:
            state: Full state from the state machine

        Returns:
            Dictionary mapping report type to file path
        """
        md_path = self.generate_markdown(state)
        json_path = self.generate_json(state)
        
        return {
            "markdown": md_path,
            "json": json_path
        }

    def save_patches(self, state: Dict[str, Any]) -> List[Path]:
        """
        Save verified patches as individual .diff files.

        Args:
            state: Full state from the state machine

        Returns:
            List of paths to saved patch files
        """
        saved_paths = []
        verified_patches = state.get("verified_patches", [])
        
        if not verified_patches:
            logger.debug("No verified patches to save.")
            return []

        for patch in verified_patches:
            file_path = patch.get("file_path", "unknown")
            bug_id = patch.get("bug_id", "bug")
            diff = patch.get("patch_diff", "")
            
            if not diff:
                continue
                
            # Create safe filename
            safe_file = Path(file_path).name.replace(".", "_")
            patch_filename = f"{safe_file}_{bug_id}_{self.timestamp}.diff"
            patch_file = self.patches_dir / patch_filename
            
            try:
                with open(patch_file, "w", encoding="utf-8") as f:
                    f.write(diff)
                saved_paths.append(patch_file)
                logger.debug(f"Saved patch to {patch_file}")
            except Exception as e:
                logger.error(f"Failed to save patch file {patch_file}: {e}")
                
        logger.info(f"Saved {len(saved_paths)} patch files to {self.patches_dir}")
        return saved_paths

    def generate_markdown(self, state: Dict[str, Any]) -> Path:
        """
        Generate a human-readable Markdown report in the scans directory.

        Args:
            state: Full state from the state machine

        Returns:
            Path to the generated file
        """
        report_file = self.scans_dir / f"{self.project_name}_scan_{self.timestamp}.md"

        # Aggregate findings by file (filter out docs/, tests/, etc.)
        findings_by_file: Dict[str, List[Dict[str, Any]]] = {}

        # From prefilter (Semgrep) - NUR src/ Verzeichnisse
        prefilter = state.get("prefilter_result", {})
        if prefilter and "semgrep_result" in prefilter:
            for finding in prefilter["semgrep_result"].get("findings", []):
                file_path = finding.get("file_path", "unknown")
                
                # Filtere docs/, tests/ und andere ausgeschlossene Verzeichnisse
                if self._should_exclude_file(file_path):
                    logger.debug(f"Excluding prefilter finding from {file_path}")
                    continue
                    
                if file_path not in findings_by_file:
                    findings_by_file[file_path] = []
                findings_by_file[file_path].append({
                    "type": "Security/Correctness (Semgrep)",
                    "rule": finding.get("rule_id"),
                    "severity": finding.get("severity"),
                    "message": finding.get("message"),
                    "line": finding.get("line_start")
                })

        # From candidates (only if they have real issues AND are not in excluded dirs)
        for candidate in state.get("candidates", []):
            if not candidate.get("bug_type") or candidate.get("bug_type") == "None":
                continue

            file_path = candidate.get("file_path", "unknown")
            
            # Filtere docs/, tests/ und andere ausgeschlossene Verzeichnisse
            if self._should_exclude_file(file_path):
                logger.debug(f"Excluding candidate from {file_path}")
                continue
            
            if file_path not in findings_by_file:
                findings_by_file[file_path] = []

            findings_by_file[file_path].append({
                "type": "AI Candidate",
                "rule": candidate.get("bug_type"),
                "severity": candidate.get("severity"),
                "message": candidate.get("description"),
                "line": candidate.get("line_start"),
                "confidence": candidate.get("confidence")
            })

        # From verified hypotheses (only in real source code)
        for hyp in state.get("hypotheses", []):
            if not hyp.get("verified") and hyp.get("confidence", 0) < 0.7:
                continue

            candidate = hyp.get("candidate", {})
            file_path = candidate.get("file_path", "unknown")
            
            # Filtere docs/, tests/ und andere ausgeschlossene Verzeichnisse
            if self._should_exclude_file(file_path):
                logger.debug(f"Excluding hypothesis from {file_path}")
                continue
            
            if file_path not in findings_by_file:
                findings_by_file[file_path] = []

            findings_by_file[file_path].append({
                "type": "Verified AI Finding",
                "rule": candidate.get("bug_type") or "Logic Defect",
                "severity": candidate.get("severity") or "MEDIUM",
                "message": hyp.get("hypothesis"),
                "line": candidate.get("line_start"),
                "confidence": hyp.get("confidence")
            })

        # Build Markdown content
        lines = [
            f"# GlitchHunter Scan Report: {self.project_name}",
            f"\n- **Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Repository**: `{self.repo_path}`",
            f"- **System State**: `{state.get('current_state', 'unknown')}`",
            "\n## Executive Summary",
        ]

        summary = state.get("metadata", {}).get("summary", {})
        total_findings = sum(len(f) for f in findings_by_file.values())
        
        # Severity counts
        sev_counts: Dict[str, int] = {"CRITICAL": 0, "ERROR": 0, "WARNING": 0, "INFO": 0}
        for file_findings in findings_by_file.values():
            for f in file_findings:
                sev = str(f.get("severity", "INFO")).upper()
                if sev in sev_counts:
                    sev_counts[sev] += 1
                else:
                    sev_counts["INFO"] += 1

        lines.append("\n| Metric | Value |")
        lines.append("| :--- | :--- |")
        lines.append(f"| Total Findings | {total_findings} |")
        lines.append(f"| Files with Issues | {len(findings_by_file)} |")
        lines.append(f"| Critical / Errors | {sev_counts['CRITICAL'] + sev_counts['ERROR']} |")
        lines.append(f"| Verified Patches | {len(state.get('verified_patches', []))} |")
        
        lines.append("\n## Detailed Findings by File")
        
        if not findings_by_file:
            lines.append("\n> [!TIP]\n> No critical software defects or security issues were identified in the primary analysis.")
        else:
            for file_path, items in sorted(findings_by_file.items()):
                # Try to make path relative to repo_root
                try:
                    p = Path(file_path)
                    if p.is_absolute():
                        rel_path = p.relative_to(self.repo_path)
                    else:
                        rel_path = file_path
                except ValueError:
                    rel_path = file_path
                
                lines.append(f"\n### 📄 {rel_path}")
                for item in items:
                    sev = str(item.get("severity", "")).upper()
                    icon = "🔴" if sev in ("ERROR", "CRITICAL") else "🟡" if sev == "WARNING" else "🔵"
                    
                    lines.append(f"- {icon} **{item.get('rule', 'Defect')}**")
                    lines.append(f"  - **Type**: {item.get('type')}")
                    lines.append(f"  - **Severity**: {sev}")
                    lines.append(f"  - **Line**: {item.get('line') or 'N/A'}")
                    lines.append(f"  - **Description**: {item.get('message')}")

        lines.append("\n---")
        lines.append("## Analyzed Content")
        lines.append("The following directories and files were included in the current scan scope:")
        lines.append(f"- Input path: `{self.repo_path}`")
        
        lines.append("\n\n*Report generated by GlitchHunter TurboQuant*")

        with open(report_file, "w") as f:
            f.write("\n".join(lines))
        
        logger.info(f"Markdown report generated: {report_file}")
        return report_file

    def generate_json(self, state: Dict[str, Any]) -> Path:
        """
        Generate a machine-readable JSON report in the scans directory.

        Args:
            state: Full state from the state machine

        Returns:
            Path to the generated file
        """
        report_file = self.scans_dir / f"{self.project_name}_scan_{self.timestamp}.json"

        # Filter candidates: nur echte Source-Code-Dateien, keine docs/, tests/, etc.
        real_candidates = [
            c for c in state.get("candidates", [])
            if c.get("bug_type") and c.get("bug_type") != "None"
            and not self._should_exclude_file(c.get("file_path", ""))
        ]
        
        # Filter hypotheses: nur echte Source-Code-Dateien
        verified_hypotheses = [
            h for h in state.get("hypotheses", [])
            if h.get("verified")
            and not self._should_exclude_file(h.get("candidate", {}).get("file_path", ""))
        ]

        report_data = {
            "project_name": self.project_name,
            "repo_path": str(self.repo_path),
            "timestamp": self.timestamp,
            "summary": state.get("metadata", {}).get("summary", {}),
            "findings_count": len(real_candidates) + len(verified_hypotheses),
            "candidates": real_candidates,
            "verified_hypotheses": verified_hypotheses,
            "verified_patches_count": len(state.get("verified_patches", [])),
            "errors": state.get("errors", []),
            "metadata": state.get("metadata", {})
        }

        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"JSON report generated: {report_file}")
        return report_file
