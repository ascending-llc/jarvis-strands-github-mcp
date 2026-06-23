"""Standalone A2A service for a single agent, powered by Strands' A2AServer.

One image serves any agent; AGENT_ID selects which. A2AServer handles the agent
card, the A2A HTTP/JSON + streaming (SSE) endpoints, task state, and per-context
isolation — replacing the previous hand-rolled a2a-sdk plumbing.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from strands.multiagent.a2a import A2AServer

from agents.deep_intel.orchestrator import build_orchestrator_agent
from agents.registry import AGENT_REGISTRY, AgentSpec
from agents.shared.core.config import load_config
from agents.shared.core.logging_config import setup_logging
from agents.shared.research_agent import build_research_agent
from agents.shared.tavily_mcp import build_tavily_mcp_client


def _load_spec() -> AgentSpec:
    agent_id = os.getenv("AGENT_ID", "").strip()
    if not agent_id:
        raise ValueError("AGENT_ID is required (deep_intel, aws_research, business_intel)")
    if agent_id not in AGENT_REGISTRY:
        raise ValueError(f"Unknown AGENT_ID: {agent_id}")
    return AGENT_REGISTRY[agent_id]


def create_app(agent_id: str | None = None) -> FastAPI:
    setup_logging()
    config = load_config()
    spec = AGENT_REGISTRY[agent_id] if agent_id else _load_spec()
    base_url = os.getenv("AGENT_BASE_URL", "http://localhost:8000").rstrip("/")

    if spec.kind == "orchestrator":
        def agent_factory(_context_id: str):
            return build_orchestrator_agent(config)
    else:
        # One shared, started MCP client (background-threaded ToolProvider) reused
        # across request contexts; a fresh agent is built per context.
        mcp_client = build_tavily_mcp_client(config)
        mcp_client.start()

        def agent_factory(_context_id: str):
            return build_research_agent(
                name=spec.name,
                role_line=spec.role_line,
                skill_dir=spec.skill_dir,
                output_schema=spec.output_schema,
                config=config,
                mcp_client=mcp_client,
            )

    server = A2AServer(
        agent_factory=agent_factory,
        skills=spec.a2a_skills,
        http_url=base_url,
        version="0.1.0",
        serve_at_root=True,
    )
    return server.to_fastapi_app()


app = create_app()
