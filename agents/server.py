"""AgentCore-compatible A2A entrypoint for a single agent.

One image serves any agent; ``AGENT_ID`` selects which. The server is started via
``bedrock_agentcore.runtime.serve_a2a`` — the AWS-supported A2A entrypoint that
binds the AgentCore A2A contract (port 9000 at ``/``, ``/ping`` health, agent-card
serving, Bedrock header propagation) and runs the Strands agent through
``StrandsA2AExecutor``.

Run locally or in a container the same way::

    AGENT_ID=deep_intel uv run python -m agents.server
"""

from __future__ import annotations

import os

from a2a.types import AgentCapabilities, AgentCard
from bedrock_agentcore.runtime import serve_a2a
from strands.multiagent.a2a.executor import StrandsA2AExecutor

from agents.deep_intel.orchestrator import build_orchestrator_agent
from agents.registry import AGENT_REGISTRY, MCP_BUILDERS, AgentSpec
from agents.shared.core.config import load_config
from agents.shared.core.logging_config import get_logger, setup_logging
from agents.shared.research_agent import build_research_agent

logger = get_logger(__name__)

# AgentCore's A2A contract serves on 9000 at the root path; honor PORT for local overrides.
DEFAULT_PORT = 9000


def _load_spec() -> AgentSpec:
    agent_id = os.getenv("AGENT_ID", "").strip()
    if not agent_id:
        raise ValueError("AGENT_ID is required (deep_intel, aws_research, business_intel)")
    if agent_id not in AGENT_REGISTRY:
        raise ValueError(f"Unknown AGENT_ID: {agent_id}")
    return AGENT_REGISTRY[agent_id]


def build_executor(spec: AgentSpec, config) -> StrandsA2AExecutor:
    """Build the A2A executor for a spec.

    A fresh agent is built per request context (isolation). MCP capability is declared
    per-agent in the registry (``AgentSpec.mcp_servers``), not hardcoded by agent kind —
    any agent, worker or orchestrator, can opt into any MCP server this way. Each named
    server is started once per process and shared across contexts.
    """
    mcp_tools = []
    for mcp_name in spec.mcp_servers:
        client = MCP_BUILDERS[mcp_name](config)
        client.start()
        mcp_tools.append(client)

    if spec.kind == "orchestrator":
        def agent_factory(_context_id: str):
            return build_orchestrator_agent(config, extra_tools=mcp_tools)
    else:
        def agent_factory(_context_id: str):
            return build_research_agent(
                name=spec.name,
                role_line=spec.role_line,
                skill_dir=spec.skill_dir,
                output_schema=spec.output_schema,
                config=config,
                tools=mcp_tools,
            )

    # Streaming mode differs by kind:
    # - orchestrator: A2A-compliant streaming ON — the client sees the report stream live.
    # - workers: OFF (legacy mode). Workers return one structured-output JSON artifact;
    #   in compliant mode any mid-loop narration streams into the artifact and the final
    #   structured JSON is dropped (executor only includes str(result) when nothing was
    #   streamed). Legacy mode sends narration as status updates and the artifact is
    #   exactly the structured JSON.
    streaming = spec.kind == "orchestrator"
    return StrandsA2AExecutor(agent_factory=agent_factory, enable_a2a_compliant_streaming=streaming)


def _build_agent_card(spec: AgentSpec, port: int) -> AgentCard:
    """Build the real agent card from the registry spec.

    serve_a2a's auto-builder only introspects a single top-level ``executor.agent``; we use
    ``agent_factory`` (agents are built lazily per A2A context), so there is no such attribute
    and it falls back to generic "agent"/"main" defaults. We already have everything real
    (name, description, skills) in the spec, so build the card explicitly instead.

    CRITICAL: A2A clients send messages to ``card.url`` (the endpoint they were given is only
    used to fetch the card). The URL must therefore be the address at which OTHER agents reach
    this one — in docker-compose that's the service DNS name (AGENT_BASE_URL per service), never
    ``localhost``, which inside a caller's container points at the caller itself and causes
    infinite self-recursion. When deployed, AgentCore overrides card.url with the real runtime
    URL via the AGENTCORE_RUNTIME_URL env var.
    """
    base_url = os.getenv("AGENT_BASE_URL", f"http://localhost:{port}")
    return AgentCard(
        name=spec.name,
        description=spec.description,
        url=f"{base_url.rstrip('/')}/",
        version="0.1.0",
        capabilities=AgentCapabilities(streaming=True),
        skills=spec.a2a_skills,
        default_input_modes=["text"],
        default_output_modes=["text"],
    )


def main() -> None:
    setup_logging()
    config = load_config()
    spec = _load_spec()
    port = int(os.getenv("PORT", str(DEFAULT_PORT)))
    logger.info("Starting A2A server for agent_id=%s on port %s", spec.agent_id, port)
    executor = build_executor(spec, config)
    agent_card = _build_agent_card(spec, port)
    serve_a2a(executor, agent_card=agent_card, port=port)


if __name__ == "__main__":
    main()
