"""A2A executor for AWS-focused research."""

from __future__ import annotations

from typing import Any

from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater

from agents.shared.base_executor import (
    BaseExecutor,
    build_status_message,
    parse_request_payload,
    publish_json_artifact,
)
from agents.aws_research.research_agent import TavilyAgent
from agents.shared.core.logging_config import get_logger


logger = get_logger(__name__)


def build_aws_query(payload: dict[str, Any], fallback_text: str) -> str:
    if payload.get("search_query"):
        return str(payload["search_query"])

    dispatcher = payload.get("dispatcher_context", {}) if isinstance(payload, dict) else {}
    company = dispatcher.get("company") or dispatcher.get("official_name")
    domain = dispatcher.get("domain")
    base_prompt = payload.get("prompt") or payload.get("user_input") or fallback_text

    query_parts = [
        "AWS opportunities",
        "case studies",
        "cloud migration",
    ]
    if company:
        query_parts.append(str(company))
    if domain:
        query_parts.append(str(domain))
    if base_prompt:
        query_parts.append(str(base_prompt))

    return " ".join(query_parts).strip()


class AwsResearchExecutor(BaseExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or "unknown"
        context_id = context.context_id or "unknown"
        updater = TaskUpdater(event_queue, task_id=task_id, context_id=context_id)

        await updater.submit()
        await updater.start_work(build_status_message("Starting AWS research", task_id, context_id))

        try:
            raw_input = context.get_user_input()
            payload = parse_request_payload(context)
            query = build_aws_query(payload, raw_input)
            agent = TavilyAgent()
            aws_research = agent.search({"search_query": query})
            response_payload = {
                "agent": "aws_research",
                "query": query,
                "dispatcher_context": payload.get("dispatcher_context"),
                "aws_research": aws_research,
            }
            await publish_json_artifact(updater, response_payload, "aws_research.json")
            await updater.complete(build_status_message("AWS research complete", task_id, context_id))
        except Exception as exc:
            logger.error("AWS research failed: %s", exc, exc_info=True)
            await updater.failed(build_status_message(f"AWS research failed: {exc}", task_id, context_id))
