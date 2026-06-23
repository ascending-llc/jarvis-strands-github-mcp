"""Runtime configuration for the Strands orchestration service."""

import os
from dataclasses import dataclass
from typing import Optional

from agents.shared.core.exceptions import ConfigurationError
from agents.shared.core.logging_config import get_logger
from dotenv import load_dotenv

logger = get_logger(__name__)


def _require(key: str, description: str = "") -> str:
    """Return a required environment variable or raise ConfigurationError."""
    value = os.getenv(key)
    if not value or not value.strip():
        msg = f"Required environment variable '{key}' is not set"
        if description:
            msg += f" ({description})"
        logger.error(msg)
        raise ConfigurationError(msg)
    return value


@dataclass(frozen=True)
class AppConfig:
    # Web-research capability (shared by both workers, via Tavily MCP)
    tavily_mcp_url: str
    tavily_mcp_token: Optional[str]
    tavily_mcp_auth_header: str
    tavily_mcp_auth_prefix: str
    tavily_mcp_transport: str
    # Bedrock model
    model: str
    max_tokens: int
    bedrock_read_timeout: int
    bedrock_connect_timeout: int
    bedrock_max_attempts: int
    # Reporting
    report_output_dir: str
    aws_region: str
    s3_bucket: Optional[str]
    s3_prefix: str

    def __post_init__(self) -> None:
        try:
            os.makedirs(self.report_output_dir, exist_ok=True)
        except PermissionError as e:
            raise ConfigurationError(
                f"report_output_dir '{self.report_output_dir}' is not writable: {e}"
            )


def load_config() -> AppConfig:
    """Load and validate configuration from environment variables."""
    logger.debug("Loading configuration from environment variables")
    load_dotenv(override=False)

    try:
        config = AppConfig(
            tavily_mcp_url=_require("TAVILY_MCP_URL", "Tavily MCP server URL"),
            tavily_mcp_token=os.getenv("TAVILY_MCP_TOKEN"),
            tavily_mcp_auth_header=os.getenv("TAVILY_MCP_AUTH_HEADER", "Authorization"),
            tavily_mcp_auth_prefix=os.getenv("TAVILY_MCP_AUTH_PREFIX", "Bearer "),
            tavily_mcp_transport=os.getenv("TAVILY_MCP_TRANSPORT", "streamable_http"),
            model=_require("MODEL", "Bedrock model id or inference profile ARN"),
            max_tokens=int(os.getenv("MAX_TOKENS", "8192")),
            bedrock_read_timeout=int(os.getenv("BEDROCK_READ_TIMEOUT", "300")),
            bedrock_connect_timeout=int(os.getenv("BEDROCK_CONNECT_TIMEOUT", "30")),
            bedrock_max_attempts=int(os.getenv("BEDROCK_MAX_ATTEMPTS", "3")),
            report_output_dir=os.getenv("REPORT_OUTPUT_DIR", "reports"),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            s3_bucket=os.getenv("S3_BUCKET"),
            s3_prefix=os.getenv("S3_PREFIX", "aws-intel-reports"),
        )
        logger.info("Configuration loaded successfully")
        return config
    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}", exc_info=True)
        raise ConfigurationError(f"Configuration loading failed: {e}") from e
