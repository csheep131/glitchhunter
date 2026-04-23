"""
Refactoring-Service für GlitchHunter Web-UI.

Bietet API-Endpoints für:
- Refactoring-Vorschläge anzeigen
- Preview generieren (Diff)
- Refactoring anwenden
- Rollback durchführen

Features:
- Git-Integration für Rollback
- Diff-Generierung
- Pre-Apply-Validierung
- Post-Apply-Testing
"""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/refactor", tags=["Refactoring"])


# ============== Models ==============

class RefactoringSuggestion(BaseModel):
    """Vorschlag für ein Refactoring."""
    id: str
    file_path: str
    line_start: int
    line_end: int
    category: str
    title: str
    description: str
    original_code: str
    suggested_code: str
    confidence: float = 0.5
    risk_level: str = "medium"
    estimated_impact: Optional[str] = None


class RefactoringPreview(BaseModel):
    """Preview eines Refactorings."""
    suggestion_id: str
    file_path: str
    diff: str
    lines_added: int
    lines_removed: int
    risk_assessment: str
    test_required: bool


class ApplyRefactoringRequest(BaseModel):
    """Request zum Anwenden eines Refactorings."""
    suggestion_id: str
    file_path: str
    preview_accepted: bool = True
    create_backup: bool = True
    run_tests: bool = True


class ApplyRefactoringResponse(BaseModel):
    """Response nach Anwenden eines Refactorings."""
    success: bool
    message: str
    git_commit: Optional[str] = None
    backup_path: Optional[str] = None
    test_result: Optional[Dict[str, Any]] = None
    diff: Optional[str] = None


class RollbackRequest(BaseModel):
    """Request für Rollback."""
    git_commit: str
    reason: str = "User requested rollback"


class RollbackResponse(BaseModel):
    """Response nach Rollback."""
    success: bool
    message: str
    git_commit: Optional[str] = None


# ============== Service ==============

class RefactoringService:
    """
    Service für Refactoring-Operationen.
    
    Usage:
        service = RefactoringService()
        suggestions = await service.get_suggestions(file_path)
        preview = await service.generate_preview(suggestion)
        result = await service.apply(suggestion)
    """
    
    def __init__(self):
        """Initialisiert Refactoring-Service."""
        self._auto_refactor = None
        logger.info("RefactoringService initialisiert")
    
    def _get_auto_refactor(self):
        """Lädt AutoRefactor-Instanz."""
        if self._auto_refactor is None:
            from src.fixing.auto_refactor import AutoRefactor
            self._auto_refactor = AutoRefactor(
                use_git=True,
                run_tests=True,
                backup=True,
            )
        return self._auto_refactor
    
    async def get_suggestions(self, file_path: str) -> List[RefactoringSuggestion]:
        """
        Holt Refactoring-Vorschläge für eine Datei.
        
        Args:
            file_path: Pfad zur Datei
            
        Returns:
            Liste von RefactoringSuggestion
        """
        try:
            auto_refactor = self._get_auto_refactor()
            path = Path(file_path)
            
            if not path.exists():
                raise HTTPException(status_code=404, detail=f"Datei nicht gefunden: {file_path}")
            
            # Vorschläge analysieren
            suggestions = await auto_refactor.analyze_file(path)
            
            # In API-Modell konvertieren
            return [
                RefactoringSuggestion(
                    id=s.id,
                    file_path=s.file_path,
                    line_start=s.line_start,
                    line_end=s.line_end,
                    category=s.category,
                    title=s.title,
                    description=s.description,
                    original_code=s.original_code,
                    suggested_code=s.suggested_code,
                    confidence=s.confidence,
                    risk_level=s.risk_level,
                    estimated_impact=s.estimated_impact,
                )
                for s in suggestions
            ]
            
        except Exception as e:
            logger.error(f"Fehler beim Analysieren: {e}")
            return []
    
    async def generate_preview(self, suggestion: RefactoringSuggestion) -> RefactoringPreview:
        """
        Generiert Preview (Diff) für ein Refactoring.
        
        Args:
            suggestion: RefactoringSuggestion
            
        Returns:
            RefactoringPreview
        """
        try:
            # Diff generieren
            diff = self._generate_diff(
                suggestion.original_code,
                suggestion.suggested_code,
            )
            
            lines_added = suggestion.suggested_code.count('\n') + 1
            lines_removed = suggestion.original_code.count('\n') + 1
            
            # Risk-Assessment
            risk = self._assess_risk(suggestion)
            
            return RefactoringPreview(
                suggestion_id=suggestion.id,
                file_path=suggestion.file_path,
                diff=diff,
                lines_added=max(0, lines_added - lines_removed),
                lines_removed=max(0, lines_removed - lines_added),
                risk_assessment=risk,
                test_required=suggestion.risk_level in ["high", "critical"],
            )
            
        except Exception as e:
            logger.error(f"Fehler beim Generieren der Preview: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def _generate_diff(self, original: str, new: str) -> str:
        """Generiert Unified Diff."""
        import difflib
        
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile="original",
            tofile="refactored",
        )
        
        return "".join(diff)
    
    def _assess_risk(self, suggestion: RefactoringSuggestion) -> str:
        """Bewertet Risiko eines Refactorings."""
        if suggestion.risk_level == "critical":
            return "Hoch - Umfangreiche Änderungen, Tests erforderlich"
        elif suggestion.risk_level == "high":
            return "Mittel-Hoch - Größere Änderungen, Tests empfohlen"
        elif suggestion.risk_level == "medium":
            return "Mittel - Standard-Refactoring"
        else:
            return "Niedrig - Kosmetische Änderungen"
    
    async def apply(self, request: ApplyRefactoringRequest) -> ApplyRefactoringResponse:
        """
        Wendet Refactoring an.
        
        Args:
            request: ApplyRefactoringRequest
            
        Returns:
            ApplyRefactoringResponse
        """
        try:
            auto_refactor = self._get_auto_refactor()
            path = Path(request.file_path)
            
            if not path.exists():
                raise HTTPException(status_code=404, detail=f"Datei nicht gefunden: {request.file_path}")
            
            # Vorschlag finden (hier simuliert - in echter Implementierung aus DB/Cache laden)
            suggestion = await self._get_suggestion_by_id(request.suggestion_id)
            
            if not suggestion:
                raise HTTPException(status_code=404, detail=f"Vorschlag nicht gefunden: {request.suggestion_id}")
            
            # Refactoring anwenden
            result = await auto_refactor.refactor_file(path, suggestion)
            
            if result.success:
                return ApplyRefactoringResponse(
                    success=True,
                    message="Refactoring erfolgreich angewendet",
                    git_commit=result.git_commit,
                    backup_path=result.metadata.get("backup_path"),
                    test_result=result.test_result,
                    diff=result.diff,
                )
            else:
                return ApplyRefactoringResponse(
                    success=False,
                    message=f"Refactoring fehlgeschlagen: {result.error}",
                )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Fehler beim Anwenden: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_suggestion_by_id(self, suggestion_id: str) -> Optional[Any]:
        """Lädt Vorschlag nach ID (hier simuliert)."""
        # In echter Implementierung: Aus Datenbank oder Cache laden
        # Hier: Dummy-Implementierung
        from src.fixing.auto_refactor import RefactoringSuggestion
        
        return RefactoringSuggestion(
            id=suggestion_id,
            file_path="dummy.py",
            line_start=1,
            line_end=10,
            category="test",
            title="Test",
            description="Test",
            original_code="pass",
            suggested_code="pass",
        )
    
    async def rollback(self, request: RollbackRequest) -> RollbackResponse:
        """
        Führt Rollback durch.
        
        Args:
            request: RollbackRequest
            
        Returns:
            RollbackResponse
        """
        try:
            # Git-Rollback durchführen
            result = subprocess.run(
                ["git", "reset", "--hard", request.git_commit],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode == 0:
                return RollbackResponse(
                    success=True,
                    message=f"Rollback erfolgreich zu {request.git_commit[:8]}",
                    git_commit=request.git_commit,
                )
            else:
                return RollbackResponse(
                    success=False,
                    message=f"Rollback fehlgeschlagen: {result.stderr}",
                )
            
        except Exception as e:
            logger.error(f"Fehler beim Rollback: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# ============== Router ==============

service = RefactoringService()


@router.get("/suggestions", response_model=List[RefactoringSuggestion])
async def get_suggestions(file_path: str):
    """Refactoring-Vorschläge für eine Datei."""
    return await service.get_suggestions(file_path)


@router.post("/preview", response_model=RefactoringPreview)
async def generate_preview(suggestion: RefactoringSuggestion):
    """Preview (Diff) für ein Refactoring generieren."""
    return await service.generate_preview(suggestion)


@router.post("/apply", response_model=ApplyRefactoringResponse)
async def apply_refactoring(request: ApplyRefactoringRequest):
    """Refactoring anwenden."""
    return await service.apply(request)


@router.post("/rollback", response_model=RollbackResponse)
async def rollback_refactoring(request: RollbackRequest):
    """Rollback durchführen."""
    return await service.rollback(request)


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_refactoring_history(file_path: Optional[str] = None):
    """Refactoring-Historie anzeigen."""
    # TODO: Implementierung
    return []
