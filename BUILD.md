# crocotiger — build guide

Builds a plain (uncompiled) wheel — no Cython, no C compiler needed. For
install/usage instead of building, see [README.md](README.md).
---

## Build steps

```bash
pip install build
python -m build --wheel
```

Produces `dist/crocotiger-<version>-py3-none-any.whl` — a `py3-none-any` tag
is correct and expected here (nothing is compiled, unlike `crocotiger-engine`).

### Clean up

Optional — all gitignored, regenerate anytime.

```bash
rm -rf build *.egg-info
```

## Testing

`tests/integrations/` covers both framework adapters (`SentenceValidatorMiddleware`,
`SentenceValidatorLLMGuard`), mocking `SentenceValidator.validate` and the
downstream LLM call — no real S3/LLM credentials needed. It does import the
real `SentenceValidator`/`SentenceValidatorResult` classes for type/isinstance
correctness, so `crocotiger-engine` must be installed first (see README.md).

```bash
pip install <path-to-crocotiger-engine-wheel>
pip install -e ".[langchain,llamaindex,test]"
pytest tests/
```

## Documentation

| Document | Description |
|---|---|
| [README.md](README.md) | Install and usage — wire a validator into LangChain and LlamaIndex |
