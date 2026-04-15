"""
Tests für Ensemble Coordinator mit llama-cpp Integration.

Unit tests für ModelLoader, EnsembleCoordinator und parallele Analysen.
Verwendet Mock-Objekte statt echte GGUF-Dateien zu laden.
"""

import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from escalation.ensemble_coordinator import (
    EnsembleCoordinator,
    EnsembleResult,
    ModelConfig,
    ModelLoader,
    ModelResponse,
)


class TestModelConfig:
    """Test cases für ModelConfig."""

    def test_from_dict_complete(self) -> None:
        """Test ModelConfig.from_dict mit vollständigen Daten."""
        data = {
            "name": "qwen3.5-9b",
            "path": "/models/qwen.gguf",
            "context_length": 8192,
            "n_gpu_layers": 35,
            "n_threads": 8,
            "n_batch": 512,
        }

        config = ModelConfig.from_dict(data)

        assert config.name == "qwen3.5-9b"
        assert config.path == "/models/qwen.gguf"
        assert config.context_length == 8192
        assert config.n_gpu_layers == 35
        assert config.n_threads == 8
        assert config.n_batch == 512

    def test_from_dict_defaults(self) -> None:
        """Test ModelConfig.from_dict mit Default-Werten."""
        data = {
            "name": "test-model",
            "path": "/models/test.gguf",
        }

        config = ModelConfig.from_dict(data)

        assert config.name == "test-model"
        assert config.path == "/models/test.gguf"
        assert config.context_length == 4096  # Default
        assert config.n_gpu_layers == 0  # Default
        assert config.n_threads == 4  # Default
        assert config.n_batch == 512  # Default


class TestModelLoader:
    """Test cases für ModelLoader Singleton."""

    def setup_method(self) -> None:
        """Setup für jede Test-Methode."""
        # Clean up singleton state before each test
        ModelLoader._models = {}
        ModelLoader._model_metadata = {}
        ModelLoader._instance = None

    def test_singleton_instance(self) -> None:
        """Test dass ModelLoader Singleton funktioniert."""
        loader1 = ModelLoader()
        loader2 = ModelLoader()

        assert loader1 is loader2

    def test_singleton_thread_safety(self) -> None:
        """Test Thread-Safety des Singletons."""
        instances = []
        lock = threading.Lock()

        def create_instance() -> None:
            instance = ModelLoader()
            with lock:
                instances.append(instance)

        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Alle Instanzen sollten identisch sein
        assert all(instance is instances[0] for instance in instances)

    @patch("escalation.ensemble_coordinator.Path")
    @patch("escalation.ensemble_coordinator.Llama")
    def test_get_model_loads_new(self, mock_llama: MagicMock, mock_path_cls: MagicMock) -> None:
        """Test dass get_model ein neues Modell lädt."""
        mock_model = MagicMock()
        mock_llama.return_value = mock_model
        
        # Mock Path.exists() return True
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_cls.return_value = mock_path_instance

        model = ModelLoader.get_model(
            model_path="/test/model.gguf",
            n_gpu_layers=35,
            n_threads=8,
        )

        assert model is mock_model
        mock_llama.assert_called_once()
        assert "/test/model.gguf" in ModelLoader._models

    @patch("escalation.ensemble_coordinator.Path")
    @patch("escalation.ensemble_coordinator.Llama")
    def test_get_model_returns_cached(self, mock_llama: MagicMock, mock_path_cls: MagicMock) -> None:
        """Test dass get_model cachedes Modell zurückgibt."""
        mock_model = MagicMock()
        mock_llama.return_value = mock_model
        
        # Mock Path.exists() return True
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_cls.return_value = mock_path_instance

        # Erster Aufruf lädt
        model1 = ModelLoader.get_model("/test/model.gguf")
        # Zweiter Aufruf verwendet Cache
        model2 = ModelLoader.get_model("/test/model.gguf")

        assert model1 is model2
        mock_llama.assert_called_once()  # Nur einmal aufgerufen

    @patch("escalation.ensemble_coordinator.Llama")
    def test_get_model_file_not_found(self, mock_llama: MagicMock) -> None:
        """Test FileNotFoundError bei nicht existierender Datei."""
        from pathlib import Path

        # Patch Path.exists um FileNotFoundError zu simulieren
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                ModelLoader.get_model("/nonexistent/model.gguf")

    @patch("escalation.ensemble_coordinator.Path")
    @patch("escalation.ensemble_coordinator.Llama")
    def test_get_model_runtime_error(self, mock_llama: MagicMock, mock_path_cls: MagicMock) -> None:
        """Test RuntimeError bei Ladefehler."""
        # Mock Path.exists() return True
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_cls.return_value = mock_path_instance
        
        mock_llama.side_effect = RuntimeError("GPU OOM")

        with pytest.raises(RuntimeError):
            ModelLoader.get_model("/test/model.gguf")

    def test_unload_model(self) -> None:
        """Test unload_model."""
        ModelLoader._models["/test/model.gguf"] = MagicMock()
        ModelLoader._model_metadata["/test/model.gguf"] = {"test": "data"}

        result = ModelLoader.unload_model("/test/model.gguf")

        assert result is True
        assert "/test/model.gguf" not in ModelLoader._models
        assert "/test/model.gguf" not in ModelLoader._model_metadata

    def test_unload_model_not_found(self) -> None:
        """Test unload_model für nicht existierendes Modell."""
        result = ModelLoader.unload_model("/nonexistent/model.gguf")

        assert result is False

    def test_unload_all(self) -> None:
        """Test unload_all."""
        ModelLoader._models["/test/model1.gguf"] = MagicMock()
        ModelLoader._models["/test/model2.gguf"] = MagicMock()
        ModelLoader._model_metadata["/test/model1.gguf"] = {}
        ModelLoader._model_metadata["/test/model2.gguf"] = {}

        ModelLoader.unload_all()

        assert len(ModelLoader._models) == 0
        assert len(ModelLoader._model_metadata) == 0

    def test_get_loaded_models(self) -> None:
        """Test get_loaded_models."""
        ModelLoader._models["/test/model1.gguf"] = MagicMock()
        ModelLoader._models["/test/model2.gguf"] = MagicMock()

        models = ModelLoader.get_loaded_models()

        assert len(models) == 2
        assert "/test/model1.gguf" in models
        assert "/test/model2.gguf" in models

    def test_is_model_loaded(self) -> None:
        """Test is_model_loaded."""
        ModelLoader._models["/test/model.gguf"] = MagicMock()

        assert ModelLoader.is_model_loaded("/test/model.gguf") is True
        assert ModelLoader.is_model_loaded("/test/other.gguf") is False


class TestModelResponse:
    """Test cases für ModelResponse."""

    def test_to_dict(self) -> None:
        """Test ModelResponse.to_dict."""
        response = ModelResponse(
            model_id="test-model",
            hypothesis="Test hypothesis",
            confidence=0.85,
            reasoning="Test reasoning",
            patch_suggestion="Test patch",
            response_time_ms=123.45,
            metadata={"key": "value"},
        )

        result = response.to_dict()

        assert result["model_id"] == "test-model"
        assert result["hypothesis"] == "Test hypothesis"
        assert result["confidence"] == 0.85
        assert result["reasoning"] == "Test reasoning"
        assert result["patch_suggestion"] == "Test patch"
        assert result["response_time_ms"] == 123.45
        assert result["metadata"] == {"key": "value"}


class TestEnsembleResult:
    """Test cases für EnsembleResult."""

    def test_to_dict(self) -> None:
        """Test EnsembleResult.to_dict."""
        response = ModelResponse(
            model_id="test-model",
            hypothesis="Test",
            confidence=0.8,
        )

        result = EnsembleResult(
            winning_hypothesis="Test",
            votes={"Test": 2},
            agreement_level="majority",
            models_used=["model1", "model2"],
            total_models=2,
            all_responses=[response],
        )

        data = result.to_dict()

        assert data["winning_hypothesis"] == "Test"
        assert data["votes"] == {"Test": 2}
        assert data["agreement_level"] == "majority"
        assert data["models_used"] == ["model1", "model2"]
        assert data["total_models"] == 2
        assert len(data["all_responses"]) == 1


class MockConfig:
    """Mock Config für Tests."""

    def __init__(self, stack_name: str = "stack_a") -> None:
        self.stack_name = stack_name
        self._models = {
            "stack_a": {
                "primary": {
                    "name": "qwen3.5-9b",
                    "path": "/test/models/qwen.gguf",
                    "context_length": 8192,
                    "n_gpu_layers": 35,
                    "n_threads": 8,
                    "n_batch": 512,
                },
                "secondary": {
                    "name": "phi-4-mini",
                    "path": "/test/models/phi.gguf",
                    "context_length": 4096,
                    "n_gpu_layers": 25,
                    "n_threads": 6,
                    "n_batch": 512,
                },
            },
            "stack_b": {
                "primary": {
                    "name": "qwen3.5-27b",
                    "path": "/test/models/qwen27b.gguf",
                    "context_length": 16384,
                    "n_gpu_layers": 50,
                    "n_threads": 12,
                    "n_batch": 512,
                },
            },
        }

    def get_hardware_profile(self, stack_name: str) -> Any:
        """Mock get_hardware_profile."""
        mock_profile = MagicMock()
        mock_profile.models = self._models.get(stack_name, {})
        return mock_profile


class TestEnsembleCoordinator:
    """Test cases für EnsembleCoordinator."""

    def setup_method(self) -> None:
        """Setup für jede Test-Methode."""
        ModelLoader._models = {}
        ModelLoader._model_metadata = {}
        ModelLoader._instance = None

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_init(self, mock_get_model: MagicMock) -> None:
        """Test Initialisierung."""
        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config, stack_name="stack_a")

        assert coordinator.config is config
        assert coordinator.stack_name == "stack_a"
        assert coordinator.models == ["primary", "secondary"]

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_get_model_config(self, mock_get_model: MagicMock) -> None:
        """Test _get_model_config."""
        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config, stack_name="stack_a")

        model_config = coordinator._get_model_config("primary")

        assert model_config.name == "qwen3.5-9b"
        assert model_config.path == "/test/models/qwen.gguf"
        assert model_config.n_gpu_layers == 35
        assert model_config.n_threads == 8

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_get_model_config_not_found(self, mock_get_model: MagicMock) -> None:
        """Test _get_model_config für unbekanntes Modell."""
        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config, stack_name="stack_a")

        with pytest.raises(ValueError):
            coordinator._get_model_config("unknown_model")

    def test_get_model_config_no_config(self) -> None:
        """Test _get_model_config ohne Config."""
        coordinator = EnsembleCoordinator(config=None)

        with pytest.raises(ValueError):
            coordinator._get_model_config("primary")

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_create_analysis_prompt(self, mock_get_model: MagicMock) -> None:
        """Test _create_analysis_prompt."""
        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        bug = {
            "bug_id": "BUG-001",
            "bug_type": "null_pointer",
            "file_path": "/src/main.py",
            "line_number": 42,
            "description": "Null pointer exception in user service",
            "code_snippet": "user.getName().toString()",
        }

        prompt = coordinator._create_analysis_prompt(bug)

        assert "BUG-001" in prompt
        assert "null_pointer" in prompt
        assert "/src/main.py" in prompt
        assert "42" in prompt
        assert "Null pointer exception" in prompt
        assert "user.getName().toString()" in prompt

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_parse_model_response_structured(
        self, mock_get_model: MagicMock
    ) -> None:
        """Test _parse_model_response mit strukturiertem Format."""
        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        response_text = """HYPOTHESE: Null pointer in user service
URSACHE: User object is null when not authenticated
BETROFFEN: UserService, AuthController
LÖSUNG: Add null check before accessing user"""

        result = coordinator._parse_model_response(response_text, {})

        assert "Null pointer" in result["hypothesis"]
        assert "User object" in result["reasoning"]
        assert "Add null check" in result["patch_suggestion"]
        assert result["confidence"] == 0.8  # Vollständig strukturiert

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_parse_model_response_unstructured(
        self, mock_get_model: MagicMock
    ) -> None:
        """Test _parse_model_response mit unstrukturiertem Format."""
        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        response_text = "This is an unstructured response text without sections."

        result = coordinator._parse_model_response(response_text, {})

        assert "This is an unstructured" in result["hypothesis"]
        assert result["confidence"] == 0.6  # Nur Hypothese

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_parse_model_response_partial(self, mock_get_model: MagicMock) -> None:
        """Test _parse_model_response mit teilweise strukturiertem Format."""
        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        response_text = """HYPOTHESE: Memory leak detected
URSACHE: Resources not properly released"""

        result = coordinator._parse_model_response(response_text, {})

        assert "Memory leak" in result["hypothesis"]
        assert "Resources" in result["reasoning"]
        assert result["confidence"] == 0.7  # Hypothese + Reasoning

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_perform_voting(self, mock_get_model: MagicMock) -> None:
        """Test _perform_voting."""
        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        responses = [
            ModelResponse(
                model_id="model1",
                hypothesis="Hypothesis A",
                confidence=0.8,
            ),
            ModelResponse(
                model_id="model2",
                hypothesis="Hypothesis A",
                confidence=0.7,
            ),
            ModelResponse(
                model_id="model3",
                hypothesis="Hypothesis B",
                confidence=0.9,
            ),
        ]

        votes = coordinator._perform_voting(responses)

        assert votes == {"Hypothesis A": 2, "Hypothesis B": 1}

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_perform_voting_skip_empty(self, mock_get_model: MagicMock) -> None:
        """Test _perform_voting überspringt leere Hypothesen."""
        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        responses = [
            ModelResponse(
                model_id="model1",
                hypothesis="Hypothesis A",
                confidence=0.8,
            ),
            ModelResponse(
                model_id="model2",
                hypothesis="",  # Leer
                confidence=0.0,
            ),
        ]

        votes = coordinator._perform_voting(responses)

        assert votes == {"Hypothesis A": 1}

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_get_winning_hypothesis(self, mock_get_model: MagicMock) -> None:
        """Test _get_winning_hypothesis."""
        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        votes = {"Hypothesis A": 2, "Hypothesis B": 1}
        winner = coordinator._get_winning_hypothesis(votes)

        assert winner == "Hypothesis A"

    def test_get_winning_hypothesis_empty(self) -> None:
        """Test _get_winning_hypothesis mit leeren Votes."""
        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        winner = coordinator._get_winning_hypothesis({})

        assert winner == ""

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_calculate_agreement_unanimous(self, mock_get_model: MagicMock) -> None:
        """Test _calculate_agreement - einstimmig."""
        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        votes = {"Hypothesis A": 3}
        agreement = coordinator._calculate_agreement(votes, 3)

        assert agreement == coordinator.AGREEMENT_UNANIMOUS

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_calculate_agreement_majority(self, mock_get_model: MagicMock) -> None:
        """Test _calculate_agreement - Mehrheit."""
        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        votes = {"Hypothesis A": 2, "Hypothesis B": 1}
        agreement = coordinator._calculate_agreement(votes, 3)

        assert agreement == coordinator.AGREEMENT_MAJORITY

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_calculate_agreement_plurality(self, mock_get_model: MagicMock) -> None:
        """Test _calculate_agreement - Pluralität."""
        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        votes = {"Hypothesis A": 2, "Hypothesis B": 1, "Hypothesis C": 1}
        agreement = coordinator._calculate_agreement(votes, 4)

        assert agreement == coordinator.AGREEMENT_PLURALITY

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_calculate_agreement_none(self, mock_get_model: MagicMock) -> None:
        """Test _calculate_agreement - keine Übereinstimmung."""
        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        votes = {"Hypothesis A": 1, "Hypothesis B": 1, "Hypothesis C": 1}
        agreement = coordinator._calculate_agreement(votes, 3)

        assert agreement == coordinator.AGREEMENT_NONE

    def test_calculate_agreement_empty(self) -> None:
        """Test _calculate_agreement mit leeren Daten."""
        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        agreement = coordinator._calculate_agreement({}, 0)

        assert agreement == coordinator.AGREEMENT_NONE

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_get_weighted_voting(self, mock_get_model: MagicMock) -> None:
        """Test get_weighted_voting."""
        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        responses = [
            ModelResponse(
                model_id="model1",
                hypothesis="Hypothesis A",
                confidence=0.8,
            ),
            ModelResponse(
                model_id="model2",
                hypothesis="Hypothesis A",
                confidence=0.7,
            ),
            ModelResponse(
                model_id="model3",
                hypothesis="Hypothesis B",
                confidence=0.9,
            ),
        ]

        weighted = coordinator.get_weighted_voting(responses)

        assert weighted["Hypothesis A"] == 1.5  # 0.8 + 0.7
        assert weighted["Hypothesis B"] == 0.9

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    @patch("escalation.ensemble_coordinator.time")
    def test_run_parallel_analyses_success(
        self, mock_time: MagicMock, mock_get_model: MagicMock
    ) -> None:
        """Test _run_parallel_analyses mit erfolgreichen Analysen."""
        # Mock time für konsistente Messungen
        mock_time.time.return_value = 1000.0

        # Mock Modell
        mock_model = MagicMock()
        mock_model.return_value = {
            "choices": [
                {
                    "text": "HYPOTHESE: Test hypothesis\nURSACHE: Test cause\nLÖSUNG: Test fix"
                }
            ]
        }
        mock_get_model.return_value = mock_model

        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config, stack_name="stack_a")

        bug = {
            "bug_id": "BUG-001",
            "bug_type": "test",
            "file_path": "/test.py",
            "line_number": 1,
            "description": "Test bug",
            "code_snippet": "test()",
        }

        responses = coordinator._run_parallel_analyses(bug, ["primary", "secondary"])

        assert len(responses) == 2
        assert all(r.model_id in ["primary", "secondary"] for r in responses)
        assert all("Test hypothesis" in r.hypothesis for r in responses)

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_run_parallel_analyses_file_not_found(
        self, mock_get_model: MagicMock
    ) -> None:
        """Test _run_parallel_analyses mit FileNotFoundError."""
        mock_get_model.side_effect = FileNotFoundError("Model not found")

        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        bug = {"bug_id": "BUG-001"}

        responses = coordinator._run_parallel_analyses(bug, ["primary"])

        assert len(responses) == 1
        assert responses[0].hypothesis == ""
        assert responses[0].metadata["error"] == "file_not_found"
        assert responses[0].metadata["success"] is False

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_run_parallel_analyses_runtime_error(
        self, mock_get_model: MagicMock
    ) -> None:
        """Test _run_parallel_analyses mit RuntimeError."""
        mock_get_model.side_effect = RuntimeError("GPU OOM")

        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        bug = {"bug_id": "BUG-001"}

        responses = coordinator._run_parallel_analyses(bug, ["primary"])

        assert len(responses) == 1
        assert responses[0].hypothesis == ""
        assert responses[0].metadata["error"] == "runtime_error"

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    @patch("escalation.ensemble_coordinator.time")
    def test_run_ensemble_complete(
        self, mock_time: MagicMock, mock_get_model: MagicMock
    ) -> None:
        """Test vollständigen run_ensemble Durchlauf."""
        mock_time.time.return_value = 1000.0

        mock_model = MagicMock()
        mock_model.return_value = {
            "choices": [
                {
                    "text": "HYPOTHESE: Test hypothesis\nURSACHE: Test cause\nLÖSUNG: Test fix"
                }
            ]
        }
        mock_get_model.return_value = mock_model

        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        bug = {
            "bug_id": "BUG-001",
            "bug_type": "test",
            "file_path": "/test.py",
            "description": "Test bug",
            "code_snippet": "test()",
        }

        result = coordinator.run_ensemble(bug)

        assert isinstance(result, EnsembleResult)
        assert result.total_models == 2
        assert len(result.models_used) == 2
        assert result.winning_hypothesis != ""
        assert result.agreement_level in [
            coordinator.AGREEMENT_UNANIMOUS,
            coordinator.AGREEMENT_MAJORITY,
            coordinator.AGREEMENT_PLURALITY,
            coordinator.AGREEMENT_NONE,
        ]
        assert result.metadata["voting_complete"] is True

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_callable_for_langgraph(
        self, mock_get_model: MagicMock
    ) -> None:
        """Test __call__ für LangGraph Integration."""
        mock_model = MagicMock()
        mock_model.return_value = {
            "choices": [
                {"text": "HYPOTHESE: LangGraph test\nURSACHE: Test\nLÖSUNG: Fix"}
            ]
        }
        mock_get_model.return_value = mock_model

        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        # Mock State
        mock_state = MagicMock()
        mock_state.current_bug = {
            "bug_id": "BUG-001",
            "bug_type": "test",
            "file_path": "/test.py",
            "description": "Test",
            "code_snippet": "test()",
        }
        mock_state.ensemble_models = None

        result = coordinator(mock_state)

        assert "ensemble_result" in result
        assert "winning_hypothesis" in result
        assert "metadata" in result
        assert result["metadata"]["ensemble_complete"] is True


class TestTimeoutHandling:
    """Test cases für Timeout-Handling."""

    def setup_method(self) -> None:
        """Setup für jede Test-Methode."""
        ModelLoader._models = {}
        ModelLoader._model_metadata = {}
        ModelLoader._instance = None

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    def test_timeout_handling(
        self, mock_get_model: MagicMock
    ) -> None:
        """Test Timeout-Handling bei langsamen Modellen."""
        # Mock Modell das zu langsam ist (simuliert durch TimeoutError)
        mock_get_model.side_effect = TimeoutError("Analysis timed out")

        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config)

        bug = {"bug_id": "BUG-001"}

        responses = coordinator._run_parallel_analyses(bug, ["primary"])

        # Bei TimeoutError wird eine leere Response mit Error-Metadata zurückgegeben
        assert len(responses) == 1
        assert responses[0].model_id == "primary"
        assert responses[0].metadata["success"] is False


class TestIntegration:
    """Integration Tests für Ensemble Coordinator."""

    def setup_method(self) -> None:
        """Setup für jede Test-Methode."""
        ModelLoader._models = {}
        ModelLoader._model_metadata = {}
        ModelLoader._instance = None

    @patch("escalation.ensemble_coordinator.ModelLoader.get_model")
    @patch("escalation.ensemble_coordinator.time")
    def test_full_workflow_with_mock_models(
        self, mock_time: MagicMock, mock_get_model: MagicMock
    ) -> None:
        """Test vollständigen Workflow mit Mock-Modellen."""
        mock_time.time.return_value = 1000.0

        # Mock Modell-Antworten
        mock_model = MagicMock()
        mock_model.return_value = {
            "choices": [
                {
                    "text": """HYPOTHESE: Race condition in async handler
URSACHE: Shared state not properly synchronized
BETROFFEN: AsyncHandler, StateManager
LÖSUNG: Add mutex lock around shared state access"""
                }
            ]
        }
        mock_get_model.return_value = mock_model

        config = MockConfig()
        coordinator = EnsembleCoordinator(config=config, stack_name="stack_a")

        # Realistischer Bug
        bug = {
            "bug_id": "BUG-2024-001",
            "bug_type": "race_condition",
            "file_path": "/src/handlers/async_handler.py",
            "line_number": 127,
            "description": "Intermittent data corruption in high-load scenarios",
            "code_snippet": """
class AsyncHandler:
    def process(self, data):
        self.shared_state.update(data)  # Line 127
        return self.shared_state.get_result()
""",
        }

        # Führe Ensemble-Analyse durch
        result = coordinator.run_ensemble(bug, ["primary", "secondary"])

        # Verifiziere Ergebnisse
        assert result.total_models == 2
        assert len(result.all_responses) == 2
        assert result.winning_hypothesis != ""
        assert "Race condition" in result.winning_hypothesis

        # Verifiziere Voting
        assert len(result.votes) > 0
        assert result.agreement_level in [
            coordinator.AGREEMENT_UNANIMOUS,
            coordinator.AGREEMENT_MAJORITY,
            coordinator.AGREEMENT_PLURALITY,
            coordinator.AGREEMENT_NONE,
        ]

        # Verifiziere Response-Zeiten
        for response in result.all_responses:
            assert response.response_time_ms >= 0
            assert response.confidence > 0
