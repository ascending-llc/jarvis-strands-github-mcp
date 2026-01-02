"""A2A executor that orchestrates the full deep intel workflow."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from botocore.config import Config as BotocoreConfig
from strands import Agent
from strands.models.bedrock import BedrockModel
from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater

from agents.shared.base_executor import (
    BaseExecutor,
    build_status_message,
    publish_json_artifact,
    publish_text_artifact,
)
from agents.aws_research.executor import build_aws_query
from agents.business_intel.executor import build_business_query
from agents.clients import send_agent_request
from agents.reporting import render_and_store_report
from agents.shared.core.config import load_config
from agents.shared.core.logging_config import get_logger
from agents.shared.tools.strands_tools import tavily_extract_tool
from agents.shared.utils import extract_json_from_text, load_prompt


logger = get_logger(__name__)


def _build_deep_intel_agent() -> Agent:
    config = load_config()
    system_prompt = load_prompt("deep_intel_agent.md")
    boto_config = BotocoreConfig(
        read_timeout=config.bedrock_read_timeout,
        connect_timeout=config.bedrock_connect_timeout,
        retries={"max_attempts": config.bedrock_max_attempts},
    )
    return Agent(
        name="deep_intel",
        system_prompt=system_prompt,
        model=BedrockModel(
            model_id=config.model,
            max_tokens=config.max_tokens,
            boto_client_config=boto_config,
        ),
        tools=[tavily_extract_tool],
    )


async def run_deep_intel(user_input: str) -> dict[str, Any]:
    aws_payload = {
        "user_input": user_input,
        "search_query": build_aws_query({"user_input": user_input}, user_input),
    }
    business_payload = {
        "user_input": user_input,
        "research_query": build_business_query({"user_input": user_input}, user_input),
    }

    aws_result, business_result = await asyncio.gather(
        send_agent_request("aws_research", aws_payload),
        send_agent_request("business_intel", business_payload),
    )

    aws_research = aws_result.get("aws_research") if isinstance(aws_result, dict) else aws_result
    business_intel = (
        business_result.get("business_intel") if isinstance(business_result, dict) else business_result
    )

    agent = _build_deep_intel_agent()
    user_prompt = (
        "User input:\n"
        f"{user_input}\n\n"
        "AWS Research (JSON):\n"
        f"{json.dumps(aws_research or {}, indent=2)}\n\n"
        "Business Intelligence (JSON):\n"
        f"{json.dumps(business_intel or {}, indent=2)}\n\n"
        "Return ONLY a single JSON object with the required fields."
    )

    result = agent(user_prompt)
    if not result or not hasattr(result, "message"):
        raise ValueError("Deep intel agent returned invalid response")

    final_synthesis = extract_json_from_text(str(result.message))

    html_report = ""
    html_path = None
    report_url = None
    try:
        html_report, html_path, report_url = render_and_store_report(final_synthesis)
    except Exception as exc:
        logger.error("HTML report generation failed: %s", exc, exc_info=True)

    return {
        "status": "completed",
        "aws_research": aws_research,
        "business_intel": business_intel,
        "final_synthesis": final_synthesis,
        "html_report": html_report,
        "html_report_path": html_path,
        "report_url": report_url,
    }


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
            await publish_json_artifact(updater, result, "deep_intel.json")

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
