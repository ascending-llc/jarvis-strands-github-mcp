"""Agent card builders for standalone A2A services."""

from __future__ import annotations

from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentProvider,
    AgentSkill,
    TransportProtocol,
)

from agents.registry import AgentRegistration, agent_base_url


DEFAULT_AGENT_VERSION = "0.1.0"
DEFAULT_INPUT_MODES = ["text/plain", "application/json"]
DEFAULT_OUTPUT_MODES = ["application/json", "text/plain", "text/html"]


def build_agent_card(
    registration: AgentRegistration,
    skills: list[AgentSkill],
    version: str = DEFAULT_AGENT_VERSION,
    base_url: str | None = None,
) -> AgentCard:
    base_url = (base_url or agent_base_url(registration.agent_id)).rstrip("/")
    return AgentCard(
        name=registration.name,
        description=registration.description,
        url=base_url,
        version=version,
        protocol_version="0.3.0",
        preferred_transport=TransportProtocol.http_json,
        capabilities=AgentCapabilities(
            streaming=True,
            push_notifications=False,
            state_transition_history=False,
        ),
        default_input_modes=DEFAULT_INPUT_MODES,
        default_output_modes=DEFAULT_OUTPUT_MODES,
        provider=AgentProvider(
            organization="AWS Customer Intelligence Orchestrator",
            url="https://strandsagents.com",
        ),
        skills=skills,
        additional_interfaces=[
            AgentInterface(transport=TransportProtocol.http_json, url=base_url),
        ],
    )
