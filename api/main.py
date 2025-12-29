"""FastAPI app and CLI entry for running the research graph."""

import json
import sys
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from orchestrator.core.exceptions import AgentError, OrchestratorException
from orchestrator.core.logging_config import get_logger, setup_logging
from orchestrator.graph import run_research_graph

app = FastAPI(title="AWS Customer Intelligence API", version="0.1.0")
logger = get_logger(__name__)


class ResearchRequest(BaseModel):
    prompt: str


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/research")
def research(request: ResearchRequest) -> Dict[str, Any]:
    try:
        return run_research_graph({"user_input": request.prompt})
    except AgentError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def main() -> None:
    """
    Main CLI entry point for executing the research graph.

    Accepts natural language input as arguments.
    Example: python -m api.main "analyze example.com" "focus on security"

    Exit codes:
        0: Success
        1: Configuration error
        2: Input validation error
        3: Graph execution error
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
        logger.info("Executing research graph")
        result = run_research_graph(payload)
        logger.info("Research graph execution completed successfully")
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
        error_msg = f"Unexpected error during graph execution: {e}"
        logger.error(error_msg, exc_info=True)
        print(json.dumps({"status": "error", "error": str(e), "error_type": type(e).__name__}, indent=2), file=sys.stderr)
        sys.exit(4)


def run_server() -> None:
    """Run the FastAPI server."""
    setup_logging()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
