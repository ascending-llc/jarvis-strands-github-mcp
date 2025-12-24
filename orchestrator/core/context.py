"""Shared workflow context for graph execution."""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class WorkflowContext:
    """Holds node outputs and shared metadata for the graph execution."""

    data: Dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)
