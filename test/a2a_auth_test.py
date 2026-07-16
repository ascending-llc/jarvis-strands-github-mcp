"""Tests for bearer-token passthrough on inter-agent A2A calls."""

from __future__ import annotations

import pytest
from bedrock_agentcore.runtime.context import BedrockAgentCoreContext

from agents.shared import auth


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    monkeypatch.delenv("A2A_BEARER_TOKEN", raising=False)
    token = BedrockAgentCoreContext._request_headers.set(None)
    yield
    BedrockAgentCoreContext._request_headers.reset(token)


def test_no_token_anywhere_returns_none() -> None:
    assert auth.get_bearer_token() is None


def test_env_override_token(monkeypatch) -> None:
    monkeypatch.setenv("A2A_BEARER_TOKEN", "env-tok")
    assert auth.get_bearer_token() == "env-tok"


def test_incoming_bearer_header_is_passed_through() -> None:
    BedrockAgentCoreContext.set_request_headers({"Authorization": "Bearer jwt-123"})
    assert auth.get_bearer_token() == "jwt-123"


def test_incoming_header_case_insensitive_and_raw_token() -> None:
    # HTTP/2 lowercases header names; also tolerate a value without the Bearer prefix.
    BedrockAgentCoreContext.set_request_headers({"authorization": "jwt-raw"})
    assert auth.get_bearer_token() == "jwt-raw"


def test_incoming_header_wins_over_env(monkeypatch) -> None:
    monkeypatch.setenv("A2A_BEARER_TOKEN", "env-tok")
    BedrockAgentCoreContext.set_request_headers({"Authorization": "Bearer request-tok"})
    assert auth.get_bearer_token() == "request-tok"


def test_client_config_attaches_token(monkeypatch) -> None:
    from agents import a2a_client

    monkeypatch.setenv("A2A_BEARER_TOKEN", "tok-abc")
    config = a2a_client._auth_client_config()
    assert config is not None
    headers = config.httpx_client.headers
    assert headers["Authorization"] == "Bearer tok-abc"
    assert len(headers[a2a_client._SESSION_HEADER]) >= 33


def test_client_config_none_when_unauthenticated() -> None:
    from agents import a2a_client

    assert a2a_client._auth_client_config() is None
