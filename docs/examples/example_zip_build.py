"""Builds a SentenceValidator from a ZIP of reference documents, instead of
just a topic description.

crocotiger-engine's ZipLoader (used internally when `zip_path` is passed to
build_sentence_validator) reads every file in the zip and feeds its content
to the topic-question generator — useful when you already have real
reference material (product docs, policy PDFs, support articles, ...)
instead of describing the topic from scratch. PDF files inside the zip get
their text extracted via PyPDF2 (see crocotiger-engine's
builder/utils/pdf_utils.py); everything else is read as UTF-8 text.

Only needs one of OPENAI_API_KEY/GEMINI_API_KEY/DEEPSEEK_API_KEY — no
LangChain/LlamaIndex wiring here, just the build plus a direct validate()
call. See example_1.py for wiring a built validator into both framework
adapters.
"""

import asyncio
import getpass
import os
import zipfile
from pathlib import Path

from crocotiger_engine import SentenceValidator, build_sentence_validator

VALIDATOR_NAME = "product-docs-support"
# Shares offline_builds/ and datasets/ with example_1.py's demo — same
# corpus cache, no duplicate ~16GB download.
WORKING_DIR = Path(__file__).parent / "offline_builds"
VALIDATOR_PATH = WORKING_DIR / VALIDATOR_NAME / "sentence_validator"
DATASETS_PATH = Path(__file__).parent / "datasets"
ZIP_PATH = WORKING_DIR / VALIDATOR_NAME / "source_docs.zip"

# --- Stand-in for real reference material -----------------------------------
# In practice this zip would hold actual product docs / policy PDFs / support
# articles. ZipLoader reads every file here and uses its content to generate
# in-topic training questions, instead of relying only on `topic`/`context`.
SAMPLE_DOCS = {
    "refund_policy.txt": (
        "Refunds are available within 30 days of purchase for unused "
        "products in original packaging. Store credit is issued instead of "
        "a refund for purchases made with a gift card."
    ),
    "shipping_faq.txt": (
        "Standard shipping takes 3-5 business days. Expedited shipping "
        "takes 1-2 business days and is available at checkout for an "
        "additional fee. We do not ship to PO boxes."
    ),
}


def _build_sample_zip(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in SAMPLE_DOCS.items():
            zf.writestr(name, content)


if not (
    os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
):
    os.environ["OPENAI_API_KEY"] = getpass.getpass(
        "Enter your OpenAI API key (used to build the sentence validator): "
    )

if VALIDATOR_PATH.exists():
    sentence_validator = SentenceValidator.load_from(str(VALIDATOR_PATH))
else:
    if not ZIP_PATH.exists():
        _build_sample_zip(ZIP_PATH)

    sentence_validator = build_sentence_validator(
        output_dir=VALIDATOR_PATH.parent,
        topic="customer support for an e-commerce store's shipping and refund policies",
        context="an e-commerce customer support assistant",
        restricted_topics=["processing payments or accessing order data directly"],
        zip_path=str(ZIP_PATH),
        total_topic_questions=300,
        datasets_path=DATASETS_PATH,
    )

# --- Try it out --------------------------------------------------------------
for prompt in [
    "What's your refund policy for a gift-card purchase?",
    "Can you manually charge my credit card for $500?",
]:
    result = asyncio.run(sentence_validator.validate(prompt))
    print(f"{result.valid!s:>5}  {prompt}")
