# Concepts

## What is crocotiger?

`crocotiger` is a sentence-level prompt guardrail. Given a piece of text , it decides whether that text acceptable or not before the text ever reaches your LLM.

## Open wrapper vs proprietary engine

crocotiger is split across two packages with different licenses:

| Layer | Package | License | What it does |
|---|---|---|---|
| Open wrapper | `crocotiger` | Apache 2.0 | Framework adapters (`SentenceValidatorMiddleware`, `SentenceValidatorLLMGuard`) that wire a validator into LangChain/LlamaIndex. |
| Proprietary engine | `crocotiger-engine` | Commercial EULA | The actual guardrail: `SentenceValidator`, `build_sentence_validator`, embeddings, threshold fitting. |

See the [README](../README.md#license-boundary) for the full licensing detail. This document covers how the two work together conceptually.

## Building vs loading a validator

A `SentenceValidator` is built once from a topic description, then reused indefinitely from a saved artifact:

- **`build_sentence_validator(...)`** — describe what should be allowed (`topic`, `context`) and what should be restricted (`restricted_topics`). This generates a question corpus via an LLM, embeds it, and fits accept/reject thresholds. It costs real LLM API calls and can take minutes — you do this once per guardrail configuration, not per request.
- **`SentenceValidator.load_from(path)`** — reloads a previously built validator from disk. No LLM calls, no network access beyond loading local files. This is what you use on every subsequent run.

```python
from pathlib import Path
from crocotiger_engine import SentenceValidator, build_sentence_validator

validator_path = Path("./my_validator/sentence_validator")

if validator_path.exists():
    sentence_validator = SentenceValidator.load_from(str(validator_path))
else:
    sentence_validator = build_sentence_validator(
        output_dir=validator_path.parent,
        topic="customer support for an online banking product",
        context="a banking customer support assistant",
        restricted_topics=["hacking or unauthorized system access"],
    )
```

## How validate() works

`validate(text)` embeds the text and compares it against the fitted accept-list and reject-list embeddings. The result is one of three outcomes, reported as `reason_code`:

| `reason_code` | `valid` | Meaning |
|---|---|---|
| `within_allowed_threshold` | `True` | Close enough to the accept list to allow. |
| `within_denied_threshold` | `False` | Close enough to the reject list to block. |
| `outside_semantic_fence` | `False` | Neither — an ambiguous case, treated as not valid. |

`reason_code` is the full explanation surface — the result doesn't expose the underlying nearest-neighbor matches or scores that produced it, since that detail isn't meaningful outside deep_firewall's own product.

## Optimization strategies

`build_sentence_validator()` auto-tunes the accept/reject thresholds according to an `OptimizationStrategy`:

- **`BALANCED`** (default) — balances false accepts against false rejects.
- **`BROAD`** — fewer false rejects, at the cost of more false accepts. Use when letting a borderline request through is cheaper than blocking a legitimate one.
- **`STRICT`** — fewer false accepts, at the cost of more false rejects. Use when a missed block is more costly than an over-eager one.

There is no single right choice — it depends on which kind of mistake is more expensive for your product.

## Framework integrations

crocotiger doesn't require a framework — `SentenceValidator.validate()` works standalone. The framework adapters exist to wire that decision into an agent pipeline without hand-rolling the plumbing:

- **LangChain** — `SentenceValidatorMiddleware` runs before the agent processes the first user message. If the message is invalid, the middleware jumps straight to the end of the graph with a block message, and the underlying LLM is never called.
- **LlamaIndex** — `SentenceValidatorLLMGuard` wraps an `LLM` as a query engine. An invalid query is blocked before `llm.acomplete()`/`llm.aquery()` ever runs.

Both attach the `SentenceValidatorResult` to their output (`state["validation_result"]` / `response.metadata["validation_result"]`), so callers can inspect `reason_code` to see *why* a request was blocked, not just whether it was.

## Saving and loading

A built validator is a single artifact — a zip containing its fitted state (`state.json`) and its embedding tensors (`tensors.pt`):

```python
sentence_validator.save_to("./my_validator/sentence_validator")

sentence_validator = SentenceValidator.load_from("./my_validator/sentence_validator")
```

Commit this artifact (or store it in a shared location) so every environment loads the same validator instead of rebuilding it — rebuilding costs LLM API calls, loading does not.
