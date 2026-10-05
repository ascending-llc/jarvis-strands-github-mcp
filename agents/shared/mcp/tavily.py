"""Tavily web-research MCP client (search + extract), shared by both research workers."""

from __future__ import annotations

from strands.tools.mcp import MCPClient

from agents.shared.auth import get_bearer_token
from agents.shared.core.config import AppConfig
from agents.shared.core.exceptions import AgentError
from agents.shared.mcp.base import build_streamable_http_mcp_client


def build_tavily_mcp_client(config: AppConfig) -> MCPClient:
    """Build the Tavily MCP client, or raise if it is not configured.

    The Tavily gateway is served by the same Jarvis registry proxy as inter-agent A2A
    calls (``/gateway/proxy/internet`` → ``/proxy/internet``), gated by the same
    managed-agent bearer token requirement. Reuse ``get_bearer_token()`` so this agent
    doesn't need a second, separately-provisioned secret just for Tavily; an explicit
    ``TAVILY_MCP_TOKEN`` still overrides it for local/non-registry endpoints.
    """
    if not config.tavily_mcp_url or not str(config.tavily_mcp_url).strip():
        raise AgentError("Tavily MCP is not configured (set TAVILY_MCP_URL)")

    return build_streamable_http_mcp_client(
        config.tavily_mcp_url,
        token=config.tavily_mcp_token or get_bearer_token(),
        auth_header=config.tavily_mcp_auth_header or "Authorization",
        auth_prefix=config.tavily_mcp_auth_prefix or "",
        transport=config.tavily_mcp_transport or "streamable_http",
    )
