"""A2A client helpers for agent-to-agent calls."""

from __future__ import annotations

import json
from typing import Any

from a2a.client.client import ClientConfig
from a2a.client.client_factory import ClientFactory
from a2a.client.helpers import create_text_message_object
from a2a.types import Message, Part, Role, Task, TextPart, TransportProtocol

from agents.registry import agent_service_url
from agents.shared.utils import extract_json_from_text


def _extract_text_from_part(part: Part) -> str | None:
    root = getattr(part, "root", None)
    if isinstance(root, TextPart):
        return root.text
    return None


def _extract_task_payload(task: Task) -> dict[str, Any]:
    if task.artifacts:
        for artifact in reversed(task.artifacts):
            for part in artifact.parts or []:
                text = _extract_text_from_part(part)
                if text:
                    return extract_json_from_text(text)
    if task.history:
        for message in reversed(task.history):
            for part in message.parts or []:
                text = _extract_text_from_part(part)
                if text:
                    return extract_json_from_text(text)
    return {}


def _extract_message_payload(message: Message) -> dict[str, Any]:
    for part in message.parts or []:
        text = _extract_text_from_part(part)
        if text:
            return extract_json_from_text(text)
    return {}


async def send_agent_request(agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    client_config = ClientConfig(supported_transports=[TransportProtocol.http_json])
    client = await ClientFactory.connect(agent_service_url(agent_id), client_config=client_config)
    message = create_text_message_object(role=Role.user, content=json.dumps(payload))
    latest_task: Task | None = None

    async for event in client.send_message(message):
        if isinstance(event, Message):
            return _extract_message_payload(event)
        latest_task = event[0]

    return _extract_task_payload(latest_task) if latest_task else {}
