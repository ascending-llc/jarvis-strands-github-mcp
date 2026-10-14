"""Deep Intel agent: synthesizes the AWS customer-intelligence report.

Fan-out to the two specialist workers (AWS Research, Business Intel) and the join
that feeds their outputs here are owned by a Jarvis Registry workflow, not this
process — a workflow ``parallel`` node runs both workers against the trigger input,
and the following ``step`` node (this agent) declares ``referencedNodeNames`` on both,
so their JSON outputs arrive already embedded in the incoming prompt (under "Current
Step Inputs"). This agent only cross-checks, composes, and saves the report.
"""

from __future__ import annotations

from typing import Any

from strands import Agent, tool

from agents.deep_intel.reporting import render_report, store_html_report
from agents.shared.bedrock import build_bedrock_model
from agents.shared.core.config import AppConfig, load_config
from agents.shared.schemas import ReportContent


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
    "You compose the final AWS customer-intelligence report for a target company. "
    "The AWS findings and company profile JSON produced by the research specialists are "
    "provided to you in the message below (under 'Current Step Inputs' / referenced node "
    "outputs) — do not re-research or call any tool to fetch them.\n\n"
    "Your job:\n"
    "1. Cross-check the two sources for company identity and resolve obvious conflicts.\n"
    "2. Compose the report content: an executive summary, a company snapshot table, AWS "
    "opportunities mapped to business challenges (with named case studies only when "
    "verified), and strategic recommendations. Mark confidence honestly; write 'Unknown' "
    "rather than inventing facts. If research data is thin, say so in data_notice.\n"
    "3. Call `save_report` with the full report content — the HTML is rendered from a "
    "template, so provide content only, no markup.\n"
    "4. Your final answer: a brief summary of key findings plus the saved report path and "
    "URL returned by save_report. Do NOT output HTML."
)


def build_orchestrator_agent(config: AppConfig | None = None, extra_tools: list = ()) -> Agent:
    config = config or load_config()
    return Agent(
        name="deep_intel",
        description="Synthesizes AWS research and business intelligence into a full report.",
        model=build_bedrock_model(config),
        system_prompt=SYSTEM_PROMPT,
        tools=[save_report, *extra_tools],
    )
