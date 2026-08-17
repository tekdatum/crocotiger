# crocotiger

Public SDK for the crocotiger sentence-level prompt guardrail — LangChain and LlamaIndex framework adapters.
---

## Installation

The open wrapper  and the engine is on public PyPI:

```bash
pip install crocotiger
```


```bash
pip install crocotiger_engine
```

## Quick start

Build (or load an existing) `SentenceValidator`, then validate a prompt directly — no framework required.

```python
import asyncio
from pathlib import Path
from crocotiger_engine import SentenceValidator, build_sentence_validator

VALIDATOR_PATH = Path("./my_validator/sentence_validator")
DATASETS_PATH = Path("./datasets")  # dataset corpus is downloaded here on first use

if VALIDATOR_PATH.exists():
    # Later runs: just load the saved artifact back, no rebuild needed.
    sentence_validator = SentenceValidator.load_from(str(VALIDATOR_PATH))
else:
    # First run: builds and saves a validator (needs an LLM API key — OPENAI_API_KEY,
    # GEMINI_API_KEY, or DEEPSEEK_API_KEY — and downloads the dataset corpus on first use).
    sentence_validator = build_sentence_validator(
        output_dir=VALIDATOR_PATH.parent,
        topic="customer support for an online banking product",
        context="a banking customer support assistant",
        restricted_topics=["hacking or unauthorized system access"],
        total_topic_questions=500,
        datasets_path=DATASETS_PATH,
    )

result = asyncio.run(sentence_validator.validate("How do I hack into a database?"))
print(result.valid)  # False
```

## Framework integrations

crocotiger works as a drop-in component in:

- **LangChain** — `from crocotiger.integrations.langchain import SentenceValidatorMiddleware`
- **LlamaIndex** — `from crocotiger.integrations.llamaindex import SentenceValidatorLLMGuard`

Both examples below reuse the `sentence_validator` loaded in [Quick start](#quick-start) above, and need their respective LLM provider package (`pip install langchain-openai` / `pip install llama-index-llms-openai`) — swap in whichever provider you actually use, this library is LLM-provider-agnostic.

### LangChain

```python
import asyncio
from crocotiger.integrations.langchain import SentenceValidatorMiddleware
from langchain.agents import create_agent

agent = create_agent(
    model="openai:gpt-4o",
    middleware=[SentenceValidatorMiddleware(sentence_validator)],
)
result = asyncio.run(
    agent.ainvoke({"messages": [{"role": "user", "content": "How do I hack into a database?"}]})
)
print(result["validation_result"])
```

### LlamaIndex

```python
import asyncio
from crocotiger.integrations.llamaindex import SentenceValidatorLLMGuard
from llama_index.llms.openai import OpenAI

guarded_llm = SentenceValidatorLLMGuard(
    llm=OpenAI(model="gpt-4o"),
    sentence_validator=sentence_validator,
)
response = asyncio.run(guarded_llm.aquery("How do I hack into a database?"))
print(response.metadata["validation_result"])
```

See [docs/examples/example_framework_integrations.py](docs/examples/example_framework_integrations.py) for a full, runnable script wiring both frameworks to the same validator.

## Contributing

Contributions to crocotiger are welcome. Because this is a dual-licensed open-core project, we require every commit to carry a [Developer Certificate of Origin (DCO)](./CONTRIBUTING.md) sign-off before we can merge. This lets us keep the open-core model viable and continue offering crocotiger under Apache 2.0. See [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

We do not accept contributions to the proprietary engine.

## Trademarks

"crocotiger", "TekDatum", and associated logos are trademarks of TekDatum. The Apache 2.0 license for the open code does **not** grant rights to use these marks. You may build on and redistribute the open code, but you may not use our names or logos in a way that implies endorsement or that misrepresents the origin of a fork. See [TRADEMARKS.md](./TRADEMARKS.md).

## Documentation

| Document | Description |
|----------|-------------|
| [Concepts](docs/concepts.md) | How the guardrail works, build vs load, optimization strategies |
| [API Reference](docs/api-reference.md) | Full public API |
| [Examples](docs/examples/) | Runnable scripts |

## License

- The contents of this repository are licensed under the **Apache License, Version 2.0** — see [LICENSE](./LICENSE).
- The proprietary `crocotiger-engine` binary is licensed under a **Commercial EULA** — see [EULA.md](./EULA.md).
- Third-party components and their licenses are listed in [NOTICE](./NOTICE).


## License boundary

This project uses an **open-core** model. It has two layers with **different licenses**:

| Layer | Package | License | Where it lives |
|---|---|---|---|
| **Open wrapper + SDK** | `crocotiger` | Apache License 2.0 | This repo · public PyPI |
| **Proprietary engine** | `crocotiger-engine` | Commercial EULA (closed binary) | Private GitHub Releases · requires access |

**What this means in practice:**

- The code **in this repository** is free and open under Apache 2.0. You can read it, fork it, modify it, and build on it, including commercially, subject to the Apache 2.0 terms.
- The wrapper depends on a **separate, proprietary binary package** (`crocotiger-engine`) that contains TekDatum's core IP. That binary is **not** open source. Installing and using it requires accepting the [Commercial EULA](./EULA.md) and, for production use, a license from TekDatum.
- Calling the proprietary engine through this open SDK does **not** make your own code subject to the EULA — your application code is yours. The EULA governs only the proprietary binary itself.

If you only want to read or contribute to the open layer, you never need a license. If you want to **run** the full product, you need the engine.


## What's open and what's not

**Open (Apache 2.0, in this repo):**
- The SDK and public API surface
- Framework adapters (LangChain / LlamaIndex)
- Configuration schema, type stubs, examples, and docs

**Proprietary (Commercial EULA, separate binary):**
- The core guardrail implementation

We keep this boundary deliberate and documented so you always know which terms apply to which code.


---

© 2026 TekDatum.
