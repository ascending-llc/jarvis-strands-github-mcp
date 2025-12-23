"""Custom graph node adapters for deterministic workflow steps."""

import json
from typing import Any, Callable, Optional

from strands.agent.agent_result import AgentResult
from strands.multiagent.base import MultiAgentBase, MultiAgentResult, NodeResult, Status
from strands.types.content import ContentBlock, Message

from orchestrator.context import WorkflowContext


class FunctionNode(MultiAgentBase):
    """Execute deterministic Python functions as graph nodes."""

    def __init__(
        self,
        func: Callable[..., Any],
        name: Optional[str] = None,
        context: Optional[WorkflowContext] = None,
    ) -> None:
        super().__init__()
        self.func = func
        self.name = name or func.__name__
        self.context = context

    async def invoke_async(self, task, invocation_state, **kwargs):
        result = self.func(task, self.context) if self.context else self.func(task)
        payload = json.dumps(result, ensure_ascii=True)

        agent_result = AgentResult(
            stop_reason="end_turn",
            message=Message(role="assistant", content=[ContentBlock(text=payload)]),
        )

        return MultiAgentResult(
            status=Status.COMPLETED,
            results={self.name: NodeResult(result=agent_result)},
        )
