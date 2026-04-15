"""
Tests für VectorRuleLearner mit Vector-DB Integration.

Testet:
- Embedding-Generierung
- Qdrant/ChromaDB Storage (gemockt)
- Similarity-Search
- Auto-Learning Pipeline
"""

import logging
import pytest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch, PropertyMock

from src.fixing.rule_learner import (
    CodePattern,
    LearningResult,
    VectorRule,
    VectorRuleLearner,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample Konfiguration für Tests."""
    return {
        "embeddings": {
            "model": "sentence-transformers/all-MiniLM-L6-v2",
            "cache_dir": ".glitchhunter/test_embeddings",
            "device": "cpu",
        },
        "learned_rules": {
            "vector_db": "chromadb",
            "collection": "test_learned_rules",
            "auto_learn": True,
            "min_similarity": 0.7,
            "top_k": 5,
            "chromadb": {
                "persist_dir": ".glitchhunter/test_chroma",
                "anonymized_telemetry": False,
            },
        },
        "cache": {
            "redis": {
                "enabled": False,
            },
        },
    }


@pytest.fixture
def sample_patch() -> Dict[str, Any]:
    """Sample Patch für Tests."""
    return {
        "file_path": "src/example.py",
        "bug_type": "null_pointer",
        "patch_diff": """- value = None
+ value = "default"
""",
        "explanation": "Initialize variable to avoid null pointer",
        "confidence": 0.85,
    }


@pytest.fixture
def sample_code_pattern() -> CodePattern:
    """Sample CodePattern für Tests."""
    return CodePattern(
        pattern_type="fix",
        language="python",
        pattern='value = "default"',
        message="Initialize variable to avoid null pointer",
        severity="medium",
        files_seen=["src/example.py"],
        fix_success_rate=0.95,
        metadata={
            "bug_type": "null_pointer",
            "file_path": "src/example.py",
            "source": "patch",
        },
    )


@pytest.fixture
def mock_embedding_model() -> MagicMock:
    """Mock für SentenceTransformer Modell."""
    mock_model = MagicMock()
    # 384-dimensional embedding für all-MiniLM-L6-v2
    mock_embedding = [0.1] * 384
    mock_model.encode.return_value = mock_embedding
    return mock_model


# =============================================================================
# VectorRule Tests
# =============================================================================


class TestVectorRule:
    """Tests für VectorRule Dataclass."""

    def test_vector_rule_creation(self, sample_code_pattern: CodePattern) -> None:
        """Test VectorRule Erstellung."""
        embedding = [0.1] * 384
        metadata = {"source": "test"}

        rule = VectorRule(
            id="test-rule-1",
            pattern=sample_code_pattern,
            embedding=embedding,
            metadata=metadata,
        )

        assert rule.id == "test-rule-1"
        assert rule.pattern == sample_code_pattern
        assert rule.embedding == embedding
        assert rule.metadata == metadata
        assert rule.similarity == 0.0

    def test_vector_rule_to_dict(self, sample_code_pattern: CodePattern) -> None:
        """Test VectorRule.to_dict()."""
        rule = VectorRule(
            id="test-rule-2",
            pattern=sample_code_pattern,
            similarity=0.85,
        )

        result = rule.to_dict()

        assert result["id"] == "test-rule-2"
        assert result["pattern"]["pattern_type"] == "fix"
        assert result["similarity"] == 0.85
        assert "metadata" in result


# =============================================================================
# VectorRuleLearner Initialization Tests
# =============================================================================


class TestVectorRuleLearnerInit:
    """Tests für VectorRuleLearner Initialisierung."""

    @patch("sentence_transformers.SentenceTransformer")
    def test_init_with_chromadb(
        self,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
    ) -> None:
        """Test Initialisierung mit ChromaDB."""
        mock_sentence_transformer.return_value = mock_embedding_model

        with patch("chromadb.PersistentClient") as mock_chroma_client:
            mock_collection = MagicMock()
            mock_chroma_client.return_value.get_or_create_collection.return_value = (
                mock_collection
            )

            learner = VectorRuleLearner(config=sample_config)

            assert learner.embedding_model is not None
            assert learner.chroma_client is not None
            assert learner.qdrant_client is None
            assert learner.collection_name == "test_learned_rules"

    @patch("sentence_transformers.SentenceTransformer")
    def test_init_default_config(
        self,
        mock_sentence_transformer: MagicMock,
        mock_embedding_model: MagicMock,
    ) -> None:
        """Test Initialisierung mit Default-Konfiguration."""
        mock_sentence_transformer.return_value = mock_embedding_model

        with patch("chromadb.PersistentClient") as mock_chroma_client:
            mock_collection = MagicMock()
            mock_chroma_client.return_value.get_or_create_collection.return_value = (
                mock_collection
            )

            learner = VectorRuleLearner()

            assert learner.config == {}
            assert learner.collection_name == "learned_rules"

    @patch("sentence_transformers.SentenceTransformer")
    def test_init_embedding_model_cache(
        self,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
    ) -> None:
        """Test dass Embedding-Modell Cache verwendet."""
        mock_sentence_transformer.return_value = mock_embedding_model

        with patch("chromadb.PersistentClient"):
            VectorRuleLearner(config=sample_config)

            # Prüfen dass SentenceTransformer mit cache_folder aufgerufen wurde
            mock_sentence_transformer.assert_called_once()
            call_kwargs = mock_sentence_transformer.call_args[1]
            assert "cache_folder" in call_kwargs


# =============================================================================
# Embedding Tests
# =============================================================================


class TestEmbeddingGeneration:
    """Tests für Embedding-Generierung."""

    @patch("sentence_transformers.SentenceTransformer")
    def test_generate_embedding(
        self,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
    ) -> None:
        """Test Embedding-Generierung."""
        mock_sentence_transformer.return_value = mock_embedding_model

        with patch("chromadb.PersistentClient"):
            learner = VectorRuleLearner(config=sample_config)

            text = "Test pattern for embedding"
            embedding = learner._generate_embedding(text)

            assert isinstance(embedding, list)
            assert len(embedding) == 384
            assert all(isinstance(x, float) for x in embedding)
            mock_embedding_model.encode.assert_called_once_with(text)

    @patch("sentence_transformers.SentenceTransformer")
    def test_pattern_to_text(
        self,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
        sample_code_pattern: CodePattern,
    ) -> None:
        """Test Pattern zu Text Konvertierung."""
        mock_sentence_transformer.return_value = mock_embedding_model

        with patch("chromadb.PersistentClient"):
            learner = VectorRuleLearner(config=sample_config)

            text = learner._pattern_to_text(sample_code_pattern)

            assert "Bug Type: null_pointer" in text
            assert "File: src/example.py" in text
            assert "Language: python" in text
            assert "Pattern Type: fix" in text
            assert "Code Context:" in text
            assert "Fix Description:" in text

    @patch("sentence_transformers.SentenceTransformer")
    def test_pattern_to_text_long_context(
        self,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
    ) -> None:
        """Test Pattern zu Text mit langem Context."""
        mock_sentence_transformer.return_value = mock_embedding_model

        pattern = CodePattern(
            pattern_type="fix",
            language="python",
            pattern="x" * 600,  # Länger als 500 Zeichen
            message="Test message",
            metadata={"bug_type": "test"},
        )

        with patch("chromadb.PersistentClient"):
            learner = VectorRuleLearner(config=sample_config)

            text = learner._pattern_to_text(pattern)

            # Sollte auf 500 Zeichen + "..." begrenzt sein
            code_context_part = text.split("Code Context:")[1].split("\n")[0]
            assert len(code_context_part) <= 504  # 500 + "..."
            assert code_context_part.endswith("...")


# =============================================================================
# Learning Tests
# =============================================================================


class TestLearningFromPatches:
    """Tests für Learning aus Patches."""

    @patch("sentence_transformers.SentenceTransformer")
    def test_learn_from_patches(
        self,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
        sample_patch: Dict[str, Any],
    ) -> None:
        """Test Learning aus Patches."""
        mock_sentence_transformer.return_value = mock_embedding_model

        with patch("chromadb.PersistentClient") as mock_chroma_client:
            mock_collection = MagicMock()
            mock_chroma_client.return_value.get_or_create_collection.return_value = (
                mock_collection
            )

            learner = VectorRuleLearner(config=sample_config)

            patches = [sample_patch]
            result = learner.learn_from_patches(patches)

            assert isinstance(result, LearningResult)
            assert len(result.patterns) > 0
            assert len(result.semgrep_rules) > 0
            assert result.rules_file is not None

            # Prüfen dass in ChromaDB gespeichert wurde
            mock_collection.add.assert_called()

    @patch("sentence_transformers.SentenceTransformer")
    def test_learn_from_multiple_patches(
        self,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
    ) -> None:
        """Test Learning aus mehreren Patches."""
        mock_sentence_transformer.return_value = mock_embedding_model

        with patch("chromadb.PersistentClient"):
            learner = VectorRuleLearner(config=sample_config)

            patches = [
                {
                    "file_path": "src/file1.py",
                    "bug_type": "null_pointer",
                    "patch_diff": "- x = None\n+ x = 'default'",
                    "explanation": "Init variable",
                },
                {
                    "file_path": "src/file2.py",
                    "bug_type": "index_error",
                    "patch_diff": "- arr[0]\n+ arr[0] if arr else None",
                    "explanation": "Check bounds",
                },
            ]

            result = learner.learn_from_patches(patches)

            assert len(result.patterns) >= 2
            assert len(result.semgrep_rules) >= 1


# =============================================================================
# Similarity Search Tests
# =============================================================================


class TestSimilaritySearch:
    """Tests für Similarity-Search."""

    @patch("sentence_transformers.SentenceTransformer")
    def test_find_similar_rules_chromadb(
        self,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
    ) -> None:
        """Test Similarity-Search mit ChromaDB."""
        mock_sentence_transformer.return_value = mock_embedding_model

        with patch("chromadb.PersistentClient") as mock_chroma_client:
            mock_collection = MagicMock()
            mock_chroma_client.return_value.get_or_create_collection.return_value = (
                mock_collection
            )

            # Mock Search-Ergebnis
            mock_collection.query.return_value = {
                "ids": [["rule-1", "rule-2"]],
                "distances": [[0.2, 0.4]],
                "metadatas": [
                    [
                        {"bug_type": "null_pointer", "language": "python"},
                        {"bug_type": "index_error", "language": "python"},
                    ]
                ],
                "documents": [["doc1", "doc2"]],
            }

            learner = VectorRuleLearner(config=sample_config)

            results = learner.find_similar_rules(
                "null pointer exception", top_k=5
            )

            assert isinstance(results, list)
            assert len(results) == 2
            assert results[0]["id"] == "rule-1"
            assert "similarity" in results[0]
            assert "metadata" in results[0]

            # Query wurde aufgerufen
            mock_collection.query.assert_called_once()

    @patch("sentence_transformers.SentenceTransformer")
    def test_find_similar_rules_min_similarity(
        self,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
    ) -> None:
        """Test Similarity-Search mit min_similarity Filter."""
        mock_sentence_transformer.return_value = mock_embedding_model

        with patch("chromadb.PersistentClient") as mock_chroma_client:
            mock_collection = MagicMock()
            mock_chroma_client.return_value.get_or_create_collection.return_value = (
                mock_collection
            )

            # Mock Search-Ergebnis mit verschiedenen Similarities
            mock_collection.query.return_value = {
                "ids": [["rule-1", "rule-2", "rule-3"]],
                "distances": [[0.1, 0.5, 0.8]],  # Similarities: 0.95, 0.75, 0.6
                "metadatas": [[{}, {}, {}]],
                "documents": [["doc1", "doc2", "doc3"]],
            }

            learner = VectorRuleLearner(config=sample_config)

            # Mit min_similarity=0.7 sollten nur 2 Ergebnisse zurückkommen
            results = learner.find_similar_rules(
                "test query", top_k=5, min_similarity=0.7
            )

            assert len(results) == 2

    @patch("sentence_transformers.SentenceTransformer")
    @patch("qdrant_client.QdrantClient")
    def test_find_similar_rules_qdrant(
        self,
        mock_qdrant_client: MagicMock,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
    ) -> None:
        """Test Similarity-Search mit Qdrant."""
        mock_sentence_transformer.return_value = mock_embedding_model

        # Qdrant konfigurieren
        sample_config["learned_rules"]["vector_db"] = "qdrant"

        # Mock Qdrant Search-Ergebnis
        mock_hit1 = MagicMock()
        mock_hit1.id = "qdrant-rule-1"
        mock_hit1.score = 0.92
        mock_hit1.payload = {
            "pattern": {"pattern_type": "fix"},
            "bug_type": "null_pointer",
        }

        mock_hit2 = MagicMock()
        mock_hit2.id = "qdrant-rule-2"
        mock_hit2.score = 0.78
        mock_hit2.payload = {
            "pattern": {"pattern_type": "vulnerability"},
            "bug_type": "injection",
        }

        mock_qdrant_client.return_value.search.return_value = [mock_hit1, mock_hit2]
        mock_qdrant_client.return_value.get_collections.return_value = MagicMock(
            collections=[]
        )

        learner = VectorRuleLearner(config=sample_config)

        results = learner.find_similar_rules("null pointer", top_k=5)

        assert len(results) == 2
        assert results[0]["id"] == "qdrant-rule-1"
        assert results[0]["similarity"] == 0.92


# =============================================================================
# Statistics Tests
# =============================================================================


class TestRuleStatistics:
    """Tests für Rule-Statistiken."""

    @patch("sentence_transformers.SentenceTransformer")
    def test_get_rule_statistics_chromadb(
        self,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
    ) -> None:
        """Test Statistiken mit ChromaDB."""
        mock_sentence_transformer.return_value = mock_embedding_model

        with patch("chromadb.PersistentClient") as mock_chroma_client:
            mock_collection = MagicMock()
            mock_collection.count.return_value = 42
            mock_chroma_client.return_value.get_or_create_collection.return_value = (
                mock_collection
            )

            learner = VectorRuleLearner(config=sample_config)

            stats = learner.get_rule_statistics()

            assert stats["collection_name"] == "test_learned_rules"
            assert stats["vector_db"] == "chromadb"
            assert stats["total_rules"] == 42
            assert stats["embedding_model"] == "sentence-transformers/all-MiniLM-L6-v2"
            assert stats["embedding_dimension"] == 384

    @patch("sentence_transformers.SentenceTransformer")
    @patch("qdrant_client.QdrantClient")
    def test_get_rule_statistics_qdrant(
        self,
        mock_qdrant_client: MagicMock,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
    ) -> None:
        """Test Statistiken mit Qdrant."""
        mock_sentence_transformer.return_value = mock_embedding_model

        sample_config["learned_rules"]["vector_db"] = "qdrant"

        mock_collection_info = MagicMock()
        mock_collection_info.points_count = 128
        mock_qdrant_client.return_value.get_collection.return_value = (
            mock_collection_info
        )
        mock_qdrant_client.return_value.get_collections.return_value = MagicMock(
            collections=[]
        )

        learner = VectorRuleLearner(config=sample_config)

        stats = learner.get_rule_statistics()

        assert stats["vector_db"] == "qdrant"
        assert stats["total_rules"] == 128


# =============================================================================
# Clear Rules Tests
# =============================================================================


class TestClearRules:
    """Tests für Löschen von Rules."""

    @patch("sentence_transformers.SentenceTransformer")
    def test_clear_rules_chromadb(
        self,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
    ) -> None:
        """Test Löschen mit ChromaDB."""
        mock_sentence_transformer.return_value = mock_embedding_model

        with patch("chromadb.PersistentClient") as mock_chroma_client:
            mock_client_instance = MagicMock()
            mock_collection = MagicMock()
            mock_chroma_client.return_value = mock_client_instance
            mock_client_instance.get_or_create_collection.return_value = mock_collection

            learner = VectorRuleLearner(config=sample_config)
            learner.clear_rules()

            # delete_collection wurde aufgerufen
            mock_client_instance.delete_collection.assert_called_once_with(
                "test_learned_rules"
            )

    @patch("sentence_transformers.SentenceTransformer")
    @patch("qdrant_client.QdrantClient")
    def test_clear_rules_qdrant(
        self,
        mock_qdrant_client: MagicMock,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
    ) -> None:
        """Test Löschen mit Qdrant."""
        mock_sentence_transformer.return_value = mock_embedding_model

        sample_config["learned_rules"]["vector_db"] = "qdrant"
        mock_qdrant_client.return_value.get_collections.return_value = MagicMock(
            collections=[]
        )

        learner = VectorRuleLearner(config=sample_config)
        learner.clear_rules()

        # delete_collection wurde aufgerufen
        mock_qdrant_client.return_value.delete_collection.assert_called_once_with(
            "test_learned_rules"
        )


# =============================================================================
# Integration Tests (Mock-basiert)
# =============================================================================


class TestIntegration:
    """Integrationstests für VectorRuleLearner Pipeline."""

    @patch("sentence_transformers.SentenceTransformer")
    def test_full_learning_pipeline(
        self,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
    ) -> None:
        """Test komplette Learning-Pipeline."""
        mock_sentence_transformer.return_value = mock_embedding_model

        with patch("chromadb.PersistentClient") as mock_chroma_client:
            mock_collection = MagicMock()
            mock_chroma_client.return_value.get_or_create_collection.return_value = (
                mock_collection
            )

            learner = VectorRuleLearner(config=sample_config)

            # 1. Lernen aus Patches
            patches = [
                {
                    "file_path": "src/auth.py",
                    "bug_type": "sql_injection",
                    "patch_diff": '- query = f"SELECT * FROM users WHERE id = {user_id}"\n+ query = "SELECT * FROM users WHERE id = ?"\n+ cursor.execute(query, (user_id,))',
                    "explanation": "Use parameterized queries to prevent SQL injection",
                    "confidence": 0.95,
                }
            ]

            result = learner.learn_from_patches(patches)

            # 2. Prüfen dass Rules gelernt wurden
            assert len(result.patterns) > 0
            assert len(result.semgrep_rules) > 0

            # 3. Similarity-Search testen
            search_results = learner.find_similar_rules(
                "SQL injection vulnerability", top_k=5
            )

            # ChromaDB mock sollte query aufgerufen haben
            assert mock_collection.query.called or mock_collection.add.called

            # 4. Statistiken prüfen
            stats = learner.get_rule_statistics()
            assert stats["vector_db"] == "chromadb"
            assert stats["embedding_dimension"] == 384

    @patch("sentence_transformers.SentenceTransformer")
    def test_error_handling_no_embedding_model(
        self,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
    ) -> None:
        """Test Error Handling wenn Embedding-Modell nicht geladen."""
        # Simuliere ImportError
        mock_sentence_transformer.side_effect = ImportError(
            "sentence-transformers not installed"
        )

        with pytest.raises(ImportError):
            with patch("chromadb.PersistentClient"):
                VectorRuleLearner(config=sample_config)


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests für Edge Cases."""

    @patch("sentence_transformers.SentenceTransformer")
    def test_empty_patches_list(
        self,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
    ) -> None:
        """Test mit leerer Patch-Liste."""
        mock_sentence_transformer.return_value = mock_embedding_model

        with patch("chromadb.PersistentClient"):
            learner = VectorRuleLearner(config=sample_config)

            result = learner.learn_from_patches([])

            assert isinstance(result, LearningResult)
            assert len(result.patterns) == 0
            assert len(result.semgrep_rules) == 0

    @patch("sentence_transformers.SentenceTransformer")
    def test_search_empty_collection(
        self,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
    ) -> None:
        """Test Similarity-Search auf leerer Collection."""
        mock_sentence_transformer.return_value = mock_embedding_model

        with patch("chromadb.PersistentClient") as mock_chroma_client:
            mock_collection = MagicMock()
            mock_collection.query.return_value = {
                "ids": [[]],
                "distances": [[]],
                "metadatas": [[]],
                "documents": [[]],
            }
            mock_chroma_client.return_value.get_or_create_collection.return_value = (
                mock_collection
            )

            learner = VectorRuleLearner(config=sample_config)

            results = learner.find_similar_rules("test query")

            assert results == []

    @patch("sentence_transformers.SentenceTransformer")
    def test_pattern_with_missing_metadata(
        self,
        mock_sentence_transformer: MagicMock,
        sample_config: Dict[str, Any],
        mock_embedding_model: MagicMock,
    ) -> None:
        """Test Pattern mit fehlenden Metadaten."""
        mock_sentence_transformer.return_value = mock_embedding_model

        with patch("chromadb.PersistentClient"):
            learner = VectorRuleLearner(config=sample_config)

            pattern = CodePattern(
                pattern_type="fix",
                language="python",
                pattern="test",
                message="test",
                # Kein metadata dict
            )

            # Sollte nicht crashen
            text = learner._pattern_to_text(pattern)
            assert "Bug Type: unknown" in text
