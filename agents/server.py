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

from bedrock_agentcore.runtime import serve_a2a
from strands.multiagent.a2a.executor import StrandsA2AExecutor

from agents.deep_intel.orchestrator import build_orchestrator_agent
from agents.registry import AGENT_REGISTRY, AgentSpec
from agents.shared.core.config import load_config
from agents.shared.core.logging_config import get_logger, setup_logging
from agents.shared.mcp import build_tavily_mcp_client
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

    A fresh agent is built per request context (isolation). Workers share one
    started Tavily MCP client (a background-threaded ToolProvider) across contexts.
    """
    if spec.kind == "orchestrator":
        def agent_factory(_context_id: str):
            return build_orchestrator_agent(config)
    else:
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

    # enable_a2a_compliant_streaming surfaces token/event streaming over A2A SSE —
    # the streaming goal of this refactor. Flip to False to fall back to single-shot.
    return StrandsA2AExecutor(agent_factory=agent_factory, enable_a2a_compliant_streaming=True)


def main() -> None:
    setup_logging()
    config = load_config()
    spec = _load_spec()
    port = int(os.getenv("PORT", str(DEFAULT_PORT)))
    logger.info("Starting A2A server for agent_id=%s on port %s", spec.agent_id, port)
    executor = build_executor(spec, config)
    # agent_card=None → serve_a2a auto-builds the card by introspecting the executor.
    # (To advertise spec.a2a_skills explicitly, build an a2a.types.AgentCard and pass it.)
    serve_a2a(executor, port=port)


if __name__ == "__main__":
    main()
