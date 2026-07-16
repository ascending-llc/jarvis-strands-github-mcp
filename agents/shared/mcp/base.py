"""Reusable MCP client builder.

Most MCP integrations are a remote streamable-HTTP server distinguished only by URL +
auth header, so they share this builder. Add a new client (web research, agent-discovery
registry, ...) as its own module in this package that wraps this helper.
"""

from __future__ import annotations

from typing import Optional

from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient


def build_streamable_http_mcp_client(
    url: str,
    *,
    token: Optional[str] = None,
    auth_header: str = "Authorization",
    auth_prefix: str = "Bearer ",
    transport: str = "streamable_http",
) -> MCPClient:
    """Build a streamable-HTTP MCP client.

    Returns a ToolProvider with its own background thread; call ``.start()`` once and
    reuse it across request contexts rather than building one per call.
    """
    if not url or not str(url).strip():
        raise ValueError("MCP client URL is required")

    transport = str(transport or "streamable_http").lower()
    if transport != "streamable_http":
        raise ValueError(f"Unsupported MCP transport: {transport}")

    headers: Optional[dict[str, str]] = None
    if token:
        headers = {auth_header: f"{auth_prefix}{token}"}

    return MCPClient(lambda: streamablehttp_client(url=str(url), headers=headers))
