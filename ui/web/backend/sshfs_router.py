"""
SSHFS Mount Router für GlitchHunter Web-UI.

Ermöglicht das Einbinden von Remote-Verzeichnissen (z.B. sundancer:/home/schaf/projects)
via SSHFS in den Container, damit lokale Projekte im WebUI sichtbar werden.
"""

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sshfs", tags=["sshfs"])

# Mount-Konfiguration
MOUNT_BASE = "/mnt/remote"
STATE_FILE = "/app/data/sshfs_state.json"

# SSHFS-Konfiguration (wird aus State geladen)
class SSHFSConfig(BaseModel):
    host: str = Field(default="sundancer", description="Remote-Host")
    remote_path: str = Field(default="/home/schaf/projects", description="Remote-Pfad")
    mount_point: str = Field(default="/mnt/remote/projects", description="Lokaler Mount-Point")
    user: str = Field(default="schaf", description="SSH-User")
    auto_mount: bool = Field(default=False, description="Automatisch mounten beim Start")


class SSHFSStatus(BaseModel):
    mounted: bool
    host: str = ""
    remote_path: str = ""
    mount_point: str = ""
    projects: list = []
    error: Optional[str] = None


def _load_state() -> SSHFSConfig:
    """Lädt gespeicherte SSHFS-Konfiguration."""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                data = json.load(f)
            return SSHFSConfig(**data)
    except Exception as e:
        logger.warning(f"SSHFS State konnte nicht geladen werden: {e}")
    return SSHFSConfig()


def _save_state(config: SSHFSConfig):
    """Speichert SSHFS-Konfiguration."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(config.model_dump(), f, indent=2)


def _is_mounted(mount_point: str) -> bool:
    """Prüft ob der Mount-Point aktiv ist."""
    try:
        result = subprocess.run(
            ["mountpoint", "-q", mount_point],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def _list_projects(mount_point: str) -> list:
    """Listet Projekte im Mount-Point auf."""
    projects = []
    try:
        mp = Path(mount_point)
        if mp.is_dir():
            for entry in sorted(mp.iterdir()):
                if entry.is_dir() and not entry.name.startswith("."):
                    is_git = (entry / ".git").exists()
                    projects.append({
                        "name": entry.name,
                        "path": str(entry),
                        "is_project": is_git,
                    })
    except Exception as e:
        logger.warning(f"Projekte konnten nicht gelistet werden: {e}")
    return projects


@router.get("/status", response_model=SSHFSStatus)
async def get_sshfs_status():
    """Gibt aktuellen SSHFS-Status zurück."""
    config = _load_state()
    mounted = _is_mounted(config.mount_point)
    projects = _list_projects(config.mount_point) if mounted else []

    return SSHFSStatus(
        mounted=mounted,
        host=config.host,
        remote_path=config.remote_path,
        mount_point=config.mount_point,
        projects=projects,
    )


@router.post("/mount", response_model=SSHFSStatus)
async def sshfs_mount(config: SSHFSConfig):
    """Mountet Remote-Verzeichnis via SSHFS."""
    logger.info(f"SSHFS Mount angefordert: {config.user}@{config.host}:{config.remote_path} -> {config.mount_point}")

    # Prüfe ob bereits gemountet
    if _is_mounted(config.mount_point):
        logger.info(f"Bereits gemountet: {config.mount_point}")
        _save_state(config)
        projects = _list_projects(config.mount_point)
        return SSHFSStatus(
            mounted=True,
            host=config.host,
            remote_path=config.remote_path,
            mount_point=config.mount_point,
            projects=projects,
        )

    # Mount-Point erstellen
    os.makedirs(config.mount_point, exist_ok=True)

    # SSHFS Mount
    remote = f"{config.user}@{config.host}:{config.remote_path}"
    cmd = [
        "sshfs",
        "-o", "allow_other",
        "-o", "StrictHostKeyChecking=no",
        "-o", "IdentityFile=/root/.ssh/id_ed25519",
        "-o", "reconnect",
        "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=3",
        "-o", "auto_unmount",
        remote,
        config.mount_point,
    ]

    logger.info(f"Führe aus: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            error_msg = result.stderr.strip() or f"Exit code {result.returncode}"
            logger.error(f"SSHFS Mount fehlgeschlagen: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Mount fehlgeschlagen: {error_msg}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="SSHFS Mount Timeout (30s)")
    except HTTPException:
        raise

    # Kurz warten bis Mount stabil
    await asyncio.sleep(1)

    mounted = _is_mounted(config.mount_point)
    if not mounted:
        raise HTTPException(status_code=500, detail="Mount wurde erstellt aber ist nicht aktiv")

    # State speichern
    config.auto_mount = True
    _save_state(config)

    projects = _list_projects(config.mount_point)
    logger.info(f"SSHFS Mount erfolgreich: {len(projects)} Projekte sichtbar")

    return SSHFSStatus(
        mounted=True,
        host=config.host,
        remote_path=config.remote_path,
        mount_point=config.mount_point,
        projects=projects,
    )


@router.post("/unmount", response_model=SSHFSStatus)
async def sshfs_unmount():
    """Unmountet SSHFS-Verzeichnis."""
    config = _load_state()

    if not _is_mounted(config.mount_point):
        config.auto_mount = False
        _save_state(config)
        return SSHFSStatus(
            mounted=False,
            host=config.host,
            remote_path=config.remote_path,
            mount_point=config.mount_point,
        )

    logger.info(f"SSHFS Unmount: {config.mount_point}")

    try:
        result = subprocess.run(
            ["fusermount", "-u", config.mount_point],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            # Fallback: lazy unmount
            logger.warning(f"fusermount fehlgeschlagen, versuche lazy unmount: {result.stderr}")
            result = subprocess.run(
                ["fusermount", "-uz", config.mount_point],
                capture_output=True, text=True, timeout=15
            )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Unmount Timeout")

    config.auto_mount = False
    _save_state(config)

    mounted = _is_mounted(config.mount_point)
    return SSHFSStatus(
        mounted=mounted,
        host=config.host,
        remote_path=config.remote_path,
        mount_point=config.mount_point,
    )


@router.get("/projects", response_model=list)
async def list_remote_projects():
    """Listet Projekte im gemounteten Verzeichnis."""
    config = _load_state()

    if not _is_mounted(config.mount_point):
        raise HTTPException(status_code=400, detail="Nicht gemountet. Bitte zuerst mounten.")

    return _list_projects(config.mount_point)


@router.post("/auto-mount")
async def auto_mount():
    """Automatischer Mount beim Start (wenn konfiguriert)."""
    config = _load_state()

    if not config.auto_mount:
        return {"status": "skipped", "message": "Auto-Mount nicht aktiviert"}

    if _is_mounted(config.mount_point):
        return {"status": "already_mounted", "mount_point": config.mount_point}

    try:
        return await sshfs_mount(config)
    except Exception as e:
        logger.error(f"Auto-Mount fehlgeschlagen: {e}")
        return {"status": "error", "message": str(e)}