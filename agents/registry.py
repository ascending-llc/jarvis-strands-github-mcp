"""Agent registry: specs, skill paths, output schemas, and A2A card skills.

One place that describes every agent the platform can serve. The server (server.py)
selects one by AGENT_ID and wraps it in a Strands A2AServer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Type
from urllib.parse import quote

from a2a.types import AgentSkill
from pydantic import BaseModel

from agents.shared.schemas import AwsFindings, CompanyProfile

SKILLS_DIR = Path(__file__).parent / "skills"


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    name: str
    description: str
    role_line: str
    kind: str  # "worker" | "orchestrator"
    a2a_skills: list[AgentSkill]
    skill_dir: Optional[Path] = None
    output_schema: Optional[Type[BaseModel]] = None
    url_env: Optional[str] = None  # env var holding this agent's base URL (local/docker callers)
    arn_env: Optional[str] = None  # env var holding this agent's AgentCore runtime ARN (deployed)


AGENT_REGISTRY: dict[str, AgentSpec] = {
    "aws_research": AgentSpec(
        agent_id="aws_research",
        name="AWS Research Agent",
        description="Finds AWS opportunities, case studies, and cloud-adoption signals.",
        role_line="You are an AWS-focused research analyst.",
        kind="worker",
        skill_dir=SKILLS_DIR / "aws-opportunity-research",
        output_schema=AwsFindings,
        url_env="AWS_RESEARCH_URL",
        arn_env="AWS_RESEARCH_AGENT_ARN",
        a2a_skills=[
            AgentSkill(
                id="aws-opportunity-research",
                name="AWS opportunity research",
                description="Find AWS opportunities, case studies, and cloud-adoption signals "
                "for a target company.",
                tags=["aws", "research", "case-studies", "cloud"],
            )
        ],
    ),
    "business_intel": AgentSpec(
        agent_id="business_intel",
        name="Business Intel Agent",
        description="Builds company profile, market position, tech stack, and leadership.",
        role_line="You are a company-intelligence research analyst.",
        kind="worker",
        skill_dir=SKILLS_DIR / "company-intelligence",
        output_schema=CompanyProfile,
        url_env="BUSINESS_INTEL_URL",
        arn_env="BUSINESS_INTEL_AGENT_ARN",
        a2a_skills=[
            AgentSkill(
                id="company-intelligence",
                name="Company intelligence research",
                description="Build a company profile: identity, market position, tech stack, "
                "and leadership.",
                tags=["company", "research", "market", "intelligence"],
            )
        ],
    ),
    "deep_intel": AgentSpec(
        agent_id="deep_intel",
        name="Deep Intel Agent",
        description="Orchestrates AWS research and business intelligence into a full report.",
        role_line="You are the master orchestrator for AWS customer intelligence.",
        kind="orchestrator",
        url_env="DEEP_INTEL_URL",
        a2a_skills=[
            AgentSkill(
                id="customer-intelligence-report",
                name="Customer intelligence report",
                description="Produce a full AWS customer-intelligence HTML report for a company "
                "domain by orchestrating specialist research agents.",
                tags=["aws", "report", "orchestration", "sales-intelligence"],
            )
        ],
    ),
}


def _agentcore_invocation_url(runtime_arn: str) -> str:
    """Build the AgentCore A2A invocation base URL for a runtime ARN.

    A2A clients resolve the agent card at ``<base>/.well-known/agent-card.json`` and
    POST JSON-RPC to ``<base>``.
    """
    region = os.getenv("AWS_REGION", "us-east-1")
    return (
        f"https://bedrock-agentcore.{region}.amazonaws.com/"
        f"runtimes/{quote(runtime_arn, safe='')}/invocations/"
    )


def agent_service_url(agent_id: str) -> str:
    """Resolve a target agent's base URL.

    Precedence: explicit URL env (local/docker-compose) → AgentCore runtime ARN env
    (deployed). A centralized discovery registry can later replace this lookup.
    """
    spec = AGENT_REGISTRY.get(agent_id)
    if spec and spec.url_env:
        url = os.getenv(spec.url_env)
        if url:
            return url.rstrip("/")
    if spec and spec.arn_env:
        arn = os.getenv(spec.arn_env)
        if arn:
            return _agentcore_invocation_url(arn)
    hints = [e for e in (spec.url_env, spec.arn_env) if spec and e]
    raise ValueError(f"Missing endpoint for agent: {agent_id} (set one of {hints or '?'})")
