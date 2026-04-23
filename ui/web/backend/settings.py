"""
Settings-Service für GlitchHunter Web-UI.

Verwaltet alle Einstellungen mit:
- Pydantic Models für Validierung
- SQLite Storage für Persistenz
- Fernet-Verschlüsselung für sensible Daten
- Kategorien für bessere Organisation
"""

import logging
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from ui.web.backend.storage import get_database

logger = logging.getLogger(__name__)


# ============== Settings Models ==============

class GeneralSettings(BaseModel):
    """Allgemeine Einstellungen."""
    language: str = "de"
    theme: Literal["light", "dark", "auto"] = "auto"
    timezone: str = "Europe/Berlin"
    date_format: str = "DD.MM.YYYY"


class AnalysisSettings(BaseModel):
    """Analyse-Einstellungen."""
    default_stack: str = "stack_b"
    default_parallel: bool = True
    default_ml_prediction: bool = True
    default_auto_refactor: bool = False
    max_workers: int = Field(default=4, ge=1, le=16)
    timeout_per_analysis: int = Field(default=300, ge=60, le=3600)
    auto_refresh_interval: int = Field(default=30, ge=5, le=300)


class SecuritySettings(BaseModel):
    """Security-Einstellungen."""
    session_timeout_minutes: int = Field(default=60, ge=5, le=1440)
    cors_origins: List[str] = ["http://localhost:6262"]
    rate_limit_per_minute: int = Field(default=60, ge=10, le=1000)


class LoggingSettings(BaseModel):
    """Logging-Einstellungen."""
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    logging_file: str = "logs/glitchhunter_webui.log"
    logging_max_size_mb: int = Field(default=10, ge=1, le=100)
    logging_backup_count: int = Field(default=5, ge=1, le=20)


class CompleteSettings(BaseModel):
    """Vollständige Settings-Struktur."""
    version: str = "1.0"
    general: GeneralSettings = Field(default_factory=GeneralSettings)
    analysis: AnalysisSettings = Field(default_factory=AnalysisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)


# ============== Settings Service ==============

class SettingsService:
    """
    Service für Settings-Management.
    
    Features:
    - Laden/Speichern von Settings
    - Validierung mit Pydantic
    - Verschlüsselung sensibler Daten
    - Export/Import
    
    Usage:
        service = SettingsService()
        settings = service.get_all_settings()
        service.save_settings(settings)
    """
    
    def __init__(self):
        """Initialisiert Settings-Service."""
        self.db = get_database()
        logger.info("SettingsService initialisiert")
    
    def get_all_settings(self) -> CompleteSettings:
        """
        Lädt alle Settings aus der Datenbank.
        
        Returns:
            CompleteSettings
        """
        db_settings = self.db.get_all_settings()
        
        # Defaults verwenden wenn keine Settings vorhanden
        general_data = db_settings.get("general", {})
        analysis_data = db_settings.get("analysis", {})
        security_data = db_settings.get("security", {})
        logging_data = db_settings.get("logging", {})
        
        settings = CompleteSettings(
            general=GeneralSettings(**general_data) if general_data else GeneralSettings(),
            analysis=AnalysisSettings(**analysis_data) if analysis_data else AnalysisSettings(),
            security=SecuritySettings(**security_data) if security_data else SecuritySettings(),
            logging=LoggingSettings(**logging_data) if logging_data else LoggingSettings(),
        )
        
        logger.debug(f"Settings geladen: {settings.model_dump()}")
        
        return settings
    
    def save_all_settings(self, settings: CompleteSettings):
        """
        Speichert alle Settings in der Datenbank.
        
        Args:
            settings: CompleteSettings
        """
        all_settings = {
            "general": settings.general.model_dump(),
            "analysis": settings.analysis.model_dump(),
            "security": settings.security.model_dump(),
            "logging": settings.logging.model_dump(),
        }
        
        # API-Keys und Passwörter verschlüsseln
        encrypted_keys = []  # Future: API-Keys
        
        self.db.set_all_settings(all_settings, encrypted_keys=encrypted_keys)
        
        logger.info("Alle Settings gespeichert")
    
    def get_category_settings(self, category: str) -> Dict[str, Any]:
        """
        Lädt Settings einer Kategorie.
        
        Args:
            category: Kategorie-Name
            
        Returns:
            Dict mit Settings
        """
        db_settings = self.db.get_all_settings()
        return db_settings.get(category, {})
    
    def save_category_settings(self, category: str, settings: Dict[str, Any]):
        """
        Speichert Settings einer Kategorie.
        
        Args:
            category: Kategorie-Name
            settings: Settings-Dict
        """
        self.db.set_all_settings({category: settings})
        logger.info(f"Settings gespeichert für Kategorie: {category}")
    
    def reset_settings(self, category: Optional[str] = None):
        """
        Setzt Settings zurück.
        
        Args:
            category: Kategorie (None = alle)
        """
        self.db.reset_settings(category=category)
        logger.info(f"Settings zurückgesetzt: {category or 'alle'}")
    
    def export_settings(self) -> str:
        """
        Exportiert Settings als JSON-String.
        
        Returns:
            JSON-String
        """
        settings = self.get_all_settings()
        return settings.model_dump_json(indent=2)
    
    def import_settings(self, json_data: str):
        """
        Importiert Settings aus JSON-String.
        
        Args:
            json_data: JSON-String
        """
        data = CompleteSettings.model_validate_json(json_data)
        self.save_all_settings(data)
        logger.info("Settings importiert")


# ============== FastAPI Router ==============

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticBaseModel

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])

service = SettingsService()


class SettingsResponse(PydanticBaseModel):
    """Response für Settings."""
    version: str
    general: GeneralSettings
    analysis: AnalysisSettings
    security: SecuritySettings
    logging: LoggingSettings


class SuccessResponse(PydanticBaseModel):
    """Response für Erfolg."""
    status: str
    message: str


@router.get("/", response_model=SettingsResponse)
async def get_all_settings():
    """Alle Settings laden."""
    try:
        settings = service.get_all_settings()
        return settings
    except Exception as e:
        logger.error(f"Fehler beim Laden der Settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/", response_model=SuccessResponse)
async def save_all_settings(settings: SettingsResponse):
    """Alle Settings speichern."""
    try:
        complete_settings = CompleteSettings(
            version=settings.version,
            general=settings.general,
            analysis=settings.analysis,
            security=settings.security,
            logging=settings.logging,
        )
        service.save_all_settings(complete_settings)
        
        return SuccessResponse(
            status="success",
            message="Settings erfolgreich gespeichert"
        )
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{category}", response_model=dict)
async def get_category_settings(category: str):
    """Settings einer Kategorie laden."""
    try:
        settings = service.get_category_settings(category)
        return settings
    except Exception as e:
        logger.error(f"Fehler beim Laden der Kategorie-Settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{category}", response_model=SuccessResponse)
async def save_category_settings(category: str, settings: dict):
    """Settings einer Kategorie speichern."""
    try:
        service.save_category_settings(category, settings)
        
        return SuccessResponse(
            status="success",
            message=f"Settings für '{category}' gespeichert"
        )
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Kategorie-Settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_settings():
    """Settings exportieren."""
    try:
        json_data = service.export_settings()
        
        from fastapi.responses import Response
        return Response(
            content=json_data,
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=glitchhunter-settings.json"
            }
        )
    except Exception as e:
        logger.error(f"Fehler beim Exportieren der Settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import", response_model=SuccessResponse)
async def import_settings(file: bytes):
    """Settings importieren."""
    try:
        json_data = file.decode("utf-8")
        service.import_settings(json_data)
        
        return SuccessResponse(
            status="success",
            message="Settings erfolgreich importiert"
        )
    except Exception as e:
        logger.error(f"Fehler beim Importieren der Settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset", response_model=SuccessResponse)
async def reset_settings(category: Optional[str] = None):
    """Settings zurücksetzen."""
    try:
        service.reset_settings(category=category)
        
        return SuccessResponse(
            status="success",
            message=f"Settings {'für ' + category if category else 'alle'} zurückgesetzt"
        )
    except Exception as e:
        logger.error(f"Fehler beim Zurücksetzen der Settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
