"""Inject a minimal crocotiger_engine stub into sys.modules before any
crocotiger import.

Runs via pytest_configure (before collection) so test files can import
crocotiger_engine at module level without the proprietary (private, not on
PyPI) engine installed. Mirrors the equivalent stub in simlar's own
tests/conftest.py.

The stub is always active, deterministically, regardless of whether the
real crocotiger_engine happens to be installed -- these tests validate
crocotiger's own adapter/middleware logic against a well-defined mock
contract, not the real engine's behavior (that's the private engine repo's
own test suite's job). Preferring a real install when present was
considered and rejected: it would make test results depend on what happens
to be in a given environment (non-deterministic across contributors/CI),
and would pull in the real engine's heavy dependencies (torch,
sentence-transformers) just for class introspection.
"""

from __future__ import annotations

import sys
import types


class _StubSentenceValidatorResult:
    def __init__(self, valid: bool, reason_code: str, duration: float) -> None:
        self.valid = valid
        self.reason_code = reason_code
        self.duration = duration


class _StubSentenceValidatorOptions:
    def __init__(
        self,
        name: str | None = None,
        model_name: str | None = None,
        accept_threshold: float = 0.5,
        reject_threshold: float = 0.5,
        review_criteria: str = "base",
        use_density: bool = False,
    ) -> None:
        self.name = name
        self.model_name = model_name
        self.accept_threshold = accept_threshold
        self.reject_threshold = reject_threshold
        self.review_criteria = review_criteria
        self.use_density = use_density


class _StubGuardrailBuildError(Exception):
    pass


class _StubSentenceValidator:
    def get_options(self) -> _StubSentenceValidatorOptions:
        return _StubSentenceValidatorOptions()

    async def validate(self, text: str) -> _StubSentenceValidatorResult:
        return _StubSentenceValidatorResult(valid=True, reason_code="stub", duration=0.0)

    def save_to(self, filename: str) -> None:
        pass

    @classmethod
    def load_from(cls, filename: str) -> _StubSentenceValidator:
        return cls()


def _stub_build_sentence_validator(*args, **kwargs) -> _StubSentenceValidator:
    return _StubSentenceValidator()


def _inject_crocotiger_engine_stub() -> None:
    """Populate sys.modules with a stub crocotiger_engine module."""
    if "crocotiger_engine" in sys.modules:
        return  # already stubbed (e.g. a previous test session in this process)

    mod = types.ModuleType("crocotiger_engine")
    mod.SentenceValidator = _StubSentenceValidator  # type: ignore[attr-defined]
    mod.SentenceValidatorResult = _StubSentenceValidatorResult  # type: ignore[attr-defined]
    mod.SentenceValidatorOptions = _StubSentenceValidatorOptions  # type: ignore[attr-defined]
    mod.GuardrailBuildError = _StubGuardrailBuildError  # type: ignore[attr-defined]
    mod.build_sentence_validator = _stub_build_sentence_validator  # type: ignore[attr-defined]
    mod.__all__ = [  # type: ignore[attr-defined]
        "SentenceValidator",
        "SentenceValidatorResult",
        "SentenceValidatorOptions",
        "GuardrailBuildError",
        "build_sentence_validator",
    ]
    sys.modules["crocotiger_engine"] = mod


def pytest_configure(config) -> None:
    """Inject the engine stub before any test module is imported."""
    _inject_crocotiger_engine_stub()
