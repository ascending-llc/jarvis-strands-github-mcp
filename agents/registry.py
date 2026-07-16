"""Agent registry: specs, skill paths, output schemas, and A2A card skills.

One place that describes every agent the platform can serve. The server (server.py)
selects one by AGENT_ID and wraps it in a Strands A2AServer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Type
from urllib.parse import quote

from a2a.types import AgentSkill
from pydantic import BaseModel
from strands.tools.mcp import MCPClient

from agents.shared.core.config import AppConfig
from agents.shared.mcp import build_tavily_mcp_client
from agents.shared.schemas import AwsFindings, CompanyProfile

SKILLS_DIR = Path(__file__).parent / "skills"

# Maps a short name (used in AgentSpec.mcp_servers) to its client builder. Any agent can
# opt into any MCP server by listing its name in the registry — capability is a per-agent
# declaration here, not a hardcoded branch on agent kind in server.py.
MCP_BUILDERS: dict[str, Callable[[AppConfig], MCPClient]] = {
    "tavily": build_tavily_mcp_client,
}


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
    mcp_servers: list[str] = field(default_factory=list)  # names into MCP_BUILDERS this agent uses


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
        mcp_servers=["tavily"],
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
        mcp_servers=["tavily"],
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


def _registry_proxy_url(agent_id: str) -> Optional[str]:
    """Build the Jarvis registry A2A proxy URL for an agent, or None if no registry is set.

    The registry proxies standard A2A at ``{REGISTRY_URL}/api/v1/proxy/a2a/{path}``:
    it looks up the agent by its registry ``path`` slug, enforces ACLs, mints the
    downstream AgentCore runtime JWT, and forwards the unchanged A2A request. The
    path defaults to the agent id; override per agent with ``<AGENT_ID>_REGISTRY_PATH``
    if it was registered under a different slug.
    """
    registry_url = os.getenv("REGISTRY_URL")
    if not registry_url:
        return None
    path = os.getenv(f"{agent_id.upper()}_REGISTRY_PATH", agent_id)
    return f"{registry_url.rstrip('/')}/api/v1/proxy/a2a/{quote(path, safe='')}"


def agent_service_url(agent_id: str) -> str:
    """Resolve a target agent's base URL.

    Precedence: explicit URL env (local/docker-compose) → Jarvis registry proxy
    (``REGISTRY_URL``, deployed) → AgentCore runtime ARN env (deployed, direct).
    """
    spec = AGENT_REGISTRY.get(agent_id)
    if spec and spec.url_env:
        url = os.getenv(spec.url_env)
        if url:
            return url.rstrip("/")
    if spec:
        registry_url = _registry_proxy_url(agent_id)
        if registry_url:
            return registry_url
    if spec and spec.arn_env:
        arn = os.getenv(spec.arn_env)
        if arn:
            return _agentcore_invocation_url(arn)
    hints = [e for e in (spec.url_env, spec.arn_env) if spec and e] + ["REGISTRY_URL"]
    raise ValueError(f"Missing endpoint for agent: {agent_id} (set one of {hints})")
