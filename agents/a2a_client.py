"""Thin A2A client for deterministic, parallel worker calls.

The server side is owned by Strands' A2AServer / AgentCore ``serve_a2a``; the client
side is owned by Strands' ``A2AAgent``, which wraps a remote A2A endpoint and handles
transport negotiation, card resolution, and streaming. We keep a small helper here so
the orchestrator can fan out to workers with guaranteed parallelism (asyncio.gather)
rather than relying on model-driven tool calls.

AUTH: deployed calls go through the Jarvis registry proxy (``REGISTRY_URL``) with a
static Entra ID bearer token from env or Secrets Manager, falling back to passthrough
of the caller's own JWT — see ``agents/shared/auth.py`` for the resolution order. The
registry handles downstream AgentCore auth (runtime JWT minting, session headers).
Local/docker calls have no token configured and go out unauthenticated, unchanged.
"""

from __future__ import annotations

import os
from uuid import uuid4

import httpx
from a2a.client import A2ACardResolver, ClientConfig
from strands.agent import A2AAgent

from agents.registry import agent_service_url
from agents.shared.auth import get_bearer_token

# AgentCore requires a session id (>= 33 chars) on every InvokeAgentRuntime request.
_SESSION_HEADER = "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"

# The Jarvis registry's ingress blocks any path with a dot-segment (e.g. ``.well-known``),
# which is the A2A spec's default card path. The registry serves the identical card at this
# dot-free alias instead, scoped to its own proxy routes only (``/proxy/a2a/{agent_path}``).
_REGISTRY_PROXY_MARKER = "/proxy/a2a/"
_REGISTRY_PROXY_CARD_PATH = "agent-card.json"


class PinnedEndpointA2AAgent(A2AAgent):
    """A2AAgent that sends messages to the resolved endpoint, ignoring ``card.url``.

    Per the A2A spec, clients send messages to the agent card's ``url``, using the
    configured endpoint only to fetch the card. That behavior breaks proxying: a card
    fetched through the Jarvis registry proxy still carries the agent's direct
    (AgentCore) URL, so a spec-default client would bypass the registry — and fail
    auth — on every message. It is also the root of the historical self-recursion
    trap (a ``localhost`` card URL calling itself). We resolve every endpoint
    deliberately in ``agent_service_url``, so pin the card to it unconditionally.
    """

    async def get_agent_card(self):
        if self._agent_card is not None:
            return self._agent_card

        relative_card_path = _REGISTRY_PROXY_CARD_PATH if _REGISTRY_PROXY_MARKER in self.endpoint else None

        if self._client_config is not None and self._client_config.httpx_client is not None:
            resolver = A2ACardResolver(httpx_client=self._client_config.httpx_client, base_url=self.endpoint)
            card = await resolver.get_agent_card(relative_card_path=relative_card_path)
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resolver = A2ACardResolver(httpx_client=client, base_url=self.endpoint)
                card = await resolver.get_agent_card(relative_card_path=relative_card_path)

        if self.name is None and card.name is not None:
            self.name = card.name
        if self.description is None and card.description is not None:
            self.description = card.description

        if str(card.url).rstrip("/") != self.endpoint.rstrip("/"):
            card = card.model_copy(update={"url": f"{self.endpoint.rstrip('/')}/"})

        self._agent_card = card
        return card


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
    agent = PinnedEndpointA2AAgent(endpoint=agent_service_url(agent_id), name=agent_id, **kwargs)
    result = await agent.invoke_async(prompt)
    blocks = result.message.get("content", [])
    return "".join(b["text"] for b in blocks if isinstance(b, dict) and "text" in b)
