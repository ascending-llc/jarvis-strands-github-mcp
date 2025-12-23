"""Tavily agent wrapper that uses Strands tools to gather AWS intelligence."""

from typing import Any, Dict

from strands import Agent

from orchestrator.tools.strands_tools import tavily_extract_tool, tavily_search_tool
from orchestrator.utils import extract_json_from_text, load_prompt


def run_tavily_agent(task: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = load_prompt("prompts/TAVILY_AGENT.md")

    agent = Agent(
        name="tavily_agent",
        system_prompt=system_prompt,
        tools=[tavily_search_tool, tavily_extract_tool],
    )

    user_prompt = (
        "You are executing the Tavily AWS-focused research. "
        "Return ONLY valid JSON per the expected schema.\n\n"
        f"Target domain: {task.get('target_domain')}\n"
        f"Validated company name: {task.get('validated_company_name', 'Unknown')}\n"
        f"Preliminary industry: {task.get('preliminary_industry', 'Unknown')}\n"
        f"Disambiguation context: {task.get('disambiguation_context', {})}\n"
        f"Research focus: {task.get('research_focus', [])}\n"
        f"Constraints: {task.get('constraints', [])}\n"
    )

    result = agent(user_prompt)
    return extract_json_from_text(str(result.message))
