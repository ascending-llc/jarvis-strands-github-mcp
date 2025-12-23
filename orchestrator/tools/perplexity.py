"""Perplexity Sonar API wrapper (placeholder endpoints; update when confirmed)."""

from typing import Any, Dict, List

import httpx

from orchestrator.config import AppConfig


def perplexity_query(
    config: AppConfig,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1200,
    temperature: float = 0.2,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": config.perplexity_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {config.perplexity_api_key}",
        "Content-Type": "application/json",
    }
    url = f"{config.perplexity_base_url}{config.perplexity_chat_path}"
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        return {"ok": True, "data": response.json()}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc), "data": None}
