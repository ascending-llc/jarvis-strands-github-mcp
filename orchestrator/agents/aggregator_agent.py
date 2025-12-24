"""Aggregator Agent - Synthesizes parallel research into comprehensive report.

Runs last in the research graph, after Tavily and Perplexity have completed.
Combines findings into coherent customer intelligence.
"""

from typing import Any, Dict

from strands import Agent
from strands.models.bedrock import BedrockModel
from botocore.config import Config as BotocoreConfig

from orchestrator.core.config import load_config
from orchestrator.core.exceptions import AgentError
from orchestrator.core.logging_config import get_logger
from orchestrator.utils import extract_json_from_text, load_prompt

logger = get_logger(__name__)


# ============================================================================
# ============================================================================
# AGENT CREATION
# ============================================================================
def create_aggregator_agent() -> Agent:
    """Create aggregator agent for synthesis and recommendations.
    
    Returns:
        Agent: Configured Strands Agent with system prompt from prompts/
    """
    config = load_config()
    system_prompt = load_prompt("prompts/aggregator_agent.md")
    
    boto_config = BotocoreConfig(
        read_timeout=config.bedrock_read_timeout,
        connect_timeout=config.bedrock_connect_timeout,
        retries={"max_attempts": config.bedrock_max_attempts},
    )

    return Agent(
        name="aggregator",
        system_prompt=system_prompt,
        model=BedrockModel(
            model_id=config.model,
            max_tokens=config.max_tokens,
            boto_client_config=boto_config,
        ),
    )


# ============================================================================
# EXECUTION
# ============================================================================
def run_aggregator_agent(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the aggregator agent to synthesize research findings.

    Args:
        task: Task definition with results from dispatcher, tavily, and perplexity

    Returns:
        Dictionary with synthesized customer intelligence and recommendations

    Raises:
        AgentError: If synthesis fails
    """
    logger.info("Starting aggregator agent for research synthesis")

    try:
        config = load_config()
        logger.debug("Configuration loaded successfully")
    except Exception as e:
        error_msg = f"Failed to load configuration for aggregator: {e}"
        logger.error(error_msg)
        raise AgentError(error_msg) from e

    try:
        agent = create_aggregator_agent()
        logger.debug(f"Aggregator agent created with model: {config.model}, max_tokens: {config.max_tokens}")
    except Exception as e:
        error_msg = f"Failed to initialize aggregator agent: {e}"
        logger.error(error_msg, exc_info=True)
        raise AgentError(error_msg) from e

    # Build user prompt with all research findings
    dispatcher_context = task.get("dispatcher_context", {})
    perplexity_findings = task.get("perplexity_findings", {})
    tavily_findings = task.get("tavily_findings", {})

    user_prompt = (
        "Synthesize the following research findings into comprehensive customer intelligence.\n\n"
        "=== DOMAIN VERIFICATION ===\n"
        f"{dispatcher_context}\n\n"
        "=== BUSINESS INTELLIGENCE (Perplexity) ===\n"
        f"{perplexity_findings}\n\n"
        "=== AWS RESEARCH (Tavily) ===\n"
        f"{tavily_findings}\n\n"
        "Combine these findings, eliminate redundancy, create strategic insights and recommendations."
        "\nReturn ONLY valid JSON per the specified schema."
    )

    try:
        logger.info("Calling aggregator agent")
        result = agent(user_prompt)
        logger.debug("Aggregator agent response received")

        if not result or not hasattr(result, "message"):
            error_msg = "Aggregator agent returned invalid response: missing message attribute"
            logger.error(error_msg)
            raise AgentError(error_msg)

        response_text = str(result.message)
        logger.debug(f"Aggregator response length: {len(response_text)} characters")

        parsed_response = extract_json_from_text(response_text)
        logger.info("Aggregator agent completed successfully")
        return parsed_response

    except AgentError:
        raise
    except Exception as e:
        error_msg = f"Aggregator agent execution failed: {e}"
        logger.error(error_msg, exc_info=True)
        raise AgentError(error_msg) from e
