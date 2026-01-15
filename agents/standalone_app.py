"""Standalone A2A service for a single agent."""

from __future__ import annotations

import os

from a2a.server.apps.rest.fastapi_app import A2ARESTFastAPIApplication
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from fastapi import FastAPI

from agents.agent_cards import build_agent_card
from agents.aws_research.executor import AwsResearchExecutor
from agents.business_intel.executor import BusinessIntelExecutor
from agents.deep_intel.executor import DeepIntelExecutor
from agents.registry import AGENT_REGISTRY, service_base_url
from agents.shared.core.logging_config import setup_logging
from agents.skills import (
    aws_research_skills,
    business_intel_skills,
    deep_intel_skills,
)


_EXECUTORS = {
    "deep_intel": DeepIntelExecutor,
    "aws_research": AwsResearchExecutor,
    "business_intel": BusinessIntelExecutor,
}

_SKILLS = {
    "deep_intel": deep_intel_skills,
    "aws_research": aws_research_skills,
    "business_intel": business_intel_skills,
}


def _load_agent_id() -> str:
    agent_id = os.getenv("AGENT_ID", "").strip()
    if not agent_id:
        raise ValueError("AGENT_ID is required (deep_intel, aws_research, business_intel)")
    if agent_id not in AGENT_REGISTRY:
        raise ValueError(f"Unknown AGENT_ID: {agent_id}")
    return agent_id


def create_app(agent_id: str | None = None) -> FastAPI:
    setup_logging()
    agent_id = agent_id or _load_agent_id()
    registration = AGENT_REGISTRY[agent_id]
    base_url = service_base_url()
    agent_card = build_agent_card(
        registration,
        _SKILLS[agent_id](),
        base_url=base_url,
    )
    executor_cls = _EXECUTORS[agent_id]

    return A2ARESTFastAPIApplication(
        agent_card=agent_card,
        http_handler=DefaultRequestHandler(
            agent_executor=executor_cls(),
            task_store=InMemoryTaskStore(),
        ),
    ).build()


app = create_app()
