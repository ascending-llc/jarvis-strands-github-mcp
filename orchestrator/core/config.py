"""Runtime configuration for the Strands orchestration service."""

import os
from dataclasses import dataclass
from typing import Optional

from orchestrator.core.exceptions import ConfigurationError
from orchestrator.core.logging_config import get_logger
from dotenv import load_dotenv

logger = get_logger(__name__)


def _validate_required_env(key: str, description: str = "") -> str:
    """Get and validate that a required environment variable is set."""
    value = os.getenv(key)
    if not value or not value.strip():
        error_msg = f"Required environment variable '{key}' is not set"
        if description:
            error_msg += f" ({description})"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)
    return value


@dataclass(frozen=True)
class AppConfig:
    tavily_api_key: str
    perplexity_api_key: str
    model: str
    perplexity_model: str
    report_output_dir: str
    max_tokens: int
    bedrock_read_timeout: int
    bedrock_connect_timeout: int
    bedrock_max_attempts: int

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        # Validate API keys are not empty
        if not self.tavily_api_key or not self.tavily_api_key.strip():
            raise ConfigurationError("tavily_api_key is empty")
        if not self.perplexity_api_key or not self.perplexity_api_key.strip():
            raise ConfigurationError("perplexity_api_key is empty")

        # Validate report output directory is writable or creatable
        try:
            os.makedirs(self.report_output_dir, exist_ok=True)
        except PermissionError as e:
            raise ConfigurationError(
                f"report_output_dir '{self.report_output_dir}' is not writable: {e}"
            )


def load_config() -> AppConfig:
    """
    Load and validate application configuration from environment variables.

    Returns:
        Validated AppConfig instance

    Raises:
        ConfigurationError: If any required configuration is missing or invalid
    """
    logger.debug("Loading configuration from environment variables")
    load_dotenv(override=False)

    try:
        config = AppConfig(
            tavily_api_key=_validate_required_env(
                "TAVILY_API_KEY", "Tavily API authentication key"
            ),
            perplexity_api_key=_validate_required_env(
                "PERPLEXITY_API_KEY", "Perplexity API authentication key"
            ),
            model=os.getenv("MODEL", os.getenv("PERPLEXITY_MODEL", "sonar")),
            perplexity_model=os.getenv("PERPLEXITY_MODEL", "sonar"),
            report_output_dir=os.getenv("REPORT_OUTPUT_DIR", "reports"),
            max_tokens=int(os.getenv("MAX_TOKENS", "8192")),
            bedrock_read_timeout=int(os.getenv("BEDROCK_READ_TIMEOUT", "300")),
            bedrock_connect_timeout=int(os.getenv("BEDROCK_CONNECT_TIMEOUT", "30")),
            bedrock_max_attempts=int(os.getenv("BEDROCK_MAX_ATTEMPTS", "3")),
        )
        logger.info("Configuration loaded successfully")
        return config
    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}", exc_info=True)
        raise ConfigurationError(f"Configuration loading failed: {e}") from e
