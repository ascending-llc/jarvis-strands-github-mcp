"""A2A executor for business intelligence research."""

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
from agents.business_intel.research_agent import PerplexityAgent
from agents.shared.core.logging_config import get_logger


logger = get_logger(__name__)


def build_business_query(payload: dict[str, Any], fallback_text: str) -> str:
    if payload.get("research_query"):
        return str(payload["research_query"])

    dispatcher = payload.get("dispatcher_context", {}) if isinstance(payload, dict) else {}
    company = dispatcher.get("company") or dispatcher.get("official_name")
    domain = dispatcher.get("domain")
    base_prompt = payload.get("prompt") or payload.get("user_input") or fallback_text

    query_parts = [
        "company profile",
        "market position",
        "competitive landscape",
    ]
    if company:
        query_parts.append(str(company))
    if domain:
        query_parts.append(str(domain))
    if base_prompt:
        query_parts.append(str(base_prompt))

    return " ".join(query_parts).strip()


class BusinessIntelExecutor(BaseExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or "unknown"
        context_id = context.context_id or "unknown"
        updater = TaskUpdater(event_queue, task_id=task_id, context_id=context_id)

        await updater.submit()
        await updater.start_work(build_status_message("Starting business intelligence research", task_id, context_id))

        try:
            raw_input = context.get_user_input()
            payload = parse_request_payload(context)
            query = build_business_query(payload, raw_input)
            agent = PerplexityAgent()
            business_intel = agent.research({"research_query": query})
            response_payload = {
                "agent": "business_intel",
                "query": query,
                "dispatcher_context": payload.get("dispatcher_context"),
                "business_intel": business_intel,
            }
            await publish_json_artifact(updater, response_payload, "business_intel.json")
            await updater.complete(build_status_message("Business intelligence complete", task_id, context_id))
        except Exception as exc:
            logger.error("Business intelligence failed: %s", exc, exc_info=True)
            await updater.failed(build_status_message(f"Business intelligence failed: {exc}", task_id, context_id))
