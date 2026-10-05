"""Integration test: inbound Authorization header → executor context → outbound token.

Runs the REAL AgentCore server plumbing (``build_a2a_app`` — the same app ``serve_a2a``
serves, including ``BedrockCallContextBuilder``) with a stub executor, sends an A2A
``message/send`` carrying an ``Authorization`` header, and asserts that, from inside the
executor (where orchestrator tools run), ``get_bearer_token()`` returns that same token
and ``_auth_client_config()`` would attach it to outbound worker calls.
"""

from __future__ import annotations

from a2a.server.agent_execution import AgentExecutor
from a2a.types import AgentCapabilities, AgentCard
from a2a.utils import new_agent_text_message
from bedrock_agentcore.runtime.a2a import build_a2a_app
from starlette.testclient import TestClient

from agents import a2a_client
from agents.shared import auth


class _CapturingExecutor(AgentExecutor):
    """Records what the auth helpers see at the point where agent tools execute."""

    def __init__(self) -> None:
        self.seen_token: str | None = None
        self.outbound_auth_header: str | None = None

    async def execute(self, context, event_queue) -> None:
        self.seen_token = auth.get_bearer_token()
        config = a2a_client._auth_client_config()
        if config is not None:
            self.outbound_auth_header = config.httpx_client.headers.get("Authorization")
        await event_queue.enqueue_event(new_agent_text_message("ok"))

    async def cancel(self, context, event_queue) -> None:  # pragma: no cover
        raise NotImplementedError


def _send_message(client: TestClient, headers: dict[str, str]) -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "role": "user",
                "messageId": "m-1",
                "parts": [{"kind": "text", "text": "hello"}],
            }
        },
    }
    resp = client.post("/", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    assert "error" not in resp.json(), resp.json()


def _make_app(executor: _CapturingExecutor):
    card = AgentCard(
        name="stub",
        description="stub agent",
        url="http://testserver/",
        version="0.1.0",
        capabilities=AgentCapabilities(streaming=True),
        skills=[],
        default_input_modes=["text"],
        default_output_modes=["text"],
    )
    return build_a2a_app(executor, card)


def test_incoming_jwt_reaches_outbound_client_config() -> None:
    executor = _CapturingExecutor()
    client = TestClient(_make_app(executor))

    _send_message(client, headers={"Authorization": "Bearer jwt-from-frontend"})

    assert executor.seen_token == "jwt-from-frontend"
    assert executor.outbound_auth_header == "Bearer jwt-from-frontend"


def test_no_auth_header_means_unauthenticated_outbound(monkeypatch) -> None:
    monkeypatch.delenv("A2A_BEARER_TOKEN", raising=False)
    executor = _CapturingExecutor()
    client = TestClient(_make_app(executor))

    _send_message(client, headers={})

    assert executor.seen_token is None
    assert executor.outbound_auth_header is None
