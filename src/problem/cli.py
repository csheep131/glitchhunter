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
from .stack_adapter import StackID
from .validation import ValidationStatus


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
    from core.config import Config

    config = Config.load()
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
    from core.config import Config

    config = Config.load()
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


def cmd_problem_stack(args: argparse.Namespace) -> int:
    """
    `glitchhunter problem stack` - Stack-Informationen anzeigen.
    """
    from core.config import Config

    config = Config.load()
    # Repository-Pfad ermitteln (fallback zu aktuellem Verzeichnis)
    repo_path = Path(getattr(config, 'repository', None) and getattr(config.repository, 'path', None) or Path.cwd())
    manager = ProblemManager(repo_path=repo_path)

    if args.compare:
        # Stack-Vergleich
        comparison = manager.compare_stacks(args.capability)

        print(f"\n📊 Stack-Vergleich")
        print(f"{'='*60}")

        print(f"\n{comparison['stack_a']['name']}:")
        caps_a = comparison['stack_a']['capabilities']
        print(f"  Capabilities: {caps_a['supported_capabilities']}/{caps_a['total_capabilities']}")
        print(f"  Coverage: {caps_a['capability_coverage']:.0f}%")

        print(f"\n{comparison['stack_b']['name']}:")
        caps_b = comparison['stack_b']['capabilities']
        print(f"  Capabilities: {caps_b['supported_capabilities']}/{caps_b['total_capabilities']}")
        print(f"  Coverage: {caps_b['capability_coverage']:.0f}%")

        if 'differences' in comparison:
            print(f"\nUnterschiede:")
            for key, diff in comparison['differences'].items():
                if isinstance(diff, dict) and 'difference' in diff:
                    print(f"  {key}: {diff['difference']:+.1f}%")

    elif args.recommend:
        # Empfehlung für Problem
        recommendation = manager.recommend_stack_for_problem(args.recommend)
        print(f"\n✅ Empfehlung für {args.recommend}:")
        print(f"   Stack: {recommendation}")

    elif args.profile:
        # Spezifisches Profil
        profile = manager.get_stack_profile(args.profile)
        if profile:
            stats = profile.get_statistics()
            print(f"\n📋 {profile.name}")
            print(f"{'='*60}")
            print(f"Beschreibung: {profile.description}")
            print(f"\nRessourcen:")
            print(f"  Memory: {stats['resources']['memory_gb']}GB")
            print(f"  CPU: {stats['resources']['cpu_cores']} Kerne")
            print(f"  GPU: {stats['resources']['gpu']}")
            print(f"\nCapabilities:")
            print(f"  Gesamt: {stats['total_capabilities']}")
            print(f"  Unterstützt: {stats['supported_capabilities']}")
            print(f"  Coverage: {stats['capability_coverage']:.0f}%")
            print(f"\nFeatures: {stats['enabled_features']}/{stats['total_features']}")
        else:
            print(f"Stack-Profil nicht gefunden: {args.profile}", file=sys.stderr)
            return 1

    else:
        # Übersicht
        print(f"\n📦 Verfügbare Stacks:")
        print(f"{'='*60}")

        for stack_id in StackID:
            if stack_id == StackID.AUTO:
                continue

            profile = manager.get_stack_profile(stack_id.value)
            if profile:
                stats = profile.get_statistics()
                print(f"\n{stack_id.value}:")
                print(f"  Name: {profile.name}")
                print(f"  Capabilities: {stats['supported_capabilities']}/{stats['total_capabilities']}")
                print(f"  Coverage: {stats['capability_coverage']:.0f}%")
                print(f"  Features: {stats['enabled_features']}/{stats['total_features']}")

        print(f"\n{'='*60}")
        print(f"\nCommands:")
        print(f"  glitchhunter problem stack --compare")
        print(f"  glitchhunter problem stack --profile stack_a")
        print(f"  glitchhunter problem stack --recommend <problem_id>")

    return 0


def cmd_problem_validate(args: argparse.Namespace) -> int:
    """
    `glitchhunter problem validate` - Goal Validation durchführen.
    
    Prüft ob die Success Criteria eines Problems erfüllt sind.
    """
    from core.config import load_config
    
    config = load_config()
    repo_path = Path(config.repository.path)
    manager = ProblemManager(repo_path=repo_path)
    
    # Validation durchführen
    try:
        report = manager.validate_goal(
            problem_id=args.problem_id,
            implemented_changes=None,  # Kann aus Datei geladen werden
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    # Ausgabe
    print(f"\n✅ Goal Validation für {args.problem_id}")
    print(f"{'='*60}")
    print(f"{report.summary}")
    print(f"\n{'='*60}")
    
    # Einzelne Kriterien
    print(f"\nKriterien:")
    for i, result in enumerate(report.results, 1):
        status_icon = {
            "passed": "✅",
            "failed": "❌",
            "partial": "⚠️",
            "pending": "⏳",
            "blocked": "🚫",
        }.get(result.status.value, "❓")
        
        print(f"\n{i}. {status_icon} {result.criterion}")
        if result.description:
            print(f"   {result.description}")
        if result.status == ValidationStatus.FAILED:
            print(f"   Grund: {result.failure_reason}")
            if result.remediation_steps:
                print(f"   Nächste Schritte:")
                for step in result.remediation_steps[:3]:
                    print(f"     - {step}")
    
    # Statistik
    stats = report.get_statistics()
    print(f"\n{'='*60}")
    print(f"Statistik:")
    print(f"  Bestanden: {stats['passed']}/{stats['total_criteria']} ({stats['completion_percentage']:.0f}%)")
    print(f"  Fehlgeschlagen: {stats['failed']}")
    print(f"  Ausstehend: {stats['pending']}")
    print(f"  Blockiert: {stats['blocked']}")
    print(f"  Gesamt-Status: {stats['overall_status']}")
    
    print(f"\n{'='*60}")
    return 0


def cmd_problem_intent(args: argparse.Namespace) -> int:
    """
    `glitchhunter problem intent` - Intent Validation durchführen.
    
    Prüft ob das ursprüngliche Problem wirklich gelöst wurde
    oder nur Symptome behandelt wurden (Scheinlösung).
    """
    from core.config import load_config
    
    config = load_config()
    repo_path = Path(config.repository.path)
    manager = ProblemManager(repo_path=repo_path)
    
    # Intent Validation durchführen
    try:
        report = manager.validate_intent(
            problem_id=args.problem_id,
            solution_description=args.solution or "",
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    # Ausgabe
    print(f"\n✅ Intent Validation für {args.problem_id}")
    print(f"{'='*60}")
    print(f"Original-Problem: {report.original_problem_description[:100]}...")
    print(f"\nAnalyse:")
    print(report.analysis)
    
    if report.concerns:
        print(f"\nBedenken:")
        for concern in report.concerns:
            print(f"  {concern}")
    
    print(f"\n{'='*60}")
    print(f"Status: {report.overall_status.value}")
    print(f"{'='*60}")
    return 0


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

    # stack
    stack_parser = problem_subparsers.add_parser(
        "stack",
        help="Show stack information and recommendations",
    )
    stack_parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare both stacks",
    )
    stack_parser.add_argument(
        "--profile",
        help="Show profile for specific stack",
    )
    stack_parser.add_argument(
        "--recommend",
        metavar="PROBLEM_ID",
        help="Recommend stack for problem",
    )
    stack_parser.add_argument(
        "--capability",
        help="Compare specific capability",
    )
    stack_parser.set_defaults(func=cmd_problem_stack)

    # validate
    validate_parser = problem_subparsers.add_parser(
        "validate",
        help="Perform goal validation for problem",
    )
    validate_parser.add_argument(
        "problem_id",
        help="ID of the problem",
    )
    validate_parser.set_defaults(func=cmd_problem_validate)

    # intent
    intent_parser = problem_subparsers.add_parser(
        "intent",
        help="Perform intent validation for problem",
    )
    intent_parser.add_argument(
        "problem_id",
        help="ID of the problem",
    )
    intent_parser.add_argument(
        "-s", "--solution",
        help="Description of the implemented solution",
    )
    intent_parser.set_defaults(func=cmd_problem_intent)

    # fix
    fix_parser = problem_subparsers.add_parser(
        "fix",
        help="Perform auto-fix for problem",
    )
    fix_parser.add_argument(
        "problem_id",
        help="ID of the problem",
    )
    fix_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't apply actual changes",
    )
    fix_parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip validation after applying patches",
    )
    fix_parser.set_defaults(func=cmd_problem_fix)

    # rollback
    rollback_parser = problem_subparsers.add_parser(
        "rollback",
        help="Rollback auto-fix for problem",
    )
    rollback_parser.add_argument(
        "problem_id",
        help="ID of the problem",
    )
    rollback_parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )
    rollback_parser.set_defaults(func=cmd_problem_rollback)


def cmd_problem_fix(args: argparse.Namespace) -> int:
    """
    `glitchhunter problem fix` - Auto-Fix durchführen.

    Führt automatische Patch-Generierung und Anwendung durch
    basierend auf dem SolutionPlan.
    """
    from core.config import Config

    config = Config.load(args.config if hasattr(args, 'config') else None)
    repo_path = Path(config.repository.path)
    manager = ProblemManager(repo_path=repo_path)

    # Auto-Fix durchführen
    try:
        result = manager.auto_fix(
            problem_id=args.problem_id,
            dry_run=args.dry_run,
            validate=not args.no_validate,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Ausgabe
    print(f"\n✅ Auto-Fix für {args.problem_id}")
    if args.dry_run:
        print(f"   (DRY RUN - keine Änderungen angewendet)")
    print(f"{'='*60}")
    print(f"{result.summary}")
    print(f"\n{'='*60}")

    # Einzelne Patches
    print(f"\nPatches ({len(result.patches)}):")
    for i, patch in enumerate(result.patches, 1):
        status_icon = {
            "completed": "✅",
            "failed": "❌",
            "rolled_back": "↩️",
            "pending": "⏳",
            "in_progress": "🔵",
            "blocked": "🚫",
        }.get(patch.status.value, "❓")

        print(f"\n{i}. {status_icon} {patch.id}")
        print(f"   File: {patch.file_path}")
        print(f"   SubProblem: {patch.subproblem_id}")

        if patch.validation_errors:
            print(f"   Errors: {', '.join(patch.validation_errors)}")

    # Statistik
    stats = result.get_statistics()
    print(f"\n{'='*60}")
    print(f"Statistik:")
    print(f"  Angewendet: {stats['applied']}/{stats['total_patches']} ({stats['success_rate']:.0f}%)")
    print(f"  Fehlgeschlagen: {stats['failed']}")
    print(f"  Rollback: {stats['rolled_back']}")
    print(f"  Ausstehend: {stats['pending']}")
    print(f"  Status: {stats['overall_status']}")

    if args.dry_run:
        print(f"\n💡 Hinweis: Dies war ein Dry-Run.")
        print(f"   Ohne --dry-run werden die Patches tatsächlich angewendet.")

    print(f"\n{'='*60}")
    return 0


def cmd_problem_rollback(args: argparse.Namespace) -> int:
    """
    `glitchhunter problem rollback` - Rollback von Auto-Fix.

    Stellt den Zustand vor der Auto-Fix-Anwendung wieder her
    mittels Backup-Dateien.
    """
    from core.config import Config

    config = Config.load(args.config if hasattr(args, 'config') else None)
    repo_path = Path(config.repository.path)
    manager = ProblemManager(repo_path=repo_path)

    # Bestätigung einholen
    if not args.force:
        confirm = input(f"Rollback für {args.problem_id} durchführen? [y/N] ")
        if confirm.lower() != 'y':
            print("Rollback abgebrochen")
            return 0

    # Rollback durchführen
    try:
        result = manager.rollback_fix(args.problem_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Ausgabe
    print(f"\n✅ Rollback für {args.problem_id}")
    print(f"{'='*60}")
    print(f"{result.summary}")
    print(f"\n{'='*60}")
    print(f"Status: {result.overall_status.value}")
    print(f"{'='*60}")
    return 0
