"""Tests for endpoint resolution (URL env → registry proxy → ARN) and card pinning."""

from __future__ import annotations

import asyncio

import pytest
from a2a.types import AgentCapabilities, AgentCard

from agents.a2a_client import PinnedEndpointA2AAgent
from agents.registry import agent_service_url


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in [
        "AWS_RESEARCH_URL",
        "AWS_RESEARCH_AGENT_ARN",
        "AWS_RESEARCH_REGISTRY_PATH",
        "REGISTRY_URL",
    ]:
        monkeypatch.delenv(var, raising=False)


def test_url_env_wins(monkeypatch) -> None:
    monkeypatch.setenv("AWS_RESEARCH_URL", "http://aws_research:9000/")
    monkeypatch.setenv("REGISTRY_URL", "https://jarvis.ascendingdc.com")
    assert agent_service_url("aws_research") == "http://aws_research:9000"


def test_registry_proxy_used_when_no_url_env(monkeypatch) -> None:
    monkeypatch.setenv("REGISTRY_URL", "https://jarvis.ascendingdc.com/")
    monkeypatch.setenv("AWS_RESEARCH_AGENT_ARN", "arn:aws:bedrock-agentcore:us-east-1:1:runtime/x")
    assert (
        agent_service_url("aws_research")
        == "https://jarvis.ascendingdc.com/proxy/a2a/aws_research"
    )


def test_registry_path_override(monkeypatch) -> None:
    monkeypatch.setenv("REGISTRY_URL", "https://jarvis.ascendingdc.com")
    monkeypatch.setenv("AWS_RESEARCH_REGISTRY_PATH", "aws-research-prod")
    assert (
        agent_service_url("aws_research")
        == "https://jarvis.ascendingdc.com/proxy/a2a/aws-research-prod"
    )


def test_arn_fallback_without_registry(monkeypatch) -> None:
    monkeypatch.setenv("AWS_RESEARCH_AGENT_ARN", "arn:aws:bedrock-agentcore:us-east-1:1:runtime/x")
    url = agent_service_url("aws_research")
    assert url.startswith("https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/")


def test_missing_everything_raises() -> None:
    with pytest.raises(ValueError, match="REGISTRY_URL"):
        agent_service_url("aws_research")


def _make_upstream_card() -> AgentCard:
    return AgentCard(
        name="AWS Research Agent",
        description="d",
        url="https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/arn/invocations/",
        version="0.1.0",
        capabilities=AgentCapabilities(streaming=True),
        skills=[],
        default_input_modes=["text"],
        default_output_modes=["text"],
    )


def test_pinned_card_rewrites_url(monkeypatch) -> None:
    proxy = "https://jarvis.ascendingdc.com/proxy/a2a/aws_research"
    upstream_card = _make_upstream_card()

    async def fake_resolver_get_card(self, relative_card_path=None, http_kwargs=None, signature_verifier=None):
        return upstream_card

    monkeypatch.setattr("agents.a2a_client.A2ACardResolver.get_agent_card", fake_resolver_get_card)
    agent = PinnedEndpointA2AAgent(endpoint=proxy, name="aws_research")
    card = asyncio.run(agent.get_agent_card())
    assert str(card.url) == f"{proxy}/"
    # The pinned card is cached, so message sending targets the proxy too.
    assert agent._agent_card is card


def test_registry_proxy_card_fetch_uses_dot_free_path(monkeypatch) -> None:
    """The registry's ingress blocks nested ``.well-known`` paths, so proxied card fetches
    must use its dot-free ``agent-card.json`` alias instead of the A2A spec default."""
    proxy = "https://jarvis.ascendingdc.com/proxy/a2a/aws_research"
    upstream_card = _make_upstream_card()
    seen_paths: list[str | None] = []

    async def fake_resolver_get_card(self, relative_card_path=None, http_kwargs=None, signature_verifier=None):
        seen_paths.append(relative_card_path)
        return upstream_card

    monkeypatch.setattr("agents.a2a_client.A2ACardResolver.get_agent_card", fake_resolver_get_card)
    agent = PinnedEndpointA2AAgent(endpoint=proxy, name="aws_research")
    asyncio.run(agent.get_agent_card())
    assert seen_paths == ["agent-card.json"]


def test_direct_endpoint_card_fetch_uses_spec_default_path(monkeypatch) -> None:
    """A direct (non-registry) endpoint keeps the A2A spec default ``.well-known`` path."""
    direct = "https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/arn/invocations"
    upstream_card = _make_upstream_card()
    seen_paths: list[str | None] = []

    async def fake_resolver_get_card(self, relative_card_path=None, http_kwargs=None, signature_verifier=None):
        seen_paths.append(relative_card_path)
        return upstream_card

    monkeypatch.setattr("agents.a2a_client.A2ACardResolver.get_agent_card", fake_resolver_get_card)
    agent = PinnedEndpointA2AAgent(endpoint=direct, name="aws_research")
    asyncio.run(agent.get_agent_card())
    assert seen_paths == [None]
