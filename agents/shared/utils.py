
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from agents.shared.core.logging_config import get_logger

logger = get_logger(__name__)

PROMPT_DIR = Path(__file__).parent / "prompts"


def load_prompt(path: str) -> str:
    prompt_path = Path(path)
    if not prompt_path.is_absolute():
        prompt_path = PROMPT_DIR / path
    with open(prompt_path, "r", encoding="utf-8") as handle:
        return handle.read()


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Parse a JSON object from a text blob."""
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return {"raw_text": text}


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def utc_timestamp() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


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


def format_task(task: Dict[str, Any]) -> str:
    """Format a task payload into a single string for the graph."""
    if task.get("user_input"):
        return task["user_input"]
    lines = []
    for key, value in task.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)
