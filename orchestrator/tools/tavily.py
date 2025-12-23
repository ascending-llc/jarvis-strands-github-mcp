"""Tavily API wrapper (placeholder endpoints; update when confirmed)."""

from typing import Any, Dict, Optional

import httpx

from orchestrator.config import AppConfig


def tavily_search(
    config: AppConfig,
    query: str,
    max_results: int = 8,
    include_domains: Optional[list[str]] = None,
    exclude_domains: Optional[list[str]] = None,
    timeframe: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "api_key": config.tavily_api_key,
        "query": query,
        "max_results": max_results,
    }
    if include_domains:
        payload["include_domains"] = include_domains
    if exclude_domains:
        payload["exclude_domains"] = exclude_domains
    if timeframe:
        payload["timeframe"] = timeframe

    url = f"{config.tavily_base_url}{config.tavily_search_path}"
    try:
        response = httpx.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return {"ok": True, "data": response.json()}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc), "data": None}


def tavily_extract(config: AppConfig, url: str) -> Dict[str, Any]:
    payload = {"api_key": config.tavily_api_key, "url": url}
    endpoint = f"{config.tavily_base_url}{config.tavily_extract_path}"
    try:
        response = httpx.post(endpoint, json=payload, timeout=30)
        response.raise_for_status()
        return {"ok": True, "data": response.json()}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc), "data": None}
