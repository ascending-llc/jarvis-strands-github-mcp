"""Thin A2A client for deterministic, parallel worker calls.

The server side is owned by Strands' A2AServer / AgentCore ``serve_a2a``; the client
side is owned by Strands' ``A2AAgent``, which wraps a remote A2A endpoint and handles
transport negotiation, card resolution, and streaming. We keep a small helper here so
the orchestrator can fan out to workers with guaranteed parallelism (asyncio.gather)
rather than relying on model-driven tool calls.

AUTH: calling a deployed AgentCore runtime requires a bearer token plus the AgentCore
session header. Tokens are pass-through for now (see ``agents/shared/auth.py``): the
orchestrator reuses the JWT its own caller presented (or ``A2A_BEARER_TOKEN`` as a
manual override). Local/docker calls have no incoming token and go out
unauthenticated, unchanged.
"""

from __future__ import annotations

import os
from uuid import uuid4

import httpx
from a2a.client import ClientConfig
from strands.agent import A2AAgent

from agents.registry import agent_service_url
from agents.shared.auth import get_bearer_token

# AgentCore requires a session id (>= 33 chars) on every InvokeAgentRuntime request.
_SESSION_HEADER = "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"


def _auth_client_config() -> ClientConfig | None:
    """Build an authenticated A2A ClientConfig, or None to use the default unauthenticated client."""
    token = get_bearer_token()
    if not token:
        return None
    headers = {
        "Authorization": f"Bearer {token}",
        _SESSION_HEADER: os.getenv("AGENTCORE_SESSION_ID") or uuid4().hex * 2,
    }
    return ClientConfig(httpx_client=httpx.AsyncClient(headers=headers))


async def call_agent_text(agent_id: str, prompt: str) -> str:
    """Send a prompt to a remote A2A agent and return its final text response.

    With A2A-compliant streaming, the remote answer arrives as many token-chunk parts,
    which become separate content blocks on the result. ``str(result)`` joins blocks
    with ``"\\n"`` — injecting newlines mid-word and corrupting JSON payloads — so we
    concatenate the text blocks ourselves with no separator.
    """
    client_config = _auth_client_config()
    kwargs = {"client_config": client_config} if client_config is not None else {}
    agent = A2AAgent(endpoint=agent_service_url(agent_id), name=agent_id, **kwargs)
    result = await agent.invoke_async(prompt)
    blocks = result.message.get("content", [])
    return "".join(b["text"] for b in blocks if isinstance(b, dict) and "text" in b)
