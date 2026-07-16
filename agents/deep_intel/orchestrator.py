"""Deep Intel orchestrator agent.

Served via A2AServer like the workers. To guarantee the two specialists run in
parallel (rather than depending on the model emitting concurrent tool calls), the
fan-out lives inside a single `gather_research` tool that uses asyncio.gather. The
agent then streams the HTML report to the caller.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from strands import Agent, tool

from agents.a2a_client import call_agent_text
from agents.deep_intel.reporting import render_report, store_html_report
from agents.shared.bedrock import build_bedrock_model
from agents.shared.core.config import AppConfig, load_config
from agents.shared.core.logging_config import get_logger
from agents.shared.schemas import AwsFindings, CompanyProfile, ReportContent

logger = get_logger(__name__)


def _coerce(text: str, model):
    """Validate worker JSON text into its schema, tolerating stray fences."""
    cleaned = text.replace("```json", "").replace("```", "").strip()
    try:
        return model.model_validate_json(cleaned)
    except Exception as exc:  # noqa: BLE001 - tolerate malformed worker output
        logger.warning("Could not validate %s output: %s", model.__name__, exc)
        return model()


async def _gather_research(user_input: str) -> dict[str, Any]:
    """Call both specialist workers in parallel over A2A and validate their output."""
    aws_text, biz_text = await asyncio.gather(
        call_agent_text("aws_research", user_input),
        call_agent_text("business_intel", user_input),
    )
    aws = _coerce(aws_text, AwsFindings)
    biz = _coerce(biz_text, CompanyProfile)
    return {
        "aws_findings": aws.model_dump(),
        "company_profile": biz.model_dump(),
        "company_name": biz.identity.official_name or user_input,
    }


@tool(
    name="gather_research",
    description="Run AWS opportunity research and company intelligence in parallel for the "
    "user's request. Returns both findings as JSON. Call this first.",
)
async def gather_research(user_input: str) -> dict[str, Any]:
    return await _gather_research(user_input)


@tool(
    name="save_report",
    description="Render and persist the final report (HTML via template, saved to disk and S3 "
    "if configured). Pass the complete report content. Call this exactly once, after your "
    "analysis is done.",
)
def save_report(report: ReportContent) -> dict[str, Any]:
    # Strands builds the tool schema from the annotation but passes the raw input dict —
    # validate explicitly so we get a typed model (and the LLM gets a precise validation
    # error to self-correct against, instead of an AttributeError).
    content = ReportContent.model_validate(report)
    html_document = render_report(content)
    _, path, url = store_html_report(html_document, content.company_name)
    return {"saved_path": path, "report_url": url}


SYSTEM_PROMPT = (
    "You are the master orchestrator for AWS customer intelligence. Your job is to produce "
    "one complete customer-intelligence report for the user's target company.\n\n"
    "Workflow:\n"
    "1. Call `gather_research` with the user's request to get AWS findings and the company "
    "profile (the two specialists run in parallel).\n"
    "2. Cross-check the two sources for company identity and resolve obvious conflicts.\n"
    "3. Compose the report content: an executive summary, a company snapshot table, AWS "
    "opportunities mapped to business challenges (with named case studies only when "
    "verified), and strategic recommendations. Mark confidence honestly; write 'Unknown' "
    "rather than inventing facts. If research data is thin, say so in data_notice.\n"
    "4. Call `save_report` with the full report content — the HTML is rendered from a "
    "template, so provide content only, no markup.\n"
    "5. Your final answer: a brief summary of key findings plus the saved report path and "
    "URL returned by save_report. Do NOT output HTML."
)


def build_orchestrator_agent(config: AppConfig | None = None, extra_tools: list = ()) -> Agent:
    config = config or load_config()
    return Agent(
        name="deep_intel",
        description="Orchestrates AWS research and business intelligence into a full report.",
        model=build_bedrock_model(config),
        system_prompt=SYSTEM_PROMPT,
        tools=[gather_research, save_report, *extra_tools],
    )


async def run_report(user_input: str) -> dict[str, Any]:
    """Non-streaming convenience entrypoint (CLI/tests): gather, synthesize, persist."""
    config = load_config()
    research = await _gather_research(user_input)
    agent = build_orchestrator_agent(config)
    prompt = (
        f"User input:\n{user_input}\n\n"
        f"Research findings (JSON):\n{json.dumps(research, indent=2)}\n\n"
        "Compose the report content and save it with save_report now."
    )
    result = await agent.invoke_async(prompt)
    return {"result": str(result), "company_name": research["company_name"]}
