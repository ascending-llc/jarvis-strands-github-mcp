"""CLI entry for running the Strands research graph."""

import json
import sys

from orchestrator.core.exceptions import OrchestratorException
from orchestrator.core.logging_config import get_logger, setup_logging
from orchestrator.graph import run_research_graph

logger = get_logger(__name__)


def main() -> None:
    """
    Main CLI entry point for executing the research graph.

    Accepts natural language input as arguments.
    Example: python -m orchestrator.run "analyze example.com" "focus on security"

    Exit codes:
        0: Success
        1: Configuration error
        2: Input validation error
        3: Graph execution error
        4: Unexpected error
    """
    # Set up logging before processing
    setup_logging()

    if len(sys.argv) < 2:
        logger.error("Usage error: No input provided")
        print("Usage: python -m orchestrator.run <natural_language_input> [additional_context...]", file=sys.stderr)
        sys.exit(2)

    # Combine all arguments as natural language input
    user_input = " ".join(sys.argv[1:])
    logger.info(f"Received input: {user_input}")

    # Create payload with user input - dispatcher agent will parse it
    payload = {
        "user_input": user_input,
    }

    # Run research graph
    try:
        logger.info("Executing research graph")
        result = run_research_graph(payload)
        logger.info("Research graph execution completed successfully")

        # Output results
        print(json.dumps(result, indent=2))
        sys.exit(0)

    except OrchestratorException as e:
        error_msg = f"Orchestrator error: {e}"
        logger.error(error_msg, exc_info=True)
        print(json.dumps({"status": "error", "error": str(e), "error_type": type(e).__name__}, indent=2), file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        error_msg = f"Unexpected error during graph execution: {e}"
        logger.error(error_msg, exc_info=True)
        print(json.dumps({"status": "error", "error": str(e), "error_type": type(e).__name__}, indent=2), file=sys.stderr)
        sys.exit(4)


if __name__ == "__main__":
    main()
