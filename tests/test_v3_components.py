"""
Tests für GlitchHunter v3.0 Komponenten.

Testet:
- Swarm Coordinator & Agents
- Parallel Swarm Processing
- Prediction Engine
- Auto-Refactoring
- Language Registry
- Sandbox Tracers
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Agent Tests
from agent.state import SwarmFinding, SwarmState
from agent.agents.base import BaseAgent
from agent.agents.static_scanner import StaticScannerAgent
from agent.parallel_swarm import ParallelSwarmCoordinator, ParallelConfig


class TestSwarmFinding:
    """Tests für SwarmFinding Dataclass."""
    
    def test_create_finding(self):
        """Erstellt ein Finding."""
        finding = SwarmFinding(
            id="test_001",
            agent="static",
            file_path="test.py",
            line_start=10,
            line_end=20,
            severity="high",
            category="security",
            title="Security Issue",
            description="Test description",
        )
        
        assert finding.id == "test_001"
        assert finding.agent == "static"
        assert finding.severity == "high"
        assert finding.confidence == 0.5  # Default
    
    def test_finding_to_dict(self):
        """Konvertiert Finding zu Dict."""
        finding = SwarmFinding(
            id="test_002",
            agent="dynamic",
            file_path="example.py",
            line_start=5,
            line_end=15,
            severity="critical",
            category="runtime",
            title="Runtime Error",
            description="Critical runtime issue",
            confidence=0.9,
        )
        
        result = finding.to_dict()
        
        assert result["id"] == "test_002"
        assert result["agent"] == "dynamic"
        assert result["severity"] == "critical"
        assert result["confidence"] == 0.9
        assert "evidence" in result
        assert "metadata" in result


class TestSwarmState:
    """Tests für SwarmState Dataclass."""
    
    def test_create_state(self):
        """Erstellt SwarmState."""
        state = SwarmState(
            repo_path=Path("/test/repo"),
            current_phase="init",
        )
        
        assert state.repo_path == Path("/test/repo")
        assert state.current_phase == "init"
        assert len(state.static_findings) == 0
        assert len(state.errors) == 0
    
    def test_state_to_dict(self):
        """Konvertiert State zu Dict."""
        state = SwarmState(
            repo_path=Path("/test/repo"),
            current_phase="running",
        )
        
        result = state.to_dict()
        
        assert result["repo_path"] == "/test/repo"
        assert result["current_phase"] == "running"
        assert result["static_findings_count"] == 0


class TestBaseAgent:
    """Tests für BaseAgent Interface."""
    
    @pytest.mark.asyncio
    async def test_base_agent_abstract(self):
        """BaseAgent ist abstrakt."""
        with pytest.raises(TypeError):
            BaseAgent()
    
    @pytest.mark.asyncio
    async def test_concrete_agent(self):
        """Konkreter Agent implementiert Interface."""
        class TestAgent(BaseAgent):
            async def execute(self, state):
                return {"success": True}
        
        agent = TestAgent()
        result = await agent.execute({})
        
        assert result["success"] == True


class TestStaticScannerAgent:
    """Tests für StaticScannerAgent."""
    
    @pytest.mark.asyncio
    async def test_static_scanner_init(self):
        """Initialisiert StaticScannerAgent."""
        agent = StaticScannerAgent()
        
        assert agent is not None
        assert hasattr(agent, 'analyzer')
    
    @pytest.mark.asyncio
    async def test_static_scanner_scan(self, tmp_path):
        """Scannt Repository."""
        # Test-Datei erstellen
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass\n")
        
        agent = StaticScannerAgent()
        
        with patch.object(agent, 'analyze', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = []
            findings = await agent.scan(tmp_path)
            
            assert isinstance(findings, list)


class TestParallelSwarmCoordinator:
    """Tests für ParallelSwarmCoordinator."""
    
    def test_parallel_config_default(self):
        """Standardkonfiguration."""
        config = ParallelConfig()
        
        assert config.max_workers == 4
        assert config.enable_sharding == True
        assert config.agent_timeout == 300
        assert config.circuit_breaker_threshold == 3
    
    def test_parallel_config_custom(self):
        """Benutzerkonfiguration."""
        config = ParallelConfig(
            max_workers=8,
            enable_sharding=False,
            shard_size_threshold=100_000,
            agent_timeout=600,
        )
        
        assert config.max_workers == 8
        assert config.enable_sharding == False
        assert config.shard_size_threshold == 100_000
    
    @pytest.mark.asyncio
    async def test_coordinator_init(self):
        """Initialisiert Coordinator."""
        coordinator = ParallelSwarmCoordinator(max_workers=2)
        
        assert coordinator.max_workers == 2
        assert coordinator.enable_sharding == True
    
    @pytest.mark.asyncio
    async def test_circuit_breaker(self):
        """Circuit-Breaker Mechanismus."""
        coordinator = ParallelSwarmCoordinator()
        
        # Initial geschlossen
        assert coordinator._circuit_breaker.get("test_agent", False) == False
        
        # Fehler zählen
        for i in range(3):
            coordinator._increment_failure("test_agent")
        
        # Nach 3 Fehlern geöffnet
        assert coordinator._circuit_breaker["test_agent"] == True
    
    @pytest.mark.asyncio
    async def test_reset_circuit_breakers(self):
        """Setzt Circuit-Breaker zurück."""
        coordinator = ParallelSwarmCoordinator()
        
        # Fehler erzeugen
        coordinator._increment_failure("agent1")
        coordinator._increment_failure("agent1")
        coordinator._increment_failure("agent2")
        
        # Zurücksetzen
        coordinator.reset_circuit_breakers()
        
        assert len(coordinator._circuit_breaker) == 0
        assert len(coordinator._failure_counts) == 0


class TestDeduplication:
    """Tests für Finding-Deduplizierung."""
    
    def test_deduplicate_findings(self):
        """Dedupliziert Findings."""
        coordinator = ParallelSwarmCoordinator()
        
        findings = [
            SwarmFinding(
                id="1",
                agent="static",
                file_path="test.py",
                line_start=10,
                line_end=20,
                severity="high",
                category="security",
                title="Issue 1",
                description="Desc 1",
            ),
            SwarmFinding(
                id="2",
                agent="dynamic",
                file_path="test.py",
                line_start=10,
                line_end=20,
                severity="medium",
                category="security",
                title="Issue 2",
                description="Desc 2",
            ),
            SwarmFinding(
                id="3",
                agent="static",
                file_path="other.py",
                line_start=5,
                line_end=15,
                severity="low",
                category="performance",
                title="Issue 3",
                description="Desc 3",
            ),
        ]
        
        unique = coordinator._deduplicate_findings(findings)
        
        # Gleiche file_path + line + category sollten dedupliziert werden
        assert len(unique) == 2
        
        # Erstes Finding sollte Confidence-Boost haben (von 2 Agenten)
        first = unique[0]
        assert first.confidence > 0.5  # Boost von 1.2x
        assert "confirmed_by" in first.metadata


class TestLoadBalancer:
    """Tests für LoadBalancer."""
    
    @pytest.mark.asyncio
    async def test_load_balancer_init(self):
        """Initialisiert LoadBalancer."""
        from agent.parallel_swarm import LoadBalancer
        
        lb = LoadBalancer(num_workers=4)
        
        assert lb.num_workers == 4
    
    @pytest.mark.asyncio
    async def test_distribute_work(self):
        """Verteilt Arbeit."""
        from agent.parallel_swarm import LoadBalancer, WorkItem
        
        lb = LoadBalancer(num_workers=2)
        
        work_items = [
            WorkItem(id="1", file_batch=[], agent_type="static", priority=1),
            WorkItem(id="2", file_batch=[], agent_type="dynamic", priority=2),
            WorkItem(id="3", file_batch=[], agent_type="static", priority=1),
        ]
        
        async def dummy_worker(item):
            return {"id": item.id, "processed": True}
        
        results = await lb.distribute_work(work_items, dummy_worker)
        
        assert len(results) == 3
        assert all(r["processed"] for r in results)


# Integration Tests

class TestIntegration:
    """Integration-Tests für v3.0 Komponenten."""
    
    @pytest.mark.asyncio
    async def test_full_swarm_workflow(self, tmp_path):
        """Kompletter Swarm-Workflow."""
        # Test-Repository erstellen
        test_file = tmp_path / "example.py"
        test_file.write_text("""
def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                return x + y + z
    return 0
""")
        
        # Coordinator mit minimalem Timeout
        coordinator = ParallelSwarmCoordinator(
            max_workers=2,
            enable_sharding=False,
        )
        
        # Analyse starten (sollte schnell timeouten oder empty results liefern)
        result = await coordinator.run_swarm_parallel(
            str(tmp_path),
            timeout=5.0,
        )
        
        # Result-Struktur prüfen
        assert hasattr(result, 'success')
        assert hasattr(result, 'findings')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'execution_time')
        assert hasattr(result, 'parallelization_factor')


class TestLanguageRegistry:
    """Tests für LanguageRegistry."""
    
    def test_detect_language(self):
        """Erkennt Sprache aus Dateiendung."""
        from prefilter.language_registry import LanguageRegistry
        
        registry = LanguageRegistry()
        
        assert registry.detect_language(Path("test.py")) == "python"
        assert registry.detect_language(Path("test.js")) == "javascript"
        assert registry.detect_language(Path("test.ts")) == "typescript"
        assert registry.detect_language(Path("test.rs")) == "rust"
        assert registry.detect_language(Path("test.zig")) == "zig"
        assert registry.detect_language(Path("test.sol")) == "solidity"
    
    def test_get_extensions(self):
        """Returns Dateiendungen für Sprache."""
        from prefilter.language_registry import get_registry
        
        registry = get_registry()
        
        py_exts = registry.get_extensions_for_language("python")
        assert ".py" in py_exts
        
        ts_exts = registry.get_extensions_for_language("typescript")
        assert ".ts" in ts_exts
        assert ".tsx" in ts_exts
    
    def test_supported_languages(self):
        """Listet unterstützte Sprachen."""
        from prefilter.language_registry import get_supported_languages
        
        languages = get_supported_languages()
        
        assert len(languages) >= 14
        assert "python" in languages
        assert "javascript" in languages
        assert "zig" in languages
        assert "solidity" in languages
        assert "kotlin" in languages


# Performance Tests

class TestPerformance:
    """Performance-Tests für Parallelverarbeitung."""
    
    @pytest.mark.asyncio
    async def test_parallel_speedup(self, tmp_path):
        """Testet Parallel-Speedup."""
        # Große Test-Dateien erstellen
        for i in range(10):
            test_file = tmp_path / f"test_{i}.py"
            test_file.write_text("\n".join([f"def func_{i}(): pass"] * 100))
        
        coordinator = ParallelSwarmCoordinator(
            max_workers=4,
            enable_sharding=True,
        )
        
        # Parallele Analyse
        result = await coordinator.run_swarm_parallel(str(tmp_path))
        
        # Parallelisierung sollte > 1 sein
        assert result.parallelization_factor >= 1.0
        
        # Ausführung sollte erfolgreich sein (auch wenn empty results)
        assert result.success or len(result.errors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
