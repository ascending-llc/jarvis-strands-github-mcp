"""MCP client builders. One module per integration; all share base.py.

Add future clients here (e.g. an agent-discovery registry MCP) and export them below.
"""

from agents.shared.mcp.base import build_streamable_http_mcp_client
from agents.shared.mcp.tavily import build_tavily_mcp_client

__all__ = ["build_streamable_http_mcp_client", "build_tavily_mcp_client"]
