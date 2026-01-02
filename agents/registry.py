"""Agent registry and URL helpers for the A2A gateway."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentRegistration:
    agent_id: str
    name: str
    path: str
    description: str


AGENT_REGISTRY = {
    "deep_intel": AgentRegistration(
        agent_id="deep_intel",
        name="Deep Intel Agent",
        path="/agents/deep-intel",
        description="Orchestrates AWS research and business intelligence into a full report.",
    ),
    "aws_research": AgentRegistration(
        agent_id="aws_research",
        name="AWS Research Agent",
        path="/agents/aws-research",
        description="Finds AWS opportunities, case studies, and cloud adoption signals.",
    ),
    "business_intel": AgentRegistration(
        agent_id="business_intel",
        name="Business Intel Agent",
        path="/agents/business-intel",
        description="Builds company profile, market position, and competitive intelligence.",
    ),
}


def gateway_base_url() -> str:
    return os.getenv("A2A_BASE_URL", "http://localhost:8000").rstrip("/")


def agent_base_url(agent_id: str) -> str:
    registration = AGENT_REGISTRY[agent_id]
    return f"{gateway_base_url()}{registration.path}"
