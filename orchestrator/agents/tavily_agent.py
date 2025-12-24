"""Tavily AWS Research Agent - Structured research protocol.

This agent discovers AWS opportunities, relevant case studies, and technical
intelligence. Uses Strands tools for web search and domain extraction.
"""

from typing import Any, Dict

from strands import Agent
from strands.models.bedrock import BedrockModel
from botocore.config import Config as BotocoreConfig

from orchestrator.core.config import load_config
from orchestrator.core.exceptions import AgentError
from orchestrator.core.logging_config import get_logger
from orchestrator.tools.strands_tools import tavily_extract_tool, tavily_search_tool
from orchestrator.utils import extract_json_from_text, load_prompt

logger = get_logger(__name__)


# ============================================================================
# AGENT CREATION
# ============================================================================
def create_tavily_agent() -> Agent:
    """Create Tavily AWS research agent with tools.
    
    Returns:
        Agent: Configured Strands Agent with system prompt and Tavily tools
    """
    config = load_config()
    system_prompt = load_prompt("prompts/tavily_agent.md")
    
    boto_config = BotocoreConfig(
        read_timeout=config.bedrock_read_timeout,
        connect_timeout=config.bedrock_connect_timeout,
        retries={"max_attempts": config.bedrock_max_attempts},
    )

    return Agent(
        name="tavily_agent",
        system_prompt=system_prompt,
        model=BedrockModel(
            model_id=config.model,
            max_tokens=config.max_tokens,
            boto_client_config=boto_config,
        ),
        tools=[tavily_search_tool, tavily_extract_tool],
    )


# ============================================================================
# EXECUTION
# ============================================================================
def run_tavily_agent(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the Tavily AWS research agent.

    Args:
        task: Task definition with:
            - target_domain: Company domain
            - validated_company_name: Company name (if verified)
            - industry: Industry classification (if known)
            - business_challenges: List of known challenges (optional)
            - research_focus: Specific areas to focus on (optional)

    Returns:
        Dictionary with structured AWS research findings

    Raises:
        AgentError: If agent execution fails or response is invalid
    """
    logger.info(f"Starting Tavily agent for domain: {task.get('target_domain')}")

    try:
        config = load_config()
        logger.debug("Configuration loaded successfully")
    except Exception as e:
        error_msg = f"Failed to load configuration for Tavily agent: {e}"
        logger.error(error_msg)
        raise AgentError(error_msg) from e

    try:
        system_prompt = load_prompt("prompts/tavily_agent.md")
        logger.debug("Tavily system prompt loaded")
    except FileNotFoundError as e:
        error_msg = f"Tavily agent prompt file not found: {e}"
        logger.error(error_msg)
        raise AgentError(error_msg) from e
    except Exception as e:
        error_msg = f"Failed to load Tavily agent prompt: {e}"
        logger.error(error_msg, exc_info=True)
        raise AgentError(error_msg) from e

    try:
        boto_config = BotocoreConfig(
            read_timeout=config.bedrock_read_timeout,
            connect_timeout=config.bedrock_connect_timeout,
            retries={"max_attempts": config.bedrock_max_attempts},
        )

        agent = Agent(
            name="tavily_agent",
            system_prompt=system_prompt,
            model=BedrockModel(
                model_id=config.model,
                max_tokens=config.max_tokens,
                boto_client_config=boto_config,
            ),
            tools=[tavily_search_tool, tavily_extract_tool],
        )
        logger.debug(f"Tavily agent created with model: {config.model}, max_tokens: {config.max_tokens}")
    except Exception as e:
        error_msg = f"Failed to initialize Tavily agent: {e}"
        logger.error(error_msg, exc_info=True)
        raise AgentError(error_msg) from e

    user_prompt = (
        "Conduct comprehensive AWS research on target company.\n\n"
        f"Target domain: {task.get('target_domain')}\n"
        f"Validated company name: {task.get('validated_company_name', 'Unknown')}\n"
    )
    
    if task.get('industry'):
        user_prompt += f"Industry: {task.get('industry')}\n"
    
    if task.get('business_challenges'):
        user_prompt += f"Known challenges: {', '.join(task.get('business_challenges', []))}\n"
    
    if task.get('research_focus'):
        user_prompt += f"Research focus: {', '.join(task.get('research_focus', []))}\n"
    
    user_prompt += "\nReturn ONLY valid JSON per the specified schema."

    try:
        logger.info("Calling Tavily agent")
        result = agent(user_prompt)
        logger.debug("Tavily agent response received")

        if not result or not hasattr(result, "message"):
            error_msg = "Tavily agent returned invalid response: missing message attribute"
            logger.error(error_msg)
            raise AgentError(error_msg)

        response_text = str(result.message)
        logger.debug(f"Tavily response length: {len(response_text)} characters")

        parsed_response = extract_json_from_text(response_text)
        logger.info("Tavily agent completed successfully")
        return parsed_response

    except AgentError:
        raise
    except Exception as e:
        error_msg = f"Tavily agent execution failed: {e}"
        logger.error(error_msg, exc_info=True)
        raise AgentError(error_msg) from e
