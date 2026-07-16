"""Bearer-token passthrough for inter-agent A2A calls.

Temporary auth model (until a machine client-credentials flow exists on the IdP):
the platform frontend obtains a JWT from the IdP and invokes the orchestrator with
it. AgentCore's ``BedrockCallContextBuilder`` captures the incoming ``Authorization``
header into ``BedrockAgentCoreContext`` on every request; when the orchestrator then
calls a worker runtime, we reuse that same token — the workers' JWT authorizer
validates it against the same IdP discovery URL, so no new token is needed.

Resolution order:
    1. the incoming request's Authorization header (deployed passthrough)
    2. ``A2A_BEARER_TOKEN`` env var (manual override / smoke-testing a deployed stack)
    3. None → unauthenticated call (local / docker-compose, unchanged)

Caveat: the passed-through token has whatever lifetime the frontend's token has —
a long-running orchestration can outlive it and get a 403 mid-run. Acceptable for
now; the fix is the future machine-OAuth flow.
"""

from __future__ import annotations

import os
from typing import Optional

from agents.shared.core.logging_config import get_logger

logger = get_logger(__name__)

_AUTH_HEADER = "authorization"
_BEARER_PREFIX = "bearer "


def get_bearer_token() -> Optional[str]:
    """Return the bearer token for an outbound A2A call, or None when unauthenticated."""
    token = _incoming_request_token()
    if token:
        return token
    return os.getenv("A2A_BEARER_TOKEN") or None


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
