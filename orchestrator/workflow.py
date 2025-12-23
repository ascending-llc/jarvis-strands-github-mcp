"""Strands graph orchestration for the customer intelligence workflow."""

from typing import Any, Dict, Tuple

from strands.multiagent import GraphBuilder
from strands.multiagent.base import Status
from strands.multiagent.graph import GraphState

from orchestrator.context import WorkflowContext
from orchestrator.graph_nodes import FunctionNode
from orchestrator.workflow_nodes import (
    artifact_node,
    domain_verification_node,
    final_validation_node,
    gap_fill_node,
    input_validation_node,
    integration_node,
    perplexity_handoff_node,
    synthesis_node,
    tavily_handoff_node,
)


def all_dependencies_complete(required_nodes: list[str]):
    def check_all_complete(state: GraphState) -> bool:
        return all(
            node_id in state.results and state.results[node_id].status == Status.COMPLETED
            for node_id in required_nodes
        )

    return check_all_complete


def build_workflow() -> Tuple[Any, WorkflowContext]:
    context = WorkflowContext()
    builder = GraphBuilder()

    builder.add_node(FunctionNode(input_validation_node, "input_validation", context), "input_validation")
    builder.add_node(FunctionNode(domain_verification_node, "domain_verification", context), "domain_verification")
    builder.add_node(FunctionNode(perplexity_handoff_node, "perplexity_handoff", context), "perplexity_handoff")
    builder.add_node(FunctionNode(tavily_handoff_node, "tavily_handoff", context), "tavily_handoff")
    builder.add_node(FunctionNode(integration_node, "integration", context), "integration")
    builder.add_node(FunctionNode(gap_fill_node, "gap_fill", context), "gap_fill")
    builder.add_node(FunctionNode(synthesis_node, "synthesis", context), "synthesis")
    builder.add_node(FunctionNode(final_validation_node, "final_validation", context), "final_validation")
    builder.add_node(FunctionNode(artifact_node, "artifact", context), "artifact")

    builder.add_edge("input_validation", "domain_verification")
    builder.add_edge("domain_verification", "perplexity_handoff")
    builder.add_edge("domain_verification", "tavily_handoff")

    condition = all_dependencies_complete(["perplexity_handoff", "tavily_handoff"])
    builder.add_edge("perplexity_handoff", "integration", condition=condition)
    builder.add_edge("tavily_handoff", "integration", condition=condition)

    builder.add_edge("integration", "gap_fill")
    builder.add_edge("gap_fill", "synthesis")
    builder.add_edge("synthesis", "final_validation")
    builder.add_edge("final_validation", "artifact")

    builder.set_entry_point("input_validation")
    builder.set_execution_timeout(3600)

    return builder.build(), context


def run_workflow(input_payload: Dict[str, Any]) -> Dict[str, Any]:
    graph, context = build_workflow()
    result = graph(input_payload)
    return {"status": result.status, "context": context.data}
