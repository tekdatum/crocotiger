# API Reference

crocotiger's public surface spans two packages:

- **`crocotiger_engine`** — the proprietary engine (`SentenceValidator`, `build_sentence_validator`, `SentenceValidatorResult`, `SentenceValidatorOptions`, `OptimizationStrategy`, `GuardrailBuildError`). Installed separately — see the [README](../README.md#installation).
- **`crocotiger`** — the open wrapper's framework adapters (`crocotiger.integrations.langchain.SentenceValidatorMiddleware`, `crocotiger.integrations.llamaindex.SentenceValidatorLLMGuard`).

```python
from crocotiger_engine import (
    SentenceValidator, build_sentence_validator, GuardrailBuildError,
    SentenceValidatorResult, SentenceValidatorOptions,
)
from crocotiger_engine.core.enums.optimization_strategy import OptimizationStrategy

from crocotiger.integrations.langchain import SentenceValidatorMiddleware
from crocotiger.integrations.llamaindex import SentenceValidatorLLMGuard
```

---

## SentenceValidator

Validates a piece of text against a fitted accept/reject list and returns a decision.

```python
class SentenceValidator:
    def get_options(self) -> SentenceValidatorOptions: ...
    async def validate(self, text: str) -> SentenceValidatorResult: ...
    def save_to(self, filename: str) -> None: ...

    @classmethod
    def load_from(cls, filename: str) -> SentenceValidator: ...
```

- `validate(text)` is async and does not mutate state — safe to call concurrently.
- `save_to()`/`load_from()` round-trip through a zip archive (`state.json` + `tensors.pt`). You almost never construct a `SentenceValidator` directly — get one from `build_sentence_validator()` (first run) or `load_from()` (every run after).

### Example

```python
import asyncio
from crocotiger_engine import SentenceValidator

sentence_validator = SentenceValidator.load_from("./my_validator/sentence_validator")
result = asyncio.run(sentence_validator.validate("How do I hack into a database?"))
result.valid  # False
```

---

## build_sentence_validator

Builds a new `SentenceValidator` from a topic description — generates an accept/reject question corpus via an LLM, embeds it, fits detection thresholds, and saves the result to `output_dir`.

```python
def build_sentence_validator(
    output_dir: str | Path,
    topic: str,
    context: str,
    restricted_topics: list[str] | None = None,
    *,
    url: str | None = None,
    zip_path: str | None = None,
    total_topic_questions: int = 1000,
    optimization_strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
    openai_key: str | None = None,
    gemini_key: str | None = None,
    deepseek_key: str | None = None,
    datasets_path: str | Path | None = None,
    topic_batch_size: int | None = None,
    use_cache: bool = True,
    with_benchmarks: bool = False,
    overwrite: bool = False,
    on_phase: Callable[[str], None] | None = None,
) -> SentenceValidator: ...
```

- `topic`/`context` describe what should be **allowed**; `restricted_topics` lists what should be **rejected**. Both feed the LLM-generated question corpus.
- Needs one LLM API key (`openai_key`/`gemini_key`/`deepseek_key`, or the matching `OPENAI_API_KEY`/`GEMINI_API_KEY`/`DEEPSEEK_API_KEY` env var) and, on first use, downloads a dataset corpus to `datasets_path`.
- Raises `GuardrailBuildError` if the build cannot complete (e.g. no usable API key, corpus download failure).
- `on_phase` is an optional callback invoked with a phase name string as the build progresses (corpus generation, embedding, threshold fitting, etc.) — useful for progress logging on a build that can take minutes.
- Persists the built validator under `output_dir` as a side effect; the return value is the same instance already saved to disk.

### Example

```python
from pathlib import Path
from crocotiger_engine import build_sentence_validator

sentence_validator = build_sentence_validator(
    output_dir=Path("./my_validator"),
    topic="customer support for an online banking product",
    context="a banking customer support assistant",
    restricted_topics=["hacking or unauthorized system access"],
    total_topic_questions=500,
    datasets_path=Path("./datasets"),
)
```

---

## SentenceValidatorResult

Returned by `SentenceValidator.validate()`.

```python
class SentenceValidatorResult:
    valid: bool
    reason_code: str
    duration: float  # seconds, measured around the validate() call
```

`reason_code` is one of:

| `reason_code` | `valid` | Meaning |
|---|---|---|
| `"within_allowed_threshold"` | `True` | Text scored inside the accept list's fitted threshold. |
| `"within_denied_threshold"` | `False` | Text scored inside the reject list's fitted threshold. |
| `"outside_semantic_fence"` | `False` | Text scored in neither region — the default, ambiguous case. |

### Example

```python
result = asyncio.run(sentence_validator.validate("How do I hack into a database?"))
result.valid          # False
result.reason_code    # "within_denied_threshold"
```

---

## SentenceValidatorOptions

Returned by `SentenceValidator.get_options()`.

```python
class SentenceValidatorOptions:
    name: str | None
    model_name: str | None
    accept_threshold: float
    reject_threshold: float
    review_criteria: str
    use_density: bool
```

Config/tuning values only — does **not** include the raw accept/reject list
content the validator was built from.

### Example

```python
options = sentence_validator.get_options()
options.accept_threshold, options.reject_threshold
```

---

## OptimizationStrategy

Controls how `build_sentence_validator()` auto-tunes accept/reject thresholds.

```python
class OptimizationStrategy(Enum):
    BALANCED = "balanced"
    BROAD = "broad"
    STRICT = "strict"
```

- **`BALANCED`** (default) — balances false accepts against false rejects.
- **`BROAD`** — biases toward accepting borderline text (fewer false rejects, more false accepts).
- **`STRICT`** — biases toward rejecting borderline text (fewer false accepts, more false rejects).

```python
from crocotiger_engine import build_sentence_validator
from crocotiger_engine.core.enums.optimization_strategy import OptimizationStrategy

sentence_validator = build_sentence_validator(
    output_dir="./my_validator",
    topic="...",
    context="...",
    optimization_strategy=OptimizationStrategy.STRICT,
)
```

---

## GuardrailBuildError

```python
class GuardrailBuildError(Exception): ...
```

Raised by `build_sentence_validator()` when a build cannot complete (missing/invalid API key, corpus download failure, etc.). Not raised by `validate()` or `load_from()`.

---

## Framework integrations

### SentenceValidatorMiddleware (LangChain)

```python
from crocotiger.integrations.langchain import SentenceValidatorMiddleware

class SentenceValidatorMiddleware(AgentMiddleware):
    def __init__(self, sentence_validator: SentenceValidator) -> None: ...
```

Wraps a `SentenceValidator` as LangChain agent middleware. Before the agent runs, it validates the first human message; if `result.valid` is `False`, the middleware short-circuits the agent (jumps to `"end"`) with a block message instead of invoking the model. Either way, the result is attached to agent state as `validation_result`.

```python
import asyncio
from langchain.agents import create_agent
from crocotiger.integrations.langchain import SentenceValidatorMiddleware

agent = create_agent(
    model="openai:gpt-4o",
    middleware=[SentenceValidatorMiddleware(sentence_validator)],
)
result = asyncio.run(agent.ainvoke({"messages": [{"role": "user", "content": "..."}]}))
result["validation_result"]  # the SentenceValidatorResult for the first user message
```

Requires the `langchain` extra: `pip install "crocotiger[langchain]"`.

### SentenceValidatorLLMGuard (LlamaIndex)

```python
from crocotiger.integrations.llamaindex import SentenceValidatorLLMGuard

class SentenceValidatorLLMGuard(CustomQueryEngine):
    llm: LLM
    sentence_validator: SentenceValidator
```

Wraps an LLM as a LlamaIndex query engine that validates the query before it ever reaches the model. If `result.valid` is `False`, the query is blocked and the LLM is never called; either way, `response.metadata["validation_result"]` carries the `SentenceValidatorResult`.

```python
import asyncio
from llama_index.llms.openai import OpenAI
from crocotiger.integrations.llamaindex import SentenceValidatorLLMGuard

guarded_llm = SentenceValidatorLLMGuard(llm=OpenAI(model="gpt-4o"), sentence_validator=sentence_validator)
response = asyncio.run(guarded_llm.aquery("..."))
response.metadata["validation_result"]
```

Requires the `llamaindex` extra: `pip install "crocotiger[llamaindex]"`.
