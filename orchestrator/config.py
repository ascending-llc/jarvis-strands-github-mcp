"""Runtime configuration for the Strands orchestration service."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    tavily_api_key: str
    perplexity_api_key: str
    tavily_base_url: str
    tavily_search_path: str
    tavily_extract_path: str
    perplexity_base_url: str
    perplexity_chat_path: str
    perplexity_model: str
    report_output_dir: str


def load_config() -> AppConfig:
    return AppConfig(
        tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
        perplexity_api_key=os.getenv("PERPLEXITY_API_KEY", ""),
        # Placeholder endpoints; update once confirmed.
        tavily_base_url=os.getenv("TAVILY_BASE_URL", "https://api.tavily.com"),
        tavily_search_path=os.getenv("TAVILY_SEARCH_PATH", "/search"),
        tavily_extract_path=os.getenv("TAVILY_EXTRACT_PATH", "/extract"),
        perplexity_base_url=os.getenv("PERPLEXITY_BASE_URL", "https://api.perplexity.ai"),
        perplexity_chat_path=os.getenv("PERPLEXITY_CHAT_PATH", "/chat/completions"),
        perplexity_model=os.getenv("PERPLEXITY_MODEL", "sonar"),
        report_output_dir=os.getenv("REPORT_OUTPUT_DIR", "reports"),
    )
