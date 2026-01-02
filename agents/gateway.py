"""Build and register A2A agent sub-apps."""

from __future__ import annotations

from a2a.server.apps.rest.fastapi_app import A2ARESTFastAPIApplication
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import AgentSkill

from agents.agent_cards import build_agent_card
from agents.aws_research.executor import AwsResearchExecutor
from agents.business_intel.executor import BusinessIntelExecutor
from agents.deep_intel.executor import DeepIntelExecutor
from agents.registry import AGENT_REGISTRY


def _deep_intel_skills() -> list[AgentSkill]:
    return [
        AgentSkill(
            id="deep_intel_report",
            name="Deep Intel Report",
            description="Run AWS research and business intelligence, then synthesize a full report.",
            tags=["research", "orchestration", "aws", "intelligence"],
            examples=["Analyze atscale.com for AWS opportunities"],
        )
    ]


def _aws_research_skills() -> list[AgentSkill]:
    return [
        AgentSkill(
            id="aws_research",
            name="AWS Research",
            description="Search for AWS opportunities, case studies, and cloud adoption signals.",
            tags=["aws", "research", "case-study"],
            examples=["Find AWS case studies for fintech companies"],
        )
    ]


def _business_intel_skills() -> list[AgentSkill]:
    return [
        AgentSkill(
            id="business_intel",
            name="Business Intelligence",
            description="Profile a company, its market position, and competitive landscape.",
            tags=["business", "market", "competitive"],
            examples=["Summarize company profile for atscale.com"],
        )
    ]


def build_agent_apps() -> dict[str, object]:
    deep_intel_registration = AGENT_REGISTRY["deep_intel"]
    aws_research_registration = AGENT_REGISTRY["aws_research"]
    business_intel_registration = AGENT_REGISTRY["business_intel"]

    deep_intel_card = build_agent_card(deep_intel_registration, _deep_intel_skills())
    aws_research_card = build_agent_card(aws_research_registration, _aws_research_skills())
    business_intel_card = build_agent_card(business_intel_registration, _business_intel_skills())

    deep_intel_app = A2ARESTFastAPIApplication(
        agent_card=deep_intel_card,
        http_handler=DefaultRequestHandler(
            agent_executor=DeepIntelExecutor(),
            task_store=InMemoryTaskStore(),
        ),
    ).build()

    aws_research_app = A2ARESTFastAPIApplication(
        agent_card=aws_research_card,
        http_handler=DefaultRequestHandler(
            agent_executor=AwsResearchExecutor(),
            task_store=InMemoryTaskStore(),
        ),
    ).build()

    business_intel_app = A2ARESTFastAPIApplication(
        agent_card=business_intel_card,
        http_handler=DefaultRequestHandler(
            agent_executor=BusinessIntelExecutor(),
            task_store=InMemoryTaskStore(),
        ),
    ).build()

    return {
        deep_intel_registration.path: deep_intel_app,
        aws_research_registration.path: aws_research_app,
        business_intel_registration.path: business_intel_app,
    }
