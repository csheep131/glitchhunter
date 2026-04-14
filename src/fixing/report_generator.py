"""
Report Generator für GlitchHunter.

Erstellt JSON + Markdown Reports für:
- Bug-Zusammenfassungen
- Fix-Details
- Test-Ergebnisse
- Eskalations-Reports
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BugSummary:
    """
    Bug-Zusammenfassung.

    Attributes:
        bug_id: Eindeutige Bug-ID
        bug_type: Typ des Bugs
        description: Beschreibung
        severity: Schweregrad
        file_path: Dateipfad
        line_number: Zeilennummer
        status: Status (fixed, escalated, pending)
        confidence: Konfidenz
    """

    bug_id: str
    bug_type: str
    description: str
    severity: str
    file_path: str
    line_number: int
    status: str = "pending"
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "bug_id": self.bug_id,
            "bug_type": self.bug_type,
            "description": self.description,
            "severity": self.severity,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "status": self.status,
            "confidence": self.confidence,
        }


@dataclass
class FixDetail:
    """
    Fix-Details.

    Attributes:
        bug_id: Zugehörige Bug-ID
        patch_diff: Patch-Diff
        explanation: Erklärung
        files_changed: Geänderte Dateien
        lines_changed: Geänderte Zeilen
        test_results: Test-Ergebnisse
        verification_confidence: Verifier-Konfidenz
    """

    bug_id: str
    patch_diff: str
    explanation: str
    files_changed: List[str] = field(default_factory=list)
    lines_changed: int = 0
    test_results: List[Dict[str, Any]] = field(default_factory=list)
    verification_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "bug_id": self.bug_id,
            "patch_diff": self.patch_diff,
            "explanation": self.explanation,
            "files_changed": self.files_changed,
            "lines_changed": self.lines_changed,
            "test_results": self.test_results,
            "verification_confidence": self.verification_confidence,
        }


@dataclass
class ReportBundle:
    """
    Report-Bündel.

    Attributes:
        json_report: JSON-Report
        markdown_report: Markdown-Report
        generated_at: Generierungs-Zeitpunkt
        total_bugs: Gesamtanzahl Bugs
        fixed_bugs: Fixierte Bugs
        escalated_bugs: Eskalierte Bugs
    """

    json_report: Dict[str, Any] = field(default_factory=dict)
    markdown_report: str = ""
    generated_at: datetime = field(default_factory=datetime.now)
    total_bugs: int = 0
    fixed_bugs: int = 0
    escalated_bugs: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "json_report": self.json_report,
            "markdown_report": self.markdown_report,
            "generated_at": self.generated_at.isoformat(),
            "total_bugs": self.total_bugs,
            "fixed_bugs": self.fixed_bugs,
            "escalated_bugs": self.escalated_bugs,
        }


class ReportGenerator:
    """
    Generiert Reports für GlitchHunter.

    Erstellt:
    - JSON-Reports (maschinenlesbar)
    - Markdown-Reports (menschenlesbar)
    - Eskalations-Reports

    Usage:
        generator = ReportGenerator(output_dir="reports")
        bundle = generator.generate_report(bugs, fixes)
    """

    def __init__(
        self,
        output_dir: str = "reports",
    ) -> None:
        """
        Initialisiert Report Generator.

        Args:
            output_dir: Ausgabe-Verzeichnis.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"ReportGenerator initialisiert: output_dir={self.output_dir}")

    def generate_report(
        self,
        bugs: List[BugSummary],
        fixes: List[FixDetail],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ReportBundle:
        """
        Generiert kompletten Report.

        Args:
            bugs: Liste von Bugs.
            fixes: Liste von Fixes.
            metadata: Zusätzliche Metadaten.

        Returns:
            ReportBundle.
        """
        logger.info(f"Generiere Report für {len(bugs)} Bugs, {len(fixes)} Fixes")

        bundle = ReportBundle()

        # JSON-Report generieren
        bundle.json_report = self._generate_json_report(bugs, fixes, metadata)

        # Markdown-Report generieren
        bundle.markdown_report = self._generate_markdown_report(bugs, fixes, metadata)

        # Statistik
        bundle.total_bugs = len(bugs)
        bundle.fixed_bugs = len(fixes)
        bundle.escalated_bugs = len([b for b in bugs if b.status == "escalated"])
        bundle.generated_at = datetime.now()

        # Reports speichern
        self._save_reports(bundle)

        logger.info(
            f"Report generiert: {bundle.total_bugs} Bugs, "
            f"{bundle.fixed_bugs} gefixt, "
            f"{bundle.escalated_bugs} eskaliert"
        )

        return bundle

    def _generate_json_report(
        self,
        bugs: List[BugSummary],
        fixes: List[FixDetail],
        metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generiert JSON-Report.

        Args:
            bugs: Liste von Bugs.
            fixes: Liste von Fixes.
            metadata: Zusätzliche Metadaten.

        Returns:
            JSON-Report.
        """
        # Fix-Map erstellen
        fix_map = {f.bug_id: f.to_dict() for f in fixes}

        # Bugs mit Fixes anreichern
        enriched_bugs = []
        for bug in bugs:
            bug_dict = bug.to_dict()
            if bug.bug_id in fix_map:
                bug_dict["fix"] = fix_map[bug.bug_id]
                bug_dict["status"] = "fixed"
            enriched_bugs.append(bug_dict)

        report = {
            "report_type": "glitchhunter_analysis",
            "version": "2.0",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_bugs": len(bugs),
                "fixed_bugs": len(fixes),
                "escalated_bugs": len([b for b in bugs if b.status == "escalated"]),
                "pending_bugs": len([b for b in bugs if b.status == "pending"]),
            },
            "bugs": enriched_bugs,
            "fixes": [f.to_dict() for f in fixes],
            "metadata": metadata or {},
        }

        return report

    def _generate_markdown_report(
        self,
        bugs: List[BugSummary],
        fixes: List[FixDetail],
        metadata: Optional[Dict[str, Any]],
    ) -> str:
        """
        Generiert Markdown-Report.

        Args:
            bugs: Liste von Bugs.
            fixes: Liste von Fixes.
            metadata: Zusätzliche Metadaten.

        Returns:
            Markdown-Report.
        """
        lines = []

        # Header
        lines.extend([
            "# GlitchHunter Analysis Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Version:** 2.0",
            "",
        ])

        # Summary
        fixed_count = len(fixes)
        escalated_count = len([b for b in bugs if b.status == "escalated"])
        pending_count = len([b for b in bugs if b.status == "pending"])

        lines.extend([
            "## Summary",
            "",
            "| Metric | Count |",
            "|--------|-------|",
            f"| Total Bugs | {len(bugs)} |",
            f"| Fixed | {fixed_count} |",
            f"| Escalated | {escalated_count} |",
            f"| Pending | {pending_count} |",
            "",
        ])

        # Fixed Bugs
        if fixes:
            lines.extend([
                "## Fixed Bugs",
                "",
            ])

            for i, fix in enumerate(fixes, 1):
                bug = next((b for b in bugs if b.bug_id == fix.bug_id), None)

                lines.extend([
                    f"### {i}. {fix.bug_id}",
                    "",
                    f"**Type:** {bug.bug_type if bug else 'unknown'}",
                    f"**Severity:** {bug.severity if bug else 'unknown'}",
                    f"**File:** `{bug.file_path}` (Line {bug.line_number})" if bug else "",
                    "",
                    "**Description:**",
                    f"> {bug.description if bug else 'N/A'}",
                    "",
                    "**Fix:**",
                    f"```diff",
                    fix.patch_diff[:500],  # Truncate für Lesbarkeit
                    "```",
                    "",
                    "**Explanation:**",
                    f"{fix.explanation}",
                    "",
                    f"**Verification Confidence:** {fix.verification_confidence:.0%}",
                    "",
                    "---",
                    "",
                ])

        # Pending Bugs
        pending_bugs = [b for b in bugs if b.status == "pending"]
        if pending_bugs:
            lines.extend([
                "## Pending Bugs",
                "",
                "These bugs are pending review or fixing:",
                "",
            ])

            for i, bug in enumerate(pending_bugs, 1):
                lines.extend([
                    f"### {i}. {bug.bug_id}",
                    "",
                    f"**Type:** {bug.bug_type}",
                    f"**Severity:** {bug.severity}",
                    f"**File:** `{bug.file_path}` (Line {bug.line_number})",
                    "",
                    "**Description:**",
                    f"> {bug.description}",
                    "",
                    f"**Confidence:** {bug.confidence:.0%}",
                    "",
                    "---",
                    "",
                ])

        # Escalated Bugs
        escalated_bugs = [b for b in bugs if b.status == "escalated"]
        if escalated_bugs:
            lines.extend([
                "## Escalated Bugs",
                "",
                "These bugs require manual review:",
                "",
            ])

            for i, bug in enumerate(escalated_bugs, 1):
                lines.extend([
                    f"### {i}. {bug.bug_id}",
                    "",
                    f"**Type:** {bug.bug_type}",
                    f"**Severity:** {bug.severity}",
                    f"**File:** `{bug.file_path}` (Line {bug.line_number})",
                    "",
                    "**Description:**",
                    f"> {bug.description}",
                    "",
                    f"**Confidence:** {bug.confidence:.0%}",
                    "",
                    "---",
                    "",
                ])

        # Metadata
        if metadata:
            lines.extend([
                "## Additional Information",
                "",
            ])
            for key, value in metadata.items():
                lines.append(f"- **{key}:** {value}")
            lines.append("")

        # Footer
        lines.extend([
            "---",
            "",
            "*Report generated by GlitchHunter v2.0*",
        ])

        return "\n".join(lines)

    def _save_reports(self, bundle: ReportBundle) -> None:
        """
        Speichert Reports.

        Args:
            bundle: ReportBundle.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON-Report speichern
        json_path = self.output_dir / f"report_{timestamp}.json"
        with open(json_path, "w") as f:
            json.dump(bundle.json_report, f, indent=2, default=str)
        logger.info(f"JSON-Report gespeichert: {json_path}")

        # Markdown-Report speichern
        md_path = self.output_dir / f"report_{timestamp}.md"
        with open(md_path, "w") as f:
            f.write(bundle.markdown_report)
        logger.info(f"Markdown-Report gespeichert: {md_path}")

    def generate_escalation_report(
        self,
        bugs: List[BugSummary],
        escalation_level: int,
        attempted_fixes: List[str],
        evidence: List[Dict[str, Any]],
        recommendation: str,
    ) -> str:
        """
        Generiert Eskalations-Report.

        Args:
            bugs: Eskalierte Bugs.
            escalation_level: Eskalations-Level (1-4).
            attempted_fixes: Versuchte Fixes.
            evidence: Gesammelte Evidenz.
            recommendation: Empfehlung.

        Returns:
            Markdown-Eskalations-Report.
        """
        lines = []

        # Header
        level_names = {
            1: "Context Explosion",
            2: "Bug Decomposition",
            3: "Multi-Model Ensemble",
            4: "Human-in-the-Loop",
        }

        lines.extend([
            "# GlitchHunter Escalation Report",
            "",
            f"**Level:** {escalation_level} - {level_names.get(escalation_level, 'Unknown')}",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
        ])

        # Executive Summary
        lines.extend([
            "## Executive Summary",
            "",
            f"Automated fixing was escalated to **Level {escalation_level}** after unsuccessful attempts.",
            "",
            f"**Affected Bugs:** {len(bugs)}",
            "",
        ])

        # Bug Details
        lines.extend([
            "## Affected Bugs",
            "",
        ])

        for i, bug in enumerate(bugs, 1):
            lines.extend([
                f"### {i}. {bug.bug_id}",
                "",
                f"- **Type:** {bug.bug_type}",
                f"- **Severity:** {bug.severity}",
                f"- **Location:** `{bug.file_path}` (Line {bug.line_number})",
                f"- **Description:** {bug.description}",
                "",
            ])

        # Attempted Fixes
        lines.extend([
            "## Attempted Fixes",
            "",
        ])

        for i, fix in enumerate(attempted_fixes, 1):
            lines.append(f"{i}. {fix}")
        lines.append("")

        # Evidence
        if evidence:
            lines.extend([
                "## Evidence",
                "",
            ])

            for i, ev in enumerate(evidence, 1):
                lines.extend([
                    f"### Evidence {i}",
                    "",
                    f"- **Type:** {ev.get('type', 'unknown')}",
                    f"- **Content:** {ev.get('content', 'N/A')}",
                    "",
                ])

        # Recommendation
        lines.extend([
            "## Recommendation",
            "",
            f"{recommendation}",
            "",
        ])

        # Next Steps
        if escalation_level < 4:
            lines.extend([
                "## Next Steps",
                "",
                f"The system will proceed to **Level {escalation_level + 1}** if this escalation is not resolved.",
                "",
            ])
        else:
            lines.extend([
                "## Next Steps",
                "",
                "**Manual review required.** Please review the evidence and attempted fixes above.",
                "",
            ])

        # Footer
        lines.extend([
            "---",
            "",
            "*Generated by GlitchHunter Escalation Manager*",
        ])

        return "\n".join(lines)

    def generate_summary_report(
        self,
        total_bugs: int,
        fixed_bugs: int,
        escalated_bugs: int,
        rules_learned: int,
        total_time_seconds: float,
    ) -> str:
        """
        Generiert Zusammenfassungs-Report.

        Args:
            total_bugs: Gesamtanzahl Bugs.
            fixed_bugs: Fixierte Bugs.
            escalated_bugs: Eskalierte Bugs.
            rules_learned: Gelernte Regeln.
            total_time_seconds: Gesamtzeit.

        Returns:
            Markdown-Zusammenfassung.
        """
        success_rate = (fixed_bugs / total_bugs * 100) if total_bugs > 0 else 0

        lines = [
            "# GlitchHunter Session Summary",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Key Metrics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Bugs | {total_bugs} |",
            f"| Fixed | {fixed_bugs} |",
            f"| Escalated | {escalated_bugs} |",
            f"| Success Rate | {success_rate:.1f}% |",
            f"| Rules Learned | {rules_learned} |",
            f"| Total Time | {total_time_seconds:.1f}s |",
            "",
        ]

        if success_rate >= 80:
            lines.append("**Excellent!** High success rate achieved.")
        elif success_rate >= 50:
            lines.append("**Good.** Moderate success rate with room for improvement.")
        else:
            lines.append("**Needs Attention.** Low success rate - consider reviewing escalation cases.")

        lines.extend([
            "",
            "---",
            "",
            "*Generated by GlitchHunter v2.0*",
        ])

        return "\n".join(lines)

    def __call__(self, state: Any) -> Dict[str, Any]:
        """
        Callable für LangGraph.

        Args:
            state: AgentState.

        Returns:
            State-Updates.
        """
        bugs = getattr(state, "bugs", [])
        fixes = getattr(state, "fixes", [])
        metadata = getattr(state, "metadata", {})

        bundle = self.generate_report(bugs, fixes, metadata)

        return {
            "report_bundle": bundle.to_dict(),
            "metadata": {
                "report_generated": True,
                "total_bugs": bundle.total_bugs,
                "fixed_bugs": bundle.fixed_bugs,
                "escalated_bugs": bundle.escalated_bugs,
            },
        }
