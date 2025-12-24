"""Dispatcher Agent - Initial domain verification and context preparation.

Runs first in the research graph to validate domain, extract company info,
and prepare context for parallel research agents.
"""

from typing import Any, Dict

from strands import Agent
from strands.models.bedrock import BedrockModel
from botocore.config import Config as BotocoreConfig

from orchestrator.core.config import load_config
from orchestrator.core.exceptions import AgentError
from orchestrator.core.logging_config import get_logger
from orchestrator.tools.strands_tools import tavily_extract_tool
from orchestrator.utils import extract_json_from_text, load_prompt

logger = get_logger(__name__)


# ============================================================================
# AGENT CREATION
# ============================================================================
def create_dispatcher_agent() -> Agent:
    """Create dispatcher agent for domain verification and context prep.
    
    Returns:
        Agent: Configured Strands Agent with system prompt from prompts/
    """
    config = load_config()
    system_prompt = load_prompt("prompts/dispatcher_agent.md")
    
    boto_config = BotocoreConfig(
        read_timeout=config.bedrock_read_timeout,
        connect_timeout=config.bedrock_connect_timeout,
        retries={"max_attempts": config.bedrock_max_attempts},
    )

    return Agent(
        name="dispatcher",
        system_prompt=system_prompt,
        model=BedrockModel(
            model_id=config.model,
            max_tokens=config.max_tokens,
            boto_client_config=boto_config,
        ),
        tools=[tavily_extract_tool],
    )


# ============================================================================
# EXECUTION
# ============================================================================
def run_dispatcher_agent(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the dispatcher agent for domain verification.

    Args:
        task: Task definition with:
            - target_domain: Company domain to verify
            - company_name_hint: Optional hint for company name

    Returns:
        Dictionary with domain verification and context for next agents

    Raises:
        AgentError: If domain verification fails
    """
    logger.info(f"Starting dispatcher agent for domain: {task.get('target_domain')}")

    try:
        config = load_config()
        logger.debug("Configuration loaded successfully")
    except Exception as e:
        error_msg = f"Failed to load configuration for dispatcher: {e}"
        logger.error(error_msg)
        raise AgentError(error_msg) from e

    try:
        agent = create_dispatcher_agent()
        logger.debug(f"Dispatcher agent created with model: {config.model}, max_tokens: {config.max_tokens}")
    except Exception as e:
        error_msg = f"Failed to initialize dispatcher agent: {e}"
        logger.error(error_msg, exc_info=True)
        raise AgentError(error_msg) from e

    # Build user prompt from task context
    # Support both structured and natural language input
    if task.get('user_input'):
        # Natural language input - agent parses it
        user_prompt = (
            "Analyze the following user input and verify the target company domain.\n\n"
            f"User input: {task.get('user_input')}\n\n"
            "Extract the target domain and company information from this input.\n"
            "Then access the domain, extract company information, and verify it's the target company."
            "\nReturn ONLY valid JSON per the specified schema."
        )
    else:
        # Structured input - traditional format
        user_prompt = (
            "Verify and analyze the target company domain.\n\n"
            f"Target domain: {task.get('target_domain')}\n"
            f"Company name hint (if any): {task.get('company_name_hint', 'None')}\n"
            "\nAccess the domain, extract company information, and verify it's the target company."
            "\nReturn ONLY valid JSON per the specified schema."
        )

    try:
        logger.info("Calling dispatcher agent")
        result = agent(user_prompt)
        logger.debug("Dispatcher agent response received")

        if not result or not hasattr(result, "message"):
            error_msg = "Dispatcher agent returned invalid response: missing message attribute"
            logger.error(error_msg)
            raise AgentError(error_msg)

        response_text = str(result.message)
        logger.debug(f"Dispatcher response length: {len(response_text)} characters")

        parsed_response = extract_json_from_text(response_text)
        logger.info("Dispatcher agent completed successfully")
        return parsed_response

    except AgentError:
        raise
    except Exception as e:
        error_msg = f"Dispatcher agent execution failed: {e}"
        logger.error(error_msg, exc_info=True)
        raise AgentError(error_msg) from e
