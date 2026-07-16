"""Small filesystem/report helpers."""

from __future__ import annotations

import os
from datetime import datetime, timezone


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def save_report(html: str, output_path: str) -> str:
    """Write the HTML report to disk and return its absolute path."""
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
