"""
CLI Commands für Problem-Solver.

Neue Commands parallel zu bestehenden Bug-Hunting-Commands:
- glitchhunter problem intake
- glitchhunter problem list
- glitchhunter problem show
- glitchhunter problem classify
- glitchhunter problem delete
- glitchhunter problem stats
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .manager import ProblemManager
from .models import ProblemStatus, ProblemType


def cmd_problem_intake(args: argparse.Namespace) -> int:
    """
    `glitchhunter problem intake` - Neues Problem aufnehmen.
    
    Usage:
        glitchhunter problem intake "Das Startup ist zu langsam"
        glitchhunter problem intake -f problem_description.txt
    """
    from core.config import Config
    
    config = Config.load(args.config if hasattr(args, 'config') else None)
    repo_path = Path(config.repository.path)
    manager = ProblemManager(repo_path=repo_path)
    
    # Beschreibung holen (entweder aus Argument oder Datei)
    if args.file:
        try:
            description = Path(args.file).read_text()
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            return 1
    else:
        description = args.description
    
    if not description or not description.strip():
        print("Error: Empty problem description", file=sys.stderr)
        return 1
    
    # Problem aufnehmen
    problem = manager.intake_problem(
        description=description,
        title=args.title,
        source="cli",
    )
    
    # Ausgabe
    print(f"\n✅ Problem created:")
    print(f"   ID: {problem.id}")
    print(f"   Title: {problem.title}")
    print(f"   Type: {problem.problem_type.value}")
    print(f"   Status: {problem.status.value}")
    print(f"\nTo classify this problem, run:")
    print(f"   glitchhunter problem classify {problem.id}")
    
    return 0


def cmd_problem_list(args: argparse.Namespace) -> int:
    """
    `glitchhunter problem list` - Alle Probleme auflisten.
    """
    from core.config import Config
    
    config = Config.load(args.config if hasattr(args, 'config') else None)
    repo_path = Path(config.repository.path)
    manager = ProblemManager(repo_path=repo_path)
    
    # Filter
    status_filter = None
    type_filter = None
    
    if args.status:
        try:
            status_filter = ProblemStatus(args.status)
        except ValueError:
            print(f"Invalid status: {args.status}", file=sys.stderr)
            return 1
    
    if args.type:
        try:
            type_filter = ProblemType(args.type)
        except ValueError:
            print(f"Invalid type: {args.type}", file=sys.stderr)
            return 1
    
    # Probleme laden
    problems = manager.list_problems(
        status_filter=status_filter,
        type_filter=type_filter,
    )
    
    if not problems:
        print("No problems found")
        return 0
    
    # Ausgabe
    print(f"\n{'ID':<25} {'Title':<40} {'Type':<15} {'Status':<12}")
    print("-" * 95)
    
    for problem in problems:
        title = problem.title[:38] + ".." if len(problem.title) > 40 else problem.title
        print(
            f"{problem.id:<25} {title:<40} "
            f"{problem.problem_type.value:<15} {problem.status.value:<12}"
        )
    
    print(f"\nTotal: {len(problems)} problem(s)")
    return 0


def cmd_problem_show(args: argparse.Namespace) -> int:
    """
    `glitchhunter problem show` - Problem-Details anzeigen.
    """
    from core.config import Config
    
    config = Config.load(args.config if hasattr(args, 'config') else None)
    repo_path = Path(config.repository.path)
    manager = ProblemManager(repo_path=repo_path)
    
    problem = manager.get_problem(args.problem_id)
    if not problem:
        print(f"Problem {args.problem_id} not found", file=sys.stderr)
        return 1
    
    # Ausgabe
    print(f"\n{'='*60}")
    print(f"Problem: {problem.title}")
    print(f"{'='*60}")
    print(f"ID:        {problem.id}")
    print(f"Type:      {problem.problem_type.value}")
    print(f"Severity:  {problem.severity.value}")
    print(f"Status:    {problem.status.value}")
    print(f"Created:   {problem.created_at}")
    print(f"Updated:   {problem.updated_at}")
    print(f"\nDescription:")
    print(f"  {problem.raw_description}")
    
    if problem.goal_state:
        print(f"\nGoal State:")
        print(f"  {problem.goal_state}")
    
    if problem.affected_components:
        print(f"\nAffected Components:")
        for comp in problem.affected_components:
            print(f"  - {comp}")
    
    if problem.success_criteria:
        print(f"\nSuccess Criteria:")
        for criteria in problem.success_criteria:
            print(f"  - {criteria}")
    
    if problem.constraints:
        print(f"\nConstraints:")
        for constraint in problem.constraints:
            print(f"  - {constraint}")
    
    print(f"\n{'='*60}")
    return 0


def cmd_problem_classify(args: argparse.Namespace) -> int:
    """
    `glitchhunter problem classify` - Problem klassifizieren.
    """
    from core.config import Config
    
    config = Config.load(args.config if hasattr(args, 'config') else None)
    repo_path = Path(config.repository.path)
    manager = ProblemManager(repo_path=repo_path)
    
    # Klassifikation durchführen
    try:
        result = manager.classify_problem(args.problem_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    # Ausgabe
    print(f"\n✅ Classification complete for {args.problem_id}")
    print(f"\nProblem Type: {result.problem_type.value}")
    print(f"Confidence:   {result.confidence:.2%}")
    
    if result.keywords_found:
        print(f"\nKeywords found ({len(result.keywords_found)}):")
        for kw in result.keywords_found[:10]:
            print(f"  - {kw}")
    
    if result.alternatives:
        print(f"\nAlternative classifications:")
        for alt in result.alternatives:
            print(
                f"  - {alt['problem_type']} "
                f"(confidence: {alt['confidence']:.2%})"
            )
    
    if result.affected_components:
        print(f"\nAffected components:")
        for comp in result.affected_components:
            print(f"  - {comp}")
    
    print(f"\nRecommended actions:")
    for action in result.recommended_actions:
        print(f"  - {action}")
    
    return 0


def cmd_problem_delete(args: argparse.Namespace) -> int:
    """
    `glitchhunter problem delete` - Problem löschen.
    """
    from core.config import Config
    
    config = Config.load(args.config if hasattr(args, 'config') else None)
    repo_path = Path(config.repository.path)
    manager = ProblemManager(repo_path=repo_path)
    
    # Bestätigung einholen falls nicht erzwungen
    if not args.force:
        confirm = input(f"Delete problem {args.problem_id}? [y/N] ")
        if confirm.lower() != 'y':
            print("Delete cancelled")
            return 0
    
    # Löschen
    if manager.delete_problem(args.problem_id):
        print(f"✅ Problem {args.problem_id} deleted")
        return 0
    else:
        print(f"Problem {args.problem_id} not found", file=sys.stderr)
        return 1


def cmd_problem_stats(args: argparse.Namespace) -> int:
    """
    `glitchhunter problem stats` - Statistik anzeigen.
    """
    from core.config import Config

    config = Config.load(args.config if hasattr(args, 'config') else None)
    repo_path = Path(config.repository.path)
    manager = ProblemManager(repo_path=repo_path)

    stats = manager.get_statistics()

    print(f"\n📊 Problem Statistics")
    print(f"{'='*40}")
    print(f"Total Problems: {stats['total_problems']}")

    if stats['by_type']:
        print(f"\nBy Type:")
        for type_name, count in sorted(stats['by_type'].items()):
            print(f"  {type_name}: {count}")

    if stats['by_status']:
        print(f"\nBy Status:")
        for status_name, count in sorted(stats['by_status'].items()):
            print(f"  {status_name}: {count}")

    if stats['oldest_problem']:
        print(f"\nOldest Problem: {stats['oldest_problem']}")
    if stats['newest_problem']:
        print(f"Newest Problem: {stats['newest_problem']}")

    return 0


def cmd_problem_report(args: argparse.Namespace) -> int:
    """
    `glitchhunter problem report` - Reports generieren.
    """
    from core.config import Config

    config = Config.load(args.config if hasattr(args, 'config') else None)
    repo_path = Path(config.repository.path)
    manager = ProblemManager(repo_path=repo_path)

    # Problem laden
    problem = manager.get_problem(args.problem_id)
    if not problem:
        print(f"Problem {args.problem_id} not found", file=sys.stderr)
        return 1

    # Optional klassifizieren
    classification = None
    if args.classify:
        try:
            classification = manager.classify_problem(args.problem_id)
        except ValueError as e:
            print(f"Classification failed: {e}", file=sys.stderr)

    # Reports generieren
    output_dir = Path(args.output_dir) if args.output_dir else (
        repo_path / ".glitchhunter" / "problem_reports"
    )

    generator = ProblemReportGenerator(output_dir=str(output_dir))
    reports = generator.generate_all_reports(problem, classification)

    print(f"\n✅ Reports generiert:")
    for report_type, path in reports.items():
        print(f"   {report_type}: {path}")

    return 0


def cmd_problem_diagnose(args: argparse.Namespace) -> int:
    """
    `glitchhunter problem diagnose` - Diagnose generieren.
    """
    from core.config import Config

    config = Config.load(args.config if hasattr(args, 'config') else None)
    repo_path = Path(config.repository.path)
    manager = ProblemManager(repo_path=repo_path)

    # Diagnose generieren
    try:
        diagnosis = manager.generate_diagnosis(args.problem_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Ausgabe
    print(f"\n✅ Diagnose generiert für {args.problem_id}")
    print(f"\n{'='*60}")
    print(f"Zusammenfassung:")
    print(f"{diagnosis.summary}")
    print(f"\n{'='*60}")

    # Root Causes
    root_causes = diagnosis.get_root_causes()
    if root_causes:
        print(f"\n🔍 Root Causes ({len(root_causes)}):")
        for cause in root_causes:
            print(f"  - {cause.description}")
            print(f"    Confidence: {cause.confidence:.0%}")
            if cause.evidence:
                print(f"    Evidence: {', '.join(cause.evidence[:2])}")

    # Blockierende Ursachen
    blocking = diagnosis.get_blocking_causes()
    if blocking:
        print(f"\n🚧 Blockierende Ursachen ({len(blocking)}):")
        for cause in blocking:
            print(f"  - {cause.description}")

    # Unsicherheiten
    high_impact = diagnosis.get_high_impact_uncertainties()
    if high_impact:
        print(f"\n❓ Offene Unsicherheiten ({len(high_impact)}):")
        for unc in high_impact:
            print(f"  - {unc.question}")

    # Nächste Schritte
    print(f"\n📋 Nächste Schritte:")
    for i, step in enumerate(diagnosis.recommended_next_steps, 1):
        print(f"  {i}. {step}")

    print(f"\n{'='*60}")
    return 0


def cmd_problem_decompose(args: argparse.Namespace) -> int:
    """
    `glitchhunter problem decompose` - Problem zerlegen.
    """
    from core.config import Config

    config = Config.load(args.config if hasattr(args, 'config') else None)
    repo_path = Path(config.repository.path)
    manager = ProblemManager(repo_path=repo_path)

    # Decomposition durchführen
    try:
        decomposition = manager.decompose_problem(args.problem_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Ausgabe
    print(f"\n✅ Problem zerlegt: {args.problem_id}")
    print(f"\n{'='*60}")
    print(f"Ansatz: {decomposition.decomposition_approach}")
    print(f"\nTeilprobleme ({len(decomposition.subproblems)}):")
    print(f"{'='*60}")

    # Nach Priorität sortiert
    sorted_subs = sorted(decomposition.subproblems, key=lambda x: x.priority)

    for i, sp in enumerate(sorted_subs, 1):
        status_icon = {
            "open": "⚪",
            "in_progress": "🔵",
            "blocked": "🔴",
            "done": "✅",
        }.get(sp.status, "⚪")

        print(f"\n{i}. {status_icon} {sp.title}")
        print(f"   Typ: {sp.subproblem_type.value}")
        print(f"   Priorität: {sp.priority}/10")
        print(f"   Aufwand: {sp.effort}")

        if sp.dependencies:
            print(f"   Dependencies: {', '.join(sp.dependencies)}")

        if sp.affected_components:
            print(f"   Komponenten: {', '.join(sp.affected_components)}")

    # Statistik
    stats = decomposition.get_statistics()
    print(f"\n{'='*60}")
    print(f"Statistik:")
    print(f"  Gesamt: {stats['total_subproblems']}")
    print(f"  Ready: {stats['ready_count']}")
    print(f"  Blocked: {stats['blocked_count']}")
    print(f"  Blocking: {stats['blocking_count']}")

    # Ausführungsreihenfolge
    print(f"\n{'='*60}")
    print(f"Ausführungsreihenfolge:")
    order = decomposition.get_execution_order()
    for i, sp in enumerate(order, 1):
        print(f"  {i}. {sp.title}")

    print(f"\n{'='*60}")
    return 0


def cmd_problem_plan(args: argparse.Namespace) -> int:
    """
    `glitchhunter problem plan` - Lösungsplan erstellen.
    """
    from core.config import load_config

    config = load_config()
    repo_path = Path(config.repository.path)
    manager = ProblemManager(repo_path=repo_path)

    # Lösungsplan erstellen
    try:
        plan = manager.create_solution_plan(
            problem_id=args.problem_id,
            use_decomposition=not args.skip_decomposition,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Ausgabe
    print(f"\n✅ Lösungsplan erstellt für {args.problem_id}")
    print(f"\n{'='*60}")
    print(f"Strategie: {plan.overall_strategy}")
    print(f"\n{'='*60}")

    # Lösungspfade pro Teilproblem
    for sp_id, paths in plan.solution_paths.items():
        print(f"\n📍 Teilproblem: {sp_id}")
        print("-" * 40)

        # Nach Score sortiert
        sorted_paths = sorted(paths, key=lambda p: p.overall_score(), reverse=True)

        for i, path in enumerate(sorted_paths, 1):
            selected = "✅" if plan.selected_paths.get(sp_id) == path.id else "  "
            score = path.overall_score()

            print(f"\n{selected} {i}. {path.title} (Score: {score:.1f})")
            print(f"   Typ: {path.solution_type.value}")
            print(f"   Wirksamkeit: {'★' * path.effectiveness}{'☆' * (10-path.effectiveness)}")
            print(f"   Aufwand: {path.effort}/10 ({path.estimated_hours or '?'}h)")
            print(f"   Risiko: {path.risk.value}")

            if path.implementation_steps:
                print(f"   Schritte:")
                for step in path.implementation_steps[:3]:
                    print(f"     - {step}")

        # Besten Pfad anzeigen
        best = plan.get_best_path(sp_id)
        if best and plan.selected_paths.get(sp_id) != best.id:
            print(f"\n   💡 Empfehlung: {best.title} (Score: {best.overall_score():.1f})")

    # Statistik
    stats = plan.get_statistics()
    print(f"\n{'='*60}")
    print(f"Statistik:")
    print(f"  Teilprobleme: {stats['total_subproblems']}")
    print(f"  Lösungspfade gesamt: {stats['total_paths']}")
    print(f"  Ausgewählt: {stats['selected_count']} ({stats['completion_percentage']:.0f}%)")
    print(f"  Quick Wins: {stats['quick_wins']}")
    print(f" 高风险ige Pfade: {stats['high_risk_paths']}")

    if 'avg_overall_score' in stats:
        print(f"  Ø Score: {stats['avg_overall_score']:.1f}/10")

    print(f"\n{'='*60}")
    return 0


def cmd_problem_select_path(args: argparse.Namespace) -> int:
    """
    `glitchhunter problem select` - Lösungsweg auswählen.
    """
    from core.config import load_config

    config = load_config()
    repo_path = Path(config.repository.path)
    manager = ProblemManager(repo_path=repo_path)

    # Lösungsweg auswählen
    success = manager.select_solution_path(
        problem_id=args.problem_id,
        subproblem_id=args.subproblem_id,
        path_id=args.path_id,
    )

    if success:
        print(f"✅ Lösungsweg ausgewählt für {args.subproblem_id}")
        return 0
    else:
        print(f"❌ Fehler: Problem/Plan nicht gefunden", file=sys.stderr)
        return 1


def setup_problem_parser(subparsers) -> None:
    """
    Registriert Problem-Solver Commands im CLI-Parser.
    
    Wird von main.py aufgerufen um Commands zu registrieren:
    - problem intake
    - problem list
    - problem show
    - problem classify
    - problem delete
    - problem stats
    """
    # Haupt-Parser für "problem" Command
    problem_parser = subparsers.add_parser(
        "problem",
        help="Problem-Solver commands (parallel to bug-hunting)",
    )
    problem_subparsers = problem_parser.add_subparsers(
        dest="problem_command",
        help="Problem-Solver subcommand",
    )
    
    # intake
    intake_parser = problem_subparsers.add_parser(
        "intake",
        help="Take in a new problem",
    )
    intake_parser.add_argument(
        "description",
        nargs="?",
        help="Problem description text",
    )
    intake_parser.add_argument(
        "-f", "--file",
        help="Read problem description from file",
    )
    intake_parser.add_argument(
        "-t", "--title",
        help="Optional title for the problem",
    )
    intake_parser.set_defaults(func=cmd_problem_intake)
    
    # list
    list_parser = problem_subparsers.add_parser(
        "list",
        help="List all problems",
    )
    list_parser.add_argument(
        "--status",
        help="Filter by status (intake, diagnosis, planning, etc.)",
    )
    list_parser.add_argument(
        "--type",
        help="Filter by problem type (bug, performance, etc.)",
    )
    list_parser.set_defaults(func=cmd_problem_list)
    
    # show
    show_parser = problem_subparsers.add_parser(
        "show",
        help="Show problem details",
    )
    show_parser.add_argument(
        "problem_id",
        help="ID of the problem to show",
    )
    show_parser.set_defaults(func=cmd_problem_show)
    
    # classify
    classify_parser = problem_subparsers.add_parser(
        "classify",
        help="Classify a problem",
    )
    classify_parser.add_argument(
        "problem_id",
        help="ID of the problem to classify",
    )
    classify_parser.set_defaults(func=cmd_problem_classify)
    
    # delete
    delete_parser = problem_subparsers.add_parser(
        "delete",
        help="Delete a problem",
    )
    delete_parser.add_argument(
        "problem_id",
        help="ID of the problem to delete",
    )
    delete_parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )
    delete_parser.set_defaults(func=cmd_problem_delete)
    
    # stats
    stats_parser = problem_subparsers.add_parser(
        "stats",
        help="Show problem statistics",
    )
    stats_parser.set_defaults(func=cmd_problem_stats)

    # report
    report_parser = problem_subparsers.add_parser(
        "report",
        help="Generate problem reports",
    )
    report_parser.add_argument(
        "problem_id",
        help="ID of the problem",
    )
    report_parser.add_argument(
        "-o", "--output-dir",
        help="Output directory for reports",
    )
    report_parser.add_argument(
        "-c", "--classify",
        action="store_true",
        help="Classify before generating reports",
    )
    report_parser.set_defaults(func=cmd_problem_report)

    # diagnose
    diagnose_parser = problem_subparsers.add_parser(
        "diagnose",
        help="Generate diagnosis for a problem",
    )
    diagnose_parser.add_argument(
        "problem_id",
        help="ID of the problem to diagnose",
    )
    diagnose_parser.set_defaults(func=cmd_problem_diagnose)

    # decompose
    decompose_parser = problem_subparsers.add_parser(
        "decompose",
        help="Decompose problem into subproblems",
    )
    decompose_parser.add_argument(
        "problem_id",
        help="ID of the problem to decompose",
    )
    decompose_parser.set_defaults(func=cmd_problem_decompose)

    # plan
    plan_parser = problem_subparsers.add_parser(
        "plan",
        help="Create solution plan for problem",
    )
    plan_parser.add_argument(
        "problem_id",
        help="ID of the problem",
    )
    plan_parser.add_argument(
        "--skip-decomposition",
        action="store_true",
        help="Skip using decomposition",
    )
    plan_parser.set_defaults(func=cmd_problem_plan)

    # select
    select_parser = problem_subparsers.add_parser(
        "select",
        help="Select solution path for subproblem",
    )
    select_parser.add_argument(
        "problem_id",
        help="ID of the problem",
    )
    select_parser.add_argument(
        "subproblem_id",
        help="ID of the subproblem",
    )
    select_parser.add_argument(
        "path_id",
        help="ID of the solution path",
    )
    select_parser.set_defaults(func=cmd_problem_select_path)
