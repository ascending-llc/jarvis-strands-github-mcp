"""Utility helpers for prompt loading and JSON handling."""

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


def load_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def parse_json_maybe(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Best-effort JSON extraction from model output."""

    parsed = parse_json_maybe(text)
    if parsed is not None:
        return parsed

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {"raw_text": text}

    candidate = text[start : end + 1]
    parsed = parse_json_maybe(candidate)
    if parsed is not None:
        return parsed

    return {"raw_text": text}


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def utc_timestamp() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
