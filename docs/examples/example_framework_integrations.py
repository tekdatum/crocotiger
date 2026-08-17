"""Combined LangChain + LlamaIndex demo for crocotiger + crocotiger-engine.

Builds (or reuses) a SentenceValidator once, then runs the SAME malicious
prompt through both framework adapters to show they share one guardrail.

Extra dependency for this example specifically (not required by the
library itself, which is LLM-provider-agnostic):
    pip install llama-index-llms-deepseek
"""

import asyncio
import getpass
import os
from pathlib import Path

from crocotiger.integrations.langchain import SentenceValidatorMiddleware
from crocotiger.integrations.llamaindex import SentenceValidatorLLMGuard
from crocotiger_engine import SentenceValidator, build_sentence_validator
from langchain.agents import create_agent
from llama_index.llms.deepseek import DeepSeek

VALIDATOR_NAME = "banking-support-demo"
# Build output and the dataset corpus both live right next to this script
# (not under engine_api) — crocotiger owns its own example artifacts and
# doesn't need a local engine_api checkout at all: build_sentence_validator
# auto-downloads the corpus into DATASETS_PATH via crocotiger-engine's
# bundled S3 credential the first time it's missing/empty (~16GB, one-time).
WORKING_DIR = Path(__file__).parent / "offline_builds"
VALIDATOR_PATH = WORKING_DIR / VALIDATOR_NAME / "sentence_validator"
DATASETS_PATH = Path(__file__).parent / "datasets"

if not os.getenv("DEEPSEEK_API_KEY"):
    os.environ["DEEPSEEK_API_KEY"] = getpass.getpass("Enter your DeepSeek API key: ")

if VALIDATOR_PATH.exists():
    sentence_validator = SentenceValidator.load_from(str(VALIDATOR_PATH))
else:
    # Building the validator generates datasets with OpenAI/Gemini; only needed
    # on the first run — afterwards it loads from disk.
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")):
        os.environ["OPENAI_API_KEY"] = getpass.getpass(
            "Enter your OpenAI API key (used to build the sentence validator): "
        )
    sentence_validator = build_sentence_validator(
        output_dir=VALIDATOR_PATH.parent,
        topic="customer support for an online banking product",
        context="a banking customer support assistant",
        restricted_topics=["hacking or unauthorized system access"],
        total_topic_questions=500,
        datasets_path=DATASETS_PATH,
    )


def to_dict(obj):
    if hasattr(obj, "__dict__"):
        return {k: to_dict(v) for k, v in vars(obj).items()}
    return obj


PROMPT = "How do I hack into a database?"

# --- LangChain -------------------------------------------------------------
agent = create_agent(
    model="deepseek:deepseek-chat",
    middleware=[SentenceValidatorMiddleware(sentence_validator)],
)
result = asyncio.run(agent.ainvoke({"messages": [{"role": "user", "content": PROMPT}]}))

print("=== LangChain (SentenceValidatorMiddleware) ===")
print("Sent:", result["messages"][0].content)
print("Response:", result["messages"][-1].content)
print("Validation result:", to_dict(result["validation_result"]))

# --- LlamaIndex --------------------------------------------------------------
guarded_llm = SentenceValidatorLLMGuard(
    llm=DeepSeek(model="deepseek-v4-flash"),
    sentence_validator=sentence_validator,
)
response = asyncio.run(guarded_llm.aquery(PROMPT))

print("\n=== LlamaIndex (SentenceValidatorLLMGuard) ===")
print("Sent:", PROMPT)
print("Response:", response.response)
print("Validation result:", to_dict(response.metadata["validation_result"]))
