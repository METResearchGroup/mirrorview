"""Model configuration registry (loads from external YAML)."""

import threading
from pathlib import Path
from typing import Any

import yaml


class ModelConfig:
    """Configuration wrapper for a specific model with hierarchical kwarg resolution.

    Provides methods to resolve configuration values with the following hierarchy:
    1. Model-specific configuration (highest precedence)
    2. Provider-specific configuration
    3. Default configuration (lowest precedence)
    """

    def __init__(
        self,
        model_identifier: str,
        config_data: dict[str, Any],
    ):
        """Initialize ModelConfig for a specific model.

        Args:
            model_identifier: Model identifier (e.g., 'gpt-4o-mini', 'groq/llama3-8b-8192')
            config_data: Full configuration dictionary from YAML file
        """
        self.model_identifier = model_identifier
        self._config_data = config_data

        # Find which provider supports this model
        # Lazy import to allow mocking in tests
        from ml_tooling.llm.providers.registry import LLMProviderRegistry

        try:
            provider_instance = LLMProviderRegistry.get_provider(model_identifier)
            self.provider_name = provider_instance.provider_name
        except ValueError as e:
            raise ValueError(
                f"No provider found for model '{model_identifier}'. "
                f"Cannot create ModelConfig without a provider."
            ) from e

        # Get model-specific config if it exists
        provider_config = config_data.get("models", {}).get(self.provider_name, {})
        supported_models = provider_config.get("supported_models", {})
        self._model_config = supported_models.get(model_identifier, {})

    def get_litellm_route(self) -> str:
        """Get the provider-runtime model route for this public model identifier."""
        route = self._model_config.get("litellm_route")
        if isinstance(route, str) and route.strip():
            return route
        return self.model_identifier

    def is_available(self) -> bool:
        """Whether the model should be presented/accepted for app usage."""
        return bool(self._model_config.get("available", False))

    def get_display_name(self) -> str:
        """Get model display label for UI surfaces."""
        display = self._model_config.get("display_name")
        if isinstance(display, str) and display.strip():
            return display
        return self.model_identifier

    def get_kwarg_value(self, key: str, default: Any = None) -> Any:
        """Get a kwarg value with hierarchical resolution.

        Resolution order (first match wins):
        1. Model-specific llm_inference_kwargs (highest precedence)
        2. Provider-specific llm_inference_kwargs
        3. Default llm_inference_kwargs (lowest precedence)

        Args:
            key: The kwarg key to look up (e.g., 'temperature', 'max_tokens')
            default: Default value to return if key is not found at any level

        Returns:
            The resolved kwarg value, or default if not found
        """
        # 1. Check model-specific llm_inference_kwargs
        model_kwargs = self._model_config.get("llm_inference_kwargs", {})
        if isinstance(model_kwargs, dict) and key in model_kwargs:
            return model_kwargs[key]

        # 2. Check provider-specific llm_inference_kwargs
        provider_config = self._config_data.get("models", {}).get(self.provider_name, {})
        provider_kwargs = provider_config.get("llm_inference_kwargs", {})
        if isinstance(provider_kwargs, dict) and key in provider_kwargs:
            return provider_kwargs[key]

        # 3. Check default llm_inference_kwargs
        default_config = self._config_data.get("models", {}).get("default", {})
        default_kwargs = default_config.get("llm_inference_kwargs", {})
        if isinstance(default_kwargs, dict) and key in default_kwargs:
            return default_kwargs[key]

        # Not found at any level
        return default

    def get_config_value(self, *keys: str) -> Any:
        """Get a configuration value using dot-separated keys.

        Similar to query_interface/backend/config/config.py get_config_value.
        Traverses the configuration dictionary using the provided keys.

        Args:
            *keys: Variable number of keys to traverse the config dict.
                For example: get_config_value("models", "openai", "llm_inference_kwargs")

        Returns:
            The configuration value at the specified path.

        Raises:
            KeyError: If any key in the path does not exist.
            ValueError: If config cannot be traversed (parent is not a dict).
        """
        value = self._config_data
        path_so_far: list[str] = []
        for key in keys:
            path_so_far.append(key)
            if not isinstance(value, dict):
                raise ValueError(
                    f"Cannot traverse key '{key}' - parent is not a dictionary. "
                    f"Path so far: {' -> '.join(path_so_far)}"
                )
            if key not in value:
                raise KeyError(f"Configuration key not found: {' -> '.join(path_so_far)}")
            value = value[key]
        return value

    def get_all_llm_inference_kwargs(self) -> dict[str, Any]:
        """Get all llm_inference_kwargs resolved hierarchically.

        Merges kwargs from all levels (default -> provider -> model),
        with higher precedence values overriding lower precedence ones.

        Returns:
            Dictionary of all resolved llm_inference_kwargs
        """
        # Start with default
        default_config = self._config_data.get("models", {}).get("default", {})
        merged_kwargs = default_config.get("llm_inference_kwargs", {}).copy()

        # Override with provider defaults
        provider_config = self._config_data.get("models", {}).get(self.provider_name, {})
        provider_kwargs = provider_config.get("llm_inference_kwargs", {})
        if isinstance(provider_kwargs, dict):
            merged_kwargs.update(provider_kwargs)

        # Override with model-specific (highest precedence)
        model_kwargs = self._model_config.get("llm_inference_kwargs", {})
        if isinstance(model_kwargs, dict):
            merged_kwargs.update(model_kwargs)

        return merged_kwargs


class ModelConfigRegistry:
    """Registry for model-specific configurations.

    Loads configurations from YAML file, similar to query_interface backend config.
    """

    _config: dict[str, Any] | None = None
    _lock = threading.Lock()
    _config_path: Path | None = None

    @classmethod
    def set_config_path(cls, path: Path | str) -> None:
        """Set custom configuration file path (useful for testing)."""
        cls._config_path = Path(path)
        cls._config = None  # Force reload

    @classmethod
    def _load_config(cls) -> dict[str, Any]:
        """Load configuration from YAML file (thread-safe)."""
        config_path = cls._config_path or (Path(__file__).parent / "models.yaml")
        if cls._config is not None:
            return cls._config
        with cls._lock:
            if cls._config is not None:
                return cls._config
            if not config_path.exists():
                raise FileNotFoundError(f"Model configuration file not found: {config_path}")
            with open(config_path, "r") as f:
                cls._config = yaml.safe_load(f)
            cls._config_path = config_path  # Save resolved path
            return cls._config or {}

    @classmethod
    def get_model_config(cls, model_identifier: str) -> ModelConfig:
        """Get ModelConfig for a specific model identifier.

        Args:
            model_identifier: Model identifier (e.g., 'gpt-4o-mini', 'groq/llama3-8b-8192')

        Returns:
            ModelConfig instance for the specified model

        Raises:
            ValueError: If model is not supported by any provider or not found in config
        """
        config = cls._load_config()

        # Verify provider exists for this model
        # Lazy import to allow mocking in tests
        from ml_tooling.llm.providers.registry import LLMProviderRegistry

        try:
            LLMProviderRegistry.get_provider(model_identifier)
        except ValueError as e:
            raise ValueError(
                f"Model '{model_identifier}' is not supported by any provider. "
                f"Cannot create ModelConfig."
            ) from e

        return ModelConfig(model_identifier, config)

    @classmethod
    def model_exists(cls, model_identifier: str) -> bool:
        """Return whether a model identifier is configured and provider-supported."""
        try:
            cls.get_model_config(model_identifier)
            return True
        except (ValueError, FileNotFoundError):
            return False

    @classmethod
    def is_model_available(cls, model_identifier: str) -> bool:
        """Return whether a model exists and is marked available."""
        try:
            return cls.get_model_config(model_identifier).is_available()
        except (ValueError, FileNotFoundError):
            return False

    @classmethod
    def resolve_litellm_route(cls, model_identifier: str) -> str:
        """Resolve a public model ID to provider runtime route."""
        return cls.get_model_config(model_identifier).get_litellm_route()

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all configured provider names (excluding 'default')."""
        config = cls._load_config()
        providers = list(config.get("models", {}).keys())
        # Remove 'default' from the list
        return [p for p in providers if p != "default"]

    @classmethod
    def list_models_for_provider(cls, provider_name: str) -> list[str]:
        """List all model identifiers for a specific provider.

        Args:
            provider_name: Provider name (e.g., 'openai', 'gemini', 'groq')

        Returns:
            List of model identifiers supported by this provider
        """
        config = cls._load_config()
        provider_config = config.get("models", {}).get(provider_name, {})
        supported_models = provider_config.get("supported_models", {})
        return list(supported_models.keys())

    @classmethod
    def list_all_models(cls) -> list[str]:
        """List all model identifiers across all providers.

        Returns:
            List of all model identifiers in the configuration
        """
        all_models = []
        for provider_name in cls.list_providers():
            all_models.extend(cls.list_models_for_provider(provider_name))
        return all_models

    @classmethod
    def list_available_models(cls) -> list[dict[str, str]]:
        """List all available models with UI/display metadata."""
        available_models: list[dict[str, str]] = []
        for provider_name in cls.list_providers():
            for model_id in cls.list_models_for_provider(provider_name):
                try:
                    model_config = cls.get_model_config(model_id)
                except (ValueError, FileNotFoundError):
                    # Ignore config entries without an implemented provider.
                    continue
                if not model_config.is_available():
                    continue
                available_models.append(
                    {
                        "model_id": model_id,
                        "display_name": model_config.get_display_name(),
                        "provider": provider_name,
                        "litellm_route": model_config.get_litellm_route(),
                    }
                )
        return available_models

    @classmethod
    def get_default_model(cls) -> str:
        """Get the default model from the configuration.

        Returns:
            Default model identifier (e.g., 'gpt-4o-mini')

        Raises:
            KeyError: If default_model is not found in the default configuration
        """
        config = cls._load_config()
        default_config = config.get("models", {}).get("default", {})
        default_model = default_config.get("default_model")
        if default_model is None:
            raise KeyError("default_model not found in models.default configuration")
        if not cls.is_model_available(default_model):
            raise ValueError(f"default_model '{default_model}' must exist and be available")
        return default_model

