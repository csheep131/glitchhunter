"""
Tests für GlitchHunter Web-UI Phase 2 Features.

Testet:
- Problem-Solver Service
- Report-Generator Service
- History Manager
- API-Endpoints
"""

import asyncio
import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Test-Fixtures

@pytest.fixture
def sample_problem_request():
    """Sample Problem-Solve-Request."""
    return {
        "prompt": "Finde Security-Issues in auth.py",
        "repo_path": "/test/repo",
        "with_ml_prediction": True,
        "with_code_analysis": True,
        "auto_fix": False,
        "stack": "stack_b",
    }


@pytest.fixture
def sample_report_request():
    """Sample Report-Generate-Request."""
    return {
        "job_id": "test_job_123",
        "problem_id": None,
        "format": "markdown",
        "include_raw_data": False,
        "template": None,
    }


@pytest.fixture
def sample_analysis_entry():
    """Sample Analysis-History-Eintrag."""
    return {
        "job_id": "test_job_123",
        "repo_path": "/test/repo",
        "stack": "stack_b",
        "status": "completed",
        "findings_count": 5,
        "critical_count": 1,
        "high_count": 2,
        "medium_count": 1,
        "low_count": 1,
        "duration_seconds": 45.5,
        "parallelization_factor": 2.5,
    }


# ============== Problem-Solver Tests ==============

class TestProblemSolver:
    """Tests für Problem-Solver Service."""

    @pytest.mark.asyncio
    async def test_solve_problem_basic(self, sample_problem_request):
        """Test grundlegende Problemlösung."""
        from ui.web.backend.problem_solver import ProblemSolverService
        
        service = ProblemSolverService()
        problem_id = await service.solve_problem(
            MagicMock(**sample_problem_request)
        )
        
        assert problem_id is not None
        assert problem_id.startswith("problem_")
    
    @pytest.mark.asyncio
    async def test_get_problem_result(self, sample_problem_request):
        """Test Ergebnis-Abruf."""
        from ui.web.backend.problem_solver import ProblemSolverService
        
        service = ProblemSolverService()
        problem_id = await service.solve_problem(
            MagicMock(**sample_problem_request)
        )
        
        result = service.get_problem(problem_id)
        
        assert result is not None
        assert result.problem_id == problem_id
        assert result.prompt == sample_problem_request["prompt"]
    
    @pytest.mark.asyncio
    async def test_get_problem_history(self, sample_problem_request):
        """Test Historien-Abruf."""
        from ui.web.backend.problem_solver import ProblemSolverService
        
        service = ProblemSolverService()
        
        # Mehrere Probleme erstellen
        for i in range(5):
            request = MagicMock(**sample_problem_request)
            request.prompt = f"Problem {i}"
            await service.solve_problem(request)
        
        history = service.get_history(limit=10)
        
        assert len(history) == 5
        assert all(isinstance(h, dict) for h in history)


# ============== Report-Generator Tests ==============

class TestReportGenerator:
    """Tests für Report-Generator Service."""

    @pytest.mark.asyncio
    async def test_generate_json_report(self, sample_report_request):
        """Test JSON-Report-Generierung."""
        from ui.web.backend.reports import ReportService
        
        service = ReportService()
        request = MagicMock(**sample_report_request)
        request.format = "json"
        
        report = await service.generate_report(request)
        
        assert report is not None
        assert report.format == "json"
        assert report.content.startswith("{")
    
    @pytest.mark.asyncio
    async def test_generate_markdown_report(self, sample_report_request):
        """Test Markdown-Report-Generierung."""
        from ui.web.backend.reports import ReportService
        
        service = ReportService()
        request = MagicMock(**sample_report_request)
        request.format = "markdown"
        
        report = await service.generate_report(request)
        
        assert report is not None
        assert report.format == "markdown"
        assert "# GlitchHunter Report" in report.content
    
    @pytest.mark.asyncio
    async def test_generate_html_report(self, sample_report_request):
        """Test HTML-Report-Generierung."""
        from ui.web.backend.reports import ReportService
        
        service = ReportService()
        request = MagicMock(**sample_report_request)
        request.format = "html"
        
        report = await service.generate_report(request)
        
        assert report is not None
        assert report.format == "html"
        assert "<!DOCTYPE html>" in report.content
        assert "<h1>" in report.content
    
    def test_report_storage(self, sample_report_request):
        """Test Report-Speicherung."""
        from ui.web.backend.reports import ReportService
        
        service = ReportService()
        request = MagicMock(**sample_report_request)
        
        # Report generieren und speichern
        report = asyncio.run(service.generate_report(request))
        
        # Report abrufen
        retrieved = service.get_report(report.report_id)
        
        assert retrieved is not None
        assert retrieved.report_id == report.report_id
    
    def test_report_list(self, sample_report_request):
        """Test Report-Liste."""
        from ui.web.backend.reports import ReportService
        
        service = ReportService()
        
        # Mehrere Reports erstellen
        for i in range(3):
            request = MagicMock(**sample_report_request)
            asyncio.run(service.generate_report(request))
        
        reports = service.list_reports()
        
        assert len(reports) == 3
    
    def test_report_delete(self, sample_report_request):
        """Test Report-Löschen."""
        from ui.web.backend.reports import ReportService
        
        service = ReportService()
        request = MagicMock(**sample_report_request)
        
        # Report erstellen
        report = asyncio.run(service.generate_report(request))
        
        # Löschen
        success = service.delete_report(report.report_id)
        
        assert success is True
        assert service.get_report(report.report_id) is None


# ============== History Manager Tests ==============

class TestHistoryManager:
    """Tests für History Manager."""

    @pytest.fixture
    def history_manager(self):
        """History-Manager Fixture."""
        from ui.web.backend.history import HistoryManager
        
        manager = HistoryManager(db_path=":memory:")
        manager.initialize()
        return manager

    def test_add_analysis_entry(self, history_manager, sample_analysis_entry):
        """Test Analyse-Eintrag hinzufügen."""
        history_manager.add_analysis_entry(**sample_analysis_entry)
        
        entry = history_manager.get_analysis_entry(sample_analysis_entry["job_id"])
        
        assert entry is not None
        assert entry["job_id"] == sample_analysis_entry["job_id"]
        assert entry["findings_count"] == 5
    
    def test_get_analysis_history(self, history_manager, sample_analysis_entry):
        """Test Analyse-History-Abruf."""
        # Mehrere Einträge hinzufügen
        for i in range(10):
            entry = sample_analysis_entry.copy()
            entry["job_id"] = f"job_{i}"
            history_manager.add_analysis_entry(**entry)
        
        history = history_manager.get_analysis_history(limit=5)
        
        assert len(history) == 5
        assert all(isinstance(h, dict) for h in history)
    
    def test_analysis_history_filter(self, history_manager, sample_analysis_entry):
        """Test Analyse-History-Filter."""
        # Einträge mit unterschiedlichen Status
        for status in ["completed", "running", "failed"]:
            entry = sample_analysis_entry.copy()
            entry["job_id"] = f"job_{status}"
            entry["status"] = status
            history_manager.add_analysis_entry(**entry)
        
        # Nach Status filtern
        history = history_manager.get_analysis_history(status_filter="completed")
        
        assert len(history) == 1
        assert history[0]["status"] == "completed"
    
    def test_add_problem_entry(self, history_manager):
        """Test Problem-Eintrag hinzufügen."""
        history_manager.add_problem_entry(
            problem_id="problem_123",
            prompt="Test problem",
            status="completed",
            classification="security",
            with_ml_prediction=True,
            duration_seconds=30.0,
        )
        
        history = history_manager.get_problem_history(limit=10)
        
        assert len(history) == 1
        assert history[0]["problem_id"] == "problem_123"
    
    def test_add_report_entry(self, history_manager):
        """Test Report-Eintrag hinzufügen."""
        history_manager.add_report_entry(
            report_id="report_123",
            format="markdown",
            job_id="job_123",
            file_size=1024,
        )
        
        history = history_manager.get_report_history(limit=10)
        
        assert len(history) == 1
        assert history[0]["format"] == "markdown"
    
    def test_statistics(self, history_manager, sample_analysis_entry):
        """Test Statistik-Abruf."""
        # Einträge hinzufügen
        for i in range(5):
            entry = sample_analysis_entry.copy()
            entry["job_id"] = f"job_{i}"
            history_manager.add_analysis_entry(**entry)
        
        stats = history_manager.get_statistics(days=30)
        
        assert "analysis" in stats
        assert "problems" in stats
        assert "reports" in stats
        assert stats["analysis"]["total_analyses"] == 5
    
    def test_daily_stats(self, history_manager, sample_analysis_entry):
        """Test tägliche Statistiken."""
        # Einträge hinzufügen
        for i in range(7):
            entry = sample_analysis_entry.copy()
            entry["job_id"] = f"job_{i}"
            history_manager.add_analysis_entry(**entry)
        
        stats = history_manager.get_daily_stats(days=7)
        
        assert len(stats) > 0
        assert "date" in stats[0]
        assert "total_analyses" in stats[0]
    
    def test_cleanup(self, history_manager, sample_analysis_entry):
        """Test Bereinigung."""
        # Einträge hinzufügen
        for i in range(10):
            entry = sample_analysis_entry.copy()
            entry["job_id"] = f"job_{i}"
            history_manager.add_analysis_entry(**entry)
        
        # Bereinigen (alle löschen da in-memory)
        history_manager.cleanup(older_than_days=0)
        
        history = history_manager.get_analysis_history()
        assert len(history) == 0
    
    def test_clear_all(self, history_manager, sample_analysis_entry):
        """Test Komplettes Löschen."""
        # Einträge hinzufügen
        for i in range(5):
            entry = sample_analysis_entry.copy()
            entry["job_id"] = f"job_{i}"
            history_manager.add_analysis_entry(**entry)
        
        # Alles löschen
        history_manager.clear_all()
        
        history = history_manager.get_analysis_history()
        assert len(history) == 0


# ============== API Endpoint Tests ==============

class TestAPIEndpoints:
    """Tests für API-Endpoints."""

    @pytest.mark.asyncio
    async def test_history_analysis_endpoint(self):
        """Test History-Analyse-Endpoint."""
        from fastapi.testclient import TestClient
        from ui.web.backend.app import app
        
        client = TestClient(app)
        response = client.get("/api/v1/history/analysis?limit=10")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    @pytest.mark.asyncio
    async def test_history_statistics_endpoint(self):
        """Test History-Statistik-Endpoint."""
        from fastapi.testclient import TestClient
        from ui.web.backend.app import app
        
        client = TestClient(app)
        response = client.get("/api/v1/history/statistics?days=30")
        
        assert response.status_code == 200
        data = response.json()
        assert "analysis" in data
        assert "problems" in data
        assert "reports" in data
    
    @pytest.mark.asyncio
    async def test_history_daily_stats_endpoint(self):
        """Test History-Täglich-Statistik-Endpoint."""
        from fastapi.testclient import TestClient
        from ui.web.backend.app import app
        
        client = TestClient(app)
        response = client.get("/api/v1/history/daily-stats?days=7")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ============== Integration Tests ==============

class TestIntegration:
    """Integration-Tests für Phase 2."""

    @pytest.mark.asyncio
    async def test_full_problem_flow(self, sample_problem_request):
        """Test kompletter Problem-Lösungs-Flow."""
        from ui.web.backend.problem_solver import ProblemSolverService
        
        service = ProblemSolverService()
        
        # Problem lösen
        problem_id = await service.solve_problem(
            MagicMock(**sample_problem_request)
        )
        
        # Ergebnis abrufen
        result = service.get_problem(problem_id)
        
        assert result is not None
        assert result.problem_id == problem_id
    
    @pytest.mark.asyncio
    async def test_full_report_flow(self, sample_report_request):
        """Test kompletter Report-Generierungs-Flow."""
        from ui.web.backend.reports import ReportService
        
        service = ReportService()
        request = MagicMock(**sample_report_request)
        
        # Report generieren
        report = await service.generate_report(request)
        
        # Report abrufen
        retrieved = service.get_report(report.report_id)
        
        assert retrieved is not None
        assert retrieved.format == report.format
    
    @pytest.mark.asyncio
    async def test_full_history_flow(self, sample_analysis_entry):
        """Test kompletter History-Flow."""
        from ui.web.backend.history import HistoryManager
        
        manager = HistoryManager(db_path=":memory:")
        manager.initialize()
        
        # Eintrag hinzufügen
        manager.add_analysis_entry(**sample_analysis_entry)
        
        # History abrufen
        history = manager.get_analysis_history()
        
        assert len(history) == 1
        assert history[0]["job_id"] == sample_analysis_entry["job_id"]
        
        # Statistik abrufen
        stats = manager.get_statistics(days=30)
        
        assert stats["analysis"]["total_analyses"] == 1


# ============== Performance Tests ==============

class TestPerformance:
    """Performance-Tests für Phase 2."""

    @pytest.mark.asyncio
    async def test_problem_solver_performance(self, sample_problem_request):
        """Test Problem-Solver-Performance."""
        from ui.web.backend.problem_solver import ProblemSolverService
        import time
        
        service = ProblemSolverService()
        
        start = time.time()
        
        # 10 Probleme lösen
        for i in range(10):
            request = MagicMock(**sample_problem_request)
            request.prompt = f"Problem {i}"
            await service.solve_problem(request)
        
        elapsed = time.time() - start
        
        # Sollte weniger als 5 Sekunden dauern
        assert elapsed < 5.0
    
    @pytest.mark.asyncio
    async def test_report_generator_performance(self, sample_report_request):
        """Test Report-Generator-Performance."""
        from ui.web.backend.reports import ReportService
        import time
        
        service = ReportService()
        
        start = time.time()
        
        # 10 Reports generieren
        for i in range(10):
            request = MagicMock(**sample_report_request)
            await service.generate_report(request)
        
        elapsed = time.time() - start
        
        # Sollte weniger als 3 Sekunden dauern
        assert elapsed < 3.0
    
    @pytest.mark.asyncio
    async def test_history_manager_performance(self, sample_analysis_entry):
        """Test History-Manager-Performance."""
        from ui.web.backend.history import HistoryManager
        import time
        
        manager = HistoryManager(db_path=":memory:")
        manager.initialize()
        
        start = time.time()
        
        # 100 Einträge hinzufügen
        for i in range(100):
            entry = sample_analysis_entry.copy()
            entry["job_id"] = f"job_{i}"
            manager.add_analysis_entry(**entry)
        
        # History abrufen
        history = manager.get_analysis_history(limit=50)
        
        elapsed = time.time() - start
        
        # Sollte weniger als 2 Sekunden dauern
        assert elapsed < 2.0
        assert len(history) == 50


# ============== Run Tests ==============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
