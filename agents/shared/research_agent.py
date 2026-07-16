"""Unified research worker engine.

One configurable Strands agent replaces the previously copy-pasted TavilyAgent /
PerplexityAgent. Workers differ only by:
  - their Skill (methodology, loaded on demand via progressive disclosure)
  - their output schema (the typed contract they must return)
  - the resolved domain scope passed in their system prompt role line

Output is produced via Strands structured output (``structured_output_model``): the
schema is enforced by the provider at decode time, so the final answer is always a
valid instance of the contract — no prompt-embedded JSON schema, no text parsing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Type

from pydantic import BaseModel
from strands import Agent
from strands.vended_plugins.skills import AgentSkills

from agents.shared.bedrock import build_bedrock_model
from agents.shared.core.config import AppConfig


def _system_prompt(role_line: str) -> str:
    return (
        f"{role_line}\n\n"
        "You investigate using your web-research tools (search and extract) when available. "
        "A research skill is available to you with the detailed methodology and source "
        "strategy — consult it. Form your own search queries; do not just echo the prompt. "
        "Be efficient: when the orchestrator has already resolved the company identity, do "
        "not re-derive it. Prefer cited, recent facts; omit what you cannot confirm and "
        "lower your confidence rating rather than guessing."
    )


def build_research_agent(
    *,
    name: str,
    role_line: str,
    skill_dir: Path | str,
    output_schema: Type[BaseModel],
    config: AppConfig,
    tools: list = (),
) -> Agent:
    """Build a research worker agent.

    Capability-agnostic: the caller supplies whatever tools (e.g. started MCP clients)
    this agent should have — see agents/registry.py (AgentSpec.mcp_servers) for what each
    agent actually gets. The output schema is enforced natively via structured output.
    """
    return Agent(
        name=name,
        description=role_line,
        model=build_bedrock_model(config),
        system_prompt=_system_prompt(role_line),
        tools=list(tools),
        structured_output_model=output_schema,
        plugins=[AgentSkills(skills=[str(skill_dir)])],
    )
