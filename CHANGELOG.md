# Changelog

All notable changes to **crocotiger** (the open-source wrapper) are documented here.
Dates are in YYYY-MM-DD format.

## [Unreleased]

### Added
- Initial public SDK: `crocotiger_engine` re-exports (`SentenceValidator`,
  `build_sentence_validator`, `SentenceValidatorResult`,
  `SentenceValidatorOptions`, `GuardrailBuildError`).
- LangChain integration: `SentenceValidatorMiddleware` (`pip install crocotiger[langchain]`).
- LlamaIndex integration: `SentenceValidatorLLMGuard` (`pip install crocotiger[llamaindex]`).
