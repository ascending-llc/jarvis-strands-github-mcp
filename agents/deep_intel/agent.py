"""Deep intel agent orchestration and synthesis."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from botocore.config import Config as BotocoreConfig
from strands import Agent
from strands.models.bedrock import BedrockModel

from agents.aws_research.executor import build_aws_query
from agents.business_intel.executor import build_business_query
from agents.clients import send_agent_request
from agents.deep_intel.reporting import store_html_report
from agents.shared.core.config import load_config
from agents.shared.core.logging_config import get_logger
from agents.shared.tools.strands_tools import tavily_extract_tool
from agents.shared.utils import load_prompt


logger = get_logger(__name__)


class DeepIntelAgent:
    """Orchestrates sub-agents and synthesizes the final deep intel report."""

    def __init__(self) -> None:
        config = load_config()
        system_prompt = load_prompt("deep_intel_agent.md")
        boto_config = BotocoreConfig(
            read_timeout=config.bedrock_read_timeout,
            connect_timeout=config.bedrock_connect_timeout,
            retries={"max_attempts": config.bedrock_max_attempts},
        )
        model = BedrockModel(
            model_id=config.model,
            max_tokens=config.max_tokens,
            boto_client_config=boto_config,
        )
        self.agent = Agent(
            name="deep_intel",
            system_prompt=system_prompt,
            model=model,
            tools=[tavily_extract_tool],
        )

    @staticmethod
    def _extract_text(result: Any) -> str:
        if not result or not hasattr(result, "message"):
            raise ValueError("Agent returned invalid response")
        message = result.message
        content = message["content"]
        first = content[0]
        return str(first["text"])

    async def run(self, user_input: str) -> dict[str, Any]:
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

        logger.debug(
            "Agent results received. aws_result_type=%s business_result_type=%s",
            type(aws_result).__name__,
            type(business_result).__name__,
        )
        aws_research = aws_result.get("aws_research") if isinstance(aws_result, dict) else aws_result
        business_intel = (
            business_result.get("business_intel") if isinstance(business_result, dict) else business_result
        )

        user_prompt = (
            "User input:\n"
            f"{user_input}\n\n"
            "AWS Research (JSON):\n"
            f"{json.dumps(aws_research or {}, indent=2)}\n\n"
            "Business Intelligence (JSON):\n"
            f"{json.dumps(business_intel or {}, indent=2)}\n\n"
            "Return ONLY a complete HTML document."
        )

        logger.debug("Invoking deep intel synthesis agent")
        result = self.agent(user_prompt)
        try:
            message = result.message
            logger.debug("Deep intel message type=%s", type(message).__name__)
            response_text = self._extract_text(result)
        except (TypeError, KeyError, IndexError, AttributeError, ValueError) as exc:
            logger.error("Deep intel message format invalid: %s", exc, exc_info=True)
            return {
                "status": "failed",
                "error": "Deep intel agent returned unexpected message format",
                "aws_research": aws_research,
                "business_intel": business_intel,
            }
        response_text = response_text.replace("```html", "").replace("```", "").strip()
        logger.debug("Deep intel response length=%d chars", len(response_text))

        html_report = ""
        html_path = None
        report_url = None
        render_error = None
        try:
            html_report = response_text
            company_name = None
            if isinstance(business_intel, dict):
                company_name = (
                    business_intel.get("company_identity", {}).get("official_name")
                    or business_intel.get("company_overview", {}).get("official_name")
                )
            if not company_name and isinstance(aws_research, dict):
                company_name = aws_research.get("company_overview", {}).get("official_name")
            if not company_name:
                company_name = user_input
            html_report, html_path, report_url = store_html_report(html_report, company_name)
        except Exception as exc:
            render_error = f"HTML report generation failed: {exc}"
            logger.error("HTML report generation failed: %s", exc, exc_info=True)

        return {
            "status": "completed" if render_error is None else "partial",
            "aws_research": aws_research,
            "business_intel": business_intel,
            "html_report": html_report,
            "html_report_path": html_path,
            "report_url": report_url,
            "error": render_error,
        }
