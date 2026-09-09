# Changelog

All notable changes to **crocotiger** (the open-source wrapper) are documented here.
Dates are in YYYY-MM-DD format.

## [Unreleased]

## [0.1.1] - 2026-09-09

### Fixed
- `docs/api-reference.md`'s `build_sentence_validator` signature corrected to
  match `crocotiger-engine`'s real parameters: dropped a stale `use_cache`
  entry that isn't a real parameter at all, and updated
  `overwrite`/`with_benchmarks`/`on_phase` to their current names
  (`allow_rebuild`/`run_benchmarks`/`progress_callback`, see
  `crocotiger-engine`'s 0.2.0 changelog entry). Docs-only — no code in this
  package changed, since nothing here calls any of these by name.

## [0.1.0] - 2026-09-08

### Added
- Initial public SDK: `crocotiger_engine` re-exports (`SentenceValidator`,
  `build_sentence_validator`, `SentenceValidatorResult`,
  `SentenceValidatorOptions`, `GuardrailBuildError`).
- LangChain integration: `SentenceValidatorMiddleware` (`pip install crocotiger[langchain]`).
- LlamaIndex integration: `SentenceValidatorLLMGuard` (`pip install crocotiger[llamaindex]`).
