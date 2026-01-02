"""Shared helpers for A2A executors."""

from __future__ import annotations

import json
from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, Part, TextPart
from a2a.utils.message import new_agent_text_message

from agents.shared.core.logging_config import get_logger
from agents.shared.utils import extract_json_from_text


logger = get_logger(__name__)


def parse_request_payload(context: RequestContext) -> dict[str, Any]:
    user_input = context.get_user_input()
    if not user_input:
        return {}
    return extract_json_from_text(user_input)


def build_text_part(text: str) -> Part:
    return Part(root=TextPart(text=text))


def build_status_message(text: str, task_id: str, context_id: str) -> Message:
    return new_agent_text_message(text=text, task_id=task_id, context_id=context_id)


async def publish_json_artifact(
    updater: TaskUpdater,
    payload: dict[str, Any],
    name: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> None:
    await updater.add_artifact(
        parts=[build_text_part(json.dumps(payload))],
        name=name,
        metadata=metadata,
        last_chunk=True,
    )


async def publish_text_artifact(
    updater: TaskUpdater,
    text: str,
    name: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> None:
    await updater.add_artifact(
        parts=[build_text_part(text)],
        name=name,
        metadata=metadata,
        last_chunk=True,
    )


class BaseExecutor(AgentExecutor):
    """Base executor with common cancel handling."""

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or "unknown"
        context_id = context.context_id or "unknown"
        updater = TaskUpdater(event_queue, task_id=task_id, context_id=context_id)
        await updater.cancel(build_status_message("Task canceled", task_id, context_id))
