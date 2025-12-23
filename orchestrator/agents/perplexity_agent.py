"""Perplexity Sonar agent wrapper."""

from typing import Any, Dict

from strands import Agent

from orchestrator.config import load_config
from orchestrator.utils import extract_json_from_text, load_prompt


def run_perplexity_agent(task: Dict[str, Any]) -> Dict[str, Any]:
    config = load_config()
    system_prompt = load_prompt("prompts/PERPLEXITY_AGENT.md")

    agent = Agent(
        name="perplexity_agent",
        system_prompt=system_prompt,
        model=config.perplexity_model,
    )

    user_prompt = (
        "You are executing the Perplexity Sonar business intelligence research. "
        "Return ONLY valid JSON per the expected schema.\n\n"
        f"Target domain: {task.get('target_domain')}\n"
        f"Validated company name: {task.get('validated_company_name', 'Unknown')}\n"
        f"Disambiguation context: {task.get('disambiguation_context', {})}\n"
        f"Research focus: {task.get('research_focus', [])}\n"
        f"Constraints: {task.get('constraints', [])}\n"
    )

    result = agent(user_prompt)
    return extract_json_from_text(str(result.message))
