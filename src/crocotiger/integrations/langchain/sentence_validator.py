from typing import Annotated, Any, NotRequired

from crocotiger_engine import SentenceValidator, SentenceValidatorResult
from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langchain.agents.middleware.types import OmitFromInput
from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime


class SentenceValidatorState(AgentState):
    """Extends `AgentState` with the last sentence-review result.

    `OmitFromInput` keeps this out of what a caller needs to supply when
    invoking the agent, while still surfacing it in the final output state —
    diagnostic metadata for callers/tests, not something the LLM should see.
    """

    validation_result: NotRequired[Annotated[SentenceValidatorResult | None, OmitFromInput]]


def _extract_text(content: str | list[str | dict[str, Any]]) -> str:
    """Pull the text portion out of a LangChain message's content.

    `content` is a plain string for a text-only message, or a list of content
    blocks for a multimodal one (e.g. text + image blocks) — each block is
    either a bare string or a dict with a "text" key (LangChain/OpenAI's
    content-block convention). Non-text blocks (images, etc.) are dropped;
    only the text portions get validated.
    """
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and isinstance(block.get("text"), str):
            parts.append(block["text"])
    return "\n".join(parts)


class SentenceValidatorMiddleware(AgentMiddleware):
    """Middleware that uses a SentenceValidator to block requests containing banned keywords."""

    state_schema = SentenceValidatorState

    def __init__(self, sentence_validator: SentenceValidator):
        super().__init__()
        self.sentence_validator = sentence_validator

    @hook_config(can_jump_to=["end"])
    async def abefore_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        # Get the first user message
        if not state["messages"]:
            return None

        first_message = state["messages"][0]
        if first_message.type != "human":
            return None

        content = _extract_text(first_message.content)

        result = await self.sentence_validator.validate(content)

        if result.valid:
            return {"validation_result": result}

        return {
            "jump_to": "end",
            "messages": [AIMessage(content="Request blocked: ...")],
            "validation_result": result,
        }
