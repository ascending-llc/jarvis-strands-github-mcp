"""Agent registry and URL helpers for standalone A2A services."""

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


def service_base_url() -> str:
    return os.getenv("AGENT_BASE_URL", "http://localhost:8000").rstrip("/")


def agent_service_url(agent_id: str) -> str:
    env_map = {
        "deep_intel": "DEEP_INTEL_URL",
        "aws_research": "AWS_RESEARCH_URL",
        "business_intel": "BUSINESS_INTEL_URL",
    }
    env_var = env_map.get(agent_id)
    if env_var:
        url = os.getenv(env_var)
        if url:
            return url.rstrip("/")
    raise ValueError(f"Missing base URL for agent: {agent_id}")
