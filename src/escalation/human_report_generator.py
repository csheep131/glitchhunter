"""
Human Report Generator für GlitchHunter Escalation Level 4.

Generiert detaillierte Reports für menschliche Review.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class HumanReport:
    """
    Menschlicher Report.

    Attributes:
        title: Titel
        summary: Zusammenfassung
        bug_description: Bug-Beschreibung
        attempted_fixes: Versuchte Fixes
        evidence: Evidenz
        recommendation: Empfehlung
        created_at: Erstelldatum
        severity: Schweregrad
        files_affected: Betroffene Dateien
    """

    title: str
    summary: str
    bug_description: str
    attempted_fixes: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    recommendation: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    severity: str = "medium"
    files_affected: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "title": self.title,
            "summary": self.summary,
            "bug_description": self.bug_description,
            "attempted_fixes": self.attempted_fixes,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "created_at": self.created_at.isoformat(),
            "severity": self.severity,
            "files_affected": self.files_affected,
            "metadata": self.metadata,
        }


class HumanReportGenerator:
    """
    Generiert Reports für menschliche Review.

    Features:
    - Detaillierte Bug-Beschreibung
    - Liste versuchter Fixes
    - Evidenz-Zusammenstellung
    - Handlungsempfehlungen
    - Draft-PR Erstellung

    Usage:
        generator = HumanReportGenerator()
        report = generator.generate(bug, attempts, evidence)
    """

    def __init__(
        self,
        output_dir: str = "reports/escalation",
    ) -> None:
        """
        Initialisiert Human Report Generator.

        Args:
            output_dir: Ausgabe-Verzeichnis.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"HumanReportGenerator initialisiert: {self.output_dir}")

    def generate(
        self,
        bug: Dict[str, Any],
        attempted_fixes: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        escalation_level: int = 4,
    ) -> HumanReport:
        """
        Generiert Human Report.

        Args:
            bug: Bug-Information.
            attempted_fixes: Versuchte Fixes.
            evidence: Evidenz.
            escalation_level: Eskalations-Level.

        Returns:
            HumanReport.
        """
        logger.info(f"Generiere Human Report für {bug.get('bug_id', 'unknown')}")

        report = HumanReport(
            title=self._generate_title(bug, escalation_level),
            summary=self._generate_summary(bug, attempted_fixes),
            bug_description=self._generate_bug_description(bug),
            attempted_fixes=self._format_attempted_fixes(attempted_fixes),
            evidence=evidence,
            recommendation=self._generate_recommendation(bug, escalation_level),
            severity=bug.get("severity", "medium"),
            files_affected=[bug.get("file_path", "")],
            metadata={
                "escalation_level": escalation_level,
                "bug_id": bug.get("bug_id", ""),
            },
        )

        # Report speichern
        self._save_report(report)

        logger.info(f"Human Report generiert: {report.title}")

        return report

    def generate_draft_pr(
        self,
        bug: Dict[str, Any],
        fix_suggestions: List[str],
    ) -> Dict[str, Any]:
        """
        Generiert Draft-PR Information.

        Args:
            bug: Bug.
            fix_suggestions: Fix-Vorschläge.

        Returns:
            PR-Information.
        """
        return {
            "title": f"Fix: {bug.get('bug_type', 'unknown')} in {bug.get('file_path', '')}",
            "body": self._generate_pr_body(bug, fix_suggestions),
            "labels": ["bug", "automated-fix", "needs-review"],
            "draft": True,
        }

    def _generate_title(self, bug: Dict[str, Any], escalation_level: int) -> str:
        """Generiert Titel."""
        bug_id = bug.get("bug_id", "unknown")
        bug_type = bug.get("bug_type", "unknown")

        level_names = {
            1: "Context Explosion",
            2: "Bug Decomposition",
            3: "Multi-Model Ensemble",
            4: "Human Review Required",
        }

        return f"[Escalation L{escalation_level}] {bug_type} - {bug_id} - {level_names.get(escalation_level, '')}"

    def _generate_summary(self, bug: Dict[str, Any], attempted_fixes: List[Dict[str, Any]]) -> str:
        """Generiert Zusammenfassung."""
        bug_type = bug.get("bug_type", "unknown")
        file_path = bug.get("file_path", "")
        fix_count = len(attempted_fixes)

        return (
            f"Automated fixing for **{bug_type}** in `{file_path}` was escalated "
            f"after **{fix_count}** unsuccessful fix attempts. "
            f"Manual review and intervention is required."
        )

    def _generate_bug_description(self, bug: Dict[str, Any]) -> str:
        """Generiert Bug-Beschreibung."""
        lines = [
            f"**Type:** {bug.get('bug_type', 'unknown')}",
            f"**Severity:** {bug.get('severity', 'medium')}",
            f"**Location:** `{bug.get('file_path', '')}` (Line {bug.get('line_number', 'N/A')})",
            "",
            "**Description:**",
            f"> {bug.get('description', 'No description available.')}",
            "",
            "**Context:**",
            f"- Confidence: {bug.get('confidence', 0):.0%}",
            f"- First detected: {bug.get('detected_at', 'N/A')}",
        ]

        return "\n".join(lines)

    def _format_attempted_fixes(self, attempted_fixes: List[Dict[str, Any]]) -> List[str]:
        """Formatiert versuchte Fixes."""
        formatted = []

        for i, fix in enumerate(attempted_fixes, 1):
            fix_desc = fix.get("description", "Fix attempt")
            fix_result = fix.get("result", "failed")
            fix_reason = fix.get("reason", "Unknown reason")

            formatted.append(
                f"**Attempt {i}:** {fix_desc}\n\n"
                f"- Result: {fix_result}\n"
                f"- Reason: {fix_reason}"
            )

        return formatted

    def _generate_recommendation(self, bug: Dict[str, Any], escalation_level: int) -> str:
        """Generiert Empfehlung."""
        bug_type = bug.get("bug_type", "unknown")
        severity = bug.get("severity", "medium")

        if escalation_level == 4:
            return (
                f"**Immediate action required:**\n\n"
                f"1. Review the evidence and attempted fixes above\n"
                f"2. Manually analyze `{bug.get('file_path', '')}` for {bug_type}\n"
                f"3. Create a fix considering the failed attempts\n"
                f"4. Add regression tests to prevent future issues\n\n"
                f"**Priority:** {'High' if severity in ['high', 'critical'] else 'Medium'}"
            )
        else:
            return (
                f"The system will proceed to **Level {escalation_level + 1}** if this "
                f"escalation is not resolved within the configured timeframe."
            )

    def _generate_pr_body(
        self,
        bug: Dict[str, Any],
        fix_suggestions: List[str],
    ) -> str:
        """Generiert PR-Beschreibung."""
        lines = [
            "## Automated Fix Suggestion",
            "",
            f"This PR attempts to fix: **{bug.get('bug_type', 'unknown')}**",
            "",
            "### Bug Description",
            "",
            bug.get("description", "No description available."),
            "",
            "### Fix Suggestions",
            "",
        ]

        for i, suggestion in enumerate(fix_suggestions, 1):
            lines.append(f"{i}. {suggestion}")

        lines.extend([
            "",
            "### Notes",
            "",
            "- [ ] Review the fix carefully",
            "- [ ] Add regression tests",
            "- [ ] Verify no breaking changes",
            "",
            "---",
            "",
            "*Generated by GlitchHunter Escalation Manager*",
        ])

        return "\n".join(lines)

    def _save_report(self, report: HumanReport) -> Path:
        """
        Speichert Report.

        Args:
            report: Report.

        Returns:
            Pfad zur gespeicherten Datei.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bug_id = report.metadata.get("bug_id", "unknown").replace("/", "_")

        # Markdown-Report
        md_path = self.output_dir / f"escalation_{bug_id}_{timestamp}.md"

        with open(md_path, "w") as f:
            f.write(self._report_to_markdown(report))

        logger.info(f"Report gespeichert: {md_path}")
        return md_path

    def _report_to_markdown(self, report: HumanReport) -> str:
        """Konvertiert Report zu Markdown."""
        lines = [
            f"# {report.title}",
            "",
            f"**Generated:** {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Severity:** {report.severity}",
            "",
            "---",
            "",
            "## Summary",
            "",
            report.summary,
            "",
            "## Bug Description",
            "",
            report.bug_description,
            "",
            "## Attempted Fixes",
            "",
        ]

        for fix in report.attempted_fixes:
            lines.extend([fix, "", "---", ""])

        lines.extend([
            "## Evidence",
            "",
        ])

        for i, ev in enumerate(report.evidence, 1):
            lines.extend([
                f"### Evidence {i}",
                "",
                f"- **Type:** {ev.get('type', 'unknown')}",
                f"- **Content:** {ev.get('content', 'N/A')}",
                "",
            ])

        lines.extend([
            "## Recommendation",
            "",
            report.recommendation,
            "",
            "---",
            "",
            "*Generated by GlitchHunter Human Report Generator*",
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
        bug = getattr(state, "current_bug", {})
        attempted_fixes = getattr(state, "attempted_fixes", [])
        evidence = getattr(state, "evidence", [])
        escalation_level = getattr(state, "escalation_level", 4)

        report = self.generate(bug, attempted_fixes, evidence, escalation_level)

        return {
            "human_report": report.to_dict(),
            "report_path": str(self.output_dir),
            "metadata": {
                "human_report_generated": True,
                "escalation_level": escalation_level,
                "requires_manual_review": True,
            },
        }
