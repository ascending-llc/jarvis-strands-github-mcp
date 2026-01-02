"""Tavily AWS Research Agent - Structured research protocol.

This agent discovers AWS opportunities, relevant case studies, and technical
intelligence. Uses Strands tools for web search and domain extraction.
"""

from typing import Any, Dict

from strands import Agent
from strands.models.bedrock import BedrockModel
from botocore.config import Config as BotocoreConfig

from agents.shared.core.config import load_config
from agents.shared.core.exceptions import AgentError
from agents.shared.core.logging_config import get_logger
from agents.shared.tools.strands_tools import tavily_extract_tool, tavily_search_tool
from agents.shared.utils import extract_json_from_text, load_prompt

logger = get_logger(__name__)

# ============================================================================
# TAVILY AGENT CLASS
# ============================================================================
class TavilyAgent:
    def __init__(self):
        try:
            self.config = load_config()
            self.system_prompt = load_prompt("tavily_agent.md")
            self.boto_config = BotocoreConfig(
                read_timeout=self.config.bedrock_read_timeout,
                connect_timeout=self.config.bedrock_connect_timeout,
                retries={"max_attempts": self.config.bedrock_max_attempts},
            )
            self.agent = Agent(
                name="tavily_agent",
                system_prompt=self.system_prompt,
                model=BedrockModel(
                    model_id=self.config.model,
                    max_tokens=self.config.max_tokens,
                    boto_client_config=self.boto_config,
                ),
                tools=[tavily_search_tool, tavily_extract_tool],
            )
            logger.debug(f"Tavily agent created with model: {self.config.model}, max_tokens: {self.config.max_tokens}")
        except Exception as e:
            error_msg = f"Failed to initialize TavilyAgent: {e}"
            logger.error(error_msg, exc_info=True)
            raise AgentError(error_msg) from e

    def search(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the Tavily agent for web search and extraction.
        Args:
            task: Task definition with search_query
        Returns:
            Dictionary with search results
        Raises:
            AgentError: If search fails
        """
        logger.info(f"Starting Tavily agent for query: {task.get('search_query')}")

        user_prompt = (
            "Search the web for the following query and extract relevant information.\n\n"
            f"Search query: {task.get('search_query')}\n"
            "\nReturn ONLY valid JSON per the specified schema."
        )

        try:
            logger.info("Calling Tavily agent")
            result = self.agent(user_prompt)
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
