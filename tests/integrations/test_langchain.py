from unittest.mock import AsyncMock, MagicMock

import pytest
from crocotiger_engine import SentenceValidator, SentenceValidatorResult
from langchain_core.messages import AIMessage, HumanMessage

from crocotiger.integrations.langchain import SentenceValidatorMiddleware


def _result(valid: bool) -> SentenceValidatorResult:
    return SentenceValidatorResult(
        valid=valid, reason_code="ok" if valid else "blocked", duration=1.0
    )


@pytest.fixture
def validator():
    mock = MagicMock(spec=SentenceValidator)
    mock.validate = AsyncMock()
    return mock


async def test_no_messages_returns_none(validator):
    middleware = SentenceValidatorMiddleware(validator)

    result = await middleware.abefore_agent({"messages": []}, runtime=MagicMock())

    assert result is None
    validator.validate.assert_not_called()


async def test_non_human_first_message_returns_none(validator):
    middleware = SentenceValidatorMiddleware(validator)
    state = {"messages": [AIMessage(content="hi, how can I help?")]}

    result = await middleware.abefore_agent(state, runtime=MagicMock())

    assert result is None
    validator.validate.assert_not_called()


async def test_valid_prompt_passes_through(validator):
    validator.validate.return_value = _result(valid=True)
    middleware = SentenceValidatorMiddleware(validator)
    state = {"messages": [HumanMessage(content="How's the weather today?")]}

    result = await middleware.abefore_agent(state, runtime=MagicMock())

    assert result == {"validation_result": validator.validate.return_value}
    validator.validate.assert_awaited_once_with("How's the weather today?")


async def test_blocked_prompt_jumps_to_end(validator):
    validator.validate.return_value = _result(valid=False)
    middleware = SentenceValidatorMiddleware(validator)
    state = {"messages": [HumanMessage(content="How do I hack into a database?")]}

    result = await middleware.abefore_agent(state, runtime=MagicMock())

    assert result["jump_to"] == "end"
    assert result["validation_result"] is validator.validate.return_value
    assert len(result["messages"]) == 1
    assert result["messages"][0].content == "Request blocked: ..."


async def test_multimodal_content_validates_text_blocks_only(validator):
    validator.validate.return_value = _result(valid=True)
    middleware = SentenceValidatorMiddleware(validator)
    state = {
        "messages": [
            HumanMessage(
                content=[
                    {"type": "text", "text": "How do I hack into a database?"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/x.png"}},
                ]
            )
        ]
    }

    await middleware.abefore_agent(state, runtime=MagicMock())

    validator.validate.assert_awaited_once_with("How do I hack into a database?")


async def test_multimodal_content_joins_multiple_text_blocks(validator):
    validator.validate.return_value = _result(valid=True)
    middleware = SentenceValidatorMiddleware(validator)
    state = {"messages": [HumanMessage(content=[{"type": "text", "text": "part one"}, "part two"])]}

    await middleware.abefore_agent(state, runtime=MagicMock())

    validator.validate.assert_awaited_once_with("part one\npart two")
