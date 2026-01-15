"""A2A executor that orchestrates the full deep intel workflow."""

from __future__ import annotations

from typing import Any

from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater

from agents.deep_intel.agent import DeepIntelAgent
from agents.shared.base_executor import (
    BaseExecutor,
    build_status_message,
    publish_text_artifact,
)
from agents.shared.core.logging_config import get_logger


logger = get_logger(__name__)


async def run_deep_intel(user_input: str) -> dict[str, Any]:
    agent = DeepIntelAgent()
    return await agent.run(user_input)


class DeepIntelExecutor(BaseExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or "unknown"
        context_id = context.context_id or "unknown"
        updater = TaskUpdater(event_queue, task_id=task_id, context_id=context_id)

        await updater.submit()
        await updater.start_work(build_status_message("Starting deep intel workflow", task_id, context_id))

        try:
            user_input = context.get_user_input()
            if not user_input:
                raise ValueError("No user input provided")

            result = await run_deep_intel(user_input)

            html_report = result.get("html_report")
            if html_report:
                await publish_text_artifact(
                    updater,
                    html_report,
                    "deep_intel_report.html",
                    metadata={"content_type": "text/html"},
                )

            await updater.complete(build_status_message("Deep intel workflow complete", task_id, context_id))
        except Exception as exc:
            logger.error("Deep intel workflow failed: %s", exc, exc_info=True)
            await updater.failed(build_status_message(f"Deep intel workflow failed: {exc}", task_id, context_id))
