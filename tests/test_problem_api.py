"""
Tests für Problem-Solver API Endpoints.

Testet die REST API Endpoints gemäß PROBLEM_SOLVER.md Phase 1.3.
Parallele Struktur zu bestehenden Bug-Hunting-Tests.
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def temp_repo():
    """Erstellt temporäres Repository für Tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        # Config erstellen
        config_file = repo_path / "config.yaml"
        config_file.write_text("""
repository:
  path: {}
  
api:
  host: 0.0.0.0
  port: 8000
  debug: false

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
""".format(str(repo_path)))
        
        yield repo_path


@pytest.fixture
def client(temp_repo):
    """Erstellt TestClient mit temporärem Repository."""
    with patch('core.config.Config.load') as mock_load:
        mock_config = MagicMock()
        mock_config.repository.path = str(temp_repo)
        mock_config.api.host = "0.0.0.0"
        mock_config.api.port = 8000
        mock_config.api.debug = False
        mock_config.logging.level = "INFO"
        mock_load.return_value = mock_config
        
        from api.server import create_app
        app = create_app()
        
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture
def sample_problem(client):
    """Erstellt ein Sample Problem für Tests."""
    response = client.post(
        "/api/problems",
        json={
            "description": "Die API ist sehr langsam bei großen Datenmengen",
            "title": "API Performance Problem",
            "source": "test",
        },
    )
    return response.json()


class TestCreateProblem:
    """Tests für POST /api/problems."""
    
    def test_create_problem_basic(self, client):
        """Problem mit minimalen Feldern erstellen."""
        response = client.post(
            "/api/problems",
            json={
                "description": "Die API ist sehr langsam",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "id" in data
        assert data["id"].startswith("prob_")
        assert data["title"] == "Die API ist sehr langsam"
        assert data["raw_description"] == "Die API ist sehr langsam"
        assert data["status"] == "intake"
        assert data["source"] == "api"
    
    def test_create_problem_with_title(self, client):
        """Problem mit benutzerdefiniertem Titel."""
        response = client.post(
            "/api/problems",
            json={
                "description": "Die API ist sehr langsam",
                "title": "Custom Title",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Custom Title"
    
    def test_create_problem_with_source(self, client):
        """Problem mit benutzerdefinierter Quelle."""
        response = client.post(
            "/api/problems",
            json={
                "description": "Die API ist sehr langsam",
                "source": "custom_source",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["source"] == "custom_source"
    
    def test_create_problem_empty_description(self, client):
        """Problem mit leerer Beschreibung sollte fehlschlagen."""
        response = client.post(
            "/api/problems",
            json={
                "description": "",
            },
        )
        
        assert response.status_code == 422  # Validation Error
    
    def test_create_problem_missing_description(self, client):
        """Problem ohne Beschreibung sollte fehlschlagen."""
        response = client.post(
            "/api/problems",
            json={},
        )
        
        assert response.status_code == 422  # Validation Error


class TestListProblems:
    """Tests für GET /api/problems."""
    
    def test_list_empty(self, client):
        """Leere Problemliste."""
        response = client.get("/api/problems")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["problems"] == []
    
    def test_list_with_problems(self, client, sample_problem):
        """Liste mit Problemen."""
        response = client.get("/api/problems")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["problems"]) >= 1
    
    def test_list_filter_by_status(self, client, sample_problem):
        """Liste nach Status filtern."""
        response = client.get("/api/problems?status=intake")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for problem in data["problems"]:
            assert problem["status"] == "intake"
    
    def test_list_filter_by_type(self, client, sample_problem):
        """Liste nach Typ filtern."""
        response = client.get("/api/problems?type=performance")
        
        assert response.status_code == 200
        data = response.json()
        # Sollte nur performance Probleme zurückgeben
    
    def test_list_invalid_status_filter(self, client):
        """Liste mit ungültigem Status-Filter."""
        response = client.get("/api/problems?status=invalid_status")
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid status" in data["detail"]
    
    def test_list_invalid_type_filter(self, client):
        """Liste mit ungültigem Typ-Filter."""
        response = client.get("/api/problems?type=invalid_type")
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid type" in data["detail"]


class TestGetProblem:
    """Tests für GET /api/problems/{problem_id}."""
    
    def test_get_existing_problem(self, client, sample_problem):
        """Existierendes Problem abrufen."""
        problem_id = sample_problem["id"]
        response = client.get(f"/api/problems/{problem_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == problem_id
        assert data["title"] == sample_problem["title"]
    
    def test_get_nonexistent_problem(self, client):
        """Nicht-existierendes Problem abrufen."""
        response = client.get("/api/problems/prob_nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]


class TestClassifyProblem:
    """Tests für POST /api/problems/{problem_id}/classify."""
    
    def test_classify_existing_problem(self, client, sample_problem):
        """Existierendes Problem klassifizieren."""
        problem_id = sample_problem["id"]
        response = client.post(f"/api/problems/{problem_id}/classify")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["problem_id"] == problem_id
        assert "problem_type" in data
        assert "confidence" in data
        assert isinstance(data["confidence"], float)
        assert 0 <= data["confidence"] <= 1
        assert "recommended_actions" in data
    
    def test_classify_nonexistent_problem(self, client):
        """Nicht-existierendes Problem klassifizieren."""
        response = client.post("/api/problems/prob_nonexistent/classify")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]


class TestUpdateProblem:
    """Tests für PATCH /api/problems/{problem_id}."""
    
    def test_update_title(self, client, sample_problem):
        """Titel aktualisieren."""
        problem_id = sample_problem["id"]
        response = client.patch(
            f"/api/problems/{problem_id}",
            json={"title": "Updated Title"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["id"] == problem_id
    
    def test_update_status(self, client, sample_problem):
        """Status aktualisieren."""
        problem_id = sample_problem["id"]
        response = client.patch(
            f"/api/problems/{problem_id}",
            json={"status": "diagnosis"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "diagnosis"
    
    def test_update_multiple_fields(self, client, sample_problem):
        """Mehrere Felder aktualisieren."""
        problem_id = sample_problem["id"]
        response = client.patch(
            f"/api/problems/{problem_id}",
            json={
                "title": "New Title",
                "goal_state": "Antwortzeit unter 100ms",
                "status": "planning",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["goal_state"] == "Antwortzeit unter 100ms"
        assert data["status"] == "planning"
    
    def test_update_nonexistent_problem(self, client):
        """Nicht-existierendes Problem aktualisieren."""
        response = client.patch(
            "/api/problems/prob_nonexistent",
            json={"title": "Test"},
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]


class TestDeleteProblem:
    """Tests für DELETE /api/problems/{problem_id}."""
    
    def test_delete_existing_problem(self, client, sample_problem):
        """Existierendes Problem löschen."""
        problem_id = sample_problem["id"]
        response = client.delete(f"/api/problems/{problem_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["problem_id"] == problem_id
        
        # Verify deletion
        get_response = client.get(f"/api/problems/{problem_id}")
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_problem(self, client):
        """Nicht-existierendes Problem löschen."""
        response = client.delete("/api/problems/prob_nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]


class TestGetProblemStatistics:
    """Tests für GET /api/problems/stats."""
    
    def test_stats_empty(self, client):
        """Stats ohne Probleme."""
        response = client.get("/api/problems/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_problems"] == 0
        assert data["by_type"] == {}
        assert data["by_status"] == {}
    
    def test_stats_with_problems(self, client, sample_problem):
        """Stats mit Problemen."""
        # Zweites Problem erstellen
        client.post(
            "/api/problems",
            json={"description": "Anderes Problem"},
        )
        
        response = client.get("/api/problems/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_problems"] >= 2
        assert "by_type" in data
        assert "by_status" in data
        assert data["oldest_problem"] is not None
        assert data["newest_problem"] is not None


class TestProblemResponseSchema:
    """Tests für Response-Schema Validierung."""
    
    def test_response_schema_complete(self, client, sample_problem):
        """Response-Schema hat alle erforderlichen Felder."""
        problem_id = sample_problem["id"]
        response = client.get(f"/api/problems/{problem_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields prüfen
        required_fields = [
            "id", "title", "raw_description", "problem_type",
            "severity", "status", "created_at", "updated_at", "source"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Optional fields prüfen (sollten vorhanden sein mit Defaults)
        optional_fields = [
            "goal_state", "constraints", "affected_components",
            "success_criteria", "risk_level", "risk_factors"
        ]
        for field in optional_fields:
            assert field in data, f"Missing optional field: {field}"


class TestClassificationResultSchema:
    """Tests für ClassificationResult-Schema."""
    
    def test_classification_schema_complete(self, client, sample_problem):
        """ClassificationResult-Schema hat alle Felder."""
        problem_id = sample_problem["id"]
        response = client.post(f"/api/problems/{problem_id}/classify")
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "problem_id", "problem_type", "confidence",
            "keywords_found", "affected_components",
            "recommended_actions", "alternatives"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"


class TestIntegration:
    """Integrationstests für kompletten API-Workflow."""
    
    def test_full_api_workflow(self, client):
        """Kompletter API-Workflow."""
        # 1. Problem erstellen
        create_response = client.post(
            "/api/problems",
            json={
                "description": "Performance Problem in der API",
                "title": "API Performance",
                "source": "test",
            },
        )
        assert create_response.status_code == 201
        problem = create_response.json()
        problem_id = problem["id"]
        
        # 2. Problem abrufen
        get_response = client.get(f"/api/problems/{problem_id}")
        assert get_response.status_code == 200
        
        # 3. Problem klassifizieren
        classify_response = client.post(f"/api/problems/{problem_id}/classify")
        assert classify_response.status_code == 200
        classification = classify_response.json()
        assert classification["problem_type"] in [
            "bug", "performance", "security", "scalability",
            "maintainability", "ux_issue", "unknown"
        ]
        
        # 4. Problem aktualisieren
        update_response = client.patch(
            f"/api/problems/{problem_id}",
            json={"status": "diagnosis"},
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["status"] == "diagnosis"
        
        # 5. Stats abrufen
        stats_response = client.get("/api/problems/stats")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["total_problems"] >= 1
        
        # 6. Problem löschen
        delete_response = client.delete(f"/api/problems/{problem_id}")
        assert delete_response.status_code == 200
        
        # 7. Verify deletion
        get_deleted = client.get(f"/api/problems/{problem_id}")
        assert get_deleted.status_code == 404
    
    def test_multiple_problems_workflow(self, client):
        """Workflow mit mehreren Problemen."""
        # Mehrere Probleme erstellen
        problem_ids = []
        for i in range(3):
            response = client.post(
                "/api/problems",
                json={"description": f"Problem {i}"},
            )
            assert response.status_code == 201
            problem_ids.append(response.json()["id"])
        
        # Liste sollte alle enthalten
        list_response = client.get("/api/problems")
        assert list_response.status_code == 200
        assert list_response.json()["total"] >= 3
        
        # Alle löschen
        for problem_id in problem_ids:
            delete_response = client.delete(f"/api/problems/{problem_id}")
            assert delete_response.status_code == 200
        
        # Liste sollte leer sein
        final_list = client.get("/api/problems")
        assert final_list.json()["total"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
