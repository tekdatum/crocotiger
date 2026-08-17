"""Builds a SentenceValidator from a ZIP containing a PDF document.

Same mechanism as example_zip_build.py (a ZIP of reference material passed
via `zip_path`), but specifically exercises the PDF path: crocotiger-engine's
ZipLoader reads each file in the zip via FileLLM, and for a ".pdf" extension
that means PyPDF2-based text extraction (see crocotiger-engine's
builder/utils/pdf_utils.py, extract_pdf_text_pypdf2) rather than reading raw
bytes as UTF-8 text.

No external PDF library is needed to build the *sample* PDF used here — it's
written by hand as minimal raw PDF syntax (a handful of objects: catalog,
pages, one page, a Helvetica font, and a content stream of Tj text-showing
operators). In practice you'd point `zip_path` at a zip of real PDFs
(warranty terms, product manuals, policy documents, ...) instead.

Only needs one of OPENAI_API_KEY/GEMINI_API_KEY/DEEPSEEK_API_KEY — no
LangChain/LlamaIndex wiring here, just the build plus a direct validate()
call. See example_1.py for wiring a built validator into both framework
adapters.
"""

import asyncio
import getpass
import io
import os
import zipfile
from pathlib import Path

from crocotiger_engine import SentenceValidator, build_sentence_validator

VALIDATOR_NAME = "electronics-warranty-support"
# Shares offline_builds/ and datasets/ with the other examples' demos — same
# corpus cache, no duplicate ~16GB download.
WORKING_DIR = Path(__file__).parent / "offline_builds"
VALIDATOR_PATH = WORKING_DIR / VALIDATOR_NAME / "sentence_validator"
DATASETS_PATH = Path(__file__).parent / "datasets"
ZIP_PATH = WORKING_DIR / VALIDATOR_NAME / "source_docs.zip"

WARRANTY_POLICY_LINES = [
    "Warranty Policy",
    "All electronics purchased from this store include a 1-year",
    "manufacturer warranty covering defects in materials and workmanship.",
    "Accidental damage and water damage are not covered.",
    "A valid proof of purchase is required for all warranty claims.",
]


def _make_simple_pdf(lines: list[str]) -> bytes:
    """Hand-rolled minimal single-page PDF with the given lines of text.

    Just enough PDF structure (catalog, pages, one page, a Helvetica font,
    a content stream) for PyPDF2 to extract the text back out — not a
    general-purpose PDF writer.
    """
    content_lines = ["BT", "/F1 12 Tf", "72 720 Td", "14 TL"]
    for i, line in enumerate(lines):
        escaped = line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        content_lines.append("T*" if i else f"({escaped}) Tj")
        if i:
            content_lines.append(f"({escaped}) Tj")
    content_lines.append("ET")
    content = "\n".join(content_lines).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 612 792] /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
    ]

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode())
        out.write(obj)
        out.write(b"\nendobj\n")

    xref_offset = out.tell()
    n = len(objects) + 1
    out.write(f"xref\n0 {n}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.write(f"{off:010} 00000 n \n".encode())
    out.write(b"trailer\n")
    out.write(f"<< /Size {n} /Root 1 0 R >>\n".encode())
    out.write(b"startxref\n")
    out.write(f"{xref_offset}\n".encode())
    out.write(b"%%EOF")
    return out.getvalue()


def _build_sample_zip(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("warranty_policy.pdf", _make_simple_pdf(WARRANTY_POLICY_LINES))


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
        topic="customer support for consumer electronics warranty questions",
        context="an electronics store's warranty support assistant",
        restricted_topics=["issuing refunds or replacement units directly"],
        zip_path=str(ZIP_PATH),
        total_topic_questions=300,
        datasets_path=DATASETS_PATH,
    )

# --- Try it out --------------------------------------------------------------
for prompt in [
    "Does the warranty cover a cracked screen from a drop?",
    "Can you approve a replacement unit for me right now?",
]:
    result = asyncio.run(sentence_validator.validate(prompt))
    print(f"{result.valid!s:>5}  {prompt}")
