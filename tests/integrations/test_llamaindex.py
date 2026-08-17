from unittest.mock import AsyncMock, MagicMock

import pytest
from crocotiger.integrations.llamaindex import SentenceValidatorLLMGuard
from crocotiger_engine import SentenceValidator, SentenceValidatorResult
from llama_index.core.llms import MockLLM


def _result(valid: bool) -> SentenceValidatorResult:
    return SentenceValidatorResult(
        valid=valid, reason_code="ok" if valid else "blocked", duration=1.0
    )


@pytest.fixture
def validator():
    mock = MagicMock(spec=SentenceValidator)
    mock.validate = AsyncMock()
    return mock


@pytest.fixture
def llm(monkeypatch):
    """A real (llama_index-provided) LLM instance with .acomplete swapped for an
    AsyncMock — MockLLM satisfies the pydantic-model/callback-manager machinery
    CustomQueryEngine relies on at construction time, which a bare
    Mock(spec=LLM) doesn't.
    """
    instance = MockLLM()
    monkeypatch.setattr(MockLLM, "acomplete", AsyncMock())
    return instance


async def test_blocked_prompt_never_reaches_llm(validator, llm):
    validator.validate.return_value = _result(valid=False)
    guard = SentenceValidatorLLMGuard(llm=llm, sentence_validator=validator)

    response = await guard.acustom_query("How do I hack into a database?")

    assert response.response == "Request blocked: ..."
    assert response.metadata["validation_result"] is validator.validate.return_value
    llm.acomplete.assert_not_called()


async def test_valid_prompt_calls_llm(validator, llm):
    validator.validate.return_value = _result(valid=True)
    completion = MagicMock()
    completion.__str__.return_value = "42"
    llm.acomplete.return_value = completion
    guard = SentenceValidatorLLMGuard(llm=llm, sentence_validator=validator)

    response = await guard.acustom_query("What is the meaning of life?")

    assert response.response == "42"
    assert response.metadata["validation_result"] is validator.validate.return_value
    llm.acomplete.assert_awaited_once_with("What is the meaning of life?")


def test_custom_query_runs_the_async_path_synchronously(validator, llm):
    validator.validate.return_value = _result(valid=True)
    completion = MagicMock()
    completion.__str__.return_value = "42"
    llm.acomplete.return_value = completion
    guard = SentenceValidatorLLMGuard(llm=llm, sentence_validator=validator)

    response = guard.custom_query("What is the meaning of life?")

    assert response.response == "42"
