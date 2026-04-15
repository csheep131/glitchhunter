"""
Problem Report Generator - Erzeugt Reports für ProblemCases.

Gemäß PROBLEM_SOLVER.md Phase 1.5:
- problem_case.json (vollständige Daten)
- diagnosis_stub.md (erste Diagnose)
- constraints.md (Einschränkungen)

Parallele Struktur zu bestehenden Report-Generatoren.
KEINE Änderungen an bestehenden Bug-Hunting-Reports.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import ProblemCase, ProblemType, ProblemSeverity, ProblemStatus
from .classifier import ClassificationResult

logger = logging.getLogger(__name__)


class ProblemReportGenerator:
    """
    Generiert Reports für ProblemCases.
    
    Usage:
        generator = ProblemReportGenerator(output_dir=".glitchhunter/problem_reports")
        generator.generate_problem_case_report(problem)
        generator.generate_diagnosis_stub(problem, classification)
        generator.generate_constraints_report(problem)
    """
    
    def __init__(self, output_dir: str):
        """
        Initialisiert Report-Generator.
        
        Args:
            output_dir: Verzeichnis für Report-Ausgabe
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_problem_case_report(
        self,
        problem: ProblemCase,
        classification: Optional[ClassificationResult] = None,
    ) -> Path:
        """
        Generiert vollständigen Problem-Case-Report (JSON).
        
        Args:
            problem: ProblemCase mit allen Daten
            classification: Optionale Klassifikation
        
        Returns:
            Pfad zur generierten Datei
        """
        report_data = problem.to_dict()
        
        # Klassifikation hinzufügen falls vorhanden
        if classification:
            report_data["classification"] = classification.to_dict()
        
        # Report-Metadaten
        report_data["report_metadata"] = {
            "generated_at": datetime.now().isoformat(),
            "report_type": "problem_case",
            "version": "1.0",
        }
        
        # Datei-Pfad
        report_file = self.output_dir / f"{problem.id}_problem_case.json"
        
        # JSON speichern
        report_file.write_text(
            json.dumps(report_data, indent=2, ensure_ascii=False)
        )
        
        logger.info(f"Problem-Case-Report generiert: {report_file}")
        return report_file
    
    def generate_diagnosis_stub(
        self,
        problem: ProblemCase,
        classification: ClassificationResult,
    ) -> Path:
        """
        Generiert erste Diagnose als Markdown-Stub.
        
        Args:
            problem: ProblemCase
            classification: Klassifikation-Ergebnis
        
        Returns:
            Pfad zur generierten Datei
        """
        lines = [
            f"# 🔍 Diagnose: {problem.title}",
            "",
            f"**Problem-ID:** {problem.id}",
            f"**Generiert:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Zusammenfassung",
            "",
            f"**Problemtyp:** {classification.problem_type.value}",
            f"**Confidence:** {classification.confidence:.0%}",
            f"**Schweregrad:** {problem.severity.value}",
            f"**Status:** {problem.status.value}",
            "",
            "## Erkannte Indikatoren",
            "",
        ]
        
        # Keywords
        if classification.keywords_found:
            lines.append("### Gefundene Keywords")
            lines.append("")
            for kw in classification.keywords_found[:15]:
                lines.append(f"- `{kw}`")
            lines.append("")
        
        # Alternative Klassifikationen
        if classification.alternatives:
            lines.append("### Alternative Einstufungen")
            lines.append("")
            for alt in classification.alternatives:
                lines.append(
                    f"- {alt['problem_type']} "
                    f"(Confidence: {alt['confidence']:.0%})"
                )
            lines.append("")
        
        # Betroffene Komponenten
        if classification.affected_components:
            lines.append("### Betroffene Komponenten")
            lines.append("")
            for comp in classification.affected_components:
                lines.append(f"- {comp}")
            lines.append("")
        
        # Empfohlene Schritte
        lines.append("## Empfohlene Nächste Schritte")
        lines.append("")
        for i, action in enumerate(classification.recommended_actions, 1):
            lines.append(f"{i}. {action}")
        lines.append("")
        
        # Rohbeschreibung
        lines.append("## Ursprüngliche Beschreibung")
        lines.append("")
        lines.append(problem.raw_description)
        lines.append("")
        
        # Disclaimer
        lines.append("---")
        lines.append("")
        lines.append("*Dies ist eine automatische Erstdiagnose. ")
        lines.append("Eine detaillierte Analyse folgt in Phase 2.*")
        
        # Datei speichern
        report_file = self.output_dir / f"{problem.id}_diagnosis_stub.md"
        report_file.write_text("\n".join(lines))
        
        logger.info(f"Diagnose-Stub generiert: {report_file}")
        return report_file
    
    def generate_constraints_report(
        self,
        problem: ProblemCase,
    ) -> Path:
        """
        Generiert Constraints-Report.
        
        Args:
            problem: ProblemCase
        
        Returns:
            Pfad zur generierten Datei
        """
        lines = [
            f"# 📋 Constraints: {problem.title}",
            "",
            f"**Problem-ID:** {problem.id}",
            f"**Generiert:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
        ]
        
        # Explizite Constraints
        if problem.constraints:
            lines.append("## Explizite Einschränkungen")
            lines.append("")
            for i, constraint in enumerate(problem.constraints, 1):
                lines.append(f"{i}. {constraint}")
            lines.append("")
        else:
            lines.append("## Explizite Einschränkungen")
            lines.append("")
            lines.append("*Keine expliziten Constraints angegeben.*")
            lines.append("")
        
        # Implizite Constraints (aus Problemtyp abgeleitet)
        lines.append("## Implizite Einschränkungen")
        lines.append("")
        
        implicit_constraints = self._derive_implicit_constraints(problem)
        for i, constraint in enumerate(implicit_constraints, 1):
            lines.append(f"{i}. {constraint}")
        lines.append("")
        
        # Zielzustand
        if problem.goal_state:
            lines.append("## Zielzustand")
            lines.append("")
            lines.append(problem.goal_state)
            lines.append("")
        
        # Erfolgskriterien
        if problem.success_criteria:
            lines.append("## Erfolgskriterien")
            lines.append("")
            for i, criteria in enumerate(problem.success_criteria, 1):
                lines.append(f"{i}. {criteria}")
            lines.append("")
        
        # Risikofaktoren
        if problem.risk_factors:
            lines.append("## Risikofaktoren")
            lines.append("")
            for i, risk in enumerate(problem.risk_factors, 1):
                lines.append(f"{i}. {risk}")
            lines.append("")
        
        # Stack-Information
        lines.append("## Stack-Zuordnung")
        lines.append("")
        lines.append(f"**Ziel-Stack:** {problem.target_stack}")
        
        if problem.stack_capabilities:
            lines.append("")
            lines.append("### Stack-spezifische Fähigkeiten")
            for key, value in problem.stack_capabilities.items():
                lines.append(f"- {key}: {value}")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*Constraints können sich während der Diagnose präzisieren.*")
        
        # Datei speichern
        report_file = self.output_dir / f"{problem.id}_constraints.md"
        report_file.write_text("\n".join(lines))
        
        logger.info(f"Constraints-Report generiert: {report_file}")
        return report_file
    
    def _derive_implicit_constraints(self, problem: ProblemCase) -> List[str]:
        """
        Leitet implizite Constraints aus Problemtyp ab.
        
        Args:
            problem: ProblemCase
        
        Returns:
            Liste von impliziten Constraints
        """
        constraints = []
        
        if problem.problem_type == ProblemType.PERFORMANCE:
            constraints.append("Lösung darf keine signifikante zusätzliche Latenz verursachen")
            constraints.append("Speicherverbrauch sollte nicht exponentiell wachsen")
        
        elif problem.problem_type == ProblemType.RELIABILITY:
            constraints.append("Lösung muss unter allen Betriebsbedingungen stabil sein")
            constraints.append("Fehlertoleranz muss gewährleistet sein")
        
        elif problem.problem_type == ProblemType.MISSING_FEATURE:
            constraints.append("Feature muss konsistent mit existierender Architektur sein")
            constraints.append("Dokumentation muss mitgeliefert werden")
        
        elif problem.problem_type == ProblemType.WORKFLOW_GAP:
            constraints.append("Automatisierung muss manuelle Schritte vollständig ersetzen")
            constraints.append("Ausnahmen müssen erkennbar und eskalierbar sein")
        
        elif problem.problem_type == ProblemType.UX_ISSUE:
            constraints.append("Lösung muss intuitiv bedienbar bleiben")
            constraints.append("Bestehende Workflows dürfen nicht gebrochen werden")
        
        elif problem.problem_type == ProblemType.BUG:
            constraints.append("Fix darf keine Regressionen verursachen")
            constraints.append("Bestehende Tests müssen weiterhin bestehen")
        
        # Immer hinzufügen
        constraints.append("Lösung muss im gewählten Stack umsetzbar sein")
        
        return constraints
    
    def generate_all_reports(
        self,
        problem: ProblemCase,
        classification: Optional[ClassificationResult] = None,
    ) -> Dict[str, Path]:
        """
        Generiert alle Reports für ein Problem.
        
        Args:
            problem: ProblemCase
            classification: Optionale Klassifikation
        
        Returns:
            Dict mit Report-Typen und Dateipfaden
        """
        reports = {}
        
        # Problem-Case-Report (immer)
        reports["problem_case"] = self.generate_problem_case_report(
            problem, classification
        )
        
        # Diagnosis-Stub (nur mit Klassifikation)
        if classification:
            reports["diagnosis_stub"] = self.generate_diagnosis_stub(
                problem, classification
            )
        
        # Constraints-Report (immer)
        reports["constraints"] = self.generate_constraints_report(problem)
        
        logger.info(
            f"Alle Reports generiert: {', '.join(reports.keys())}"
        )
        
        return reports
