"""Bearer tokens for inter-agent A2A calls (via the Jarvis registry or direct).

Current auth model (until the IdP gets a machine client-credentials flow): outbound
calls authenticate with a **static Entra ID token** provisioned to every agent, read
from an env var or from Secrets Manager. If neither is configured, we fall back to
**passthrough** of the JWT the agent's own caller presented (AgentCore's
``BedrockCallContextBuilder`` captures the incoming ``Authorization`` header into
``BedrockAgentCoreContext`` on every request). Locally (docker-compose) nothing is
configured and calls go out unauthenticated, unchanged.

Resolution order:
    1. ``A2A_BEARER_TOKEN`` env var — static token, highest precedence
    2. ``A2A_TOKEN_SECRET_ARN`` env var — Secrets Manager secret holding the token
       (raw string, or JSON with a ``"token"`` key), cached for a short TTL so
       manual rotation is picked up without a restart
    3. the incoming request's Authorization header (passthrough)
    4. None → unauthenticated call (local / docker-compose)

Caveats: a static Entra token expires on the IdP's schedule and must be rotated in
Secrets Manager (the TTL cache re-reads it within ~5 minutes). Passthrough tokens
have whatever lifetime the frontend token has. Both are stopgaps until a machine
OAuth flow exists.
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

from agents.shared.core.logging_config import get_logger

logger = get_logger(__name__)

_AUTH_HEADER = "authorization"
_BEARER_PREFIX = "bearer "

# Re-read the Secrets Manager token this often so manual rotation is picked up.
_SECRET_TTL_S = 300.0

_secret_cache: Optional[str] = None
_secret_cache_expires_at: float = 0.0


def reset_cache() -> None:
    """Drop the cached Secrets Manager token (tests / forced rotation pickup)."""
    global _secret_cache, _secret_cache_expires_at
    _secret_cache = None
    _secret_cache_expires_at = 0.0


def get_bearer_token() -> Optional[str]:
    """Return the bearer token for an outbound A2A call, or None when unauthenticated."""
    token = os.getenv("A2A_BEARER_TOKEN")
    if token:
        return token
    token = _secrets_manager_token()
    if token:
        return token
    return _incoming_request_token()


def _secrets_manager_token() -> Optional[str]:
    global _secret_cache, _secret_cache_expires_at
    arn = os.getenv("A2A_TOKEN_SECRET_ARN")
    if not arn:
        return None
    if _secret_cache and time.monotonic() < _secret_cache_expires_at:
        return _secret_cache
    import boto3

    client = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION", "us-east-1"))
    raw = client.get_secret_value(SecretId=arn)["SecretString"]
    try:
        parsed = json.loads(raw)
        token = parsed["token"] if isinstance(parsed, dict) and "token" in parsed else raw
    except ValueError:
        token = raw
    _secret_cache = token
    _secret_cache_expires_at = time.monotonic() + _SECRET_TTL_S
    logger.info("Loaded A2A bearer token from Secrets Manager (cached %.0fs)", _SECRET_TTL_S)
    return token


def _incoming_request_token() -> Optional[str]:
    """Extract the caller's bearer token from the current AgentCore request context."""
    try:
        from bedrock_agentcore.runtime.context import BedrockAgentCoreContext

        headers = BedrockAgentCoreContext.get_request_headers() or {}
    except Exception:  # not running under an AgentCore request context
        return None
    value = next((v for k, v in headers.items() if k.lower() == _AUTH_HEADER), None)
    if not value:
        return None
    if value.lower().startswith(_BEARER_PREFIX):
        return value[len(_BEARER_PREFIX):].strip()
    return value.strip()
