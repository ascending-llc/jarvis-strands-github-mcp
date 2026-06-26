"""Unified research worker engine.

One configurable Strands agent replaces the previously copy-pasted TavilyAgent /
PerplexityAgent. Workers differ only by:
  - their Skill (methodology, loaded on demand via progressive disclosure)
  - their output schema (the typed contract they must return)
  - the resolved domain scope passed in their system prompt role line

Capability (web research via Tavily MCP) and the agent loop are shared.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Type

from pydantic import BaseModel
from strands import Agent
from strands.vended_plugins.skills import AgentSkills

from agents.shared.bedrock import build_bedrock_model
from agents.shared.core.config import AppConfig
from agents.shared.mcp import build_tavily_mcp_client


def _system_prompt(role_line: str, schema: Type[BaseModel]) -> str:
    return (
        f"{role_line}\n\n"
        "You investigate using your web-research tools (search and extract). A research "
        "skill is available to you with the detailed methodology and source strategy — "
        "consult it. Form your own search queries; do not just echo the prompt. Be "
        "efficient: when the orchestrator has already resolved the company identity, do "
        "not re-derive it.\n\n"
        "When your research is complete, respond with ONLY a single JSON object that "
        "conforms to this JSON schema. No prose, no markdown fences:\n\n"
        f"{json.dumps(schema.model_json_schema(), indent=2)}"
    )


def build_research_agent(
    *,
    name: str,
    role_line: str,
    skill_dir: Path | str,
    output_schema: Type[BaseModel],
    config: AppConfig,
    mcp_client=None,
) -> Agent:
    """Build a research worker agent.

    The MCP client is a ToolProvider with its own background thread; pass a shared,
    already-started client so it is reused across A2A request contexts.
    """
    if mcp_client is None:
        mcp_client = build_tavily_mcp_client(config)
        mcp_client.start()

    return Agent(
        name=name,
        description=role_line,
        model=build_bedrock_model(config),
        system_prompt=_system_prompt(role_line, output_schema),
        tools=[mcp_client],
        plugins=[AgentSkills(skills=[str(skill_dir)])],
    )
