"""
Report-Generator Service für GlitchHunter Web-UI.

Bietet API-Endpoints für Report-Generierung:
- Reports in verschiedenen Formaten (JSON, Markdown, HTML)
- Template-System für konsistente Reports
- Download-Funktion

Features:
- Integration mit bestehendem ReportGenerator
- Multi-Format Support
- Template-basierte Generierung
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


# ============== Models ==============

class GenerateReportRequest(BaseModel):
    """Request zum Generieren eines Reports."""
    job_id: Optional[str] = Field(None, description="Job-ID für Analyse-Report")
    problem_id: Optional[str] = Field(None, description="Problem-ID für Problem-Report")
    format: str = Field(default="markdown", description="Format: json, markdown, html")
    include_raw_data: bool = Field(default=False, description="Rohdaten einschließen")
    template: Optional[str] = Field(None, description="Template-Name")


class GenerateReportResponse(BaseModel):
    """Response nach Report-Generierung."""
    report_id: str
    format: str
    message: str
    download_url: Optional[str] = None


class ReportBundle(BaseModel):
    """Report-Daten."""
    report_id: str
    title: str
    generated_at: datetime = Field(default_factory=datetime.now)
    format: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============== Service ==============

class ReportService:
    """
    Service für Report-Generierung.
    
    Features:
    - JSON, Markdown, HTML Export
    - Template-System
    - Analyse- und Problem-Reports
    
    Usage:
        service = ReportService()
        report = await service.generate_report(request)
    """
    
    def __init__(self):
        """Initialisiert Report-Service."""
        self._reports: Dict[str, ReportBundle] = {}
        logger.info("ReportService initialisiert")
    
    async def generate_report(self, request: GenerateReportRequest) -> ReportBundle:
        """
        Generiert Report.
        
        Args:
            request: GenerateReportRequest
            
        Returns:
            ReportBundle
        """
        try:
            report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Daten laden
            data = await self._load_data(request.job_id, request.problem_id)
            
            # Report generieren basierend auf Format
            if request.format == "json":
                content = self._generate_json(data, request.include_raw_data)
            elif request.format == "markdown":
                content = self._generate_markdown(data)
            elif request.format == "html":
                content = self._generate_html(data)
            else:
                raise ValueError(f"Unbekanntes Format: {request.format}")
            
            # Report speichern
            report = ReportBundle(
                report_id=report_id,
                title=f"GlitchHunter Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                generated_at=datetime.now(),
                format=request.format,
                content=content,
                metadata={
                    "job_id": request.job_id,
                    "problem_id": request.problem_id,
                    "include_raw_data": request.include_raw_data,
                },
            )
            
            self._reports[report_id] = report
            
            return report
            
        except Exception as e:
            logger.error(f"Fehler beim Generieren des Reports: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _load_data(
        self,
        job_id: Optional[str],
        problem_id: Optional[str],
    ) -> Dict[str, Any]:
        """
        Lädt Daten für Report.
        
        Args:
            job_id: Job-ID
            problem_id: Problem-ID
            
        Returns:
            Daten-Dict
        """
        data = {
            "generated_at": datetime.now().isoformat(),
            "job_id": job_id,
            "problem_id": problem_id,
            "findings": [],
            "summary": {},
        }
        
        # Job-Daten laden (simuliert - in Produktion aus API laden)
        if job_id:
            # TODO: Echte API-Integration
            data["job"] = {
                "id": job_id,
                "repo_path": "/path/to/repo",
                "status": "completed",
                "findings_count": 0,
                "duration_seconds": 0,
            }
        
        # Problem-Daten laden (simuliert)
        if problem_id:
            # TODO: Echte API-Integration
            data["problem"] = {
                "id": problem_id,
                "prompt": "Problem description",
                "classification": "security",
                "diagnosis": "Diagnosis text",
                "solution": "Solution text",
            }
        
        return data
    
    def _generate_json(self, data: Dict[str, Any], include_raw: bool) -> str:
        """
        Generiert JSON-Report.
        
        Args:
            data: Daten
            include_raw: Rohdaten einschließen
            
        Returns:
            JSON-String
        """
        report = {
            "report": {
                "generated_at": data["generated_at"],
                "job_id": data.get("job_id"),
                "problem_id": data.get("problem_id"),
            },
            "summary": data.get("summary", {}),
            "findings": data.get("findings", []),
        }
        
        if include_raw:
            report["raw_data"] = data
        
        return json.dumps(report, indent=2, ensure_ascii=False)
    
    def _generate_markdown(self, data: Dict[str, Any]) -> str:
        """
        Generiert Markdown-Report.
        
        Args:
            data: Daten
            
        Returns:
            Markdown-String
        """
        md = []
        
        # Header
        md.append(f"# GlitchHunter Report")
        md.append(f"**Generated:** {data['generated_at']}")
        md.append("")
        
        # Job-Info
        if data.get("job"):
            job = data["job"]
            md.append(f"## Analyse-Informationen")
            md.append(f"- **Job-ID:** {job.get('id', 'N/A')}")
            md.append(f"- **Repository:** {job.get('repo_path', 'N/A')}")
            md.append(f"- **Status:** {job.get('status', 'N/A')}")
            md.append(f"- **Findings:** {job.get('findings_count', 0)}")
            md.append(f"- **Dauer:** {job.get('duration_seconds', 0):.2f}s")
            md.append("")
        
        # Problem-Info
        if data.get("problem"):
            problem = data["problem"]
            md.append(f"## Problem-Analyse")
            md.append(f"- **Problem-ID:** {problem.get('id', 'N/A')}")
            md.append(f"- **Klassifikation:** {problem.get('classification', 'N/A')}")
            md.append("")
            md.append(f"### Diagnose")
            md.append(problem.get('diagnosis', 'N/A'))
            md.append("")
            md.append(f"### Lösung")
            md.append(problem.get('solution', 'N/A'))
            md.append("")
        
        # Findings
        md.append(f"## Findings")
        findings = data.get("findings", [])
        if findings:
            for i, finding in enumerate(findings, 1):
                md.append(f"### {i}. {finding.get('title', 'Finding')}")
                md.append(f"**Severity:** {finding.get('severity', 'N/A')}")
                md.append(f"**File:** {finding.get('file_path', 'N/A')}:{finding.get('line_start', 0)}")
                md.append(f"**Confidence:** {finding.get('confidence', 0) * 100:.0f}%")
                md.append("")
                md.append(finding.get('description', 'N/A'))
                md.append("")
        else:
            md.append("Keine Findings gefunden.")
            md.append("")
        
        # Footer
        md.append("---")
        md.append(f"*Report generated by GlitchHunter v3.0*")
        
        return "\n".join(md)
    
    def _generate_html(self, data: Dict[str, Any]) -> str:
        """
        Generiert HTML-Report.
        
        Args:
            data: Daten
            
        Returns:
            HTML-String
        """
        markdown = self._generate_markdown(data)
        
        # Einfache Markdown-zu-HTML-Konvertierung
        html_content = markdown
        html_content = html_content.replace("# ", "<h1>")
        html_content = html_content.replace("\n# ", "\n</h1><h1>")
        html_content = html_content.replace("## ", "<h2>")
        html_content = html_content.replace("\n## ", "\n</h2><h2>")
        html_content = html_content.replace("### ", "<h3>")
        html_content = html_content.replace("\n### ", "\n</h3><h3>")
        html_content = html_content.replace("**", "</strong>")
        html_content = html_content.replace("**", "<strong>")
        html_content = html_content.replace("\n---", "</div>")
        html_content = html_content.replace("\n", "<br>")
        
        html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GlitchHunter Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
            color: #333;
        }}
        h1 {{ color: #8b7355; border-bottom: 2px solid #d4c4a8; padding-bottom: 10px; }}
        h2 {{ color: #8b7355; margin-top: 30px; }}
        h3 {{ color: #a09070; }}
        .metadata {{ background: #f9f9f9; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .finding {{ background: #fff; border-left: 4px solid #d4c4a8; padding: 15px; margin: 20px 0; }}
        .finding.critical {{ border-left-color: #ef4444; }}
        .finding.high {{ border-left-color: #f59e0b; }}
        .finding.medium {{ border-left-color: #3b82f6; }}
        .finding.low {{ border-left-color: #10b981; }}
        footer {{ margin-top: 40px; padding-top: 20px; border-top: 2px solid #e0e0e0; color: #666; }}
    </style>
</head>
<body>
    {html_content}
    <footer>
        <p><em>Report generated by GlitchHunter v3.0</em></p>
    </footer>
</body>
</html>"""
        
        return html
    
    def get_report(self, report_id: str) -> Optional[ReportBundle]:
        """
        Holt Report nach ID.
        
        Args:
            report_id: Report-ID
            
        Returns:
            ReportBundle oder None
        """
        return self._reports.get(report_id)
    
    def list_reports(self) -> List[ReportBundle]:
        """
        Listet alle Reports.
        
        Returns:
            Liste von ReportBundle
        """
        return list(self._reports.values())
    
    def delete_report(self, report_id: str) -> bool:
        """
        Löscht Report.
        
        Args:
            report_id: Report-ID
            
        Returns:
            True wenn erfolgreich
        """
        if report_id in self._reports:
            del self._reports[report_id]
            return True
        return False


# ============== Router ==============

service = ReportService()


@router.post("/generate", response_model=GenerateReportResponse)
async def generate_report(request: GenerateReportRequest):
    """Report generieren."""
    report = await service.generate_report(request)
    
    return GenerateReportResponse(
        report_id=report.report_id,
        format=report.format,
        message=f"Report im Format '{report.format}' generiert",
        download_url=f"/api/v1/reports/{report.report_id}/download",
    )


@router.get("", response_model=List[ReportBundle])
async def list_reports():
    """Alle Reports auflisten."""
    return service.list_reports()


@router.get("/{report_id}", response_model=ReportBundle)
async def get_report(report_id: str):
    """Report-Details abrufen."""
    report = service.get_report(report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report nicht gefunden")
    
    return report


@router.get("/{report_id}/download")
async def download_report(report_id: str):
    """Report herunterladen."""
    report = service.get_report(report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report nicht gefunden")
    
    filename = f"glitchhunter-report-{report.report_id}.{report.format}"
    
    if report.format == "json":
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=json.loads(report.content),
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    elif report.format == "markdown":
        return PlainTextResponse(
            content=report.content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    elif report.format == "html":
        return HTMLResponse(
            content=report.content,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )


@router.delete("/{report_id}")
async def delete_report(report_id: str):
    """Report löschen."""
    success = service.delete_report(report_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Report nicht gefunden")
    
    return {"status": "success", "message": "Report gelöscht"}
