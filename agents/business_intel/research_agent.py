"""Perplexity Sonar Agent - Business Intelligence Research.

Discovers company fundamentals, market position, competitive landscape,
technology stack, leadership, and growth indicators.
"""

from typing import Any, Dict

from strands import Agent
from strands.models.bedrock import BedrockModel
from botocore.config import Config as BotocoreConfig

from agents.shared.core.config import load_config
from agents.shared.core.exceptions import AgentError
from agents.shared.core.logging_config import get_logger
from agents.shared.utils import extract_json_from_text, load_prompt

logger = get_logger(__name__)


# ============================================================================
# PERPLEXITY AGENT CLASS
# ============================================================================
class PerplexityAgent:
    def __init__(self):
        try:
            self.config = load_config()
            self.system_prompt = load_prompt("perplexity_agent.md")
            self.boto_config = BotocoreConfig(
                read_timeout=self.config.bedrock_read_timeout,
                connect_timeout=self.config.bedrock_connect_timeout,
                retries={"max_attempts": self.config.bedrock_max_attempts},
            )
            self.agent = Agent(
                name="perplexity",
                system_prompt=self.system_prompt,
                model=BedrockModel(
                    model_id=self.config.model,
                    max_tokens=self.config.max_tokens,
                    boto_client_config=self.boto_config,
                ),
                tools=[],
            )
            logger.debug(f"Perplexity agent created with model: {self.config.model}, max_tokens: {self.config.max_tokens}")
        except Exception as e:
            error_msg = f"Failed to initialize PerplexityAgent: {e}"
            logger.error(error_msg, exc_info=True)
            raise AgentError(error_msg) from e

    def research(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the Perplexity agent for research and Q&A.
        Args:
            task: Task definition with research_query
        Returns:
            Dictionary with research results
        Raises:
            AgentError: If research fails
        """
        logger.info(f"Starting Perplexity agent for query: {task.get('research_query')}")

        user_prompt = (
            "Research the following question or topic and provide a concise, factual answer.\n\n"
            f"Research query: {task.get('research_query')}\n"
            "\nReturn ONLY valid JSON per the specified schema."
        )

        try:
            logger.info("Calling Perplexity agent")
            result = self.agent(user_prompt)
            logger.debug("Perplexity agent response received")

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
