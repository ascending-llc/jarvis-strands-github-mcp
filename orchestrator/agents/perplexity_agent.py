"""Perplexity Sonar Agent - Business Intelligence Research.

Discovers company fundamentals, market position, competitive landscape,
technology stack, leadership, and growth indicators.
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
# AGENT CREATION
# ============================================================================
def create_perplexity_agent() -> Agent:
    """Create Perplexity business intelligence agent.
    
    Returns:
        Agent: Configured Strands Agent with system prompt from prompts/
    """
    config = load_config()
    system_prompt = load_prompt("prompts/perplexity_agent.md")
    
    boto_config = BotocoreConfig(
        read_timeout=config.bedrock_read_timeout,
        connect_timeout=config.bedrock_connect_timeout,
        retries={"max_attempts": config.bedrock_max_attempts},
    )

    return Agent(
        name="perplexity_agent",
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
def run_perplexity_agent(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the Perplexity Sonar agent for business intelligence research.

    Args:
        task: Task definition with target domain, company name, research focus, etc.

    Returns:
        Dictionary with agent response (expected to contain research data)

    Raises:
        AgentError: If agent execution fails or response is invalid
    """
    logger.info(f"Starting Perplexity agent for domain: {task.get('target_domain')}")

    try:
        config = load_config()
        logger.debug("Configuration loaded successfully")
    except Exception as e:
        error_msg = f"Failed to load configuration for Perplexity agent: {e}"
        logger.error(error_msg)
        raise AgentError(error_msg) from e

    try:
        agent = create_perplexity_agent()
        logger.debug(f"Perplexity agent created with model: {config.model}, max_tokens: {config.max_tokens}")
    except Exception as e:
        error_msg = f"Failed to initialize Perplexity agent: {e}"
        logger.error(error_msg, exc_info=True)
        raise AgentError(error_msg) from e

    user_prompt = (
        "Conduct comprehensive business intelligence research on the target company.\n\n"
        f"Target domain: {task.get('target_domain')}\n"
        f"Validated company name: {task.get('validated_company_name', 'Unknown')}\n"
    )
    
    if task.get('industry'):
        user_prompt += f"Industry: {task.get('industry')}\n"
    
    if task.get('research_focus'):
        user_prompt += f"Research focus: {', '.join(task.get('research_focus', []))}\n"
    
    user_prompt += "\nReturn ONLY valid JSON per the specified schema."

    try:
        logger.info("Calling Perplexity agent")
        result = agent(user_prompt)
        logger.debug(f"Perplexity agent response received")

        if not result or not hasattr(result, "message"):
            error_msg = "Perplexity agent returned invalid response: missing message attribute"
            logger.error(error_msg)
            raise AgentError(error_msg)

        response_text = str(result.message)
        logger.debug(f"Perplexity response length: {len(response_text)} characters")

        parsed_response = extract_json_from_text(response_text)
        logger.info("Perplexity agent completed successfully")
        return parsed_response

    except AgentError:
        raise
    except Exception as e:
        error_msg = f"Perplexity agent execution failed: {e}"
        logger.error(error_msg, exc_info=True)
        raise AgentError(error_msg) from e
