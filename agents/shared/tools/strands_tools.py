"""Tavily tool wrappers for Strands agents."""

from typing import Any, Dict, List, Optional

from strands import tool
from tavily import TavilyClient

from agents.shared.core.config import load_config
from agents.shared.core.exceptions import ToolError
from agents.shared.core.logging_config import get_logger

logger = get_logger(__name__)
config = load_config()

# Initialize Tavily client
_tavily_client = None


def _get_tavily_client() -> TavilyClient:
    """Get or create Tavily client singleton."""
    global _tavily_client
    if _tavily_client is None:
        if not config.tavily_api_key:
            raise ToolError("TAVILY_API_KEY not configured")
        _tavily_client = TavilyClient(api_key=config.tavily_api_key)
        logger.debug("Tavily client initialized")
    return _tavily_client


def _sanitize_query(query: str) -> str:
    tokens = query.split()
    if not tokens:
        return "company overview"
    non_site_tokens = [token for token in tokens if not token.lower().startswith("site:")]
    if not non_site_tokens:
        return f"{query} company overview"
    return query


def tavily_search(
    config: Any,
    query: str,
    max_results: int = 8,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    timeframe: Optional[str] = None,
) -> Dict[str, Any]:
    """Search using Tavily API.

    Args:
        config: Application configuration
        query: Search query string
        max_results: Maximum number of results
        include_domains: Optional list of domains to include
        exclude_domains: Optional list of domains to exclude
        timeframe: Optional timeframe hint (e.g., "1y")

    Returns:
        Dictionary with search results
    """
    try:
        client = _get_tavily_client()
        query = _sanitize_query(query)
        logger.debug(f"Executing Tavily search: query='{query}', max_results={max_results}")

        # Build search parameters
        search_params = {
            "query": query,
            "max_results": max_results,
        }

        if include_domains:
            search_params["include_domains"] = include_domains
        if exclude_domains:
            search_params["exclude_domains"] = exclude_domains
        if timeframe:
            search_params["days"] = _parse_timeframe_to_days(timeframe)

        # Execute search
        response = client.search(**search_params)

        logger.info(f"Tavily search completed: {len(response.get('results', []))} results")
        return {
            "ok": True,
            "query": query,
            "results": response.get("results", []),
            "answer": response.get("answer"),
            "images": response.get("images", []),
        }

    except Exception as e:
        logger.error(f"Tavily search failed: {e}", exc_info=True)
        raise ToolError(f"Tavily search failed: {e}") from e


def tavily_extract(config: Any, url: str) -> Dict[str, Any]:
    """Extract content from a URL using Tavily.

    Args:
        config: Application configuration
        url: URL to extract

    Returns:
        Dictionary with extracted content
    """
    try:
        client = _get_tavily_client()
        logger.debug(f"Executing Tavily extract: url='{url}'")

        # Execute extraction
        response = client.extract(urls=[url])

        # Extract the first result (we only passed one URL)
        results = response.get("results", [])
        if not results:
            logger.warning(f"Tavily extract returned no results for URL: {url}")
            return {
                "ok": False,
                "error": "No content extracted",
                "url": url,
            }

        extracted = results[0]
        logger.info(f"Tavily extract completed: {len(extracted.get('raw_content', ''))} chars")

        return {
            "ok": True,
            "url": extracted.get("url", url),
            "raw_content": extracted.get("raw_content", ""),
            "title": extracted.get("title", ""),
        }

    except Exception as e:
        logger.error(f"Tavily extract failed: {e}", exc_info=True)
        raise ToolError(f"Tavily extract failed: {e}") from e


def _parse_timeframe_to_days(timeframe: str) -> int:
    """Parse timeframe string (e.g., '1y', '6m', '30d') to days.

    Args:
        timeframe: Timeframe string

    Returns:
        Number of days
    """
    timeframe = timeframe.lower().strip()

    if timeframe.endswith('d'):
        return int(timeframe[:-1])
    elif timeframe.endswith('w'):
        return int(timeframe[:-1]) * 7
    elif timeframe.endswith('m'):
        return int(timeframe[:-1]) * 30
    elif timeframe.endswith('y'):
        return int(timeframe[:-1]) * 365
    else:
        logger.warning(f"Unknown timeframe format: {timeframe}, defaulting to 365 days")
        return 365


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

    Returns:
        Dictionary with search results or error information
    """
    logger.debug(f"Tool tavily_search called with query: {query}")
    try:
        result = tavily_search(
            config=config,
            query=query,
            max_results=max_results,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            timeframe=timeframe,
        )
        return result
    except ToolError as e:
        logger.error(f"Tavily search tool failed: {e}")
        return {"ok": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in tavily_search_tool: {e}", exc_info=True)
        return {"ok": False, "error": f"Unexpected error: {e}"}


@tool(name="tavily_extract", description="Extract content from a URL using Tavily.")
def tavily_extract_tool(url: str) -> Dict[str, Any]:
    """Extract content from a URL using Tavily.

    Args:
        url: URL to extract

    Returns:
        Dictionary with extracted content or error information
    """
    logger.debug(f"Tool tavily_extract called for URL: {url}")
    try:
        result = tavily_extract(config=config, url=url)
        return result
    except ToolError as e:
        logger.error(f"Tavily extract tool failed: {e}")
        return {"ok": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in tavily_extract_tool: {e}", exc_info=True)
        return {"ok": False, "error": f"Unexpected error: {e}"}
