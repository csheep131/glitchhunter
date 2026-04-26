"""
Discovery Router für GlitchHunter Web-UI.

Stellt API-Endpoints bereit, die Projekt- und Datei-Pfade
für das Frontend automatisch auflösen (kein manuelles Tippen nötig).
"""

import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/discover", tags=["Discovery"])

# Basis-Verzeichnisse für die Suche
PROJECTS_BASE = Path("/home/schaf/projects")
GLITCHHUNTER_BASE = Path("/home/schaf/projects/glitchhunter")
# SSHFS Remote-Mount Basis
SSHFS_MOUNT_BASE = Path("/mnt/remote")


def scan_projects(base: Path) -> List[str]:
    """Scannt ein Verzeichnis nach Git-Projekten und Unterordnern."""
    if not base.exists():
        return []
    
    projects = []
    for item in sorted(base.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue
        # Ist es ein Projekt? (hat src/, pyproject.toml, package.json, .git oder Cargo.toml)
        has_project_marker = any(
            (item / marker).exists()
            for marker in [".git", "src", "pyproject.toml", "package.json", "Cargo.toml", "setup.py", "go.mod"]
        )
        if has_project_marker or any((item / d).is_dir() for d in ["src", "backend", "frontend", "app"]):
            projects.append(str(item))
    
    return projects


@router.get("/projects")
async def discover_projects():
    """Erkennt alle Projekte in /home/schaf/projects/ und SSHFS-Mounts."""
    projects = scan_projects(PROJECTS_BASE)
    
    # SSHFS Remote-Projekte hinzufügen
    remote_projects = []
    if SSHFS_MOUNT_BASE.exists():
        for mount_dir in sorted(SSHFS_MOUNT_BASE.iterdir()):
            if mount_dir.is_dir() and not mount_dir.name.startswith("."):
                remote_projects.extend(scan_projects(mount_dir))
    
    return {
        "projects": projects,
        "remote_projects": remote_projects,
        "total_count": len(projects) + len(remote_projects),
        "count": len(projects),
        "remote_count": len(remote_projects),
        "base_path": str(PROJECTS_BASE),
        "sshfs_base": str(SSHFS_MOUNT_BASE),
    }


@router.get("/projects/remote")
async def discover_remote_projects():
    """Erkennt alle Projekte in SSHFS Remote-Mounts."""
    remote_projects = []
    
    if not SSHFS_MOUNT_BASE.exists():
        return {
            "projects": [],
            "count": 0,
            "base_path": str(SSHFS_MOUNT_BASE),
            "error": "SSHFS Mount-Verzeichnis nicht gefunden",
        }
    
    for mount_dir in sorted(SSHFS_MOUNT_BASE.iterdir()):
        if mount_dir.is_dir() and not mount_dir.name.startswith("."):
            found = scan_projects(mount_dir)
            for p in found:
                remote_projects.append({
                    "path": p,
                    "mount_point": str(mount_dir),
                    "name": Path(p).name,
                })
    
    return {
        "projects": remote_projects,
        "count": len(remote_projects),
        "base_path": str(SSHFS_MOUNT_BASE),
    }


@router.get("/browse")
async def browse_directory(path: str = "/home/schaf"):
    """Verzeichnis-Browser für Datei-Auswahl-Dialog."""
    base = Path(path)
    if not base.exists() or not base.is_dir():
        return {"path": path, "parent": None, "dirs": [], "error": "Pfad nicht gefunden"}
    
    dirs = []
    try:
        for item in sorted(base.iterdir()):
            if item.is_dir() and not item.name.startswith(".") and item.name != "__pycache__":
                has_project = any(
                    (item / marker).exists()
                    for marker in [".git", "src", "pyproject.toml", "package.json", "Cargo.toml", "setup.py", "go.mod"]
                )
                dirs.append({
                    "name": item.name,
                    "path": str(item),
                    "is_project": has_project,
                })
    except PermissionError:
        return {"path": str(base), "parent": str(base.parent), "dirs": [], "error": "Keine Berechtigung"}
    
    return {
        "path": str(base),
        "parent": str(base.parent) if base.parent != base else None,
        "dirs": dirs,
    }


@router.get("/files")
async def discover_files(project_path: str = ""):
    """Erkennt alle relevanten Dateien in einem Projekt."""
    base = Path(project_path) if project_path else GLITCHHUNTER_BASE
    if not base.exists() or not base.is_dir():
        return {"files": [], "count": 0, "error": f"Pfad nicht gefunden: {base}"}
    
    # Relevante Code-Dateien finden
    extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java", ".cpp", ".c", ".h", ".hpp"}
    files = []
    for ext in extensions:
        for f in sorted(base.rglob(f"*{ext}")):
            if any(part.startswith(".") or part == "__pycache__" or part == "node_modules" or part == "target" for part in f.parts):
                continue
            files.append(str(f))
            if len(files) >= 500:
                break
        if len(files) >= 500:
            break
    
    return {
        "files": files[:500],
        "count": min(len(files), 500),
        "project_path": str(base),
    }
