"""Utility helpers for prompt loading, JSON handling, and report rendering."""

import json
import codecs
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader

from agents.shared.core.logging_config import get_logger

logger = get_logger(__name__)

# Template directory for HTML reports
TEMPLATE_DIR = Path(__file__).parent / "templates"
PROMPT_DIR = Path(__file__).parent / "prompts"


def load_prompt(path: str) -> str:
    prompt_path = Path(path)
    if not prompt_path.is_absolute():
        prompt_path = PROMPT_DIR / path
    with open(prompt_path, "r", encoding="utf-8") as handle:
        return handle.read()


def parse_json_maybe(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _parse_json_with_unescape(text: str) -> Optional[Dict[str, Any]]:
    parsed = parse_json_maybe(text)
    if parsed is not None:
        return parsed
    try:
        unescaped = codecs.decode(text, "unicode_escape")
    except Exception:
        unescaped = text.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
    return parse_json_maybe(unescaped)


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Best-effort JSON extraction from model output."""

    # Handle fenced code blocks like ```json ... ```
    if "```" in text:
        fence_start = text.find("```")
        fence_end = text.rfind("```")
        if fence_start != -1 and fence_end != -1 and fence_end > fence_start:
            fenced = text[fence_start + 3 : fence_end].strip()
            # Strip optional language tag
            if "\n" in fenced:
                first_line, rest = fenced.split("\n", 1)
                if first_line.strip().lower() in {"json", "javascript"}:
                    fenced = rest.strip()
            parsed = _parse_json_with_unescape(fenced)
            if parsed is not None:
                return parsed

    parsed = _parse_json_with_unescape(text)
    if parsed is not None:
        return parsed

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {"raw_text": text}

    candidate = text[start : end + 1]
    parsed = _parse_json_with_unescape(candidate)
    if parsed is not None:
        return parsed

    return {"raw_text": text}


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def utc_timestamp() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


# ============================================================================
# HTML Report Rendering
# ============================================================================

def get_jinja_env() -> Environment:
    """Get Jinja2 environment configured for template rendering.

    Returns:
        Jinja2 Environment with template loader
    """
    if not TEMPLATE_DIR.exists():
        raise FileNotFoundError(f"Template directory not found: {TEMPLATE_DIR}")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    return env


def render_report(data: Dict[str, Any]) -> str:
    """Render HTML report from aggregated data.

    Args:
        data: Dictionary with aggregated research findings

    Returns:
        Rendered HTML string

    Raises:
        ValueError: If required data fields are missing
    """
    logger.info("Rendering HTML report from aggregated data")

    # Validate required fields
    required_fields = ["company_overview", "confidence_level", "research_completeness"]
    missing = [field for field in required_fields if field not in data]

    if missing:
        raise ValueError(f"Missing required fields for rendering: {missing}")

    # Get Jinja2 environment
    env = get_jinja_env()
    template = env.get_template("report.html")

    # Render template
    try:
        html = template.render(**data)
        logger.info("HTML report rendered successfully (%d chars)", len(html))
        return html
    except Exception as e:
        logger.error("Failed to render HTML template: %s", e, exc_info=True)
        raise ValueError(f"Template rendering failed: {e}") from e


def save_report(html: str, output_path: str) -> str:
    """Save rendered HTML report to disk.

    Args:
        html: Rendered HTML string
        output_path: Path to save the HTML file

    Returns:
        Absolute path to saved file
    """
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info("HTML report saved to: %s", output_path)
    return output_path


def extract_node_json(graph_result: Any, node_id: str) -> Dict[str, Any]:
    """Extract JSON from a node's result in the graph.

    Handles Strands agent response format where content is in:
    {'role': 'assistant', 'content': [{'text': '...'}]}
    """
    node_result = graph_result.results.get(node_id) if graph_result and graph_result.results else None
    if not node_result:
        return {}

    agent_result = getattr(node_result, "result", None)
    message = getattr(agent_result, "message", None)
    text = str(message) if message is not None else str(agent_result)

    try:
        import ast

        response_dict = ast.literal_eval(text)
        if isinstance(response_dict, dict) and "content" in response_dict:
            content = response_dict["content"]
            if isinstance(content, list) and len(content) > 0:
                if isinstance(content[0], dict) and "text" in content[0]:
                    text = content[0]["text"]
    except (ValueError, SyntaxError, KeyError, IndexError):
        pass

    parsed = extract_json_from_text(text)
    return parsed or {}


def format_task(task: Dict[str, Any]) -> str:
    """Format a task payload into a single string for the graph."""
    if task.get("user_input"):
        return task["user_input"]
    lines = []
    for key, value in task.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)
