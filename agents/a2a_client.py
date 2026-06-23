"""Thin A2A client for deterministic, parallel worker calls.

The server side is owned by Strands' A2AServer. On the client side we keep a small
deterministic caller so the orchestrator can fan out to workers with guaranteed
parallelism (asyncio.gather) rather than relying on model-driven tool calls.
"""

from __future__ import annotations

from a2a.client.client import ClientConfig
from a2a.client.client_factory import ClientFactory
from a2a.client.helpers import create_text_message_object
from a2a.types import Message, Part, Role, Task, TextPart, TransportProtocol

from agents.registry import agent_service_url


def _text_from_part(part: Part) -> str | None:
    root = getattr(part, "root", None)
    if isinstance(root, TextPart):
        return root.text
    return None


def _final_text(task: Task | None) -> str:
    if task is None:
        return ""
    if task.artifacts:
        for artifact in reversed(task.artifacts):
            for part in artifact.parts or []:
                if text := _text_from_part(part):
                    return text
    if task.history:
        for message in reversed(task.history):
            for part in message.parts or []:
                if text := _text_from_part(part):
                    return text
    return ""


async def call_agent_text(agent_id: str, prompt: str) -> str:
    """Send a prompt to a remote A2A agent and return its final text artifact."""
    client_config = ClientConfig(
        supported_transports=[TransportProtocol.jsonrpc, TransportProtocol.http_json]
    )
    client = await ClientFactory.connect(agent_service_url(agent_id), client_config=client_config)
    message = create_text_message_object(role=Role.user, content=prompt)

    latest_task: Task | None = None
    async for event in client.send_message(message):
        if isinstance(event, Message):
            for part in event.parts or []:
                if text := _text_from_part(part):
                    return text
            return ""
        latest_task = event[0]

    return _final_text(latest_task)
