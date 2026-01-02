"""FastAPI app and CLI entry for running the deep intel workflow."""

import asyncio
import json
import sys

import uvicorn

from api.app import create_app
from agents.shared.core.exceptions import OrchestratorException
from agents.shared.core.logging_config import get_logger, setup_logging
from agents.deep_intel.executor import run_deep_intel

app = create_app()
logger = get_logger(__name__)


def main() -> None:
    """
    Main CLI entry point for executing the deep intel workflow.

    Accepts natural language input as arguments.
    Example: python -m api.main "analyze example.com" "focus on security"

    Exit codes:
        0: Success
        1: Configuration error
        2: Input validation error
        3: Workflow execution error
        4: Unexpected error
    """
    setup_logging()

    if len(sys.argv) < 2:
        logger.error("Usage error: No input provided")
        print("Usage: python -m api.main <natural_language_input> [additional_context...]", file=sys.stderr)
        sys.exit(2)

    user_input = " ".join(sys.argv[1:])
    logger.info("Received input: %s", user_input)

    payload = {"user_input": user_input}

    try:
        logger.info("Executing deep intel workflow")
        result = asyncio.run(run_deep_intel(payload["user_input"]))
        logger.info("Deep intel workflow completed successfully")
        print(json.dumps(result, indent=2))
        sys.exit(0)
    except OrchestratorException as e:
        error_msg = f"Orchestrator error: {e}"
        logger.error(error_msg, exc_info=True)
        print(
            json.dumps({"status": "error", "error": str(e), "error_type": type(e).__name__}, indent=2),
            file=sys.stderr,
        )
        sys.exit(3)
    except Exception as e:
        error_msg = f"Unexpected error during workflow execution: {e}"
        logger.error(error_msg, exc_info=True)
        print(json.dumps({"status": "error", "error": str(e), "error_type": type(e).__name__}, indent=2), file=sys.stderr)
        sys.exit(4)


def run_server() -> None:
    """Run the FastAPI server."""
    setup_logging()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
