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
from orchestrator.utils import (
    ensure_dir,
    extract_json_from_text,
    extract_node_json,
    format_task,
    render_report,
    save_report,
    utc_timestamp,
)
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
            task_text = format_task(task)

            logger.info("Executing compiled research graph")
            result = graph(task_text)

            dispatcher_result = extract_node_json(result, "dispatcher")
            tavily_result = extract_node_json(result, "tavily")
            perplexity_result = extract_node_json(result, "perplexity")
            aggregator_result = extract_node_json(result, "aggregator")
            logger.info(
                "Aggregator keys: %s",
                sorted(aggregator_result.keys()) if isinstance(aggregator_result, dict) else type(aggregator_result),
            )
            status_str = str(result.status)
            execution_order = [node.node_id for node in result.execution_order]

        html_path = None
        html_report = ""
        try:
            if not aggregator_result:
                logger.warning("Aggregator result is empty, cannot render HTML")
            else:
                html_report = render_report(aggregator_result)
        except ValueError as e:
            logger.error("HTML rendering failed due to missing data: %s", e)
        except Exception as e:
            logger.error("HTML rendering failed: %s", e, exc_info=True)

        if html_report:
            config = load_config()
            ensure_dir(config.report_output_dir)
            company = aggregator_result.get("company_overview", {}).get("official_name", "report")
            safe_company = str(company).replace(" ", "_").replace("/", "_")
            timestamp = utc_timestamp().replace(" ", "_").replace(":", "-")
            html_path = f"{config.report_output_dir}/{safe_company}_{timestamp}.html"
            html_path = save_report(html_report, html_path)

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
