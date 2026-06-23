"""Shared Tavily MCP client builder.

Both research workers use the same web-research capability (Tavily search +
extract) exposed as an MCP server. Differentiation between workers is their
skill and output schema, not their tools.
"""

from __future__ import annotations

from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

from agents.shared.core.config import AppConfig
from agents.shared.core.exceptions import AgentError


def build_tavily_mcp_client(config: AppConfig) -> MCPClient:
    """Build the Tavily MCP client, or raise if it is not configured."""
    if not config.tavily_mcp_url or not str(config.tavily_mcp_url).strip():
        raise AgentError("Tavily MCP is not configured (set TAVILY_MCP_URL)")

    transport = str(config.tavily_mcp_transport or "streamable_http").lower()
    if transport != "streamable_http":
        raise ValueError(f"Unsupported Tavily MCP transport: {transport}")

    headers: dict[str, str] | None = None
    if config.tavily_mcp_token:
        auth_header = config.tavily_mcp_auth_header or "Authorization"
        auth_prefix = config.tavily_mcp_auth_prefix or ""
        headers = {auth_header: f"{auth_prefix}{config.tavily_mcp_token}"}

    return MCPClient(
        lambda: streamablehttp_client(url=str(config.tavily_mcp_url), headers=headers)
    )
