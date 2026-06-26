"""Thin A2A client for deterministic, parallel worker calls.

The server side is owned by Strands' A2AServer / AgentCore ``serve_a2a``; the client
side is owned by Strands' ``A2AAgent``, which wraps a remote A2A endpoint and handles
transport negotiation, card resolution, and streaming. We keep a small helper here so
the orchestrator can fan out to workers with guaranteed parallelism (asyncio.gather)
rather than relying on model-driven tool calls.

AUTH (deferred): calling a deployed AgentCore runtime requires a bearer token (from the
machine OAuth client-credentials flow) plus the AgentCore session header. The plumbing
lives in ``_auth_client_config`` below but is intentionally a no-op until the machine
OAuth workflow is ready — local/docker calls need no auth and work unchanged.
"""

from __future__ import annotations

import os
from uuid import uuid4

import httpx
from a2a.client import ClientConfig
from strands.agent import A2AAgent

from agents.registry import agent_service_url

# AgentCore requires a session id (>= 33 chars) on every InvokeAgentRuntime request.
_SESSION_HEADER = "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"


def _auth_token() -> str | None:
    """Return a bearer token for inter-agent calls, or None when no auth is needed.

    TODO(machine-oauth): implement the OAuth2 client_credentials flow against the IdP
    (read client id/secret + token endpoint from env/Secrets Manager, fetch, and cache
    with a refresh buffer). Until then this returns None and calls go out unauthenticated
    (correct for local docker-compose; deployed AgentCore calls will 403 until wired).
    """
    return None


def _auth_client_config() -> ClientConfig | None:
    """Build an authenticated A2A ClientConfig, or None to use the default unauthenticated client."""
    token = _auth_token()
    if not token:
        return None
    headers = {
        "Authorization": f"Bearer {token}",
        _SESSION_HEADER: os.getenv("AGENTCORE_SESSION_ID") or uuid4().hex * 2,
    }
    return ClientConfig(httpx_client=httpx.AsyncClient(headers=headers))


async def call_agent_text(agent_id: str, prompt: str) -> str:
    """Send a prompt to a remote A2A agent and return its final text response."""
    client_config = _auth_client_config()
    kwargs = {"client_config": client_config} if client_config is not None else {}
    agent = A2AAgent(endpoint=agent_service_url(agent_id), name=agent_id, **kwargs)
    result = await agent.invoke_async(prompt)
    return str(result)
