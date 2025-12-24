"""4-node parallel research graph using Strands GraphBuilder pattern.

Topology:
    Dispatcher → Tavily Agent (parallel)
              → Perplexity Agent (parallel)
              → Aggregator

Each node is a real Strands Agent. The graph only handles orchestration.
"""

import os
from typing import Any, Dict

from strands.multiagent import GraphBuilder
from strands.multiagent.base import Status
from strands.multiagent.graph import GraphState

from orchestrator.core.config import load_config
from orchestrator.core.exceptions import AgentError
from orchestrator.core.logging_config import get_logger
from orchestrator.utils import ensure_dir, extract_json_from_text, utc_timestamp, render_report
from orchestrator.agents.dispatcher_agent import create_dispatcher_agent
from orchestrator.agents.tavily_agent import create_tavily_agent
from orchestrator.agents.perplexity_agent import create_perplexity_agent
from orchestrator.agents.aggregator_agent import create_aggregator_agent

logger = get_logger(__name__)


def all_workers_complete(required_nodes: list[str]):
    """Return a condition that waits for all required nodes to complete."""

    def check_all_complete(state: GraphState) -> bool:
        return all(
            node_id in state.results and state.results[node_id].status == Status.COMPLETED
            for node_id in required_nodes
        )

    return check_all_complete


def build_research_graph() -> Any:
    """Build and compile the research graph."""
    logger.info("Building research graph")

    builder = GraphBuilder()
    builder.add_node(create_dispatcher_agent(), "dispatcher")
    builder.add_node(create_tavily_agent(), "tavily")
    builder.add_node(create_perplexity_agent(), "perplexity")
    builder.add_node(create_aggregator_agent(), "aggregator")

    builder.add_edge("dispatcher", "tavily")
    builder.add_edge("dispatcher", "perplexity")

    condition = all_workers_complete(["tavily", "perplexity"])
    builder.add_edge("tavily", "aggregator", condition=condition)
    builder.add_edge("perplexity", "aggregator", condition=condition)

    builder.set_entry_point("dispatcher")
    return builder.build()


def _extract_node_json(graph_result: Any, node_id: str) -> Dict[str, Any]:
    """Extract JSON from a node's result in the graph.

    Handles Strands agent response format where content is in:
    {'role': 'assistant', 'content': [{'text': '...'}]}
    """
    node_result = graph_result.results.get(node_id) if graph_result and graph_result.results else None
    if not node_result:
        return {}

    agent_result = getattr(node_result, "result", None)
    message = getattr(agent_result, "message", None)
    text = str(message) if message is not None else str(agent_result)

    # Try to extract content from Strands agent response format
    # Format: {'role': 'assistant', 'content': [{'text': 'actual content'}]}
    try:
        # Attempt to eval the string as a Python dict
        import ast
        response_dict = ast.literal_eval(text)

        # Extract text from content array
        if isinstance(response_dict, dict) and 'content' in response_dict:
            content = response_dict['content']
            if isinstance(content, list) and len(content) > 0:
                if isinstance(content[0], dict) and 'text' in content[0]:
                    text = content[0]['text']
    except (ValueError, SyntaxError, KeyError, IndexError):
        # If parsing fails, use the original text
        pass

    parsed = extract_json_from_text(text)
    return parsed or {}


def _format_task(task: Dict[str, Any]) -> str:
    if task.get("user_input"):
        return task["user_input"]
    lines = []
    for key, value in task.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _render_html_report(aggregator_result: Dict[str, Any]) -> str:
    """Render HTML report from aggregator JSON data using Jinja2 template.

    Args:
        aggregator_result: JSON data from aggregator agent

    Returns:
        Rendered HTML string, or empty string if rendering fails
    """
    try:
        if not aggregator_result:
            logger.warning("Aggregator result is empty, cannot render HTML")
            return ""

        # Render HTML using Jinja2 template
        html = render_report(aggregator_result)
        logger.info("HTML report rendered successfully (%d chars)", len(html))
        return html

    except ValueError as e:
        logger.error("HTML rendering failed due to missing data: %s", e)
        return ""
    except Exception as e:
        logger.error("HTML rendering failed: %s", e, exc_info=True)
        return ""


def run_research_graph(task: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the research graph on a given task."""
    logger.info("Starting research graph execution")

    try:
        if os.getenv("AGGREGATOR_ONLY", "").lower() in {"1", "true", "yes"}:
            logger.info("AGGREGATOR_ONLY enabled; running aggregator only")
            agent = create_aggregator_agent()
            test_prompt = (
                "TEST MODE: Generate the HTML report using the required template.\n\n"
                "Use the following minimal context for placeholders:\n"
                "- Company: AtScale, Inc.\n"
                "- Domain: atscale.com\n"
                "- Confidence: HIGH\n"
                "- Data completeness: PARTIAL\n\n"
                "Return ONLY valid JSON with html_report populated."
            )
            result = agent(test_prompt)
            dispatcher_result = {}
            tavily_result = {}
            perplexity_result = {}
            aggregator_result = extract_json_from_text(str(result.message))
            status_str = "Status.COMPLETED"
            execution_order = ["aggregator"]
        else:
            graph = build_research_graph()
            task_text = _format_task(task)

            logger.info("Executing compiled research graph")
            result = graph(task_text)

            dispatcher_result = _extract_node_json(result, "dispatcher")
            tavily_result = _extract_node_json(result, "tavily")
            perplexity_result = _extract_node_json(result, "perplexity")
            aggregator_result = _extract_node_json(result, "aggregator")
            logger.info(
                "Aggregator keys: %s",
                sorted(aggregator_result.keys()) if isinstance(aggregator_result, dict) else type(aggregator_result),
            )
            status_str = str(result.status)
            execution_order = [node.node_id for node in result.execution_order]

        html_path = None
        html_report = _render_html_report(aggregator_result)
        if html_report:
            config = load_config()
            ensure_dir(config.report_output_dir)
            company = aggregator_result.get("company_overview", {}).get("official_name", "report")
            safe_company = str(company).replace(" ", "_").replace("/", "_")
            timestamp = utc_timestamp().replace(" ", "_").replace(":", "-")
            html_path = f"{config.report_output_dir}/{safe_company}_{timestamp}.html"
            with open(html_path, "w", encoding="utf-8") as handle:
                handle.write(html_report)
            logger.info("HTML report written to %s", html_path)

        logger.info("Research graph execution completed successfully")
        return {
            "status": status_str,
            "execution_order": execution_order,
            "dispatcher_verification": dispatcher_result,
            "tavily_research": tavily_result,
            "perplexity_research": perplexity_result,
            "final_synthesis": aggregator_result,
            "html_report_path": html_path,
        }

    except AgentError:
        raise
    except Exception as e:
        error_msg = f"Research graph execution failed: {e}"
        logger.error(error_msg, exc_info=True)
        raise AgentError(error_msg) from e
