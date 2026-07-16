"""Tests for outbound A2A bearer-token resolution (static env/SM → passthrough)."""

from __future__ import annotations

import pytest
from bedrock_agentcore.runtime.context import BedrockAgentCoreContext

from agents.shared import auth


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    monkeypatch.delenv("A2A_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("A2A_TOKEN_SECRET_ARN", raising=False)
    auth.reset_cache()
    token = BedrockAgentCoreContext._request_headers.set(None)
    yield
    auth.reset_cache()
    BedrockAgentCoreContext._request_headers.reset(token)


def _fake_secretsmanager(monkeypatch, secret_string: str, calls: list) -> None:
    import boto3

    class FakeClient:
        def get_secret_value(self, SecretId):
            calls.append(SecretId)
            return {"SecretString": secret_string}

    monkeypatch.setattr(boto3, "client", lambda *a, **kw: FakeClient())


def test_no_token_anywhere_returns_none() -> None:
    assert auth.get_bearer_token() is None


def test_env_token_wins_over_everything(monkeypatch) -> None:
    monkeypatch.setenv("A2A_BEARER_TOKEN", "env-tok")
    monkeypatch.setenv("A2A_TOKEN_SECRET_ARN", "arn:unused")
    BedrockAgentCoreContext.set_request_headers({"Authorization": "Bearer request-tok"})
    assert auth.get_bearer_token() == "env-tok"


def test_secrets_manager_token_raw_string(monkeypatch) -> None:
    calls: list = []
    _fake_secretsmanager(monkeypatch, "sm-raw-tok", calls)
    monkeypatch.setenv("A2A_TOKEN_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:1:secret:t")
    assert auth.get_bearer_token() == "sm-raw-tok"
    assert calls == ["arn:aws:secretsmanager:us-east-1:1:secret:t"]


def test_secrets_manager_token_json_key(monkeypatch) -> None:
    calls: list = []
    _fake_secretsmanager(monkeypatch, '{"token": "sm-json-tok"}', calls)
    monkeypatch.setenv("A2A_TOKEN_SECRET_ARN", "arn:x")
    assert auth.get_bearer_token() == "sm-json-tok"


def test_secrets_manager_token_is_ttl_cached(monkeypatch) -> None:
    calls: list = []
    _fake_secretsmanager(monkeypatch, "sm-tok", calls)
    monkeypatch.setenv("A2A_TOKEN_SECRET_ARN", "arn:x")
    assert auth.get_bearer_token() == "sm-tok"
    assert auth.get_bearer_token() == "sm-tok"
    assert len(calls) == 1  # second call served from TTL cache

    # Expire the cache → re-fetched.
    auth.reset_cache()
    assert auth.get_bearer_token() == "sm-tok"
    assert len(calls) == 2


def test_secrets_manager_wins_over_passthrough(monkeypatch) -> None:
    _fake_secretsmanager(monkeypatch, "sm-tok", [])
    monkeypatch.setenv("A2A_TOKEN_SECRET_ARN", "arn:x")
    BedrockAgentCoreContext.set_request_headers({"Authorization": "Bearer request-tok"})
    assert auth.get_bearer_token() == "sm-tok"


def test_passthrough_fallback_bearer_header() -> None:
    BedrockAgentCoreContext.set_request_headers({"Authorization": "Bearer jwt-123"})
    assert auth.get_bearer_token() == "jwt-123"


def test_passthrough_case_insensitive_and_raw_token() -> None:
    # HTTP/2 lowercases header names; also tolerate a value without the Bearer prefix.
    BedrockAgentCoreContext.set_request_headers({"authorization": "jwt-raw"})
    assert auth.get_bearer_token() == "jwt-raw"


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
