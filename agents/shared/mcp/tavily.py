"""Tavily web-research MCP client (search + extract), shared by both research workers."""

from __future__ import annotations

from strands.tools.mcp import MCPClient

from agents.shared.core.config import AppConfig
from agents.shared.core.exceptions import AgentError
from agents.shared.mcp.base import build_streamable_http_mcp_client


def build_tavily_mcp_client(config: AppConfig) -> MCPClient:
    """Build the Tavily MCP client, or raise if it is not configured."""
    if not config.tavily_mcp_url or not str(config.tavily_mcp_url).strip():
        raise AgentError("Tavily MCP is not configured (set TAVILY_MCP_URL)")

    return build_streamable_http_mcp_client(
        config.tavily_mcp_url,
        token=config.tavily_mcp_token,
        auth_header=config.tavily_mcp_auth_header or "Authorization",
        auth_prefix=config.tavily_mcp_auth_prefix or "",
        transport=config.tavily_mcp_transport or "streamable_http",
    )
