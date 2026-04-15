"""
Configuration management for GlitchHunter.

Loads and validates configuration from config.yaml, providing
type-safe access to all configuration values.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from core.exceptions import ConfigError

logger = logging.getLogger(__name__)

# Default configuration file path
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"


@dataclass
class HardwareStackConfig:
    """Configuration for a hardware stack."""

    name: str
    vram_limit: int
    cuda_compute: str
    mode: str
    models: Dict[str, Any]
    security: Dict[str, Any]
    inference: Dict[str, Any]


@dataclass
class PreFilterConfig:
    """Configuration for pre-filter pipeline."""

    enabled: bool
    semgrep: Dict[str, Any]
    ast: Dict[str, Any]
    complexity: Dict[str, Any]


@dataclass
class AgentConfig:
    """Configuration for agent system."""

    states: List[str]
    max_iterations: int
    timeout_per_state: int
    sandbox: Dict[str, Any]


@dataclass
class MapperConfig:
    """Configuration for repository mapper."""

    enabled: bool
    use_ctags: bool
    use_tree_sitter: bool
    symbol_graph: bool
    repomix: Dict[str, Any]


@dataclass
class APIConfig:
    """Configuration for API server."""

    host: str
    port: int
    debug: bool
    cors_origins: List[str]
    rate_limit: Dict[str, Any]
    auth: Dict[str, Any]


@dataclass
class LoggingConfig:
    """Configuration for logging."""

    level: str
    format: str
    file: str
    max_size_mb: int
    backup_count: int
    stack_a: Dict[str, Any] = field(default_factory=dict)
    stack_b: Dict[str, Any] = field(default_factory=dict)

    def get_level_for_stack(self, stack_name: str) -> str:
        """
        Get logging level for a specific stack.

        Args:
            stack_name: Name of the stack (stack_a or stack_b)

        Returns:
            Logging level (e.g., "DEBUG", "INFO")
        """
        if stack_name == "stack_a" and "level" in self.stack_a:
            return self.stack_a["level"]
        if stack_name == "stack_b" and "level" in self.stack_b:
            return self.stack_b["level"]
        return self.level


@dataclass
class FeaturesConfig:
    """Configuration for feature toggles."""

    parallel_inference: bool
    deep_security_scan: bool
    multi_model_consensus: bool
    ast_analysis: bool
    complexity_check: bool
    basic_security: bool
    patch_generation: bool
    sandbox_execution: bool


@dataclass
class PathsConfig:
    """Configuration for file paths."""

    models: str
    logs: str
    cache: str
    temp: str
    security_rules: str
    reports: str
    llama_tools_path: str


@dataclass
class ModelDownloadConfig:
    """Configuration for a single model download."""

    repo_id: str
    filename: str
    description: str
    size_gb: float
    stack: str


@dataclass
class MCPConfig:
    """Configuration for MCP (SocratiCode) integration."""

    enabled: bool
    server: Dict[str, Any]
    socraticode: Dict[str, Any]
    auto_start: bool = True


@dataclass
class ModelDownloadsConfig:
    """Configuration for model downloads."""

    models: Dict[str, ModelDownloadConfig]


@dataclass
class Config:
    """
    Main configuration class for GlitchHunter.

    Loads configuration from YAML file and provides type-safe access
    to all configuration values.

    Attributes:
        hardware: Hardware stack configurations
        prefilter: Pre-filter pipeline configuration
        agent: Agent system configuration
        mapper: Repository mapper configuration
        api: API server configuration
        logging: Logging configuration
        features: Feature toggle configuration
        paths: File path configuration
        model_downloads: Model downloads configuration
    """

    hardware: Dict[str, HardwareStackConfig]
    prefilter: PreFilterConfig
    agent: AgentConfig
    mapper: MapperConfig
    api: APIConfig
    logging: LoggingConfig
    features: FeaturesConfig
    paths: PathsConfig
    model_downloads: ModelDownloadsConfig
    mcp_integration: MCPConfig

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config file (default: config.yaml in project root)

        Returns:
            Config instance with loaded configuration

        Raises:
            ConfigError: If config file not found or invalid
        """
        if config_path is None:
            config_path = DEFAULT_CONFIG_PATH
        
        # Ensure config_path is a Path object
        if isinstance(config_path, str):
            config_path = Path(config_path)

        logger.info(f"Loading configuration from {config_path}")

        if not config_path.exists():
            raise ConfigError(
                f"Configuration file not found: {config_path}",
                details={"config_path": str(config_path)},
            )

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(
                f"Invalid YAML syntax in config file: {e}",
                details={"config_path": str(config_path)},
            )

        return cls._from_dict(raw_config)

    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "Config":
        """
        Create Config instance from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            Config instance

        Raises:
            ConfigError: If required fields are missing or invalid
        """
        try:
            # Parse hardware stacks
            hardware = {}
            for stack_name, stack_data in data.get("hardware", {}).items():
                hardware[stack_name] = HardwareStackConfig(**stack_data)

            # Parse prefilter config
            prefilter_data = data.get("prefilter", {})
            prefilter = PreFilterConfig(
                enabled=prefilter_data.get("enabled", True),
                semgrep=prefilter_data.get("semgrep", {}),
                ast=prefilter_data.get("ast", {}),
                complexity=prefilter_data.get("complexity", {}),
            )

            # Parse agent config
            agent_data = data.get("agent", {})
            agent = AgentConfig(
                states=agent_data.get("states", []),
                max_iterations=agent_data.get("max_iterations", 5),
                timeout_per_state=agent_data.get("timeout_per_state", 300),
                sandbox=agent_data.get("sandbox", {}),
            )

            # Parse mapper config
            mapper_data = data.get("mapper", {})
            mapper = MapperConfig(
                enabled=mapper_data.get("enabled", True),
                use_ctags=mapper_data.get("use_ctags", True),
                use_tree_sitter=mapper_data.get("use_tree_sitter", True),
                symbol_graph=mapper_data.get("symbol_graph", True),
                repomix=mapper_data.get("repomix", {}),
            )

            # Parse API config
            api_data = data.get("api", {})
            api = APIConfig(
                host=api_data.get("host", "0.0.0.0"),
                port=api_data.get("port", 8000),
                debug=api_data.get("debug", False),
                cors_origins=api_data.get("cors_origins", []),
                rate_limit=api_data.get("rate_limit", {}),
                auth=api_data.get("auth", {}),
            )

            # Parse logging config
            logging_data = data.get("logging", {})
            logging_config = LoggingConfig(
                level=logging_data.get("level", "INFO"),
                format=logging_data.get("format", ""),
                file=logging_data.get("file", "logs/glitchhunter.log"),
                max_size_mb=logging_data.get("max_size_mb", 100),
                backup_count=logging_data.get("backup_count", 5),
                stack_a=logging_data.get("stack_a", {}),
                stack_b=logging_data.get("stack_b", {}),
            )

            # Parse features config
            features_data = data.get("features", {})
            features = FeaturesConfig(
                parallel_inference=features_data.get("parallel_inference", False),
                deep_security_scan=features_data.get("deep_security_scan", False),
                multi_model_consensus=features_data.get("multi_model_consensus", False),
                ast_analysis=features_data.get("ast_analysis", True),
                complexity_check=features_data.get("complexity_check", True),
                basic_security=features_data.get("basic_security", True),
                patch_generation=features_data.get("patch_generation", True),
                sandbox_execution=features_data.get("sandbox_execution", True),
            )

            # Parse paths config
            paths_data = data.get("paths", {})
            paths = PathsConfig(
                models=paths_data.get("models", "models"),
                logs=paths_data.get("logs", "logs"),
                cache=paths_data.get("cache", ".cache"),
                temp=paths_data.get("temp", ".temp"),
                security_rules=paths_data.get("security_rules", "src/security/rules"),
                reports=paths_data.get("reports", "reports"),
                llama_tools_path=paths_data.get("llama_tools_path", "/home/schaf/tools/llama-cpp-turboquant-cuda"),
            )

            # Parse model downloads config
            model_downloads_data = data.get("model_downloads", {})
            model_downloads = {}
            for model_key, model_data in model_downloads_data.items():
                model_downloads[model_key] = ModelDownloadConfig(**model_data)
            
            model_downloads_config = ModelDownloadsConfig(models=model_downloads)

            # Parse MCP config
            mcp_data = data.get("mcp_integration", {})
            mcp_integration = MCPConfig(
                enabled=mcp_data.get("enabled", False),
                server=mcp_data.get("server", {}),
                socraticode=mcp_data.get("socraticode", {}),
                auto_start=mcp_data.get("auto_start", True),
            )

            return cls(
                hardware=hardware,
                prefilter=prefilter,
                agent=agent,
                mapper=mapper,
                api=api,
                logging=logging_config,
                features=features,
                paths=paths,
                model_downloads=model_downloads_config,
                mcp_integration=mcp_integration,
            )

        except TypeError as e:
            raise ConfigError(
                f"Invalid configuration structure: {e}",
                details={"error": str(e)},
            )

    def get_hardware_profile(self, stack_name: str) -> HardwareStackConfig:
        """
        Get hardware stack configuration by name.

        Args:
            stack_name: Name of the hardware stack (e.g., "stack_a")

        Returns:
            HardwareStackConfig for the specified stack

        Raises:
            ConfigError: If stack not found
        """
        if stack_name not in self.hardware:
            raise ConfigError(
                f"Hardware stack '{stack_name}' not found",
                field="hardware",
                details={"available_stacks": list(self.hardware.keys())},
            )
        return self.hardware[stack_name]

    def get_default_stack(self) -> str:
        """
        Get the default hardware stack name.

        Returns:
            Name of the default stack (stack_a)
        """
        return "stack_a"

    def get_model_download_info(self, model_key: str) -> Optional[ModelDownloadConfig]:
        """
        Get download information for a specific model.

        Args:
            model_key: Key of the model (e.g., "qwen3.5-9b")

        Returns:
            ModelDownloadConfig if found, None otherwise
        """
        return self.model_downloads.models.get(model_key)

    def get_models_for_stack(self, stack_name: str) -> Dict[str, ModelDownloadConfig]:
        """
        Get all models for a specific hardware stack.

        Args:
            stack_name: Name of the hardware stack (e.g., "stack_a")

        Returns:
            Dictionary of model configurations for the stack
        """
        return {
            key: config
            for key, config in self.model_downloads.models.items()
            if config.stack == stack_name or config.stack == "both"
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return {
            "hardware": {
                name: {
                    "name": stack.name,
                    "vram_limit": stack.vram_limit,
                    "cuda_compute": stack.cuda_compute,
                    "mode": stack.mode,
                    "models": stack.models,
                    "security": stack.security,
                    "inference": stack.inference,
                }
                for name, stack in self.hardware.items()
            },
            "prefilter": {
                "enabled": self.prefilter.enabled,
                "semgrep": self.prefilter.semgrep,
                "ast": self.prefilter.ast,
                "complexity": self.prefilter.complexity,
            },
            "agent": {
                "states": self.agent.states,
                "max_iterations": self.agent.max_iterations,
                "timeout_per_state": self.agent.timeout_per_state,
                "sandbox": self.agent.sandbox,
            },
            "mapper": {
                "enabled": self.mapper.enabled,
                "use_ctags": self.mapper.use_ctags,
                "use_tree_sitter": self.mapper.use_tree_sitter,
                "symbol_graph": self.mapper.symbol_graph,
                "repomix": self.mapper.repomix,
            },
            "api": {
                "host": self.api.host,
                "port": self.api.port,
                "debug": self.api.debug,
                "cors_origins": self.api.cors_origins,
                "rate_limit": self.api.rate_limit,
                "auth": self.api.auth,
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "file": self.logging.file,
                "max_size_mb": self.logging.max_size_mb,
                "backup_count": self.logging.backup_count,
            },
            "features": {
                "parallel_inference": self.features.parallel_inference,
                "deep_security_scan": self.features.deep_security_scan,
                "multi_model_consensus": self.features.multi_model_consensus,
                "ast_analysis": self.features.ast_analysis,
                "complexity_check": self.features.complexity_check,
                "basic_security": self.features.basic_security,
                "patch_generation": self.features.patch_generation,
                "sandbox_execution": self.features.sandbox_execution,
            },
            "paths": {
                "models": self.paths.models,
                "logs": self.paths.logs,
                "cache": self.paths.cache,
                "temp": self.paths.temp,
                "security_rules": self.paths.security_rules,
            },
            "model_downloads": {
                key: {
                    "repo_id": config.repo_id,
                    "filename": config.filename,
                    "description": config.description,
                    "size_gb": config.size_gb,
                    "stack": config.stack,
                }
                for key, config in self.model_downloads.models.items()
            },
            "mcp_integration": {
                "enabled": self.mcp_integration.enabled,
                "server": self.mcp_integration.server,
                "socraticode": self.mcp_integration.socraticode,
                "auto_start": self.mcp_integration.auto_start,
            },
        }

    def __str__(self) -> str:
        """String representation of configuration."""
        return (
            f"Config(hardware_stacks={list(self.hardware.keys())}, "
            f"default_stack={self.get_default_stack()}, "
            f"models={list(self.model_downloads.models.keys())})"
        )