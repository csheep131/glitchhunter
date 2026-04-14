"""
Tests for Config.

Unit tests for configuration loading and validation.
"""

import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import Config
from core.exceptions import ConfigError


class TestConfig:
    """Test cases for Config."""

    def create_temp_config(self, config_dict: Dict[str, Any]) -> Path:
        """Create a temporary config file."""
        fd, path = tempfile.mkstemp(suffix=".yaml")
        try:
            with open(path, "w") as f:
                yaml.safe_dump(config_dict, f)
            return Path(path)
        except Exception:
            Path(path).unlink()
            raise

    def test_load_default_config(self) -> None:
        """Test loading default configuration."""
        config_dict = {
            "hardware": {
                "stack_a": {
                    "name": "GTX 3060",
                    "vram_limit": 8,
                    "cuda_compute": "8.6",
                    "mode": "sequential",
                    "models": {},
                    "security": {},
                    "inference": {},
                }
            },
            "prefilter": {"enabled": True, "semgrep": {}, "ast": {}, "complexity": {}},
            "agent": {"states": [], "max_iterations": 5, "timeout_per_state": 300},
            "mapper": {
                "enabled": True,
                "use_ctags": True,
                "use_tree_sitter": True,
                "symbol_graph": True,
                "repomix": {},
            },
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "debug": False,
                "cors_origins": [],
                "rate_limit": {},
                "auth": {},
            },
            "logging": {
                "level": "INFO",
                "format": "",
                "file": "logs/glitchhunter.log",
                "max_size_mb": 100,
                "backup_count": 5,
            },
            "features": {
                "parallel_inference": False,
                "deep_security_scan": False,
                "multi_model_consensus": False,
                "ast_analysis": True,
                "complexity_check": True,
                "basic_security": True,
                "patch_generation": True,
                "sandbox_execution": True,
            },
            "paths": {
                "models": "models",
                "logs": "logs",
                "cache": ".cache",
                "temp": ".temp",
                "security_rules": "src/security/rules",
            },
        }

        config_path = self.create_temp_config(config_dict)

        try:
            config = Config.load(config_path)

            assert config is not None
            assert "stack_a" in config.hardware
            assert config.prefilter.enabled is True
            assert config.api.port == 8000
            assert config.logging.level == "INFO"
        finally:
            config_path.unlink()

    def test_load_nonexistent_file(self) -> None:
        """Test loading nonexistent config file."""
        with pytest.raises(ConfigError) as exc_info:
            Config.load(Path("/nonexistent/path/config.yaml"))

        assert "Configuration file not found" in exc_info.value.message

    def test_load_invalid_yaml(self) -> None:
        """Test loading invalid YAML."""
        fd, path = tempfile.mkstemp(suffix=".yaml")
        try:
            with open(path, "w") as f:
                f.write("invalid: yaml: content: [")

            with pytest.raises(ConfigError) as exc_info:
                Config.load(Path(path))

            assert "Invalid YAML syntax" in exc_info.value.message
        finally:
            Path(path).unlink()

    def test_get_hardware_profile(self) -> None:
        """Test getting hardware profile by name."""
        config_dict = {
            "hardware": {
                "stack_a": {
                    "name": "GTX 3060",
                    "vram_limit": 8,
                    "cuda_compute": "8.6",
                    "mode": "sequential",
                    "models": {},
                    "security": {},
                    "inference": {},
                },
                "stack_b": {
                    "name": "RTX 3090",
                    "vram_limit": 24,
                    "cuda_compute": "8.6",
                    "mode": "parallel",
                    "models": {},
                    "security": {},
                    "inference": {},
                },
            },
            "prefilter": {},
            "agent": {},
            "mapper": {},
            "api": {},
            "logging": {},
            "features": {},
            "paths": {},
        }

        config_path = self.create_temp_config(config_dict)

        try:
            config = Config.load(config_path)

            profile_a = config.get_hardware_profile("stack_a")
            assert profile_a.name == "GTX 3060"
            assert profile_a.vram_limit == 8

            profile_b = config.get_hardware_profile("stack_b")
            assert profile_b.name == "RTX 3090"
            assert profile_b.vram_limit == 24
        finally:
            config_path.unlink()

    def test_get_unknown_hardware_profile(self) -> None:
        """Test getting unknown hardware profile."""
        config_dict = {
            "hardware": {},
            "prefilter": {},
            "agent": {},
            "mapper": {},
            "api": {},
            "logging": {},
            "features": {},
            "paths": {},
        }

        config_path = self.create_temp_config(config_dict)

        try:
            config = Config.load(config_path)

            with pytest.raises(ConfigError) as exc_info:
                config.get_hardware_profile("unknown_stack")

            assert "not found" in exc_info.value.message
        finally:
            config_path.unlink()

    def test_get_default_stack(self) -> None:
        """Test getting default stack name."""
        config_dict = {
            "hardware": {},
            "prefilter": {},
            "agent": {},
            "mapper": {},
            "api": {},
            "logging": {},
            "features": {},
            "paths": {},
        }

        config_path = self.create_temp_config(config_dict)

        try:
            config = Config.load(config_path)
            default_stack = config.get_default_stack()
            assert default_stack == "stack_a"
        finally:
            config_path.unlink()

    def test_to_dict(self) -> None:
        """Test converting config to dictionary."""
        config_dict = {
            "hardware": {
                "stack_a": {
                    "name": "GTX 3060",
                    "vram_limit": 8,
                    "cuda_compute": "8.6",
                    "mode": "sequential",
                    "models": {},
                    "security": {},
                    "inference": {},
                }
            },
            "prefilter": {"enabled": True, "semgrep": {}, "ast": {}, "complexity": {}},
            "agent": {"states": [], "max_iterations": 5, "timeout_per_state": 300},
            "mapper": {
                "enabled": True,
                "use_ctags": True,
                "use_tree_sitter": True,
                "symbol_graph": True,
                "repomix": {},
            },
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "debug": False,
                "cors_origins": [],
                "rate_limit": {},
                "auth": {},
            },
            "logging": {
                "level": "INFO",
                "format": "",
                "file": "logs/glitchhunter.log",
                "max_size_mb": 100,
                "backup_count": 5,
            },
            "features": {
                "parallel_inference": False,
                "deep_security_scan": False,
                "multi_model_consensus": False,
                "ast_analysis": True,
                "complexity_check": True,
                "basic_security": True,
                "patch_generation": True,
                "sandbox_execution": True,
            },
            "paths": {
                "models": "models",
                "logs": "logs",
                "cache": ".cache",
                "temp": ".temp",
                "security_rules": "src/security/rules",
            },
        }

        config_path = self.create_temp_config(config_dict)

        try:
            config = Config.load(config_path)
            result = config.to_dict()

            assert isinstance(result, dict)
            assert "hardware" in result
            assert "api" in result
            assert "logging" in result
        finally:
            config_path.unlink()

    def test_str_representation(self) -> None:
        """Test string representation."""
        config_dict = {
            "hardware": {
                "stack_a": {
                    "name": "GTX 3060",
                    "vram_limit": 8,
                    "cuda_compute": "8.6",
                    "mode": "sequential",
                    "models": {},
                    "security": {},
                    "inference": {},
                }
            },
            "prefilter": {},
            "agent": {},
            "mapper": {},
            "api": {},
            "logging": {},
            "features": {},
            "paths": {},
        }

        config_path = self.create_temp_config(config_dict)

        try:
            config = Config.load(config_path)
            config_str = str(config)

            assert "stack_a" in config_str
            assert "Config" in config_str
        finally:
            config_path.unlink()
