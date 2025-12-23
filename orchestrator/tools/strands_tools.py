"""Strands tool wrappers for Tavily APIs."""

from typing import Any, Dict, List, Optional

from strands import tool

from orchestrator.config import load_config
from orchestrator.tools.tavily import tavily_extract, tavily_search


@tool(name="tavily_search", description="Search the web using Tavily.")
def tavily_search_tool(
    query: str,
    max_results: int = 8,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    timeframe: Optional[str] = None,
) -> Dict[str, Any]:
    """Search the web using Tavily.

    Args:
        query: Search query string
        max_results: Maximum number of results
        include_domains: Optional list of domains to include
        exclude_domains: Optional list of domains to exclude
        timeframe: Optional timeframe hint (e.g., "1y")
    """
    config = load_config()
    return tavily_search(
        config=config,
        query=query,
        max_results=max_results,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        timeframe=timeframe,
    )


@tool(name="tavily_extract", description="Extract content from a URL using Tavily.")
def tavily_extract_tool(url: str) -> Dict[str, Any]:
    """Extract content from a URL using Tavily.

    Args:
        url: URL to extract
    """
    config = load_config()
    return tavily_extract(config=config, url=url)
