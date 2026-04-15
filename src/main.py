#!/usr/bin/env python3
"""
GlitchHunter -- AI-Powered Autonomous Bug-Fixing System.

Entry point for CLI and API server.
"""

import argparse
import atexit
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).parent))

# Global list of child processes to clean up
_child_processes = []

def _cleanup_child_processes():
    """Beende alle gestarteten Child-Prozesse ordentlich."""
    global _child_processes
    
    if not _child_processes:
        return
    
    logging.info(f"🧹 Cleaning up {len(_child_processes)} child process(es)...")
    
    for proc in _child_processes:
        try:
            if proc.poll() is None:  # Noch laufend
                logging.debug(f"  Terminating PID {proc.pid}...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                    logging.debug(f"  ✓ PID {proc.pid} terminated gracefully")
                except subprocess.TimeoutExpired:
                    logging.debug(f"  ⚠ PID {proc.pid} didn't terminate, killing...")
                    proc.kill()
        except Exception as e:
            logging.debug(f"Failed to terminate child process: {e}")
    
    _child_processes.clear()
    logging.info("✅ Cleanup complete")

def _signal_handler(signum, frame):
    """Signal-Handler für SIGTERM und SIGINT."""
    sig_name = signal.Signals(signum).name
    logging.info(f"📶 Received {sig_name}, cleaning up...")
    _cleanup_child_processes()
    sys.exit(128 + signum)

# Register signal handlers
signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)

# Register atexit handler for cleanup on normal exit
atexit.register(_cleanup_child_processes)

# Monkey-patch subprocess.Popen to track child processes
original_popen_init = subprocess.Popen.__init__

def _patched_popen_init(self, *args, **kwargs):
    """Wrapper um subprocess.Popen um Child-Prozesse zu tracken."""
    result = original_popen_init(self, *args, **kwargs)
    _child_processes.append(self)
    return result

subprocess.Popen.__init__ = _patched_popen_init


def cmd_analyze(args: argparse.Namespace) -> int:
    """Run full analysis pipeline on a repository."""
    from core.config import Config
    from core.logging_config import setup_logging

    config = Config.load(args.config)
    setup_logging(config.logging if hasattr(config, "logging") else None)

    repo_path = Path(args.repository).resolve()
    if not repo_path.exists():
        print(f"ERROR: Repository path not found: {repo_path}")
        return 1

    print(f"GlitchHunter v2.0.0")
    print(f"Target: {repo_path}")
    print(f"Config: {args.config}")
    print()

    from agent.state_machine import GlitchHunterWorkflow

    workflow = GlitchHunterWorkflow(config)
    result = workflow.run(str(repo_path))

    # Print summary
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

    if hasattr(result, "to_dict"):
        summary = result.to_dict()
    elif isinstance(result, dict):
        summary = result
    else:
        summary = {"result": str(result)}

    bugs_found = summary.get("bugs_found", summary.get("candidates_found", 0))
    bugs_fixed = summary.get("bugs_fixed", 0)
    bugs_escalated = summary.get("bugs_escalated", 0)

    print(f"  Bugs found:      {bugs_found}")
    print(f"  Bugs fixed:      {bugs_fixed}")
    print(f"  Bugs escalated:  {bugs_escalated}")

    report_path = summary.get("report_path")
    if report_path:
        print(f"  Report:          {report_path}")

    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Check system requirements and configuration."""
    print("GlitchHunter System Check")
    print("=" * 40)

    errors = []

    # 1. Check Python version
    py_ver = sys.version_info
    print(f"  Python:          {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    if py_ver < (3, 11):
        errors.append("Python 3.11+ required")

    # 2. Check config
    config_path = Path(args.config)
    if config_path.exists():
        print(f"  Config:          {config_path} [OK]")
    else:
        errors.append(f"Config not found: {config_path}")
        print(f"  Config:          {config_path} [MISSING]")

    # 3. Check hardware
    try:
        from hardware.detector import HardwareDetector
        detector = HardwareDetector()
        profile = detector.detect()
        print(f"  GPU Stack:       {profile.stack_type.value} [OK]")
        print(f"  VRAM Limit:      {profile.vram_limit}GB")
        gpu_name = detector.get_gpu_name()
        if gpu_name:
            print(f"  GPU:             {gpu_name}")
        detector.shutdown()
    except Exception as e:
        print(f"  Hardware:        [ERROR] {e}")
        errors.append(f"Hardware detection failed: {e}")

    # 4. Check Docker
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "--version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print(f"  Docker:          {result.stdout.strip()} [OK]")
        else:
            errors.append("Docker not available")
            print(f"  Docker:          [NOT AVAILABLE]")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print(f"  Docker:          [NOT INSTALLED]")

    # 5. Check key dependencies
    deps = [
        ("langgraph", "LangGraph"),
        ("networkx", "NetworkX"),
        ("tree_sitter", "Tree-sitter"),
        ("yaml", "PyYAML"),
        ("httpx", "httpx"),
        ("pydantic", "Pydantic"),
    ]
    for mod_name, display_name in deps:
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, "__version__", "unknown")
            print(f"  {display_name + ':':18s} {ver} [OK]")
        except ImportError:
            print(f"  {display_name + ':':18s} [MISSING]")
            errors.append(f"Missing dependency: {display_name}")

    print()
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("All checks passed!")
        return 0


def cmd_api(args: argparse.Namespace) -> int:
    """Start the API server."""
    try:
        import uvicorn
    except ImportError:
        print("ERROR: uvicorn not installed. Run: pip install uvicorn")
        return 1

    from api.server import create_app
    from core.config import Config

    config = Config.load(args.config)
    app = create_app(config)

    host = args.host or "0.0.0.0"
    port = args.port or 8000

    print(f"Starting GlitchHunter API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="glitchhunter",
        description="GlitchHunter -- AI-Powered Autonomous Bug-Fixing System",
    )
    parser.add_argument(
        "--config", "-c",
        default=str(Path(__file__).parent.parent / "config.yaml"),
        help="Path to config.yaml (default: config.yaml)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a repository")
    analyze_parser.add_argument("repository", help="Path to the repository to analyze")
    analyze_parser.add_argument("--output", "-o", help="Output directory for reports")

    # check command
    check_parser = subparsers.add_parser("check", help="Check system requirements")

    # api command
    api_parser = subparsers.add_parser("api", help="Start API server")
    api_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    api_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")

    args = parser.parse_args()

    if args.command == "analyze":
        return cmd_analyze(args)
    elif args.command == "check":
        return cmd_check(args)
    elif args.command == "api":
        return cmd_api(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
