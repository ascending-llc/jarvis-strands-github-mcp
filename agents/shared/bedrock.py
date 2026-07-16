"""Shared Bedrock model construction.

Centralizes the BedrockModel + botocore timeout/retry config that was previously
copy-pasted into every agent class.
"""

from __future__ import annotations

from botocore.config import Config as BotocoreConfig
from strands.models.bedrock import BedrockModel

from agents.shared.core.config import AppConfig


def build_bedrock_model(config: AppConfig) -> BedrockModel:
    boto_config = BotocoreConfig(
        read_timeout=config.bedrock_read_timeout,
        connect_timeout=config.bedrock_connect_timeout,
        retries={"max_attempts": config.bedrock_max_attempts},
    )
    return BedrockModel(
        model_id=config.model,
        max_tokens=config.max_tokens,
        boto_client_config=boto_config,
    )
