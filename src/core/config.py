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
class RateLimitConfig:
    """
    Rate-Limiting-Konfiguration für Remote-APIs.

    Attributes:
        enabled: Ob Rate-Limiting aktiviert ist
        requests_per_minute: Maximale Anzahl Requests pro Minute
        tokens_per_minute: Maximale Anzahl Tokens pro Minute
        burst_limit: Maximale Anzahl gleichzeitiger Requests
    """

    enabled: bool = True
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000
    burst_limit: int = 10


@dataclass
class RetryConfig:
    """
    Retry-Konfiguration mit exponentiellem Backoff.

    Attributes:
        enabled: Ob Retry aktiviert ist
        max_retries: Maximale Anzahl Retry-Versuche
        initial_delay: Initiale Verzögerung in Sekunden
        max_delay: Maximale Verzögerung in Sekunden
        exponential_base: Basis für exponentielle Berechnung
        retry_on_status_codes: HTTP-Status-Codes die Retry auslösen
    """

    enabled: bool = True
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    retry_on_status_codes: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])


@dataclass
class CacheConfig:
    """
    Caching-Konfiguration für Remote-API-Antworten.

    Attributes:
        enabled: Ob Caching aktiviert ist
        backend: Cache-Backend ("memory" oder "redis")
        ttl_seconds: Time-To-Live in Sekunden
        max_size: Maximale Anzahl Cache-Einträge
        redis_url: Redis-Verbindungs-URL (nur für redis-Backend)
    """

    enabled: bool = True
    backend: str = "memory"
    ttl_seconds: int = 3600
    max_size: int = 1000
    redis_url: Optional[str] = None


@dataclass
class APIKeyManagerConfig:
    """
    API-Key-Management-Konfiguration.

    Attributes:
        enabled: Ob API-Key-Management aktiviert ist
        key_file: Pfad zur verschlüsselten API-Key-Datei
        encryption_password_env: Name der Environment-Variable für Master-Passwort
    """

    enabled: bool = True
    key_file: str = ".glitchhunter/api_keys.enc"
    encryption_password_env: str = "GLITCHHUNTER_MASTER_PASSWORD"


@dataclass
class RemoteProviderConfig:
    """
    Konfiguration für einen Remote-Provider.

    Attributes:
        name: Name des Providers
        base_url: Basis-URL der API
        api_key_env: Name der Environment-Variable für API-Key (optional)
        model_mapping: Mapping von lokalen zu remote Modellnamen
        rate_limit: Rate-Limiting-Konfiguration (optional)
        timeout: Request-Timeout in Sekunden
        retry_config: Retry-Konfiguration (optional)
    """

    name: str
    base_url: str
    api_key_env: Optional[str] = None
    model_mapping: Dict[str, str] = field(default_factory=dict)
    rate_limit: Optional[RateLimitConfig] = None
    timeout: int = 120
    retry_config: Optional[RetryConfig] = None


@dataclass
class StackCConfig:
    """
    Konfiguration für Stack C (Remote API).

    Attributes:
        name: Name des Stacks
        enabled: Ob Stack C aktiviert ist
        providers: Dictionary von Provider-Konfigurationen
        default_provider: Standard-Provider für Requests
        cache: Cache-Konfiguration
        api_key_manager: API-Key-Manager-Konfiguration
        fallback_chain: Fallback-Kette bei Provider-Fehlern
    """

    name: str = "stack_c"
    enabled: bool = True
    providers: Dict[str, RemoteProviderConfig] = field(default_factory=dict)
    default_provider: str = "ollama_lan"
    cache: CacheConfig = field(default_factory=CacheConfig)
    api_key_manager: APIKeyManagerConfig = field(default_factory=APIKeyManagerConfig)
    fallback_chain: List[str] = field(default_factory=lambda: ["ollama_lan", "local_stack_a"])


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
        if stack_name == "stack_a":
            return self.stack_a.get("level", self.level)
        elif stack_name == "stack_b":
            return self.stack_b.get("level", self.level)
        return self.level


@dataclass
class AILoggingConfig:
    """Configuration for AI communication logging."""

    enabled: bool = False
    directory: str = "ai_logs"
    max_files: int = 100
    log_requests: bool = True
    log_responses: bool = True
    log_prompts: bool = True
    log_full_response: bool = True


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
class RemoteInferenceConfig:
    """Configuration for remote Llama inference."""

    enabled: bool = False
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    timeout: int = 120
    fallback_to_local: bool = True
    health_check_interval: int = 30
    model_mapping: Dict[str, str] = field(default_factory=dict)
    
    @property
    def is_enabled(self) -> bool:
        """Check if remote inference is enabled."""
        return self.enabled and self.base_url is not None
    
    def get_server_url(self) -> Optional[str]:
        """Get the remote server URL."""
        return self.base_url if self.is_enabled else None
    
    def get_model_name(self, local_alias: str) -> str:
        """Get remote model name for a local alias."""
        return self.model_mapping.get(local_alias, local_alias)


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
        remote_inference: Remote Llama inference configuration
    """

    hardware: Dict[str, HardwareStackConfig]
    prefilter: PreFilterConfig
    agent: AgentConfig
    mapper: MapperConfig
    api: APIConfig
    logging: LoggingConfig
    ai_logging: AILoggingConfig
    features: FeaturesConfig
    paths: PathsConfig
    model_downloads: ModelDownloadsConfig
    mcp_integration: MCPConfig
    remote_inference: RemoteInferenceConfig = field(default_factory=RemoteInferenceConfig)
    stack_c: StackCConfig = field(default_factory=StackCConfig)

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

            # Parse AI logging config
            ai_logging_data = data.get("ai_logging", {})
            ai_logging_config = AILoggingConfig(
                enabled=ai_logging_data.get("enabled", False),
                directory=ai_logging_data.get("directory", "ai_logs"),
                max_files=ai_logging_data.get("max_files", 100),
                log_requests=ai_logging_data.get("log_requests", True),
                log_responses=ai_logging_data.get("log_responses", True),
                log_prompts=ai_logging_data.get("log_prompts", True),
                log_full_response=ai_logging_data.get("log_full_response", True),
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

            # Parse remote inference config
            remote_data = data.get("remote_inference", {})
            remote_inference = RemoteInferenceConfig(
                enabled=remote_data.get("enabled", False),
                base_url=remote_data.get("base_url"),
                api_key=remote_data.get("api_key"),
                timeout=remote_data.get("timeout", 120),
                fallback_to_local=remote_data.get("fallback_to_local", True),
                health_check_interval=remote_data.get("health_check_interval", 30),
                model_mapping=remote_data.get("model_mapping", {}),
            )

            # Parse Stack C config
            stack_c_data = data.get("stack_c", {})
            stack_c = cls._parse_stack_c_config(stack_c_data)

            return cls(
                hardware=hardware,
                prefilter=prefilter,
                agent=agent,
                mapper=mapper,
                api=api,
                logging=logging_config,
                ai_logging=ai_logging_config,
                features=features,
                paths=paths,
                model_downloads=model_downloads_config,
                mcp_integration=mcp_integration,
                remote_inference=remote_inference,
                stack_c=stack_c,
            )

        except TypeError as e:
            raise ConfigError(
                f"Invalid configuration structure: {e}",
                details={"error": str(e)},
            )

    @classmethod
    def _parse_stack_c_config(cls, data: Dict[str, Any]) -> StackCConfig:
        """
        Parse Stack C configuration from dictionary.

        Args:
            data: Configuration dictionary for Stack C

        Returns:
            StackCConfig instance
        """
        providers_data = data.get("providers", {})
        providers = {}

        for provider_name, provider_data in providers_data.items():
            rate_limit_data = provider_data.get("rate_limit")
            retry_config_data = provider_data.get("retry_config")

            rate_limit = None
            if rate_limit_data:
                rate_limit = RateLimitConfig(**rate_limit_data)

            retry_config = None
            if retry_config_data:
                retry_config = RetryConfig(**retry_config_data)

            providers[provider_name] = RemoteProviderConfig(
                name=provider_data.get("name", provider_name),
                base_url=provider_data.get("base_url", ""),
                api_key_env=provider_data.get("api_key_env"),
                model_mapping=provider_data.get("model_mapping", {}),
                rate_limit=rate_limit,
                timeout=provider_data.get("timeout", 120),
                retry_config=retry_config,
            )

        cache_data = data.get("cache", {})
        cache = CacheConfig(
            enabled=cache_data.get("enabled", True),
            backend=cache_data.get("backend", "memory"),
            ttl_seconds=cache_data.get("ttl_seconds", 3600),
            max_size=cache_data.get("max_size", 1000),
            redis_url=cache_data.get("redis_url"),
        )

        api_key_manager_data = data.get("api_key_manager", {})
        api_key_manager = APIKeyManagerConfig(
            enabled=api_key_manager_data.get("enabled", True),
            key_file=api_key_manager_data.get("key_file", ".glitchhunter/api_keys.enc"),
            encryption_password_env=api_key_manager_data.get(
                "encryption_password_env", "GLITCHHUNTER_MASTER_PASSWORD"
            ),
        )

        return StackCConfig(
            name=data.get("name", "stack_c"),
            enabled=data.get("enabled", True),
            providers=providers,
            default_provider=data.get("default_provider", "ollama_lan"),
            cache=cache,
            api_key_manager=api_key_manager,
            fallback_chain=data.get("fallback_chain", ["ollama_lan", "local_stack_a"]),
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

    def get_model_path(self, stack_name: str, model_role: str) -> Optional[str]:
        """
        Get model path for a specific stack and role.
        
        Checks environment variables first, then falls back to config.yaml.
        
        Supported environment variables:
        - GLITCHHUNTER_MODEL_PRIMARY / GLITCHHUNTER_MODEL_SECONDARY (global)
        - GLITCHHUNTER_STACK_A_MODEL_PRIMARY / GLITCHHUNTER_STACK_A_MODEL_SECONDARY
        - GLITCHHUNTER_STACK_B_MODEL_PRIMARY / GLITCHHUNTER_STACK_B_MODEL_SECONDARY
        
        Args:
            stack_name: Name of the stack (e.g., "stack_a")
            model_role: Model role (e.g., "primary", "secondary")
            
        Returns:
            Model path or None
        """
        import os
        
        # Check stack-specific env vars first
        env_key = f"GLITCHHUNTER_{stack_name.upper()}_MODEL_{model_role.upper()}"
        env_path = os.environ.get(env_key)
        if env_path:
            logger.info(f"Model path for {stack_name}/{model_role} from env var {env_key}: {env_path}")
            return env_path
        
        # Check global env vars
        global_env_key = f"GLITCHHUNTER_MODEL_{model_role.upper()}"
        global_env_path = os.environ.get(global_env_key)
        if global_env_path:
            logger.info(f"Model path for {stack_name}/{model_role} from global env var {global_env_key}: {global_env_path}")
            return global_env_path
        
        # Fall back to config.yaml
        if stack_name in self.hardware:
            hw = self.hardware[stack_name]
            models = hw.models if hasattr(hw, 'models') else {}
            if model_role in models:
                model_data = models[model_role]
                if isinstance(model_data, dict):
                    return model_data.get("path")
        
        return None

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
            "remote_inference": {
                "enabled": self.remote_inference.enabled,
                "base_url": self.remote_inference.base_url,
                "api_key": self.remote_inference.api_key,
                "timeout": self.remote_inference.timeout,
                "fallback_to_local": self.remote_inference.fallback_to_local,
                "health_check_interval": self.remote_inference.health_check_interval,
                "model_mapping": self.remote_inference.model_mapping,
            },
            "stack_c": self._stack_c_to_dict(),
        }

    def _stack_c_to_dict(self) -> Dict[str, Any]:
        """
        Convert Stack C configuration to dictionary.

        Returns:
            Dictionary representation of Stack C configuration
        """
        return {
            "name": self.stack_c.name,
            "enabled": self.stack_c.enabled,
            "default_provider": self.stack_c.default_provider,
            "fallback_chain": self.stack_c.fallback_chain,
            "providers": {
                name: {
                    "name": provider.name,
                    "base_url": provider.base_url,
                    "api_key_env": provider.api_key_env,
                    "model_mapping": provider.model_mapping,
                    "timeout": provider.timeout,
                    "rate_limit": {
                        "enabled": provider.rate_limit.enabled,
                        "requests_per_minute": provider.rate_limit.requests_per_minute,
                        "tokens_per_minute": provider.rate_limit.tokens_per_minute,
                        "burst_limit": provider.rate_limit.burst_limit,
                    }
                    if provider.rate_limit
                    else None,
                    "retry_config": {
                        "enabled": provider.retry_config.enabled,
                        "max_retries": provider.retry_config.max_retries,
                        "initial_delay": provider.retry_config.initial_delay,
                        "max_delay": provider.retry_config.max_delay,
                        "exponential_base": provider.retry_config.exponential_base,
                        "retry_on_status_codes": provider.retry_config.retry_on_status_codes,
                    }
                    if provider.retry_config
                    else None,
                }
                for name, provider in self.stack_c.providers.items()
            },
            "cache": {
                "enabled": self.stack_c.cache.enabled,
                "backend": self.stack_c.cache.backend,
                "ttl_seconds": self.stack_c.cache.ttl_seconds,
                "max_size": self.stack_c.cache.max_size,
                "redis_url": self.stack_c.cache.redis_url,
            },
            "api_key_manager": {
                "enabled": self.stack_c.api_key_manager.enabled,
                "key_file": self.stack_c.api_key_manager.key_file,
                "encryption_password_env": self.stack_c.api_key_manager.encryption_password_env,
            },
        }

    def __str__(self) -> str:
        """String representation of configuration."""
        return (
            f"Config(hardware_stacks={list(self.hardware.keys())}, "
            f"default_stack={self.get_default_stack()}, "
            f"models={list(self.model_downloads.models.keys())})"
        )